import json

from django.db.models import Max
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string

from althingi.models import CommitteeAgenda
from althingi.models import CommitteeAgendaItem
from althingi.models import Session
from althingi.models import SessionAgendaItem

from core.models import Issue
from core.models import IssueUtilities

from dossier.models import Dossier
from dossier.models import DossierStatistic
from dossier.models import Memo

from jsonizer.utils import jsonize


@login_required
@jsonize
def dossier_fieldstate(request, dossier_id, fieldname):
    fieldstate = request.GET.get('fieldstate', None)

    if not fieldname in Dossier.tracker.fields:
        raise Exception('"%s" is not a recognized fieldname of a dossier' % fieldname)

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
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
def delete_dossier(request, dossier_id):

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    document_id = dossier.document_id
    review_id = dossier.review_id

    dossier.delete()

    ctx = {
        'document_id': document_id,
        'review_id': review_id,
    }
    return ctx


@login_required
@jsonize
def delete_issue_dossiers(request, issue_id):

    stub_ctx = {}

    Dossier.objects.filter(issue_id=issue_id, user_id=request.user.id).delete()
    DossierStatistic.objects.filter(issue_id=issue_id, user_id=request.user.id).delete()

    issue = Issue.objects.select_related('parliament').get(id=issue_id)
    IssueUtilities.populate_dossier_statistics([issue])

    monitored_issues = request.extravars['monitored_issues']

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
        'monitored_issues': monitored_issues,
    })
    html_content = render_to_string('core/stub/issue.html', stub_ctx, request=request)

    ctx = {
        'issue_id': issue_id,
        'html_content': html_content,
    }
    return ctx


@login_required
@jsonize
def add_memo(request, dossier_id):

    max_order = Memo.objects.filter(
        user_id=request.user.id,
        dossier_id=dossier_id
    ).aggregate(maximum=Max('order'))['maximum']

    memo = Memo(user_id=request.user.id, dossier_id=dossier_id)
    memo.content = request.POST.get('content')
    memo.order = max_order + 1 if max_order is not None else 1
    memo.save()

    memos = Memo.objects.filter(dossier_id=dossier_id, user_id=request.user.id)

    stub_ctx = {
        'memos': memos,
        'dossier_id': dossier_id,
        'max_memo_length': Memo._meta.get_field('content').max_length,
    }
    html_content = render_to_string('core/stub/dossier_memos.html', stub_ctx)

    ctx = {
        'html_content': html_content,
        'dossier_id': dossier_id,
        'memo_count': len(memos),
    }
    return ctx


@login_required
@jsonize
def edit_memo(request, memo_id):

    memo = Memo.objects.get(id=memo_id, user_id=request.user.id)
    dossier_id = memo.dossier_id

    memo.content = request.POST.get('content')
    memo.save()

    memos = Memo.objects.filter(dossier_id=dossier_id, user_id=request.user.id)

    stub_ctx = {
        'memos': memos,
        'dossier_id': dossier_id,
        'max_memo_length': Memo._meta.get_field('content').max_length,
    }
    html_content = render_to_string('core/stub/dossier_memos.html', stub_ctx)

    ctx = {
        'html_content': html_content,
        'dossier_id': dossier_id,
    }
    return ctx


@login_required
@jsonize
def delete_memo(request, memo_id):

    memo = Memo.objects.get(id=memo_id, user_id=request.user.id)
    dossier_id = memo.dossier_id
    memo.delete()

    memos = Memo.objects.filter(dossier_id=dossier_id, user_id=request.user.id)

    stub_ctx = {
        'memos': memos,
        'dossier_id': dossier_id,
        'max_memo_length': Memo._meta.get_field('content').max_length,
    }
    html_content = render_to_string('core/stub/dossier_memos.html', stub_ctx)

    ctx = {
        'html_content': html_content,
        'dossier_id': dossier_id,
        'memo_count': len(memos),
    }
    return ctx


@login_required
@jsonize
def sort_memos(request, dossier_id):

    order_map = json.loads(request.POST.get('order_map'))

    memos = Memo.objects.filter(dossier_id=dossier_id, user_id=request.user.id)
    for memo in memos:
        if memo.order != order_map[str(memo.id)]:
            memo.order = order_map[str(memo.id)]
            memo.save()

    memos = memos.order_by('order')

    stub_ctx = {
        'memos': memos,
        'dossier_id': dossier_id,
        'max_memo_length': Memo._meta.get_field('content').max_length,
    }
    html_content = render_to_string('core/stub/dossier_memos.html', stub_ctx)

    ctx = {
        'html_content': html_content,
        'dossier_id': memo.dossier_id,
    }
    return ctx


