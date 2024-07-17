from django import template

from djalthingi.althingi_settings import ALTHINGI_ISSUE_URL
from djalthingi.althingi_settings import ALTHINGI_PERSON_URL

register = template.Library()


@register.simple_tag
def external_issue_url(parliament_num, issue_num):
    return ALTHINGI_ISSUE_URL % (parliament_num, issue_num)


@register.simple_tag
def external_person_url(person_xml_id):
    return ALTHINGI_PERSON_URL % person_xml_id
