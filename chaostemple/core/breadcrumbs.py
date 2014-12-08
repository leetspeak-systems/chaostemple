from django.utils.translation import ugettext as _

def leave_breadcrumb(breadcrumbs, urlname, caption):
    return breadcrumbs + ((urlname, caption),)

def make_breadcrumbs(func_name, parliament_num, issue_num, session_num):
    breadcrumbs = ()

    if parliament_num:
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament', parliament_num),
            '%d. %s' % (parliament_num, _('parliament'))
        )

    if func_name in ('parliament_issues', 'parliament_issue'):
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_issues', parliament_num),
            _('Issues')
        )

    if func_name == 'parliament_issue':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_issue', parliament_num, issue_num),
            '%d. %s' % (issue_num, _('issue'))
        )

    if func_name in ('parliament_sessions', 'parliament_session'):
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_sessions', parliament_num),
            _('Parliamentary Sessions')
        )

    if func_name == 'parliament_session':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_session', parliament_num, session_num),
            '%d. %s' % (session_num, _('parliamentary session'))
        )

    return breadcrumbs

