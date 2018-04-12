from collections import OrderedDict
from datetime import datetime
from django.db.models import Q
from sys import stderr
from sys import stdout
from xml.parsers.expat import ExpatError

from althingi.althingi_settings import FIRST_PARLIAMENT_NUM

from althingi.models import Category
from althingi.models import CategoryGroup
from althingi.models import Committee
from althingi.models import CommitteeAgenda
from althingi.models import CommitteeAgendaItem
from althingi.models import CommitteeSeat
from althingi.models import Constituency
from althingi.models import Document
from althingi.models import Issue
from althingi.models import IssueSummary
from althingi.models import IssueStep
from althingi.models import Minister
from althingi.models import MinisterSeat
from althingi.models import Parliament
from althingi.models import Party
from althingi.models import Person
from althingi.models import President
from althingi.models import PresidentSeat
from althingi.models import Proposer
from althingi.models import Rapporteur
from althingi.models import Review
from althingi.models import Seat
from althingi.models import Session
from althingi.models import SessionAgendaItem
from althingi.models import Speech
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
    'category_grpups': {},
    'parliaments': {},
    'parties': {},
    'persons': {},
    'ministers': {},
    'minister_seats': {},
    'presidents': {},
    'president_seats': {},
    'seats': {},
    'committees': {},
    'committee_seats': {},
    'constituencies': {},
    'issues': {},
    'sessions': {},
    'speeches': {},
    'vote_castings': {},

    'xml': {},
}


def clear_already_haves():
    for varname in already_haves:
        already_haves[varname] = {}


def update_parliament(parliament_num):

    last_parliament_num = get_last_parliament_num()

    # Make sure that input makes sense
    if parliament_num is not None and not isinstance(parliament_num, int):
        raise TypeError('Function update_parliament() expects either None or exactly one integer as input')

    # Default to most recent parliament number if nothing is provided
    parliament_num = parliament_num if parliament_num else last_parliament_num

    # Make sure that the parliament number makes sense (information before the 20th does not exist)
    if parliament_num < FIRST_PARLIAMENT_NUM or parliament_num > last_parliament_num:
        raise AlthingiException('Parliament number must be between %d and %d' % (FIRST_PARLIAMENT_NUM, last_parliament_num))

    if parliament_num in already_haves['parliaments']:
        return already_haves['parliaments'][parliament_num]

    xml = get_xml('PARLIAMENT_URL', parliament_num).find('þing')

    if xml is None:
        raise AlthingiException('Parliament %s could not be found' % parliament_num)

    era = xml.find('tímabil').text
    timing_start = sensible_datetime(xml.find('þingsetning').text)
    try:
        timing_end = sensible_datetime(xml.find('þinglok').text)
    except AttributeError:
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

    # We'll combine the lists of MPs and ministers.
    xml_mp = get_xml('PERSONS_MPS_URL', parliament.parliament_num).findall('þingmaður')
    xml_min = get_xml('PERSONS_MINISTERS_URL', parliament.parliament_num).findall('ráðherra')

    person_xml_ids = [int(a.attrib['id']) for a in xml_mp] + [int(a.attrib['id']) for a in xml_min]

    for person_xml_id in person_xml_ids:
        update_person(person_xml_id, parliament.parliament_num)


def update_person(person_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)

    # Make sure that input makes sense
    if person_xml_id is not None and not isinstance(person_xml_id, int):
        raise TypeError('Parameter person_xml_id must be a number')

    # Cached by parliament_num as well, to make sure that if we're iterating
    # through multiple parliaments, we also catch the seats and committee
    # seats below.
    ah_key = '%d-%d' % (parliament.parliament_num, person_xml_id)
    if ah_key in already_haves['persons']:
        return already_haves['persons'][ah_key]

    xml = get_xml('PERSON_URL', person_xml_id)
    if xml.tag != 'þingmaður':
        raise AlthingiException('Person with XML-ID %d not found' % person_xml_id)

    try:
        email_name = xml.find('netfang/nafn').text
        email_domain = xml.find('netfang/lén').text
        email = '%s@%s' % (email_name, email_domain)
    except AttributeError:
        email = None

    try:
        facebook_url = xml.find('facebook').text
    except AttributeError:
        facebook_url = None

    try:
        twitter_url = xml.find('twitter').text
    except AttributeError:
        twitter_url = None

    try:
        youtube_url = xml.find('youtube').text
    except AttributeError:
        youtube_url = None

    try:
        blog_url = xml.find('blogg').text
    except AttributeError:
        blog_url = None

    try:
        website_url = xml.find('vefur').text
    except AttributeError:
        website_url = None

    name = xml.find('nafn').text
    birthdate = sensible_datetime(xml.find('fæðingardagur').text)

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
    update_minister_seats(person_xml_id, parliament.parliament_num)

    return person


def update_seats(person_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)
    person = update_person(person_xml_id, parliament.parliament_num)

    ah_key = '%d-%d' % (parliament.parliament_num, person_xml_id)
    if ah_key in already_haves['seats']:
        return already_haves['seats'][ah_key]

    update_constituencies(parliament.parliament_num)
    update_parties(parliament.parliament_num)

    xml = get_xml('SEATS_URL', person_xml_id).findall('þingsetur/þingseta')

    seats = []
    for seat_xml in xml:
        seat_parliament_num = int(seat_xml.find('þing').text)

        if seat_parliament_num == parliament.parliament_num:
            seat_type = seat_xml.find('tegund').text

            name_abbreviation = seat_xml.find('skammstöfun').text

            try:
                physical_seat_number = int(seat_xml.find('þingsalssæti').text)
            except (AttributeError, TypeError):
                physical_seat_number = None

            timing_in = sensible_datetime(seat_xml.find('tímabil/inn').text)

            try:
                timing_out = sensible_datetime(seat_xml.find('tímabil/út').text)
            except AttributeError:
                timing_out = None

            constituency_xml_id = int(seat_xml.find('kjördæmi').attrib['id'])
            constituency_mp_num = int(seat_xml.find('kjördæmanúmer').text)

            party_xml_id = int(seat_xml.find('þingflokkur').attrib['id'])

            try:
                seat = Seat.objects.get(
                    person=person,
                    parliament__parliament_num=parliament.parliament_num,
                    timing_in=timing_in,
                    timing_out=timing_out
                )

                print('Already have seat: %s' % seat)

            except Seat.DoesNotExist:
                seat = Seat()
                seat.person = person
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


