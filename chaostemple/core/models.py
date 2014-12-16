from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import FieldTracker

from althingi.models import Document
from althingi.models import Issue
from althingi.models import Person
from althingi.models import Review

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userprofile')

class Dossier(models.Model):
    tracker = FieldTracker(fields=['attention', 'knowledge', 'support'])

    DOSSIER_TYPES = (
        ('document', _('Parliamentary Documents')),
        ('review', _('Reviews')),
    )

    STATUS_TYPES = (
        ('attention', _('Attention')),
        ('knowledge', _('Knowledge')),
        ('support', _('Support')),
    )

    ATTENTION_STATES = (
        ('none', _('None')),
        ('question', _('Question')),
        ('exclamation', _('Exclamation')),
    )

    KNOWLEDGE_STATES = (
        (0, _('Unread')),
        (1, _('Briefly examined')),
        (2, _('Examined')),
        (3, _('Thoroughly examined')),
    )

    SUPPORT_STATES = (
        ('undefined', _('Undefined')),
        ('strongopposition', _('Strong Opposition')),
        ('oppose', _('Oppose')),
        ('neutral', _('Neutral')),
        ('support', _('Support')),
        ('strongsupport', _('Strong Support')),
        ('other', _('Other')),
    )

    issue = models.ForeignKey(Issue, related_name='dossiers')
    dossier_type = models.CharField(max_length=10, choices=DOSSIER_TYPES)

    document = models.ForeignKey(Document, null=True, related_name='dossiers')
    review = models.ForeignKey(Review, null=True, related_name='dossiers')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dossiers')
    attention = models.CharField(max_length=20, default='none', choices=ATTENTION_STATES)
    knowledge = models.IntegerField(default=0, choices=KNOWLEDGE_STATES)
    support = models.CharField(max_length=20, default='undefined', choices=SUPPORT_STATES)

    def update_statistic(self, field, old_value, new_value):
        # Short-hands
        issue_id = self.issue_id
        user_id = self.user_id
        dossier_type = self.dossier_type

        new_stat, c = DossierStatistic.objects.get_or_create(issue_id=issue_id, user_id=user_id)

        if old_value is not None:
            statistic_field = '%s_%s_%s' % (dossier_type, field, old_value)
            if hasattr(new_stat, statistic_field):
                kwargs = {'issue_id': issue_id, 'user_id': user_id, 'dossier_type': dossier_type, field: old_value}
                count = Dossier.objects.filter(**kwargs).count()
                setattr(new_stat, statistic_field, count)
                new_stat.save()

        if new_value is not None:
            statistic_field = '%s_%s_%s' % (dossier_type, field, new_value)
            new_stat, c = DossierStatistic.objects.get_or_create(issue_id=issue_id, user_id=user_id)
            if hasattr(new_stat, statistic_field):
                kwargs = {'issue_id': issue_id, 'user_id': user_id, 'dossier_type': dossier_type, field: new_value}
                count = Dossier.objects.filter(**kwargs).count()
                setattr(new_stat, statistic_field, count)
                new_stat.save()


    def save(self, update_statistics=True, *args, **kwargs):
        if self.document_id:
            self.issue_id = self.document.issue_id
            self.dossier_type = 'document'
        elif self.review_id:
            self.issue_id = self.review.issue_id
            self.dossier_type = 'review'

        super(Dossier, self).save(*args, **kwargs)

        if update_statistics or True:
            for field, old_value in self.tracker.changed().items():
                self.update_statistic(field, old_value, getattr(self, field))


    def delete(self):
        super(Dossier, self).delete()
        for field in self.tracker.fields:
            self.update_statistic(field, getattr(self, field), None)


class DossierStatistic(models.Model):
    issue = models.ForeignKey(Issue, related_name='dossier_statistics')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dossier_statistics')

    document_attention_exclamation = models.IntegerField(default=0)
    document_attention_question = models.IntegerField(default=0)
    document_knowledge_0 = models.IntegerField(default=0)
    document_knowledge_1 = models.IntegerField(default=0)
    document_knowledge_2 = models.IntegerField(default=0)
    document_knowledge_3 = models.IntegerField(default=0)
    document_support_undefined = models.IntegerField(default=0)
    document_support_strongopposition = models.IntegerField(default=0)
    document_support_oppose = models.IntegerField(default=0)
    document_support_neutral = models.IntegerField(default=0)
    document_support_support = models.IntegerField(default=0)
    document_support_strongsupport = models.IntegerField(default=0)
    document_support_other = models.IntegerField(default=0)

    review_attention_exclamation = models.IntegerField(default=0)
    review_attention_question = models.IntegerField(default=0)
    review_knowledge_0 = models.IntegerField(default=0)
    review_knowledge_1 = models.IntegerField(default=0)
    review_knowledge_2 = models.IntegerField(default=0)
    review_knowledge_3 = models.IntegerField(default=0)
    review_support_undefined = models.IntegerField(default=0)
    review_support_strongopposition = models.IntegerField(default=0)
    review_support_oppose = models.IntegerField(default=0)
    review_support_neutral = models.IntegerField(default=0)
    review_support_support = models.IntegerField(default=0)
    review_support_strongsupport = models.IntegerField(default=0)
    review_support_other = models.IntegerField(default=0)

    def get_status_display(self):
        '''
        # Explicit is better than implicit. It may seem tempting to generalize this but keep in
        # mind that more statii will no doubt be added later which may be displayed differently.
        if self.status_type == 'attention':
            return self.get_attention_display()
        elif self.status_type == 'knowledge':
            return self.get_knowledge_display()
        elif self.status_type == 'support':
            return self.get_support_display()
        '''

class Memo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='memos')
    dossier = models.ForeignKey('Dossier', related_name='memos')
    content = models.CharField(max_length=2000)
    order = models.IntegerField()

