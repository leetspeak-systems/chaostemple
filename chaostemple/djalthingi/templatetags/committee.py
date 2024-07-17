from django import template
from django.template.defaultfilters import date
from django.template.defaultfilters import time

register = template.Library()


@register.filter
def fancy_committee_agenda_timing(agenda, skipdate=False):
    """Display appropriate timing of committee agenda depending on context and available information"""

    timing = agenda.timing_start_planned

    if timing.time().isoformat() != "00:00:00":
        return timing if not skipdate else time(timing)
    elif agenda.timing_text:
        return (
            "%s (%s)" % (date(timing), agenda.timing_text)
            if not skipdate
            else agenda.timing_text
        )
    else:
        return date(timing) if not skipdate else ""
