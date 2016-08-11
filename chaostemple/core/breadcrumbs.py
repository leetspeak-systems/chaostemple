from django.utils.translation import ugettext as _

from althingi.models import Committee
from althingi.models import CommitteeAgenda

def leave_breadcrumb(breadcrumbs, urlname, caption):
    return breadcrumbs + ((urlname, caption),)

def make_breadcrumbs(func_name, parliament_num, issue_num, session_num, committee_id, agenda_id):
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

    if func_name in ('parliament_committees', 'parliament_committee', 'parliament_committee_agenda'):
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_committees', parliament_num),
            _('Committees')
        )

    if func_name in ('parliament_committee', 'parliament_committee_agenda'):
        committee = Committee.objects.get(id=committee_id)
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_committee', parliament_num, committee_id),
            committee
        )

    if func_name == 'parliament_committee_agenda':
        committee_agenda = CommitteeAgenda.objects.get(id=agenda_id)
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_committee_agenda', parliament_num, committee_id, agenda_id),
            committee_agenda.timing_start_planned
        )

    if func_name == 'parliament_persons':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_persons', parliament_num),
            _('Parliamentarians')
        )

    return breadcrumbs

