# -*- coding: utf-8
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.db.models import F
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from althingi.models import Document
from althingi.models import Issue
from althingi.models import Review

from model_utils import FieldTracker


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
        ('referral', _('Referral')),
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
        u'þáltill. n.': ['support', 'proposal'],
    }

    issue = models.ForeignKey(Issue, related_name='dossiers')
    dossier_type = models.CharField(max_length=10, choices=DOSSIER_TYPES)

    document = models.ForeignKey(Document, null=True, related_name='dossiers')
    review = models.ForeignKey(Review, null=True, related_name='dossiers')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dossiers')
    attention = models.CharField(max_length=20, default='none', choices=ATTENTION_STATES)
    knowledge = models.IntegerField(default=0, choices=KNOWLEDGE_STATES)
    support = models.CharField(max_length=20, default='undefined', choices=SUPPORT_STATES)
    proposal = models.CharField(max_length=20, default='none', choices=PROPOSAL_STATES)

    def update_statistic(self, statistic, field, old_value, new_value):
        # Short-hands
        issue_id = self.issue_id
        user_id = self.user_id
        dossier_type = self.dossier_type

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

        if new_value is not None:
            statistic_field = '%s_%s_%s' % (dossier_type, field, new_value)
            if hasattr(statistic, statistic_field):
                kwargs = {'issue_id': issue_id, 'user_id': user_id, 'dossier_type': dossier_type, field: new_value}
                count = Dossier.objects.filter(**kwargs).exclude(**exclude_kwargs).count()
                setattr(statistic, statistic_field, count)


    def update_counts(self, statistic, dossier_type):
        # Son, never trust an input value that doesn't drink.
        if dossier_type not in dict(self.DOSSIER_TYPES).keys():
            return

        count = Dossier.objects.filter(issue_id=self.issue_id, user_id=self.user_id, dossier_type=dossier_type).count()
        setattr(statistic, '%s_count' % dossier_type, count)


    def update_memo_counts(self, statistic, dossier_type):
        fieldname = '%s_memo_count' % dossier_type
        count = Memo.objects.filter(
            user_id=statistic.user_id,
            dossier__issue_id=statistic.issue_id,
            dossier__dossier_type=dossier_type
        ).count()

        setattr(statistic, fieldname, count)


    def save(self, input_statistic=None, *args, **kwargs):
        new = self.pk is None

        if self.document_id:
            self.issue_id = self.document.issue_id
            self.dossier_type = 'document'
        elif self.review_id:
            self.issue_id = self.review.issue_id
            self.dossier_type = 'review'

        super(Dossier, self).save(*args, **kwargs)

        if input_statistic is None:
            statistic, c = DossierStatistic.objects.get_or_create(issue_id=self.issue_id, user_id=self.user_id)
        else:
            statistic = input_statistic

        for field, old_value in self.tracker.changed().items():
            self.update_statistic(statistic, field, old_value, getattr(self, field))

        if new:
            self.update_counts(statistic, self.dossier_type)

        if input_statistic is None:
            statistic.save()


    def delete(self):
        statistic = DossierStatistic.objects.get(issue_id=self.issue_id, user_id=self.user_id)
        dossier_type = self.dossier_type

        super(Dossier, self).delete()

        dossier_count = Dossier.objects.filter(issue_id=self.issue_id, user_id=self.user_id).count()

        if dossier_count == 0:
            statistic.delete()
        else:
            for field in self.tracker.fields:
                self.update_statistic(statistic, field, getattr(self, field), None)
            self.update_counts(statistic, dossier_type)

            self.update_memo_counts(statistic, dossier_type)

            statistic.save()


    @staticmethod
    def fieldstate_applicable(doc_type, fieldstate):
        if doc_type and Dossier.DOC_TYPE_EXCLUSIONS.has_key(doc_type):
            if fieldstate in Dossier.DOC_TYPE_EXCLUSIONS[doc_type]:
                return False

        return True


