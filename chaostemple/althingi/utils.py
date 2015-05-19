# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import errno
import os
import pytz
import urllib2
from datetime import date
from datetime import datetime
from sys import stderr
from sys import stdout
from xml.dom import minidom
from xml.parsers.expat import ExpatError

from althingi.models import Committee
from althingi.models import CommitteeAgenda
from althingi.models import CommitteeAgendaItem
from althingi.models import Document
from althingi.models import Issue
from althingi.models import IssueSummary
from althingi.models import Parliament
from althingi.models import Person
from althingi.models import Proposer
from althingi.models import Review
from althingi.models import Session
from althingi.models import SessionAgendaItem

from althingi.exceptions import AlthingiException

from althingi import althingi_settings

ISSUE_LIST_URL = 'http://www.althingi.is/altext/xml/thingmalalisti/?lthing=%d'
ISSUE_URL = 'http://www.althingi.is/altext/xml/thingmalalisti/thingmal/?lthing=%d&malnr=%d'
ISSUE_SUMMARY_URL = 'http://www.althingi.is/altext/xml/samantektir/samantekt/?lthing=%d&malnr=%d'
PERSON_URL = 'http://www.althingi.is/altext/xml/thingmenn/thingmadur/?nr=%d'
COMMITTEE_FULL_LIST_URL = 'http://www.althingi.is/altext/xml/nefndir/'
COMMITTEE_LIST_URL = 'http://www.althingi.is/altext/xml/nefndir/?lthing=%d'
COMMITTEE_AGENDA_LIST_URL = 'http://www.althingi.is/altext/xml/nefndarfundir/?lthing=%d'
COMMITTEE_AGENDA_URL = 'http://www.althingi.is/altext/xml/nefndarfundir/nefndarfundur/?dagskrarnumer=%d'
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
    'issues': {},

    'xml': {},
}

def get_response(web_url):

    retry_count = 2

    success = False
    while not success and retry_count > -1:
        try:
            response = urllib2.urlopen(web_url, timeout=5)
            success = True
        except IOError:
            print('Retrieving remote content failed, retries left: %s...' % retry_count)
            retry_count = retry_count - 1

    if success:
        return response
    else:
        print('Error: Failed retrieving URL: %s' % web_url, file=stderr)
        quit(1)

def sensible_datetime(value):

    if value is None:
        return None

    if type(value) is date:
        d = datetime(value.year, value.month, value.day, 0, 0, 0)
    elif type(value) is datetime:
        d = value
    else:
        try:
            d = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            try:
                d = datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                d = datetime.strptime(value, '%d.%m.%Y')

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

    content = get_response(remote_path).read()
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

    response = get_response(remote_path)

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
        print('Added parliament: %s' % parliament_num)
    else:
        print('Already have parliament: %s' % parliament_num)

    already_haves['parliaments'][parliament_num] = parliament

    return parliament


def ensure_person(person_xml_id):

    if already_haves['persons'].has_key(person_xml_id):
        return already_haves['persons'][person_xml_id]

    person_xml = minidom.parse(get_response(PERSON_URL % person_xml_id))

    name = person_xml.getElementsByTagName(u'nafn')[0].firstChild.nodeValue.strip()
    birthdate = person_xml.getElementsByTagName(u'fæðingardagur')[0].firstChild.nodeValue

    person_try = Person.objects.filter(person_xml_id=person_xml_id)
    if person_try.count() > 0:
        person = person_try[0]

        print('Already have person: %s' % person)
    else:
        person = Person()
        person.name = name
        person.birthdate = birthdate
        person.person_xml_id = person_xml_id
        person.save()

        print('Added person: %s' % person)

    already_haves['persons'][person_xml_id] = person

    return person


