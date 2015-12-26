# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import errno
import os
import urllib2
import pytz

from sys import stderr
from sys import stdout
from datetime import date
from datetime import datetime
from althingi import althingi_settings

def get_response(web_url):

    retry_count = 2

    success = False
    while not success and retry_count > -1:
        try:
            response = urllib2.urlopen(web_url, timeout=5)
            success = True
        except IOError:
            print('Retrieving remote content failed, retries left: %s...' % retry_count)
            retry_count = retry_count - 1

    if success:
        return response
    else:
        print('Error: Failed retrieving URL: %s' % web_url, file=stderr)
        quit(1)


def mkpath(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


# Download and save document
def maybe_download_document(remote_path, parliament_num, issue_num):

    if not althingi_settings.DOWNLOAD_DOCUMENTS:
        return ''

    basename = os.path.basename(remote_path)

    stdout.write('Downloading file %s...' % basename)
    stdout.flush()

    local_filename = os.path.join('althingi', parliament_num.__str__(), issue_num.__str__(), basename)

    content = get_response(remote_path).read()
    localpath = os.path.join(althingi_settings.STATIC_DOCUMENT_DIR, local_filename)
    mkpath(os.path.dirname(localpath))
    outfile = open(localpath, 'w')
    outfile.write(content)
    outfile.close()

    stdout.write('done\n')

    return local_filename


# Download and review document
def maybe_download_review(remote_path, log_num, parliament_num, issue_num):

    if not althingi_settings.DOWNLOAD_REVIEWS:
        return ''

    basename = os.path.basename(remote_path)

    stdout.write('Downloading review with log number %d...' % log_num)
    stdout.flush()

    response = get_response(remote_path)

    filename = os.path.basename(remote_path)
    local_filename = os.path.join('althingi', parliament_num.__str__(), issue_num.__str__(), filename)

    content = response.read()
    localpath = os.path.join(althingi_settings.STATIC_DOCUMENT_DIR, local_filename)
    mkpath(os.path.dirname(localpath))
    outfile = open(localpath, 'w')
    outfile.write(content)
    outfile.close()

    stdout.write('done\n')

    return local_filename


def get_last_parliament_num():
    return althingi_settings.CURRENT_PARLIAMENT_NUM  # Temporary, while we figure out a wholesome way to auto-detect


'''
A function for consistently formatting dates in script output.
Since datetime.strftime() can't handle dates prior to 1900 we must assume a format of '%Y-%m-%d'.
'''
def format_date(dt):
    if dt.year >= 1900:
        return dt.strftime('%Y-%m-%d')

    month = '0%d' % dt.month if len(str(dt.month)) == 1 else dt.month
    day = '0%d' % dt.day if len(str(dt.day)) == 1 else dt.day

    return '%s-%s-%s' % (dt.year, month, day)


def sensible_datetime(value):

    if value is None:
        return None

    if type(value) is date:
        d = datetime(value.year, value.month, value.day, 0, 0, 0)
    elif type(value) is datetime:
        d = value
    else:
        try:
            d = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            try:
                d = datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                d = datetime.strptime(value, '%d.%m.%Y')

    return pytz.timezone('UTC').localize(d)

