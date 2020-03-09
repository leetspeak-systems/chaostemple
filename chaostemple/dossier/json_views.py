from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.template.loader import render_to_string
from dossier.models import Dossier
from dossier.models import Memo
from dossier.templatetags.dossier_tags import supports_dossier
from jsonizer.utils import jsonize

@login_required
@jsonize
def dossier_deck(request, parliament_num, doc_num=None, log_num=None):
    dossiers = Dossier.objects.by_user(request.user)

    if log_num is not None:
        dossiers = dossiers.filter(review__issue__parliament__parliament_num=parliament_num, review__log_num=log_num)
    elif doc_num is not None:
        dossiers = dossiers.filter(document__issue__parliament__parliament_num=parliament_num, document__doc_num=doc_num)

    total_html = ''
    for dossier in dossiers:
        total_html += '<div class="panel-footer" data-dossier-id="%d">' % dossier.id
        stub_ctx = {
            'request': request,
            'dossier': dossier,
            'attentionstates': Dossier.ATTENTION_STATES,
            'knowledgestates': Dossier.KNOWLEDGE_STATES,
            'supportstates': Dossier.SUPPORT_STATES,
            'proposalstates': Dossier.PROPOSAL_STATES,
            'max_memo_length': Memo._meta.get_field('content').max_length,
        }
        total_html += render_to_string('core/stub/dossier.html', stub_ctx)
        total_html += '</div>'

    return { 'html': total_html }