def ensure_committee(committee_xml_id, parliament_num=None):

    ah_key = '%d-%d' % (parliament_num, committee_xml_id)
    if already_haves['committees'].has_key(ah_key):
        return already_haves['committees'][ah_key]

    parliament = ensure_parliament(parliament_num)

    # This should be revisited when committees have their own, individual XML page
    def parse_committee_xml(xml_url):
        # Cache the XML document, so that we only need to retrieve it once per run
        if already_haves['xml'].has_key(xml_url):
            committees_full_xml = already_haves['xml'][xml_url]
        else:
            committees_full_xml = minidom.parse(get_response(xml_url))
            already_haves['xml'][xml_url] = committees_full_xml

        committees_xml = committees_full_xml.getElementsByTagName(u'nefnd')

        committee = None
        for committee_xml in committees_xml:
            if int(committee_xml.getAttribute(u'id')) == committee_xml_id:
                abbreviations_xml = committee_xml.getElementsByTagName(u'skammstafanir')[0]

                name = committee_xml.getElementsByTagName(u'heiti')[0].firstChild.nodeValue
                abbreviation_short = abbreviations_xml.getElementsByTagName(u'stuttskammstöfun')[0].firstChild.nodeValue
                abbreviation_long = abbreviations_xml.getElementsByTagName(u'löngskammstöfun')[0].firstChild.nodeValue

                committee_try = Committee.objects.filter(committee_xml_id=committee_xml_id, parliaments=parliament)
                if committee_try.count() > 0:
                    committee = committee_try[0]

                    print('Already have committee: %s' % committee)
                else:
                    committee = Committee()
                    committee.name = name
                    committee.abbreviation_short = abbreviation_short
                    committee.abbreviation_long = abbreviation_long
                    committee.parliament = parliament
                    committee.committee_xml_id = committee_xml_id

                    committee.save()
                    committee.parliaments.add(parliament)

                    print('Added committee: %s' % committee)

                break # We have found what we were looking for.

        return committee

    committee = parse_committee_xml(COMMITTEE_LIST_URL % parliament.parliament_num)
    if committee is None:
        # if the variable 'committee' is still None at this point, it means that the committee we requested
        # does not exist in the appropriate parliament's XML. This is a mistake in the XML that the XML
        # maintainers should be notified of, but we can still remedy this by downloading a different,
        # much larger XML document which contains all committees regardless of parliament.
        committee = parse_committee_xml(COMMITTEE_FULL_LIST_URL)
        print('Warning! Committee with ID %d is missing from committee listing in parliament %d! Tell the XML keeper!' %(committee_xml_id, parliament_num))

    already_haves['committees'][ah_key] = committee

    return committee


def update_issues(parliament_num=None):
    """
    Fetch a list of "recent" issues on Althingi and update our database accordingly.
    """

    parliament = ensure_parliament(parliament_num)

    issue_list_xml = minidom.parse(get_response(ISSUE_LIST_URL % parliament.parliament_num))
    issues_xml = issue_list_xml.getElementsByTagName(u'mál')

    for issue_xml in issues_xml:

        issue_num = int(issue_xml.getAttribute(u'málsnúmer'))

        update_issue(issue_num, parliament_num=parliament.parliament_num)


