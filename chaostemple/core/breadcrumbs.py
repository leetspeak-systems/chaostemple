from django.core.urlresolvers import resolve
from django.core.urlresolvers import reverse
from django.template.defaultfilters import date
from django.utils import dateparse
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import ugettext as _

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import Committee
from althingi.models import CommitteeAgenda
from althingi.models import Party
from althingi.models import Person

from core.templatetags.committee import fancy_committee_agenda_timing


# Utility function to add an URL to the crumbs in a crumb string.
def append_to_crumb_string(input_path, input_crumb_string):
    crumb_string = urlsafe_base64_encode(input_path)
    if input_crumb_string:
        crumb_string = crumb_string + ',' + input_crumb_string

    return crumb_string


def generate_prepended_views(crumb_string):
    if not crumb_string:
        return []

    prepended_views = []

    for part in reversed(crumb_string.split(',')):
        path = urlsafe_base64_decode(part)
        resolved_path = resolve(path)
        prepended_views.append(resolved_path)

    return prepended_views


def leave_breadcrumb(breadcrumbs, view, caption):

    prior_crumb_strings = []
    for breadcrumb in breadcrumbs:
        view_data = breadcrumb['view']
        path = reverse(view_data[0], args=view_data[1:])
        crumb_string = urlsafe_base64_encode(path)
        prior_crumb_strings.append(crumb_string)

    breadcrumbs.append({
        'view': view,
        'caption': caption,
        'crumb_string': ','.join(reversed(prior_crumb_strings))
    })
    return breadcrumbs


def make_breadcrumbs(request):
    breadcrumbs = []

    parliament_num = int(request.resolver_match.kwargs.get('parliament_num', CURRENT_PARLIAMENT_NUM))

    # parliament_num should always exist.
    breadcrumbs = leave_breadcrumb(
        breadcrumbs,
        ('parliament', parliament_num),
        '%d. %s' % (parliament_num, _('parliament'))
    )

    prepended_views = generate_prepended_views(request.GET.get('from', ''))
    for prepended_view in prepended_views:
        breadcrumbs = process_breadcrumbs(breadcrumbs, prepended_view)

    breadcrumbs = process_breadcrumbs(breadcrumbs, request.resolver_match)

    return breadcrumbs


def process_breadcrumbs(breadcrumbs, view):

    # Short-hands.
    view_name = view.view_name
    view_kwargs = view.kwargs

    # Iterate through URLconf parameters and set the appropriate variables appropriately.
    # This is to lessen repetition and uniformly address default values, type conversions and such.
    for kwarg in view_kwargs:
        if kwarg == 'parliament_num':
            parliament_num = int(view_kwargs.get('parliament_num', CURRENT_PARLIAMENT_NUM))
        elif kwarg == 'input_date':
            input_date = view_kwargs.get('input_date')
        elif kwarg == 'issue_num':
            issue_num = int(view_kwargs.get('issue_num', 0))
        elif kwarg == 'session_num':
            session_num = int(view_kwargs.get('session_num', 0))
        elif kwarg == 'committee_id':
            committee_id = int(view_kwargs.get('committee_id', 0))
        elif kwarg == 'agenda_id':
            agenda_id = int(view_kwargs.get('agenda_id', 0))
        elif kwarg == 'slug':
            slug = view_kwargs.get('slug')
        elif kwarg == 'subslug':
            subslug = view_kwargs.get('subslug')

    if view_name == 'day':
        if 'input_date' in locals():
            requested_date = timezone.make_aware(dateparse.parse_datetime('%s 00:00:00' % input_date))
            caption = '%s (%s)' % (_('Today\'s issues'), date(requested_date, 'SHORT_DATE_FORMAT'))
        else:
            input_date = None
            caption = _('Today\'s issues')

        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('day', input_date),
            caption
        )

    if view_name == 'user_issues_bookmarked':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('user_issues_bookmarked', parliament_num),
            _('Bookmarks')
        )

    if view_name == 'user_issues_open':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('user_issues_open', parliament_num),
            _('Opened Issues')
        )

    if view_name == 'user_issues_incoming':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('user_issues_incoming',),
            _('Issues with new data')
        )

    if view_name == 'parliament_issues':
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

    if view_name == 'parliament_sessions':
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

    if view_name == 'parliament_committees':
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
            fancy_committee_agenda_timing(committee_agenda)
        )

    if view_name == 'parliament_parties':
        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_parties', parliament_num),
            _('Parliamentary Parties')
        )

    if view_name == 'parliament_persons':
        if view_kwargs.has_key('party_slug'):
            party = Party.objects.get(slug=view_kwargs.get('party_slug'))
        else:
            party = None

        breadcrumbs = leave_breadcrumb(
            breadcrumbs,
            ('parliament_persons', parliament_num, party.slug) if party else ('parliament_persons', parliament_num),
            party if party else _('Parliamentarians')
        )

    if view_name == 'person':
        if 'subslug' in locals():
            person = Person.objects.get(slug=slug, subslug=subslug)
            person_count = 1
        else:
            persons = Person.objects.filter(slug=slug)
            person_count = persons.count()
            person = persons[0] # We'll only use the name so just need either one of them, doesn't matter which.

        if person_count == 1:
            breadcrumbs = leave_breadcrumb(
                breadcrumbs,
                ('person', person.slug, person.subslug),
                '%s (%s %s)' % (person.name, _('b.'), date(person.birthdate, 'SHORT_DATE_FORMAT'))
            )
        else:
            breadcrumbs = leave_breadcrumb(
                breadcrumbs,
                ('person', person.slug),
                person.name
            )

    return breadcrumbs

