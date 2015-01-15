import time
import re # for hacking strftime

from datetime import datetime, timedelta
from PyQt4.QtCore import QDateTime


""" A module to have time related functionality """

__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"


OGR_DATE_FORMAT="%Y/%m/%d"
OGR_DATETIME_FORMAT="%Y-%m-%dT%H:%M:%S" # FIXME so date has slashes and datetime dashes???
DEFAULT_FORMAT = "%Y-%m-%d %H:%M:%S"
SAVE_STRING_FORMAT =  DEFAULT_FORMAT # Used to be: "%Y-%m-%d %H:%M:%S.%f", but this format is not portable in Windows because of the %f directive
UTC = "UTC"
SUPPORTED_FORMATS = [
"%Y-%m-%d %H:%M:%S.%f",
"%Y-%m-%d %H:%M:%S",
"%Y-%m-%d %H:%M",
"%Y-%m-%d",
"%Y/%m/%d %H:%M:%S.%f",
"%Y/%m/%d %H:%M:%S",
"%Y/%m/%d %H:%M",
"%Y/%m/%d",
"%d.%m.%Y %H:%M:%S.%f",
"%d.%m.%Y %H:%M:%S",
"%d.%m.%Y %H:%M",
"%d.%m.%Y",
"%d-%m-%Y %H:%M:%S.%f",
"%d-%m-%Y %H:%M:%S",
"%d-%m-%Y %H:%M",
"%d-%m-%Y",
"%d/%m/%Y %H:%M:%S.%f",
"%d/%m/%Y %H:%M:%S",
"%d/%m/%Y %H:%M",
"%d/%m/%Y"
]

def QDateTime_to_datetime(date):
    return date.toPyDateTime()

def datetime_at_start_of_day(dt):
    return datetime.combine(dt, datetime.min.time())

def datetime_at_end_of_day(dt):
    return datetime.combine(dt, datetime.max.time())

def epoch_to_datetime(seconds_from_epoch):
    """Convert seconds since 1970-1-1 (UNIX epoch) to a datetime"""
    #FIXME: Maybe this doesnt work on windows for negative timestamps
    # http://stackoverflow.com/questions/22082103/on-windows-how-to-convert-a-timestamps-before-1970-into-something-manageable
    # return datetime.utcfromtimestamp(seconds_from_epoch)
    # but this should:
    return datetime(1970, 1, 1) + timedelta(seconds=seconds_from_epoch)

def datetime_to_epoch(dt):
    """ convert a datetime to seconds after (or possibly before) 1970-1-1 """
    return int((dt - datetime(1970,1,1)).total_seconds())

def datetime_to_str(dt, fmt=DEFAULT_FORMAT):
    """ strftime has a bug for years<1900, so fixing it as well as we can """
    if dt.year>=1900:
        return datetime.strftime(dt, fmt)
    else:
        return fixed_strftime(dt, fmt)

# Based on code submitted to comp.lang.python by Andrew Dalke and subsequently used on the django project
# https://github.com/django/django/
# This fix does not support strftime's "%s" or "%y" format strings.
# Allowed if there's an even number of "%"s because they are escaped.
_illegal_formatting = re.compile(r"((^|[^%])(%%)*%[sy])")

def _findall(text, substr):
    # Also finds overlaps
    sites = []
    i = 0
    while 1:
        j = text.find(substr, i)
        if j == -1:
            break
        sites.append(j)
        i=j+1
    return sites

def fixed_strftime(dt, fmt):

    illegal_formatting = _illegal_formatting.search(fmt)
    if illegal_formatting:
        raise TypeError("strftime of dates before 1900 does not handle" + illegal_formatting.group(0))
    year = dt.year
    # For every non-leap year century, advance by
    # 6 years to get into the 28-year repeat cycle
    delta = 2000 - year
    off = 6 * (delta // 100 + delta // 400)
    year = year + off
    # Move to around the year 2000
    year = year + ((2000 - year) // 28) * 28
    timetuple = dt.timetuple()
    s1 = time.strftime(fmt, (year,) + timetuple[1:])
    sites1 = _findall(s1, str(year))
    s2 = time.strftime(fmt, (year+28,) + timetuple[1:])
    sites2 = _findall(s2, str(year+28))
    sites = []
    for site in sites1:
        if site in sites2:
            sites.append(site)
    s = s1
    syear = "%4d" % (dt.year,)
    for site in sites:
        s = s[:site] + syear + s[site+4:]
    return s

def getFormatOfDatetimeValue(datetimeValue, hint=DEFAULT_FORMAT):
    #FIXME, here we can see if the type is QDate and handle it accordingly
    datetimeValue = str(datetimeValue)
    # is it an integer representing seconds?
    try:
        seconds = int(datetimeValue)
        return UTC
    except:
        pass

    formatsToTry = [hint] + SUPPORTED_FORMATS
    for format in formatsToTry:
        try:
            datetime.strptime(datetimeValue, format)
            return format
        except:
            pass
    # If all fail, raise an exception
    raise Exception("Could not find a suitable time format for value {}, choices {}".format(datetimeValue, formatsToTry))

def str_to_datetime(str, fmt):
    return strToDatetimeWithFormatHint(str, fmt)


def strToDatetime(datetimeString):
    """convert a date/time string into a Python datetime object"""
    return strToDatetimeWithFormatHint(datetimeString, hint=getFormatOfDatetimeValue(datetimeString))


def strToDatetimeWithFormatHint(datetimeString, hint=DEFAULT_FORMAT):
    """convert a date/time string into a Python datetime object"""
    datetimeString = str(datetimeString)
    # is it an integer representing seconds?
    try:
        seconds = int(datetimeString)
        return datetime.utcfromtimestamp(seconds)
    except:
        pass
     
    # is it a string in a known format?
    try:
       # Try the hinted format, if not, try all known formats.
       return datetime.strptime(datetimeString, hint)
    except:
        for format in SUPPORTED_FORMATS:
            try:
                return datetime.strptime(datetimeString, format)
            except:
                pass
    # If all fail, re-raise the exception
    raise
