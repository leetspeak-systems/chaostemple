# NOTE: These are only default values. If you want to change them, override them in 'althingi/settings.py'.

import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

FIRST_PARLIAMENT_NUM = 20

CURRENT_PARLIAMENT_NUM = 154

STATIC_DOCUMENT_DIR = os.path.join(BASE_DIR, "djalthingi/static")
XML_CACHE_DIR = os.path.join(BASE_DIR, "djalthingi/xmlcache")
XML_ERROR_DIR = os.path.join(XML_CACHE_DIR, "invalid")

DOWNLOAD_DOCUMENTS = False
DOWNLOAD_REVIEWS = False

# Development flags
# - XML_USE_CACHE: Cache XML for no internet or to save bandwidth.
# - XML_SAVE_INVALID: Save invalid XML files for ability to investigate.
XML_USE_CACHE = False
XML_SAVE_INVALID = False

# Timeout in seconds for retrieving remote XML files
REMOTE_CONTENT_TIMEOUT = 10

ALTHINGI_ISSUE_URL = "https://www.althingi.is/thingstorf/thingmalalistar-eftir-thingum/ferill/?ltg=%d&mnr=%d"  # % (parliament_num, issue_num)
ALTHINGI_PERSON_URL = (
    "http://www.althingi.is/altext/cv/is/?nfaerslunr=%d"  # % person_xml_id
)

if not os.path.isfile(os.path.join(BASE_DIR, "djalthingi/settings.py")):
    with open(os.path.join(BASE_DIR, "djalthingi/settings.py"), "w") as f:
        f.write(
            "# Put your custom settings here. See 'djalthingi/althingi_settings.py' for available options.\n"
        )
        f.close()

from djalthingi.settings import *
