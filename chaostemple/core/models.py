from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import FieldTracker

from althingi.models import Document
from althingi.models import Issue
from althingi.models import Person
from althingi.models import Review

class DossierStatisticManager(models.Manager):

    def generate_statistics(self, issue_id, user_id):

        result = {}
        dossiers = Dossier.objects.filter(issue_id=issue_id, user_id=user_id)
        for dossier in dossiers:
            dossier_type = dossier.dossier_type # Short-hand

            if not dossier_type in result:
                result[dossier_type] = {}

            for field in Dossier.tracker.fields:
                value = getattr(dossier, field)

                if not field in result[dossier_type]:
                    result[dossier_type][field] = {}

                if not value in result[dossier_type][field]:
                    result[dossier_type][field][getattr(dossier, field)] = 0

                result[dossier_type][field][value] = result[dossier_type][field][value] + 1

        DossierStatistic.objects.filter(issue_id=issue_id, user_id=user_id).delete()
        for dossier_type in result:
            for field in Dossier.tracker.fields:
                for value in result[dossier_type][field]:
                    kwargs = {
                        'issue_id': issue_id,
                        'user_id': user_id,
                        'dossier_type': dossier_type,
                        field: value
                    }
                    stat = DossierStatistic(**kwargs)
                    stat.count = result[dossier_type][field][value]
                    stat.save()


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userprofile')

class Dossier(models.Model):
    tracker = FieldTracker(fields=['attention', 'knowledge'])

    DOSSIER_TYPES = (
        ('document', _('Document')),
        ('review', _('Review')),
    )

    STATUS_TYPES = (
        ('attention', _('Attention')),
        ('knowledge', _('Knowledge')),
    )

    ATTENTION_STATES = (
        ('none', _('None')),
        ('question', _('Question')),
        ('attention', _('Attention')),
    )

    KNOWLEDGE_STATES = (
        (0, _('Unread')),
        (1, _('Briefly examined')),
        (2, _('Examined')),
        (3, _('Thoroughly examined')),
    )

    issue = models.ForeignKey(Issue, related_name='dossiers')
    dossier_type = models.CharField(max_length=10, choices=DOSSIER_TYPES)

    document = models.ForeignKey(Document, null=True, related_name='dossiers')
    review = models.ForeignKey(Review, null=True, related_name='dossiers')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dossiers')
    attention = models.CharField(max_length=10, default='none', choices=ATTENTION_STATES)
    knowledge = models.IntegerField(default=0, choices=KNOWLEDGE_STATES)

    def update_statistic(self, field, old_value, new_value):
        # Short-hands
        issue_id = self.issue_id
        user_id = self.user_id
        dossier_type = self.dossier_type

        if old_value is not None:
            kwargs = {'issue_id': issue_id, 'user_id': user_id, 'dossier_type': dossier_type, field: old_value}
            old_stat = DossierStatistic.objects.get(**kwargs)

            if old_stat.count == 1:
                old_stat.delete()
            else:
                # count() is used instead of -1 for self-healing if stats go bad
                old_stat.count = Dossier.objects.filter(**kwargs).count()
                old_stat.save()

        if new_value is not None:
            kwargs = {'issue_id': issue_id, 'user_id': user_id, 'dossier_type': dossier_type, field: new_value}
            new_stat, c = DossierStatistic.objects.get_or_create(**kwargs)

            # count() is used instead of +1 for self-healing if stats go bad
            new_stat.count = Dossier.objects.filter(**kwargs).count()
            new_stat.save()


    def save(self, update_statistics=True, *args, **kwargs):
        if self.document_id:
            self.issue_id = self.document.issue_id
            self.dossier_type = 'document'
        elif self.review_id:
            self.issue_id = self.review.issue_id
            self.dossier_type = 'review'

        super(Dossier, self).save(*args, **kwargs)

        if update_statistics:
            for field, old_value in self.tracker.changed().items():
                self.update_statistic(field, old_value, getattr(self, field))


    def delete(self):
        super(Dossier, self).delete()
        for field in self.tracker.fields:
            self.update_statistic(field, getattr(self, field), None)


class DossierStatistic(models.Model):
    objects = DossierStatisticManager()

    issue = models.ForeignKey(Issue, related_name='dossier_statistics')
    dossier_type = models.CharField(max_length=10, choices=Dossier.DOSSIER_TYPES)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dossier_statistics')

    status_type = models.CharField(max_length=10, choices=Dossier.STATUS_TYPES)

    attention = models.CharField(max_length=10, null=True, choices=Dossier.ATTENTION_STATES)
    knowledge = models.IntegerField(null=True, choices=Dossier.KNOWLEDGE_STATES)

    count = models.IntegerField(default=0)

    def __unicode__(self):
        return "[ dossier_type: '%s', 'attention': %s, 'knowledge': %s, 'count': %d ]" % (self.dossier_type, self.attention, self.knowledge, self.count)

    def get_status_display(self):
        # Explicit is better than implicit. It may seem tempting to generalize this but keep in
        # mind that more statii will no doubt be added later which may be displayed differently.
        if self.status_type == 'attention':
            return self.get_attention_display()
        elif self.status_type == 'knowledge':
            return self.get_knowledge_display()

    def save(self, *args, **kwargs):
        for status_type, status_type_label in Dossier.STATUS_TYPES:
            if getattr(self, status_type) is not None:
                self.status_type = status_type

        super(DossierStatistic, self).save(*args, **kwargs)


class Memo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='memos')
    dossier = models.ForeignKey('Dossier', related_name='memos')
    content = models.CharField(max_length=2000)
    order = models.IntegerField()

