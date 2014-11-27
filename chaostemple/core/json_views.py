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
def knowledgestate(request, dossier_id):

    knowledgestate = request.GET.get('knowledgestate', None)
    if knowledgestate:
        knowledgestate = int(knowledgestate)

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    if knowledgestate is not None and dossier.knowledge != knowledgestate:
        dossier.knowledge = knowledgestate
        dossier.save()

    ctx = {
        'knowledgestate': dossier.knowledge
    }
    return ctx

@login_required
@jsonize
def delete_dossier(request, dossier_id):

    dossier = Dossier.objects.get(id=dossier_id, user=request.user)
    document_id = dossier.document_id
    review_id = dossier.review_id

    dossier.delete()

    ctx = {
        'document_id': document_id,
        'review_id': review_id,
    }
    return ctx

