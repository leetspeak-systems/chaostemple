from django import template
from django.template import Context
from django.template import loader
from django.utils.safestring import mark_safe

from core.models import Dossier

register = template.Library()

@register.filter(name='attention')
def attention(dossier):
    t = loader.get_template('core/stub/stub_attention.html')

    ctx = Context({
        'attention': dossier.attention,
        'attention_display': dossier.get_attention_display(),
    })
    return t.render(ctx)

