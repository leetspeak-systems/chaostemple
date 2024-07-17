from django import template

register = template.Library()


@register.filter
def tenure_ended_prematurely(seat):
    if not seat:
        return None
    return seat.tenure_ended_prematurely()
