# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

from datetime import datetime
from django.db.models import Q
from sys import stderr
from sys import stdout
from xml.parsers.expat import ExpatError

from althingi.models import Committee
from althingi.models import CommitteeAgenda
from althingi.models import CommitteeAgendaItem
from althingi.models import CommitteeSeat
from althingi.models import Constituency
from althingi.models import Document
from althingi.models import Issue
from althingi.models import IssueSummary
from althingi.models import Parliament
from althingi.models import Party
from althingi.models import Person
from althingi.models import Proposer
from althingi.models import Rapporteur
from althingi.models import Review
from althingi.models import Seat
from althingi.models import Session
from althingi.models import SessionAgendaItem
from althingi.models import Vote
from althingi.models import VoteCasting

from althingi.exceptions import AlthingiException

from althingi.utils import get_last_parliament_num
from althingi.utils import maybe_download_document
from althingi.utils import maybe_download_review
from althingi.utils import sensible_datetime

from althingi.xmlutils import get_xml


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
    'parties': {},
    'persons': {},
    'seats': {},
    'committees': {},
    'committee_seats': {},
    'constituencies': {},
    'issues': {},
    'sessions': {},
    'vote_castings': {},

    'xml': {},
}


def update_parliament(parliament_num):
    parliament_num = parliament_num if parliament_num else get_last_parliament_num()

    if already_haves['parliaments'].has_key(parliament_num):
        return already_haves['parliaments'][parliament_num]

    parliaments_full_xml = get_xml('PARLIAMENT_URL', parliament_num)

    try:
        parliament_xml = parliaments_full_xml.getElementsByTagName(u'þing')[0]
    except IndexError:
        raise AlthingiException('Parliament %s could not be found' % parliament_num)

    era = parliament_xml.getElementsByTagName(u'tímabil')[0].firstChild.nodeValue;
    timing_start = sensible_datetime(parliament_xml.getElementsByTagName(u'þingsetning')[0].firstChild.nodeValue)
    try:
        timing_end = sensible_datetime(parliament_xml.getElementsByTagName(u'þinglok')[0].firstChild.nodeValue)
    except IndexError:
        timing_end = None

    try:
        parliament = Parliament.objects.get(parliament_num=parliament_num)

        changed = False
        if parliament.era != era:
            parliament.era = era
            changed = True

        if parliament.timing_start != sensible_datetime(timing_start):
            parliament.timing_start = timing_start
            changed = True

        if parliament.timing_end != sensible_datetime(timing_end):
            parliament.timing_end = timing_end
            changed = True

        if changed:
            parliament.save()
            print('Updated parliament: %s' % parliament)
        else:
            print('Already have parliament: %s' % parliament)

    except Parliament.DoesNotExist:
        parliament = Parliament()
        parliament.parliament_num = parliament_num
        parliament.era = era
        parliament.timing_start = timing_start
        parliament.timing_end = timing_end
        parliament.save()

        print('Added parliament: %s' % parliament)

    already_haves['parliaments'][parliament_num] = parliament

    return parliament


def update_persons(parliament_num=None):

    parliament = update_parliament(parliament_num)

    persons_full_xml = get_xml('PERSONS_URL', parliament.parliament_num)

    persons_xml = persons_full_xml.getElementsByTagName(u'þingmaður')

    for person_xml in persons_xml:
        person_xml_id = int(person_xml.getAttribute(u'id'))

        update_person(person_xml_id, parliament.parliament_num)

def update_person(person_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)

    # Cached by parliament_num as well, to make sure that if we're iterating
    # through multiple parliaments, we also catch the seats and committee
    # seats below.
    ah_key = '%d-%d' % (parliament.parliament_num, person_xml_id)
    if already_haves['persons'].has_key(ah_key):
        return already_haves['persons'][ah_key]

    person_xml = get_xml('PERSON_URL', person_xml_id)

    try:
        # For some unknown reason, an email address is given in two separate tags
        email_xml = person_xml.getElementsByTagName(u'netfang')[0]
        email_name = email_xml.getElementsByTagName(u'nafn')[0].firstChild.nodeValue.strip()
        email_domain = email_xml.getElementsByTagName(u'lén')[0].firstChild.nodeValue.strip()
        email = '%s@%s' % (email_name, email_domain)
    except (AttributeError, IndexError):
        email = None
    try:
        facebook_url = person_xml.getElementsByTagName(u'facebook')[0].firstChild.nodeValue.strip()
    except (AttributeError, IndexError):
        facebook_url = None
    try:
        twitter_url = person_xml.getElementsByTagName(u'twitter')[0].firstChild.nodeValue.strip()
    except (AttributeError, IndexError):
        twitter_url = None
    try:
        youtube_url = person_xml.getElementsByTagName(u'youtube')[0].firstChild.nodeValue.strip()
    except (AttributeError, IndexError):
        youtube_url = None
    try:
        blog_url = person_xml.getElementsByTagName(u'blogg')[0].firstChild.nodeValue.strip()
    except (AttributeError, IndexError):
        blog_url = None
    try:
        website_url = person_xml.getElementsByTagName(u'vefur')[0].firstChild.nodeValue.strip()
    except (AttributeError, IndexError):
        website_url = None

    name = person_xml.getElementsByTagName(u'nafn')[0].firstChild.nodeValue.strip()
    birthdate = sensible_datetime(person_xml.getElementsByTagName(u'fæðingardagur')[0].firstChild.nodeValue)

    try:
        person = Person.objects.get(person_xml_id=person_xml_id)

        changed = False
        if person.name != name:
            person.name = name
            changed = True

        if sensible_datetime(person.birthdate) != birthdate:
            person.birthdate = person.birthdate
            changed = True

        if person.email != email:
            person.email = email
            changed = True

        if person.facebook_url != facebook_url:
            person.facebook_url = facebook_url
            changed = True

        if person.twitter_url != twitter_url:
            person.twitter_url = twitter_url
            changed = True

        if person.youtube_url != youtube_url:
            person.youtube_url = youtube_url
            changed = True

        if person.blog_url != blog_url:
            person.blog_url = blog_url
            changed = True

        if person.website_url != website_url:
            person.website_url = website_url
            changed = True

        if changed:
            person.save()
            print('Updated person: %s' % person)
        else:
            print('Already have person: %s' % person)

    except Person.DoesNotExist:
        person = Person()
        person.name = name
        person.birthdate = birthdate
        person.email = email
        person.facebook_url = facebook_url
        person.twitter_url = twitter_url
        person.youtube_url = youtube_url
        person.blog_url = blog_url
        person.website_url = website_url
        person.person_xml_id = person_xml_id
        person.save()

        print('Added person: %s' % person)

    already_haves['persons'][ah_key] = person

    update_seats(person_xml_id, parliament.parliament_num)
    update_committee_seats(person_xml_id, parliament.parliament_num)

    return person


