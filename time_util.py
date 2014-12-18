from datetime import datetime

""" A module to have time related functionality """

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
