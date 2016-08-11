from django import template
from django.template.defaultfilters import date
from django.template.defaultfilters import time

register = template.Library()

# Django 1.9 has no built-in datetime template filter, so we've made our own
@register.filter
def datetime(dt):
    return '%s (%s)' % (date(dt), time(dt))