def update_seats(person_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)

    ah_key = '%d-%d' % (parliament.parliament_num, person_xml_id)
    if already_haves['seats'].has_key(ah_key):
        return already_haves['seats'][ah_key]

    update_constituencies(parliament.parliament_num)
    update_parties(parliament.parliament_num)

    seats_full_xml = get_xml('SEATS_URL', person_xml_id)
    seats_xml = seats_full_xml.getElementsByTagName(u'þingsetur')[0].getElementsByTagName(u'þingseta')

    seats = []
    for seat_xml in seats_xml:
        seat_parliament_num = int(seat_xml.getElementsByTagName(u'þing')[0].firstChild.nodeValue)

        if seat_parliament_num == parliament.parliament_num:
            seat_type = seat_xml.getElementsByTagName(u'tegund')[0].firstChild.nodeValue

            name_abbreviation = seat_xml.getElementsByTagName(u'skammstöfun')[0].firstChild.nodeValue
            try:
                physical_seat_number = int(seat_xml.getElementsByTagName(u'þingsalssæti')[0].firstChild.nodeValue)
            except AttributeError:
                physical_seat_number = None

            timing_in = sensible_datetime(seat_xml.getElementsByTagName(u'inn')[0].firstChild.nodeValue)
            try:
                timing_out = sensible_datetime(seat_xml.getElementsByTagName(u'út')[0].firstChild.nodeValue)
            except AttributeError:
                timing_out = None

            constituency_xml_id = int(seat_xml.getElementsByTagName(u'kjördæmi')[0].getAttribute(u'id'))
            constituency_mp_num = int(seat_xml.getElementsByTagName(u'kjördæmanúmer')[0].firstChild.nodeValue)

            party_xml_id = int(seat_xml.getElementsByTagName(u'þingflokkur')[0].getAttribute(u'id'))

            try:
                seat = Seat.objects.get(
                    person__person_xml_id=person_xml_id,
                    parliament__parliament_num=parliament.parliament_num,
                    timing_in=timing_in,
                    timing_out=timing_out
                )

                print('Already have seat: %s' % seat)

            except Seat.DoesNotExist:
                seat = Seat()
                seat.person = Person.objects.get(person_xml_id=person_xml_id)
                seat.parliament = parliament
                seat.seat_type = seat_type
                seat.name_abbreviation = name_abbreviation
                seat.physical_seat_number = physical_seat_number
                seat.timing_in = timing_in
                seat.timing_out = timing_out
                seat.constituency = Constituency.objects.get(constituency_xml_id=constituency_xml_id)
                seat.constituency_mp_num = constituency_mp_num
                seat.party = Party.objects.get(party_xml_id=party_xml_id)

                seat.save()
                print('Added seat: %s' % seat)

            seats.append(seat)

    deletable_seats = Seat.objects.filter(
        parliament__parliament_num=parliament.parliament_num,
        person__person_xml_id=person_xml_id
    ).exclude(id__in=[s.id for s in seats])
    for seat in deletable_seats:
        seat.delete()
        print('Deleted non-existent seat: %s' % seat)

    already_haves['seats'][ah_key] = seats

    return seats


def update_vote_castings(parliament_num=None):

    parliament = update_parliament(parliament_num)

    vote_castings_full_xml = get_xml('VOTE_CASTINGS_URL', parliament.parliament_num)

    vote_castings_xml = vote_castings_full_xml.getElementsByTagName(u'atkvæðagreiðsla')

    for vote_casting_xml in vote_castings_xml:
        vote_casting_xml_id = int(vote_casting_xml.getAttribute(u'atkvæðagreiðslunúmer'))

        update_vote_casting(vote_casting_xml_id, parliament.parliament_num)


def update_vote_casting(vote_casting_xml_id, parliament_num):

    parliament = update_parliament(parliament_num)

    if already_haves['vote_castings'].has_key('vote_casting_xml_id'):
        return already_haves['vote_castings'][vote_casting_xml_id]

    vote_casting_full_xml = get_xml('VOTE_CASTING_URL', vote_casting_xml_id)
    vote_casting_xml = vote_casting_full_xml.getElementsByTagName(u'atkvæðagreiðsla')[0]

    issue_num = int(vote_casting_xml.getAttribute(u'málsnúmer'))
    issue_group = vote_casting_xml.getAttribute(u'málsflokkur')

    if issue_group == 'A':
        issue = update_issue(issue_num, parliament.parliament_num)

        doc_num = int(vote_casting_xml.getElementsByTagName(u'þingskjal')[0].getAttribute(u'skjalsnúmer'))
        document = issue.documents.get(doc_num=doc_num)
    # NOTE / TODO: Waiting for B-issue types to appear in XML for vote castings.
    #elif issue_group == 'B':
    #    docless_issue_xml = vote_casting_xml.getElementsByTagName(u'mál')[0]
    #    issue = _process_docless_issue(docless_issue_xml)
    #    document = None
    else:
        issue = None
        document = None

    timing = sensible_datetime(vote_casting_xml.getElementsByTagName(u'tími')[0].firstChild.nodeValue)
    vote_casting_type = vote_casting_xml.getElementsByTagName(u'tegund')[0].firstChild.nodeValue
    try:
        specifics = vote_casting_xml.getElementsByTagName(u'nánar')[0].firstChild.nodeValue.strip()
    except (IndexError, AttributeError):
        specifics = ''

    session_num = int(vote_casting_xml.getElementsByTagName(u'fundur')[0].firstChild.nodeValue)
    session = update_session(session_num, parliament.parliament_num)

    try:
        committee_xml_id = int(vote_casting_xml.getElementsByTagName(u'til')[0].getAttribute('id'))
        to_committee = update_committee(committee_xml_id, parliament.parliament_num)
    except IndexError:
        to_committee = None

    try:
        conclusion_xml = vote_casting_xml.getElementsByTagName(u'niðurstaða')[0]

        try:
            method = conclusion_xml.getElementsByTagName(u'aðferð')[0].firstChild.nodeValue
        except IndexError:
            method = None

        try:
            count_yes = int(
                conclusion_xml.getElementsByTagName(u'já')[0].getElementsByTagName(u'fjöldi')[0].firstChild.nodeValue
            )
        except (IndexError, AttributeError):
            count_yes = None

        try:
            count_no = int(
                conclusion_xml.getElementsByTagName(u'nei')[0].getElementsByTagName(u'fjöldi')[0].firstChild.nodeValue
            )
        except (IndexError, AttributeError):
            count_no = None

        try:
            count_abstain = int(
                conclusion_xml.getElementsByTagName(
                    u'greiðirekkiatkvæði'
                )[0].getElementsByTagName(u'fjöldi')[0].firstChild.nodeValue
            )
        except (IndexError, AttributeError):
            count_abstain = None

        try:
            conclusion = conclusion_xml.getElementsByTagName(u'niðurstaða')[0].firstChild.nodeValue
        except:
            conclusion = None

    except IndexError:
        method = None
        count_yes = None
        count_no = None
        count_abstain = None
        conclusion = None

    try:
        vote_casting = VoteCasting.objects.get(vote_casting_xml_id=vote_casting_xml_id)

        changed = False
        if sensible_datetime(vote_casting.timing) != sensible_datetime(timing):
            vote_casting.timing = sensible_datetime(timing)
            changed = True

        if vote_casting.vote_casting_type != vote_casting_type:
            vote_casting.vote_casting_type = vote_casting_type
            changed = True

        if vote_casting.specifics != specifics:
            vote_casting.specifics = specifics
            changed = True

        if vote_casting.method != method:
            vote_casting.method = method
            changed = True

        if vote_casting.count_yes != count_yes:
            vote_casting.count_yes = count_yes
            changed = True

        if vote_casting.count_no != count_no:
            vote_casting.count_no = count_no
            changed = True

        if vote_casting.count_abstain != count_abstain:
            vote_casting.count_abstain = count_abstain
            changed = True

        if vote_casting.conclusion != conclusion:
            vote_casting.conclusion = conclusion
            changed = True

        if vote_casting.issue != issue:
            vote_casting.issue = issue
            changed = True

        if vote_casting.document != document:
            vote_casting.document = document
            changed = True

        if vote_casting.session != session:
            vote_casting.session = session
            changed = True

        if vote_casting.to_committee != to_committee:
            vote_casting.to_committee = to_committee
            changed = True

        if changed:
            vote_casting.save()
            print('Updated vote casting: %s' % vote_casting)
        else:
            print('Already have vote casting: %s' % vote_casting)

    except VoteCasting.DoesNotExist:
        vote_casting = VoteCasting()

        vote_casting.timing = timing
        vote_casting.vote_casting_type = vote_casting_type
        vote_casting.specifics = specifics
        vote_casting.method = method
        vote_casting.count_yes = count_yes
        vote_casting.count_no = count_no
        vote_casting.count_abstain = count_abstain
        vote_casting.conclusion = conclusion
        vote_casting.issue = issue
        vote_casting.document = document
        vote_casting.session = session
        vote_casting.to_committee = to_committee
        vote_casting.vote_casting_xml_id = vote_casting_xml_id

        vote_casting.save()

        print('Added vote casting: %s' % vote_casting)

    # Process actual votes, if they exist.
    votes_xml = vote_casting_xml.getElementsByTagName(u'atkvæðaskrá')
    if len(votes_xml) > 0:
        for vote_xml in votes_xml[0].getElementsByTagName(u'þingmaður'):
            person_xml_id = int(vote_xml.getAttribute(u'id'))
            vote_response = vote_xml.getElementsByTagName(u'atkvæði')[0].firstChild.nodeValue

            # NOTE: To be removed when XML is fixed.
            if vote_response == u'f: óþekktur kóði':
                vote_response = u'boðaði fjarvist'

            person = update_person(person_xml_id, parliament.parliament_num)

            try:
                vote = vote_casting.votes.get(vote_casting_id=vote_casting.id, person_id=person.id)

                changed = False
                if vote.vote_response != vote_response:
                    vote.vote_response = vote_response
                    changed = True

                if changed:
                    vote.save()
                    print('Updated vote: %s' % vote)
                else:
                    print('Already have vote: %s' % vote)
            except Vote.DoesNotExist:
                vote = Vote()
                vote.vote_casting_id = vote_casting.id
                vote.person_id = person.id
                vote.vote_response = vote_response

                vote.save()

                print('Added vote: %s' % vote)

    already_haves['vote_castings'][vote_casting_xml_id] = vote_casting

    return vote_casting


