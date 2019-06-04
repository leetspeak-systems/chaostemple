from django.db import models
from django.db.models import CASCADE
from django.db.models import Case
from django.db.models import Count
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import Prefetch
from django.db.models import PROTECT
from django.db.models import Q
from django.db.models import SET_NULL
from django.db.models import When
from django.template.defaultfilters import capfirst
from django.template.defaultfilters import slugify
from django.templatetags.static import static
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from collections import OrderedDict
from unidecode import unidecode
import urllib

from althingi.althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.exceptions import DataIntegrityException
from althingi.utils import format_date


class IssueQuerySet(models.QuerySet):
    def from_party(self, party):
        return self.filter(
            Q(proposers__person__seats__timing_out__gte=F('time_published'))
            | Q(proposers__person__seats__timing_out=None),
            proposers__person__seats__timing_in__lte=F('time_published'),
            proposers__person__seats__party=party,
            proposers__order=1
        ).distinct()


class PartyQuerySet(models.QuerySet):
    def annotate_mp_counts(self, timing):
        return self.annotate(
            mp_count=Count(
                Case(
                    When(
                        Q(
                            Q(seats__timing_out__gte=timing) | Q(seats__timing_out=None),
                            seats__timing_in__lte=timing,
                            seats__seat_type__in=['þingmaður', 'varamaður'],
                            seats__party_id=F('id')
                        ),
                        then='seats__person_id'
                    ),
                    output_field=IntegerField()
                ),
                distinct=True
            )
        )

class PersonQuerySet(models.QuerySet):
    def prefetch_latest_seats(self, parliament=None, *args):
        if parliament is None:
            parliament = Parliament.objects.get(parliament_num=CURRENT_PARLIAMENT_NUM)

        if parliament.timing_end is None:
            q_timing = Q(timing_out=None) | Q(timing_out__gte=parliament.timing_start, seat_type='varamaður')
        else:
            # NOTE: One day given as wiggle-room due to imperfect data.
            q_timing = Q(
                timing_out__lte=parliament.timing_end + timezone.timedelta(days=1),
                timing_out__gte=parliament.timing_start
            )

        p_filter = Q(q_timing, parliament__parliament_num=parliament.parliament_num)

        if args:
            p_queryset = Seat.objects.select_related(*args).filter(p_filter).order_by('-timing_out')
        else:
            p_queryset = Seat.objects.filter(p_filter).order_by('-timing_out')

        p = Prefetch('seats', queryset=p_queryset, to_attr='last_seat')

        return self.prefetch_related(p)

    def prefetch_latest_president_seats(self, parliament=None, *args):
        if parliament is None:
            parliament = Parliament.objects.get(parliament_num=CURRENT_PARLIAMENT_NUM)

        if parliament.timing_end is None:
            q_timing = Q(timing_out=None)
        else:
            # NOTE: One day given as wiggle-room due to imperfect data.
            q_timing = Q(
                timing_out__lte=parliament.timing_end + timezone.timedelta(days=1),
                timing_out__gte=parliament.timing_end - timezone.timedelta(days=1)
            )

        p_filter = Q(q_timing, parliament__parliament_num=parliament.parliament_num)

        if args:
            p_queryset = PresidentSeat.objects.select_related(*args).filter(p_filter).order_by('-timing_out')
        else:
            p_queryset = PresidentSeat.objects.filter(p_filter).order_by('-timing_out')

        p = Prefetch('president_seats', queryset=p_queryset, to_attr='last_president_seat')

        return self.prefetch_related(p)

    def prefetch_latest_minister_seats(self, parliament=None, *args):
        if parliament is None:
            parliament = Parliament.objects.get(parliament_num=CURRENT_PARLIAMENT_NUM)

        if parliament.timing_end is None:
            q_timing = Q(timing_out=None)
        else:
            # NOTE: One day given as wiggle-room due to imperfect data.
            q_timing = Q(
                timing_out__lte=parliament.timing_end + timezone.timedelta(days=1),
                timing_out__gte=parliament.timing_end - timezone.timedelta(days=1)
            )

        p_filter = Q(q_timing, parliament__parliament_num=parliament.parliament_num)

        if args:
            p_queryset = MinisterSeat.objects.select_related(*args).filter(p_filter).order_by('-timing_out')
        else:
            p_queryset = MinisterSeat.objects.filter(p_filter).order_by('-timing_out')

        p = Prefetch('minister_seats', queryset=p_queryset, to_attr='last_minister_seats')

        return self.prefetch_related(p)

    def prefetch_latest_committee_seats(self, committee, parliament=None, *args):
        if parliament is None:
            parliament = Parliament.objects.get(parliament_num=CURRENT_PARLIAMENT_NUM)

        if parliament.timing_end is None:
            q_timing = Q(timing_out=None)
        else:
            # NOTE: One day given as wiggle-room due to imperfect data.
            q_timing = Q(
                timing_out__lte=parliament.timing_end + timezone.timedelta(days=1),
                timing_out__gte=parliament.timing_start
            )

        p_filter = Q(q_timing, committee=committee, parliament__parliament_num=parliament.parliament_num)

        if args:
            p_queryset = CommitteeSeat.objects.select_related(*args).filter(p_filter).order_by('-timing_out')
        else:
            p_queryset = CommitteeSeat.objects.filter(p_filter).order_by('-timing_out')

        p = Prefetch('seats', queryset=p_queryset, to_attr='last_committee_seat')

        return self.prefetch_related(p)


class PresidentSeatQuerySet(models.QuerySet):
    def main_on_date(self, parliament, dt=None):
        if dt is None:
            dt = timezone.now()

        # Only the main president if one has already been elected. There may
        # be temporary presidential positions ("starfsforseti"), but due to
        # imperfections in the data, this query will not find those. However,
        # those positions should never be relevant to other data since those
        # temporary positions are only active when Parliament has only
        # recently been elected and hasn't started doing anything, so it
        # shouldn't be a problem. Returns None if no president is found.
        query = self.filter(
            president__is_main=True,
            timing_in__gte=parliament.timing_start,
            timing_in__lte=dt
        ).order_by('-timing_in').first()

        return query


