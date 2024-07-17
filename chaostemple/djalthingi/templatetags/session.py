from django import template
from django.template.defaultfilters import capfirst
from django.template.defaultfilters import date
from django.template.defaultfilters import time

register = template.Library()


@register.filter
def fancy_session_timing(session, skipdate=False):
    """Display appropriate timing of session depending on context and available information"""

    timing = session.timing_start_planned

    if timing:
        return timing if not skipdate else time(timing)
    elif session.timing_text:
        return capfirst(session.timing_text)
    else:
        return ""