def update_committee_seats(person_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)

    ah_key = '%d-%d' % (parliament.parliament_num, person_xml_id)
    if already_haves['committee_seats'].has_key(ah_key):
        return already_haves['committee_seats'][ah_key]

    committee_seats_full_xml = get_xml('COMMITTEE_SEATS_URL', person_xml_id)
    committee_seats_xml = committee_seats_full_xml.getElementsByTagName(u'nefndasetur')[0].getElementsByTagName(u'nefndaseta')

    committee_seats = []
    for committee_seat_xml in committee_seats_xml:
        committee_seat_parliament_num = int(committee_seat_xml.getElementsByTagName(u'þing')[0].firstChild.nodeValue)

        if committee_seat_parliament_num == parliament.parliament_num:

            committee_xml_id = int(committee_seat_xml.getElementsByTagName(u'nefnd')[0].getAttribute('id'))
            committee = update_committee(committee_xml_id, parliament.parliament_num)

            committee_seat_type = committee_seat_xml.getElementsByTagName(u'staða')[0].firstChild.nodeValue

            order = committee_seat_xml.getElementsByTagName(u'röð')[0].firstChild.nodeValue

            timing_in = sensible_datetime(committee_seat_xml.getElementsByTagName(u'inn')[0].firstChild.nodeValue)
            try:
                timing_out = sensible_datetime(committee_seat_xml.getElementsByTagName(u'út')[0].firstChild.nodeValue)
            except IndexError:
                timing_out = None

            try:
                committee_seat = CommitteeSeat.objects.filter(
                    person__person_xml_id=person_xml_id,
                    committee=committee,
                    parliament__parliament_num=parliament.parliament_num,
                    timing_in=timing_in
                ).get(Q(timing_out=timing_out) | Q(timing_out=None))

                changed = False
                if committee_seat.timing_out != timing_out:
                    committee_seat.timing_out = timing_out
                    changed = True

                if changed:
                    committee_seat.save()
                    print('Updated committee seat: %s' % committee_seat)
                else:
                    print('Already have committee seat: %s' % committee_seat)

            except CommitteeSeat.DoesNotExist:
                committee_seat = CommitteeSeat()
                committee_seat.person = Person.objects.get(person_xml_id=person_xml_id)
                committee_seat.committee = committee
                committee_seat.parliament = parliament
                committee_seat.committee_seat_type = committee_seat_type
                committee_seat.order = order
                committee_seat.timing_in = timing_in
                committee_seat.timing_out = timing_out

                committee_seat.save()
                print('Added committee seat: %s' % committee_seat)

            committee_seats.append(committee_seat)

    already_haves['committee_seats'][ah_key] = committee_seats

    return committee_seats


def update_committees(parliament_num=None):

    parliament = update_parliament(parliament_num)

    committees_full_xml = get_xml('COMMITTEE_LIST_URL', parliament.parliament_num)
    committees_xml = committees_full_xml.getElementsByTagName(u'nefndir')[0]

    for committee_xml in committees_xml.getElementsByTagName(u'nefnd'):
        committee_xml_id = int(committee_xml.getAttribute(u'id'))
        update_committee(committee_xml_id, parliament.parliament_num)


def update_committee(committee_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)

    ah_key = '%d-%d' % (parliament.parliament_num, committee_xml_id)
    if already_haves['committees'].has_key(ah_key):
        return already_haves['committees'][ah_key]

    # NOTE: This should be revisited when committees have their own, individual XML page
    def parse_committee_xml(xml_url_name, parliament_num=None):
        # NOTE: We import this here, only because this entire function should go away when
        # committees have their own, individual XML page.
        from althingi.xmlutils import xml_urls

        if parliament_num:
            xml_url = xml_urls[xml_url_name] % parliament_num
        else:
            xml_url = xml_urls[xml_url_name]

        # Cache the XML document, so that we only need to retrieve it once per run
        if already_haves['xml'].has_key(xml_url):
            committees_full_xml = already_haves['xml'][xml_url]
        else:
            if parliament_num:
                committees_full_xml = get_xml(xml_url_name, parliament_num)
            else:
                committees_full_xml = get_xml(xml_url_name)
            already_haves['xml'][xml_url] = committees_full_xml

        committees_xml = committees_full_xml.getElementsByTagName(u'nefnd')

        committee = None
        for committee_xml in committees_xml:
            if int(committee_xml.getAttribute(u'id')) == committee_xml_id:
                abbreviations_xml = committee_xml.getElementsByTagName(u'skammstafanir')[0]
                period_xml = committee_xml.getElementsByTagName(u'tímabil')[0]

                name = committee_xml.getElementsByTagName(u'heiti')[0].firstChild.nodeValue
                abbreviation_short = abbreviations_xml.getElementsByTagName(u'stuttskammstöfun')[0].firstChild.nodeValue
                abbreviation_long = abbreviations_xml.getElementsByTagName(u'löngskammstöfun')[0].firstChild.nodeValue

                parliament_num_first = int(period_xml.getElementsByTagName(u'fyrstaþing')[0].firstChild.nodeValue)
                try:
                    parliament_num_last = int(period_xml.getElementsByTagName(u'síðastaþing')[0].firstChild.nodeValue)
                except (AttributeError, IndexError):
                    parliament_num_last = None

                try:
                    committee = Committee.objects.get(committee_xml_id=committee_xml_id)

                    changed = False
                    if committee.parliament_num_first != parliament_num_first:
                        committee.parliament_num_first = parliament_num_first
                        changed = True

                    if committee.parliament_num_last != parliament_num_last:
                        committee.parliament_num_last = parliament_num_last
                        changed = True

                    if parliament not in committee.parliaments.all():
                        committee.parliaments.add(parliament)
                        changed = True

                    if changed:
                        committee.save()
                        print('Updated committee: %s' % committee)
                    else:
                        print('Already have committee: %s' % committee)

                except Committee.DoesNotExist:
                    committee = Committee()
                    committee.name = name
                    committee.abbreviation_short = abbreviation_short
                    committee.abbreviation_long = abbreviation_long
                    committee.parliament_num_first = parliament_num_first
                    committee.parliament_num_last = parliament_num_last
                    committee.committee_xml_id = committee_xml_id

                    committee.save()
                    committee.parliaments.add(parliament)

                    print('Added committee: %s' % committee)

                break # We have found what we were looking for.

        return committee

    committee = parse_committee_xml('COMMITTEE_LIST_URL', parliament.parliament_num)
    if committee is None:
        # if the variable 'committee' is still None at this point, it means that the committee we requested
        # does not exist in the appropriate parliament's XML. This is a mistake in the XML that the XML
        # maintainers should be notified of, but we can still remedy this by downloading a different,
        # much larger XML document which contains all committees regardless of parliament.
        print('Warning: Committee with ID %d is missing from committee listing in parliament %d! Tell the XML keeper!' % (
            committee_xml_id,
            parliament.parliament_num
        ), file=stderr)
        committee = parse_committee_xml('COMMITTEE_FULL_LIST_URL')

    already_haves['committees'][ah_key] = committee

    return committee


