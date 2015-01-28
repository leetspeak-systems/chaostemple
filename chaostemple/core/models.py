# -*- coding: utf-8
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import FieldTracker

from althingi.models import Document
from althingi.models import Issue as AlthingiIssue
from althingi.models import Person
from althingi.models import Review

### QuerySets

class IssueQuerySet(models.QuerySet):
    def populate_dossier_statistics(self, user_id):
        issues = self
        dossier_statistics = DossierStatistic.objects.filter(user_id=user_id)
        for issue in issues:
            for dossier_statistic in dossier_statistics:
                if dossier_statistic.issue_id == issue.id:
                    if not hasattr(issue, 'dossier_statistics'):
                        issue.dossier_statistics = []
                    issue.dossier_statistics.append(dossier_statistic)
        return issues

### Managers

class IssueManager(models.Manager):
    def get_queryset(self):
        return IssueQuerySet(self.model, using=self._db)

### Models

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userprofile')

class IssueBookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='issue_bookmarks')
    issue = models.ForeignKey(AlthingiIssue, related_name='issue_bookmarks')

class Issue(AlthingiIssue):
    objects = IssueManager()

    class Meta:
        proxy = True

class Dossier(models.Model):
    tracker = FieldTracker(fields=['attention', 'knowledge', 'support', 'proposal'])

    DOSSIER_TYPES = (
        ('document', _('Parliamentary Documents')),
        ('review', _('Reviews')),
    )

    STATUS_TYPES = (
        ('attention', _('Attention')),
        ('knowledge', _('Knowledge')),
        ('support', _('Support')),
        ('proposal', _('Proposals')),
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

    PROPOSAL_STATES = (
        ('none', _('None')),
        ('minor', _('Minor')),
        ('some', _('Some')),
        ('major', _('Major')),
    )

    DOC_TYPE_EXCLUSIONS = {
        u'beiðni um skýrslu': ['support', 'proposal'],
        u'breytingartillaga': ['support'],
        u'frumvarp': ['support', 'proposal'],
        u'frumvarp eftir 2. umræðu': ['support', 'proposal'],
        u'frumvarp nefndar': ['support', 'proposal'],
        u'fsp. til munnl. svars': ['support', 'proposal'],
        u'fsp. til skrifl. svars': ['support', 'proposal'],
        u'lög (samhlj.)': ['support', 'proposal'],
        u'lög í heild': ['support', 'proposal'],
        u'nál. með brtt.': [],
        u'nefndarálit': ['proposal'],
        u'skýrsla n. (frumskjal)': ['support', 'proposal'],
        u'skýrsla rh. (frumskjal)': ['support', 'proposal'],
        u'stjórnarfrumvarp': ['support', 'proposal'],
        u'stjórnartillaga': ['support', 'proposal'],
        u'svar': ['support', 'proposal'],
        u'þál. (samhlj.)': ['support', 'proposal'],
        u'þál. í heild': ['support', 'proposal'],
        u'þáltill.': ['support', 'proposal'],
    }

    issue = models.ForeignKey(AlthingiIssue, related_name='dossiers')
    dossier_type = models.CharField(max_length=10, choices=DOSSIER_TYPES)

    document = models.ForeignKey(Document, null=True, related_name='dossiers')
    review = models.ForeignKey(Review, null=True, related_name='dossiers')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dossiers')
    attention = models.CharField(max_length=20, default='none', choices=ATTENTION_STATES)
    knowledge = models.IntegerField(default=0, choices=KNOWLEDGE_STATES)
    support = models.CharField(max_length=20, default='undefined', choices=SUPPORT_STATES)
    proposal = models.CharField(max_length=20, default='none', choices=PROPOSAL_STATES)

    def update_statistic(self, field, old_value, new_value):
        # Short-hands
        issue_id = self.issue_id
        user_id = self.user_id
        dossier_type = self.dossier_type

        statistic, c = DossierStatistic.objects.get_or_create(issue_id=issue_id, user_id=user_id)

        exclude_kwargs = {} # Will be empty and without effect if nothing is excluded
        excluded_doc_types = []
        if dossier_type == 'document':
            for doc_type in Dossier.DOC_TYPE_EXCLUSIONS:
                if field in Dossier.DOC_TYPE_EXCLUSIONS[doc_type]:
                    excluded_doc_types += [doc_type]
        if len(excluded_doc_types):
            exclude_kwargs.update({'document__doc_type__in': excluded_doc_types})

        if old_value is not None:
            statistic_field = '%s_%s_%s' % (dossier_type, field, old_value)
            if hasattr(statistic, statistic_field):
                kwargs = {'issue_id': issue_id, 'user_id': user_id, 'dossier_type': dossier_type, field: old_value}
                count = Dossier.objects.filter(**kwargs).exclude(**exclude_kwargs).count()
                setattr(statistic, statistic_field, count)
                statistic.save()

        if new_value is not None:
            statistic_field = '%s_%s_%s' % (dossier_type, field, new_value)
            if hasattr(statistic, statistic_field):
                kwargs = {'issue_id': issue_id, 'user_id': user_id, 'dossier_type': dossier_type, field: new_value}
                count = Dossier.objects.filter(**kwargs).exclude(**exclude_kwargs).count()
                setattr(statistic, statistic_field, count)
                statistic.save()


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


    @staticmethod
    def fieldstate_applicable(doc_type, fieldstate):
        if doc_type and Dossier.DOC_TYPE_EXCLUSIONS.has_key(doc_type):
            if fieldstate in Dossier.DOC_TYPE_EXCLUSIONS[doc_type]:
                return False

        return True


class DossierStatistic(models.Model):
    issue = models.ForeignKey(AlthingiIssue)
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
    document_proposal_minor = models.IntegerField(default=0)
    document_proposal_some = models.IntegerField(default=0)
    document_proposal_major = models.IntegerField(default=0)

    document_memo_count = models.IntegerField(default=0)

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
    review_proposal_minor = models.IntegerField(default=0)
    review_proposal_some = models.IntegerField(default=0)
    review_proposal_major = models.IntegerField(default=0)

    review_memo_count = models.IntegerField(default=0)


class Memo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='memos')
    dossier = models.ForeignKey('Dossier', related_name='memos')
    content = models.CharField(max_length=2000)
    order = models.IntegerField()

    def save(self, *args, **kwargs):
        new = self.pk is None

        super(Memo, self).save(*args, **kwargs)

        if new:
            self.update_statistic(self.user_id, self.dossier_id)

    def delete(self):
        user_id = self.user_id
        dossier_id = self.dossier_id

        super(Memo, self).delete()

        self.update_statistic(user_id, dossier_id)

    def update_statistic(self, user_id, dossier_id):
        dossier = Dossier.objects.get(id=dossier_id)

        fieldname = '%s_memo_count' % dossier.dossier_type
        count = Memo.objects.filter(
            user_id=user_id,
            dossier__issue_id=dossier.issue_id,
            dossier__dossier_type=dossier.dossier_type
        ).count()

        stat = DossierStatistic.objects.get(user_id=user_id, issue_id=dossier.issue_id)
        setattr(stat, fieldname, count)
        stat.save()

    class Meta:
        ordering = ['order']

