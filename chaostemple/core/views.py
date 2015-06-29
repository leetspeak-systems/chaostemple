from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.template import RequestContext

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
    if request.extravars['newest_parliament_num'] is not None:
        return redirect(reverse('parliament', args=(request.extravars['newest_parliament_num'],)))
    else:
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

    # NOTE: The use of these get_prefetched_* functions is to be revised when Django 1.8 is released.
    # Specifically, it is hoped that the .refresh_from_db() function introduced will be a good replacement.

    def get_prefetched_documents():
        return Document.objects.prefetch_related(
            Prefetch('dossiers', queryset=Dossier.objects.filter(user_id=request.user.id)),
            'dossiers__memos',
            'proposers__person',
            'proposers__committee',
        ).filter(issue=issue)

    def get_prefetched_reviews():
        return Review.objects.prefetch_related(
            Prefetch('dossiers', queryset=Dossier.objects.filter(user_id=request.user.id)),
            'dossiers__memos',
        ).filter(issue=issue)

    issue = Issue.objects.get(parliament__parliament_num=parliament_num, issue_group='A', issue_num=issue_num)
    documents = get_prefetched_documents()
    reviews = get_prefetched_reviews()

    issue_sessions = Session.objects.select_related('parliament').filter(agenda_items__issue_id=issue.id)
    issue_committee_agendas = CommitteeAgenda.objects.select_related(
        'parliament',
        'committee'
    ).filter(committee_agenda_items__issue_id=issue.id)

    reload_documents = False
    reload_reviews = False
    if request.user.is_authenticated():
        for document in documents:
            if document.dossiers.count() == 0:
                Dossier(document=document, user=request.user).save(update_statistics=False)
                reload_documents = True

        for review in reviews:
            if review.dossiers.count() == 0:
                Dossier(review=review, user=request.user).save(update_statistics=False)
                reload_reviews = True

    if reload_documents:
        documents = get_prefetched_documents()
    if reload_reviews:
        reviews = get_prefetched_reviews()

    ctx = {
        'issue': issue,
        'issue_sessions': issue_sessions,
        'issue_committee_agendas': issue_committee_agendas,
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
    agenda_items = session.agenda_items.select_related('issue__parliament').all()

    IssueUtilities.populate_dossier_statistics((i.issue for i in agenda_items), request.user.id)

    ctx = {
        'session': session,
        'agenda_items': agenda_items,
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
def user_home(request, username):

    home_user = get_object_or_404(User, username=username)

    ctx = {
        'home_user': home_user,
    }
    return render(request, 'core/user_home.html', ctx)

@login_required
def user_issues_bookmarked(request):

    issues = Issue.objects.select_related('parliament').filter(issue_bookmarks__user_id=request.user.id)

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'issues': issues
    }
    return render(request, 'core/user_issues_bookmarked.html', ctx)

@login_required
def user_issues_incoming(request):
    ctx = RequestContext(request)

    issues = [ds.issue for ds in ctx['dossier_statistics_incoming']]

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'issues': issues
    }

    return render(request, 'core/user_issues_incoming.html', ctx)

@login_required
def user_issues_open(request):
    ctx = RequestContext(request)

    issues = [i for i in ctx['open_issues']]

    IssueUtilities.populate_dossier_statistics(issues, request.user.id)

    ctx = {
        'issues': issues
    }

    return render(request, 'core/user_issues_open.html', ctx)

def error500(request):
    response = render(request, '500.html')
    return response
