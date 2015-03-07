from django.conf import settings
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

from core.breadcrumbs import make_breadcrumbs

from althingi.models import Parliament

class ExtraVarsMiddleware():
    # For handing certain variables over to the context processor for global display.
    def process_view(self, request, view_func, view_args, view_kwargs):

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

        try:
            newest_parliament_num = Parliament.objects.order_by('-parliament_num')[0].parliament_num
        except IndexError:
            newest_parliament_num = None

        request.extravars = {
            'newest_parliament_num': newest_parliament_num,
            'parliament_num': parliament_num,
            'issue_num': issue_num,
            'breadcrumbs': make_breadcrumbs(view_func.func_name, parliament_num, issue_num, session_num, committee_id, agenda_id),
            'urlname': view_func.func_name,
        }

class ForceLoginMiddleware():
    # Force login.
    def process_view(self, request, view_func, view_args, view_kwargs):
        return # temp, for development purposes

        if not request.user.is_authenticated() and request.get_full_path() != settings.LOGIN_URL:
            return redirect(settings.LOGIN_URL)

