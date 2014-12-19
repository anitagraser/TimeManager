from datetime import datetime
from PyQt4.QtCore import QDateTime

""" A module to have time related functionality """

__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"

DEFAULT_FORMAT = "%Y-%m-%d %H:%M:%S"
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
    return datetime.strptime( str(date.toString('yyyy-MM-dd hh:mm:ss.zzz')) ,"%Y-%m-%d %H:%M:%S.%f")

def ordinal_to_datetime(ordinal):
    """Convert a number of seconds till the beginning of time (NOT the epoch of 1970 but year 0) to datetime"""
    return datetime.fromordinal(int(ordinal) if ordinal>0 else 1)

def epoch_to_datetime(seconds_from_epoch):
    """Convert seconds since 1970-1-1 (UNIX epoch) to a datetime"""
    return datetime.utcfromtimestamp(seconds_from_epoch)

def time_position_to_datetime(pos):
    if type(pos) == datetime:
        return pos
    if type(pos) == QDateTime:
        #convert QDateTime to datetime :
        return QDateTime_to_datetime(pos)
    elif type(pos) == int or type(pos) == float:
        return epoch_to_datetime(pos)#ordinal_to_datetime(pos)

def datetime_to_epoch(dt):
    """ convert a datetime to seconds after (or possibly before) 1970-1-1 """
    return int((dt - datetime(1970,1,1)).total_seconds())

def datetime_to_str(dt, fmt):
    """ strftime has a bug for years<1900, so fixing """
    if dt.year>=1900:
        return datetime.strftime(dt, fmt)
    else:
        #TODO: work-around
        raise Exception("Invalid date (<1900) for strftime")

def getFormatOfStr(datetimeString, hint=DEFAULT_FORMAT):
    datetimeString = str(datetimeString)
    # is it an integer representing seconds?
    try:
        seconds = int(datetimeString)
        return UTC
    except:
        pass

    formatsToTry = [hint] + SUPPORTED_FORMATS
    for format in formatsToTry:
        try:
            datetime.strptime(datetimeString, format)
            return format
        except:
            pass
    # If all fail, raise an exception
    raise "Could not find a suitable time format for value {}".format(datetimeString)


def strToDatetime(datetimeString):
    """convert a date/time string into a Python datetime object"""
    return strToDatetimeWithFormatHint(datetimeString, hint=getFormatOfStr(datetimeString))


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
