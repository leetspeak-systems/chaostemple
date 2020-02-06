import errno
import os
import pytz

from sys import stdout
from datetime import date
from datetime import datetime

from althingi import althingi_settings
from althingi.xmlutils import get_response

# We simply **cannot** be bothered to figure out the fancy locale-based way of
# doing this. These months will always be Icelandic and in no other language,
# and we don't care about the OS's or runtime environment's opinion on that.
ICELANDIC_MONTHS = {
    1: 'janúar',
    2: 'febrúar',
    3: 'mars',
    4: 'apríl',
    5: 'maí',
    6: 'júní',
    7: 'júlí',
    8: 'ágúst',
    9: 'september',
    10: 'október',
    11: 'nóvember',
    12: 'desember',
}


# To determine whether the time is 'árdegis', 'á hádegi', 'miðdegis' or
# 'síðdegis' according to Althingi's customs.
def icelandic_am_pm(dt):
    if dt.hour >= 0 and dt.hour < 12:
        return 'árdegis'
    elif dt.hour == 12 and dt.minute == 0:
        return 'á hádegi'
    elif ((dt.hour == 12 and dt.minute > 0) or dt.hour > 12) and dt.hour < 15:
        return 'miðdegis'
    elif dt.hour >= 15:
        return 'síðdegis'


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

    content = get_response(remote_path).content
    localpath = os.path.join(althingi_settings.STATIC_DOCUMENT_DIR, local_filename)
    mkpath(os.path.dirname(localpath))
    outfile = open(localpath, 'wb')
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

    content = response.content
    localpath = os.path.join(althingi_settings.STATIC_DOCUMENT_DIR, local_filename)
    mkpath(os.path.dirname(localpath))
    outfile = open(localpath, 'wb')
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
                try:
                    d = datetime.strptime(value, '%d.%m.%Y')
                except ValueError:
                    try:
                        d = datetime.strptime(value, '%Y-%m-%d %H:%M+00:00')
                    except ValueError:
                        raise ValueError('Could not figure out datetime format for "%s"' % value)

    if d.tzinfo:
        return d
    else:
        return pytz.timezone('UTC').localize(d)


# Monkey-patch iCalendar output text to make up for `ics`s lack of support for
# a few fields.
def monkey_patch_ical(ical_text, name, description=None, time_zone=None, duration=None):
    extra = [
        'NAME:%s' % name,
        'X-WR-CALNAME:%s' % name,
    ]

    if description is not None:
        extra += [
            'DESCRIPTION:%s' % description,
            'X-WR-CALDESC:%s' % description,
        ]

    if time_zone is not None:
        extra += [
            'TIMEZONE-ID:%s' % time_zone,
            'X-WR-TIMEZONE:%s' % time_zone,
        ]

    if duration is not None:
        extra += [
            'REFRESH-INTERVAL;VALUE=DURATION:%s' % duration,
            'X-PUBLISHED-TTL:%s' % duration,
        ]

    newlines = []
    for line in ical_text.split('\r\n'):
        newlines.append(line)
        if line[0:7] == 'PRODID:':
            newlines += extra

    return '\r\n'.join(newlines)


# Short-hand function for putting quotes around an input value, primarily for
# use in CSV exporting.
def quote(input_string):
    return '"%s"' % input_string if input_string not in [None, 'None'] else '""'
