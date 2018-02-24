# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import os
import urllib2

from sys import stderr

from lxml import etree

from althingi import althingi_settings

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
def xml_cache_filename(xml_url_name, *args):
    filename = xml_url_name

    for arg in args:
        filename += '.%d' % arg

    filename = os.path.join(althingi_settings.XML_CACHE_DIR, '%s.xml' % filename)

    return filename


# Retrieve XML and cache it
def get_xml(xml_url_name, *args):

    cache_filename = xml_cache_filename(xml_url_name, *args)

    if not os.path.isdir(althingi_settings.XML_CACHE_DIR):
        os.makedirs(althingi_settings.XML_CACHE_DIR)

    if althingi_settings.USE_XML_CACHE and os.path.isfile(cache_filename):
        with open(cache_filename, 'r') as f:
            xml_content = f.read()
            f.close()

    else:
        response = get_response(xml_urls[xml_url_name] % args)
        xml_content = response.read()

        # Write the XML contents to cache file.
        with open(cache_filename, 'w') as f:
            f.write(xml_content)
            f.close()

    # Return the parsed XML.
    return etree.fromstring(xml_content)


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
            response = urllib2.urlopen(web_url, timeout=althingi_settings.REMOTE_CONTENT_TIMEOUT)
            success = True
        except IOError:
            print('Retrieving remote content failed, retries left: %s...' % retry_count)
            retry_count = retry_count - 1

    if success:
        return response
    else:
        print('Error: Failed retrieving URL: %s' % web_url, file=stderr)
        quit(1)
