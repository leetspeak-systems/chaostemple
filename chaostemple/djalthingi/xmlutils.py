import os
import requests

from datetime import datetime
from sys import stderr

from lxml import etree

from djalthingi import althingi_settings

xml_urls = {
    'CATEGORIES_LIST_URL': 'http://www.althingi.is/altext/xml/efnisflokkar/',
    'DOCUMENT_URL': 'http://www.althingi.is/altext/xml/thingskjol/thingskjal/?lthing=%d&skjalnr=%d',
    'PARLIAMENT_URL': 'http://www.althingi.is/altext/xml/loggjafarthing/?lthing=%d',
    'ISSUE_LIST_URL': 'http://www.althingi.is/altext/xml/thingmalalisti/?lthing=%d',
    'ISSUE_URL': 'http://www.althingi.is/altext/xml/thingmalalisti/thingmal/?lthing=%d&malnr=%d',
    'ISSUE_SUMMARY_URL': 'http://www.althingi.is/altext/xml/samantektir/samantekt/?lthing=%d&malnr=%d',
    'MINISTER_LIST_URL': 'http://www.althingi.is/altext/xml/radherraembaetti/?lthing=%d',
    'MINISTER_SEATS_URL': 'http://www.althingi.is/altext/xml/radherrar/radherraseta/?nr=%d',
    'PARTIES_URL': 'http://www.althingi.is/altext/xml/thingflokkar/?lthing=%d',
    'PERSON_URL': 'http://www.althingi.is/altext/xml/thingmenn/thingmadur/?nr=%d',
    'COMMITTEE_FULL_LIST_URL': 'http://www.althingi.is/altext/xml/nefndir/',
    'COMMITTEE_LIST_URL': 'http://www.althingi.is/altext/xml/nefndir/?lthing=%d',
    'COMMITTEE_AGENDA_LIST_URL': 'http://www.althingi.is/altext/xml/nefndarfundir/?lthing=%d',
    'COMMITTEE_AGENDA_URL': 'http://www.althingi.is/altext/xml/nefndarfundir/nefndarfundur/?dagskrarnumer=%d',
    'COMMITTEE_SEATS_URL': 'http://www.althingi.is/altext/xml/thingmenn/thingmadur/nefndaseta/?nr=%d',
    'CONSTITUENCIES_URL': 'http://www.althingi.is/altext/xml/kjordaemi/?lthing=%d',
    'SESSION_LIST_URL': 'http://www.althingi.is/altext/xml/thingfundir/?lthing=%d',
    'SESSION_AGENDA_URL': 'http://www.althingi.is/altext/xml/dagskra/thingfundur/?lthing=%d&fundur=%d',
    'SESSION_NEXT_AGENDA_URL': 'http://www.althingi.is/altext/xml/dagskra/thingfundur/',
    'SPEECHES_URL': 'http://www.althingi.is/altext/xml/raedulisti/?lthing=%d',
    'PERSONS_MPS_URL': 'http://www.althingi.is/altext/xml/thingmenn/?lthing=%d',
    'PERSONS_MINISTERS_URL': 'http://www.althingi.is/altext/xml/radherrar/?lthing=%d',
    'PRESIDENT_LIST_URL': 'http://www.althingi.is/altext/xml/forsetar/?lthing=%d',
    'SEATS_URL': 'http://www.althingi.is/altext/xml/thingmenn/thingmadur/thingseta/?nr=%d',
    'VOTE_CASTING_URL': 'http://www.althingi.is/altext/xml/atkvaedagreidslur/atkvaedagreidsla/?numer=%d',
    'VOTE_CASTINGS_URL': 'http://www.althingi.is/altext/xml/atkvaedagreidslur/?lthing=%d',
}


# Construct cached XML filename.
def xml_cache_filename(xml_url_name, *args, **kwargs):
    filename = xml_url_name

    for arg in args:
        filename += '.%d' % arg

    if 'days' in kwargs and kwargs['days'] is not None:
        filename += '.days_%d' % kwargs['days']

    filename = os.path.join(althingi_settings.XML_CACHE_DIR, '%s.xml' % filename)

    return filename


# Retrieve XML and cache it
def get_xml(xml_url_name, *args, **kwargs):

    cache_filename = xml_cache_filename(xml_url_name, *args, **kwargs)

    if not os.path.isdir(althingi_settings.XML_CACHE_DIR):
        os.makedirs(althingi_settings.XML_CACHE_DIR)

    if althingi_settings.XML_USE_CACHE and os.path.isfile(cache_filename):
        with open(cache_filename, 'r') as f:
            xml_content = f.read()
            f.close()

    else:
        url = xml_urls[xml_url_name] % args

        if 'days' in kwargs and kwargs['days'] is not None:
            url += '&' if '?' in url else '?'
            url += 'dagar=%d' % kwargs['days']

        response = get_response(url)
        xml_content = response.text

        # Write the XML contents to cache file.
        with open(cache_filename, 'w') as f:
            f.write(xml_content)
            f.close()

    # Return the parsed XML.
    try:
        return etree.fromstring(xml_content.encode('utf-8'))
    except etree.XMLSyntaxError:
        # When XML breaks, we'll want to save the document so that it can be
        # researched by whoever receives notification of the error. Optional
        # and configurable through settings variable.
        if althingi_settings.XML_SAVE_INVALID:

            if not os.path.isdir(althingi_settings.XML_ERROR_DIR):
                os.makedirs(althingi_settings.XML_ERROR_DIR)

            filename = '%s.%s' % (
                datetime.now().strftime('%Y-%m-%d.%H-%M-%S'),
                os.path.basename(cache_filename)
            )
            with open(os.path.join(althingi_settings.XML_ERROR_DIR, filename), 'w') as f:
                f.write(xml_content)

        # Pass on exception so that it gets caught by runtime environment.
        raise


# Clear XML cache.
def clear_xml_cache():
    for filename in os.listdir(althingi_settings.XML_CACHE_DIR):
        fullpath = os.path.join(althingi_settings.XML_CACHE_DIR, filename)
        if os.path.isfile(fullpath):
            os.unlink(fullpath)
    

def get_response(web_url):

    retry_count = 2

    success = False
    while not success and retry_count > -1:
        try:
            response = requests.get(web_url, timeout=althingi_settings.REMOTE_CONTENT_TIMEOUT, headers={'Cache-Control': 'no-cache'})
            success = True
        except IOError:
            print('Retrieving remote content failed, retries left: %s...' % retry_count)
            retry_count = retry_count - 1

    if success:
        return response
    else:
        print('Error: Failed retrieving URL: %s' % web_url, file=stderr)
        quit(1)
