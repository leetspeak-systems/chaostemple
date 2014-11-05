from django.conf import settings
from django.shortcuts import redirect
from django.utils.translation import ugettext as _

class ExtraVarsMiddleware():
    def leave_breadcrumb(self, breadcrumbs, urlname, caption):
        return breadcrumbs + ((urlname, caption),)

    # For handing certain variables over to the context processor for global display.
    def process_view(self, request, view_func, view_args, view_kwargs):

        parliament_num = view_kwargs.get('parliament_num')
        issue_num = view_kwargs.get('issue_num')
        session_num = view_kwargs.get('session_num')
        if parliament_num:
            parliament_num = int(parliament_num)
        if issue_num:
            issue_num = int(issue_num)
        if session_num:
            session_num = int(session_num)

        breadcrumbs = (
            (('home',), _('Home')),
        )

        if parliament_num:
            breadcrumbs = self.leave_breadcrumb(
                breadcrumbs,
                ('parliament', parliament_num),
                '%d. %s' % (parliament_num, _('parliament'))
            )

        if view_func.func_name in ('parliament_issues', 'parliament_issue'):
            breadcrumbs = self.leave_breadcrumb(
                breadcrumbs,
                ('parliament_issues', parliament_num),
                _('Issues')
            )
        
        if view_func.func_name == 'parliament_issue':
            breadcrumbs = self.leave_breadcrumb(
                breadcrumbs,
                ('parliament_issue', parliament_num, issue_num),
                '%d. %s' % (issue_num, _('issue'))
            )

        if view_func.func_name in ('parliament_sessions', 'parliament_session'):
            breadcrumbs = self.leave_breadcrumb(
                breadcrumbs,
                ('parliament_sessions', parliament_num),
                _('Parliamentary Sessions')
            )

        if view_func.func_name == 'parliament_session':
            breadcrumbs = self.leave_breadcrumb(
                breadcrumbs,
                ('parliament_session', parliament_num, session_num),
                '%d. %s' % (session_num, _('parliamentary session'))
            )

        request.extravars = {
            'parliament_num': parliament_num,
            'issue_num': issue_num,
            'breadcrumbs': breadcrumbs,
        }

class ForceLoginMiddleware():
    # Force login.
    def process_view(self, request, view_func, view_args, view_kwargs):
        return # temp, for development purposes

        if not request.user.is_authenticated() and request.get_full_path() != settings.LOGIN_URL:
            return redirect(settings.LOGIN_URL)

