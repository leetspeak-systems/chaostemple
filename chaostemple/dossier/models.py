import re

from core.models import AccessUtilities
from core.models import Subscription

from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import CASCADE
from django.db.models import Case
from django.db.models import Count
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import PROTECT
from django.db.models import Q
from django.db.models import When
from django.utils.translation import gettext_lazy as _

from djalthingi.models import Document
from djalthingi.models import Issue
from djalthingi.models import Review

from model_utils import FieldTracker


class DossierManager(models.Manager):
    def by_user(self, user):
        """
        Filters dossiers by the appropriate visibility toward the given user.
        Example:

            dossiers = Dossier.objects.by_user(request.user).filter(
                document__issue__parliament__parliament_num=150,
                document__doc_num=123
            )

        Can also be used with prefetch_related.
        Example:

            visible_dossiers = Dossier.objects.by_user(request.user)
            documents = Document.objects.prefetch_related(
                Prefetch('dossiers', queryset=visible_dossiers)
            )
        """

        # Get access objects and sort them
        accesses = {"partial": [], "full": []}
        for access in AccessUtilities.get_access():
            accesses["full" if access.full_access else "partial"].append(access)

        visible_user_ids = [a.user_id for a in accesses["full"]]

        partial_conditions = []
        for partial_access in accesses["partial"]:
            for partial_issue in partial_access.issues.all():
                partial_conditions.append(
                    Q(user_id=partial_access.user_id) & Q(issue_id=partial_issue.id)
                )

        # Add dossiers from users who have given full access
        filter_params = Q(user_id__in=visible_user_ids) | Q(user_id=user.id)
        # Add dossiers from users who have given access to this particular issue
        if len(partial_conditions) > 0:
            filter_params.add(Q(reduce(operator.or_, partial_conditions)), Q.OR)

        # Add prefetch query but leave out useless information from other users
        visible_dossiers = (
            Dossier.objects.select_related("user__userprofile")
            .filter(filter_params)
            .annotate(
                # In order to order the current user first but everyone else by
                # initials, we first annotate the results so that the current user
                # gets the order 0 (first) and others get 1. Then the current user is
                # before everyone else, but the rest are tied with 1, which is
                # resolved with a second order clause in the order_by below.
                ordering=Case(
                    When(user_id=user.id, then=0),
                    default=1,
                    output_field=IntegerField(),
                )
            )
            .exclude(is_useful=False)
            .order_by("-ordering", "-user__userprofile__initials")
            .distinct()
        )

        return visible_dossiers