class SessionQuerySet(models.QuerySet):
    '''
    ON CODE:
    Sometimes a session is planned immediately following another one.
    In these cases, the first session has timing_start_planned accurately configured,
    but the following session has no timing_start_planned at all (None).
    The only way to determine that such sessions are planned to be held on the same day as the previous one
    is by them having a session_num of the previous session plus one.
    Example:
        Session nr. 112 is planned on a specific day. <- timing_start_planned is accurately configured.
        Session nr. 113 is planned immediately following session nr. 112. <- timing_start_planned is None.

    As a result, to include a session which is following the one requested,
    such as in SessionManager.upcoming() and SessionManager.on_date(), more than one query is required.
    This is undesirable but necessary until the XML properly designates "following session X".
    Currently this is only designated in manually entered text which cannot safely be parsed.
    If you notice that the XML has been updated to solve this problem, please revise this code accordingly.
    '''

    def upcoming(self):
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            next_session = self.select_related('parliament').filter(timing_start_planned__gte=today)[0:1].get()
            return self.filter(
                session_num__gte=next_session.session_num,
                parliament__parliament_num=next_session.parliament.parliament_num
            )

        except Session.DoesNotExist:
            return Session.objects.none()

    def on_date(self, requested_date):
        '''
        ON CODE:
        Because of how session data is provided (see comment in top of class), this function needs to
        execute its database queries immediately. Every retrieved session must be checked to see if
        there is another one following it, so the number of queries executed are number_of_sesssions + 1.
        Improvements are welcomed.
        Note however that the resulting queryset is still chainable and is not executed until used.

        For the sake of clarity and performance, "under the hood" queries are entirely separate from the
        resulting queryset and are therefore called via 'Session.objects' rather than 'self'.
        This does not impact performance since every "under the hood" query needs to be executed anyway.
        In fact, if the main queryset were used and modified a lot before execution, it might negatively
        affect performance.
        '''

        requested_tomorrow = requested_date + timezone.timedelta(days=1)

        # Get first session of day
        first_session = Session.objects.select_related('parliament').filter(
            timing_start_planned__gte=requested_date,
            timing_start_planned__lt=requested_tomorrow
        ).order_by('session_num').first()

        # Return with empty result if no session exists on day
        if first_session is None:
            return Session.objects.none()

        # Collect following sessions
        session_nums = [first_session.session_num]
        next_session = first_session
        while next_session is not None:
            try:
                next_session = Session.objects.select_related('parliament').get(
                    Q(timing_start_planned=None)
                    | Q(timing_start_planned__gte=requested_date, timing_start_planned__lt=requested_tomorrow),
                    parliament__parliament_num=next_session.parliament.parliament_num,
                    session_num=next_session.session_num+1
                )

                session_nums.append(next_session.session_num)
            except Session.DoesNotExist:
                next_session = None
                pass

        # Return a chainable QuerySet object
        return self.filter(
            parliament__parliament_num=first_session.parliament.parliament_num,
            session_num__in=session_nums
        )


class CommitteeAgendaQuerySet(models.QuerySet):
    def upcoming(self):
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        return self.filter(timing_start_planned__gte=today)

    def on_date(self, requested_date):
        requested_tomorrow = requested_date + timezone.timedelta(days=1)

        return self.filter(timing_start_planned__gte=requested_date, timing_start_planned__lt=requested_tomorrow)


class Parliament(models.Model):
    parliament_num = models.IntegerField(unique=True)  # IS: Þingnúmer

    era = models.CharField(max_length=9)
    timing_start = models.DateTimeField()
    timing_end = models.DateTimeField(null=True)

    last_full_update = models.DateTimeField(default=None, null=True)

    def __str__(self):
        return 'Parliament %d' % self.parliament_num

    class Meta:
        ordering = ['-parliament_num']