def update_issues(parliament_num=None):
    """
    Fetch a list of "recent" issues on Althingi and update our database accordingly.
    """

    parliament = update_parliament(parliament_num)

    issue_list_xml = get_xml('ISSUE_LIST_URL', parliament.parliament_num)
    issues_xml = issue_list_xml.getElementsByTagName(u'mál')

    for issue_xml in issues_xml:
        # We are only interested in A-issues (with documents).
        if issue_xml.getAttribute(u'málsflokkur') != 'A':
            continue

        issue_num = int(issue_xml.getAttribute(u'málsnúmer'))

        update_issue(issue_num, parliament_num=parliament.parliament_num)


# NOTE: Only updates "A" issues, those with documents, reviews etc.
def update_issue(issue_num, parliament_num=None):

    parliament = update_parliament(parliament_num)

    ah_key = '%d-%d' % (parliament.parliament_num, issue_num)
    if already_haves['issues'].has_key(ah_key):
        return already_haves['issues'][ah_key]

    # If issue has been published in an earlier parliament, we'll record it in this variable and deal with it afterwards
    # Contains a list of structs, for exmaple: {'parliament_num': 144, 'issue_num': 524 }
    previously_published_as = []

    issue_xml = get_xml('ISSUE_URL', parliament.parliament_num, issue_num)
    docstubs_xml = issue_xml.getElementsByTagName(u'þingskjöl')[0].getElementsByTagName(u'þingskjal')
    reviews_xml = issue_xml.getElementsByTagName(u'erindaskrá')[0].getElementsByTagName(u'erindi')

    if len(issue_xml.getElementsByTagName(u'mál')) == 0:
        raise AlthingiException('Issue %d in parliament %d does not exist' % (issue_num, parliament.parliament_num))

    issue_type = issue_xml.getElementsByTagName(u'málstegund')[0].getAttribute(u'málstegund')

    name = issue_xml.getElementsByTagName(u'málsheiti')[0].firstChild.nodeValue.strip()

    description = issue_xml.getElementsByTagName(u'efnisgreining')[0].firstChild
    description = description.nodeValue.strip() if description != None else ''

    try:
        issue = Issue.objects.get(issue_num=issue_num, issue_group='A', parliament=parliament)

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
            print('Updated issue: %s' % issue.detailed())
        else:
            print('Already have issue: %s' % issue.detailed())

    except Issue.DoesNotExist:
        issue = Issue()
        issue.issue_num = issue_num
        issue.issue_type = issue_type
        issue.issue_group = 'A'
        issue.name = name
        issue.description = description
        issue.parliament = parliament
        issue.save()

        print('Added issue: %s' % issue.detailed())

    # Add or remove rapporteurs
    rapporteurs_xml = issue_xml.getElementsByTagName(u'framsögumenn')
    if len(rapporteurs_xml) > 0:
        rapporteur_ids = []
        for rapporteur_xml in rapporteurs_xml[0].getElementsByTagName(u'framsögumaður'):
            person_xml_id = int(rapporteur_xml.getAttribute(u'id'))
            person = update_person(person_xml_id, parliament.parliament_num)

            try:
                rapporteur = Rapporteur.objects.get(issue_id=issue.id, person_id=person.id)

                print('Already have rapporteur: %s' % rapporteur)
            except Rapporteur.DoesNotExist:
                rapporteur = Rapporteur()
                rapporteur.issue_id = issue.id
                rapporteur.person_id = person.id
                rapporteur.save()

                print('Added rapporteur: %s' % rapporteur)

            rapporteur_ids.append(rapporteur.id)

        # Delete rapporteurs that no longer exist online.
        for rapporteur in Rapporteur.objects.filter(issue_id=issue.id).exclude(id__in=rapporteur_ids):
            rapporteur.delete()
            print('Deleted non-existent rapporteur: %s' % rapporteur)

    # Check if issue was previously published
    linked_issues_xml = issue_xml.getElementsByTagName(u'tengdMál')
    if len(linked_issues_xml) > 0:
        previously_published_xml = linked_issues_xml[0].getElementsByTagName(u'lagtFramÁðurSem')
        if len(previously_published_xml) > 0:
            for previous_issue_xml in previously_published_xml[0].getElementsByTagName(u'mál'):
                previous_parliament_num = int(previous_issue_xml.getAttribute(u'þingnúmer'))
                previous_issue_num = int(previous_issue_xml.getAttribute(u'málsnúmer'))

                previously_published_as.append({
                    'parliament_num': previous_parliament_num,
                    'issue_num': previous_issue_num,
                })

    # See if this issue has summary information
    summary_xml_try = issue_xml.getElementsByTagName(u'mál')[0].getElementsByTagName(u'samantekt')
    if len(summary_xml_try) > 0:
        # Yes, it has summary information
        summary_xml = get_xml('ISSUE_SUMMARY_URL', parliament.parliament_num, issue.issue_num)

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

        try:
            issue_summary = IssueSummary.objects.get(issue_id=issue.id)

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
                print('Updated issue summary for issue: %s' % issue.detailed())
            else:
                print('Already have issue summary for issue: %s' % issue.detailed())

        except IssueSummary.DoesNotExist:
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

            print('Added issue summary for issue: %s' % issue.detailed())

    # Process documents.
    doc_nums = [] # Keep track of legit documents. Sometimes docs get deleted from the XML and so should be deleted locally.
    for i, docstub_xml in enumerate(docstubs_xml):
        # Make sure that this is indeed the correct issue.
        if int(docstub_xml.getAttribute(u'málsnúmer')) != issue.issue_num or int(docstub_xml.getAttribute(u'þingnúmer')) != parliament.parliament_num:
            continue

        is_main = False
        if i == 0:
            # If this is the zero-eth iterator, this is the main document.
            is_main = True

        doc_num = int(docstub_xml.getAttribute(u'skjalsnúmer'))

        doc_full_xml = get_xml('DOCUMENT_URL', parliament.parliament_num, doc_num)
        doc_xml = doc_full_xml.getElementsByTagName(u'þingskjal')[0].getElementsByTagName(u'þingskjal')[0]

        doc_nums.append(doc_num)

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

        try:
            doc = Document.objects.get(doc_num=doc_num, issue=issue)

            if not doc.html_filename or not doc.pdf_filename:
                if not doc.html_filename:
                    doc.html_filename = maybe_download_document(path_html, parliament.parliament_num, issue_num)
                if not doc.pdf_filename:
                    doc.pdf_filename = maybe_download_document(path_pdf, parliament.parliament_num, issue_num)
                doc.save()

            changed = False
            if doc.doc_type != doc_type:
                doc.doc_type = doc_type
                changed = True

            if sensible_datetime(doc.time_published) != sensible_datetime(time_published):
                doc.time_published = time_published
                changed = True

            if doc.html_remote_path != path_html:
                doc.html_remote_path = path_html
                changed = True

            if doc.pdf_remote_path != path_pdf:
                doc.pdf_remote_path = path_pdf
                changed = True

            if changed:
                doc.save()
                print('Updated document: %s' % doc)
            else:
                print('Already have document: %s' % doc)

        except Document.DoesNotExist:

            html_filename = maybe_download_document(path_html, parliament.parliament_num, issue_num)
            pdf_filename = maybe_download_document(path_pdf, parliament.parliament_num, issue_num)

            doc = Document()
            doc.doc_num = doc_num
            doc.doc_type = doc_type
            doc.time_published = time_published
            doc.is_main = is_main
            doc.html_remote_path = path_html
            doc.html_filename = html_filename
            doc.pdf_remote_path = path_pdf
            doc.pdf_filename = pdf_filename
            doc.issue = issue
            doc.save()

            print('Added document: %s' % doc)

        # Process proposers.
        proposer_ids = []
        for proposer_xml in doc_xml.getElementsByTagName(u'flutningsmenn'):
            committeepart = None # Reset from possible previous iteration

            committee_xml = proposer_xml.getElementsByTagName(u'nefnd')
            if len(committee_xml) > 0:
                # NOTE: This try/except should be removed once the XML is fixed and committees are displayer properly.
                try:
                    committee_xml_id = int(committee_xml[0].getAttribute('id'))
                except ValueError:
                    print('Warning! Document is missing committee ID in Parliament %d, issue %d, document %d! Assumed "sérnefnd". Tell the XML keeper!' % (parliament.parliament_num, issue.issue_num, doc.doc_num), file=stderr)
                    committee_xml_id = Committee.objects.get(abbreviation_short='sn').committee_xml_id

                committee = update_committee(committee_xml_id, parliament.parliament_num)

                committee_partname_node = committee_xml[0].getElementsByTagName(u'hluti')[0].firstChild

                committee_partname = committee_partname_node.nodeValue if committee_partname_node else ''

                try:
                    proposer = Proposer.objects.get(document=doc, committee=committee, committee_partname=committee_partname)

                    print('Already have proposer: %s on document %s' % (proposer, doc))

                except Proposer.DoesNotExist:
                    proposer = Proposer()
                    proposer.committee = committee
                    proposer.committee_partname = committee_partname
                    proposer.document = doc
                    proposer.save()

                    print('Added proposer: %s to document %s' % (proposer, doc))

                proposer_ids.append(proposer.id)

                persons_xml = committee_xml[0].getElementsByTagName(u'flutningsmaður')
                subproposer_ids = []
                for person_xml in persons_xml:
                    person_xml_id = int(person_xml.getAttribute(u'id'))
                    order = int(person_xml.getAttribute(u'röð'))

                    person = update_person(person_xml_id, parliament.parliament_num)

                    try:
                        subproposer = Proposer.objects.get(parent=proposer, person=person)

                        print('Already have sub-proposer: %s on committee %s' % (subproposer, committee))

                    except Proposer.DoesNotExist:
                        subproposer = Proposer()
                        subproposer.person = person
                        subproposer.order = order
                        subproposer.parent = proposer
                        subproposer.save()

                        print('Added sub-proposer: %s to committee %s' % (subproposer, committee))

                    subproposer_ids.append(subproposer.id)

                # Delete sub-proposers that no longer exist online.
                for subproposer in Proposer.objects.filter(parent=proposer).exclude(id__in=subproposer_ids):
                    subproposer.delete()
                    print('Deleted non-existent sub-proposer: %s' % subproposer)

            else:
                persons_xml = proposer_xml.getElementsByTagName(u'flutningsmaður')
                for person_xml in persons_xml:
                    person_xml_id = int(person_xml.getAttribute(u'id'))

                    order = int(person_xml.getAttribute(u'röð'))

                    person = update_person(person_xml_id, parliament.parliament_num)

                    try:
                        proposer = Proposer.objects.get(document=doc, person=person)

                        print('Already have proposer: %s on document %s' % (proposer, doc))

                    except Proposer.DoesNotExist:
                        proposer = Proposer()
                        proposer.person = person
                        proposer.order = order
                        proposer.document = doc
                        proposer.save()

                        print('Added proposer: %s to document %s' % (proposer, doc))

                    proposer_ids.append(proposer.id)

        # Delete proposers that no longer exist online.
        for proposer in Proposer.objects.filter(document=doc).exclude(id__in=proposer_ids):
            proposer.delete()
            print('Deleted non-existent proposer: %s' % proposer)

    # Delete local documents that no longer exist online.
    for document in Document.objects.filter(issue_id=issue.id).exclude(doc_num__in=doc_nums):
        document.delete()
        print('Deleted non-existent document: %s' % document)

    # Process reviews.
    log_nums = [] # Keep track of legit reviews. Sometimes reviews get deleted from the XML and so should be deleted locally.
    for review_xml in reviews_xml:
        log_num = int(review_xml.getAttribute(u'dagbókarnúmer'))

        log_nums.append(log_num)

        try:
            sender_name = review_xml.getElementsByTagName(u'sendandi')[0].firstChild.nodeValue
        except AttributeError:
            # Review with log_num 1057 in Parliament 112 lacks a name. Others do not exist.
            sender_name = ''
        try:
            sender_name_description = review_xml.getElementsByTagName(u'skýring')[0].firstChild.nodeValue
        except (AttributeError, IndexError):
            sender_name_description = ''

        review_type = review_xml.getElementsByTagName(u'tegunderindis')[0].getAttribute('tegund')
        try:
            date_arrived = review_xml.getElementsByTagName(u'komudagur')[0].firstChild.nodeValue
        except AttributeError:
            date_arrived = None
        try:
            date_sent = review_xml.getElementsByTagName(u'sendingadagur')[0].firstChild.nodeValue
        except AttributeError:
            date_sent = None

        try:
            committee_xml_id = int(review_xml.getElementsByTagName(u'nefnd')[0].getAttribute(u'id'))
            committee = update_committee(committee_xml_id, parliament.parliament_num)
            committee_id = committee.id
        except IndexError:
            committee_id = None

        # sender_name can contain a lot of baggage if it's old data (around 116th parliament and earlir)
        sender_name = sender_name.strip()
        while sender_name.find('  ') >= 0:
            sender_name = sender_name.replace('  ', ' ')

        paths_xml = review_xml.getElementsByTagName(u'slóð')
        pdf_paths_xml = paths_xml[0].getElementsByTagName(u'pdf')

        path_pdf = pdf_paths_xml[0].firstChild.nodeValue

        try:
            review = Review.objects.get(log_num=log_num, issue=issue)

            changed = False
            if review.sender_name != sender_name:
                review.sender_name = sender_name
                changed = True

            if review.sender_name_description != sender_name_description:
                review.sender_name_description = sender_name_description
                changed = True

            if review.committee_id != committee_id:
                review.committee_id = committee_id
                changed = True

            if review.review_type != review_type:
                review.review_type = review_type
                changed = True

            if sensible_datetime(review.date_arrived) != sensible_datetime(date_arrived):
                review.date_arrived = date_arrived
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

        except Review.DoesNotExist:

            pdf_filename = maybe_download_review(path_pdf, log_num, parliament.parliament_num, issue_num)

            review = Review()
            review.issue = issue
            review.log_num = log_num
            review.sender_name = sender_name
            review.sender_name_description = sender_name_description
            review.committee_id = committee_id
            review.review_type = review_type
            review.date_arrived = date_arrived
            review.date_sent = date_sent
            review.pdf_remote_path = path_pdf
            review.pdf_filename = pdf_filename
            review.save()

            print('Added review: %s' % review)

    # Delete local reviews that no longer exist online.
    for review in Review.objects.filter(issue_id=issue.id).exclude(log_num__in=log_nums):
        review.delete()
        print('Deleted non-existent review: %s' % review)

    already_haves['issues'][ah_key] = issue

    # Process previous publications of issue, if any
    for previous_issue_info in previously_published_as:
        previous_issue = update_issue(previous_issue_info['issue_num'], previous_issue_info['parliament_num'])
        issue.previous_issues.add(previous_issue)
        for more_previous_issue in previous_issue.previous_issues.all():
            issue.previous_issues.add(more_previous_issue)

    return issue


