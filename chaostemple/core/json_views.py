from django.contrib.auth.decorators import login_required

from core.models import Dossier
from core.jsonizer import jsonize

@login_required
@jsonize
def attentionstate(request, parliament_num, document_num):

    attentionstate = request.GET.get('attentionstate', None)

    dossier = Dossier.objects.get(document__doc_num=document_num, document__issue__parliament__parliament_num=parliament_num)
    if attentionstate and dossier.attention != attentionstate:
        dossier.attention = attentionstate
        dossier.save()

    ctx = {
        'attentionstate': dossier.attention
    }
    return ctx

