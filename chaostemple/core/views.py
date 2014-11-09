from django.db.models import Count
from django.shortcuts import render

from althingi.models import Document
from althingi.models import Issue
from althingi.models import Session

def home(request):
    ctx = {'issues': 'ISSUES'}
    return render(request, 'core/home.html', ctx)

def parliament(request, parliament_num):

    ctx = {
    }
    return render(request, 'core/parliament.html', ctx)

def parliament_issues(request, parliament_num):

    issues = Issue.objects.select_related('parliament').filter(
        parliament__parliament_num=parliament_num,
        document_count__gt=0
    )

    ctx = {
        'issues': issues
    }
    return render(request, 'core/parliament_issues.html', ctx)

def parliament_issue(request, parliament_num, issue_num):

    issue = Issue.objects.get(parliament__parliament_num=parliament_num, issue_group='A', issue_num=issue_num)
    documents = Document.objects.prefetch_related('proposers__person', 'proposers__committee').filter(issue=issue)

    ctx = {
        'issue': issue,
        'documents': documents,
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
        'agenda_items__issue__parliament'
    ).get(parliament__parliament_num=parliament_num, session_num=session_num)

    ctx = {
        'session': session
    }
    return render(request, 'core/parliament_session.html', ctx)

