from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from althingi.models import Document
from althingi.models import Person
from althingi.models import Review

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userprofile')

class Dossier(models.Model):
    ATTENTION_STATES = (
        ('n', _('None')),
        ('q', _('Question')),
        ('a', _('Attention')),
    )

    KNOWLEDGE_STATES = (
        (0, _('Unread')),
        (1, _('Briefly examined')),
        (2, _('Examined')),
        (3, _('Thoroughly examined')),
    )

    document = models.ForeignKey(Document, null=True, related_name='dossiers')
    review = models.ForeignKey(Review, null=True, related_name='dossiers')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dossiers')
    attention = models.CharField(max_length=1, default='n', choices=ATTENTION_STATES)
    knowledge = models.IntegerField(default=0, choices=KNOWLEDGE_STATES)

class Memo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='memos')
    dossier = models.ForeignKey('Dossier', related_name='memos')
    content = models.CharField(max_length=2000)
    order = models.IntegerField()

