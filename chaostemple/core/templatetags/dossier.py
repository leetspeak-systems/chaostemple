from django import template
from django.template import Context
from django.template import loader
from django.utils.safestring import mark_safe

from core.models import Dossier

register = template.Library()

fieldstate_css_dict = {
    'attention': {
        'none': 'default',
        'question': 'warning',
        'exclamation': 'warning',
    },
    'knowledge': {
        0: 'warning',
        1: 'info',
        2: 'success',
        3: 'success',
    },
    'support': {
        'undefined': 'default',
        'strongopposition': 'danger',
        'oppose': 'warning',
        'neutral': 'info',
        'support': 'primary',
        'strongsupport': 'success',
        'other': 'info',
    },
    'proposal': {
        'none': 'default',
        'minor': 'primary',
        'some': 'primary',
        'major': 'primary',
    },
}

@register.simple_tag
def fieldstate_css(status_type=None, value=None):
    if status_type is not None and value is not None:
        return fieldstate_css_dict[status_type][value]
    else:
        return fieldstate_css_dict

@register.simple_tag(takes_context=True)
def display_dossier_statistics(context, issue):

    request = context['request']

    if not request.user.is_authenticated():
        return ''

    content = []
    if hasattr(issue, 'dossier_statistics'):

        template_user = loader.get_template('core/stub/issue_dossier_statistic_user.html') # I was here. Just added this.
        template_statistic = loader.get_template('core/stub/issue_dossier_statistic.html')
        template_status_type = loader.get_template('core/stub/issue_dossier_statistic_status_type.html')
        template_fieldstate = loader.get_template('core/stub/issue_dossier_statistic_fieldstate.html')

        fieldstate_css_dict = fieldstate_css()

        # Determine all the users we need to display dossiers for
        user_count = len(set([d.user_id for d in issue.dossier_statistics]))

        last_user_id = 0
        for stat in issue.dossier_statistics:
            for dossier_type, dossier_type_name in Dossier.DOSSIER_TYPES:
                status_type_content = []

                if (user_count > 1 or stat.user_id != request.user.id) and last_user_id != stat.user_id:
                    content.append(template_user.render(Context({
                        'statistic_user': stat.user
                    })))
                    last_user_id = stat.user_id

                for status_type, status_type_name in Dossier.STATUS_TYPES:
                    fieldstate_content = []

                    fieldstates = '%s_STATES' % status_type.upper()
                    for fieldstate, fieldstate_name in getattr(Dossier, fieldstates):
                        stat_field_name = '%s_%s_%s' % (dossier_type, status_type, fieldstate)
                        if hasattr(stat, stat_field_name):
                            count = getattr(stat, stat_field_name)
                            if count:
                                fieldstate_content.append(template_fieldstate.render(Context({
                                    'css_class': fieldstate_css_dict[status_type][fieldstate],
                                    'fieldstate_name': fieldstate_name,
                                    'count': count
                                })))

                    if fieldstate_content:
                        status_type_content.append(template_status_type.render(Context({
                            'status_type_name': status_type_name,
                            'fieldstate_content': mark_safe(''.join(fieldstate_content))
                        })))

                # Determine icon
                if dossier_type == 'document':
                    icon = 'file'
                elif dossier_type == 'review':
                    icon = 'inbox'

                # Determine memo count
                memo_count = getattr(stat, '%s_memo_count' % dossier_type)

                # Calculate new documents or reviews
                new_count = 0
                stat_type_count = getattr(stat, '%s_count' % dossier_type)
                issue_type_count = getattr(issue, '%s_count' % dossier_type)
                if issue_type_count != stat_type_count:
                    new_count = issue_type_count - stat_type_count

                if status_type_content or new_count:
                    content.append(template_statistic.render(Context({
                        'icon': icon,
                        'memo_count': memo_count,
                        'new_count': new_count,
                        'dossier_type': dossier_type,
                        'dossier_type_name': dossier_type_name,
                        'status_type_content': mark_safe(''.join(status_type_content))
                    })))

    return ''.join(content)

@register.filter
def fieldstate_applicable(doc_type, fieldstate):
    return Dossier.fieldstate_applicable(doc_type, fieldstate)

