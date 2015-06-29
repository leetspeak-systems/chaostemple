from django.db.models.signals import pre_delete
from django.dispatch import receiver

from althingi.models import Document
from althingi.models import Review
from core.models import Dossier

@receiver(pre_delete, sender=Review)
@receiver(pre_delete, sender=Document)
def delete_dossiers_on_deletion(sender, instance, **kwargs):
    if sender is Document:
        dossier_kwargs = { 'document_id': instance.id }
    elif sender is Review:
        dossier_kwargs = { 'review_id': instance.id }
    else:
        return # Shouldn't happen, but better safe than sorry.

    dossiers = Dossier.objects.filter(**dossier_kwargs)
    for dossier in dossiers:
        dossier.delete()

