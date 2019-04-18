from django.conf import settings
from django.urls import reverse
from django.db.models import F
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import ugettext as _

from core.breadcrumbs import make_breadcrumbs

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import CommitteeAgenda
from althingi.models import Parliament
from althingi.models import Session

from core.models import AccessUtilities
from core.models import Issue
from core.models import IssueUtilities
from core.models import UserProfile

class AccessMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        AccessUtilities.cache_access(request.user)


class UserLastSeenMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated:
            UserProfile.objects.filter(user_id=request.user.id).update(last_seen=timezone.now())


class ExtraVarsMiddleware():
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    # For handing certain variables over to the context processor for global display.
    def process_view(self, request, view_func, view_args, view_kwargs):

        # Figure out which parliament we're viewing
        parliament_num = int(view_kwargs.get('parliament_num', CURRENT_PARLIAMENT_NUM))
        try:
            parliament = Parliament.objects.get(parliament_num=parliament_num)
        except Parliament.DoesNotExist:
            # If the requested parliament isn't the current one, we raise a "page not found" error.
            if parliament_num != CURRENT_PARLIAMENT_NUM:
                raise Http404

            # We're missing data. We'll redirect to a help page if we're not already there.
            if view_func.func_name != 'parliament_missing_data':
                return redirect(reverse('parliament_missing_data'))
            else:
                parliament = None

        # Stuff for logged in users
        monitored_issues = None
        incoming_issues = None
        if request.user.is_authenticated:
            # Monitors
            monitored_issues = Issue.objects.select_related('parliament').filter(
                issue_monitors__user_id=request.user.id,
                parliament__parliament_num=parliament_num
            ).annotate_news(
                request.user.id
            ).exclude(
                new_documents=0,
                new_reviews=0
            ).order_by(
                'issue_num'
            )

            # Hide concluded issues from monitoring menu.
            if request.user.userprofile.setting_hide_concluded_from_monitors:
                monitored_issues = monitored_issues.exclude(current_step='concluded')

            # Get incoming things that the user has not yet seen
            if settings.FEATURES['incoming_issues']:
                incoming_issues = Issue.objects.select_related('parliament', 'to_committee').filter(
                    parliament__parliament_num=parliament_num
                ).incoming(request.user.id).order_by('-issue_num')

        # Get parliaments, next sessions and next committees (we use this virtually always)
        next_sessions = Session.objects.upcoming().select_related('parliament')
        next_committee_agendas = CommitteeAgenda.objects.upcoming().select_related('parliament', 'committee')

        len(next_sessions) # Forces a len() instead of a DB-call when count is checked
        len(next_committee_agendas) # Forces a len() instead of a DB-call when count is checked

        breadcrumbs = None if parliament is None else make_breadcrumbs(request, parliament)

        request.extravars = {
            'newest_parliament_num': CURRENT_PARLIAMENT_NUM,
            'parliament_num': parliament_num,
            'parliament': parliament,
            'breadcrumbs': breadcrumbs,
            'next_sessions': next_sessions,
            'next_committee_agendas': next_committee_agendas,
            'monitored_issues': monitored_issues,
            'incoming_issues': incoming_issues,
            'view_name': request.resolver_match.view_name,
        }

