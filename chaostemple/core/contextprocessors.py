from django.conf import settings
from django.db.models import Count
from django.db.models import F
from django.db.models import Q

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import CommitteeAgenda
from althingi.models import Parliament
from althingi.models import Session

from core.models import DossierStatistic
from core.models import Issue

def globals(request):

    ctx = request.extravars # See chaostemple.middleware.ExtraVarsMiddleware

    parliaments = Parliament.objects.order_by('-parliament_num')
    next_sessions = Session.objects.upcoming().select_related('parliament')
    next_committee_agendas = CommitteeAgenda.objects.upcoming().select_related('parliament', 'committee')

    bookmarked_issues = None
    if request.user.is_authenticated():
        last_parliament_num = None
        bookmarked_issues = Issue.objects.select_related('parliament').filter(
            issue_bookmarks__user_id=request.user.id
        ).order_by('parliament__parliament_num', 'issue_num')
        for bookmarked_issue in reversed(bookmarked_issues):
            if bookmarked_issue.parliament.parliament_num != last_parliament_num:
                bookmarked_issue.display_parliament = True

            last_parliament_num = bookmarked_issue.parliament.parliament_num

    dossier_statistics_incoming = DossierStatistic.objects.select_related('issue__parliament').filter(
        Q(user_id=request.user.id, issue__parliament__parliament_num=ctx['parliament_num']),
        ~Q(
            document_count=F('issue__document_count'),
            review_count=F('issue__review_count')
        )
    ).order_by('-issue__issue_num')
    for stat in dossier_statistics_incoming:
        stat.new_documents = stat.issue.document_count - stat.document_count
        stat.new_reviews = stat.issue.review_count - stat.review_count

    len(next_sessions) # Forces a len() instead of a DB-call when count is checked
    len(next_committee_agendas) # Forces a len() instead of a DB-call when count is checked

    ctx.update({
        'PROJECT_NAME': settings.PROJECT_NAME,
        'PROJECT_VERSION': settings.PROJECT_VERSION,
        'parliaments': parliaments,
        'next_sessions': next_sessions,
        'next_committee_agendas': next_committee_agendas,
        'bookmarked_issues': bookmarked_issues,
        'dossier_statistics_incoming': dossier_statistics_incoming,
    })

    return ctx
