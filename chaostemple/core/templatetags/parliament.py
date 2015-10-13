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

    # Normally, when a different Parliament is selected, the corresponding page should be loaded with
    # respect to the page currently being viewed. However, when the user is viewing a page where it
    # does not make sense to only change the Parliament number (for example when they are viewing a
    # particular issue or a particular agenda within a Parliament), the corresponding list of items
    # should be viewed instead. This variable defines how to redirect in these special cases.
    # The key is the view that the user is viewing. Its value is a tuple which is built so:
    # (new_view_name, (variable_to_remove, another_variable_to_remove...)),
    parliament_selection_exceptions = {
        'parliament_issue': ('parliament_issues', ('issue_num',)),
        'parliament_session': ('parliament_sessions', ('session_num',)),
        'parliament_committee': ('parliament_committees', ('committee_id',)),
        'parliament_committee_agenda': ('parliament_committees', ('agenda_id', 'committee_id')),
    }

    resolver_match = context['request'].resolver_match

    if 'parliament_num' in resolver_match.kwargs:
        resolver_match.kwargs['parliament_num'] = parliament_num
        if resolver_match.view_name in parliament_selection_exceptions:
            view_name, vars_to_remove = parliament_selection_exceptions[resolver_match.view_name]
            kwargs = dict(resolver_match.kwargs)
            for var_to_remove in vars_to_remove:
                del kwargs[var_to_remove]
        else:
            view_name = resolver_match.view_name
            kwargs = resolver_match.kwargs
        return reverse(view_name, kwargs=kwargs)
    else:
        return reverse('parliament', kwargs={'parliament_num': parliament_num})
