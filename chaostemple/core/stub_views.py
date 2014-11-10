from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from core.models import Document
from core.models import Dossier

@login_required
def dossier(request, document_id):

    dossier, created = Dossier.objects.get_or_create(user=request.user, document_id=document_id)
    attentionstates = Dossier.ATTENTION_STATES

    ctx = {
        'dossier': dossier,
        'attentionstates': attentionstates
    }

    return render(request, 'core/stub/stub_dossier.html', ctx)