class Issue(models.Model):
    objects = IssueQuerySet.as_manager()

    ISSUE_TYPES = (
        ('l', 'lagafrumvarp'),
        ('a', 'þingsályktunartillaga'),
        ('q', 'fyrirspurn til skriflegs svars'),
        ('m', 'fyrirspurn'),
        ('b', 'beiðni um skýrslu'),
        ('s', 'skýrsla'),
        ('n', 'álit'),
        ('v', 'vantrauststillaga'),
        ('f', 'frestun á fundum Alþingis'),

        ('al', 'almennar stjórnmálaumræður'),
        ('av', 'ávarp'),
        ('dr', 'drengskaparheit'),
        ('fh', 'framhaldsfundir Alþingis'),
        ('ft', 'óundirbúinn fyrirspurnatími'),
        ('kb', 'rannsókn kjörbréfs'),
        ('ko', 'kosningar'),
        ('mi', 'minning'),
        ('ra', 'stefnuræða forsætisráðherra'),
        ('sr', 'skýrsla ráðherra'),
        ('st', 'störf þingsins'),
        ('sþ', 'munnleg skýrsla þingmanns'),
        ('tk', 'tilkynningar forseta'),
        ('tr', 'tilkynning frá ríkisstjórninni'),
        ('um', 'sérstök umræða'),
        ('yf', 'yfirlýsing forseta'),
        ('þi', 'þingsetning'),
    )

    ISSUE_GROUPS = (
        ('A', 'þingmál með þingskjölum'),
        ('B', 'þingmál án þingskjala'),
    )

    # Issue steps for legal bills.
    ISSUE_STEPS_L = (
        ('distributed', _('Distributed')),
        ('iteration-1-waiting', _('Awaiting 1st debate')),
        ('iteration-1-current', _('Currently in 1st debate')),
        ('iteration-1-finished', _('1st debate concluded')),
        ('committee-1-waiting', _('Sent to committee')),
        ('committee-1-current', _('Currently in committee')),
        ('committee-1-reviews-requested', _('Reviews requested')),
        ('committee-1-reviews-arrived', _('Reviews deadline expired')),
        ('committee-1-finished', _('Considered by committee')),
        ('iteration-2-waiting', _('Awaiting 2nd debate')),
        ('iteration-2-current', _('Currently in 2nd debate')),
        ('iteration-2-finished', _('2nd debate concluded')),
        ('committee-2-waiting', _('Sent to committee (after 2nd debate)')), # Optional
        ('committee-2-current', _('Currently in committee (after 2nd debate)')), # Optional
        ('committee-2-finished', _('Considered by committee (after 2nd debate)')), # Optional
        ('iteration-3-waiting', _('Awaiting 3rd debate')),
        ('iteration-3-current', _('Currently in 3rd debate')),
        ('iteration-3-finished', _('3rd debate concluded')),
        ('concluded', _('Issue concluded')),
    )

    # Issue steps for motions.
    ISSUE_STEPS_A = (
        ('distributed', _('Distributed')),
        ('iteration-former-waiting', _('Awaiting former debate')),
        ('iteration-former-current', _('Currently in former debate')),
        ('iteration-former-finished', _('Former debate concluded')),
        ('committee-former-waiting', _('Sent to committee')),
        ('committee-former-current', _('Currently in committee')),
        ('committee-former-reviews-requested', _('Reviews requested')),
        ('committee-former-reviews-arrived', _('Reviews deadline expired')),
        ('committee-former-finished', _('Considered by committee')),
        ('iteration-latter-waiting', _('Awaiting latter debate')),
        ('iteration-latter-current', _('Currently in latter debate')),
        ('iteration-latter-finished', _('Latter debate concluded')),
        ('concluded', _('Issue concluded')),
    )

    # Issue steps for written inquiries.
    ISSUE_STEPS_Q = (
        ('distributed', _('Distributed')),
        ('answered', _('Answered')),
    )

    # Issue steps for requests for reports.
    ISSUE_STEPS_B = (
        ('distributed', _('Distributed')),
        ('voted-on', _('Voted on')),
        ('report-delivered', _('Report delieverd')),
        ('concluded', _('Concluded')),
    )

    # All issue step definitions combined for use with choices-attribute in fields.
    ISSUE_STEPS = ISSUE_STEPS_L + ISSUE_STEPS_A + ISSUE_STEPS_Q + ISSUE_STEPS_B

    # Issue fates are only applicable when they are concluded.
    ISSUE_FATES = (
        ('rejected', _('rejected')),
        ('accepted', _('accepted')),
        ('sent-to-government', _('sent to government')),
    )

    # Issues that are most relevant to the function of the software.
    MOST_INTERESTING_ISSUE_TYPES = ('l', 'a')

    parliament = models.ForeignKey('Parliament', related_name='issues', on_delete=CASCADE)

    issue_num = models.IntegerField()  # IS: Málsnúmer
    issue_type = models.CharField(max_length=2, choices=ISSUE_TYPES)  # IS: Málstegund
    issue_group = models.CharField(max_length=1, choices=ISSUE_GROUPS, default='A')  # IS: Málsflokkur
    name = models.CharField(max_length=500)
    description = models.TextField()
    categories = models.ManyToManyField('Category', related_name='issues')

    time_published = models.DateTimeField(null=True)
    review_deadline = models.DateTimeField(null=True)

    special_inquisitor = models.ForeignKey(
        'Person',
        null=True,
        related_name='issues_special_inquisited',
        on_delete=CASCADE
    )
    special_inquisitor_description = models.CharField(max_length=50, null=True)
    special_responder = models.ForeignKey(
        'Person',
        null=True,
        related_name='issues_special_responded',
        on_delete=CASCADE
    )
    special_responder_description = models.CharField(max_length=50, null=True)

    previous_issues = models.ManyToManyField('Issue', related_name='future_issues')

    document_count = models.IntegerField(default=0) # Auto-populated by Document.save()
    review_count = models.IntegerField(default=0) # Auto-populated by Review.save()

    to_committee = models.ForeignKey('Committee', null=True, related_name='issues', on_delete=PROTECT)
    to_minister = models.ForeignKey('Minister', null=True, related_name='issues', on_delete=PROTECT)

    current_step = models.CharField(max_length=40, choices=ISSUE_STEPS, null=True)
    fate = models.CharField(max_length=40, choices=ISSUE_FATES, null=True)

    # Django does not appear to support a default order for ManyToMany fields. Thus this fucking shit.
    # (No, I'm not implementing a fucking through-model just to get ordering on ManyToMany fields.)
    def previous_issues_ordered(self):
        return self.previous_issues.order_by('-parliament__parliament_num')

    # Django does not appear to support a default order for ManyToMany fields. Thus this fucking shit.
    # (No, I'm not implementing a fucking through-model just to get ordering on ManyToMany fields.)
    def future_issues_ordered(self):
        return self.future_issues.order_by('parliament__parliament_num')

    def determine_status(self):
        # The overall status of an issue is composed of a sequence of steps.
        # Steps are booleans and a status is a sequential collection of
        # steps.
        #
        # The ISSUE_STEP_MAP describes which steps are relevant to each issue
        # type. An issue type is usually a single-letter code, for example 'l'
        # for a legal bill and 'a' for a motion. Each issue type has a set of
        # steps that describes its corresponding legislative procedure.
        #
        # The map contains ordered dictionaries of codes representing each
        # step (for example, "iteration-1-finished") and a corresponding
        # translatable and human-readable string for displaying in a user
        # interface.
        #
        # In the determine_issue_status function, we find the status of the
        # issue depending on its issue type. First, a clean OrderedDict is
        # created containing all the steps applicable to the issue type, each
        # step with the default value of False, meaning no steps in the
        # legislative process have been taken. Then, an examination of
        # relevant data is conducted, changing each step to True if evidence
        # is found for that step having been taken. For example, a legal
        # bill is in the 1st iteration of discussions ("iteration-1-current")
        # if we find a speech where that issue was discussed and that speech
        # is marked as being in the first iteration. When a final vote on a
        # legal bill is found, the corresponding step ("concluded") has been
        # taken and is therefore marked as True.
        #
        # When taken together, these steps and information on whether they
        # have been taken or not, represent the overall status of the issue.
        ISSUE_STEP_MAP = {
            'l': OrderedDict(self.ISSUE_STEPS_L),
            'a': OrderedDict(self.ISSUE_STEPS_A),
            'q': OrderedDict(self.ISSUE_STEPS_Q),
            'b': OrderedDict(self.ISSUE_STEPS_B),
        }

        # Short-hand.
        now = timezone.now()

        # If we don't know the issue type, there is nothing we can do.
        if self.issue_type not in ISSUE_STEP_MAP:
            return

        # Establish a clean set of steps.
        steps = OrderedDict([(x, False) for x in ISSUE_STEP_MAP[self.issue_type]])

        # Check the steps of a legal bill.
        if self.issue_type == 'l':

            steps['distributed'] = True

            steps['iteration-1-waiting'] = self.session_agenda_items.filter(discussion_type='1').count() > 0

            steps['iteration-1-current'] = self.speeches.filter(iteration='1').count() > 0

            steps['iteration-1-finished'] = self.vote_castings.filter(vote_casting_type='v2').count() > 0

            steps['committee-1-waiting'] = self.vote_castings.filter(vote_casting_type='n2').count() > 0

            steps['committee-1-current'] = self.committee_agenda_items.filter(
                committee_agenda__timing_start_planned__lt=now
            ).count() > 0

            steps['committee-1-reviews-requested'] = self.review_deadline and self.review_deadline > now

            steps['committee-1-reviews-arrived'] = self.review_deadline and self.review_deadline < now

            steps['committee-1-finished'] = self.documents.filter(doc_type__in=[
                'nál. með brtt.',
                'nál. með frávt.',
                'nál. með rökst.',
                'nefndarálit',
            ]).count() > 0

            steps['iteration-2-waiting'] = self.session_agenda_items.filter(discussion_type='2').count() > 0

            steps['iteration-2-current'] = self.speeches.filter(iteration='2').count() > 0

            steps['iteration-2-finished'] = self.vote_castings.filter(vote_casting_type='v3').count() > 0

            try:
                vc = self.vote_castings.get(vote_casting_type='n3')
                steps['committee-2-waiting'] = True

                steps['committee-2-current'] = self.committee_agenda_items.filter(
                    committee_agenda__timing_start__gt=vc.timing
                ).count() > 0

                # NOTE/TODO:
                # This cannot reliably be determined currently, but we try
                # anyway, by checking whether a new committee opinion has been
                # published since the issue was sent to that committee for the
                # second time.
                #
                # Committee opinions are not always published after 2nd
                # committee round. See issue 216/146. This code should be
                # revisited once the XML starts displaying the timing of the
                # committee returning an issue from its 2nd round to iteration
                # 3 ("committee-2-finished"). Such indicators may still be
                # unreliable, but they will still be better to have as well.
                steps['committee-2-finished'] = self.documents.filter(
                    doc_type__in=[
                        'framhaldsnefndarálit',
                        'frhnál. með brtt.',
                        'frhnál. með frávt.',
                        'frhnál. með rökst.',
                        'nál. með brtt.',
                        'nál. með frávt.',
                        'nál. með rökst.',
                        'nefndarálit',
                    ],
                    time_published__gte = vc.timing
                ).count() > 0
            except VoteCasting.DoesNotExist:
                pass

            steps['iteration-3-waiting'] = self.session_agenda_items.filter(discussion_type='3').count() > 0

            steps['iteration-3-current'] = self.speeches.filter(iteration='3').count() > 0

            steps['iteration-3-finished'] = self.vote_castings.filter(vote_casting_type='lg').count() > 0

            # If no one spoke during the first iteration
            # TODO: Check if this scenario is even possible.
            if steps['iteration-1-finished']:
                steps['iteration-1-current'] = True

            # If iteration 2 finished without anyone speaking.
            if steps['iteration-2-finished']:
                steps['iteration-2-current'] = True

            # If iteration 3 has started and the issue was directed to a
            # committee after iteration 2, then the issue should have arrived
            # out of the ocmmittee. Due to imperfect data entry, the data may
            # not necessarily reflect this fact, so it is asserted here.
            if (steps['iteration-3-current'] or steps['iteration-3-finished']) and steps['committee-2-waiting']:
                steps['committee-2-current'] = True
                steps['committee-2-finished'] = True

            # When 3 iterations of a legal bill are complete, the issue is has
            # been concluded on, and discussion ("current") is complete, even
            # if no on ever spoke in iteration 3.
            if steps['iteration-3-finished']:
                steps['iteration-3-current'] = True
                steps['concluded'] = True

            return steps

        elif self.issue_type == 'a':

            steps['distributed'] = True

            steps['iteration-former-waiting'] = self.session_agenda_items.filter(discussion_type='F').count() > 0

            steps['iteration-former-current'] = self.speeches.filter(iteration='F').count() > 0

            steps['iteration-former-finished'] = self.vote_castings.filter(vote_casting_type='vs').count() > 0

            steps['committee-former-waiting'] = self.vote_castings.filter(vote_casting_type='ns').count() > 0

            steps['committee-former-current'] = self.committee_agenda_items.filter(
                committee_agenda__timing_start_planned__lt=now
            ).count() > 0

            steps['committee-former-reviews-requested'] = self.review_deadline and self.review_deadline > now

            steps['committee-former-reviews-arrived'] = self.review_deadline and self.review_deadline < now

            steps['committee-former-finished'] = self.documents.filter(doc_type__in=[
                'nál. með brtt.',
                'nál. með frávt.',
                'nál. með rökst.',
                'nefndarálit',
            ]).count() > 0

            steps['iteration-latter-waiting'] = self.session_agenda_items.filter(discussion_type='S').count() > 0

            steps['iteration-latter-current'] = self.speeches.filter(iteration='S').count() > 0

            steps['iteration-latter-finished'] = self.vote_castings.filter(vote_casting_type='þa').count() > 0

            # If no one spoke during the first iteration
            # TODO: Check if this scenario is even possible.
            if steps['iteration-former-finished']:
                steps['iteration-former-current'] = True

            # If iteration 2 finished without anyone speaking.
            if steps['iteration-latter-finished']:
                steps['iteration-latter-current'] = True
                steps['concluded'] = True

            return steps

        elif self.issue_type == 'q':
            steps['distributed'] = True
            steps['answered'] = self.documents.filter(doc_type='svar').count() > 0
            return steps

        elif self.issue_type == 'b':
            steps['distributed'] = True
            steps['voted-on'] = self.vote_castings.filter(vote_casting_type='bn').count() > 0
            steps['report-delivered'] = self.documents.filter(doc_type='skýrsla (skv. beiðni)').count() > 0

            if steps['report-delivered']:
                steps['concluded'] = True

            return steps

        # We return None to indicate that a status cannot be determined for
        # this issue type yet.
        return None

    # Determine the committee that this issue belongs to, if anyway. In the
    # unlikely and strange but conceivable case of it having been passed to
    # more than one committee, we'll prefer the latest one.
    def determine_committee(self):
        try:
            return self.vote_castings.select_related(
                'to_committee'
            ).exclude(
                to_committee=None
            ).filter(
                Q(conclusion='samþykkt')
                | Q(conclusion=None)
            ).order_by(
                '-timing'
            ).first().to_committee
        except AttributeError:
            return None

    # Determine the minister that this issue was sent to, if anyway. In the
    # unlikely and strange but conceivable case of it having been sent to more
    # than one minister, we'll prefer the latest one.
    def determine_minister(self):
        try:
            return self.vote_castings.select_related(
                'to_minister'
            ).exclude(
                to_minister=None
            ).order_by(
                '-timing'
            ).first().to_minister
        except AttributeError:
            return None

    def determine_fate(self):

        if self.issue_type in ['l', 'a']:

            # Check if issue was sent to government.
            try:
                vote_casting = self.vote_castings.get(vote_casting_type='ft')
                if vote_casting.conclusion == 'samþykkt':
                    return 'sent-to-government'
                # Else nothing. Life goes on.
            except VoteCasting.DoesNotExist:
                pass

            if self.issue_type == 'l':
                # Check if legal bill was accepted as law.
                # NOTE/TODO: Parliament 135 fails if we use a simple .get
                # here, because of a mistaken duplicate of the final vote in
                # issue nr. 90 in the XML. Vote casting nr. 37680 is the
                # problem and should not exist, but because it does, it
                # results in a MltipleObjectsReturned exception. In principle
                # this should be a try/except with a .get function instead of
                # a .filter and .first, but we're taking this route for now to
                # make it compatible with XML that's broken in this way. Note
                # that we assume that the first such vote is the correct one,
                # then. Revisit this if 2018-04-14 was a long time ago.
                vote_casting = self.vote_castings.filter(vote_casting_type='lg').first()
                if vote_casting:
                    if vote_casting.conclusion == 'samþykkt':
                        return 'accepted'
                    elif vote_casting.conclusion == 'Fellt':
                        return 'rejected'
                    else:
                        return 'unknown'

            elif self.issue_type == 'a':
                # Check if proposal for a motion was approved.

                # A funny thing is that apparently separate articles of a
                # motion can be voted on separately without a total vote on
                # the motion in its entirety ever taking place. This happened
                # in issue 692/145. In more technical terms, we might get more
                # than one vote on the same motion. We'll check if votes on
                # all articles agree, and if they do, we'll call it "accepted"
                # and if they don't, we'll say it's "rejected", but if they
                # differ, we'll return "limbo". This is not known to have
                # happened and is extremely unlikely to ever do.

                conclusions = set([vc.conclusion for vc in self.vote_castings.filter(vote_casting_type='þa')])
                if len(conclusions) == 1:
                    conclusion = conclusions.pop()
                    if conclusion == 'samþykkt':
                        return 'accepted'
                    elif conclusion == 'Fellt':
                        return 'rejected'
                    else:
                        return 'unknown'
                elif len(conclusions) > 1:
                    return 'limbo'

        elif self.issue_type == 'b':
            # Check if the request for the report was accepted.
            try:
                vote_casting = self.vote_castings.get(vote_casting_type='bn')
                if vote_casting.conclusion == 'samþykkt':
                    return 'accepted'
                elif vote_casting.conclusion == 'Fellt':
                    return 'rejected'
                else:
                    return 'unknown'
            except VoteCasting.DoesNotExist:
                pass

        return None

    def detailed(self):
        if self.issue_group != 'A':
            return '%s (%d, %s)' % (self, self.issue_num, self.issue_group)
        else:
            return '%s (%d)' % (self, self.issue_num)

    def __str__(self):
        return '%s' % capfirst(self.name)

    class Meta:
        ordering = ['issue_num']
        unique_together = ('parliament', 'issue_num', 'issue_group')


