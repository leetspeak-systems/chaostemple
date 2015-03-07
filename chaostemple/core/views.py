from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.shortcuts import redirect
from django.shortcuts import render

from core.models import Dossier
from core.models import DossierStatistic
from core.models import Issue
from core.models import IssueBookmark
from core.models import IssueUtilities

from althingi.models import Committee
from althingi.models import CommitteeAgenda
from althingi.models import Document
from althingi.models import Parliament
from althingi.models import Review
from althingi.models import Session

def home(request):
    try:
        parliament = Parliament.objects.order_by('-parliament_num')[0]
        return redirect(reverse('parliament', args=(parliament.parliament_num,)))
    except IndexError:
        return render(request, 'core/parliament_none.html', {})

def parliament(request, parliament_num):

    ctx = {
    }
    return render(request, 'core/parliament.html', ctx)

def parliament_issues(request, parliament_num):

    issues = Issue.objects.select_related('parliament').filter(
        parliament__parliament_num=parliament_num,
        document_count__gt=0
    )

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'issues': issues,
    }
    return render(request, 'core/parliament_issues.html', ctx)

def parliament_issue(request, parliament_num, issue_num):

    issue = Issue.objects.get(parliament__parliament_num=parliament_num, issue_group='A', issue_num=issue_num)
    documents = Document.objects.prefetch_related(
        'proposers__person',
        'proposers__committee',
        'dossiers__user'
    ).filter(issue=issue)
    reviews = Review.objects.filter(issue=issue)

    if request.user.is_authenticated():
        for document in documents:
            try:
                document.mydossier = Dossier.objects.select_related('user', 'document').get(document=document, user=request.user)
            except Dossier.DoesNotExist:
                document.mydossier = Dossier(document=document, user=request.user)
                document.mydossier.save(update_statistics=False)

        for review in reviews:
            try:
                review.mydossier = Dossier.objects.select_related('user', 'document').get(review=review, user=request.user)
            except Dossier.DoesNotExist:
                review.mydossier = Dossier(review=review, user=request.user)
                review.mydossier.save(update_statistics=False)

    ctx = {
        'issue': issue,
        'documents': documents,
        'reviews': reviews,
        'attentionstates': Dossier.ATTENTION_STATES,
        'knowledgestates': Dossier.KNOWLEDGE_STATES,
        'supportstates': Dossier.SUPPORT_STATES,
        'proposalstates': Dossier.PROPOSAL_STATES,
    }
    return render(request, 'core/parliament_issue.html', ctx)

def parliament_sessions(request, parliament_num):

    sessions = Session.objects.filter(parliament__parliament_num=parliament_num).annotate(
        agenda_item_count=Count('agenda_items')
    )

    ctx = {
        'sessions': sessions
    }
    return render(request, 'core/parliament_sessions.html', ctx)

def parliament_session(request, parliament_num, session_num):

    session = Session.objects.get(parliament__parliament_num=parliament_num, session_num=session_num)
    issues = Issue.objects.select_related('parliament').filter(agenda_items__session=session).order_by('agenda_items__order')

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'session': session,
        'issues': issues,
    }
    return render(request, 'core/parliament_session.html', ctx)

def parliament_committees(request, parliament_num):

    committees = Committee.objects.filter(parliaments__parliament_num=parliament_num).annotate(
        agenda_count=Count('committee_agendas')
    )

    ctx = {
        'committees': committees
    }
    return render(request, 'core/parliament_committees.html', ctx)

def parliament_committee(request, parliament_num, committee_id):

    committee = Committee.objects.get(id=committee_id)
    agendas = committee.committee_agendas.all().annotate(item_count=Count('committee_agenda_items'))

    ctx = {
        'committee': committee,
        'agendas': agendas,
    }
    return render(request, 'core/parliament_committee.html', ctx)

def parliament_committee_agenda(request, parliament_num, committee_id, agenda_id):

    committee = Committee.objects.get(id=committee_id)
    agenda = committee.committee_agendas.get(id=agenda_id)
    items = agenda.committee_agenda_items.select_related('issue__parliament').all()

    IssueUtilities.populate_dossier_statistics([i.issue for i in items], request.user.id)

    ctx = {
        'committee': committee,
        'agenda': agenda,
        'items': items,
    }
    return render(request, 'core/parliament_committee_agenda.html', ctx)

@login_required
def user_issues_bookmarked(request):

    issues = Issue.objects.select_related('parliament').filter(issue_bookmarks__user_id=request.user.id)

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'issues': issues
    }
    return render(request, 'core/user_issues_bookmarked.html', ctx)


def error500(request):
    response = render(request, '500.html')
    return response
