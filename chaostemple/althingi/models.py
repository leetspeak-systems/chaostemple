# -*- coding: utf-8
from django.db import models
from django.templatetags.static import static

from BeautifulSoup import BeautifulSoup
import urllib


class Parliament(models.Model):
    parliament_num = models.IntegerField(unique=True)  # IS: Þingnúmer

    def __unicode__(self):
        return u'Parliament %d' % self.parliament_num


class Issue(models.Model):
    ISSUE_TYPES = (
        ('l', 'lagafrumvarp'),
        ('a', 'þingsályktunartillaga'),
        ('m', 'fyrirspurn'),
        ('q', 'fyrirspurn til skrifl. svars'),
        ('s', 'skýrsla'),
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


class Review(models.Model):
    REVIEW_TYPES = (
        ('ub', u'umsögn'),
    )

    issue = models.ForeignKey('Issue', related_name='reviews')
    log_num = models.IntegerField()  # IS: Dagbókarnúmer
    sender_name = models.CharField(max_length=100)
    # TODO: committee
    review_type = models.CharField(max_length=2, choices=REVIEW_TYPES)  #: Tegund erindis
    date_arrived = models.DateField(null=True)
    date_sent = models.DateField(null=True)
    pdf_remote_path = models.CharField(max_length=500)
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
        ordering = ['date_arrived', 'log_num']


class Document(models.Model):
    DOCUMENT_TYPES = (
        (u'þáltill.', u'þingsályktunartillaga'),
        (u'nál. með brtt.', u'nefndarálit með breytingartillögu'),
        (u'þál. í heild', u'þingsályktun í heild'),
        (u'skýrsla rh. (frumskjal)', u'Skýrsla ráðherra (frumskjal)'),
    )

    issue = models.ForeignKey('Issue', related_name='documents')

    doc_num = models.IntegerField()
    doc_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    time_published = models.DateTimeField()
    is_main = models.BooleanField(default=False)

    html_remote_path = models.CharField(max_length=500)
    html_filename = models.CharField(max_length=50)
    pdf_remote_path = models.CharField(max_length=500)
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
    abbreviation_long = models.CharField(max_length=20)
    parliaments = models.ManyToManyField('Parliament', related_name='committees')

    committee_xml_id = models.IntegerField()

    def __unicode__(self):
        return self.name


class Person(models.Model):
    name = models.CharField(max_length=100)
    ssn = models.CharField(max_length=10)
    birthdate = models.DateField()

    person_xml_id = models.IntegerField()

    def __unicode__(self):
        return u'%s' % self.name


class Session(models.Model):
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
    session = models.ForeignKey('Session', related_name='agenda_items')
    order = models.IntegerField()
    issue = models.ForeignKey('Issue', null=True, related_name='agenda_items')

    def __unicode__(self):
        return u'%d. %s' % (self.order, self.issue)

    class Meta:
        ordering = ['order']


class Parliamentarian(Person):
    parliament_num = models.ForeignKey('Parliament')
    seat_number = models.IntegerField(default=0)

    # abbreviation is stored in a different place in the xml, and therefore could change by term
    name_abbreviation = models.CharField(max_length=15, default="")
    party = models.CharField(max_length=200, default="")
    constituency = models.CharField(max_length=250, default="")