# NOTE: Only updates "A" issues, those with documents, reviews etc.
def update_issue(issue_num, parliament_num=None):

    parliament = ensure_parliament(parliament_num)

    ah_key = '%d-%d' % (parliament.parliament_num, issue_num)
    if already_haves['issues'].has_key(ah_key):
        return already_haves['issues'][ah_key]

    issue_xml = minidom.parse(get_response(ISSUE_URL % (parliament.parliament_num, issue_num)))
    docstubs_xml = issue_xml.getElementsByTagName(u'þingskjöl')[0].getElementsByTagName(u'þingskjal')
    reviews_xml = issue_xml.getElementsByTagName(u'erindaskrá')[0].getElementsByTagName(u'erindi')

    if len(issue_xml.getElementsByTagName(u'mál')) == 0:
        raise AlthingiException('Issue %d in parliament %d does not exist' % (issue_num, parliament.parliament_num))

    issue_type = issue_xml.getElementsByTagName(u'málstegund')[0].getAttribute(u'málstegund')

    name = issue_xml.getElementsByTagName(u'málsheiti')[0].firstChild.nodeValue.strip()

    description = issue_xml.getElementsByTagName(u'efnisgreining')[0].firstChild
    description = description.nodeValue.strip() if description != None else ''

    issue_try = Issue.objects.filter(issue_num=issue_num, issue_group='A', parliament=parliament)
    if issue_try.count() > 0:
        issue = issue_try[0]

        changed = False
        if issue.issue_type != issue_type:
            issue.issue_type = issue_type
            changed = True

        if issue.name != name:
            issue.name = name
            changed = True

        if issue.description != description:
            issue.description = description
            changed = True

        if changed:
            issue.save()
            print('Updated issue: %s' % issue)
        else:
            print('Already have issue: %s' % issue)
    else:
        issue = Issue()
        issue.issue_num = issue_num
        issue.issue_type = issue_type
        issue.issue_group = 'A'
        issue.name = name
        issue.description = description
        issue.parliament = parliament
        issue.save()

        print('Added issue: %s' % issue)

    # See if this issue has summary information
    summary_xml_try = issue_xml.getElementsByTagName(u'mál')[0].getElementsByTagName(u'samantekt')
    if len(summary_xml_try) > 0:
        # Yes, it has summary information
        summary_xml_url = ISSUE_SUMMARY_URL % (parliament.parliament_num, issue.issue_num)
        summary_xml = minidom.parse(get_response(summary_xml_url))

        purpose = summary_xml.getElementsByTagName(u'markmið')[0].firstChild.nodeValue
        try:
            change_description = summary_xml.getElementsByTagName(u'helstuBreytingar')[0].firstChild.nodeValue
        except AttributeError:
            change_description = ''
        try:
            changes_to_law = summary_xml.getElementsByTagName(u'breytingaráLögum')[0].firstChild.nodeValue
        except AttributeError:
            changes_to_law = ''
        try:
            cost_and_revenue = summary_xml.getElementsByTagName(u'kostnaðurOgTekjur')[0].firstChild.nodeValue
        except AttributeError:
            cost_and_revenue = ''
        try:
            other_info = summary_xml.getElementsByTagName(u'aðrarUpplýsingar')[0].firstChild.nodeValue
        except AttributeError:
            other_info = ''
        try:
            review_description = summary_xml.getElementsByTagName(u'umsagnir')[0].firstChild.nodeValue
        except AttributeError:
            review_description = ''
        try:
            fate = summary_xml.getElementsByTagName(u'afgreiðsla')[0].firstChild.nodeValue
        except AttributeError:
            fate = ''
        try:
            media_coverage = summary_xml.getElementsByTagName(u'fjölmiðlaumfjöllun')[0].firstChild.nodeValue
        except AttributeError:
            media_coverage = ''

        issue_summary_try = IssueSummary.objects.filter(issue_id=issue.id)
        if issue_summary_try.count() > 0:
            issue_summary = issue_summary_try[0]

            changed = False
            if issue_summary.purpose != purpose:
                issue_summary.purpose = purpose
                changed = True

            if issue_summary.change_description != change_description:
                issue_summary.change_description = change_description
                changed = True

            if issue_summary.changes_to_law != changes_to_law:
                issue_summary.changes_to_law = changes_to_law
                changed = True

            if issue_summary.cost_and_revenue != cost_and_revenue:
                issue_summary.cost_and_revenue = cost_and_revenue
                changed = True

            if issue_summary.other_info != other_info:
                issue_summary.other_info = other_info
                changed = True

            if issue_summary.review_description != review_description:
                issue_summary.review_description = review_description
                changed = True

            if issue_summary.fate != fate:
                issue_summary.fate = fate
                changed = True

            if issue_summary.media_coverage != media_coverage:
                issue_summary.media_coverage = media_coverage
                changed = True

            if changed:
                issue_summary.save()
                print('Updated issue summary for issue: %s' % issue)
            else:
                print('Already have issue summary for issue: %s' % issue)

        else:
            issue_summary = IssueSummary()
            issue_summary.issue_id = issue.id
            issue_summary.purpose = purpose
            issue_summary.change_description = change_description
            issue_summary.changes_to_law = changes_to_law
            issue_summary.cost_and_revenue = cost_and_revenue
            issue_summary.other_info = other_info
            issue_summary.review_description = review_description
            issue_summary.fate = fate
            issue_summary.media_coverage = media_coverage
            issue_summary.save()

            print('Added issue summary for issue: %s' % issue)

    # Process documents.
    lowest_doc_num = 0  # Lowest document number will always be the main document of the issue.
    for docstub_xml in docstubs_xml:
        # Make sure that this is indeed the correct issue.
        if int(docstub_xml.getAttribute(u'málsnúmer')) != issue.issue_num or int(docstub_xml.getAttribute(u'þingnúmer')) != parliament.parliament_num:
            continue

        doc_xml_url = docstub_xml.getElementsByTagName(u'slóð')[0].getElementsByTagName(u'xml')[0].firstChild.nodeValue

        doc_full_xml = minidom.parse(get_response(doc_xml_url))
        doc_xml = doc_full_xml.getElementsByTagName(u'þingskjal')[0].getElementsByTagName(u'þingskjal')[0]

        doc_num = int(doc_xml.getAttribute(u'skjalsnúmer'))
        doc_type = doc_xml.getElementsByTagName(u'skjalategund')[0].firstChild.nodeValue
        time_published = doc_xml.getElementsByTagName(u'útbýting')[0].firstChild.nodeValue + "+00:00"

        paths_xml = doc_xml.getElementsByTagName(u'slóð')
        html_paths_xml = paths_xml[0].getElementsByTagName(u'html') 
        pdf_paths_xml = paths_xml[0].getElementsByTagName(u'pdf')

        if len(html_paths_xml) > 0:
            path_html = html_paths_xml[0].firstChild.nodeValue
        else:
            path_html = None

        if len(pdf_paths_xml) > 0:
            path_pdf = pdf_paths_xml[0].firstChild.nodeValue
        else:
            path_pdf = None

        if path_html is None and path_pdf is None:
            print('Document not published: %d' % doc_num)
            continue

        if lowest_doc_num == 0:
            lowest_doc_num = doc_num
        elif lowest_doc_num > doc_num:
            lowest_doc_num = doc_num

        doc_try = Document.objects.filter(doc_num=doc_num, issue=issue)
        if doc_try.count() > 0:
            doc = doc_try[0]

            if not doc.html_filename or not doc.pdf_filename:
                if not doc.html_filename:
                    doc.html_filename = maybe_download_document(path_html, parliament.parliament_num, issue_num)
                if not doc.pdf_filename:
                    doc.pdf_filename = maybe_download_document(path_pdf, parliament.parliament_num, issue_num)
                doc.save()

            print('Already have document: %s' % doc)
        else:

            html_filename = maybe_download_document(path_html, parliament.parliament_num, issue_num)
            pdf_filename = maybe_download_document(path_pdf, parliament.parliament_num, issue_num)

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

            print('Added document: %s' % doc)

        # Process proposers.
        for proposer_xml in doc_xml.getElementsByTagName(u'flutningsmenn'):
            committeepart = None # Reset from possible previous iteration

            committee_xml = proposer_xml.getElementsByTagName(u'nefnd')
            if len(committee_xml) > 0:
                committee_xml_id = int(committee_xml[0].getAttribute('id'))

                committee = ensure_committee(committee_xml_id, parliament.parliament_num)

                committee_partname_node = committee_xml[0].getElementsByTagName(u'hluti')[0].firstChild

                committee_partname = committee_partname_node.nodeValue if committee_partname_node else ''
                committee_name = committee_xml[0].getElementsByTagName(u'heiti')[0].firstChild.nodeValue

                proposer_try = Proposer.objects.filter(document=doc, committee=committee, committee_partname=committee_partname)
                if proposer_try.count() > 0:
                    proposer = proposer_try[0]

                    print('Already have proposer: %s on document %s' % (proposer, doc))
                else:
                    proposer = Proposer()
                    proposer.committee = committee
                    proposer.committee_partname = committee_partname
                    proposer.document = doc
                    proposer.save()

                    print('Added proposer: %s to document %s' % (proposer, doc))

                persons_xml = committee_xml[0].getElementsByTagName(u'flutningsmaður')
                for person_xml in persons_xml:
                    person_xml_id = int(person_xml.getAttribute(u'id'))
                    order = int(person_xml.getAttribute(u'röð'))

                    person = ensure_person(person_xml_id)

                    subproposer_try = Proposer.objects.filter(parent=proposer, person=person)
                    if subproposer_try.count() > 0:
                        subproposer = subproposer_try[0]

                        print('Already have sub-proposer: %s on committee %s' % (subproposer, committee))
                    else:
                        subproposer = Proposer()
                        subproposer.person = person
                        subproposer.order = order
                        subproposer.parent = proposer
                        subproposer.save()

                        print('Added sub-proposer: %s to committee %s' % (subproposer, committee))


            else:
                persons_xml = proposer_xml.getElementsByTagName(u'flutningsmaður')
                for person_xml in persons_xml:
                    person_xml_id = int(person_xml.getAttribute(u'id'))

                    order = int(person_xml.getAttribute(u'röð'))

                    person = ensure_person(person_xml_id)

                    proposer_try = Proposer.objects.filter(document=doc, person=person)
                    if proposer_try.count() > 0:
                        proposer = proposer_try[0]

                        print('Already have proposer: %s on document %s' % (proposer, doc))
                    else:
                        proposer = Proposer()
                        proposer.person = person
                        proposer.order = order
                        proposer.document = doc
                        proposer.save()

                        print('Added proposer: %s to document %s' % (proposer, doc))


    # Figure out what the main document is, if any.
    try:
        main_doc = Document.objects.get(issue=issue, doc_num=lowest_doc_num)
        main_doc.is_main = True
        main_doc.save()
        print('Main document determined to be: %s' % main_doc)
    except Document.DoesNotExist:
        print('Main document undetermined, no documents yet')

    # Process reviews.
    for review_xml in reviews_xml:
        log_num = int(review_xml.getAttribute(u'dagbókarnúmer'))

        try:
            sender_name = review_xml.getElementsByTagName(u'sendandi')[0].firstChild.nodeValue
        except AttributeError:
            # Review with log_num 1057 in Parliament 112 lacks a name. Others do not exist.
            sender_name = ''

        review_type = review_xml.getElementsByTagName(u'tegunderindis')[0].getAttribute('tegund')
        try:
            date_arrived = review_xml.getElementsByTagName(u'komudagur')[0].firstChild.nodeValue
        except AttributeError:
            date_arrived = None
        try:
            date_sent = review_xml.getElementsByTagName(u'sendingadagur')[0].firstChild.nodeValue
        except AttributeError:
            date_sent = None

        # sender_name can contain a lot of baggage if it's old data (around 116th parliament and earlir)
        sender_name = sender_name.strip()
        while sender_name.find('  ') >= 0:
            sender_name = sender_name.replace('  ', ' ')

        paths_xml = review_xml.getElementsByTagName(u'slóð')
        pdf_paths_xml = paths_xml[0].getElementsByTagName(u'pdf')

        path_pdf = pdf_paths_xml[0].firstChild.nodeValue

        review_try = Review.objects.filter(log_num=log_num, issue=issue)
        if review_try.count() > 0:
            review = review_try[0]

            changed = False
            if review.sender_name != sender_name:
                review.sender_name = sender_name
                changed = True

            if review.review_type != review_type:
                review.review_type = review_type
                changed = True

            if sensible_datetime(review.date_arrived) != sensible_datetime(date_arrived):
                review.date_arrive = date_arrived
                changed = True

            if sensible_datetime(review.date_sent) != sensible_datetime(date_sent):
                review.date_sent = date_sent
                changed = True

            if not review.pdf_filename:
                review.pdf_filename = maybe_download_review(path_pdf, log_num, parliament.parliament_num, issue_num)
                review.save()

            if changed:
                review.save()
                print('Updated review: %s' % review)
            else:
                print('Already have review: %s' % review)
        else:

            pdf_filename = maybe_download_review(path_pdf, log_num, parliament.parliament_num, issue_num)

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

            print('Added review: %s' % review)

    already_haves['issues'][ah_key] = issue

    return issue


