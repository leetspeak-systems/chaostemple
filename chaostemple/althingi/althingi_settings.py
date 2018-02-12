# NOTE: These are only default values. If you want to change them, override them in 'althingi/settings.py'.

import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

FIRST_PARLIAMENT_NUM = 20

CURRENT_PARLIAMENT_NUM = 148

STATIC_DOCUMENT_DIR = os.path.join(BASE_DIR, 'althingi/static')
XML_CACHE_DIR = os.path.join(BASE_DIR, 'althingi/xmlcache')

DOWNLOAD_DOCUMENTS = False
DOWNLOAD_REVIEWS = False

# For development purposes - to cache XML documents for development on a bad or no internet connection
USE_XML_CACHE = False

# Timeout in seconds for retrieving remote XML files
REMOTE_CONTENT_TIMEOUT = 10

ALTHINGI_ISSUE_URL = 'http://www.althingi.is/dba-bin/ferill.pl?ltg=%d&mnr=%d' # % (parliament_num, issue_num)
ALTHINGI_PERSON_URL = 'http://www.althingi.is/altext/cv/is/?nfaerslunr=%d' # % person_xml_id

if not os.path.isfile(os.path.join(BASE_DIR, 'althingi/settings.py')):
    with open(os.path.join(BASE_DIR, 'althingi/settings.py'), 'w') as f:
        f.write('# Put your custom settings here. See \'althingi/althingi_settings.py\' for available options.\n')
        f.close()

from althingi.settings import *

