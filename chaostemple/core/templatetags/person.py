from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def tenure_ended_prematurely(seat):
    # NOTE: One day given as wiggle-room due to imperfect data.
    return seat.timing_out < seat.parliament.timing_end - timezone.timedelta(days=1)
