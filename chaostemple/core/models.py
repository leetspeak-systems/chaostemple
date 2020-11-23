import operator
from functools import reduce
from threading import currentThread

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import CASCADE
from django.db.models import Count
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.utils.translation import ugettext as _

from djalthingi.althingi_settings import CURRENT_PARLIAMENT_NUM

from djalthingi.models import Issue as AlthingiIssue
from djalthingi.models import IssueQuerySet as AlthingiIssueQuerySet
from djalthingi.models import Document as AlthingiDocument
from djalthingi.models import Person
from djalthingi.models import Review as AlthingiReview

# Custom query sets and model managers

class IssueQuerySet(AlthingiIssueQuerySet):

    def annotate_news(self, user):
        '''
        Annotates the query with the number of new_documents and new_reviews
        and a seen_count which is the total number of documents or reviews
        that the user has seen so far.
        '''

        q_filter = Q(dossiers__user_id=user.id)
        if user.userprofile.setting_seen_if_worked_by_others:
            # If the seen-if-worked-by-others setting is selected, we will
            # count other users' seen items as seen by us.
            Dossier = apps.get_model('dossier', 'Dossier')
            q_filter |= Q(dossiers__in=Dossier.objects.by_user(user))

        news_subquery = Issue.objects.filter(
            dossierstatistic__user_id=user.id,
            pk=OuterRef('pk')
        ).annotate(
            seen_documents=Count('dossiers__document', filter=q_filter, distinct=True),
            seen_reviews=Count('dossiers__review', filter=q_filter, distinct=True),

            seen_count=F('seen_documents') + F('seen_reviews'),
            new_documents=F('document_count') - F('seen_documents'),
            new_reviews=F('review_count') - F('seen_reviews')
        )

        issues = self.annotate(
            seen_count=Subquery(news_subquery.values('seen_count'), output_field=IntegerField()),
            new_documents=Subquery(news_subquery.values('new_documents'), output_field=IntegerField()),
            new_reviews=Subquery(news_subquery.values('new_reviews'), output_field=IntegerField())
        )

        return issues

    def incoming(self, user):
        '''
        Returns issues with new documents or new reviews.
        See also IssueQuerySet.annotate_news().
        '''

        issues = self.annotate_news(user).exclude(new_documents=0, new_reviews=0).filter(
            dossierstatistic__user_id=user_id,
            dossierstatistic__has_useful_info=True
        )

        return issues


class SeenQuerySet(models.QuerySet):
    '''
    A query set for annotating the "seen" attribute on the Document and Review
    models. Used with proxy models below. Depends on being used with a model
    that has Dossier relationships called "dossiers".
    '''
    def annotate_seen(self, user):

        if not user.is_authenticated:
            return self

        q_filter = Q(dossiers__user=user)
        if user.userprofile.setting_seen_if_worked_by_others:
            # If the seen-if-worked-by-others setting is selected, we will
            # count other users' seen items as seen by us.
            Dossier = apps.get_model('dossier', 'Dossier')
            q_filter |= Q(dossiers__in=Dossier.objects.by_user(user))

        return self.annotate(
            seen=Count(
                'dossiers',
                filter=q_filter
            )
        )


class SubscriptionManager(models.Manager):
    # Just so that the developer doesn't have to keep track of what things can
    # be subscribed to.
    def select_subscribed(self):
        return self.select_related(
            'committee',
            'category'
        ).prefetch_related(
            'committee__issues',
            'category__issues'
        )

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
            'access': Access.objects.filter(
                Q(friend_id=user.id, friend_group_id=None)
                | Q(friend_group_id__in=group_ids, friend_id=None)
            ),
            'user_id': user.id,
        }

