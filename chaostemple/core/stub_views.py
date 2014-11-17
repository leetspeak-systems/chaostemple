from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.models import Document
from core.models import Dossier

@login_required
def dossier(request, document_id):

    dossier, created = Dossier.objects.get_or_create(user=request.user, document_id=document_id)

    ctx = {
        'dossier': dossier,
        'attentionstates': Dossier.ATTENTION_STATES,
        'knowledgestates': Dossier.KNOWLEDGE_STATES,
    }

    return render(request, 'core/stub/stub_dossier.html', ctx)

