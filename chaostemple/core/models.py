# -*- coding: utf-8
import operator
from threading import currentThread

from django.conf import settings
from django.db import models
from django.db.models import Q

from althingi.models import Issue as AlthingiIssue
from althingi.models import Person

from dossier.models import DossierStatistic

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
            dossier_statistics = DossierStatistic.objects.select_related('user').filter(
                issue__in=issues,
                has_useful_info=True
            ).filter(reduce(operator.or_, partial_conditions))

        # Get dossier statistics from full access given by other users
        visible_user_ids = [a.user_id for a in accesses['full']]
        dossier_statistics = dossier_statistics | DossierStatistic.objects.select_related('user').filter(
            Q(user_id__in=visible_user_ids) | Q(user_id=user_id),
            issue__in=issues,
            has_useful_info=True
        )

        for issue in issues:
            if issue is None:
                continue

            for dossier_statistic in dossier_statistics:
                if dossier_statistic.issue_id == issue.id:
                    if not hasattr(issue, 'dossier_statistics'):
                        issue.dossier_statistics = []
                    issue.dossier_statistics.append(dossier_statistic)

                    # Add current user's new_documents and new_reviews
                    if dossier_statistic.user_id == user_id:
                        issue.new_documents = issue.document_count - dossier_statistic.document_count
                        issue.new_reviews = issue.review_count - dossier_statistic.review_count
        return issues


### Models

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userprofile')

    name = models.CharField(max_length=100)
    person = models.ForeignKey(Person, null=True, related_name='userprofile')


class IssueBookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='issue_bookmarks')
    issue = models.ForeignKey(AlthingiIssue, related_name='issue_bookmarks')


class Issue(AlthingiIssue):
    class Meta:
        proxy = True


class Access(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='access')
    friend = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='friend_access')

    full_access = models.BooleanField(default=False)
    issues = models.ManyToManyField('Issue')

    class Meta:
        ordering = ['friend__username']
