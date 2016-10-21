from django.utils.translation import ugettext as _

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import Committee
from althingi.models import CommitteeAgenda

def leave_breadcrumb(breadcrumbs, view_name, caption):
    return breadcrumbs + ((view_name, caption),)

def make_breadcrumbs(request):
    breadcrumbs = ()

    view_name = request.resolver_match.view_name
    kwargs = request.resolver_match.kwargs

    parliament_num = int(kwargs.get('parliament_num', CURRENT_PARLIAMENT_NUM))
    issue_num = int(kwargs.get('issue_num', 0))
    session_num = int(kwargs.get('session_num', 0))
    committee_id = int(kwargs.get('committee_id', 0))
    agenda_id = int(kwargs.get('agenda_id', 0))

    if parliament_num:
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament', parliament_num),
            '%d. %s' % (parliament_num, _('parliament'))
        )

    if view_name in ('parliament_issues', 'parliament_issue'):
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_issues', parliament_num),
            _('Issues')
        )

    if view_name == 'parliament_issue':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_issue', parliament_num, issue_num),
            '%d. %s' % (issue_num, _('issue'))
        )

    if view_name in ('parliament_sessions', 'parliament_session'):
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_sessions', parliament_num),
            _('Parliamentary Sessions')
        )

    if view_name == 'parliament_session':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_session', parliament_num, session_num),
            '%d. %s' % (session_num, _('parliamentary session'))
        )

    if view_name in ('parliament_committees', 'parliament_committee', 'parliament_committee_agenda'):
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_committees', parliament_num),
            _('Committees')
        )

    if view_name in ('parliament_committee', 'parliament_committee_agenda'):
        committee = Committee.objects.get(id=committee_id)
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_committee', parliament_num, committee_id),
            committee
        )

    if view_name == 'parliament_committee_agenda':
        committee_agenda = CommitteeAgenda.objects.get(id=agenda_id)
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_committee_agenda', parliament_num, committee_id, agenda_id),
            committee_agenda.timing_start_planned
        )

    if view_name == 'parliament_persons':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_persons', parliament_num),
            _('Parliamentarians')
        )

    return breadcrumbs

