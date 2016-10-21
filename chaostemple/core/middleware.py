from django.conf import settings
from django.db.models import F
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

from core.breadcrumbs import make_breadcrumbs

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import CommitteeAgenda
from althingi.models import Parliament
from althingi.models import Session

from core.models import AccessUtilities
from core.models import DossierStatistic
from core.models import DossierUtilities
from core.models import Issue
from core.models import IssueUtilities


class AccessMiddleware():
    def process_view(self, request, view_func, view_args, view_kwargs):
        AccessUtilities.cache_access(request.user.id)


class ExtraVarsMiddleware():
    # For handing certain variables over to the context processor for global display.
    def process_view(self, request, view_func, view_args, view_kwargs):

        # Figure out which parliament we're viewing
        parliament_num = int(view_kwargs.get('parliament_num', CURRENT_PARLIAMENT_NUM))

        # Determine newest parliament number
        try:
            newest_parliament_num = Parliament.objects.order_by('-parliament_num')[0].parliament_num
        except IndexError:
            newest_parliament_num = None

        # Stuff for logged in users
        bookmarked_issues = None
        dossier_statistics_incoming = None
        if request.user.is_authenticated():
            # Bookmarks
            bookmarked_issues = Issue.objects.select_related('parliament').filter(
                issue_bookmarks__user_id=request.user.id,
                parliament__parliament_num=parliament_num
            ).order_by('issue_num')

            IssueUtilities.populate_dossier_statistics(bookmarked_issues)

            # Get incoming things that the user has not yet seen
            dossier_statistics_incoming = DossierUtilities.get_incoming_dossier_statistics(request.user.id, parliament_num)

        # Get parliaments, next sessions and next committees (we use this virtually always)
        parliaments = Parliament.objects.order_by('-parliament_num')
        next_sessions = Session.objects.upcoming().select_related('parliament')
        next_committee_agendas = CommitteeAgenda.objects.upcoming().select_related('parliament', 'committee')

        len(next_sessions) # Forces a len() instead of a DB-call when count is checked
        len(next_committee_agendas) # Forces a len() instead of a DB-call when count is checked

        request.extravars = {
            'newest_parliament_num': newest_parliament_num,
            'parliament_num': parliament_num,
            'breadcrumbs': make_breadcrumbs(request),
            'parliaments': parliaments,
            'next_sessions': next_sessions,
            'next_committee_agendas': next_committee_agendas,
            'bookmarked_issues': bookmarked_issues,
            'dossier_statistics_incoming': dossier_statistics_incoming,
            'view_func_name': view_func.func_name,
        }