class IssueStep(models.Model):
    issue = models.ForeignKey('Issue', related_name='steps', on_delete=CASCADE)
    code = models.CharField(max_length=50)
    order = models.IntegerField()

    def __str__(self):
        return '%d - %s' % (self.order, self.code)

    class Meta:
        ordering = ['order']


class IssueSummary(models.Model):
    issue = models.OneToOneField('Issue', related_name='summary', on_delete=CASCADE)

    purpose = models.TextField()
    change_description = models.TextField()
    changes_to_law = models.TextField()
    cost_and_revenue = models.TextField()
    other_info = models.TextField()
    review_description = models.TextField()
    fate = models.TextField()
    media_coverage = models.TextField()


class Rapporteur(models.Model):
    issue = models.ForeignKey('Issue', related_name='rapporteurs', on_delete=CASCADE)
    person = models.ForeignKey('Person', related_name='rapporteurs', on_delete=CASCADE)

    def __str__(self):
        return '%s (%s)' % (self.person, self.issue)

    class Meta:
        unique_together = ('issue', 'person')


class Review(models.Model):
    REVIEW_TYPES = (
        ('aa', 'áætlun'),
        ('ab', 'afrit bréfs'),
        ('ak', 'ályktun'),
        ('al', 'álit'),
        ('am', 'almennt'),
        ('as', 'áskorun'),
        ('at', 'athugasemd'),
        ('áu', 'ábending til umfjöllunar'),
        ('be', 'beiðni'),
        ('bk', 'bókun'),
        ('fr', 'frestun á umsögn'),
        ('fs', 'fyrirspurn'),
        ('ft', 'fréttatilkynning'),
        ('fu', 'fundargerð'),
        ('gg', 'greinargerð'),
        ('it', 'ítrekun'),
        ('ka', 'kostnaðaráætlun'),
        ('lf', 'lagt fram á fundi'),
        ('lr', 'leiðrétting'),
        ('mb', 'minnisblað'),
        ('mm', 'mótmæli'),
        ('mt', 'mat'),
        ('na', 'nefndarálit'),
        ('sa', 'samþykkt'),
        ('se', 'stuðningserindi'),
        ('sk', 'skýrsla'),
        ('su', 'skýrsla til umfjöllunar'),
        ('tk', 'tilkynning'),
        ('tl', 'tillaga'),
        ('tm', 'tilmæli'),
        ('ub', 'umsögn'),
        ('uk', 'umsókn'),
        ('up', 'upplýsingar'),
        ('vb', 'viðbótarumsögn'),
        ('vi', 'viðauki'),
        ('vs', 'vinnuskjal'),
        ('xx', 'x'),
        ('yf', 'yfirlit'),
        ('yg', 'ýmis gögn'),
        ('ys', 'yfirlýsing'),
    )

    issue = models.ForeignKey('Issue', related_name='reviews', on_delete=CASCADE)
    log_num = models.IntegerField()  # IS: Dagbókarnúmer
    sender_name = models.CharField(max_length=200)
    sender_name_description = models.CharField(max_length=200, default='')
    committee = models.ForeignKey('Committee', null=True, on_delete=SET_NULL)
    president_seat = models.ForeignKey('PresidentSeat', null=True, on_delete=SET_NULL) # Unusual but possible
    review_type = models.CharField(max_length=2, choices=REVIEW_TYPES)  #: Tegund erindis
    date_arrived = models.DateField(null=True)
    date_sent = models.DateField(null=True)
    pdf_remote_path = models.CharField(max_length=500, null=True)
    pdf_filename = models.CharField(max_length=50)

    def pdf_link(self):
        if self.pdf_filename:
            return static(self.pdf_filename)
        else:
            return self.pdf_remote_path

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super(Review, self).save(*args, **kwargs)

        # Re-calculate Issue's Review count
        if is_new:
            self.issue.review_count = Review.objects.filter(issue=self.issue).count()
            self.issue.save()

    def delete(self):
        try:
            # Force a pre_delete signal being sent before we attempt to
            # delete, since Django doesn't still send the signal before
            # collecting related objects that will prevent deletion. This
            # means that the pre_delete signal is sent twice. We recklessly
            # assume that's not a problem. (Django 1.11.9)
            # The importing is done here because this should be removed when
            # Django changes in such a way that pre_delete is sent before
            # collecting related objects.
            from django.db.models.signals import pre_delete
            pre_delete.send(Review, instance=self)

            super(Review, self).delete()
        except models.deletion.ProtectedError:

            msg = 'Attempted to remove a review with referenced data:'
            msg += ' issue_id = %d' % self.issue_id
            msg += ', review_id = %d' % self.id
            msg += ', issue_name = "%s"' % self.issue.name
            msg += ', review_sender_name = "%s"' % self.sender_name
            msg += ', review_log_num = %d' % self.log_num

            raise DataIntegrityException(msg.encode('utf-8'))

        # Re-calculate Issue's Review count
        self.issue.review_count = Review.objects.filter(issue=self.issue).count()
        self.issue.save()

    def __str__(self):
        return u"%s (%s)" % (self.sender_name, self.date_arrived)

    class Meta:
        ordering = ['sender_name', 'date_arrived', 'log_num']
        unique_together = ('issue', 'log_num')


