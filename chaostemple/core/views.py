from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.shortcuts import render

from core.models import Dossier
from core.models import DossierStatistic
from core.models import IssueBookmark

from althingi.models import Document
from althingi.models import Issue
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

    issues = Issue.objects.select_related('parliament').prefetch_related('dossier_statistics').filter(
        parliament__parliament_num=parliament_num,
        document_count__gt=0
    )

    bookmarked_issue_ids = [b.issue_id for b in IssueBookmark.objects.filter(user_id=request.user.id)]
    for issue in issues:
        if issue.id in bookmarked_issue_ids:
            issue.is_bookmarked = True

    ctx = {
        'issues': issues,
        'dossier_types': [{'fieldname': fieldname, 'name': name} for fieldname, name in Dossier.DOSSIER_TYPES],
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
                document.mydossier = Dossier.objects.select_related('user').get(document=document, user=request.user)
            except Dossier.DoesNotExist:
                document.mydossier = Dossier(document=document, user=request.user)
                document.mydossier.save(update_statistics=False)

        for review in reviews:
            try:
                review.mydossier = Dossier.objects.select_related('user').get(review=review, user=request.user)
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

    sessions = Session.objects.filter(parliament__parliament_num=parliament_num)

    ctx = {
        'sessions': sessions
    }
    return render(request, 'core/parliament_sessions.html', ctx)

def parliament_session(request, parliament_num, session_num):

    session = Session.objects.prefetch_related(
        'agenda_items__issue',
        'agenda_items__issue__parliament',
        'agenda_items__issue__dossier_statistics'
    ).get(parliament__parliament_num=parliament_num, session_num=session_num)

    ctx = {
        'session': session
    }
    return render(request, 'core/parliament_session.html', ctx)

