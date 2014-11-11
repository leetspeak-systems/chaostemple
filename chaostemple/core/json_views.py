from django.contrib.auth.decorators import login_required

from core.models import Document
from core.models import Dossier
from core.jsonizer import jsonize

@login_required
@jsonize
def attentionstate(request, dossier_id):

    attentionstate = request.GET.get('attentionstate', None)

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    if attentionstate and dossier.attention != attentionstate:
        dossier.attention = attentionstate
        dossier.save()

    ctx = {
        'attentionstate': dossier.attention
    }
    return ctx

@login_required
@jsonize
def delete_dossier(request, dossier_id):

    Dossier.objects.get(id=dossier_id, user=request.user).delete()

    return {}