class Dossier(models.Model):
    objects = DossierManager()
    tracker = FieldTracker(fields=["attention", "knowledge", "support", "proposal"])

    DOSSIER_TYPES = (
        ("document", _("Parliamentary Documents")),
        ("review", _("Reviews")),
    )

    STATUS_TYPES = (
        ("attention", _("Attention")),
        ("knowledge", _("Knowledge")),
        ("support", _("Support")),
        ("proposal", _("Proposals")),
    )

    ATTENTION_STATES = (
        ("none", _("None")),
        ("question", _("Question")),
        ("exclamation", _("Exclamation")),
    )

    KNOWLEDGE_STATES = (
        (0, _("Unread")),
        (1, _("Briefly examined")),
        (2, _("Examined")),
        (3, _("Thoroughly examined")),
    )

    SUPPORT_STATES = (
        ("undefined", _("Undefined")),
        ("strongopposition", _("Strong Opposition")),
        ("oppose", _("Oppose")),
        ("neutral", _("Neutral")),
        ("support", _("Support")),
        ("strongsupport", _("Strong Support")),
        ("referral", _("Referral")),
        ("other", _("Other")),
    )

    PROPOSAL_STATES = (
        ("none", _("None")),
        ("minor", _("Minor")),
        ("some", _("Some")),
        ("major", _("Major")),
    )

    DOC_TYPE_EXCLUSIONS = {
        "beiðni um skýrslu": ["support", "proposal"],
        "breytingartillaga": ["support"],
        "frumvarp": ["support", "proposal"],
        "frumvarp eftir 2. umræðu": ["support", "proposal"],
        "frumvarp nefndar": ["support", "proposal"],
        "fsp. til munnl. svars": ["support", "proposal"],
        "fsp. til skrifl. svars": ["support", "proposal"],
        "lög (samhlj.)": ["knowledge", "attention", "support", "proposal"],
        "lög í heild": ["support", "proposal"],
        "nál. með brtt.": [],
        "nefndarálit": ["proposal"],
        "skýrsla n. (frumskjal)": ["support", "proposal"],
        "skýrsla rh. (frumskjal)": ["support", "proposal"],
        "stjórnarfrumvarp": ["support", "proposal"],
        "stjórnartillaga": ["support", "proposal"],
        "svar": ["support", "proposal"],
        "þál. (samhlj.)": ["knowledge", "attention", "support", "proposal"],
        "þál. í heild": ["support", "proposal"],
        "þáltill.": ["support", "proposal"],
        "þáltill. n.": ["support", "proposal"],
    }

    issue = models.ForeignKey(Issue, related_name="dossiers", on_delete=CASCADE)
    dossier_type = models.CharField(max_length=10, choices=DOSSIER_TYPES)

    document = models.ForeignKey(
        Document, null=True, related_name="dossiers", on_delete=PROTECT
    )
    review = models.ForeignKey(
        Review, null=True, related_name="dossiers", on_delete=PROTECT
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="dossiers", on_delete=CASCADE
    )

    notes = models.TextField(default="")
    attention = models.CharField(
        max_length=20, default="none", choices=ATTENTION_STATES
    )
    knowledge = models.IntegerField(default=0, choices=KNOWLEDGE_STATES)
    support = models.CharField(
        max_length=20, default="undefined", choices=SUPPORT_STATES
    )
    proposal = models.CharField(max_length=20, default="none", choices=PROPOSAL_STATES)

    is_useful = models.BooleanField(default=False)

    def update_statistic(self, statistic, field, old_value, new_value):
        # Short-hands
        issue_id = self.issue_id
        user_id = self.user_id
        dossier_type = self.dossier_type

        exclude_kwargs = {}  # Will be empty and without effect if nothing is excluded
        excluded_doc_types = []
        if dossier_type == "document":
            for doc_type in Dossier.DOC_TYPE_EXCLUSIONS:
                if field in Dossier.DOC_TYPE_EXCLUSIONS[doc_type]:
                    excluded_doc_types += [doc_type]
        if len(excluded_doc_types):
            exclude_kwargs.update({"document__doc_type__in": excluded_doc_types})

        if old_value is not None:
            statistic_field = "%s_%s_%s" % (dossier_type, field, old_value)
            if hasattr(statistic, statistic_field):
                kwargs = {
                    "issue_id": issue_id,
                    "user_id": user_id,
                    "dossier_type": dossier_type,
                    field: old_value,
                }
                count = (
                    Dossier.objects.filter(**kwargs).exclude(**exclude_kwargs).count()
                )
                setattr(statistic, statistic_field, count)

        if new_value is not None:
            statistic_field = "%s_%s_%s" % (dossier_type, field, new_value)
            if hasattr(statistic, statistic_field):
                kwargs = {
                    "issue_id": issue_id,
                    "user_id": user_id,
                    "dossier_type": dossier_type,
                    field: new_value,
                }
                count = (
                    Dossier.objects.filter(**kwargs).exclude(**exclude_kwargs).count()
                )
                setattr(statistic, statistic_field, count)

    def update_counts(self, statistic, dossier_type):
        # Son, never trust an input value that doesn't drink.
        if dossier_type not in dict(self.DOSSIER_TYPES).keys():
            return

        count = Dossier.objects.filter(
            issue_id=self.issue_id, user_id=self.user_id, dossier_type=dossier_type
        ).count()
        setattr(statistic, "%s_count" % dossier_type, count)

    def save(self, input_statistic=None, *args, **kwargs):
        # Check if dossier is new.
        new = self.pk is None

        # Auto-fill issue_id and denote dossier type.
        if self.document_id:
            self.issue_id = self.document.issue_id
            self.dossier_type = "document"
        elif self.review_id:
            self.issue_id = self.review.issue_id
            self.dossier_type = "review"

        # Markdown automatically considers "4. something" in the beginning of
        # a sentence to be a sequentually numbered list, and thus if usually
        # rendered as "1. something" if standing alone, ignoring the number
        # but rather going by the sequence of the sentence. In legal text we
        # very often refer to legal positions with something like "7. gr." or
        # "4. mgr." and so forth. We must thus automatically escape these
        # numbers so that they are retained durin rendering. This is done by
        # adding a backslash after the number we wish to retain literally.
        escapees = ["gr.", "mgr.", "málsl.", "tölul.", "stafl.", "kafli", "kafla"]
        for e in escapees:
            self.notes = re.sub(r"(\d+)\. %s" % e, r"\1\. %s" % e, self.notes)

        # There is a tendency to press enter after writing something, and
        # since that creates a new bullet in the editor, this tendency results
        # in stray bullets on the right side of the text. We'll take it out,
        # also accounting for white space on either side of it.
        self.notes = self.notes.strip().rstrip("*").strip()

        # Determine if dossier contains useful info. Non-useful dossiers mean
        # that the file (document or review) has been opened and thus should
        # not be marked as "unread".
        self.is_useful = any(
            [
                len(self.notes) > 0,
                self.attention != "none",
                self.knowledge != 0,
                self.support != "undefined",
                self.proposal != "none",
            ]
        )

        # Take note of fields that changed.
        changed = self.tracker.changed()

        # Make sure that standard stuff happens.
        super(Dossier, self).save(*args, **kwargs)

        # Treat DossierStatistic.
        if input_statistic is None:
            statistic, created = DossierStatistic.objects.get_or_create(
                issue_id=self.issue_id, user_id=self.user_id
            )
        else:
            statistic = input_statistic

        for field, old_value in changed.items():
            self.update_statistic(statistic, field, old_value, getattr(self, field))

        if new:
            self.update_counts(statistic, self.dossier_type)

        if input_statistic is None:
            statistic.save()

    def delete(self):
        statistic = DossierStatistic.objects.get(
            issue_id=self.issue_id, user_id=self.user_id
        )
        dossier_type = self.dossier_type

        super(Dossier, self).delete()

        dossier_count = Dossier.objects.filter(
            issue_id=self.issue_id, user_id=self.user_id
        ).count()

        for field in self.tracker.fields:
            self.update_statistic(statistic, field, getattr(self, field), None)
        self.update_counts(statistic, dossier_type)

        statistic.save()

    @staticmethod
    def fieldstate_applicable(doc_type, fieldstate):
        if doc_type in Dossier.DOC_TYPE_EXCLUSIONS:
            if fieldstate in Dossier.DOC_TYPE_EXCLUSIONS[doc_type]:
                return False

        return True


