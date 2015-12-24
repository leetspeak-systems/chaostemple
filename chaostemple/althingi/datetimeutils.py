from datetime import date
from datetime import datetime
import pytz

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

