import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

CURRENT_PARLIAMENT_NUM = 146

STATIC_DOCUMENT_DIR = os.path.join(BASE_DIR, 'althingi/static')
XML_CACHE_DIR = os.path.join(BASE_DIR, 'althingi/xmlcache')

DOWNLOAD_DOCUMENTS = False
DOWNLOAD_REVIEWS = False

# For development purposes - to cache XML documents for development on a bad or no internet connection
USE_XML_CACHE = False

ALTHINGI_ISSUE_URL = 'http://www.althingi.is/dba-bin/ferill.pl?ltg=%d&mnr=%d' # % (parliament_num, issue_num)
ALTHINGI_PERSON_URL = 'http://www.althingi.is/altext/cv/is/?nfaerslunr=%d' # % person_xml_id