class DossierStatistic(models.Model):
    issue = models.ForeignKey(Issue, on_delete=CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="dossier_statistics", on_delete=CASCADE
    )
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

    def save(self, *args, **kwargs):
        self.update_has_useful_info()
        super(DossierStatistic, self).save(*args, **kwargs)

    def update_has_useful_info(self, is_monitored=None, is_subscribed=None):

        for dossier_type, dossier_type_name in Dossier.DOSSIER_TYPES:
            for status_type, status_type_name in Dossier.STATUS_TYPES:
                fieldstates = "%s_STATES" % status_type.upper()

                fieldstate_iterator = 0
                for fieldstate, fieldstate_name in getattr(Dossier, fieldstates):
                    stat_field_name = "%s_%s_%s" % (
                        dossier_type,
                        status_type,
                        fieldstate,
                    )
                    if fieldstate_iterator > 0 and getattr(self, stat_field_name) > 0:
                        self.has_useful_info = True
                        return

                    fieldstate_iterator = fieldstate_iterator + 1

        # We will consider it useful info, if the issue is being monitored or
        # is a part of something that the user has subscribed to, and the user
        # has not yet seen some of its documents or reviews.

        # The option parameter `is_subscribed` is to save this call if it is
        # already known by the calling function.
        if is_subscribed is None:
            is_subscribed = (
                Subscription.objects.filter(
                    Q(committee__issues=self.issue) | Q(category__issues=self.issue),
                    user_id=self.user_id,
                ).count()
                > 0
            )

        # The optional parameter `is_monitored` is to save this call if it is
        # already known by the calling function.
        if is_monitored is None:
            is_monitored = (
                self.issue.issue_monitors.filter(user_id=self.user_id).count() > 0
            )

        counts_differ = any(
            [
                self.document_count != self.issue.document_count,
                self.review_count != self.issue.review_count,
            ]
        )
        if (is_monitored or is_subscribed) and counts_differ:
            self.has_useful_info = True
            return

        # If function hasn't already returned at this point, then nothing useful was found.
        self.has_useful_info = False
        return

    def reset(self):
        for field in self._meta.fields:
            if type(field.default) is int and field.default == 0:
                setattr(self, field.name, field.default)

    def issue_is_new(self):
        # An issue is considered new if no documents or reviews have ever been
        # seen by the user.
        return self.document_count == self.review_count == 0

    def update_stats_quite_inefficiently_please(self, show_output=True):
        """
        WARNING: This function is intended only for diagnostic and data-fixing purposes.
        Do not use it for general production purposes. That would be silly.
        It should not alter data if everything is working as expected.

        Preferably, it should only function as a code-guide to how stats are expected to work.
        """
        # For both 'document' and 'review'
        for dossier_type, dossier_type_name in Dossier.DOSSIER_TYPES:
            for status_type, status_type_name in Dossier.STATUS_TYPES:

                # Figure out which doc-types to exclude, if we're dealing with a document
                exclude_kwargs = (
                    {}
                )  # Will be empty and without effect if nothing is excluded
                excluded_doc_types = []
                if dossier_type == "document":
                    for doc_type in Dossier.DOC_TYPE_EXCLUSIONS:
                        if status_type in Dossier.DOC_TYPE_EXCLUSIONS[doc_type]:
                            excluded_doc_types += [doc_type]
                if len(excluded_doc_types):
                    exclude_kwargs.update(
                        {"document__doc_type__in": excluded_doc_types}
                    )

                fieldstates = "%s_STATES" % status_type.upper()
                for fieldstate, fieldstate_name in getattr(Dossier, fieldstates):
                    stat_field_name = "%s_%s_%s" % (
                        dossier_type,
                        status_type,
                        fieldstate,
                    )
                    if hasattr(self, stat_field_name):
                        kwargs = {
                            "issue_id": self.issue_id,
                            "user_id": self.user_id,
                            "dossier_type": dossier_type,
                            status_type: fieldstate,
                        }
                        count = (
                            Dossier.objects.filter(**kwargs)
                            .exclude(**exclude_kwargs)
                            .count()
                        )
                        if show_output and getattr(self, stat_field_name) != count:
                            print(
                                "(%s, %s) %s: %d"
                                % (self.user, self.issue, stat_field_name, count)
                            )
                        setattr(self, stat_field_name, count)

            count_fieldname = "%s_count" % dossier_type
            count = Dossier.objects.filter(
                issue_id=self.issue_id, user_id=self.user_id, dossier_type=dossier_type
            ).count()
            if show_output and getattr(self, count_fieldname) != count:
                print(
                    "(%s, %s) %s: %d" % (self.user, self.issue, count_fieldname, count)
                )
            setattr(self, count_fieldname, count)

        self.save()
