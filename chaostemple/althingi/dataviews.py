from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.exceptions import AlthingiException
from althingi.models import Committee
from althingi.models import CommitteeAgenda
from althingi.models import Issue
from althingi.templatetags.external_urls import external_issue_url
from althingi.utils import icelandic_am_pm
from althingi.utils import ICELANDIC_MONTHS
from althingi.utils import monkey_patch_ical
from althingi.utils import quote

from django.http import HttpResponse
from django.http import JsonResponse
from django.template.defaultfilters import capfirst
from django.urls import reverse
from django.utils.translation import ugettext as _

from ics import Calendar
from ics import Event

def calendars(request):

    committees = Committee.objects.filter(parliaments__parliament_num=CURRENT_PARLIAMENT_NUM)

    result = []
    for committee in committees:
        result.append({
            'name': capfirst(committee.name),
            'ical': '%s?committee=%s' % (request.build_absolute_uri(reverse('ical')), committee.abbreviation_short),
        })

    return JsonResponse(result, safe=False)


def ical(request):

    # This should be a comma-separated list with values corresponding to
    # Committee's abbreviation_short field.
    abbreviations = request.GET.get('committee', '').split(',') if 'committee' in request.GET else []

    committees = Committee.objects.filter(parliaments__parliament_num=CURRENT_PARLIAMENT_NUM)

    if len(abbreviations) > 0:
        committees = committees.filter(abbreviation_short__in=abbreviations)

    cal = Calendar()
    cal.creator = '-//Alþingi//NONSGML Fastanefndir Alþingis//IS'
    cal.scale = 'GREGORIAN'
    cal.method = 'PUBLISH'

    agendas = CommitteeAgenda.objects.select_related(
        'committee'
    ).prefetch_related(
        'committee_agenda_items'
    ).filter(
        parliament__parliament_num=CURRENT_PARLIAMENT_NUM,
        committee__in=committees
    ).order_by(
        'timing_start_planned'
    )

    for agenda in agendas:
        # Short-hand.
        agenda_id = agenda.committee_agenda_xml_id

        description = 'Dagskrá:\n\n'
        for item in agenda.committee_agenda_items.select_related('issue__parliament'):
            description += '%d. %s\n' % (item.order, capfirst(item.name))
            # Add URL of issue, if any.
            if item.issue is not None:
                description += '%s\n' % external_issue_url(
                    item.issue.parliament.parliament_num,
                    item.issue.issue_num
                )
            description += '\n'

        event = Event()
        event.uid = 'committee-agenda-%d@althingi.net' % agenda_id
        event.name = capfirst(agenda.committee.name)
        event.description = description
        event.begin = agenda.timing_start_planned
        event.end = agenda.timing_end
        event.url = 'https://www.althingi.is/thingnefndir/dagskra-nefndarfunda/?nfaerslunr=%d' % agenda_id

        # Committee agendas are never planned at midnight (or damn well
        # hopefully not). So when a committee agenda is planned without a time
        # factor, or in other words, is timed at midnight, we'll assume that
        # the timing is actually not precisely determined and turn it into an
        # all-day event instead, using the timing text (determined below) to
        # elaborate instead.
        if event.begin.hour == 0 and event.begin.minute == 0 and event.begin.second == 0:
            event.make_all_day()

        if agenda.timing_text:
            # If agenda.timing_text is just a representation of what is
            # already known from the planned starting time, we'll want to
            # nullify it so that we don't clutter the name with it
            # unnecessarily. To do this, we have to re-construct the text that
            # is typically provided and compare it against agenda.timing_text.
            # If they match, we won't include it. If they don't match, then
            # what's provided in agenda.timing_text is presumably more
            # meaningful than simply a (badly) reformatted version of
            # agenda.timing_start_planned.

            timing = agenda.timing_start_planned

            day = timing.day
            month_name = ICELANDIC_MONTHS[timing.month]
            year = str(timing.year)[2:]
            time = timing.strftime('%-I:%M')
            am_pm = icelandic_am_pm(timing)

            # Known inconsistencies are whether there is a space in the
            # beginning, and whether there is one space or two between "kl."
            # and the time-of-day. We strip and replace to compensate.
            timing_text_test = '%d. %s %s, kl. %s %s' % (day, month_name, year, time, am_pm)
            if agenda.timing_text.strip().replace('  ', ' ') != timing_text_test:
                event.name += ' (%s)' % agenda.timing_text.strip()

        cal.events.add(event)

    ical_text = monkey_patch_ical(
        cal.__str__(),
        'Fastanefndir Alþingis',
        'Dagatal sem inniheldur boðaða fundi fastanefnda Alþingis ásamt dagskrá í lýsingu.',
        'Reykjavik/Iceland',
        'PT10M'
    )

    if request.GET.get('plaintext', False):
        content_type = 'text/plain'
    else:
        content_type = 'text/calendar'

    return HttpResponse(ical_text, content_type='%s; charset=utf-8' % content_type)


