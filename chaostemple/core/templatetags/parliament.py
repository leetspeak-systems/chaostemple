from django import template

from althingi.althingi_settings import ALTHINGI_ISSUE_URL

register = template.Library()

@register.simple_tag
def issue_link(parliament_num, issue_num):
    return ALTHINGI_ISSUE_URL % (parliament_num, issue_num)
