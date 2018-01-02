# -*- coding: utf-8 -*-
import os
import sys

from django.test import TestCase

from althingi.althingi_settings import FIRST_PARLIAMENT_NUM
from althingi.exceptions import AlthingiException
from althingi.updaters import clear_already_haves
from althingi.updaters import update_parliament
from althingi.updaters import update_person
from althingi.updaters import update_persons
from althingi.updaters import update_seats
from althingi.updaters import update_vote_casting
from althingi.updaters import update_vote_castings
from althingi.utils import get_last_parliament_num


# Test dummies from different parliaments for testing known, valid data.
test_dummies = (
    (1166, 148, u'Helgi Hrafn Gunnarsson'),
    (1251, 147, u'Pawel Bartoszek'),
    (1261, 146, u'Áslaug Arna Sigurbjörnsdóttir'),
    (1012, 145, u'Bjarkey Olsen Gunnarsdóttir'),
    (1214, 144, u'Ásta Guðrún Helgadóttir'),
    (1168, 143, u'Jón Þór Ólafsson'),
    ( 683, 142, u'Guðbjartur Hannesson'),
    ( 287, 141, u'Jóhanna Sigurðardóttir'),
    (1138, 140, u'Amal Tamimi'),
)

# Sometimes we just need one test dummy.
main_test_dummy = test_dummies[0]

# An additional test dummy known to not exist.
broken_test_dummy = (3, 148, 'Broken Test Dummy')

# Vote castings known to be valid.
test_dummy_vote_castings = (
    (54805, 148),
    (54799, 147),
    (53954, 146),
    (51984, 145),
    (50400, 144),
    (48958, 143), # Note: No actual votes, speaker declaration.
    (48871, 142),
    (47192, 141),
    (45412, 140),
)

# Main test dummy vote casting
main_test_dummy_vote_casting = test_dummy_vote_castings[0]

# Vote casting known to be invalid.
broken_test_dummy_vote_casting = (1, 148)


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
        person_xml_id, parliament_num, name = main_test_dummy
        with self.assertRaisesRegexp(TypeError, 'Parameter person_xml_id must be a number'):
            update_person(str(person_xml_id), parliament_num)

        # Fail: Fetch a person that we know does not exist.
        person_xml_id, parliament_num, name = broken_test_dummy
        with self.assertRaisesRegexp(AlthingiException, 'Person with XML-ID \d+ not found'):
            update_person(person_xml_id, parliament_num)

        # Pass: Iterate through our test dummies and check their names.
        for person_xml_id, parliament_num, name in test_dummies:
            person = update_person(person_xml_id, parliament_num)
            self.assertEquals(person.name, name)

    @hidden_prints
    def test_update_seats(self):

        # Fail: Good number passed as something else than a number.
        person_xml_id, parliament_num, name = main_test_dummy
        with self.assertRaisesRegexp(TypeError, 'Parameter person_xml_id must be a number'):
            update_seats(str(person_xml_id), parliament_num)

        # Fail: Fetch seats for a person that does not exist.
        person_xml_id, parliament_num, name = broken_test_dummy
        with self.assertRaisesRegexp(AlthingiException, 'Person with XML-ID \d+ not found'):
            update_seats(person_xml_id, parliament_num)

        # Pass: Fetch the seats of a person known to exist.
        person_xml_id, parliament_num, name = main_test_dummy
        update_seats(person_xml_id, parliament_num)

    @hidden_prints
    def test_update_vote_castings(self):
        update_vote_castings()

    @hidden_prints
    def test_update_vote_casting(self):

        # Fail: Good number passed as something else than number.
        vote_casting_xml_id, parliament_num = main_test_dummy_vote_casting
        with self.assertRaisesRegexp(TypeError, 'Parameter vote_casting_xml_id must be a number'):
            update_vote_casting(str(vote_casting_xml_id), parliament_num)

        # Fail: Fetch vote casting that does not exist.
        vote_casting_xml_id, parliament_num = broken_test_dummy_vote_casting
        with self.assertRaisesRegexp(AlthingiException, 'Vote casting \d+ does not exist'):
            update_vote_casting(vote_casting_xml_id, parliament_num)

        # Pass: Fetch some vote castings known to be valid.
        for vote_casting_xml_id, parliament_num in test_dummy_vote_castings:
            update_vote_casting(vote_casting_xml_id, parliament_num)
