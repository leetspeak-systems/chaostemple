import json
import requests
from urllib.parse import quote


def get_gazette_law_info(law_identifier: str) -> dict:
    """
    Retrieves information about a given law from the official Gazette. Most
    importantly, we need the publication date, but all information that we find
    is retrieved.

    This functionality was reverse-engineered using a browser before we were
    aware of there being a better API for it (which may be
    `api.stjornartidindi.is`), so it's messy and unnecessarily convoluted.
    There are better ways to do this.
    """

    url_base = "https://island.is/api/graphql"
    operation_name = "Adverts"

    variables = {
        'input': {
            'department': ["a-deild"],
            'category': [],
            'involvedParty': [],
            'type': [],
            'search': law_identifier,
            'page': 1
        }
    }

    # We don't know what this means, it was retrieved from the browser during
    # reverse-engineering.
    extensions = {
        'persistedQuery': {
            'version': 1,
            'sha256Hash': '01d212af534d8cc211f78891c7aea474a5ba34629335e9cfed70cb2dbb3dafa3'
        }
    }

    url = "%s?operationName=%s&variables=%s&extensions=%s" % (
        url_base,
        operation_name,
        quote(json.dumps(variables)),
        quote(json.dumps(extensions)),
    )

    # FIXME: Better error handling needed.
    response = requests.get(url)
    listing = response.json()["data"]["officialJournalOfIcelandAdverts"]["adverts"]
    if len(listing) != 1:
        raise Exception("Expected exactly one result for advert from Gazette API.")

    advert_info = listing[0]

    return advert_info
