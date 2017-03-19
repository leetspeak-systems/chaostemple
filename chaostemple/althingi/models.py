# -*- coding: utf-8
from django.db import models
from django.db.models import Case
from django.db.models import Count
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import When
from django.template.defaultfilters import capfirst
from django.template.defaultfilters import slugify
from django.templatetags.static import static
from django.utils import timezone

from BeautifulSoup import BeautifulSoup
from unidecode import unidecode
import urllib

from althingi_settings import CURRENT_PARLIAMENT_NUM
from althingi.utils import format_date

class PartyQuerySet(models.QuerySet):
    def annotate_mp_counts(self, timing):
        return self.annotate(
            mp_count=Count(
                Case(
                    When(
                        Q(
                            Q(seats__timing_out__gte=timing) | Q(seats__timing_out=None),
                            seats__timing_in__lte=timing,
                            seats__seat_type__in=[u'þingmaður', u'varamaður'],
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
            parliament = Parliament.objects.get(CURRENT_PARLIAMENT_NUM)

        if parliament.timing_end is None:
            q_timing = Q(timing_out=None)
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

    def __unicode__(self):
        return u'Parliament %d' % self.parliament_num


class Issue(models.Model):
    ISSUE_TYPES = (
        (u'l', u'lagafrumvarp'),
        (u'a', u'þingsályktunartillaga'),
        (u'm', u'fyrirspurn'),
        (u'q', u'fyrirspurn til skriflegs svars'),
        (u's', u'skýrsla'),
        (u'b', u'beiðni um skýrslu'),
        (u'f', u'frestun á fundum Alþingis'),
        (u'n', u'álit'),
        (u'v', u'vantrauststillaga'),

        (u'al', u'almennar stjórnmálaumræður'),
        (u'av', u'ávarp'),
        (u'dr', u'drengskaparheit'),
        (u'fh', u'framhaldsfundir Alþingis'),
        (u'ft', u'óundirbúinn fyrirspurnatími'),
        (u'kb', u'rannsókn kjörbréfs'),
        (u'ko', u'kosningar'),
        (u'mi', u'minning'),
        (u'ra', u'stefnuræða forsætisráðherra'),
        (u'sr', u'skýrsla ráðherra'),
        (u'st', u'störf þingsins'),
        (u'sþ', u'munnleg skýrsla þingmanns'),
        (u'tk', u'tilkynningar forseta'),
        (u'tr', u'tilkynning frá ríkisstjórninni'),
        (u'um', u'sérstök umræða'),
        (u'yf', u'yfirlýsing forseta'),
        (u'þi', u'þingsetning'),
    )

    ISSUE_GROUPS = (
        (u'A', u'þingmál með þingskjölum'),
        (u'B', u'þingmál án þingskjala'),
    )

    parliament = models.ForeignKey('Parliament')

    issue_num = models.IntegerField()  # IS: Málsnúmer
    issue_type = models.CharField(max_length=2, choices=ISSUE_TYPES)  # IS: Málstegund
    issue_group = models.CharField(max_length=1, choices=ISSUE_GROUPS, default='A')  # IS: Málsflokkur
    name = models.CharField(max_length=500)
    description = models.TextField()
    time_published = models.DateTimeField(null=True)
    final_vote_complete = models.BooleanField(default=False)

    special_inquisitor = models.ForeignKey('Person', null=True, related_name='issues_special_inquisited')
    special_inquisitor_description = models.CharField(max_length=50, null=True)
    special_responder = models.ForeignKey('Person', null=True, related_name='issues_special_responded')
    special_responder_description = models.CharField(max_length=50, null=True)

    previous_issues = models.ManyToManyField('Issue', related_name='future_issues')

    document_count = models.IntegerField(default=0) # Auto-populated by Issue.save()
    review_count = models.IntegerField(default=0) # Auto-populated by Review.save()

    # Django does not appear to support a default order for ManyToMany fields. Thus this fucking shit.
    # (No, I'm not implementing a fucking through-model just to get ordering on ManyToMany fields.)
    def previous_issues_ordered(self):
        return self.previous_issues.order_by('-parliament__parliament_num')

    # Django does not appear to support a default order for ManyToMany fields. Thus this fucking shit.
    # (No, I'm not implementing a fucking through-model just to get ordering on ManyToMany fields.)
    def future_issues_ordered(self):
        return self.future_issues.order_by('parliament__parliament_num')

    def detailed(self):
        if self.issue_group != 'A':
            return u'%s (%d, %s)' % (self, self.issue_num, self.issue_group)
        else:
            return u'%s (%d)' % (self, self.issue_num)

    def __unicode__(self):
        return u'%s' % capfirst(self.name)

    class Meta:
        ordering = ['issue_num']


class IssueSummary(models.Model):
    issue = models.OneToOneField('Issue', related_name='summary')

    purpose = models.TextField()
    change_description = models.TextField()
    changes_to_law = models.TextField()
    cost_and_revenue = models.TextField()
    other_info = models.TextField()
    review_description = models.TextField()
    fate = models.TextField()
    media_coverage = models.TextField()


class Review(models.Model):
    REVIEW_TYPES = (
        (u'aa', u'áætlun'),
        (u'ab', u'afrit bréfs'),
        (u'ak', u'ályktun'),
        (u'al', u'álit'),
        (u'am', u'almennt'),
        (u'as', u'áskorun'),
        (u'at', u'athugasemd'),
        (u'áu', u'ábending til umfjöllunar'),
        (u'be', u'beiðni'),
        (u'bk', u'bókun'),
        (u'fr', u'frestun á umsögn'),
        (u'fs', u'fyrirspurn'),
        (u'ft', u'fréttatilkynning'),
        (u'fu', u'fundargerð'),
        (u'gg', u'greinargerð'),
        (u'it', u'ítrekun'),
        (u'ka', u'kostnaðaráætlun'),
        (u'lf', u'lagt fram á fundi'),
        (u'lr', u'leiðrétting'),
        (u'mb', u'minnisblað'),
        (u'mm', u'mótmæli'),
        (u'mt', u'mat'),
        (u'na', u'nefndarálit'),
        (u'sa', u'samþykkt'),
        (u'se', u'stuðningserindi'),
        (u'sk', u'skýrsla'),
        (u'su', u'skýrsla til umfjöllunar'),
        (u'tk', u'tilkynning'),
        (u'tl', u'tillaga'),
        (u'tm', u'tilmæli'),
        (u'ub', u'umsögn'),
        (u'uk', u'umsókn'),
        (u'up', u'upplýsingar'),
        (u'vb', u'viðbótarumsögn'),
        (u'vi', u'viðauki'),
        (u'vs', u'vinnuskjal'),
        (u'xx', u'x'),
        (u'yf', u'yfirlit'),
        (u'yg', u'ýmis gögn'),
        (u'ys', u'yfirlýsing'),
    )

    issue = models.ForeignKey('Issue', related_name='reviews')
    log_num = models.IntegerField()  # IS: Dagbókarnúmer
    sender_name = models.CharField(max_length=200)
    sender_name_description = models.CharField(max_length=200, default='')
    committee = models.ForeignKey('Committee', null=True)
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
        super(Review, self).delete()
        # Re-calculate Issue's Review count
        self.issue.review_count = Review.objects.filter(issue=self.issue).count()
        self.issue.save()

    def __unicode__(self):
        return u"%s (%s)" % (self.sender_name, self.date_arrived)

    class Meta:
        ordering = ['sender_name', 'date_arrived', 'log_num']


class Document(models.Model):
    DOCUMENT_TYPES = (
        (u'beiðni um skýrslu', u'beiðni um skýrslu'),
        (u'breytingartillaga', u'breytingartillaga'),
        (u'frumvarp', u'frumvarp'),
        (u'frumvarp eftir 2. umræðu', u'frumvarp eftir 2. umræðu'),
        (u'frumvarp nefndar', u'frumvarp nefndar'),
        (u'fsp. til munnl. svars', u'fyrirspurn til munnlegs svars'),
        (u'fsp. til skrifl. svars', u'fyrirspurn til skriflegs svars'),
        (u'lög (samhlj.)', u'lög (samhljóða)'),
        (u'lög í heild', u'lög í heild'),
        (u'nál. með brtt.', u'nefndarálit með breytingartillögu'),
        (u'nefndarálit', u'nefndarálit'),
        (u'skýrsla n. (frumskjal)', u'skýrsla nefndar (frumskjal)'),
        (u'skýrsla rh. (frumskjal)', u'skýrsla ráðherra (frumskjal)'),
        (u'stjórnarfrumvarp', u'stjórnarfrumvarp'),
        (u'stjórnartillaga', u'stjórnartillaga'),
        (u'svar', u'svar'),
        (u'þál. (samhlj.)', u'þingsályktunartillaga (samhljóða)'),
        (u'þál. í heild', u'þingsályktunartillaga í heild'),
        (u'þáltill.', u'þingsályktunartillaga'),
        (u'þáltill. n.', u'þingsályktunartillaga nefndar'),
    )

    issue = models.ForeignKey('Issue', related_name='documents')

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

    def __unicode__(self):
        return u'%d (%s)' % (self.doc_num, self.doc_type)

    class Meta:
        ordering = ['doc_num']


class Proposer(models.Model):
    issue = models.ForeignKey('Issue', null=True, related_name='proposers')
    document = models.ForeignKey('Document', null=True, related_name='proposers')
    order = models.IntegerField(null=True)
    person = models.ForeignKey('Person', null=True)
    committee = models.ForeignKey('Committee', null=True)
    committee_partname = models.CharField(max_length=50, null=True) # Only non-None if committee is non-None
    parent = models.ForeignKey('Proposer', null=True, related_name='subproposers')

    def save(self, *args, **kwargs):
        if self.document_id and self.document.is_main:
            self.issue_id = self.document.issue_id
        else:
            self.issue_id = None

        super(Proposer, self).save(*args, **kwargs)

    def __unicode__(self):
        if self.person_id is not None:
            return self.person.__unicode__()
        elif self.committee_id is not None:
            if self.committee_partname:
                return "%s (%s)" % (self.committee.__unicode__(), self.committee_partname)
            else:
                return self.committee.__unicode__()
        else:
            return 'N/A'

    class Meta:
        ordering = ['order']


class Committee(models.Model):
    name = models.CharField(max_length=100)
    abbreviation_short = models.CharField(max_length=20)
    abbreviation_long = models.CharField(max_length=30)
    parliaments = models.ManyToManyField('Parliament', related_name='committees')

    committee_xml_id = models.IntegerField()

    def __unicode__(self):
        return capfirst(self.name)

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

    person_xml_id = models.IntegerField()

    def save(self, *args, **kwargs):
        self.slug = slugify(unidecode(self.name))
        self.subslug = 'f-%d' % self.birthdate.year

        super(Person, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'%s' % self.name

    class Meta:
        ordering = ['name']


class Session(models.Model):
    objects = SessionQuerySet.as_manager()

    parliament = models.ForeignKey('Parliament', related_name='sessions')
    session_num = models.IntegerField()
    name = models.CharField(max_length=30)
    timing_start_planned = models.DateTimeField(null=True)
    timing_start = models.DateTimeField(null=True)
    timing_end = models.DateTimeField(null=True)
    timing_text = models.CharField(max_length=200, null=True)

    def __unicode__(self):
        return u'%s' % self.name

    class Meta:
        ordering = ['session_num']


class SessionAgendaItem(models.Model):
    DISCUSSION_TYPES = (
        ('*', u''),
        ('0', u''),
        ('1', u'1. umræða'),
        ('2', u'2. umræða'),
        ('3', u'3. umræða'),
        ('E', u'ein umræða'),
        ('F', u'fyrri umræða'),
        ('S', u'síðari umræða'),
    )

    session = models.ForeignKey('Session', related_name='session_agenda_items')
    order = models.IntegerField()
    discussion_type = models.CharField(max_length=1, choices=DISCUSSION_TYPES)
    discussion_continued = models.BooleanField(default=False)
    comment_type = models.CharField(max_length=1, null=True)
    comment_text = models.CharField(max_length=100, null=True)
    comment_description = models.CharField(max_length=100, null=True)
    issue = models.ForeignKey('Issue', null=True, related_name='session_agenda_items')

    def __unicode__(self):
        return u'%d. %s' % (self.order, self.issue.detailed())

    class Meta:
        ordering = ['order']


class CommitteeAgenda(models.Model):
    objects = CommitteeAgendaQuerySet.as_manager()

    parliament = models.ForeignKey('Parliament', related_name='committee_agendas')
    committee = models.ForeignKey('Committee', related_name='committee_agendas')
    timing_start_planned = models.DateTimeField(null=True)
    timing_start = models.DateTimeField(null=True)
    timing_end = models.DateTimeField(null=True)
    timing_text = models.CharField(max_length=200, null=True)

    committee_agenda_xml_id = models.IntegerField()

    def __unicode__(self):
        return u'%s @ %s' % (self.committee, self.timing_start_planned)

    class Meta:
        ordering = ['timing_start_planned', 'committee__name']


class CommitteeAgendaItem(models.Model):
    committee_agenda = models.ForeignKey('CommitteeAgenda', related_name='committee_agenda_items')
    order = models.IntegerField()
    name = models.CharField(max_length=300)
    issue = models.ForeignKey('Issue', null=True, related_name='committee_agenda_items')

    def __unicode__(self):
        if self.issue is not None:
            return u'%d. %s' % (self.order, self.issue.detailed())
        else:
            return u'%d. %s' % (self.order, self.name)

    class Meta:
        ordering = ['order']


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

    party_xml_id = models.IntegerField()

    def save(self, *args, **kwargs):
        self.slug = slugify(unidecode(self.name))

        # Special parties are party-type containers rather than actual parties.
        if self.name == u'Utan þingflokka':
            self.special = True

        super(Party, self).save(*args, **kwargs)

    def __unicode__(self):
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

    constituency_xml_id = models.IntegerField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Seat(models.Model):
    SEAT_TYPES = (
        (u'þingmaður', u'þingmaður'),
        (u'varamaður', u'varamaður'),
        (u'með varamann', u'með varamann'),
    )

    person = models.ForeignKey('Person', related_name='seats')
    parliament = models.ForeignKey('Parliament', related_name='seats')
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPES)

    name_abbreviation = models.CharField(max_length=15, default="") # abbreviations may change by term
    physical_seat_number = models.IntegerField(default=0, null=True) # This is where MP physically sits, not electoral seat

    timing_in = models.DateTimeField()
    timing_out = models.DateTimeField(null=True)

    constituency = models.ForeignKey('Constituency', related_name='seats')
    constituency_mp_num = models.PositiveSmallIntegerField()

    party = models.ForeignKey('Party', related_name='seats')

    def tenure_ended_prematurely(self):
        p = self.parliament # Short-hand
        return self.seat_type in (u'þingmaður', u'með varamann') and (
            (self.timing_out is not None and p.timing_end is None)
            or (p.timing_end is not None and self.timing_out < p.timing_end - timezone.timedelta(days=1))
        )

    def __unicode__(self):
        if self.timing_out is None:
            return u'%s (%s : ...)' % (self.person, format_date(self.timing_in))
        else:
            return u'%s (%s : %s)' % (self.person, format_date(self.timing_in), format_date(self.timing_out))

    class Meta:
        ordering = ['timing_in', 'timing_out']


class CommitteeSeat(models.Model):
    COMMITTEE_SEAT_TYPES = (
        (u'nefndarmaður', u'nefndarmaður'),
        (u'varamaður', u'varamaður'),
        (u'kjörinn varamaður', u'kjörinn varamaður'),
        (u'formaður', u'formaður'),
        (u'1. varaformaður', u'1. varaformaður'),
        (u'2. varaformaður', u'2. varaformaður'),
        (u'áheyrnarfulltrúi', u'áheyrnarfulltrúi'),
    )

    person = models.ForeignKey('Person', related_name='committee_seats')
    committee = models.ForeignKey('Committee', related_name='committee_seats')
    parliament = models.ForeignKey('Parliament', related_name='committee_seats')
    committee_seat_type = models.CharField(max_length=20, choices=COMMITTEE_SEAT_TYPES)
    order = models.IntegerField()

    timing_in = models.DateTimeField()
    timing_out = models.DateTimeField(null=True)

    def __unicode__(self):
        if self.timing_out is None:
            return u'%s (%s, %s : ...)' % (self.person, self.committee, format_date(self.timing_in))
        else:
            # Short-hands
            person = self.person
            committee = self.committee
            timing_in = self.timing_in
            timing_out = self.timing_out
            return u'%s (%s, %s : %s)' % (person, committee, format_date(timing_in), format_date(timing_out))

    class Meta:
        ordering = ['timing_in', 'timing_out']
