# -*- coding: utf-8 -*-
import os
import sys

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from althingi.althingi_settings import FIRST_PARLIAMENT_NUM
from althingi.exceptions import AlthingiException
from althingi.updaters import clear_already_haves
from althingi.updaters import update_committee
from althingi.updaters import update_committee_agenda
from althingi.updaters import update_committee_agendas
from althingi.updaters import update_committee_seats
from althingi.updaters import update_committees
from althingi.updaters import update_constituencies
from althingi.updaters import update_issue
from althingi.updaters import update_issues
from althingi.updaters import update_next_committee_agendas
from althingi.updaters import update_next_sessions
from althingi.updaters import update_parliament
from althingi.updaters import update_parties
from althingi.updaters import update_person
from althingi.updaters import update_persons
from althingi.updaters import update_seats
from althingi.updaters import update_session
from althingi.updaters import update_sessions
from althingi.updaters import update_vote_casting
from althingi.updaters import update_vote_castings
from althingi.utils import get_last_parliament_num


# Test dummies.
test_dummy = (1166, 148, u'Helgi Hrafn Gunnarsson')
broken_test_dummy = (3, 148, 'Broken Test Dummy')

# Test dummy vote castings.
test_dummy_vote_casting = (54805, 148)
broken_test_dummy_vote_casting = (1, 148)

# Test dummy committee.
test_dummy_committee = (201, 148, u'allsherjar- og menntamálanefnd')
broken_test_dummy_committee = (1, 148, u'broken test dummy committee')

# Test dummy issue.
test_dummy_issue = (1, 148, u'fjárlög 2018')
broken_test_dummy_issue = (139, 147, u'Broken Test Dummy Issue')

# Test dummy sessions
test_dummy_session = (3, 148, u'3. fundur')
broken_test_dummy_session = (9, 147, u'Broken Test Dummy Session')

# Test dummy committee agenda.
test_dummy_committee_agenda = (18462, 148, u'21. desember 17, kl. 10:00 árdegis')
broken_test_dummy_committee_agenda = (1, 148, 'Broken Test Dummy Committee Agenda')


class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout

        # Okay, I don't know why this works. The open(os.devnull...) method of
        # suppressing print messages created a very strange problem where a
        # UnicodeEncodeError was raised when it shouldn't have been. It works
        # fine with most tests, for example test_update_seats, but not others
        # like test_update_vote_castings, even though everything regarding
        # encoding is exactly the same in both cases. Setting sys.stdout to
        # None should produce an error because it doesn't have a write
        # function, but it doesn't. Instead it suppresses output, which is
        # what is wanted. Courageous souls may try reverting to using the
        # open(os.devnull...) method again to see if the encoding problem
        # either goes away in time or can be figured out. I'm leaving this the
        # way it is for now, because it works, even though I don't know why.

        #sys.stdout = open(os.devnull, 'w')
        sys.stdout = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout

# A function decorator for hiding prints.
def hidden_prints(test_function):
    def wrapped(*args, **kwargs):
        with HiddenPrints():
            return test_function(*args, **kwargs)
    return wrapped