def update_vote_castings(parliament_num=None, since=None):

    parliament = update_parliament(parliament_num)
    since = sensible_datetime(since)

    # Needed for some vote castings that cannot update individual ministers.
    update_ministers(parliament.parliament_num)
    update_committees(parliament.parliament_num)

    pref_persons = {p.person_xml_id: p for p in Person.objects.all()}
    pref_sessions = {s.session_num: s for s in Session.objects.filter(parliament_id=parliament.id)}
    pref_issues = {i.issue_num: i for i in Issue.objects.prefetch_related('documents').filter(
        issue_group='A',
        parliament_id=parliament.id,
    )}
    # We need names as keys because of weird XML explained below.
    pref_committees = {c.name: c for c in parliament.committees.all()}
    pref_ministers = {m.name: m for m in parliament.ministers.all()}
    pref_vote_castings = {vc.vote_casting_xml_id: vc for vc in VoteCasting.objects.filter(
        session__parliament__parliament_num=parliament.parliament_num
    )}
    pref_votes = {
        '%d-%d' % (
            v.vote_casting.vote_casting_xml_id,
            v.person.person_xml_id
        ): v for v in Vote.objects.select_related('vote_casting','person').filter(
            vote_casting__session__parliament_id=parliament.id
        )
    }

    for xml in get_xml('VOTE_CASTINGS_URL', parliament.parliament_num).findall('atkvæðagreiðsla'):

        # We get the timing first to see if we we to process this any further.
        timing = sensible_datetime(xml.find('tími').text)
        if since and timing < since:
            continue

        vote_casting_xml_id = int(xml.attrib['atkvæðagreiðslunúmer'])

        issue_num = int(xml.attrib['málsnúmer'])

        issue_group = xml.attrib['málsflokkur']

        if issue_group == 'A':
            try:
                issue = pref_issues[issue_num]
            except KeyError:
                issue = update_issue(issue_num, parliament.parliament_num)

            doc_num = int(xml.find('þingskjal').attrib['skjalsnúmer'])
            document = issue.documents.get(doc_num=doc_num)
        # NOTE / TODO: Waiting for B-issue types to appear in XML for vote castings.
        #elif issue_group == 'B':
        #    docless_issue_xml = vote_casting_xml.find('mál')
        #    issue = _process_docless_issue(docless_issue_xml)
        #    document = None
        else:
            issue = None
            document = None

        vote_casting_type = xml.find('tegund').attrib['tegund']

        vote_casting_type_text = xml.find('tegund').text

        try:
            specifics = xml.find('nánar').text.strip()
        except AttributeError:
            specifics = ''

        session_num = int(xml.find('fundur').text)
        try:
            session = pref_sessions[session_num]
        except KeyError:
            session = update_session(session_num, parliament.parliament_num)

        try:
            # NOTE/TODO: The XML is a bit buggy at the moment (2018-04-11). If
            # individual vote castings are looked up in the XML, then we see
            # clearly whether the vote is sending something to a committee or
            # a minister. We also receive the ID, like so:
            #
            #     <til id="[xml-id-of-committee]">
            #         [name-of-committee]
            #     </til>
            #     <tilráðherra id="[xml-id-of-minister]">
            #         [name-of-minister]
            #     </tilráðherra>
            #
            # However, this distinction is not made in the total listing of
            # vote castings. For performance reasons, we wish to process the
            # total listing information instead of looking up every single
            # vote casting, every single time. Since we only have the name to
            # go by under the <til> tag, without an ID, we need to use the
            # name of whatever we find in the tag, and check locally if it's a
            # committee or a minister. We assume that they exist locally
            # because we've updated both early in this function.
            #
            # One day this will presumably be fixed, in which case this code
            # should be updated to something like:
            #
            #     try:
            #         committee_xml_id = int(xml.find('til').attrib['id'])
            #         to_committee = update_committee(committee_xml_id, parliament.parliament_num)
            #     except AttributeError:
            #         to_committee = None
            #
            #     try:
            #         minister_xml_id = int(xml.find('tilráðherra').attrib['id'])
            #         to_minister = Minister.objects.get(minister_xml_id=minister_xml_id)
            #     except AttributeError:
            #         to_minister = None

            to_mystery = xml.find('til').text

            if to_mystery in pref_committees:
                # It's a committee!
                to_committee = pref_committees[to_mystery]
                to_minister = None

            elif to_mystery in pref_ministers:
                # It's a minister!
                to_committee = None
                to_minister = pref_ministers[to_mystery]

            else:
                # We have no clue of what this thing is. We'll forget about it
                # and act as if nothing happened. It's probably some entity
                # outside of Parliament and government.
                to_committee = None
                to_minister = None

        except AttributeError:
            to_committee = None
            to_minister = None

        try:
            method = xml.find('samantekt/aðferð').text
        except AttributeError:
            method = None

        try:
            count_yes = int(xml.find('samantekt/já/fjöldi').text)
        except (AttributeError, TypeError):
            count_yes = None

        try:
            count_no = int(xml.find('samantekt/nei/fjöldi').text)
        except (AttributeError, TypeError):
            count_no = None

        try:
            count_abstain = int(xml.find('samantekt/greiðirekkiatkvæði/fjöldi').text)
        except (AttributeError, TypeError):
            count_abstain = None

        try:
            conclusion = xml.find('samantekt/afgreiðsla').text
        except AttributeError:
            conclusion = None

        if vote_casting_xml_id in pref_vote_castings:
            vote_casting = pref_vote_castings[vote_casting_xml_id]

            changed = False
            if sensible_datetime(vote_casting.timing) != sensible_datetime(timing):
                vote_casting.timing = sensible_datetime(timing)
                changed = True

            if vote_casting.vote_casting_type != vote_casting_type:
                vote_casting.vote_casting_type = vote_casting_type
                changed = True

            if vote_casting.vote_casting_type_text != vote_casting_type_text:
                vote_casting.vote_casting_type_text = vote_casting_type_text
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

            if vote_casting.to_minister != to_minister:
                vote_casting.to_minister = to_minister
                changed = True

            if changed:
                vote_casting.save()
                print('Updated vote casting: %s' % vote_casting)
            else:
                print('Already have vote casting: %s' % vote_casting)

        else:
            vote_casting = VoteCasting()

            vote_casting.timing = timing
            vote_casting.vote_casting_type = vote_casting_type
            vote_casting.vote_casting_type_text = vote_casting_type_text
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
            vote_casting.to_minister = to_minister
            vote_casting.vote_casting_xml_id = vote_casting_xml_id

            vote_casting.save()

            print('Added vote casting: %s' % vote_casting)

        if method != 'yfirlýsing forseta/mál gengur':

            xml = get_xml('VOTE_CASTING_URL', vote_casting_xml_id)

            # Process actual votes, if they exist.
            for vote_xml in xml.findall('atkvæðaskrá/þingmaður'):
                person_xml_id = int(vote_xml.attrib['id'])
                vote_response = vote_xml.find('atkvæði').text

                # NOTE: To be removed when XML is fixed.
                if vote_response == 'f: óþekktur kóði':
                    vote_response = 'boðaði fjarvist'

                try:
                    person = pref_persons[person_xml_id]
                except KeyError:
                    person = update_person(person_xml_id, parliament.parliament_num)

                if '%s-%s' % (vote_casting_xml_id, person_xml_id) in pref_votes:
                    vote = pref_votes['%s-%s' % (vote_casting_xml_id, person_xml_id)]

                    changed = False
                    if vote.vote_response != vote_response:
                        vote.vote_response = vote_response
                        changed = True

                    if changed:
                        vote.save()
                        print('Updated vote: %s' % vote)
                    else:
                        print('Already have vote: %s' % vote)
                else:
                    vote = Vote()
                    vote.vote_casting_id = vote_casting.id
                    vote.person_id = person.id
                    vote.vote_response = vote_response

                    vote.save()

                    print('Added vote: %s' % vote)


