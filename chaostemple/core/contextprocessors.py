from django.conf import settings

from althingi.models import Parliament
from althingi.models import Session

from core.models import Issue

def globals(request):

    parliaments = Parliament.objects.order_by('-parliament_num')
    next_sessions = Session.objects.upcoming().select_related('parliament')

    bookmarked_issues = None
    if request.user.is_authenticated():
        last_parliament_num = None
        bookmarked_issues = Issue.objects.select_related('parliament').filter(issue_bookmarks__user_id=request.user.id)
        for bookmarked_issue in reversed(bookmarked_issues):
            if bookmarked_issue.parliament.parliament_num != last_parliament_num:
                bookmarked_issue.display_parliament = True

            last_parliament_num = bookmarked_issue.parliament.parliament_num

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