def _process_docless_issue(issue_xml):

    issue_num = int(issue_xml.getAttribute(u'málsnúmer'))
    parliament_num = int(issue_xml.getAttribute(u'þingnúmer'))

    parliament = update_parliament(parliament_num)

    name = issue_xml.getElementsByTagName(u'málsheiti')[0].firstChild.nodeValue
    issue_type = issue_xml.getElementsByTagName(u'málstegund')[0].getAttribute('id')

    try:
        special_inquisitor_xml = issue_xml.getElementsByTagName(u'málshefjandi')[0]
        special_responder_xml = issue_xml.getElementsByTagName(u'til_andsvara')[0]

        special_inquisitor = update_person(int(special_inquisitor_xml.getAttribute('id')), parliament.parliament_num)
        special_inquisitor_description = special_inquisitor_xml.firstChild.nodeValue
        special_responder = update_person(int(special_responder_xml.getAttribute('id')), parliament.parliament_num)
        special_responder_description = special_responder_xml.firstChild.nodeValue
    except IndexError:
        special_inquisitor = None
        special_inquisitor_description = None
        special_responder = None
        special_responder_description = None


    # Docless issue names can carry a lot of baggage if it's old data (around 116th parliament and earlier)
    name = name.strip()
    while name.find('  ') >= 0:
        name = name.replace('  ', ' ')

    try:
        issue = Issue.objects.get(issue_num=issue_num, issue_group='B', parliament__parliament_num=parliament.parliament_num)

        changed = False
        if issue.name != name:
            issue.name = name
            changed = True

        if issue.issue_type != issue_type:
            issue.issue_type = issue_type
            changed = True

        if issue.special_inquisitor != special_inquisitor:
            issue.special_inquisitor = special_inquisitor
            changed = True

        if issue.special_inquisitor_description != special_inquisitor_description:
            issue.special_inquisitor_description = special_inquisitor_description
            changed = True

        if issue.special_responder != special_responder:
            issue.special_responder = special_responder
            changed = True

        if issue.special_responder_description != special_responder_description:
            issue.special_responder_description = special_responder_description
            changed = True

        if changed:
            issue.save()
            print('Updated docless issue: %s' % issue.detailed())
        else:
            print('Already have docless issue: %s' % issue.detailed())

    except Issue.DoesNotExist:
        issue = Issue()
        issue.issue_num = issue_num
        issue.issue_group = 'B'
        issue.name = name
        issue.issue_type = issue_type
        issue.special_inquisitor = special_inquisitor
        issue.special_inquisitor_description = special_inquisitor_description
        issue.special_responder = special_responder
        issue.special_responder_description = special_responder_description
        # issue.description = description # NOTE: This never *seems* to be used
        issue.parliament = parliament
        issue.save()

        print('Added docless issue: %s' % issue.detailed())

    return issue


