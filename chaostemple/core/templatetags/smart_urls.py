from django import template
from django.core.urlresolvers import reverse

register = template.Library()

@register.simple_tag(takes_context=True)
def parliament_url(context, parliament_num):

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
        kwargs = dict(resolver_match.kwargs)
        kwargs['parliament_num'] = parliament_num
        if resolver_match.view_name in parliament_selection_exceptions:
            view_name, vars_to_remove = parliament_selection_exceptions[resolver_match.view_name]
            for var_to_remove in vars_to_remove:
                del kwargs[var_to_remove]
        else:
            view_name = resolver_match.view_name
        return reverse(view_name, kwargs=kwargs)
    else:
        return reverse('parliament', kwargs={'parliament_num': parliament_num})