class IssueUtilities():

    @staticmethod
    def bulk_update_has_useful_info(issues):
        '''
        Updates the `has_useful_info` attribute of the given issues'
        DossierStatistic as quickly as possible. Assumes logged in user.
        Creates DossierStatistic objects for those issues for which the user
        still doesn't have any.
        '''
        DossierStatistic = apps.get_model('dossier', 'DossierStatistic')

        # Get currently logged in user ID
        user_id = AccessUtilities.get_user_id()

        # Existing DossierStatistic objects.
        stats = DossierStatistic.objects.filter(
            user_id=user_id,
            issue__in=issues
        )

        # List of IDs of issues monitored, which may be deemed useful later.
        monitored_issue_ids = [m.issue_id for m in IssueMonitor.objects.filter(user_id=user_id)]

        # Returns a list of issue IDs subscribed to.
        subscribed_issue_ids = Subscription.objects.filter(
            committee__issues__parliament__parliament_num=CURRENT_PARLIAMENT_NUM,
            user_id=user_id,
        ).values_list(
            'committee__issues__id',
            flat=True
        ).union(
            Subscription.objects.filter(
                category__issues__parliament__parliament_num=CURRENT_PARLIAMENT_NUM,
                user_id=user_id
            ).values_list(
                'category__issues__id',
                flat=True
            )
        )

        # A map of DossierStatistic objects, using issue_id a key.
        stat_map = {stat.issue_id: stat for stat in stats}

        # DossierStatistic objects that will need to be created.
        stats_for_creation = []

        # Iterate through the given issues and determine which
        # DossierStatistic objects need to be updated and which ones need to
        # be created.
        for issue in issues:
            if issue.id in stat_map:
                # Update the data on the stat-objects. This does not save the
                # data to database (because that would be slow), only updates
                # the fields in the objects, which are then bulk-updated
                # after this iteration.
                stat_map[issue.id].update_has_useful_info(
                    is_monitored=issue.id in monitored_issue_ids,
                    is_subscribed=issue.id in subscribed_issue_ids
                )
            else:
                # Create non-existing stats. Only objects, which are not
                # saved to database until the bulk-create below.
                stat = DossierStatistic(user_id=user_id, issue_id=issue.id)
                stat.update_has_useful_info(
                    is_monitored=issue.id in monitored_issue_ids,
                    is_subscribed=issue.id in subscribed_issue_ids
                )
                stats_for_creation.append(stat)

        # Bulk-update stats that need updating.
        DossierStatistic.objects.bulk_update(stats, ['has_useful_info'])

        # Bulk-crate stats that need creating.
        DossierStatistic.objects.bulk_create(stats_for_creation)

    @staticmethod
    def populate_issue_data(issues):
        DossierStatistic = apps.get_model('dossier', 'DossierStatistic')

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
            issue__in=issues
        ).order_by('user__userprofile__initials')

        # Retrieve the monitors for the given issues, if any.
        monitor_map = { m.issue_id: m for m in IssueMonitor.objects.filter(user_id=user_id) }

        # Get subscriptions so that we can look them up by issue.
        subscription_map = {}
        subscriptions = Subscription.objects.select_subscribed().filter(user_id=user_id)
        for sub in subscriptions:
            for issue in sub.subscribed_thing().issues.all():
                if not issue.id in subscription_map:
                    subscription_map[issue.id] = []
                subscription_map[issue.id].append(sub)

        for issue in issues:
            if issue is None:
                continue

            # If the issue is being monitored by the user, apply the monitor to the issue.
            if issue.id in monitor_map:
                issue.monitor = monitor_map[issue.id]

            # If the issue is subscribed to, apply the subscribed thing to it.
            if issue.id in subscription_map:
                issue.subscriptions = subscription_map[issue.id]

            for dossier_statistic in dossier_statistics:
                if dossier_statistic.issue_id == issue.id:
                    if not hasattr(issue, 'dossier_statistics'):
                        issue.dossier_statistics = []

                    if dossier_statistic.user_id == user_id:
                        issue.dossier_statistics.insert(0, dossier_statistic)
                    else:
                        issue.dossier_statistics.append(dossier_statistic)

        return issues


### Models

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='userprofile', on_delete=CASCADE)

    name = models.CharField(max_length=100)
    initials = models.CharField(max_length=10, null=True)
    person = models.ForeignKey(Person, null=True, related_name='userprofile', on_delete=CASCADE)

    last_seen = models.DateTimeField(null=True)

    setting_auto_monitor = models.BooleanField(default=True)
    setting_hide_concluded_from_monitors = models.BooleanField(default=True)
    setting_seen_if_worked_by_others = models.BooleanField(default=True)

    def display_full(self):
        return mark_safe('<a href="mailto: %s">%s</a> (%s)' % (self.user.email, self.name, self.initials))

    def __str__(self):
        return self.initials if self.initials else self.user.email


class IssueMonitor(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='issue_monitors', on_delete=CASCADE)
    issue = models.ForeignKey(AlthingiIssue, related_name='issue_monitors', on_delete=CASCADE)

    def save(self, *args, **kwargs):
        DossierStatistic = apps.get_model('dossier', 'DossierStatistic')

        super(IssueMonitor, self).save(*args, **kwargs)

        try:
            stat = self.issue.dossierstatistic_set.get(user_id=self.user_id)
        except DossierStatistic.DoesNotExist:
            # When an issue is monitored, there must exist a DossierStatistic,
            # so that we have a place to record the state of things from now
            # on. We'll want to be notified about new documents/reviews and
            # changes to the issue's status.
            stat = DossierStatistic(user_id=self.user_id, issue_id=self.issue_id)

        # Trigger an update of has_useful_info.
        stat.save()

    def delete(self):
        DossierStatistic = apps.get_model('dossier', 'DossierStatistic')

        super(IssueMonitor, self).delete()

        try:
            stat = self.issue.dossierstatistic_set.get(user_id=self.user_id)
            # Trigger an update of has_useful_info.
            stat.save()
        except DossierStatistic.DoesNotExist:
            # Oh well, whatever. Nevermind.
            pass