class Document(models.Model):
    DOCUMENT_TYPES = (
        ('álit nefndar um skýrslu', 'álit nefndar um skýrslu'),
        ('beiðni um skýrslu', 'beiðni um skýrslu'),
        ('breytingartillaga', 'breytingartillaga'),
        ('framhaldsnefndarálit', 'framhaldsnefndarálit'),
        ('frávísunartilllaga', 'frávísunartilllaga'),
        ('frestun funda', 'frestun funda'),
        ('frumvarp', 'frumvarp'),
        ('frhnál. með brtt.', 'framhaldsnefndarálit með breytingartillögu'),
        ('frhnál. með frávt.', 'framhaldsnefndarálit með frávísunartillögu'),
        ('frhnál. með rökst.', 'framhaldsnefndarálit með rökstuðningi'),
        ('frumvarp eftir 2. umræðu', 'frumvarp eftir 2. umræðu'),
        ('frumvarp nefndar', 'frumvarp nefndar'),
        ('frv. til. stjórnarsk.', 'frumvarp til stjórnarskrár'),
        ('fsp. til munnl. svars', 'fyrirspurn til munnlegs svars'),
        ('fsp. til skrifl. svars', 'fyrirspurn til skriflegs svars'),
        ('lög (m.áo.br.)', 'lög (með áorðnum breytingum'),
        ('lög (samhlj.)', 'lög (samhljóða)'),
        ('lög í heild', 'lög í heild'),
        ('nál. með brtt.', 'nefndarálit með breytingartillögu'),
        ('nál. með frávt.', 'nefndarálit með frávísunartillögu'),
        ('nál. með rökst.', 'nefndarálit með rökstuðningi'),
        ('nefndarálit', 'nefndarálit'),
        ('rökstudd dagskrá', 'rökstudd dagskrá'),
        ('skýrsla (skv. beiðni)', 'skýrsla (samkvæmt beiðni)'),
        ('skýrsla n.', 'skýrsla nefndar'),
        ('skýrsla n. (frumskjal)', 'skýrsla nefndar (frumskjal)'),
        ('skýrsla rh. (frumskjal)', 'skýrsla ráðherra (frumskjal)'),
        ('stjórnarfrumvarp', 'stjórnarfrumvarp'),
        ('stjórnartillaga', 'stjórnartillaga'),
        ('svar', 'svar'),
        ('vantraust', 'vantraust'),
        ('þál. (samhlj.)', 'þingsályktunartillaga (samhljóða)'),
        ('þál. í heild', 'þingsályktunartillaga í heild'),
        ('þáltill.', 'þingsályktunartillaga'),
        ('þáltill. n.', 'þingsályktunartillaga nefndar'),
    )

    issue = models.ForeignKey('Issue', related_name='documents', on_delete=CASCADE)

    doc_num = models.IntegerField()
    doc_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    time_published = models.DateTimeField()
    is_main = models.BooleanField(default=False)

    html_remote_path = models.CharField(max_length=500, null=True)
    html_filename = models.CharField(max_length=50)
    pdf_remote_path = models.CharField(max_length=500, null=True)
    pdf_filename = models.CharField(max_length=50)

    xhtml = models.TextField()

    def html_link(self):
        if self.html_filename:
            return static(self.html_filename)
        else:
            return self.html_remote_path

    def pdf_link(self):
        if self.pdf_filename:
            return static(self.pdf_filename)
        else:
            return self.pdf_remote_path

    def preferred_link(self):
        preferred = self.html_link()
        if not preferred:
            preferred = self.pdf_link()
        return preferred

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super(Document, self).save(*args, **kwargs)

        # If this is a main document, then the issue's publishing date should be the same.
        if self.is_main and self.issue.time_published != self.time_published:
            self.issue.time_published = self.time_published
            self.issue.save()

        # Re-calculate Issue's Document count
        if is_new:
            self.issue.document_count = Document.objects.filter(issue=self.issue).count()
            self.issue.save()

    def delete(self):
        super(Document, self).delete()
        # Re-calculate Issue's Document count
        self.issue.document_count = Document.objects.filter(issue=self.issue).count()
        self.issue.save()

    def __str__(self):
        return '%d (%s)' % (self.doc_num, self.doc_type)

    class Meta:
        ordering = ['doc_num']
        unique_together = ('issue', 'doc_num')


