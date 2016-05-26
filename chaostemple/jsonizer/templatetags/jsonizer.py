from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def include_jsonizer():
    if not hasattr(settings, 'JSONIZER_DEBUG'):
        raise Exception('Boolean JSONIZER_DEBUG must be set to either True or False')

    content = template.loader.get_template('jsonizer/jsonizer.html')

    ctx = {
        'JSONIZER_DEBUG': settings.JSONIZER_DEBUG,
    }

    return mark_safe(content.render(ctx))