class Issue(AlthingiIssue):
    objects = IssueQuerySet.as_manager()

    class Meta:
        proxy = True


class Document(AlthingiDocument):
    objects = SeenQuerySet.as_manager()

    class Meta:
        proxy = True


class Review(AlthingiReview):
    objects = SeenQuerySet.as_manager()

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
            access, created = Access.objects.get_or_create(
                user=self.user,
                friend_group=self.group,
                full_access=True
            )

        self.status = status
        self.decided_by = decided_by
        self.timing_decided = timezone.now()
        self.save()

    def __str__(self):
        return '%s (%s)' % (self.group, self.get_status_display())

    class Meta:
        ordering = ['group__name', 'status']


class Subscription(models.Model):
    objects = SubscriptionManager()

    SUB_TYPE_CHOICES = (
        ('party', _('Parties')),
        ('committee', _('Committees')),
        ('person', _('MPs')),
        ('category', _('Categories')),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='subscriptions', on_delete=CASCADE)
    sub_type = models.CharField(max_length=20, choices=SUB_TYPE_CHOICES)

    party = models.ForeignKey('djalthingi.Party', null=True, related_name='subscriptions', on_delete=CASCADE)
    committee = models.ForeignKey('djalthingi.Committee', null=True, related_name='subscriptions', on_delete=CASCADE)
    person = models.ForeignKey('djalthingi.Person', null=True, related_name='subscriptions', on_delete=CASCADE)
    category = models.ForeignKey('djalthingi.Category', null=True, related_name='subscriptions', on_delete=CASCADE)

    class Meta:
        unique_together = ['user', 'party', 'committee', 'person']
        ordering = ['sub_type']

    def subscribed_thing(self):
        try:
            thing = getattr(self, self.sub_type)
        except AttributeError:
            thing = None
        return thing

    def subscribed_thing_link(self):
        thing = self.subscribed_thing()
        if self.sub_type == 'committee':
            if thing.parliament_num_last is not None:
                parliament_num = thing.parliament_num_last
            else:
                parliament_num = CURRENT_PARLIAMENT_NUM
            return reverse('parliament_committee', args=(parliament_num, thing.id))
        elif self.sub_type == 'category':
            return reverse('parliament_category', args=(CURRENT_PARLIAMENT_NUM, thing.slug))

        return None

    def save(self, *args, **kwargs):
        # Make sure that what's being subscribed to is sane.
        self.sub_type = ''
        fields = ['party', 'committee', 'person', 'category']
        for field in fields:
            if getattr(self, field) is not None:
                self.sub_type = field
                break

        if not self.sub_type:
            raise Exception('Subscription must be to one of fields: %s' % ', '.join(fields))

        # Only allow one thing to be subscribed to.
        for field in fields:
            if field != self.sub_type and getattr(self, field) is not None:
                raise Exception(
                    'Subscription may only be to one thing (currently %s)' % self.subscribed_thing()
                )

        # Prevent duplicate subscriptions.
        thing = self.subscribed_thing()
        lookup = {'user': self.user, self.sub_type: thing}
        if Subscription.objects.filter(**lookup).count() > 0:
            raise Exception('Already subscribed to that item')

        super(Subscription, self).save(*args, **kwargs)

        # Make sure that DossierStatistic objects exist for all issues and
        # that the `has_useful_info` attribute is properly set.
        #
        # NOTE: "Things", which may be a number of different types of models,
        # are assumed to have issues. Examples: Committees, categories.
        issues = thing.issues.exclude(dossierstatistic__user_id=self.user_id)
        IssueUtilities.bulk_update_has_useful_info(issues)

    def delete(self):
        DossierStatistic = apps.get_model('dossier', 'DossierStatistic')

        # Save DossierStatistic objects to trigger update_has_useful_info.
        thing = self.subscribed_thing()
        issues = thing.issues.exclude(dossierstatistic__user_id=self.user_id)

        super(Subscription, self).delete()

        # Must happen after the deletion, of course.
        IssueUtilities.bulk_update_has_useful_info(issues)

    def __str__(self):
        sub_type = self.sub_type if self.sub_type else 'undetermined'
        return '%s subscribed to %s %s' % (self.user, sub_type, self.subscribed_thing())
