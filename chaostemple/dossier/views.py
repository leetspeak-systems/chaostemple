import json

from django.db.models import Max
from django.db.models import Prefetch
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.template.defaultfilters import capfirst
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _

from djalthingi.models import CommitteeAgenda
from djalthingi.models import CommitteeAgendaItem
from djalthingi.models import Session
from djalthingi.models import SessionAgendaItem

from core.models import Document
from core.models import Issue
from core.models import IssueMonitor
from core.models import IssueUtilities
from core.models import Review
from core.models import Subscription

from dossier.models import Dossier
from dossier.models import DossierStatistic

from jsonizer.utils import jsonize


# A utility function to create sensible kwargs parameters to either locate or
# create a Dossier from given input.
def kwargs_from_input(user, parliament_num, doc_num, log_num):
    q_kwargs = {'user_id': user.id}
    if doc_num is not None and log_num is None:
        document = Document.objects.select_related('issue').get(
            issue__parliament__parliament_num=parliament_num,
            doc_num=doc_num
        )
        q_kwargs['dossier_type'] = 'document'
        q_kwargs['document_id'] = document.id
        q_kwargs['issue_id'] = document.issue_id
    elif doc_num is None and log_num is not None:
        review = Review.objects.select_related('issue').get(
            issue__parliament__parliament_num=parliament_num,
            log_num=log_num
        )
        q_kwargs['dossier_type'] = 'review'
        q_kwargs['review_id'] = review.id
        q_kwargs['issue_id'] = review.issue_id
    else:
        raise Exception('Only "doc_num" or "log_num" must be provided but not both')

    return q_kwargs


@login_required
def dossier(request, parliament_num, doc_num=None, log_num=None):

    d_kwargs = kwargs_from_input(request.user, parliament_num, doc_num, log_num)
    try:
        dossier = Dossier.objects.select_related('issue', 'document', 'review').get(**d_kwargs)
    except Dossier.DoesNotExist:
        dossier = Dossier(**d_kwargs)

    statistic = DossierStatistic.objects.filter(issue_id=dossier.issue_id, user_id=request.user.id).first()

    IssueUtilities.populate_issue_data([dossier.issue])

    # Construct the page title so that the user can more easily navigate
    # different dossiers in different tabs/windows/whatever. It needs to
    # fulfill two competing goals, being both short and descriptive.
    if doc_num is not None:
        page_title = '(%d) %s' % (
            dossier.document.doc_num,
            dossier.document.doc_type
        )
    elif log_num is not None:
        page_title = dossier.review.sender_name
    # Append the common part of the page title.
    page_title += ': %s (%d. %s)' % (
        capfirst(dossier.issue.name),
        dossier.issue.issue_num,
        _('issue')
    )

    ctx = {
        'page_title': page_title,

        'issue': dossier.issue,
        'dossier': dossier,
        'statistic': statistic,

        'attentionstates': Dossier.ATTENTION_STATES,
        'knowledgestates': Dossier.KNOWLEDGE_STATES,
        'supportstates': Dossier.SUPPORT_STATES,
        'proposalstates': Dossier.PROPOSAL_STATES,
    }
    return render(request, 'dossier/dossier.html', ctx)


@login_required
@jsonize
def dossier_fieldstate(request, parliament_num, doc_num=None, log_num=None, fieldname=None):
    fieldstate = request.GET.get('fieldstate', None)

    if not fieldname in Dossier.tracker.fields:
        raise Exception('"%s" is not a recognized fieldname of a dossier' % fieldname)

    q_kwargs = kwargs_from_input(request.user, parliament_num, doc_num, log_num)

    dossier, created = Dossier.objects.get_or_create(**q_kwargs)
    if fieldstate is not None and getattr(dossier, fieldname) != fieldstate:
        # Ensure proper type of field
        fieldtype = type(getattr(dossier, fieldname))
        fieldstate = fieldtype(fieldstate)

        setattr(dossier, fieldname, fieldstate)
        dossier.save()

    ctx = {
        fieldname: getattr(dossier, fieldname),
    }
    return ctx


@login_required
@jsonize
def create_dossier(request, parliament_num, doc_num=None, log_num=None):

    # Same dossier prefetch regardless of whether the dossier belongs to a
    # document or a review.
    prefetch_q = Dossier.objects.by_user(request.user)

    if doc_num is not None:

        document = Document.objects.get(issue__parliament__parliament_num=parliament_num, doc_num=doc_num)
        try:
            Dossier.objects.get(user=request.user, document=document)
        except Dossier.DoesNotExist:
            Dossier(user=request.user, document=document).save()

        # Data must be reloaded to reflect change.
        document = Document.objects.prefetch_related(
            Prefetch('dossiers', queryset=prefetch_q)
        ).annotate_seen(
            request.user
        ).get(
            issue__parliament__parliament_num=parliament_num,
            doc_num=doc_num
        )

        html = render_to_string('core/stub/document.html', { 'document': document }, request=request)

        return {
            'document_id': document.id,
            'html': html,
        }

    elif log_num is not None:

        review = Review.objects.get(issue__parliament__parliament_num=parliament_num, log_num=log_num)
        try:
            Dossier.objects.get(user=request.user, review=review)
        except Dossier.DoesNotExist:
            Dossier(user=request.user, review=review).save()

        # Data must be reloaded to reflect change.
        review = Review.objects.prefetch_related(
            Prefetch('dossiers', queryset=prefetch_q)
        ).annotate_seen(
            request.user
        ).get(
            issue__parliament__parliament_num=parliament_num,
            log_num=log_num
        )

        html = render_to_string('core/stub/review.html', { 'review': review }, request=request)
        print(html)

        return {
            'review_id': review.id,
            'html': html,
        }