def update_sessions(parliament_num=None, date_limit=None):

    parliament = update_parliament(parliament_num)

    if date_limit is not None:
        date_limit = sensible_datetime(date_limit)

    sessions_xml = get_xml('SESSION_LIST_URL', parliament.parliament_num)
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

    parliament = update_parliament(parliament_num)

    ah_key = '%d-%d' % (session_num, parliament.parliament_num)
    if already_haves['sessions'].has_key(ah_key):
        return already_haves['sessions'][ah_key]

    session_full_xml = get_xml('SESSION_AGENDA_URL', parliament.parliament_num, session_num)
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

    session = _process_session_agenda_xml(session_xml)

    already_haves['sessions'][ah_key] = session

    return session


def update_next_sessions():

    session_full_xml = get_xml('SESSION_NEXT_AGENDA_URL')
    sessions_xml = session_full_xml.getElementsByTagName(u'þingfundur')
    sessions = []
    for session_xml in sessions_xml:
        session = _process_session_agenda_xml(session_xml)
        sessions.append(session)

    # These are sessions that are upcoming according to the database but not according to the XML.
    # We run them through update_session() for consistency's sake, which will delete or update them appropriately.
    dubious_sessions = Session.objects.select_related('parliament').upcoming().exclude(id__in=[s.id for s in sessions])
    for dubious_session in dubious_sessions:
        update_session(dubious_session.session_num, dubious_session.parliament.parliament_num)


def update_constituencies(parliament_num=None):

    parliament = update_parliament(parliament_num)

    ah_key = parliament.parliament_num
    if already_haves['constituencies'].has_key(ah_key):
        return already_haves['constituencies'][ah_key]

    constituencies_xml = get_xml('CONSTITUENCIES_URL', parliament.parliament_num)

    constituencies = []
    for constituency_xml in constituencies_xml.getElementsByTagName(u'kjördæmin')[0].getElementsByTagName(u'kjördæmið'):
        abbreviations_xml = constituency_xml.getElementsByTagName(u'skammstafanir')[0]
        period_xml = constituency_xml.getElementsByTagName(u'tímabil')[0]

        constituency_xml_id = int(constituency_xml.getAttribute(u'id'))

        if constituency_xml_id == 1: # Only there for ministers not in Parliament and is to be ignored.
            continue

        name = constituency_xml.getElementsByTagName(u'heiti')[0].childNodes[1].nodeValue
        try:
            description = constituency_xml.getElementsByTagName(u'lýsing')[0].childNodes[1].nodeValue
        except (AttributeError, IndexError):
            description = ''
        abbreviation_short = abbreviations_xml.getElementsByTagName(u'stuttskammstöfun')[0].firstChild.nodeValue
        try:
            abbreviation_long = abbreviations_xml.getElementsByTagName(u'löngskammstöfun')[0].firstChild.nodeValue
        except (AttributeError, IndexError):
            abbreviation_long = None

        parliament_num_first = int(period_xml.getElementsByTagName(u'fyrstaþing')[0].firstChild.nodeValue)
        try:
            parliament_num_last = int(period_xml.getElementsByTagName(u'síðastaþing')[0].firstChild.nodeValue)
        except (AttributeError, IndexError):
            parliament_num_last = None

        try:
            constituency = Constituency.objects.get(constituency_xml_id=constituency_xml_id)

            changed = False
            if constituency.name != name:
                constituency.name = name
                changed = True
            if constituency.description != description:
                constituency.description = description
                changed = True
            if constituency.abbreviation_short != abbreviation_short:
                constituency.abbreviation_short = abbreviation_short
                changed = True
            if constituency.abbreviation_long != abbreviation_long:
                constituency.abbreviation_long = abbreviation_long
                changed = True
            if constituency.parliament_num_first != parliament_num_first:
                constituency.parliament_num_first = parliament_num_first
                changed = True
            if constituency.parliament_num_last != parliament_num_last:
                constituency.parliament_num_last = parliament_num_last
                changed = True

            if parliament not in constituency.parliaments.all():
                constituency.parliaments.add(parliament)
                changed = True

            if changed:
                constituency.save()
                print('Updated constituency: %s' % constituency)
            else:
                print('Already have constituency: %s' % constituency)

        except Constituency.DoesNotExist:
            constituency = Constituency()
            constituency.name = name
            constituency.description = description
            constituency.abbreviation_short = abbreviation_short
            constituency.abbreviation_long = abbreviation_long
            constituency.parliament_num_first = parliament_num_first
            constituency.parliament_num_last = parliament_num_last
            constituency.constituency_xml_id = constituency_xml_id
            constituency.save()
            constituency.parliaments.add(parliament)

            print('Added constituency: %s' % constituency)

        constituencies.append(constituency)

    already_haves['constituencies'][parliament.parliament_num] = constituencies

    return constituencies


