from django import template
from django.core.urlresolvers import reverse
from django.template.defaulttags import URLNode

from althingi.althingi_settings import ALTHINGI_ISSUE_URL

register = template.Library()

@register.simple_tag
def issue_link(parliament_num, issue_num):
    return ALTHINGI_ISSUE_URL % (parliament_num, issue_num)


@register.simple_tag(takes_context=True)
def parliament_link(context, parliament_num):

    resolver_match = context['request'].resolver_match

    if 'parliament_num' in resolver_match.kwargs:
        resolver_match.kwargs['parliament_num'] = parliament_num
        return reverse(resolver_match.view_name, kwargs=resolver_match.kwargs)
    else:
        return reverse('parliament', kwargs={'parliament_num': parliament_num})
