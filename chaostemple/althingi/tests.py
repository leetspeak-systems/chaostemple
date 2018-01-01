import os
import sys

from django.test import TestCase

from althingi.althingi_settings import FIRST_PARLIAMENT_NUM
from althingi.exceptions import AlthingiException
from althingi.updaters import clear_already_haves
from althingi.updaters import update_parliament
from althingi.utils import get_last_parliament_num


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
