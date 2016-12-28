from django import template
from django.core.urlresolvers import reverse

from core.breadcrumbs import append_to_crumb_string

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


@register.simple_tag(takes_context=True)
def breadcrumb_url(context, view_name, *args):
    '''
    This template tag works like the default 'url' template tag, except that it adds the
    currently visible page to the crumb string in the URL, so that breadcrumbs work.
    '''

    crumb_string = append_to_crumb_string(
        context.request.get_full_path().split('?')[0],
        context.request.GET.get('from', '')
    )

    return '%s?from=%s' % (reverse(view_name, args=args), crumb_string)


@register.filter()
def breadcrumb_trace_url(breadcrumb):
    view = breadcrumb['view']
    path = reverse(view[0], args=view[1:])
    if len(breadcrumb['crumb_string']):
        path = path + '?from=' + breadcrumb['crumb_string']

    return path


@register.filter()
def breadcrumb_caption(breadcrumb):
    return breadcrumb['caption']
