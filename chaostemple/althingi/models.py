# -*- coding: utf-8
from django.db import models
from django.templatetags.static import static
from django.utils import timezone

from BeautifulSoup import BeautifulSoup
import urllib


class SessionManager(models.Manager):
    def upcoming(self):

        # The XML cannot determine the planned timing of a session that comes immediately after
        # another, we first find the next upcoming session, which will need to have a timing_start_planned
        # configured. Then we look up all sessions with the same session number or higher. Then we return
        # the QuerySet object so that the calling function can modify the query further.

        now = timezone.now()
        today = timezone.make_aware(timezone.datetime(now.year, now.month, now.day), now.tzinfo)

        try:
            next_session = Session.objects.select_related(
                'parliament'
            ).filter(timing_start_planned__gt=today).order_by('-session_num')[0:1].get()
            next_num = next_session.session_num
            parliament_num = next_session.parliament.parliament_num
        except Session.DoesNotExist:
            return Session.objects.none()

        next_sessions = self.filter(session_num__gte=next_num, parliament__parliament_num=parliament_num)

        return next_sessions


class CommitteeAgendaManager(models.Manager):
    def upcoming(self):
        now = timezone.now()
        today = timezone.make_aware(timezone.datetime(now.year, now.month, now.day), now.tzinfo)

        return self.filter(timing_start_planned__gte=today)


class Parliament(models.Model):
    parliament_num = models.IntegerField(unique=True)  # IS: Þingnúmer

    def __unicode__(self):
        return u'Parliament %d' % self.parliament_num


class Issue(models.Model):
    ISSUE_TYPES = (
        ('l', 'lagafrumvarp'),
        ('a', 'þingsályktunartillaga'),
        ('m', 'fyrirspurn'),
        ('q', 'fyrirspurn til skriflegs svars'),
        ('s', 'skýrsla'),
        ('b', 'beiðni um skýrslu'),
    )

    ISSUE_GROUPS = (
        ('A', 'þingmál með þingskjölum'),
        ('B', 'þingmál án þingskjala'),
    )

    parliament = models.ForeignKey('Parliament')

    issue_num = models.IntegerField()  # IS: Málsnúmer
    issue_type = models.CharField(max_length=1, choices=ISSUE_TYPES)  # IS: Málstegund
    issue_group = models.CharField(max_length=1, choices=ISSUE_GROUPS, default='A')  # IS: Málsflokkur
    name = models.CharField(max_length=500)
    description = models.TextField()
    final_vote_complete = models.BooleanField(default=False)

    document_count = models.IntegerField(default=0) # Auto-populated by Issue.save()
    review_count = models.IntegerField(default=0) # Auto-populated by Review.save()

    def __unicode__(self):
        if self.issue_group == 'B':
            return u'%s (%s)' % (self.name, self.issue_group)
        else:
            return u'%s (%d)' % (self.name, self.issue_num)

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
        (u'vs', u'vinnuskjal'),
        (u'xx', u'x'),
        (u'yf', u'yfirlit'),
        (u'yg', u'ýmis gögn'),
        (u'ys', u'yfirlýsing'),
    )

    issue = models.ForeignKey('Issue', related_name='reviews')
    log_num = models.IntegerField()  # IS: Dagbókarnúmer
    sender_name = models.CharField(max_length=100)
    # TODO: committee
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
        ordering = ['time_published']


class Proposer(models.Model):
    document = models.ForeignKey('Document', null=True, related_name='proposers')
    order = models.IntegerField(null=True)
    person = models.ForeignKey('Person', null=True)
    committee = models.ForeignKey('Committee', null=True)
    committee_partname = models.CharField(max_length=50, null=True) # Only non-None if committee is non-None
    parent = models.ForeignKey('Proposer', null=True, related_name='subproposers')

    def __unicode__(self):
        if self.person is not None:
            return self.person.__unicode__()
        elif self.committee is not None:
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
        return self.name

    class Meta:
        ordering = ['name']


class Person(models.Model):
    name = models.CharField(max_length=100)
    ssn = models.CharField(max_length=10)
    birthdate = models.DateField()

    person_xml_id = models.IntegerField()

    def __unicode__(self):
        return u'%s' % self.name


class Session(models.Model):
    objects = SessionManager()

    parliament = models.ForeignKey('Parliament', related_name='sessions')
    session_num = models.IntegerField()
    name = models.CharField(max_length=30)
    timing_start_planned = models.DateTimeField(null=True)
    timing_start = models.DateTimeField(null=True)
    timing_end = models.DateTimeField(null=True)

    def __unicode__(self):
        return u'%s' % self.name

    class Meta:
        ordering = ['session_num']


class SessionAgendaItem(models.Model):
    DISCUSSION_TYPES = (
        ('*', u''),
        ('0', u''),
        ('1', u'fyrsta umræða'),
        ('2', u'önnur umræða'),
        ('3', u'þriðja umræða'),
        ('E', u'ein umræða'),
        ('F', u'fyrri umræða'),
        ('S', u'seinni umræða'),
    )

    session = models.ForeignKey('Session', related_name='agenda_items')
    order = models.IntegerField()
    voting = models.CharField(max_length=1, null=True)
    discussion_type = models.CharField(max_length=1, choices=DISCUSSION_TYPES)
    discussion_continued = models.BooleanField(default=False)
    issue = models.ForeignKey('Issue', null=True, related_name='agenda_items')

    def __unicode__(self):
        return u'%d. %s' % (self.order, self.issue)

    class Meta:
        ordering = ['order']


class CommitteeAgenda(models.Model):
    objects = CommitteeAgendaManager()

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
        ordering = ['timing_start_planned']


class CommitteeAgendaItem(models.Model):
    committee_agenda = models.ForeignKey('CommitteeAgenda', related_name='committee_agenda_items')
    order = models.IntegerField()
    name = models.CharField(max_length=300)
    issue = models.ForeignKey('Issue', null=True, related_name='committee_agenda_items')

    def __unicode__(self):
        if self.issue is not None:
            return u'%d. %s (%d)' % (self.order, self.name, self.issue.issue_num)
        else:
            return u'%d. %s' % (self.order, self.name)

    class Meta:
        ordering = ['order']


class Parliamentarian(Person):
    parliament_num = models.ForeignKey('Parliament')
    seat_number = models.IntegerField(default=0)

    # abbreviation is stored in a different place in the xml, and therefore could change by term
    name_abbreviation = models.CharField(max_length=15, default="")
    party = models.CharField(max_length=200, default="")
    constituency = models.CharField(max_length=250, default="")


