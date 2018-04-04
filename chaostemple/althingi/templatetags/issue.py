from django import template

from althingi.models import Issue

register = template.Library()


# Find the expected order of issue types.
ISSUE_TYPE_ORDER = [t[0] for t in Issue.ISSUE_TYPES]


@register.filter
def issue_types(issues):
    '''
    Extracts the issue types of the given issues and returns them ordered
    according to their order in the model.
    '''
    types = set([(i.issue_type, i.get_issue_type_display()) for i in issues])
    return sorted(types, key=lambda t: ISSUE_TYPE_ORDER.index(t[0]))


@register.filter
def order_by_type_and_current_step(issues):
    '''
    Sorts the given issues according to their type and step (status). First
    they are ordered according to whether they are bill, motions, inquiries
    and such, but within those types they are also ordered according to their
    status, as designated for each type.
    '''

    def checker(i):
        # This is the first sort order key.
        former = ISSUE_TYPE_ORDER.index(i.issue_type)

        # Does this issue type even have defined steps?
        if hasattr(Issue, 'ISSUE_STEPS_%s' % i.issue_type.upper()):
            # If so, we'll figure out how to sort according to those.
            ISSUE_STEP_ORDER = [s[0] for s in getattr(Issue, 'ISSUE_STEPS_%s' % i.issue_type.upper())]
            latter = ISSUE_STEP_ORDER.index(i.current_step)
        else:
            # Order is indeterminate. Let's go with zero. Zero is cool.
            latter = 0

        return former, latter

    return sorted(issues, key=checker)
