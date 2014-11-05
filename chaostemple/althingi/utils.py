# -*- coding: utf-8 -*-
from __future__ import absolute_import

import errno
import os
import pytz
import urllib
from datetime import datetime
from sys import stdout
from xml.dom import minidom

from althingi.models import Committee
from althingi.models import Document
from althingi.models import Issue
from althingi.models import Parliament
from althingi.models import Person
from althingi.models import Proposer
from althingi.models import Review
from althingi.models import Session
from althingi.models import SessionAgendaItem

from althingi import althingi_settings

ISSUE_LIST_URL = 'http://www.althingi.is/altext/xml/thingmalalisti/?lthing=%d'
ISSUE_URL = 'http://www.althingi.is/altext/xml/thingmalalisti/thingmal/?lthing=%d&malnr=%d'
PERSON_URL = 'http://www.althingi.is/altext/xml/thingmenn/thingmadur/?nr=%d'
COMMITTEE_LIST_URL = 'http://www.althingi.is/altext/xml/nefndir/?lthing=%d'
SESSION_LIST_URL = 'http://www.althingi.is/altext/xml/thingfundir/?lthing=%d'
SESSION_AGENDA_URL = 'http://www.althingi.is/altext/xml/dagskra/thingfundur/?lthing=%d&fundur=%d'
SESSION_NEXT_AGENDA_URL = 'http://www.althingi.is/altext/xml/dagskra/thingfundur/'

PERSONS_URL = 'http://www.althingi.is/altext/xml/thingmenn/?lthing=%d'
PARLIAMENTARIAN_DETAILS_URL = 'http://www.althingi.is/altext/xml/thingmenn/thingmadur/thingseta/?nr=%d'

'''
already_haves
-------------
This variable contains information on which information has already been received in a given
iteration. For example, when someone updates a single Issue, it is ensured whether the
corresponding Parliament exists. If it does not exist, it is created and its relevant information
downloaded and registered in the database.

If you then wish to check for multiple Issues, the Parliament is checked in each iteration. Seeing
that this is an import feature, this is not a critical problem, but it does mean that there is a
lot of repetitious checking for the same information in the database for no real technical reason,
but also it conflates the output of the import script considerably.

This variable is the memory of what has already been checked in the given iteration, so that once
a Parliament (as an example) has already been checked, it needs not be checked again during that
time the importing script is run.

Note that this caching is only per-running and does not (or at least shouldn't) live longer than
the time it takes to run the import.

'''
already_haves = {
    'parliaments': {},
    'persons': {},
    'committees': {},
}

def sensible_datetime(value):
    d = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
    return pytz.timezone('UTC').localize(d)