class DossierStatistic(models.Model):
    issue = models.ForeignKey(Issue)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='dossier_statistics')
    has_useful_info = models.BooleanField(default=False)

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
    document_support_referral = models.IntegerField(default=0)
    document_support_other = models.IntegerField(default=0)
    document_proposal_minor = models.IntegerField(default=0)
    document_proposal_some = models.IntegerField(default=0)
    document_proposal_major = models.IntegerField(default=0)

    document_count = models.IntegerField(default=0)
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
    review_support_referral = models.IntegerField(default=0)
    review_support_other = models.IntegerField(default=0)
    review_proposal_minor = models.IntegerField(default=0)
    review_proposal_some = models.IntegerField(default=0)
    review_proposal_major = models.IntegerField(default=0)

    review_count = models.IntegerField(default=0)
    review_memo_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        self.update_has_useful_info()
        super(DossierStatistic, self).save(*args, **kwargs)

    def update_has_useful_info(self):

        # Check this first and return, to not unnecessarily iterate through the fieldstates.
        if self.document_memo_count > 0 or self.review_memo_count > 0:
            self.has_useful_info = True
            return

        for dossier_type, dossier_type_name in Dossier.DOSSIER_TYPES:
            for status_type, status_type_name in Dossier.STATUS_TYPES:
                fieldstates = '%s_STATES' % status_type.upper()

                fieldstate_iterator = 0
                for fieldstate, fieldstate_name in getattr(Dossier, fieldstates):
                    stat_field_name = '%s_%s_%s' % (dossier_type, status_type, fieldstate)
                    if fieldstate_iterator > 0 and getattr(self, stat_field_name) > 0:
                        self.has_useful_info = True
                        return

                    fieldstate_iterator = fieldstate_iterator + 1

        # If function hasn't already returned at this point, then nothing useful was found.
        self.has_useful_info = False
        return

    def update_stats_quite_inefficiently_please(self):
        '''
        WARNING: This function is intended only for diagnostic and data-fixing purposes.
        Do not use it for general production purposes. That would be silly.
        It should not alter data if everything is working as expected.

        Preferably, it should only function as a code-guide to how stats are expected to work.
        '''
        # For both 'document' and 'review'
        for dossier_type, dossier_type_name in Dossier.DOSSIER_TYPES:
            for status_type, status_type_name in Dossier.STATUS_TYPES:

                # Figure out which doc-types to exclude, if we're dealing with a document
                exclude_kwargs = {} # Will be empty and without effect if nothing is excluded
                excluded_doc_types = []
                if dossier_type == 'document':
                    for doc_type in Dossier.DOC_TYPE_EXCLUSIONS:
                        if status_type in Dossier.DOC_TYPE_EXCLUSIONS[doc_type]:
                            excluded_doc_types += [doc_type]
                if len(excluded_doc_types):
                    exclude_kwargs.update({'document__doc_type__in': excluded_doc_types})

                fieldstates = '%s_STATES' % status_type.upper()
                for fieldstate, fieldstate_name in getattr(Dossier, fieldstates):
                    stat_field_name = '%s_%s_%s' % (dossier_type, status_type, fieldstate)
                    if hasattr(self, stat_field_name):
                        kwargs = {
                            'issue_id': self.issue_id,
                            'user_id': self.user_id,
                            'dossier_type': dossier_type,
                            status_type: fieldstate
                        }
                        count = Dossier.objects.filter(**kwargs).exclude(**exclude_kwargs).count()
                        if getattr(self, stat_field_name) != count:
                            print "(%s, %s) %s: %d" % (self.user, self.issue, stat_field_name, count)
                        setattr(self, stat_field_name, count)

            count_fieldname = '%s_count' % dossier_type
            count = Dossier.objects.filter(
                issue_id=self.issue_id,
                user_id=self.user_id,
                dossier_type=dossier_type
            ).count()
            if getattr(self, count_fieldname) != count:
                print '(%s, %s) %s: %d' % (self.user, self.issue, count_fieldname, count)
            setattr(self, count_fieldname, count)

            memo_count_fieldname = '%s_memo_count' % dossier_type
            memo_count = Memo.objects.filter(
                user_id=self.user_id,
                dossier__issue_id=self.issue_id,
                dossier__dossier_type=dossier_type
            ).count()
            if getattr(self, memo_count_fieldname) != memo_count:
                print '(%s, %s) %s: %d' % (self.user, self.issue, memo_count_fieldname, memo_count)
            setattr(self, memo_count_fieldname, memo_count)

        self.save()


class Memo(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='memos')
    dossier = models.ForeignKey('Dossier', related_name='memos')
    content = models.CharField(max_length=2000)
    order = models.IntegerField()

    def save(self, *args, **kwargs):
        new = self.pk is None

        super(Memo, self).save(*args, **kwargs)

        if new:
            statistic = DossierStatistic.objects.get(user_id=self.user_id, issue_id=self.dossier.issue_id)
            self.dossier.update_memo_counts(statistic, self.dossier.dossier_type)
            statistic.save()

    def delete(self):
        super(Memo, self).delete()

        statistic = DossierStatistic.objects.get(user_id=self.user_id, issue_id=self.dossier.issue_id)
        self.dossier.update_memo_counts(statistic, self.dossier.dossier_type)
        statistic.save()

    class Meta:
        ordering = ['order']
