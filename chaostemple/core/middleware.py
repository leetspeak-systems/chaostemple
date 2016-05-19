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

from core.models import DossierStatistic
from core.models import Issue
from core.models import IssueUtilities

class ExtraVarsMiddleware():
    # For handing certain variables over to the context processor for global display.
    def process_view(self, request, view_func, view_args, view_kwargs):

        # Collect available information from view
        parliament_num = view_kwargs.get('parliament_num')
        issue_num = view_kwargs.get('issue_num')
        session_num = view_kwargs.get('session_num')
        committee_id = view_kwargs.get('committee_id')
        agenda_id = view_kwargs.get('agenda_id')
        if parliament_num:
            parliament_num = int(parliament_num)
        if issue_num:
            issue_num = int(issue_num)
        if session_num:
            session_num = int(session_num)
        if committee_id:
            committee_id = int(committee_id)
        if agenda_id:
            agenda_id = int(agenda_id)

        # Use settings for parliament_num if not determined in view
        if not parliament_num:
            parliament_num = CURRENT_PARLIAMENT_NUM

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

            IssueUtilities.populate_dossier_statistics(bookmarked_issues, request.user.id)

            # Get incoming things that the user has not yet seen
            dossier_statistics_incoming = DossierStatistic.objects.select_related('issue__parliament').filter(
                Q(user_id=request.user.id, has_useful_info=True, issue__parliament__parliament_num=parliament_num),
                ~Q(
                    document_count=F('issue__document_count'),
                    review_count=F('issue__review_count')
                )
            ).order_by('-issue__issue_num')
            for stat in dossier_statistics_incoming:
                stat.new_documents = stat.issue.document_count - stat.document_count
                stat.new_reviews = stat.issue.review_count - stat.review_count

        # Get parliaments, next sessions and next committees (we use this virtually always)
        parliaments = Parliament.objects.order_by('-parliament_num')
        next_sessions = Session.objects.upcoming().select_related('parliament')
        next_committee_agendas = CommitteeAgenda.objects.upcoming().select_related('parliament', 'committee')

        len(next_sessions) # Forces a len() instead of a DB-call when count is checked
        len(next_committee_agendas) # Forces a len() instead of a DB-call when count is checked

        request.extravars = {
            'newest_parliament_num': newest_parliament_num,
            'parliament_num': parliament_num,
            'issue_num': issue_num,
            'breadcrumbs': make_breadcrumbs(view_func.func_name, parliament_num, issue_num, session_num, committee_id, agenda_id),
            'parliaments': parliaments,
            'next_sessions': next_sessions,
            'next_committee_agendas': next_committee_agendas,
            'bookmarked_issues': bookmarked_issues,
            'dossier_statistics_incoming': dossier_statistics_incoming,
            'urlname': view_func.func_name,
        }

class ForceLoginMiddleware():
    # Force login.
    def process_view(self, request, view_func, view_args, view_kwargs):
        return # temp, for development purposes

        if not request.user.is_authenticated() and request.get_full_path() != settings.LOGIN_URL:
            return redirect(settings.LOGIN_URL)