def update_docless_issue(issue_num, name, parliament_num=None):
    parliament = ensure_parliament(parliament_num)

    # Docless issue names can carry a lot of baggage if it's old data (around 116th parliament and earlier)
    name = name.strip()
    while name.find('  ') >= 0:
        name = name.replace('  ', ' ')

    issue_try = Issue.objects.filter(issue_num=issue_num, issue_group='B', parliament__parliament_num=parliament.parliament_num)
    if issue_try.count() > 0:
        issue = issue_try[0]

        changed = False
        if issue.name != name:
            issue.name = name
            changed = True

        if changed:
            issue.save()
            print('Updated docless issue: %s' % issue)
        else:
            print('Already have docless issue: %s' % issue)
    else:
        issue = Issue()
        issue.issue_num = issue_num
        issue.issue_group = 'B'
        issue.name = name
        # issue.description = description # NOTE: This never *seems* to be used
        issue.parliament = parliament
        issue.save()

        print('Added docless issue: %s' % issue)

    return issue


def update_sessions(parliament_num=None, date_limit=None):

    parliament = ensure_parliament(parliament_num)

    if date_limit is not None:
        date_limit = sensible_datetime(date_limit)

    sessions_xml = minidom.parse(get_response(SESSION_LIST_URL % parliament.parliament_num))
    for session_xml in reversed(sessions_xml.getElementsByTagName(u'þingfundur')):
        session_num = int(session_xml.getAttribute(u'númer'))

        session_date_tag = session_xml.getElementsByTagName(u'dagur')
        if len(session_date_tag) == 0: # If 0, then this is a session that started immediately following another.
            session_date_tag = session_xml.getElementsByTagName(u'fundursettur')

        # NOTE: If session_date is entirely unavailable, session is in the future so never less than date_limit.
        # Hence, loop is never exited on basis of a missing session_date.
        if session_date_tag[0].firstChild is not None:
            # If this raises an IndexError, suspect that XML is wrong.
            session_date = sensible_datetime(session_date_tag[0].firstChild.nodeValue)

            if date_limit is not None and session_date < date_limit:
                break

        update_session(session_num, parliament.parliament_num)


