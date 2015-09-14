import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

CURRENT_PARLIAMENT_NUM = 145

STATIC_DOCUMENT_DIR = os.path.join(BASE_DIR, 'althingi/static')

DOWNLOAD_DOCUMENTS = False
DOWNLOAD_REVIEWS = False

ALTHINGI_ISSUE_URL = 'http://www.althingi.is/dba-bin/ferill.pl?ltg=%d&mnr=%d' # % (parliament_num, issue_num)

