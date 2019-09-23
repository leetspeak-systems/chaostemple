from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.models import Committee
from althingi.models import CommitteeAgenda
from althingi.templatetags.external_urls import external_issue_url
from althingi.utils import monkey_patch_ical

from django.http import HttpResponse
from django.http import JsonResponse
from django.template.defaultfilters import capfirst
from django.urls import reverse

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
        cal.events.add(event)

    ical_text = monkey_patch_ical(
        cal.__str__(),
        'Fastanefndir Alþingis',
        'Dagatal sem inniheldur boðaða fundi fastanefnda Alþingis ásamt dagskrá í lýsingu.',
        'Reykjavik/Iceland'
    )

    if request.GET.get('plaintext', False):
        content_type = 'text/plain'
    else:
        content_type = 'text/calendar'

    return HttpResponse(ical_text, content_type='%s; charset=utf-8' % content_type)
