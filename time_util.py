from datetime import datetime

DEFAULT_FORMAT = "%Y-%m-%d %H:%M:%S"
UTC = "UTC"
SUPPORTED_FORMATS = [
             "%Y-%m-%d %H:%M:%S",
             "%Y-%m-%d %H:%M:%S.%f",
             "%Y-%m-%d %H:%M",
             "%Y-%m-%d",
             "%Y/%m/%d %H:%M:%S"]

def getFormatOfStr(datetimeString, timeFormat, supportedFormats=SUPPORTED_FORMATS):
    datetimeString = str(datetimeString)
    # is it an integer representing seconds?
    try:
        seconds = int(datetimeString)
        return UTC
    except:
        pass

    try:
       # Try the last known format, if not, try all known formats.
       datetime.strptime(datetimeString, timeFormat)
       return timeFormat
    except:
        for format in supportedFormats:
            try:
                datetime.strptime(datetimeString, format)
                return format
            except:
                pass
    # If all fail, re-raise the exception
    raise


def strToDatetime(datetimeString, timeFormat, supportedFormats=SUPPORTED_FORMATS):
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
       # Try the last known format, if not, try all known formats.
       return datetime.strptime(datetimeString, timeFormat)
    except:
        for format in supportedFormats:
            try:
                return datetime.strptime(datetimeString, format)
            except:
                pass
    # If all fail, re-raise the exception
    raise