class AlthingiUpdaterTest(TestCase):

    def setUp(self):
        clear_already_haves()

    @hidden_prints
    def test_update_parliament(self):
        '''
        Any updater function that takes parliament_num as a parameter will
        pass it on to the update_parliament function. Testing the
        parliament_num parameter in other functions in therefore redundant.
        '''

        parliament_num = get_last_parliament_num()

        # Pass: Basic usage
        parliament = update_parliament(parliament_num)
        self.assertEquals(parliament.parliament_num, parliament_num)

        # Pass: Figure out default parliament_num
        parliament = update_parliament(None)
        self.assertEquals(parliament.parliament_num, parliament_num)

        # Fail: Good number passed as string
        self.assertRaises(TypeError, update_parliament, str(parliament_num))

        # Fail: Get a parliament before the first one
        self.assertRaises(AlthingiException, update_parliament, FIRST_PARLIAMENT_NUM - 1)

        # Fail: Get a parliament from the (apparent) future
        self.assertRaises(AlthingiException, update_parliament, parliament_num + 1)

    @hidden_prints
    def test_update_persons(self):
        persons = update_persons()

    @hidden_prints
    def test_update_person(self):

        # Fail: Good number passed as something else than a number.
        person_xml_id, parliament_num, name = test_dummy
        with self.assertRaisesRegexp(TypeError, 'Parameter person_xml_id must be a number'):
            update_person(str(person_xml_id), parliament_num)

        # Fail: Fetch a person that we know does not exist.
        person_xml_id, parliament_num, name = broken_test_dummy
        with self.assertRaisesRegexp(AlthingiException, 'Person with XML-ID \d+ not found'):
            update_person(person_xml_id, parliament_num)

        # Pass: Fetch a person known to exist.
        person_xml_id, parliament_num, name = test_dummy
        person = update_person(person_xml_id, parliament_num)
        self.assertEquals(person.name, name)

    @hidden_prints
    def test_update_seats(self):

        # Fail: Good number passed as something else than a number.
        person_xml_id, parliament_num, name = test_dummy
        with self.assertRaisesRegexp(TypeError, 'Parameter person_xml_id must be a number'):
            update_seats(str(person_xml_id), parliament_num)

        # Fail: Fetch seats for a person that does not exist.
        person_xml_id, parliament_num, name = broken_test_dummy
        with self.assertRaisesRegexp(AlthingiException, 'Person with XML-ID \d+ not found'):
            update_seats(person_xml_id, parliament_num)

        # Pass: Fetch the seats of a person known to exist.
        person_xml_id, parliament_num, name = test_dummy
        update_seats(person_xml_id, parliament_num)

    @hidden_prints
    def test_update_vote_castings(self):
        update_vote_castings()

    @hidden_prints
    def test_update_vote_casting(self):

        # Fail: Good number passed as something else than number.
        vote_casting_xml_id, parliament_num = test_dummy_vote_casting
        with self.assertRaisesRegexp(TypeError, 'Parameter vote_casting_xml_id must be a number'):
            update_vote_casting(str(vote_casting_xml_id), parliament_num)

        # Fail: Fetch vote casting that does not exist.
        vote_casting_xml_id, parliament_num = broken_test_dummy_vote_casting
        with self.assertRaisesRegexp(AlthingiException, 'Vote casting \d+ does not exist'):
            update_vote_casting(vote_casting_xml_id, parliament_num)

        # Pass: Fetch a vote casting known to be valid.
        vote_casting_xml_id, parliament_num = test_dummy_vote_casting
        update_vote_casting(vote_casting_xml_id, parliament_num)

    @hidden_prints
    def test_update_committee_seats(self):

        # Fail: Good number passed as something else than number.
        person_xml_id, parliament_num, name = test_dummy
        with self.assertRaisesRegexp(TypeError, 'Parameter person_xml_id must be a number'):
            update_committee_seats(str(person_xml_id), parliament_num)

        # Fail: Fetch committee seats for a person that does not exist.
        person_xml_id, parliament_num, name = broken_test_dummy
        with self.assertRaisesRegexp(AlthingiException, 'Person with XML-ID \d+ not found'):
            update_committee_seats(person_xml_id, parliament_num)

        # Pass: Fetch committee seats for a person known to be valid.
        person_xml_id, parliament_num, name = test_dummy
        update_committee_seats(person_xml_id, parliament_num)

    @hidden_prints
    def test_update_committees(self):
        update_committees()

    @hidden_prints
    def test_update_committee(self):

        # Fail: Good number passed as something else than number.
        committee_xml_id, parliament_num, name = test_dummy_committee
        with self.assertRaisesRegexp(TypeError, 'Parameter committee_xml_id must be a number'):
            update_committee(str(committee_xml_id), parliament_num)

        # Fail: Fetch committe that does not exist.
        committee_xml_id, parliament_num, name = broken_test_dummy_committee
        with self.assertRaisesRegexp(AlthingiException, 'Committee with XML-ID \d+ does not exist'):
            update_committee(committee_xml_id, parliament_num)

        # Pass: Fetch committee known to exist.
        committee_xml_id, parliament_num, name = test_dummy_committee
        committee = update_committee(committee_xml_id, parliament_num)
        self.assertEquals(committee.name, name)

    @hidden_prints
    def test_update_issues(self):
        update_issues()

    @hidden_prints
    def test_update_issue(self):

        # Fail: Good number passed as something else than number.
        issue_num, parliament_num, name = test_dummy_issue
        with self.assertRaisesRegexp(TypeError, 'Parameter issue_num must be a number'):
            update_issue(str(issue_num), parliament_num)

        # Fail: Fetch issue that does not exist.
        issue_num, parliament_num, name = broken_test_dummy_issue
        with self.assertRaisesRegexp(AlthingiException, 'Issue \d+ in parliament \d+ does not exist'):
            update_issue(issue_num, parliament_num)

        # Pass: Fetch issue known to exist.
        issue_num, parliament_num, name = test_dummy_issue
        issue = update_issue(issue_num, parliament_num)
        self.assertEquals(issue.name, name)

    @hidden_prints
    def test_update_sessions(self):
        update_sessions()

    @hidden_prints
    def test_update_session(self):

        # Fail: Good number passed as something else than number.
        session_num, parliament_num, name = test_dummy_session
        with self.assertRaisesRegexp(TypeError, 'Parameter session_num must be a number'):
            update_session(str(session_num), parliament_num)

        # Fail: Fetch session that does not exist.
        session_num, parliament_num, name = broken_test_dummy_session
        with self.assertRaisesRegexp(AlthingiException, 'Session \d+ in parliament \d+ does not exist'):
            update_session(session_num, parliament_num)

        # Pass: Fetch session that is known to exist.
        session_num, parliament_num, name = test_dummy_session
        session = update_session(session_num, parliament_num)
        self.assertEquals(session.name, name)

    @hidden_prints
    def test_update_next_sessions(self):
        update_next_sessions()

    @hidden_prints
    def test_update_constituencies(self):
        update_constituencies()

    @hidden_prints
    def test_update_parties(self):
        update_parties()

    @hidden_prints
    def test_update_committee_agendas(self):

        # Fail: Garbage datetime.
        with self.assertRaisesRegexp(ValueError, 'Could not figure out datetime format for ".+"'):
            update_committee_agendas(None, 'garbage')

        # Fail: Properly formatted but incorrect datetime.
        with self.assertRaisesRegexp(ValueError, 'Could not figure out datetime format for ".+"'):
            update_committee_agendas(None, '2017-02-29')

        # Pass: Fetch committee agendas with a date limit from a week ago.
        date_limit = timezone.now() - timedelta(days=7)
        update_committee_agendas(None, date_limit)

    @hidden_prints
    def test_update_next_committee_agendas(self):
        update_next_committee_agendas()

    @hidden_prints
    def test_update_committee_agenda(self):

        # Fail: Good number passed as something else than number.
        committee_agenda_xml_id, parliament_num, timing_text = test_dummy_committee_agenda
        with self.assertRaisesRegexp(TypeError, 'Parameter committee_agenda_xml_id must be a number'):
            update_committee_agenda(str(committee_agenda_xml_id), parliament_num)

        # Fail: Fetch committee agenda that does not exist.
        committee_agenda_xml_id, parliament_num, timing_text = broken_test_dummy_committee_agenda
        with self.assertRaisesRegexp(AlthingiException, 'Committee agenda \d+ in parliament \d+ does not exist'):
            update_committee_agenda(committee_agenda_xml_id, parliament_num)

        # Pass> Fetch a committee agenda known to exist.
        committee_agenda_xml_id, parliament_num, timing_text = test_dummy_committee_agenda
        committee_agenda = update_committee_agenda(committee_agenda_xml_id, parliament_num)
        self.assertEquals(committee_agenda.timing_text, timing_text)
