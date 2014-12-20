from django.conf import settings
from django.utils import timezone

from althingi.models import Parliament
from althingi.models import Session

from core.models import Issue

def globals(request):

    parliaments = Parliament.objects.order_by('-parliament_num')
    next_sessions = Session.objects.select_related('parliament').filter(timing_start_planned__gt=timezone.now())

    # Since XML cannot determine the planned timing of a session that comes immediately after
    # another, we need to make an extra call to include all the sessions with a higher session_num
    if next_sessions.count() > 0:
        next_sessions = next_sessions | Session.objects.filter(session_num__gt=next_sessions.last().session_num)

    bookmarked_issues = Issue.objects.filter(issue_bookmarks__user_id=request.user.id)

    ctx = {
        'PROJECT_NAME': settings.PROJECT_NAME,
        'PROJECT_VERSION': settings.PROJECT_VERSION,
        'parliaments': parliaments,
        'next_sessions': next_sessions,
        'bookmarked_issues': bookmarked_issues,
    }

    if hasattr(request, 'extravars'):
        ctx.update(request.extravars) # See chaostemple.middleware.ExtraVarsMiddleware

    return ctx
