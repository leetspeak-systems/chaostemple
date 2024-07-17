from django import template

from djalthingi.models import Issue

from django.template.defaultfilters import date
from django.utils import timezone
from django.utils.translation import gettext as _

from time import mktime

register = template.Library()


# Find the expected order of issue types.
ISSUE_TYPE_ORDER = [t[0] for t in Issue.ISSUE_TYPES]
PROPOSER_TYPE_ORDER = [t[0] for t in Issue.PROPOSER_TYPES]


@register.filter
def issue_types(issues):
    """
    Extracts the issue types of the given issues and returns them ordered
    according to their order in the model.
    """
    types = set([(i.issue_type, i.get_issue_type_display()) for i in issues])
    return sorted(types, key=lambda t: ISSUE_TYPE_ORDER.index(t[0]))


@register.filter
def proposer_types(issues):
    """
    Extracts the proposer types of the given issues and returns them ordered
    according to their order in the model.
    """
    types = set([(i.proposer_type, i.get_proposer_type_display()) for i in issues])
    return sorted(types, key=lambda t: PROPOSER_TYPE_ORDER.index(t[0]))


@register.filter
def order_by_progression(issues):
    """
    Sorts the given issues according to their type and step (status). First
    they are ordered according to whether they are bill, motions, inquiries
    and such, but within those types they are also ordered according to their
    status, as designated for each type.
    """

    def checker(i):
        # Can we determine this issue's progression by its current step?
        if i.current_step in Issue.ISSUE_STEP_ORDER:
            # If so, we'll do that.
            primary = Issue.ISSUE_STEP_ORDER[i.current_step]
        else:
            # Order is indeterminate. Let's go with zero. Zero is cool.
            primary = 0

        if i.review_deadline:
            unix_time = mktime(i.review_deadline.timetuple())
            secondary = 0 - unix_time
        else:
            secondary = 0

        # Lower issue numbers means published earlier, meaning they should be
        # ahead in the progression (all things considered).
        tertiary = 0 - i.issue_num

        return primary, secondary, tertiary

    return sorted(issues, key=checker)


@register.filter
def review_deadline(issue, short=False):

    review_deadline_steps = [
        "committee-1-reviews-requested",
        "committee-1-reviews-arrived",
        "committee-former-reviews-requested",
        "committee-former-reviews-arrived",
    ]

    if issue.current_step in review_deadline_steps:

        if short:
            return date(issue.review_deadline, "SHORT_DATE_FORMAT")
        else:
            today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            days = (today - issue.review_deadline).days

            if days == 0:
                day_msg = _("today")
            elif days > 0:
                day_msg = _("yesterday") if days == 1 else _("%d days ago") % days
            else:
                days = 0 - days  # Minus-days are in the future.
                day_msg = _("tomorrow") if days == 1 else _("in %d days") % days

            return "%s (%s)" % (date(issue.review_deadline), day_msg)
    else:
        return ""


@register.filter
def committee(issue):

    committee_steps = [
        "committee-1-waiting",
        "committee-1-current",
        "committee-1-reviews-requested",
        "committee-1-reviews-arrived",
        "committee-1-finished",
        "committee-2-waiting",
        "committee-2-current",
        "committee-2-finished",
        "committee-former-waiting",
        "committee-former-current",
        "committee-former-reviews-requested",
        "committee-former-reviews-arrived",
        "committee-former-finished",
    ]

    if issue.current_step in committee_steps:
        return issue.to_committee


@register.filter
def is_interesting(issue_type):
    return issue_type in Issue.MOST_INTERESTING_ISSUE_TYPES