def update_committee_seats(person_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)
    person = update_person(person_xml_id, parliament.parliament_num)

    ah_key = '%d-%d' % (parliament.parliament_num, person_xml_id)
    if ah_key in already_haves['committee_seats']:
        return already_haves['committee_seats'][ah_key]

    xml = get_xml('COMMITTEE_SEATS_URL', person_xml_id).findall('nefndasetur/nefndaseta')

    committee_seats = []
    for committee_seat_xml in xml:
        committee_seat_parliament_num = int(committee_seat_xml.find('þing').text)

        if committee_seat_parliament_num == parliament.parliament_num:

            committee_xml_id = int(committee_seat_xml.find('nefnd').attrib['id'])
            committee = update_committee(committee_xml_id, parliament.parliament_num)

            committee_seat_type = committee_seat_xml.find('staða').text

            order = committee_seat_xml.find('röð').text

            timing_in = sensible_datetime(committee_seat_xml.find('tímabil/inn').text)

            try:
                timing_out = sensible_datetime(committee_seat_xml.find('tímabil/út').text)
            except AttributeError:
                timing_out = None

            try:
                committee_seat = CommitteeSeat.objects.filter(
                    person=person,
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
                committee_seat.person = person
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

    xml = get_xml('COMMITTEE_LIST_URL', parliament.parliament_num).findall('nefnd')

    for committee_xml in xml:
        committee_xml_id = int(committee_xml.attrib['id'])
        update_committee(committee_xml_id, parliament.parliament_num)


def update_committee(committee_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)

    # Make sure that input makes sense
    if committee_xml_id is not None and not isinstance(committee_xml_id, int):
        raise TypeError('Parameter committee_xml_id must be a number')

    ah_key = '%d-%d' % (parliament.parliament_num, committee_xml_id)
    if ah_key in already_haves['committees']:
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
        if xml_url in already_haves['xml']:
            xml = already_haves['xml'][xml_url]
        else:
            if parliament_num:
                xml = get_xml(xml_url_name, parliament_num).findall('nefnd')
            else:
                xml = get_xml(xml_url_name).findall('nefnd')
            already_haves['xml'][xml_url] = xml

        committee = None
        for committee_xml in xml:
            if int(committee_xml.attrib['id']) == committee_xml_id:

                name = committee_xml.find('heiti').text
                abbreviation_short = committee_xml.find('skammstafanir/stuttskammstöfun').text
                abbreviation_long = committee_xml.find('skammstafanir/löngskammstöfun').text

                parliament_num_first = int(committee_xml.find('tímabil/fyrstaþing').text)
                try:
                    parliament_num_last = int(committee_xml.find('tímabil/síðastaþing').text)
                except AttributeError:
                    parliament_num_last = None

                try:
                    committee = Committee.objects.get(committee_xml_id=committee_xml_id)

                    changed = False
                    if committee.name != name:
                        committee.name = name
                        changed = True

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

    if committee is None:
        raise AlthingiException('Committee with XML-ID %d does not exist' % committee_xml_id)

    already_haves['committees'][ah_key] = committee

    return committee


def update_issues(parliament_num=None):
    """
    Fetch a list of "recent" issues on Althingi and update our database accordingly.
    """

    parliament = update_parliament(parliament_num)

    xml = get_xml('ISSUE_LIST_URL', parliament.parliament_num).findall('mál')

    for issue_xml in xml:
        # We are only interested in A-issues (with documents).
        if issue_xml.attrib['málsflokkur'] != 'A':
            continue

        issue_num = int(issue_xml.attrib['málsnúmer'])

        update_issue(issue_num, parliament_num=parliament.parliament_num)


# NOTE: Only updates "A" issues, those with documents, reviews etc.
def update_issue(issue_num, parliament_num=None):

    parliament = update_parliament(parliament_num)

    # Make sure that input makes sense
    if issue_num is not None and not isinstance(issue_num, int):
        raise TypeError('Parameter issue_num must be a number')

    ah_key = '%d-%d' % (parliament.parliament_num, issue_num)
    if ah_key in already_haves['issues']:
        return already_haves['issues'][ah_key]

    update_categories()

    # If issue has been published in an earlier parliament, we'll record it in this variable and deal with it afterwards
    # Contains a list of structs, for exmaple: {'parliament_num': 144, 'issue_num': 524 }
    previously_published_as = []

    xml = get_xml('ISSUE_URL', parliament.parliament_num, issue_num)

    issue_xml = xml.find('mál')
    rapporteurs_xml = xml.findall('framsögumenn/framsögumaður')
    docstubs_xml = xml.findall('þingskjöl/þingskjal')
    reviews_xml = xml.findall('erindaskrá/erindi')

    if issue_xml is None:
        raise AlthingiException('Issue %d in parliament %d does not exist' % (issue_num, parliament.parliament_num))

    issue_type = issue_xml.find('málstegund').attrib['málstegund']

    name = issue_xml.find('málsheiti').text.strip()

    description = issue_xml.find('efnisgreining').text
    description = '' if description is None else description.strip()

    try:
        review_deadline = sensible_datetime(xml.find('umsagnabeiðnir').attrib['frestur'])
    except ValueError:
        review_deadline = None

    cat_xml_ids = []
    for cgx in xml.findall('efnisflokkar/yfirflokkur'):
        cat_xml_ids += [int(x.attrib['id']) for x in cgx.findall('efnisflokkur')]
    cat_xml_ids.sort() # Order should match, but just in case.

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

        if issue.review_deadline != review_deadline:
            issue.review_deadline = review_deadline
            changed = True

        if [c.category_xml_id for c in issue.categories.order_by('category_xml_id')] != cat_xml_ids:
            issue.categories.clear()
            for cat_xml_id in cat_xml_ids:
                issue.categories.add(Category.objects.get(category_xml_id=cat_xml_id))
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
        issue.review_deadline = review_deadline
        issue.parliament = parliament
        issue.save()

        for cat_xml_id in cat_xml_ids:
            issue.categories.add(Category.objects.get(category_xml_id=cat_xml_id))

        print('Added issue: %s' % issue.detailed())

    # Add or remove rapporteurs
    rapporteur_ids = []
    for rapporteur_xml in rapporteurs_xml:
        person_xml_id = int(rapporteur_xml.attrib['id'])
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
    for previous_issue_xml in xml.findall('tengdMál/lagtFramÁðurSem/mál'):
        previous_parliament_num = int(previous_issue_xml.attrib['þingnúmer'])
        previous_issue_num = int(previous_issue_xml.attrib['málsnúmer'])

        previously_published_as.append({
            'parliament_num': previous_parliament_num,
            'issue_num': previous_issue_num,
        })

    # See if this issue has summary information
    summary_xml_try = issue_xml.find('samantekt')
    if summary_xml_try is not None:
        # Yes, it has summary information
        summary_xml = get_xml('ISSUE_SUMMARY_URL', parliament.parliament_num, issue.issue_num)

        purpose = summary_xml.find('markmið').text
        try:
            change_description = summary_xml.find('helstuBreytingar').text
        except AttributeError:
            change_description = ''
        try:
            changes_to_law = summary_xml.find('breytingaráLögum').text
        except AttributeError:
            changes_to_law = ''
        try:
            cost_and_revenue = summary_xml.find('kostnaðurOgTekjur').text
        except AttributeError:
            cost_and_revenue = ''
        try:
            other_info = summary_xml.find('aðrarUpplýsingar').text
        except AttributeError:
            other_info = ''
        try:
            review_description = summary_xml.find('umsagnir').text
        except AttributeError:
            review_description = ''
        try:
            fate = summary_xml.find('afgreiðsla').text
        except AttributeError:
            fate = ''
        try:
            media_coverage = summary_xml.find('fjölmiðlaumfjöllun').text
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
        if int(docstub_xml.attrib['málsnúmer']) != issue.issue_num or int(docstub_xml.attrib['þingnúmer']) != parliament.parliament_num:
            continue

        is_main = False
        if i == 0:
            # If this is the zero-eth iterator, this is the main document.
            is_main = True

        doc_num = int(docstub_xml.attrib['skjalsnúmer'])

        doc_xml = get_xml('DOCUMENT_URL', parliament.parliament_num, doc_num).find('þingskjal')

        doc_nums.append(doc_num)

        doc_type = doc_xml.find('skjalategund').text
        time_published = doc_xml.find('útbýting').text + "+00:00"

        try:
            path_html = doc_xml.find('slóð/html').text
        except AttributeError:
            path_html = None

        try:
            path_pdf = doc_xml.find('slóð/pdf').text
        except AttributeError:
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
        committeepart = None # Reset from possible previous iteration

        committee_xml = doc_xml.find('flutningsmenn/nefnd')
        if committee_xml is not None:
            # NOTE: This try/except should be removed once the XML is fixed and committees are displayer properly.
            try:
                committee_xml_id = int(committee_xml.attrib['id'])
            except ValueError:
                print('Warning! Document is missing committee ID in Parliament %d, issue %d, document %d! Assumed "sérnefnd". Tell the XML keeper!' % (parliament.parliament_num, issue.issue_num, doc.doc_num), file=stderr)
                committee_xml_id = Committee.objects.get(abbreviation_short='sn').committee_xml_id

            committee = update_committee(committee_xml_id, parliament.parliament_num)

            committee_partname = committee_xml.find('hluti').text
            if committee_partname is None:
                committee_partname = ''

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

            persons_xml = committee_xml.findall('flutningsmaður')
            subproposer_ids = []
            for person_xml in persons_xml:
                person_xml_id = int(person_xml.attrib['id'])
                order = int(person_xml.attrib['röð'])

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
            persons_xml = doc_xml.findall('flutningsmenn/flutningsmaður')
            for person_xml in persons_xml:
                person_xml_id = int(person_xml.attrib['id'])

                order = int(person_xml.attrib['röð'])

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
        log_num = int(review_xml.attrib['dagbókarnúmer'])

        log_nums.append(log_num)

        try:
            sender_name = review_xml.find('sendandi').text
        except AttributeError:
            # Review with log_num 1057 in Parliament 112 lacks a name. Others do not exist.
            sender_name = ''
        try:
            sender_name_description = review_xml.find('skýring').text
        except AttributeError:
            sender_name_description = ''

        review_type = review_xml.find('tegunderindis').attrib['tegund']
        try:
            date_arrived = sensible_datetime(review_xml.find('komudagur').text)
        except AttributeError:
            date_arrived = None
        try:
            date_sent = sensible_datetime(review_xml.find('sendingadagur').text)
        except AttributeError:
            date_sent = None

        try:
            committee_xml_id = int(review_xml.find('viðtakandi/nefnd').attrib['id'])
            committee = update_committee(committee_xml_id, parliament.parliament_num)
            committee_id = committee.id
        except AttributeError:
            committee_id = None

        try:
            president_person_xml_id = int(review_xml.find('viðtakandi/forsetiAlþingis/nafn').attrib['id'])
            # We'll need the presidents if this is to work.
            update_presidents(parliament.parliament_num)
            president_seat = PresidentSeat.objects.main_on_date(parliament, date_sent)
        except AttributeError:
            president_seat = None

        # sender_name can contain a lot of baggage if it's old data (around 116th parliament and earlir)
        sender_name = sender_name.strip()
        while sender_name.find('  ') >= 0:
            sender_name = sender_name.replace('  ', ' ')

        path_pdf = review_xml.find('slóð/pdf').text

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

            if review.president_seat != president_seat:
                review.president_seat = president_seat
                changed = True

            if review.review_type != review_type:
                review.review_type = review_type
                changed = True

            if sensible_datetime(review.date_arrived) != date_arrived:
                review.date_arrived = date_arrived
                changed = True

            if sensible_datetime(review.date_sent) != date_sent:
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
            review.president_seat = president_seat
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

    issue_num = int(issue_xml.attrib['málsnúmer'])
    parliament_num = int(issue_xml.attrib['þingnúmer'])

    parliament = update_parliament(parliament_num)

    name = issue_xml.find('málsheiti').text
    issue_type = issue_xml.find('málstegund').attrib['id']

    try:
        special_inquisitor_xml = issue_xml.find('málshefjandi')
        special_responder_xml = issue_xml.find('til_andsvara')

        special_inquisitor = update_person(int(special_inquisitor_xml.attrib['id']), parliament.parliament_num)
        special_inquisitor_description = special_inquisitor_xml.text
        special_responder = update_person(int(special_responder_xml.attrib['id']), parliament.parliament_num)
        special_responder_description = special_responder_xml.text
    except AttributeError:
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


def update_sessions(parliament_num=None):

    parliament = update_parliament(parliament_num)

    xml = get_xml('SESSION_LIST_URL', parliament.parliament_num).findall('þingfundur')
    for session_xml in reversed(xml):
        session_num = int(session_xml.attrib['númer'])

        update_session(session_num, parliament.parliament_num)


def update_session(session_num, parliament_num=None):

    parliament = update_parliament(parliament_num)

    # Make sure that input makes sense
    if session_num is not None and not isinstance(session_num, int):
        raise TypeError('Parameter session_num must be a number')

    ah_key = '%d-%d' % (session_num, parliament.parliament_num)
    if ah_key in already_haves['sessions']:
        return already_haves['sessions'][ah_key]

    xml = get_xml('SESSION_AGENDA_URL', parliament.parliament_num, session_num).find('þingfundur')
    if xml is None:
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

    session = _process_session_agenda_xml(xml)

    already_haves['sessions'][ah_key] = session

    return session


def update_next_sessions():

    xml = get_xml('SESSION_NEXT_AGENDA_URL')

    sessions = []
    for session_xml in xml:
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
    if ah_key in already_haves['constituencies']:
        return already_haves['constituencies'][ah_key]

    xml = get_xml('CONSTITUENCIES_URL', parliament.parliament_num).findall('kjördæmið')

    constituencies = []
    for constituency_xml in xml:

        constituency_xml_id = int(constituency_xml.attrib['id'])

        if constituency_xml_id == 1: # Only there for ministers not in Parliament and is to be ignored.
            continue

        name = constituency_xml.find('heiti').text.strip()
        try:
            description = constituency_xml.find('lýsing').text.strip()
        except AttributeError:
            description = ''

        abbreviation_short = constituency_xml.find('skammstafanir/stuttskammstöfun').text

        try:
            abbreviation_long = constituency_xml.find('skammstafanir/löngskammstöfun').text
        except AttributeError:
            abbreviation_long = None

        parliament_num_first = int(constituency_xml.find('tímabil/fyrstaþing').text)

        try:
            parliament_num_last = int(constituency_xml.find('tímabil/síðastaþing').text)
        except AttributeError:
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
    if ah_key in already_haves['parties']:
        return already_haves['parties'][ah_key]

    xml = get_xml('PARTIES_URL', parliament.parliament_num).findall('þingflokkur')

    parties = []
    for party_xml in xml:

        party_xml_id = party_xml.attrib['id']

        name = party_xml.find('heiti').text.strip()

        if name == '':
            continue

        abbreviation_short = party_xml.find('skammstafanir/stuttskammstöfun').text
        abbreviation_long = party_xml.find('skammstafanir/löngskammstöfun').text

        parliament_num_first = int(party_xml.find('tímabil/fyrstaþing').text)
        try:
            parliament_num_last = int(party_xml.find('tímabil/síðastaþing').text)
        except AttributeError:
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

    xml = get_xml('COMMITTEE_AGENDA_LIST_URL', parliament.parliament_num).findall('nefndarfundur')

    committee_agendas = []
    for committee_agenda_stub_xml in reversed(xml):

        meeting_date = sensible_datetime(committee_agenda_stub_xml.find('hefst/dagur').text)
        if date_limit is not None and meeting_date < date_limit:
            break

        committee_agenda_xml_id = int(committee_agenda_stub_xml.attrib['númer'])
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

    parliament = update_parliament(parliament_num)

    now = datetime.now()
    today = datetime(now.year, now.month, now.day)

    agendas = update_committee_agendas(parliament_num=parliament.parliament_num, date_limit=today)

    # These are agendas that are upcoming according to the database but not according to the XML.
    # We run them through update_committee_agenda() for consistency's sake, which will delete or update them appropriately.
    dubious_agendas = CommitteeAgenda.objects.select_related('parliament').upcoming().exclude(id__in=[a.id for a in agendas])
    for dubious_agenda in dubious_agendas:
        update_committee_agenda(dubious_agenda.committee_agenda_xml_id, dubious_agenda.parliament.parliament_num)


def update_committee_agenda(committee_agenda_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)

    # Make sure that input makes sense
    if committee_agenda_xml_id is not None and not isinstance(committee_agenda_xml_id, int):
        raise TypeError('Parameter committee_agenda_xml_id must be a number')

    xml = get_xml('COMMITTEE_AGENDA_URL', committee_agenda_xml_id)

    if not 'númer' in xml.attrib:
        try:
            # Committee agenda has been deleted in XML, meaning cancelled.
            CommitteeAgenda.objects.get(committee_agenda_xml_id=committee_agenda_xml_id).delete()

            print('Deleted non-existent committee agenda: %d' % committee_agenda_xml_id)
            return
        except CommitteeAgenda.DoesNotExist:
            raise AlthingiException('Committee agenda %d in parliament %d does not exist' % (
                committee_agenda_xml_id,
                parliament.parliament_num
            ))

    elif int(xml.attrib['þingnúmer']) != parliament.parliament_num:
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

    return _process_committee_agenda_xml(xml) # Returns CommitteeAgenda object


# NOTE: To become a private function once we turn this into some sort of class
def _process_committee_agenda_xml(xml):

    parliament_num = int(xml.attrib['þingnúmer'])
    committee_agenda_xml_id = int(xml.attrib['númer'])
    committee_xml_id = int(xml.find('nefnd').attrib['id'])

    parliament = update_parliament(parliament_num)
    committee = update_committee(committee_xml_id, parliament_num)

    if xml.find('hefst/dagurtími') is None:
        # Sometimes only the date is known, not the datetime.
        if xml.find('hefst/dagur') is None:
            timing_start_planned = None
        else:
            timing_start_planned = sensible_datetime(xml.find('hefst/dagur').text)
    else:
        timing_start_planned = sensible_datetime(xml.find('hefst/dagurtími').text)

    if xml.find('hefst/texti') is not None:
        timing_text = xml.find('hefst/texti').text
    else:
        timing_text = None

    try:
        timing_start = sensible_datetime(xml.find('fundursettur').text)
    except AttributeError:
        timing_start = None
    try:
        timing_end = sensible_datetime(xml.find('fuslit').text)
    except AttributeError:
        timing_end = None

    try:
        committee_agenda = CommitteeAgenda.objects.get(
            committee_agenda_xml_id=committee_agenda_xml_id,
            parliament=parliament
        )

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
    items_xml = xml.findall('dagskrá/dagskrárliðir/dagskrárliður')
    for item_xml in items_xml:
        order = int(item_xml.attrib['númer'])

        try:
            name = item_xml.find('heiti').text
        except AttributeError:
            name = '[ Missing name ]'

        issue = None

        if order > max_order:
            max_order = order

        issue_xml = item_xml.find('mál')
        if issue_xml is not None:
            # There can only be one issue per agenda item. Right?
            issue_num = int(issue_xml.attrib['málsnúmer'])
            issue_parliament_num = int(issue_xml.attrib['löggjafarþing'])

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

    parliament_num = int(session_xml.attrib['þingnúmer'])
    session_num = int(session_xml.attrib['númer'])

    parliament = update_parliament(parliament_num)

    name = session_xml.find('fundarheiti').text

    try:
        timing_start_planned = sensible_datetime(session_xml.find('hefst/dagurtími').text)
    except AttributeError:
        timing_start_planned = None

    try:
        timing_text = session_xml.find('hefst/texti').text
    except AttributeError:
        timing_text = None

    try:
        timing_start = sensible_datetime(session_xml.find('fundursettur').text)
    except AttributeError:
        timing_start = None

    try:
        timing_end = sensible_datetime(session_xml.find('fuslit').text)
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

    max_order = 0
    for session_agenda_item_xml in session_xml.findall('dagskrá/dagskrárliður'):
        issue_xml = session_agenda_item_xml.find('mál')
        comment_xml = session_agenda_item_xml.find('athugasemd')

        order = int(session_agenda_item_xml.attrib['númer'])

        discussion_type = session_agenda_item_xml.find('umræða').attrib['tegund']
        discussion_continued = bool(session_agenda_item_xml.find('umræða').attrib['framhald'])

        if comment_xml is not None:
            comment_type = comment_xml.attrib['tegund']
            comment_text = comment_xml.find('dagskrártexti').text
            comment_description = comment_xml.find('skýring').text
        else:
            comment_type = None
            comment_text = None
            comment_description = None

        issue_num = int(issue_xml.attrib['málsnúmer'])
        issue_group = issue_xml.attrib['málsflokkur']

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


def update_speeches(parliament_num=None, since=None):

    parliament = update_parliament(parliament_num)
    since = sensible_datetime(since)

    if parliament.parliament_num in already_haves['speeches']:
        return already_haves['speeches'][parliament.parliament_num]

    xml = get_xml('SPEECHES_URL', parliament.parliament_num)

    pref_persons = dict((p.person_xml_id, p) for p in Person.objects.all())
    pref_sessions = dict((s.session_num, s) for s in Session.objects.filter(parliament_id=parliament.id))
    pref_issues = dict((i.issue_num, i) for i in Issue.objects.filter(
        issue_group='A',
        parliament_id=parliament.id,
    ))
    pref_speeches = dict((s.timing_start, s) for s in Speech.objects.filter(session__parliament_id=parliament.id))

    speeches = []
    speech_orders = {}
    for speech_xml in xml.findall('ræða'):

        # Timing found first to check if we need to process any further.
        timing_start = sensible_datetime(speech_xml.find('ræðahófst').text)
        if since and timing_start < since:
            continue

        timing_end = sensible_datetime(speech_xml.find('ræðulauk').text)

        seconds = (timing_end - timing_start).seconds

        person_xml_id = int(speech_xml.find('ræðumaður').attrib['id'])
        try:
            person = pref_persons[person_xml_id]
        except KeyError:
            person = update_person(person_xml_id)

        session_num = int(speech_xml.find('fundur').text)
        try:
            session = pref_sessions[session_num]
        except KeyError:
            session = update_session(session_num, parliament.parliament_num)

        issue_group = issue_group = speech_xml.find('mál/málsflokkur').text
        if issue_group == 'A':
            issue_num = int(speech_xml.find('mál/málsnúmer').text)
            try:
                issue = pref_issues[issue_num]
            except KeyError:
                issue = update_issue(issue_num, parliament.parliament_num)
        elif issue_group == 'B':
            # NOTE/TODO: We're skipping this for now, until the
            # independent B-issue XML file is complete, which should be
            # very soon since it's already almost complete. (2018-02-12)
            issue = None
        else:
            issue = None

        date = sensible_datetime(speech_xml.find('dagur').text)

        speech_type = speech_xml.find('tegundræðu').text

        iteration = speech_xml.find('umræða').text

        # In speeches in the 115th Parliament and older, the time of day is
        # unknown. Since speeches don't have unique IDs either, it is
        # effectively impossible to precisely identify speeches in those older
        # Parliaments except according to their order in whatever issue is
        # being discussed. That order is not provided either, however, so it
        # must be figured out on the client side. This gives us a unique
        # identifier from two variables, the issue's ID and the speech's order
        # within it. If no issue is specified, we leave this field as null.
        if issue is not None:
            if not issue.id in speech_orders:
                speech_orders[issue.id] = 0
            speech_orders[issue.id] += 1
            order_in_issue = speech_orders[issue.id]
        else:
            order_in_issue = None

        try:
            html_remote_path = speech_xml.find('slóðir/html').text
        except AttributeError:
            html_remote_path = None

        try:
            sgml_remote_path = speech_xml.find('slóðir/sgml').text
        except AttributeError:
            sgml_remote_path = None

        try:
            xml_remote_path = speech_xml.find('slóðir/xml').text
        except AttributeError:
            xml_remote_path = None

        try:
            text_remote_path = speech_xml.find('slóðir/text').text
        except AttributeError:
            text_remote_path = None

        try:
            sound_remote_path = speech_xml.find('slóðir/hljóð').text
        except AttributeError:
            sound_remote_path = None

        if timing_start in pref_speeches:
            # Speeches don't have IDs, so we have to go by the only unique
            # identifier, which is the moment they began. Note that this makes
            # speeches from the 115th Parliament and older incompatible. There
            # is no known solution until speeches get unique IDs in the XML.
            speech = pref_speeches[timing_start]

            changed = False
            if speech.person != person:
                speech.person = person
                changed = True

            if speech.session != session:
                speech.session = session
                changed = True

            if speech.issue != issue:
                speech.issue = issue
                changed = True

            if speech.date != date:
                speech.date = date
                changed = True

            if speech.timing_start != timing_start:
                speech.timing_start = timing_start
                changed = True

            if speech.timing_end != timing_end:
                speech.timing_end = timing_end
                changed = True

            if speech.seconds != seconds:
                speech.seconds = seconds
                changed = True

            if speech.speech_type != speech_type:
                speech.speech_type = speech_type
                changed = True

            if speech.iteration != iteration:
                speech.iteration = iteration
                changed = True

            if speech.order_in_issue != order_in_issue:
                speech.order_in_issue = order_in_issue
                changed = True

            if speech.html_remote_path != html_remote_path:
                speech.html_remote_path = html_remote_path
                changed = True

            if speech.sgml_remote_path != sgml_remote_path:
                speech.sgml_remote_path = sgml_remote_path
                changed = True

            if speech.xml_remote_path != xml_remote_path:
                speech.xml_remote_path = xml_remote_path
                changed = True

            if speech.text_remote_path != text_remote_path:
                speech.text_remote_path = text_remote_path
                changed = True

            if speech.sound_remote_path != sound_remote_path:
                speech.sound_remote_path = sound_remote_path
                changed = True

            if changed:
                speech.save()
                print('Updated speech: %s' % speech)
            else:
                print('Already have speech: %s' % speech)

        else:
            speech = Speech(timing_start=timing_start)
            speech.person = person
            speech.session = session
            speech.issue = issue
            speech.date = date
            speech.timing_start = timing_start
            speech.timing_end = timing_end
            speech.seconds = seconds
            speech.speech_type = speech_type
            speech.iteration = iteration
            speech.order_in_issue = order_in_issue
            speech.html_remote_path = html_remote_path
            speech.sgml_remote_path = sgml_remote_path
            speech.xml_remote_path = xml_remote_path
            speech.text_remote_path = text_remote_path
            speech.sound_remote_path = sound_remote_path
            speech.save()

            print('Added speech: %s' % speech)

        speeches.append(speech)

    deletable_speeches = Speech.objects.filter(
        session__parliament=parliament,
        timing_start__gte=since
    ).exclude(
        timing_start__in=[s.timing_start for s in speeches],
    )
    for deletable_speech in deletable_speeches:
        deletable_speech.delete()
        print('Deleted non-existent speech: %s' % deletable_speech)

    already_haves['speeches'][parliament.parliament_num] = speeches

    return speeches


def update_issue_statuses(parliament_num=None):

    parliament = update_parliament(parliament_num)

    for issue_num in [i.issue_num for i in parliament.issues.filter(issue_group='A')]:
        update_issue_status(issue_num, parliament.parliament_num)


def update_issue_status(issue_num, parliament_num=None):

    # Make sure that input makes sense
    if issue_num is not None and not isinstance(issue_num, int):
        raise TypeError('Parameter issue_num must be a number')

    parliament = update_parliament(parliament_num)

    try:
        issue = parliament.issues.get(issue_num=issue_num, issue_group='A')
    except Issue.DoesNotExist:
        msg = 'Issue %d/%d does not exist and is not automatically fetched.' % (issue_num, parliament.parliament_num)
        msg += ' Try first running "issue=%d parliament=%d".' % (issue_num, parliament.parliament_num)
        raise AlthingiException(msg)

    # Figure out issue's status, if supported.
    status = issue.determine_status()
    if status is not None:

        current_step_order_query = issue.steps.all() # Current according to database, that is.

        # Map the current steps to their order according to database.
        current_step_order_map = OrderedDict([(s.code, s.order) for s in current_step_order_query])

        if len(current_step_order_query) != len(current_step_order_map):
            # This means that there are duplicates of at least one step in the
            # database, which makes no sense. This should not happen and is
            # dealt with here as a precaution. We'll just delete all the rows
            # and insert them all from scratch.
            issue.steps.all().delete()
            current_step_order_map.clear()

        changed = False
        last_step = None
        order = 0
        for step, taken in status.items():
            # Has this step been taken in the issue type's legislative process?
            if taken:
                order += 1 # Must be the next step, then!

                if not step in current_step_order_map:
                    IssueStep(issue=issue, code=step, order=order).save()
                    changed = True
                elif step in current_step_order_map and current_step_order_map[step] != order:
                    IssueStep.objects.filter(issue=issue, code=step).update(order=order)
                    changed = True

                # Record the last step known to be taken.
                last_step = step

            else:
                if step in current_step_order_map:
                    IssueStep.objects.get(issue=issue, code=step).delete()
                    changed = True

        # Set the last step as the new current one.
        if issue.current_step != last_step:
            issue.current_step = last_step
            issue.save()
            changed = True

        # Remove steps that have nothing to do with this issue type (only as a precaution).
        issue.steps.exclude(code__in=status.keys()).delete()

        if changed:
            print('Updated status of issue: %s' % issue)
        else:
            print('Already have status of issue: %s' % issue)

    # Determine the issue's fate (if any).
    # This is done so near the end of the processing of the issue because it
    # relies on the status, which in turn relies on things processed after the
    # issue's basic attributes have been figured out.
    fate = issue.determine_fate()
    if issue.fate != fate:
        issue.fate = fate
        issue.save()
        print('Updated issue fate to "%s": %s' % (fate, issue))


def update_ministers(parliament_num=None):

    parliament = update_parliament(parliament_num)

    if parliament.parliament_num in already_haves['ministers']:
        return already_haves['ministers']


    xml = get_xml('MINISTER_LIST_URL', parliament.parliament_num)

    ministers = []
    for minister_xml in xml.findall('ráðherraembætti'):

        minister_xml_id = int(minister_xml.attrib['id'])

        name = minister_xml.find('heiti').text.strip()

        abbreviation_short = minister_xml.find('skammstafanir/stuttskammstöfun').text
        abbreviation_long = minister_xml.find('skammstafanir/löngskammstöfun').text

        parliament_num_first = int(minister_xml.find('tímabil/fyrstaþing').text)
        try:
            parliament_num_last = int(minister_xml.find('tímabil/síðastaþing').text)
        except AttributeError:
            parliament_num_last = None

        try:
            minister = Minister.objects.get(minister_xml_id=minister_xml_id)

            changed = False
            if minister.name != name:
                minister.name = name
                changed = True

            if minister.abbreviation_short != abbreviation_short:
                minister.abbreviation_short = abbreviation_short
                changed = True

            if minister.abbreviation_long != abbreviation_long:
                minister.abbreviation_long = abbreviation_long
                changed = True

            if minister.parliament_num_first != parliament_num_first:
                minister.parliament_num_first = parliament_num_first
                changed = True

            if minister.parliament_num_last != parliament_num_last:
                minister.parliament_num_last = parliament_num_last
                changed = True

            if parliament not in minister.parliaments.all():
                minister.parliaments.add(parliament)
                changed = True

            if changed:
                minister.save()
                print('Updated minister: %s' % minister)
            else:
                print('Already have minister: %s' % minister)

        except Minister.DoesNotExist:
            minister = Minister(minister_xml_id=minister_xml_id)
            minister.name = name
            minister.abbreviation_short = abbreviation_short
            minister.abbreviation_long = abbreviation_long
            minister.parliament_num_first = parliament_num_first
            minister.parliament_num_last = parliament_num_last
            minister.save()

            minister.parliaments.add(parliament)

            print('Added minister: %s' % minister)

        ministers.append(minister)

    already_haves['ministers'][parliament.parliament_num] = ministers

    return ministers


def update_minister_seats(person_xml_id, parliament_num=None):

    parliament = update_parliament(parliament_num)
    person = update_person(person_xml_id, parliament.parliament_num)

    ah_key = '%d-%d' % (parliament.parliament_num, person_xml_id)
    if ah_key in already_haves['minister_seats']:
        return already_haves['minister_seats'][ah_key]

    update_ministers(parliament.parliament_num)
    update_parties(parliament.parliament_num)

    xml = get_xml('MINISTER_SEATS_URL', person_xml_id).findall('ráðherrasetur/ráðherraseta')

    minister_seats = []
    for minister_seat_xml in xml:
        minister_seat_parliament_num = int(minister_seat_xml.find('þing').text)

        if minister_seat_parliament_num == parliament.parliament_num:

            minister_xml_id = int(minister_seat_xml.find('embætti').attrib['id'])
            minister = Minister.objects.get(minister_xml_id=minister_xml_id)

            timing_in = sensible_datetime(minister_seat_xml.find('tímabil/inn').text)

            try:
                timing_out = sensible_datetime(minister_seat_xml.find('tímabil/út').text)
            except AttributeError:
                timing_out = None

            try:
                party_xml_id = int(minister_seat_xml.find('þingflokkur').attrib['id'])
                party = Party.objects.get(party_xml_id=party_xml_id)
            except AttributeError:
                party = None

            try:
                minister_seat = MinisterSeat.objects.filter(
                    person=person,
                    minister=minister,
                    parliament__parliament_num=parliament.parliament_num,
                    timing_in=timing_in
                ).get(Q(timing_out=timing_out) | Q(timing_out=None))

                changed = False
                if minister_seat.timing_out != timing_out:
                    minister_seat.timing_out = timing_out
                    changed = True

                if minister_seat.party != party:
                    minister_seat.party = party
                    changed = True

                if changed:
                    minister_seat.save()
                    print('Updated minister seat: %s' % minister_seat)
                else:
                    print('Already have minister seat: %s' % minister_seat)

            except MinisterSeat.DoesNotExist:
                minister_seat = MinisterSeat()
                minister_seat.person = person
                minister_seat.minister = minister
                minister_seat.parliament = parliament
                minister_seat.timing_in = timing_in
                minister_seat.timing_out = timing_out
                minister_seat.party = party

                minister_seat.save()
                print('Added minister seat: %s' % minister_seat)

            minister_seats.append(minister_seat)

    already_haves['minister_seats'][ah_key] = minister_seats

    return minister_seats


# Returns two lists, of presidents and then president seats.
def update_presidents(parliament_num=None):

    parliament = update_parliament(parliament_num)

    ah_key = parliament.parliament_num
    if ah_key in already_haves['presidents'] and ah_key in already_haves['president_seats']:
        return already_haves['presidents'][ah_key], already_haves['president_seats'][ah_key]

    xml = get_xml('PRESIDENT_LIST_URL', parliament.parliament_num).findall('forseti')

    # Certain presidential offices have a sequential order, hard-coded here
    # since there is no more reasonable way to determine them, and they are
    # not subject to change in the future.
    orders_of_succession = {
        'forseti': 1,
        '1. varaforseti': 2,
        '2. varaforseti': 3,
        '3. varaforseti': 4,
        '4. varaforseti': 5,
        '5. varaforseti': 6,
        '6. varaforseti': 7,
    }

    presidents = []
    for node in xml:
        president_xml_id = int(node.find('embætti').attrib['id'])
        name = node.find('embætti/embættisheiti').text
        abbreviation = node.find('embætti/skammstöfun').text
        president_type = node.find('embætti/embættisflokkur').attrib['flokkur']

        is_main = name == 'forseti' # No other way to detect this.

        if name in orders_of_succession:
            order = orders_of_succession[name]
        else:
            order = None

        try:
            president = President.objects.get(president_xml_id=president_xml_id)

            changed = False
            if president.name != name:
                president.name = name
                changed = True

            if president.abbreviation != abbreviation:
                president.abbreviation = abbreviation
                changed = True

            if president.president_type != president_type:
                president.president_type = president_type
                changed = True

            if president.is_main != is_main:
                president.is_main = is_main
                changed = True

            if president.order != order:
                president.order = order
                changed = True

            if parliament not in president.parliaments.all():
                president.parliaments.add(parliament)
                changed = True

            if changed:
                president.save()
                print('Updated president: %s' % president)
            else:
                print('Already have president: %s' % president)

        except President.DoesNotExist:
            president = President(president_xml_id=president_xml_id)
            president.name = name
            president.abbreviation = abbreviation
            president.president_type = president_type
            president.is_main = is_main
            president.save()

            president.parliaments.add(parliament)

            print('Added president: %s' % president)

        presidents.append(president)

    already_haves['presidents'][ah_key] = presidents

    # NOTE: Elsewhere in this script, for example when updating seats,
    # ministerial seats and committee seats, they are updated per person, i.e.
    # person_xml_id is passed as an input variable. Finding the presidential
    # seats works differently because the data is presented differently in the
    # XML. There is no page where we can see presidential seats with a person
    # as input, only a list of all the persons that have served during the
    # given parliament. We'll iterate the whole thing again though, just in
    # case these sections get separated in the future.

    president_seats = []
    for node in xml:
        person_xml_id = int(node.attrib['id'])
        person = update_person(person_xml_id)

        timing_in = sensible_datetime(node.find('inn').text)

        try:
            timing_out = sensible_datetime(node.find('út').text)
        except AttributeError:
            timing_out = None

        president_xml_id = int(node.find('embætti').attrib['id'])
        president = President.objects.get(president_xml_id=president_xml_id)

        try:
            president_seat = PresidentSeat.objects.filter(
                person=person,
                president=president,
                parliament=parliament,
                timing_in=timing_in
            ).get(Q(timing_out=timing_out) | Q(timing_out=None))

            changed = False
            if president_seat.timing_out != timing_out:
                president_seat.timing_out = timing_out
                changed = True

            if changed:
                president.save()
                print('Updated president seat: %s' % president_seat)
            else:
                print('Already have president seat: %s' % president_seat)

        except PresidentSeat.DoesNotExist:
            president_seat = PresidentSeat()
            president_seat.person = person
            president_seat.president = president
            president_seat.parliament = parliament
            president_seat.timing_in = timing_in
            president_seat.timing_out = timing_out
            president_seat.save()

            print('Added president seat: %s' % president_seat)

        president_seats.append(president_seat)

    already_haves['president_seats'][ah_key] = president_seats

    return presidents, president_seats


def update_categories():
    # Categories are currently not dependent on specific parliaments, which is
    # unusual and may change in the future.

    if 'category_groups' in already_haves:
        return already_haves['category_groups']

    xml = get_xml('CATEGORIES_LIST_URL').findall('yfirflokkur')

    cat_groups = []
    for node in xml:
        category_group_xml_id = int(node.attrib['id'])
        name = node.find('heiti').text

        try:
            cat_group = CategoryGroup.objects.get(category_group_xml_id=category_group_xml_id)

            changed = False
            if cat_group.name != name:
                cat_group.name = name
                changed = True

            if changed:
                cat_group.save()
                print('Updated category group: %s' % cat_group)
            else:
                print('Already have category group: %s' % cat_group)

        except CategoryGroup.DoesNotExist:
            cat_group = CategoryGroup(category_group_xml_id=category_group_xml_id)
            cat_group.name = name
            cat_group.save()

            print('Added category group: %s' % cat_group)

        cat_groups.append(cat_group)

        # Let's do the categories themselves!
        for subnode in node.findall('efnisflokkur'):
            category_xml_id = int(subnode.attrib['id'])
            name = subnode.find('heiti').text
            description = subnode.find('lýsing').text or ''
            group = cat_group

            try:
                category = Category.objects.get(category_xml_id=category_xml_id)

                changed = False
                if category.name != name:
                    category.name = name
                    changed = True

                if category.description != description:
                    category.description = description
                    changed = True

                if category.group != group:
                    category.group = group
                    changed = True

                if changed:
                    category.save()
                    print('Updated category: %s' % category)
                else:
                    print('Already have category: %s' % category)

            except Category.DoesNotExist:
                category = Category(category_xml_id=category_xml_id)
                category.name = name
                category.description = description
                category.group = group
                category.save()

                print('Added category: %s' % category)

    already_haves['category_groups'] = cat_groups

    return cat_groups
