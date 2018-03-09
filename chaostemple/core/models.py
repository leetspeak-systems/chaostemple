# -*- coding: utf-8
import operator
from threading import currentThread

from django.conf import settings
from django.db import models
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django.utils.translation import ugettext as _

from althingi.models import Issue as AlthingiIssue
from althingi.models import Person

from dossier.models import DossierStatistic

# Custom query sets and model managers

class IssueQuerySet(models.QuerySet):

    def annotate_news(self, user_id):
        '''
        Annotates the query with the number of new_documents and new_reviews.
        '''

        news_subquery = Issue.objects.filter(
            dossierstatistic__user_id=user_id,
            pk=OuterRef('pk')
        ).annotate(
            new_documents=F('document_count') - F('dossierstatistic__document_count'),
            new_reviews=F('review_count') - F('dossierstatistic__review_count')
        )

        issues = self.annotate(
            new_documents=Subquery(news_subquery.values('new_documents'), output_field=IntegerField()),
            new_reviews=Subquery(news_subquery.values('new_reviews'), output_field=IntegerField())
        )

        return issues

    def incoming(self, user_id):
        '''
        Returns issues with new documents or new reviews.
        See also IssueQuerySet.annotate_news().
        '''

        issues = self.annotate_news(user_id).exclude(new_documents=0, new_reviews=0).filter(
            dossierstatistic__user_id=user_id,
            dossierstatistic__has_useful_info=True
        )

        return issues


# Model utilities

class AccessUtilities():
    cached_access = {}
    user_id = 0

    @staticmethod
    def get_access():
        return AccessUtilities.cached_access[currentThread()]

    @staticmethod
    def cache_access(user_id):
        AccessUtilities.cached_access[currentThread()] = Access.objects.filter(friend_id=user_id)
        AccessUtilities.user_id = user_id


class IssueUtilities():

    @staticmethod
    def populate_dossier_statistics(issues):

        # Get currently logged in user ID
        user_id = AccessUtilities.user_id

        access_filter = Q()

        # Get access objects and sort them
        accesses = {'partial': [], 'full': []}
        for access in AccessUtilities.get_access():
            accesses['full' if access.full_access else 'partial'].append(access)

        # Get dossier statistics from partial access given by other users
        partial_conditions = []
        dossier_statistics = DossierStatistic.objects.none()
        for partial_access in accesses['partial']:
            for issue in partial_access.issues.all():
                partial_conditions.append(Q(user_id=partial_access.user_id) & Q(issue_id=issue.id))
        if len(partial_conditions) > 0:
            access_filter = access_filter | Q(reduce(operator.or_, partial_conditions))

        # Get dossier statistics from full access given by other users
        visible_user_ids = [a.user_id for a in accesses['full']]
        access_filter = access_filter | Q(Q(user_id__in=visible_user_ids) | Q(user_id=user_id))

        dossier_statistics = DossierStatistic.objects.select_related('user__userprofile').filter(
            access_filter,
            issue__in=issues,
            has_useful_info=True
        )

        # TODO: Maybe we can make this fit with Issue.QuerySet.as_manager()
        # Perhaps by using annotate/aggregate with the DossierStatistic.objects.-query above.
        for issue in issues:
            if issue is None:
                continue

            for dossier_statistic in dossier_statistics:
                if dossier_statistic.issue_id == issue.id:
                    if not hasattr(issue, 'dossier_statistics'):
                        issue.dossier_statistics = []
                    issue.dossier_statistics.append(dossier_statistic)

        return issues


### Models

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userprofile')

    name = models.CharField(max_length=100)
    initials = models.CharField(max_length=10, null=True)
    person = models.ForeignKey(Person, null=True, related_name='userprofile')

    def __unicode__(self):
        return self.initials if self.initials else _(u'[ Missing initials ]')


class IssueBookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='issue_bookmarks')
    issue = models.ForeignKey(AlthingiIssue, related_name='issue_bookmarks')


class Issue(AlthingiIssue):
    objects = IssueQuerySet.as_manager()

    class Meta:
        proxy = True


class Access(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='access')
    friend = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friend_access')

    full_access = models.BooleanField(default=False)
    issues = models.ManyToManyField('Issue')

    class Meta:
        ordering = ['friend__username']