class Proposer(models.Model):
    issue = models.ForeignKey('Issue', null=True, related_name='proposers', on_delete=CASCADE)
    document = models.ForeignKey('Document', null=True, related_name='proposers', on_delete=CASCADE)
    order = models.IntegerField(null=True)
    person = models.ForeignKey('Person', null=True, on_delete=CASCADE)
    committee = models.ForeignKey('Committee', null=True, on_delete=CASCADE)
    committee_partname = models.CharField(max_length=50, null=True) # Only non-None if committee is non-None
    parent = models.ForeignKey('Proposer', null=True, related_name='subproposers', on_delete=CASCADE)

    def save(self, *args, **kwargs):
        if self.document_id and self.document.is_main:
            self.issue_id = self.document.issue_id
        else:
            self.issue_id = None

        super(Proposer, self).save(*args, **kwargs)

    def __str__(self):
        if self.person_id is not None:
            return self.person.__str__()
        elif self.committee_id is not None:
            if self.committee_partname:
                return "%s (%s)" % (self.committee.__str__(), self.committee_partname)
            else:
                return self.committee.__str__()
        else:
            return 'N/A'

    class Meta:
        ordering = ['order']
        unique_together = ('issue', 'person', 'committee', 'order')


class Committee(models.Model):

    NON_STANDING_COMMITTIES = (
        'forsætisnefnd',
        'Íslandsdeild Alþjóðaþingmannasambandsins',
        'Íslandsdeild Evrópuráðsþingsins',
        'Íslandsdeild NATO-þingsins',
        'Íslandsdeild Norðurlandaráðs',
        'Íslandsdeild Vestnorræna ráðsins',
        'Íslandsdeild Vestur-Evrópusambandsins',
        'Íslandsdeild þingmannanefnda EFTA og EES',
        'Íslandsdeild þingmannanefndar EFTA',
        'Íslandsdeild þingmannaráðstefnunnar um norðurskautsmál',
        'Íslandsdeild þings Öryggis- og samvinnustofnunar Evrópu',
        'kjörbréfanefnd',
        'sérnefnd um stjórnarskrármál',
        'sérnefnd um stjórnarskrármál (385. mál á 136. þingi)',
        'starfshópur utanríkismálanefndar um Evrópumál',
        'Þingmannanefnd Íslands og Evrópusambandsins af hálfu Alþingis',
        'þingmannanefnd til að fjalla um skýrslu rannsóknarnefndar Alþingis',
        'þingskapanefnd',
    )

    name = models.CharField(max_length=100)
    abbreviation_short = models.CharField(max_length=20)
    abbreviation_long = models.CharField(max_length=30)

    parliament_num_first = models.IntegerField()
    parliament_num_last = models.IntegerField(null=True)
    parliaments = models.ManyToManyField('Parliament', related_name='committees')

    committee_xml_id = models.IntegerField(unique=True)

    is_standing = models.BooleanField(default=True)

    def __str__(self):
        return capfirst(self.name)

    def save(self, *args, **kwargs):
        self.is_standing = self.name not in Committee.NON_STANDING_COMMITTIES
        super(Committee, self).save(*args, **kwargs)

    class Meta:
        ordering = ['name']