def update_session(session_num, parliament_num=None):

    parliament = ensure_parliament(parliament_num)

    response = get_response(SESSION_AGENDA_URL % (parliament.parliament_num, session_num))
    session_full_xml = minidom.parse(response)
    try:
        session_xml = session_full_xml.getElementsByTagName(u'þingfundur')[0]
    except IndexError:
        # Check if session exists in database, because if it does, it shouldn't.
        try:
            nonexistent_session = Session.objects.get(
                session_num=session_num,
                parliament__parliament_num=parliament.parliament_num
            )
            nonexistent_session.delete()

            print('Deleted non-existent session: %s' % nonexistent_session)
            return

        except Session.DoesNotExist:
            raise AlthingiException('Session %d in parliament %d does not exist' % (session_num, parliament.parliament_num))

    _process_session_agenda_xml(session_xml)


def update_next_sessions():

    response = get_response(SESSION_NEXT_AGENDA_URL)
    session_full_xml = minidom.parse(response)
    sessions_xml = session_full_xml.getElementsByTagName(u'þingfundur')
    for session_xml in sessions_xml:
        _process_session_agenda_xml(session_xml)



def update_committee_agendas(parliament_num=None, date_limit=None):

    parliament = ensure_parliament(parliament_num)

    if date_limit is not None:
        date_limit = sensible_datetime(date_limit)

    committee_agenda_list_xml = minidom.parse(get_response(COMMITTEE_AGENDA_LIST_URL % parliament.parliament_num))
    committee_agenda_stubs_xml = committee_agenda_list_xml.getElementsByTagName(u'nefndarfundur')
    for committee_agenda_stub_xml in reversed(committee_agenda_stubs_xml):

        meeting_date = sensible_datetime(committee_agenda_stub_xml.getElementsByTagName(u'dagur')[0].firstChild.nodeValue)
        if date_limit is not None and meeting_date < date_limit:
            break

        committee_agenda_xml_id = int(committee_agenda_stub_xml.getAttribute(u'númer'))
        update_committee_agenda(committee_agenda_xml_id, parliament.parliament_num)


