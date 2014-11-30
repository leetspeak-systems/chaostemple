from django import template
from django.template import Context
from django.template import loader
from django.utils.safestring import mark_safe

from core.models import Dossier

register = template.Library()

attention_css_classes = {
    'none': 'default',
    'question': 'warning',
    'attention': 'warning',
}

knowledge_css_classes = {
    0: 'warning',
    1: 'info',
    2: 'success',
    3: 'success',
}

@register.filter(name='attention')
def attention(dossier):
    t = loader.get_template('core/stub/stub_attention.html')

    ctx = Context({
        'attention': dossier.attention,
        'attention_display': dossier.get_attention_display(),
    })
    return t.render(ctx)

@register.filter(name='attention_css')
def attention_css(attention):
    return attention_css_classes[attention]

@register.simple_tag(name='attention_css_json')
def attention_css_json():
    return attention_css_classes

@register.filter(name='knowledge_css')
def knowledge_css(knowledge):
    return knowledge_css_classes[knowledge]

@register.simple_tag(name='knowledge_css_json')
def knowledge_css_json():
    return knowledge_css_classes