def update_parties(parliament_num=None):

    parliament = update_parliament(parliament_num)

    ah_key = parliament.parliament_num
    if already_haves['parties'].has_key(ah_key):
        return already_haves['parties'][ah_key]

    parties_xml = get_xml('PARTIES_URL', parliament.parliament_num)

    parties = []
    for party_xml in parties_xml.getElementsByTagName(u'þingflokkar')[0].getElementsByTagName(u'þingflokkur'):
        abbreviations_xml = party_xml.getElementsByTagName(u'skammstafanir')[0]
        period_xml = party_xml.getElementsByTagName(u'tímabil')[0]

        party_xml_id = party_xml.getAttribute(u'id')
        name = party_xml.getElementsByTagName(u'heiti')[0].firstChild.nodeValue.strip()

        if name == '':
            continue

        abbreviation_short = abbreviations_xml.getElementsByTagName(u'stuttskammstöfun')[0].firstChild.nodeValue
        abbreviation_long = abbreviations_xml.getElementsByTagName(u'löngskammstöfun')[0].firstChild.nodeValue

        parliament_num_first = int(period_xml.getElementsByTagName(u'fyrstaþing')[0].firstChild.nodeValue)
        try:
            parliament_num_last = int(period_xml.getElementsByTagName(u'síðastaþing')[0].firstChild.nodeValue)
        except (AttributeError, IndexError):
            parliament_num_last = None

        try:
            party = Party.objects.get(party_xml_id=party_xml_id)

            changed = False
            if party.name != name:
                party.name = name
                changed = True
            if party.abbreviation_short != abbreviation_short:
                party.abbreviation_short = abbreviation_short
                changed = True
            if party.abbreviation_long != abbreviation_long:
                party.abbreviation_long = abbreviation_long
                changed = True
            if party.parliament_num_first != parliament_num_first:
                party.parliament_num_first = parliament_num_first
                changed = True
            if party.parliament_num_last != parliament_num_last:
                party.parliament_num_last = parliament_num_last
                changed = True

            if parliament not in party.parliaments.all():
                party.parliaments.add(parliament)
                changed = True

            if changed:
                party.save()
                print('Updated party: %s' % party)
            else:
                print('Already have party: %s' % party)

        except Party.DoesNotExist:
            party = Party()

            party.name = name
            party.abbreviation_short = abbreviation_short
            party.abbreviation_long = abbreviation_long
            party.parliament_num_first = parliament_num_first
            party.parliament_num_last = parliament_num_last
            party.party_xml_id = party_xml_id
            party.save()
            party.parliaments.add(parliament)

            print('Added party: %s' % party)

        parties.append(party)

    already_haves['parties'][parliament.parliament_num] = parties

    return parties

def update_committee_agendas(parliament_num=None, date_limit=None):

    parliament = update_parliament(parliament_num)

    if date_limit is not None:
        date_limit = sensible_datetime(date_limit)

    committee_agenda_list_xml = get_xml('COMMITTEE_AGENDA_LIST_URL', parliament.parliament_num)
    committee_agenda_stubs_xml = committee_agenda_list_xml.getElementsByTagName(u'nefndarfundur')
    committee_agendas = []
    for committee_agenda_stub_xml in reversed(committee_agenda_stubs_xml):

        meeting_date = sensible_datetime(committee_agenda_stub_xml.getElementsByTagName(u'dagur')[0].firstChild.nodeValue)
        if date_limit is not None and meeting_date < date_limit:
            break

        committee_agenda_xml_id = int(committee_agenda_stub_xml.getAttribute(u'númer'))
        committee_agenda = update_committee_agenda(committee_agenda_xml_id, parliament.parliament_num)

        committee_agendas.append(committee_agenda)

    # Delete committee agendas that no longer exist in the requested
    # parliament. We'll skip this if we're searching by date_limit because
    # then the search criteria is no longer valid.
    if date_limit is None:
        for committee_agenda in CommitteeAgenda.objects.filter(
            parliament__parliament_num=parliament.parliament_num
        ).exclude(id__in=[a.id for a in committee_agendas]):
            # Safe delete. The function will delete the agenda if it truly no longer exists.
            update_committee_agenda(committee_agenda.committee_agenda_xml_id, parliament.parliament_num)

    return committee_agendas


def update_next_committee_agendas(parliament_num=None):
    now = datetime.now()
    today = datetime(now.year, now.month, now.day)

    agendas = update_committee_agendas(parliament_num=parliament_num, date_limit=today)

    # These are agendas that are upcoming according to the database but not according to the XML.
    # We run them through update_committee_agenda() for consistency's sake, which will delete or update them appropriately.
    dubious_agendas = CommitteeAgenda.objects.select_related('parliament').upcoming().exclude(id__in=[a.id for a in agendas])
    for dubious_agenda in dubious_agendas:
        update_committee_agenda(dubious_agenda.committee_agenda_xml_id, dubious_agenda.parliament.parliament_num)


def update_committee_agenda(committee_agenda_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)

    try:
        committee_agenda_full_xml = get_xml('COMMITTEE_AGENDA_URL', committee_agenda_xml_id)
    except ExpatError:
        raise AlthingiException('Committee agenda with XML-ID %d not found' % committee_agenda_xml_id)

    committee_agenda_xml = committee_agenda_full_xml.getElementsByTagName(u'nefndarfundur')[0]

    if not committee_agenda_xml.getAttribute(u'númer'):
        # Committee agenda has been deleted in XML, meaning cancelled.
        CommitteeAgenda.objects.get(committee_agenda_xml_id=committee_agenda_xml_id).delete()

        print('Deleted non-existent committee agenda: %d' % committee_agenda_xml_id)
        return
    elif int(committee_agenda_xml.getAttribute(u'þingnúmer')) != parliament.parliament_num:
        # Committee agenda exists, but not in this parliament. (A corrected
        # mistake in the XML, most likely.)
        CommitteeAgenda.objects.get(
            committee_agenda_xml_id=committee_agenda_xml_id,
            parliament__parliament_num=parliament.parliament_num
        ).delete()
        print('Deleted committee agenda from parliament: %d (parliament %d)' % (
            committee_agenda_xml_id,
            parliament.parliament_num)
        )
        return

    return _process_committee_agenda_xml(committee_agenda_xml) # Returns CommitteeAgenda object


