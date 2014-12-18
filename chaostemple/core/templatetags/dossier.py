from django import template
from django.template import Context
from django.template import loader
from django.utils.safestring import mark_safe

from core.models import Dossier

register = template.Library()

css_classes = {
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
    }
}

@register.simple_tag
def dossier_css(status_type, *args):
    if len(args) == 0:
        return css_classes[status_type]
    elif len(args) == 1:
        value = args[0]
        return css_classes[status_type][value]

# TODO: Needs clean-up... especially clearer file- and variable names
@register.simple_tag
def display_dossier_statistic(dossier_statistic):

    template_statistic = loader.get_template('core/stub/issue_dossier_statistic.html')
    template_field_state_content = loader.get_template('core/stub/issue_dossier_statistic_field_state_content.html')
    template_dossier_type_content = loader.get_template('core/stub/issue_dossier_statistic_dossier_type_content.html')

    result = []
    stat = dossier_statistic
    for dossier_type, dossier_type_name in Dossier.DOSSIER_TYPES:
        dossier_type_content = []

        for status_type, status_type_name in Dossier.STATUS_TYPES:
            field_state_content = []

            field_states = '%s_STATES' % status_type.upper()
            for field_state, field_state_name in getattr(Dossier, field_states):
                css_classes = dossier_css(status_type)

                stat_field_name = '%s_%s_%s' % (dossier_type, status_type, field_state)
                if hasattr(stat, stat_field_name):
                    value = getattr(stat, stat_field_name)
                    if value:
                        field_state_content.append(template_field_state_content.render(Context({
                            'css_class': css_classes[field_state],
                            'field_state_name': field_state_name,
                            'value': value
                        })))

            if field_state_content:
                dossier_type_content.append(template_dossier_type_content.render(Context({
                    'status_type_name': status_type_name,
                    'field_state_content': mark_safe(''.join(field_state_content))
                })))

        if dossier_type_content:
            if dossier_type == 'document':
                icon = 'file'
            elif dossier_type == 'review':
                icon = 'inbox'

            result.append(template_statistic.render(Context({
                'icon': icon,
                'dossier_type_name': dossier_type_name,
                'dossier_type_content': mark_safe(''.join(dossier_type_content))
            })))

    return ''.join(result)