def mkpath(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


# Download and save document
def maybe_download_document(remote_path, parliament_num, issue_num):

    if not althingi_settings.DOWNLOAD_DOCUMENTS:
        return ''

    basename = os.path.basename(remote_path)

    stdout.write('Downloading file %s...' % basename)
    stdout.flush()

    local_filename = os.path.join('althingi', parliament_num.__str__(), issue_num.__str__(), basename)

    content = urllib.urlopen(remote_path).read()
    localpath = os.path.join(althingi_settings.STATIC_DOCUMENT_DIR, local_filename)
    mkpath(os.path.dirname(localpath))
    outfile = open(localpath, 'w')
    outfile.write(content)
    outfile.close()

    stdout.write('done\n')

    return local_filename


# Download and review document
def maybe_download_review(remote_path, log_num, parliament_num, issue_num):

    if not althingi_settings.DOWNLOAD_REVIEWS:
        return ''

    basename = os.path.basename(remote_path)

    stdout.write('Downloading review with log number %d...' % log_num)
    stdout.flush()

    response = urllib.urlopen(remote_path)

    filename = os.path.basename(remote_path)
    local_filename = os.path.join('althingi', parliament_num.__str__(), issue_num.__str__(), filename)

    content = response.read()
    localpath = os.path.join(althingi_settings.STATIC_DOCUMENT_DIR, local_filename)
    mkpath(os.path.dirname(localpath))
    outfile = open(localpath, 'w')
    outfile.write(content)
    outfile.close()

    stdout.write('done\n')

    return local_filename


def get_last_parliament_num():
    return althingi_settings.CURRENT_PARLIAMENT_NUM  # Temporary, while we figure out a wholesome way to auto-detect


def ensure_parliament(parliament_num):
    parliament_num = parliament_num if parliament_num else get_last_parliament_num()

    if already_haves['parliaments'].has_key(parliament_num):
        return already_haves['parliaments'][parliament_num]

    parliament, created = Parliament.objects.get_or_create(parliament_num=parliament_num)
    if created:
        print 'Added parliament: %s' % parliament_num
    else:
        print 'Already have parliament: %s' % parliament_num

    already_haves['parliaments'][parliament_num] = parliament

    return parliament


def ensure_person(person_xml_id):

    if already_haves['persons'].has_key(person_xml_id):
        return already_haves['persons'][person_xml_id]

    person_xml = minidom.parse(urllib.urlopen(PERSON_URL % person_xml_id))

    name = person_xml.getElementsByTagName(u'nafn')[0].firstChild.nodeValue
    birthdate = person_xml.getElementsByTagName(u'fæðingardagur')[0].firstChild.nodeValue

    person_try = Person.objects.filter(person_xml_id=person_xml_id)
    if person_try.count() > 0:
        person = person_try[0]

        print 'Already have person: %s' % person
    else:
        person = Person()
        person.name = name
        person.birthdate = birthdate
        person.person_xml_id = person_xml_id
        person.save()

        print 'Added person: %s' % person

    already_haves['persons'][person_xml_id] = person

    return person


def ensure_committee(committee_xml_id, parliament_num=None):

    ah_key = '%d-%d' % (parliament_num, committee_xml_id)
    if already_haves['committees'].has_key(ah_key):
        return already_haves['committees'][ah_key]

    parliament = ensure_parliament(parliament_num)

    committees_full_xml = minidom.parse(urllib.urlopen(COMMITTEE_LIST_URL % parliament.parliament_num))
    committees_xml = committees_full_xml.getElementsByTagName(u'nefnd')

    for committee_xml in committees_xml:
        if int(committee_xml.getAttribute(u'id')) == committee_xml_id:
            abbreviations_xml = committee_xml.getElementsByTagName(u'skammstafanir')[0]

            name = committee_xml.getElementsByTagName(u'heiti')[0].firstChild.nodeValue
            abbreviation_short = abbreviations_xml.getElementsByTagName(u'stuttskammstöfun')[0].firstChild.nodeValue
            abbreviation_long = abbreviations_xml.getElementsByTagName(u'löngskammstöfun')[0].firstChild.nodeValue

            committee_try = Committee.objects.filter(committee_xml_id=committee_xml_id, parliaments=parliament)
            if committee_try.count() > 0:
                committee = committee_try[0]

                print 'Already have committee: %s' % committee
            else:
                committee = Committee()
                committee.name = name
                committee.abbreviation_short = abbreviation_short
                committee.abbreviation_long = abbreviation_long
                committee.parliament = parliament
                committee.committee_xml_id = committee_xml_id

                committee.save()
                committee.parliaments.add(parliament)

                print 'Added committee: %s' % committee

            break # We have found what we were looking for.

    already_haves['committees'][ah_key] = committee

    return committee


def update_issues(parliament_num=None):
    """
    Fetch a list of "recent" issues on Althingi and update our database accordingly.
    """

    parliament = ensure_parliament(parliament_num)

    issue_list_xml = minidom.parse(urllib.urlopen(ISSUE_LIST_URL % parliament.parliament_num))
    issues_xml = issue_list_xml.getElementsByTagName(u'mál')

    for issue_xml in issues_xml:

        issue_num = int(issue_xml.getAttribute(u'málsnúmer'))

        update_issue(issue_num, parliament_num=parliament.parliament_num)


# NOTE: Only updates "A" issues, those with documents, reviews etc.
def update_issue(issue_num, parliament_num=None):
    parliament = ensure_parliament(parliament_num)

    issue_xml = minidom.parse(urllib.urlopen(ISSUE_URL % (parliament.parliament_num, issue_num)))
    docstubs_xml = issue_xml.getElementsByTagName(u'þingskjöl')[0].getElementsByTagName(u'þingskjal')
    reviews_xml = issue_xml.getElementsByTagName(u'erindaskrá')[0].getElementsByTagName(u'erindi')


    issue_type = issue_xml.getElementsByTagName(u'málstegund')[0].getAttribute(u'málstegund')

    name = issue_xml.getElementsByTagName(u'málsheiti')[0].firstChild.nodeValue

    description = issue_xml.getElementsByTagName(u'efnisgreining')[0].firstChild
    description = description.nodeValue if description != None else ''

    issue_try = Issue.objects.filter(issue_num=issue_num, issue_group='A', parliament=parliament)
    if issue_try.count() > 0:
        issue = issue_try[0]

        print 'Already have issue: %s' % issue
    else:
        issue = Issue()
        issue.issue_num = issue_num
        issue.issue_type = issue_type
        issue.issue_group = 'A'
        issue.name = name
        issue.description = description
        issue.parliament = parliament
        issue.save()

        print 'Added issue: %s' % issue

    # Process documents.
    lowest_doc_num = 0  # Lowest document number will always be the main document of the issue.
    for docstub_xml in docstubs_xml:
        # Make sure that this is indeed the correct issue.
        if int(docstub_xml.getAttribute(u'málsnúmer')) != issue.issue_num or int(docstub_xml.getAttribute(u'þingnúmer')) != parliament.parliament_num:
            continue

        doc_xml_url = docstub_xml.getElementsByTagName(u'slóð')[0].getElementsByTagName(u'xml')[0].firstChild.nodeValue

        doc_full_xml = minidom.parse(urllib.urlopen(doc_xml_url))
        doc_xml = doc_full_xml.getElementsByTagName(u'þingskjal')[0].getElementsByTagName(u'þingskjal')[0]

        doc_num = int(doc_xml.getAttribute(u'skjalsnúmer'))
        doc_type = doc_xml.getElementsByTagName(u'skjalategund')[0].firstChild.nodeValue
        time_published = doc_xml.getElementsByTagName(u'útbýting')[0].firstChild.nodeValue + "+00:00"

        paths_xml = doc_xml.getElementsByTagName(u'slóð')
        html_paths_xml = paths_xml[0].getElementsByTagName(u'html') 
        pdf_paths_xml = paths_xml[0].getElementsByTagName(u'pdf')
        if len(html_paths_xml) == 0:
            print 'Document not published: %d' % doc_num
            continue

        path_html = html_paths_xml[0].firstChild.nodeValue
        path_pdf = pdf_paths_xml[0].firstChild.nodeValue

        if lowest_doc_num == 0:
            lowest_doc_num = doc_num
        elif lowest_doc_num > doc_num:
            lowest_doc_num = doc_num

        doc_try = Document.objects.filter(doc_num=doc_num, issue=issue)
        if doc_try.count() > 0:
            doc = doc_try[0]

            if not doc.html_filename or not doc.pdf_filename:
                if not doc.html_filename:
                    doc.html_filename = maybe_download_document(path_html, parliament_num, issue_num)
                if not doc.pdf_filename:
                    doc.pdf_filename = maybe_download_document(path_pdf, parliament_num, issue_num)
                doc.save()

            print 'Already have document: %s' % doc
        else:

            html_filename = maybe_download_document(path_html, parliament_num, issue_num)
            pdf_filename = maybe_download_document(path_pdf, parliament_num, issue_num)

            doc = Document()
            doc.doc_num = doc_num
            doc.doc_type = doc_type
            doc.time_published = time_published
            doc.html_remote_path = path_html
            doc.html_filename = html_filename
            doc.pdf_remote_path = path_pdf
            doc.pdf_filename = pdf_filename
            doc.issue = issue
            doc.save()

            print 'Added document: %s' % doc

        # Process proposers.
        for proposer_xml in doc_xml.getElementsByTagName(u'flutningsmenn'):
            committeepart = None # Reset from possible previous iteration

            committee_xml = proposer_xml.getElementsByTagName(u'nefnd')
            if len(committee_xml) > 0:
                committee_xml_id = int(committee_xml[0].getAttribute('id'))

                committee = ensure_committee(committee_xml_id, parliament_num)

                committee_partname_node = committee_xml[0].getElementsByTagName(u'hluti')[0].firstChild

                committee_partname = committee_partname_node.nodeValue if committee_partname_node else ''
                committee_name = committee_xml[0].getElementsByTagName(u'heiti')[0].firstChild.nodeValue

                proposer_try = Proposer.objects.filter(document=doc, committee=committee, committee_partname=committee_partname)
                if proposer_try.count() > 0:
                    proposer = proposer_try[0]

                    print 'Already have proposer: %s on document %s' % (proposer, doc)
                else:
                    proposer = Proposer()
                    proposer.committee = committee
                    proposer.committee_partname = committee_partname
                    proposer.document = doc
                    proposer.save()

                    print 'Added proposer: %s to document %s' % (proposer, doc)

                persons_xml = committee_xml[0].getElementsByTagName(u'flutningsmaður')
                for person_xml in persons_xml:
                    person_xml_id = int(person_xml.getAttribute(u'id'))
                    order = int(person_xml.getAttribute(u'röð'))

                    person = ensure_person(person_xml_id)

                    subproposer_try = Proposer.objects.filter(parent=proposer, person=person)
                    if subproposer_try.count() > 0:
                        subproposer = subproposer_try[0]

                        print 'Already have sub-proposer: %s on committee %s' % (subproposer, committee)
                    else:
                        subproposer = Proposer()
                        subproposer.person = person
                        subproposer.order = order
                        subproposer.parent = proposer
                        subproposer.save()

                        print 'Added sub-proposer: %s to committee %s' % (subproposer, committee)


            else:
                persons_xml = proposer_xml.getElementsByTagName(u'flutningsmaður')
                for person_xml in persons_xml:
                    person_xml_id = int(person_xml.getAttribute(u'id'))

                    order = int(person_xml.getAttribute(u'röð'))

                    person = ensure_person(person_xml_id)

                    proposer_try = Proposer.objects.filter(document=doc, person=person)
                    if proposer_try.count() > 0:
                        proposer = proposer_try[0]

                        print 'Already have proposer: %s on document %s' % (proposer, doc)
                    else:
                        proposer = Proposer()
                        proposer.person = person
                        proposer.order = order
                        proposer.document = doc
                        proposer.save()

                        print 'Added proposer: %s to document %s' % (proposer, doc)


    # Figure out what the main document is, if any.
    try:
        main_doc = Document.objects.get(issue=issue, doc_num=lowest_doc_num)
        main_doc.is_main = True
        main_doc.save()
        print 'Main document determined to be: %s' % main_doc
    except Document.DoesNotExist:
        print 'Main document undetermined, no documents yet'

    # Process reviews.
    for review_xml in reviews_xml:
        log_num = int(review_xml.getAttribute(u'dagbókarnúmer'))
        sender_name = review_xml.getElementsByTagName(u'sendandi')[0].firstChild.nodeValue
        review_type = review_xml.getElementsByTagName(u'tegunderindis')[0].getAttribute('tegund')
        try:
            date_arrived = review_xml.getElementsByTagName(u'komudagur')[0].firstChild.nodeValue
        except AttributeError:
            date_arrived = None
        try:
            date_sent = review_xml.getElementsByTagName(u'sendingadagur')[0].firstChild.nodeValue
        except AttributeError:
            date_sent = None

        paths_xml = review_xml.getElementsByTagName(u'slóð')
        pdf_paths_xml = paths_xml[0].getElementsByTagName(u'pdf')

        path_pdf = pdf_paths_xml[0].firstChild.nodeValue

        review_try = Review.objects.filter(log_num=log_num, issue=issue)
        if review_try.count() > 0:
            review = review_try[0]

            if not review.pdf_filename:
                review.pdf_filename = maybe_download_review(path_pdf, log_num, parliament_num, issue_num)
                review.save()

            print 'Already have review: %s' % review
        else:

            pdf_filename = maybe_download_review(path_pdf, log_num, parliament_num, issue_num)

            review = Review()
            review.issue = issue
            review.log_num = log_num
            review.sender_name = sender_name
            review.review_type = review_type
            review.date_arrived = date_arrived
            review.date_sent = date_sent
            review.pdf_remote_path = path_pdf
            review.pdf_filename = pdf_filename
            review.save()

            print 'Added review: %s' % review

    return issue


def update_docless_issue(issue_num, name, parliament_num=None):
    parliament = ensure_parliament(parliament_num)

    issue_try = Issue.objects.filter(issue_num=issue_num, issue_group='B', parliament__parliament_num=parliament.parliament_num)
    if issue_try.count() > 0:
        issue = issue_try[0]

        changed = False
        if issue.name != name:
            issue.name = name
            changed = True

        if changed:
            issue.save()
            print 'Updated docless issue: %s' % issue
        else:
            print 'Already have docless issue: %s' % issue
    else:
        issue = Issue()
        issue.issue_num = issue_num
        issue.issue_group = 'B'
        issue.name = name
        # issue.description = description # NOTE: This never *seems* to be used
        issue.parliament = parliament
        issue.save()

        print 'Added docless issue: %s' % issue

    return issue


def update_sessions(parliament_num=None):

    parliament = ensure_parliament(parliament_num)

    sessions_xml = minidom.parse(urllib.urlopen(SESSION_LIST_URL % parliament.parliament_num))
    for session_xml in sessions_xml.getElementsByTagName(u'þingfundur'):
        session_num = int(session_xml.getAttribute(u'númer'))

        update_session(session_num, parliament.parliament_num)


def update_session(session_num, parliament_num=None):

    response = urllib.urlopen(SESSION_AGENDA_URL % (parliament_num, session_num))
    session_full_xml = minidom.parse(response)
    session_xml = session_full_xml.getElementsByTagName(u'þingfundur')[0]

    _process_session_agenda_xml(session_xml)


def update_next_sessions():

    response = urllib.urlopen(SESSION_NEXT_AGENDA_URL)
    session_full_xml = minidom.parse(response)
    sessions_xml = session_full_xml.getElementsByTagName(u'þingfundur')
    for session_xml in sessions_xml:
        _process_session_agenda_xml(session_xml)


# NOTE: To become a private function once we turn this into some sort of class
def _process_session_agenda_xml(session_xml):

    parliament_num = int(session_xml.getAttribute(u'þingnúmer'))
    session_num = int(session_xml.getAttribute(u'númer'))

    parliament = ensure_parliament(parliament_num)

    name = session_xml.getElementsByTagName(u'fundarheiti')[0].firstChild.nodeValue

    begins_xml = session_xml.getElementsByTagName(u'hefst')[0].getElementsByTagName(u'dagurtími')
    if len(begins_xml) == 0:
        timing_start_planned = None
    else:
        timing_start_planned = sensible_datetime(begins_xml[0].firstChild.nodeValue)

    try:
        timing_start = sensible_datetime(session_xml.getElementsByTagName(u'fundursettur')[0].firstChild.nodeValue)
    except AttributeError:
        timing_start = None
    try:
        timing_end = sensible_datetime(session_xml.getElementsByTagName(u'fuslit')[0].firstChild.nodeValue)
    except AttributeError:
        timing_end = None

    session_try = Session.objects.filter(session_num=session_num, parliament=parliament)
    if session_try.count() > 0:
        session = session_try[0]

        changed = False
        if session.timing_start_planned != timing_start_planned:
            session.timing_start_planned = timing_start_planned
            changed = True
        if session.timing_start != timing_start:
            session.timing_start = timing_start
            changed = True
        if session.timing_end != timing_end:
            session.timing_end = timing_end
            changed = True

        if changed:
            session.save()
            print 'Updated session: %s' % session
        else:
            print 'Already have session: %s' % session
    else:
        session = Session()
        session.parliament = parliament
        session.session_num = session_num
        session.name = name
        session.timing_start_planned = timing_start_planned
        session.timing_start = timing_start
        session.timing_end = timing_end
        session.save()
        print 'Added session: %s' % session

    # Prepare for agenda processing.
    response = urllib.urlopen(SESSION_AGENDA_URL % (parliament.parliament_num, session_num))
    session_agenda_full_xml = minidom.parse(response)
    session_agenda_xml = session_agenda_full_xml.getElementsByTagName(u'dagskrá')[0]

    # Update issues in agenda, first.
    agenda_issues = []
    for session_agenda_item_xml in session_agenda_xml.getElementsByTagName(u'dagskrárliður'):
        issue_xml = session_agenda_item_xml.getElementsByTagName(u'mál')[0]

        order = int(session_agenda_item_xml.getAttribute(u'númer'))
        issue_num = int(issue_xml.getAttribute(u'málsnúmer'))
        issue_group = issue_xml.getAttribute(u'málsflokkur')
        issue_name = issue_xml.getElementsByTagName(u'málsheiti')[0].firstChild.nodeValue

        if issue_group == 'A':
            agenda_issues.append(update_issue(issue_num, parliament.parliament_num))
        elif issue_group == 'B':
            agenda_issues.append(update_docless_issue(issue_num, issue_name, parliament.parliament_num))

    # At this point, we have the list 'agenda_issues' as it is in XML before we update the database.

    # Update the actual agenda in local database, taking into account that it may have changed.
    c_items = iter(SessionAgendaItem.objects.select_related('issue').filter(session=session).order_by('order'))
    order = 0
    for issue in agenda_issues:
        order = order + 1

        try:
            c_item = c_items.next()
        except StopIteration:
            c_item = None

        if c_item == None:
            item = SessionAgendaItem()
            item.session = session
            item.order = order
            item.issue = issue
            item.save()

            print 'Added session agenda item: %s' % item
        elif c_item.issue.issue_num != issue.issue_num or c_item.issue.issue_group != issue.issue_group:
            item = c_item
            item.issue = issue
            item.save()

            print 'Updated session agenda item %d to issue: %s' % (order, issue)

    for item in SessionAgendaItem.objects.filter(session=session, order__gt=len(agenda_issues)):
        item.delete()

        print 'Deleted session agenda item %s' % item