class Person(models.Model):
    objects = PersonQuerySet.as_manager()

    name = models.CharField(max_length=100)
    ssn = models.CharField(max_length=10)
    birthdate = models.DateField()

    email = models.EmailField(null=True)
    facebook_url = models.URLField(null=True)
    twitter_url = models.URLField(null=True)
    youtube_url = models.URLField(null=True)
    blog_url = models.URLField(null=True)
    website_url = models.URLField(null=True)

    slug = models.CharField(max_length=100)
    subslug = models.CharField(max_length=10, null=True)

    person_xml_id = models.IntegerField(unique=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(unidecode(self.name))
        self.subslug = 'f-%d' % self.birthdate.year

        super(Person, self).save(*args, **kwargs)

    def __str__(self):
        return '%s' % self.name

    class Meta:
        ordering = ['name']


class Minister(models.Model):
    name = models.CharField(max_length=100)

    abbreviation_short = models.CharField(max_length=20)
    abbreviation_long = models.CharField(max_length=30)

    parliament_num_first = models.IntegerField()
    parliament_num_last = models.IntegerField(null=True)
    parliaments = models.ManyToManyField('Parliament', related_name='ministers')

    minister_xml_id = models.IntegerField(unique=True)

    def __str__(self):
        return '%s' % self.name

    class Meta:
        ordering = ['name']


class MinisterSeat(models.Model):
    person = models.ForeignKey('Person', related_name='minister_seats', on_delete=CASCADE)
    minister = models.ForeignKey('Minister', related_name='minister_seats', on_delete=CASCADE)
    parliament = models.ForeignKey('Parliament', related_name='minister_seats', on_delete=CASCADE)

    timing_in = models.DateTimeField()
    timing_out = models.DateTimeField(null=True)

    party = models.ForeignKey('Party', null=True, related_name='minister_seats', on_delete=CASCADE)

    def __str__(self):
        if self.timing_out is None:
            return '%s (%s, %s : ...)' % (self.person, self.minister, format_date(self.timing_in))
        else:
            # Short-hands
            person = self.person
            minister = self.minister
            timing_in = self.timing_in
            timing_out = self.timing_out
            return '%s (%s, %s : %s)' % (person, minister, format_date(timing_in), format_date(timing_out))

    class Meta:
        ordering = ['timing_in', 'timing_out']


class President(models.Model):
    name = models.CharField(max_length=100)

    abbreviation = models.CharField(max_length=30)
    president_type = models.CharField(max_length=3)

    is_main = models.BooleanField(default=False)
    order = models.IntegerField(null=True) # Order of succession; not always relevant.

    parliaments = models.ManyToManyField('Parliament', related_name='presidents')

    president_xml_id = models.IntegerField(unique=True)

    def __str__(self):
        return capfirst(self.name)

    class Meta:
        ordering = ['president_type', 'order']


class PresidentSeat(models.Model):
    objects = PresidentSeatQuerySet.as_manager()

    person = models.ForeignKey('Person', related_name='president_seats', on_delete=CASCADE)
    president = models.ForeignKey('President', related_name='president_seats', on_delete=CASCADE)
    parliament = models.ForeignKey('Parliament', related_name='president_seats', on_delete=CASCADE)

    timing_in = models.DateTimeField()
    timing_out = models.DateTimeField(null=True)

    def __str__(self):
        if self.timing_out is None:
            return '%s (%s, %s : ...)' % (self.person, self.president, format_date(self.timing_in))
        else:
            # Short-hands
            person = self.person
            president = self.president
            timing_in = self.timing_in
            timing_out = self.timing_out
            return '%s (%s, %s : %s)' % (person, president, format_date(timing_in), format_date(timing_out))

    class Meta:
        ordering = ['president__order', 'timing_in']


class Session(models.Model):
    objects = SessionQuerySet.as_manager()

    parliament = models.ForeignKey('Parliament', related_name='sessions', on_delete=CASCADE)
    session_num = models.IntegerField()
    name = models.CharField(max_length=30)
    timing_start_planned = models.DateTimeField(null=True)
    timing_start = models.DateTimeField(null=True)
    timing_end = models.DateTimeField(null=True)
    timing_text = models.CharField(max_length=200, null=True)

    def __str__(self):
        return '%s' % self.name

    class Meta:
        ordering = ['session_num']
        unique_together = ('parliament', 'session_num')


class SessionAgendaItem(models.Model):
    DISCUSSION_TYPES = (
        ('*', ''),
        ('0', ''),
        ('1', '1. umræða'),
        ('2', '2. umræða'),
        ('3', '3. umræða'),
        ('E', 'ein umræða'),
        ('F', 'fyrri umræða'),
        ('S', 'síðari umræða'),
    )

    session = models.ForeignKey('Session', related_name='session_agenda_items', on_delete=CASCADE)
    order = models.IntegerField()
    discussion_type = models.CharField(max_length=1, choices=DISCUSSION_TYPES)
    discussion_continued = models.BooleanField(default=False)
    comment_type = models.CharField(max_length=1, null=True)
    comment_text = models.CharField(max_length=100, null=True)
    comment_description = models.CharField(max_length=100, null=True)
    issue = models.ForeignKey('Issue', null=True, related_name='session_agenda_items', on_delete=CASCADE)

    def __str__(self):
        return '%d. %s' % (self.order, self.issue.detailed())

    class Meta:
        ordering = ['order']
        unique_together = ('session', 'order')


class CommitteeAgenda(models.Model):
    objects = CommitteeAgendaQuerySet.as_manager()

    parliament = models.ForeignKey('Parliament', related_name='committee_agendas', on_delete=CASCADE)
    committee = models.ForeignKey('Committee', related_name='committee_agendas', on_delete=CASCADE)
    timing_start_planned = models.DateTimeField(null=True)
    timing_start = models.DateTimeField(null=True)
    timing_end = models.DateTimeField(null=True)
    timing_text = models.CharField(max_length=200, null=True)

    committee_agenda_xml_id = models.IntegerField(unique=True)

    def __str__(self):
        return '%s @ %s' % (self.committee, self.timing_start_planned)

    class Meta:
        ordering = ['timing_start_planned', 'committee__name']


class CommitteeAgendaItem(models.Model):
    committee_agenda = models.ForeignKey('CommitteeAgenda', related_name='committee_agenda_items', on_delete=CASCADE)
    order = models.IntegerField()
    name = models.CharField(max_length=300)
    issue = models.ForeignKey('Issue', null=True, related_name='committee_agenda_items', on_delete=CASCADE)

    def __str__(self):
        if self.issue is not None:
            return '%d. %s' % (self.order, self.issue.detailed())
        else:
            return '%d. %s' % (self.order, self.name)

    class Meta:
        ordering = ['order']
        unique_together = ('committee_agenda', 'order')


class Party(models.Model):
    objects = PartyQuerySet.as_manager()

    name = models.CharField(max_length=50)
    abbreviation_short = models.CharField(max_length=20)
    abbreviation_long = models.CharField(max_length=30)

    parliament_num_first = models.IntegerField()
    parliament_num_last = models.IntegerField(null=True)
    parliaments = models.ManyToManyField('Parliament', related_name='parties')

    special = models.BooleanField(default=False)

    slug = models.CharField(max_length=100)

    party_xml_id = models.IntegerField(unique=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(unidecode(self.name))

        # Special parties are party-type containers rather than actual parties.
        if self.name == 'Utan þingflokka':
            self.special = True

        super(Party, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['special', 'name']


class Constituency(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    abbreviation_short = models.CharField(max_length=20)
    abbreviation_long = models.CharField(max_length=30, null=True)

    parliament_num_first = models.IntegerField()
    parliament_num_last = models.IntegerField(null=True)
    parliaments = models.ManyToManyField('Parliament', related_name='constituencies')

    constituency_xml_id = models.IntegerField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Seat(models.Model):
    SEAT_TYPES = (
        ('þingmaður', 'þingmaður'),
        ('varamaður', 'varamaður'),
        ('með varamann', 'með varamann'),
    )

    person = models.ForeignKey('Person', related_name='seats', on_delete=CASCADE)
    parliament = models.ForeignKey('Parliament', related_name='seats', on_delete=CASCADE)
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPES)

    name_abbreviation = models.CharField(max_length=15, default="") # abbreviations may change by term
    physical_seat_number = models.IntegerField(default=0, null=True) # This is where MP physically sits, not electoral seat

    timing_in = models.DateTimeField()
    timing_out = models.DateTimeField(null=True)

    constituency = models.ForeignKey('Constituency', related_name='seats', on_delete=CASCADE)
    constituency_mp_num = models.PositiveSmallIntegerField()

    party = models.ForeignKey('Party', related_name='seats', on_delete=CASCADE)

    def tenure_ended_prematurely(self):
        p = self.parliament # Short-hand
        return self.seat_type in ('þingmaður', 'með varamann') and (
            (self.timing_out is not None and p.timing_end is None)
            or (p.timing_end is not None and self.timing_out < p.timing_end - timezone.timedelta(days=1))
        )

    def __str__(self):
        if self.timing_out is None:
            return '%s (%s : ...)' % (self.person, format_date(self.timing_in))
        else:
            return '%s (%s : %s)' % (self.person, format_date(self.timing_in), format_date(self.timing_out))

    class Meta:
        ordering = ['timing_in', 'timing_out']


class CommitteeSeat(models.Model):
    COMMITTEE_SEAT_TYPES = (
        ('nefndarmaður', 'nefndarmaður'),
        ('varamaður', 'varamaður'),
        ('kjörinn varamaður', 'kjörinn varamaður'),
        ('formaður', 'formaður'),
        ('1. varaformaður', '1. varaformaður'),
        ('2. varaformaður', '2. varaformaður'),
        ('áheyrnarfulltrúi', 'áheyrnarfulltrúi'),
    )

    person = models.ForeignKey('Person', related_name='committee_seats', on_delete=CASCADE)
    committee = models.ForeignKey('Committee', related_name='committee_seats', on_delete=CASCADE)
    parliament = models.ForeignKey('Parliament', related_name='committee_seats', on_delete=CASCADE)
    committee_seat_type = models.CharField(max_length=20, choices=COMMITTEE_SEAT_TYPES)
    order = models.IntegerField()

    timing_in = models.DateTimeField()
    timing_out = models.DateTimeField(null=True)

    def __str__(self):
        if self.timing_out is None:
            return '%s (%s, %s : ...)' % (self.person, self.committee, format_date(self.timing_in))
        else:
            # Short-hands
            person = self.person
            committee = self.committee
            timing_in = self.timing_in
            timing_out = self.timing_out
            return '%s (%s, %s : %s)' % (person, committee, format_date(timing_in), format_date(timing_out))

    class Meta:
        ordering = ['timing_in', 'timing_out']


class VoteCasting(models.Model):
    timing = models.DateTimeField()
    vote_casting_type = models.CharField(max_length=2)
    vote_casting_type_text = models.CharField(max_length=100)
    specifics = models.CharField(max_length=100)

    method = models.CharField(max_length=50, null=True)
    count_yes = models.IntegerField(null=True)
    count_no = models.IntegerField(null=True)
    count_abstain = models.IntegerField(null=True)
    conclusion = models.CharField(max_length=100, null=True)

    issue = models.ForeignKey('Issue', null=True, related_name='vote_castings', on_delete=CASCADE)
    document = models.ForeignKey('Document', null=True, related_name='vote_castings', on_delete=CASCADE)
    session = models.ForeignKey('Session', related_name='vote_castings', on_delete=CASCADE)

    to_committee = models.ForeignKey('Committee', null=True, related_name='vote_castings', on_delete=CASCADE)
    to_minister = models.ForeignKey('Minister', null=True, related_name='vote_castings', on_delete=CASCADE)

    vote_casting_xml_id = models.IntegerField(unique=True)

    def __str__(self):
        if self.specifics:
            return '%s (%s), %s @ %s' % (self.vote_casting_type_text, self.specifics, self.method, self.timing)
        else:
            return '%s, %s @ %s' % (self.vote_casting_type_text, self.method, self.timing)

    class Meta:
        ordering = ['timing']


class Vote(models.Model):
    VOTE_RESPONSES = (
        ('já', 'já'),
        ('nei', 'nei'),
        ('fjarverandi', 'fjarverandi'),
        ('boðaði fjarvist', 'boðaði fjarvist'),
        ('greiðir ekki atkvæði', 'greiðir ekki atkvæði'),
    )

    vote_casting = models.ForeignKey('VoteCasting', related_name='votes', on_delete=CASCADE)
    vote_response = models.CharField(max_length=20, choices=VOTE_RESPONSES)
    person = models.ForeignKey('Person', related_name='votes', on_delete=CASCADE)

    def __str__(self):
        return '%s: %s' % (self.person, self.vote_response)

    class Meta:
        unique_together = ('vote_casting', 'person')


class Speech(models.Model):
    person = models.ForeignKey('Person', related_name='speeches', on_delete=CASCADE)
    session = models.ForeignKey('Session', related_name='speeches', on_delete=CASCADE)
    issue = models.ForeignKey('Issue', null=True, related_name='speeches', on_delete=CASCADE)

    date = models.DateTimeField()
    timing_start = models.DateTimeField()
    timing_end = models.DateTimeField()
    seconds = models.IntegerField()

    speech_type = models.CharField(max_length=30)
    president = models.BooleanField(default=False)
    iteration = models.CharField(max_length=3, null=True)

    order_in_issue = models.IntegerField(null=True)

    html_remote_path = models.CharField(max_length=500, null=True)
    sgml_remote_path = models.CharField(max_length=500, null=True)
    xml_remote_path = models.CharField(max_length=500, null=True)
    text_remote_path = models.CharField(max_length=500, null=True)
    sound_remote_path = models.CharField(max_length=500, null=True)

    def __str__(self):
        return '%s @ %s' % (self.person, self.timing_start.strftime('%Y-%m-%d %H:%M:%S'))

    class Meta:
        ordering = ['timing_start']


class CategoryGroup(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)

    category_group_xml_id = models.IntegerField(unique=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(unidecode(self.name))
        super(CategoryGroup, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.CharField(max_length=200)
    description = models.CharField(max_length=1000)
    group = models.ForeignKey('CategoryGroup', related_name='categories', on_delete=CASCADE)

    category_xml_id = models.IntegerField(unique=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(unidecode(self.name))
        super(Category, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