# NOTE: To become a private function once we turn this into some sort of class
def _process_committee_agenda_xml(committee_agenda_xml):

    parliament_num = int(committee_agenda_xml.getAttribute(u'þingnúmer'))
    committee_agenda_xml_id = int(committee_agenda_xml.getAttribute(u'númer'))
    committee_xml_id = int(committee_agenda_xml.getElementsByTagName(u'nefnd')[0].getAttribute('id'))

    parliament = update_parliament(parliament_num)
    committee = update_committee(committee_xml_id, parliament_num)

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

    try:
        committee_agenda = CommitteeAgenda.objects.get(committee_agenda_xml_id=committee_agenda_xml_id, parliament=parliament)

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

    except CommitteeAgenda.DoesNotExist:
        committee_agenda = CommitteeAgenda()
        committee_agenda.parliament = parliament
        committee_agenda.committee = committee
        committee_agenda.committee_agenda_xml_id = committee_agenda_xml_id
        committee_agenda.timing_start_planned = timing_start_planned
        committee_agenda.timing_start = timing_start
        committee_agenda.timing_end = timing_end
        committee_agenda.timing_text = timing_text
        committee_agenda.save()

        print('Added committee agenda: %s' % committee_agenda)

    max_order = 0
    items_xml = committee_agenda_xml.getElementsByTagName(u'dagskrárliður')
    for item_xml in items_xml:
        order = int(item_xml.getAttribute(u'númer'))

        try:
            name = item_xml.getElementsByTagName(u'heiti')[0].firstChild.nodeValue
        except AttributeError:
            name = '[ Missing name ]'

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
            try:
                issue = update_issue(issue_num, issue_parliament_num)
            except AlthingiException:
                # If the update_issue function fails here, something is wrong
                # in the XML. We'll move on with our lives. Probably, the only
                # indication will be that the order of agenda items will be
                # missing a number, which will heal when the updater is run
                # again once the XML has been fixed.
                continue

        try:
            item = CommitteeAgendaItem.objects.get(order=order, committee_agenda=committee_agenda)

            changed = False
            if item.name != name:
                item.name = name
                changed = True
            if item.issue != issue:
                item.issue = issue
                changed = True

            if changed:
                item.save()
                print('Updated committee agenda item: %s' % item)
            else:
                print('Already have committee agenda item: %s' % item)

        except CommitteeAgendaItem.DoesNotExist:
            item = CommitteeAgendaItem()
            item.committee_agenda = committee_agenda
            item.order = order
            item.name = name
            item.issue = issue
            item.save()

            print('Added committee agenda item: %s' % item)

    # Delete items higher than the max_order since that means items has been dropped
    CommitteeAgendaItem.objects.filter(order__gt=max_order, committee_agenda=committee_agenda).delete()

    return committee_agenda

# NOTE: To become a private function once we turn this into some sort of class
def _process_session_agenda_xml(session_xml):

    parliament_num = int(session_xml.getAttribute(u'þingnúmer'))
    session_num = int(session_xml.getAttribute(u'númer'))

    parliament = update_parliament(parliament_num)

    name = session_xml.getElementsByTagName(u'fundarheiti')[0].firstChild.nodeValue

    begins_xml = session_xml.getElementsByTagName(u'hefst')[0]
    timing_start_planned_xml = begins_xml.getElementsByTagName(u'dagurtími')
    if len(timing_start_planned_xml) > 0:
        timing_start_planned = sensible_datetime(timing_start_planned_xml[0].firstChild.nodeValue)
    else:
        timing_start_planned = None

    timing_text_xml = begins_xml.getElementsByTagName(u'texti')
    if len(timing_text_xml) > 0:
        timing_text = timing_text_xml[0].firstChild.nodeValue
    else:
        timing_text = None

    try:
        timing_start = sensible_datetime(session_xml.getElementsByTagName(u'fundursettur')[0].firstChild.nodeValue)
    except AttributeError:
        timing_start = None
    try:
        timing_end = sensible_datetime(session_xml.getElementsByTagName(u'fuslit')[0].firstChild.nodeValue)
    except AttributeError:
        timing_end = None

    try:
        session = Session.objects.get(session_num=session_num, parliament=parliament)

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
        if session.timing_text != timing_text:
            session.timing_text = timing_text
            changed = True

        if changed:
            session.save()
            print('Updated session: %s' % session)
        else:
            print('Already have session: %s' % session)

    except Session.DoesNotExist:
        session = Session()
        session.parliament = parliament
        session.session_num = session_num
        session.name = name
        session.timing_start_planned = timing_start_planned
        session.timing_start = timing_start
        session.timing_end = timing_end
        session.timing_text = timing_text
        session.save()
        print('Added session: %s' % session)

    # Prepare for agenda processing.
    session_agenda_full_xml = get_xml('SESSION_AGENDA_URL', parliament.parliament_num, session_num)
    session_agenda_xml = session_agenda_full_xml.getElementsByTagName(u'dagskrá')[0]

    max_order = 0
    for session_agenda_item_xml in session_agenda_xml.getElementsByTagName(u'dagskrárliður'):
        issue_xml = session_agenda_item_xml.getElementsByTagName(u'mál')[0]
        discussion_xml = session_agenda_item_xml.getElementsByTagName(u'umræða')[0]
        comment_xml = session_agenda_item_xml.getElementsByTagName(u'athugasemd')

        order = int(session_agenda_item_xml.getAttribute(u'númer'))

        discussion_type = discussion_xml.getAttribute(u'tegund')
        discussion_continued = bool(discussion_xml.getAttribute(u'framhald'))

        if len(comment_xml) > 0:
            comment_entity_xml = comment_xml[0]

            comment_type = comment_entity_xml.getAttribute(u'tegund')
            comment_text = comment_entity_xml.getElementsByTagName(u'dagskrártexti')[0].firstChild.nodeValue
            comment_description = comment_entity_xml.getElementsByTagName(u'skýring')[0].firstChild.nodeValue
        else:
            comment_type = None
            comment_text = None
            comment_description = None

        issue_num = int(issue_xml.getAttribute(u'málsnúmer'))
        issue_group = issue_xml.getAttribute(u'málsflokkur')

        if issue_group == 'A':
            issue = update_issue(issue_num, parliament.parliament_num)
        elif issue_group == 'B':
            issue = _process_docless_issue(issue_xml)

        if order > max_order:
            max_order = order

        try:
            item = SessionAgendaItem.objects.select_related('issue').get(session_id=session.id, order=order)

            changed = False
            if item.issue_id != issue.id:
                item.issue = issue
                changed = True
            if item.discussion_type != discussion_type:
                item.discussion_type = discussion_type
                changed = True
            if item.discussion_continued != discussion_continued:
                item.discussion_continued = discussion_continued
                changed = True
            if item.comment_type != comment_type:
                item.comment_type = comment_type
                changed = True
            if item.comment_text != comment_text:
                item.comment_text = comment_text
                changed = True
            if item.comment_description != comment_description:
                item.comment_description = comment_description
                changed = True

            if changed:
                item.save()
                print('Updated session agenda item: %s' % item)
            else:
                print('Already have session agenda item: %s' % item)

        except SessionAgendaItem.DoesNotExist:
            item = SessionAgendaItem()
            item.session = session
            item.order = order
            item.discussion_type = discussion_type
            item.discussion_continued = discussion_continued
            item.comment_type = comment_type
            item.comment_text = comment_text
            item.comment_description = comment_description
            item.issue = issue
            item.save()

            print('Added session agenda item: %s' % item)

    for item in SessionAgendaItem.objects.filter(session_id=session.id, order__gt=max_order):
        item.delete()

        print('Deleted session agenda item %s' % item)

    return session
