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


class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout


class AlthingiUpdaterTest(TestCase):

    def setUp(self):
        clear_already_haves()

    def test_update_parliament(self):

        parliament_num = get_last_parliament_num()

        with HiddenPrints():

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

    def test_update_persons(self):
        with HiddenPrints():
            persons = update_persons()

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
        with HiddenPrints():
            for person_xml_id, parliament_num, name in test_dummies:
                person = update_person(person_xml_id, parliament_num)
                self.assertEquals(person.name, name)
