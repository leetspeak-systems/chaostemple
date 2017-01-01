from django import template

register = template.Library()

@register.filter
def tenure_ended_prematurely(seat):
    return seat.tenure_ended_prematurely()