def csv_parliament_issues(request, parliament_num):

    # Check if a specific set of issues was requested. Otherwise we'll return
    # everything in the given parliament.
    if 'issue_nums' in request.GET:
        try:
            issue_nums = request.GET.get('issue_nums').split(',')

            # If an empty string is given, we'll want no results.
            if issue_nums == ['']:
                issue_nums = [0]
            else:
                # Make sure that this is nothing but a list of integers.
                [int(issue_num) for issue_num in issue_nums]

        except:
            raise AlthingiException('URL parameter "issue_nums" should be a comma-seperated list of integers')
    else:
        issue_nums = None

    # Standard SQL not only used for a massive performance boost but actually
    # also for clarity. The ORM way turned out to be way more convoluted and
    # involved a lot of advanced ORM features.
    issues = Issue.objects.raw(
        '''
        SELECT DISTINCT
            i.id,
            i.issue_num,
            i.issue_type,
            i.name,
            i.description,
            i.current_step,
            i.fate,
            prop_pers.name AS proposer_person,
            prop_com.name AS proposer_committee,
            i.proposer_type,
            mini.name AS minister,
            i.time_published,
            party.name AS party,
            com.name AS committee,
            rap_pers.name AS rapporteur,
            COUNT(cai.id) AS committee_meeting_count
        FROM
            -- Basic info
            althingi_issue AS i
            INNER JOIN althingi_parliament AS par ON par.id = i.parliament_id

            -- Proposers
            INNER JOIN althingi_proposer AS prop ON (
                prop.issue_id = i.id
                AND (
                    prop.order = 1
                    OR prop.order IS NULL
                )
            )
            LEFT OUTER JOIN althingi_person AS prop_pers ON (
                prop_pers.id = prop.person_id
            )
            LEFT OUTER JOIN althingi_committee AS prop_com ON (
                prop_com.id = prop.committee_id
            )

            -- Timing of person's seat, party etc.
            LEFT OUTER JOIN althingi_seat AS seat ON (
                seat.person_id = prop_pers.id
                AND (
                    seat.timing_out >= i.time_published
                    OR seat.timing_out IS NULL
                )
                AND seat.timing_in <= i.time_published
            )
            LEFT OUTER JOIN althingi_ministerseat AS mseat ON (
                mseat.person_id = prop_pers.id
                AND (
                    mseat.timing_out >= i.time_published
                    OR mseat.timing_out IS NULL
                )
                AND mseat.timing_in <= i.time_published
            )
			LEFT OUTER JOIN althingi_minister AS mini ON (
				mini.id = mseat.minister_id
            )
            LEFT OUTER JOIN althingi_party AS party ON (
                party.id = seat.party_id
                OR party.id = mseat.party_id
            )

            -- Committee
            LEFT OUTER JOIN althingi_committee AS com ON com.id = i.to_committee_id
            LEFT OUTER JOIN althingi_rapporteur AS rap ON rap.issue_id = i.id
            LEFT OUTER JOIN althingi_person AS rap_pers ON rap_pers.id = rap.person_id
            LEFT OUTER JOIN althingi_committeeagendaitem AS cai ON cai.issue_id = i.id
        WHERE
            par.parliament_num = %s
            AND i.issue_group = 'A'
            AND (
                -- The parameter will be 1 if all issues are requested.
                1 = %s
                -- Otherwise, the issue num will have to be in the given list.
                OR i.issue_num IN %s
            )
        GROUP BY
            id,
            issue_num,
            issue_type,
            name,
            description,
            current_step,
            fate,
            proposer_person,
            proposer_committee,
            proposer_type,
            time_published,
            party,
            committee,
            rapporteur
        ORDER BY
            i.issue_num
        ''',
        [
            parliament_num,

            # Give 1 if we want all issues, otherwise 0.
            1 if issue_nums is None else 0,

            # Give requested issue numbers if any are requested, otherwise
            # look for something that we know doesn't exist.
            issue_nums if issue_nums is not None else [-1]
        ]
    )

    first_line = [
        _('Nr'),
        _('Name'),
        _('Issue type'),
        _('Status'),
        _('Fate'),
        '%s (%s)' % (_('Proposer'), _('person')),
        '%s (%s)' % (_('Proposer'), _('committee')),
        _('Published'),
        _('Issue origin'),
        _('Minister'),

        _('Party'),
        _('Committee'),
        _('Rapporteur'),
        _('Committee meetings'),
    ]

    lines = ['# "%s"' % '","'.join(first_line)]
    for issue in issues:

        # Prepare basic info.
        issue_num = str(issue.issue_num)
        if len(issue.description):
            name = quote('%s (%s)' % (capfirst(issue.name), issue.description))
        else:
            name = quote(capfirst(issue.name))
        issue_type = quote(capfirst(issue.get_issue_type_display()))
        status = quote(issue.get_current_step_display())
        fate = quote(capfirst(issue.get_fate_display()))
        proposer_person = quote(issue.proposer_person)
        proposer_committee = quote(issue.proposer_committee)
        published = quote(issue.time_published.strftime('%Y-%m-%d'))
        proposer_type = quote(issue.get_proposer_type_display())
        minister = quote(capfirst(issue.minister))
        party = quote(capfirst(issue.party))
        committee = quote(capfirst(issue.committee))
        rapporteur = quote(capfirst(issue.rapporteur))
        committee_meeting_count = str(issue.committee_meeting_count)

        # Construct line for issue.
        line = [
            issue_num,
            name,
            issue_type,
            status,
            fate,
            proposer_person,
            proposer_committee,
            published,
            proposer_type,
            minister,
            party,
            committee,
            rapporteur,
            committee_meeting_count,
        ]
        lines.append(','.join(line))

    return HttpResponse('\n'.join(lines) + '\n', content_type='text/csv')
