import json
from django import template
from django.template import loader
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from dossier.models import Dossier

register = template.Library()

fieldstate_css_dict = {
    "attention": {
        "none": "default",
        "question": "warning",
        "exclamation": "warning",
    },
    "knowledge": {
        0: "warning",
        1: "info",
        2: "success",
        3: "success",
    },
    "support": {
        "undefined": "default",
        "strongopposition": "danger",
        "oppose": "warning",
        "neutral": "info",
        "support": "primary",
        "strongsupport": "success",
        "referral": "info",
        "other": "info",
    },
    "proposal": {
        "none": "default",
        "minor": "primary",
        "some": "primary",
        "major": "primary",
    },
}


@register.simple_tag
def fieldstate_css(status_type=None, value=None):
    if status_type is not None and value is not None:
        return fieldstate_css_dict[status_type][value]
    else:
        return json.dumps(fieldstate_css_dict)


@register.simple_tag(takes_context=True)
def display_issue_new(context, issue, size="normal"):
    """
    Displays a label saying "New" if the user has not seen any documents or
    reviews in the issue.
    """

    if not hasattr(issue, "dossier_statistics"):
        return ""

    for stat in issue.dossier_statistics:
        if stat.user_id == context["request"].user.id and stat.issue_is_new():
            return mark_safe(
                '<span class="label label-danger label-smooth">%s</span>' % _("New")
            )

    return ""


@register.simple_tag(takes_context=True)
def display_dossier_statistics(context, issue, size="normal"):

    request = context["request"]

    if not request.user.is_authenticated:
        return ""

    content = []
    if hasattr(issue, "dossier_statistics"):

        if size == "small":
            # template_user = loader.get_template('core/stub/small/issue_dossier_statistic_user.html')
            template_user = None
            template_statistic = loader.get_template(
                "core/stub/small/issue_dossier_statistic.html"
            )
            template_status_type = loader.get_template(
                "core/stub/small/issue_dossier_statistic_status_type.html"
            )
        elif size == "normal":
            template_user = loader.get_template(
                "core/stub/issue_dossier_statistic_user.html"
            )
            template_statistic = loader.get_template(
                "core/stub/issue_dossier_statistic.html"
            )
            template_status_type = loader.get_template(
                "core/stub/issue_dossier_statistic_status_type.html"
            )

        # Determine all the users we need to display dossiers for
        user_count = len(
            set([d.user_id for d in issue.dossier_statistics if d.has_useful_info])
        )

        last_user_id = 0
        for stat in issue.dossier_statistics:

            # We don't display stats for issues that are completely new, i.e.
            # no documents or reviews have been seen by the user yet. The
            # "new" state will be shown by `display_issue_new()`.
            if stat.issue_is_new():
                continue

            # We also don't display stats that do not contain useful info.
            if not stat.has_useful_info:
                continue

            if (
                (user_count > 1 or stat.user_id != request.user.id)
                and last_user_id != stat.user_id
                and template_user
            ):
                content.append(
                    template_user.render({"userprofile": stat.user.userprofile})
                )
                last_user_id = stat.user_id

            for dossier_type, dossier_type_name in Dossier.DOSSIER_TYPES:
                status_type_content = []

                for status_type, status_type_name in Dossier.STATUS_TYPES:
                    fieldstate_content = []
                    total_fieldstate_count = 0

                    fieldstates = "%s_STATES" % status_type.upper()
                    for fieldstate, fieldstate_name in getattr(Dossier, fieldstates):
                        stat_field_name = "%s_%s_%s" % (
                            dossier_type,
                            status_type,
                            fieldstate,
                        )
                        if hasattr(stat, stat_field_name):
                            count = getattr(stat, stat_field_name)
                            if count:
                                fieldstate_content.append(
                                    {
                                        "css_class": fieldstate_css_dict[status_type][
                                            fieldstate
                                        ],
                                        "fieldstate_name": fieldstate_name,
                                        "count": count,
                                    }
                                )

                                total_fieldstate_count += count

                    if fieldstate_content:
                        status_type_content.append(
                            template_status_type.render(
                                {
                                    "status_type": status_type,
                                    "status_type_name": status_type_name,
                                    "fieldstate_content": fieldstate_content,
                                    "total_fieldstate_count": total_fieldstate_count,
                                }
                            )
                        )

                # Determine icon
                if dossier_type == "document":
                    icon = "file"
                elif dossier_type == "review":
                    icon = "inbox"

                # Calculate new documents or reviews
                new_count = 0
                stat_type_count = getattr(stat, "%s_count" % dossier_type)
                issue_type_count = getattr(issue, "%s_count" % dossier_type)
                if issue_type_count != stat_type_count:
                    new_count = issue_type_count - stat_type_count

                if status_type_content or new_count:
                    content.append(
                        template_statistic.render(
                            {
                                "user_id": stat.user_id,
                                "issue_id": issue.id,
                                "icon": icon,
                                "new_count": new_count,
                                "dossier_type": dossier_type,
                                "dossier_type_name": dossier_type_name,
                                "status_type_content": mark_safe(
                                    "".join(status_type_content)
                                ),
                            }
                        )
                    )

    return mark_safe("".join(content))


@register.filter
def fieldstate_applicable(doc_type, fieldstate):
    return Dossier.fieldstate_applicable(doc_type, fieldstate)
