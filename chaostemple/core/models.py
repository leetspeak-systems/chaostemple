import operator
from functools import reduce
from threading import currentThread

from django.conf import settings
from django.db import models
from django.db.models import CASCADE
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django.utils.safestring import mark_safe
from django.utils import timezone
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

    cache = {}

    @staticmethod
    def get_access():
        return AccessUtilities.cache[currentThread()]['access']

    @staticmethod
    def get_user_id():
        return AccessUtilities.cache[currentThread()]['user_id']

    @staticmethod
    def cache_access(user):
        group_ids = [g.id for g in user.groups.all()]

        AccessUtilities.cache[currentThread()] = {
            'access': Access.objects.filter(Q(friend_id=user.id) | Q(friend_group_id__in=group_ids)),
            'user_id': user.id,
        }

class IssueUtilities():

    @staticmethod
    def populate_dossier_statistics(issues):

        # Get currently logged in user ID
        user_id = AccessUtilities.get_user_id()

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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userprofile', on_delete=CASCADE)

    name = models.CharField(max_length=100)
    initials = models.CharField(max_length=10, null=True)
    person = models.ForeignKey(Person, null=True, related_name='userprofile', on_delete=CASCADE)

    def display_full(self):
        return mark_safe('<a href="mailto: %s">%s</a> (%s)' % (self.user.email, self.name, self.initials))

    def __str__(self):
        return self.initials if self.initials else self.user.email


class IssueBookmark(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='issue_bookmarks', on_delete=CASCADE)
    issue = models.ForeignKey(AlthingiIssue, related_name='issue_bookmarks', on_delete=CASCADE)


class Issue(AlthingiIssue):
    objects = IssueQuerySet.as_manager()

    class Meta:
        proxy = True


class Access(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='access', on_delete=CASCADE)
    friend = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name='friend_access', on_delete=CASCADE)
    friend_group = models.ForeignKey('auth.Group', null=True, related_name='friend_group_access', on_delete=CASCADE)

    full_access = models.BooleanField(default=False)
    issues = models.ManyToManyField('Issue')

    class Meta:
        ordering = ['friend__userprofile__initials', 'friend_group__name']


class MembershipRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', _('pending')),
        ('rejected', _('rejected')),
        ('accepted', _('accepted')),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='membership_requests', on_delete=CASCADE)
    group = models.ForeignKey('auth.Group', related_name='membership_requests', on_delete=CASCADE)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        related_name='decided_membership_requests',
        on_delete=CASCADE
    )

    timing_requested = models.DateTimeField(auto_now_add=True)
    timing_decided = models.DateTimeField(null=True)

    # To not only set the status, but take appropriate actions.
    def set_status(self, status, decided_by):
        if not status in dict(self.STATUS_CHOICES):
            return None

        if status == 'accepted':
            self.group.user_set.add(self.user)

        self.status = status
        self.decided_by = decided_by
        self.timing_decided = timezone.now()
        self.save()

    def __str__(self):
        return '%s (%s)' % (self.group, self.get_status_display())

    class Meta:
        ordering = ['group__name', 'status']