def update_next_committee_agendas(parliament_num=None):
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)

    update_committee_agendas(parliament_num=parliament_num, date_limit=today)


def update_committee_agenda(committee_agenda_xml_id, parliament_num=None):

    parliament = ensure_parliament(parliament_num)

    response = get_response(COMMITTEE_AGENDA_URL % committee_agenda_xml_id)
    try:
        committee_agenda_full_xml = minidom.parse(response)
    except ExpatError:
        raise AlthingiException('Committee agenda with XML-ID %d not found' % committee_agenda_xml_id)
    committee_agenda_xml = committee_agenda_full_xml.getElementsByTagName(u'nefndarfundur')[0]
    _process_committee_agenda_xml(committee_agenda_xml)


# NOTE: To become a private function once we turn this into some sort of class
def _process_committee_agenda_xml(committee_agenda_xml):

    parliament_num = int(committee_agenda_xml.getAttribute(u'þingnúmer'))
    committee_agenda_xml_id = int(committee_agenda_xml.getAttribute(u'númer'))
    committee_xml_id = int(committee_agenda_xml.getElementsByTagName(u'nefnd')[0].getAttribute('id'))

    parliament = ensure_parliament(parliament_num)
    committee = ensure_committee(committee_xml_id, parliament_num)

    begins_xml = committee_agenda_xml.getElementsByTagName(u'hefst')[0]
    begins_datetime_xml = begins_xml.getElementsByTagName(u'dagurtími')
    begins_text_xml = begins_xml.getElementsByTagName(u'texti')
    if len(begins_datetime_xml) == 0:
        # Sometimes only the date is known, not the datetime.
        begins_date_xml = begins_xml.getElementsByTagName(u'dagur')
        if len(begins_date_xml) == 0:
            timing_start_planned = None
        else:
            timing_start_planned = sensible_datetime(begins_date_xml[0].firstChild.nodeValue)
    else:
        timing_start_planned = sensible_datetime(begins_datetime_xml[0].firstChild.nodeValue)

    if len(begins_text_xml) > 0:
        timing_text = begins_text_xml[0].firstChild.nodeValue
    else:
        timing_text = None

    try:
        timing_start = sensible_datetime(committee_agenda_xml.getElementsByTagName(u'fundursettur')[0].firstChild.nodeValue)
    except (AttributeError, IndexError):
        timing_start = None
    try:
        timing_end = sensible_datetime(committee_agenda_xml.getElementsByTagName(u'fuslit')[0].firstChild.nodeValue)
    except (AttributeError, IndexError):
        timing_end = None

    committee_agenda_try = CommitteeAgenda.objects.filter(
        committee_agenda_xml_id=committee_agenda_xml_id,
        parliament=parliament
    )
    if committee_agenda_try.count() > 0:
        committee_agenda = committee_agenda_try[0]

        changed = False
        if committee_agenda.timing_start_planned != timing_start_planned:
            committee_agenda.timing_start_planned = timing_start_planned
            changed = True
        if committee_agenda.timing_start != timing_start:
            committee_agenda.timing_start = timing_start
            changed = True
        if committee_agenda.timing_end != timing_end:
            committee_agenda.timing_end = timing_end
            changed = True
        if committee_agenda.timing_text != timing_text:
            committee_agenda.timing_text = timing_text
            changed = True

        if changed:
            committee_agenda.save()
            print('Updated committee agenda: %s' % committee_agenda)
        else:
            print('Already have committee agenda: %s' % committee_agenda)
    else:
        committee_agenda = CommitteeAgenda()
        committee_agenda.parliament = parliament
        committee_agenda.committee = committee
        committee_agenda.committee_agenda_xml_id = committee_agenda_xml_id
        committee_agenda.timing_start_planned = timing_start_planned
        committee_agenda.timing_start = timing_start
        committee_agenda.timing_end = timing_end
        committee_agenda.save()

        print('Added committee agenda: %s' % committee_agenda)

    max_order = 0
    items_xml = committee_agenda_xml.getElementsByTagName(u'dagskrárliður')
    for item_xml in items_xml:
        order = int(item_xml.getAttribute(u'númer'))
        name = item_xml.getElementsByTagName(u'heiti')[0].firstChild.nodeValue
        issue = None

        if order > max_order:
            max_order = order

        issues_xml = item_xml.getElementsByTagName(u'mál')
        if len(issues_xml) > 0:
            # There can only be one issue per agenda item. Right?
            issue_xml = issues_xml[0]
            issue_num = int(issue_xml.getAttribute(u'málsnúmer'))
            issue_parliament_num = int(issue_xml.getAttribute(u'löggjafarþing'))

            # It is assumed that issue_group will be 'A' (i.e. not 'B', which means an issue without documents)
            issue = update_issue(issue_num, issue_parliament_num)

        item_try = CommitteeAgendaItem.objects.filter(order=order, committee_agenda=committee_agenda)
        if item_try.count() > 0:
            item = item_try[0]

            changed = False
            if item.name != name:
                item.name = name
                changed = True
            if item.issue != issue:
                item.issue = issue
                changed = True

            if changed:
                item.save()
                print('Update committee agenda item: %s' % item)
            else:
                print('Already have committee agenda item: %s' % item)
        else:
            item = CommitteeAgendaItem()
            item.committee_agenda = committee_agenda
            item.order = order
            item.name = name
            item.issue = issue
            item.save()

            print('Added committee agenda item: %s' % item)

    # Delete items higher than the max_order since that means items has been dropped
    CommitteeAgendaItem.objects.filter(order__gt=max_order, committee_agenda=committee_agenda).delete()

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
            print('Updated session: %s' % session)
        else:
            print('Already have session: %s' % session)
    else:
        session = Session()
        session.parliament = parliament
        session.session_num = session_num
        session.name = name
        session.timing_start_planned = timing_start_planned
        session.timing_start = timing_start
        session.timing_end = timing_end
        session.save()
        print('Added session: %s' % session)

    # Prepare for agenda processing.
    response = get_response(SESSION_AGENDA_URL % (parliament.parliament_num, session_num))
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

            print('Added session agenda item: %s' % item)
        elif c_item.issue.issue_num != issue.issue_num or c_item.issue.issue_group != issue.issue_group:
            item = c_item
            item.issue = issue
            item.save()

            print('Updated session agenda item %d to issue: %s' % (order, issue))

    for item in SessionAgendaItem.objects.filter(session=session, order__gt=len(agenda_issues)):
        item.delete()

        print('Deleted session agenda item %s' % item)
