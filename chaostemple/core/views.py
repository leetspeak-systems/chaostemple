from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.shortcuts import render

from core.models import Dossier

from althingi.models import Document
from althingi.models import Issue
from althingi.models import Parliament
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

    ctx = {
        'issues': issues
    }
    return render(request, 'core/parliament_issues.html', ctx)

def parliament_issue(request, parliament_num, issue_num):

    issue = Issue.objects.get(parliament__parliament_num=parliament_num, issue_group='A', issue_num=issue_num)
    documents = Document.objects.prefetch_related(
        'proposers__person',
        'proposers__committee',
        'dossiers__user'
    ).filter(issue=issue)

    if request.user.is_authenticated():
        for document in documents:
            document.mydossier, created = Dossier.objects.select_related('user').get_or_create(document=document, user=request.user)

    ctx = {
        'issue': issue,
        'documents': documents,
        'attentionstates': Dossier.ATTENTION_STATES,
        'knowledgestates': Dossier.KNOWLEDGE_STATES,
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