@login_required
@jsonize
def delete_dossier(request, parliament_num, doc_num=None, log_num=None):

    # Same dossier prefetch regardless of whether the dossier belongs to a
    # document or a review.
    prefetch_q = Dossier.objects.by_user(request.user)

    if doc_num is not None:

        Dossier.objects.get(
            user=request.user,
            document__issue__parliament__parliament_num=parliament_num,
            document__doc_num=doc_num
        ).delete()

        document = Document.objects.prefetch_related(
            Prefetch('dossiers', queryset=prefetch_q)
        ).get(
            issue__parliament__parliament_num=parliament_num,
            doc_num=doc_num
        )

        html = render_to_string('core/stub/document.html', { 'document': document }, request=request)

        return {
            'document_id': document.id,
            'html': html,
        }

    elif log_num is not None:

        Dossier.objects.get(
            user=request.user,
            review__issue__parliament__parliament_num=parliament_num,
            review__log_num=log_num
        ).delete()

        review = Review.objects.prefetch_related(
            Prefetch('dossiers', queryset=prefetch_q)
        ).get(
            issue__parliament__parliament_num=parliament_num,
            log_num=log_num
        )

        html = render_to_string('core/stub/review.html', { 'review': review }, request=request)

        return {
            'review_id': review.id,
            'html': html,
        }


@login_required
@jsonize
def delete_issue_dossiers(request, issue_id):

    stub_ctx = {}

    issue = Issue.objects.select_related('parliament').get(id=issue_id)

    is_subscribed = Subscription.objects.filter(
        Q(committee__issues=issue) | Q(category__issues=issue),
        user_id=request.user.id
    ).count() > 0

    Dossier.objects.filter(issue_id=issue_id, user_id=request.user.id).delete()

    # If the issue is being monitored or is subscribed to, we want to retain
    # the dossier statistics to keep tracking changes of status and
    # document/review counts. If the issue is not being monitored, however,
    # we'll delete the dossier statistic for the sake of data cleanliness.
    stat = issue.dossierstatistic_set.get(user_id=request.user.id)
    monitor_issue_ids = [m['issue_id'] for m in IssueMonitor.objects.filter(user=request.user).values('issue_id')]
    if is_subscribed or issue.id in monitor_issue_ids:
        # Reset the statistics.
        stat.reset()

        # Trigger an upate to has_useful_info.
        stat.save()
    else:
        stat.delete()

    IssueUtilities.populate_issue_data([issue])

    # Get session agenda header information if needed
    session_agenda_item_id = int(request.GET.get('session_agenda_item_id', 0) or 0)
    if session_agenda_item_id:
        stub_ctx['session_agenda_item'] = SessionAgendaItem.objects.get(id=session_agenda_item_id)

    # Get committee agenda header information if needed
    committee_agenda_item_id = int(request.GET.get('committee_agenda_item_id', 0) or 0)
    if committee_agenda_item_id:
        stub_ctx['committee_agenda_item'] = CommitteeAgendaItem.objects.get(id=committee_agenda_item_id)

    # Get upcoming session infomation if needed
    upcoming_session_ids = request.GET.get('upcoming_session_ids', '')
    if len(upcoming_session_ids):
        stub_ctx['upcoming_sessions'] = Session.objects.filter(id__in=[int(val) for val in upcoming_session_ids.split(',')])

    # Get upcoming committee agenda information if needed
    upcoming_committee_agenda_ids = request.GET.get('upcoming_committee_agenda_ids', '')
    if len(upcoming_committee_agenda_ids):
        stub_ctx['upcoming_committee_agendas'] = CommitteeAgenda.objects.filter(
            id__in=[int(val) for val in upcoming_committee_agenda_ids.split(',')]
        )

    stub_ctx.update({
        'issue': issue,
        'user': request.user,
        'monitored_issues': request.extravars['monitored_issues'],
    })
    html_content = render_to_string('core/stub/issue.html', stub_ctx, request=request)

    ctx = {
        'issue_id': issue_id,
        'html_content': html_content,
    }
    return ctx


@login_required
@jsonize
def set_notes(request, parliament_num, doc_num=None, log_num=None):
    d_kwargs = kwargs_from_input(request.user, parliament_num, doc_num, log_num)

    dossier, created = Dossier.objects.get_or_create(**d_kwargs)

    notes = request.POST.get('notes', '')

    dossier.notes = notes
    dossier.save()

    return {'notes': notes}
