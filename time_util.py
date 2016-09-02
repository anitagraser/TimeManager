import time
import re  # for hacking strftime
import abc
from datetime import datetime, timedelta
from math import ceil

from dateutil.relativedelta import relativedelta
from PyQt4.QtCore import QDateTime
import PyQt4.QtCore as QtCore

import bcdate_util


""" A module to have time related functionality """

__author__ = "Karolina Alexiou"
__email__ = "karolina.alexiou@teralytics.ch"

OGR_DATE_FORMAT = "%Y/%m/%d"
OGR_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
# TODO: There is also an OGR format with milliseconds
DEFAULT_FORMAT = "%Y-%m-%d %H:%M:%S"
SAVE_STRING_FORMAT = DEFAULT_FORMAT  # Used to be: "%Y-%m-%d %H:%M:%S.%f",
# but this format is not portable in Windows because of the %f directive
PENDING = "WILL BE INFERRED"
UTC = "SECONDS FROM EPOCH"
UTC_FLOAT = "SECONDS FROM EPOCH (float)"
NETCDF_BAND = "NetCDF Time Dimension"
NORMAL_MODE = "Normal Mode"
ARCHAELOGY_MODE = "Archaeology Mode"
DINOSAURS_MODE = "Paleontology Mode"

_mode = NORMAL_MODE


def setCurrentMode(new_mode):
    global _mode
    _mode = new_mode


def getCurrentMode():
    return _mode


def setArchDigits(digits):
    bcdate_util.setGlobalDigitSetting(digits)


def getArchDigits():
    return bcdate_util.getGlobalDigitSetting()


def is_archaelogical():
    return _mode == ARCHAELOGY_MODE


class UnsupportedFormatException(Exception):
    pass


class DateTypes:
    IntegerTimestamps = "IntegerTimestamps"
    DatesAsStrings = "DatesAsStrings"
    DatesAsStringsArchaelogical = "DatesAsStringsArchaelogical"
    DatesAsQDates = "DatesAsQDates"
    DatesAsQDateTimes = "DatesAsQDateTimes"
    nonQDateTypes = [IntegerTimestamps, DatesAsStrings, DatesAsStringsArchaelogical]
    QDateTypes = [DatesAsQDates, DatesAsQDateTimes]

    @classmethod
    def determine_type(cls, val):
        if is_archaelogical():
            return cls.DatesAsStringsArchaelogical
        try:
            float(val)
            return cls.IntegerTimestamps
        except:
            pass
        try:
            int(val)
            return cls.IntegerTimestamps
        except:
            if type(val) is QtCore.QDate:
                return cls.DatesAsQDates
            if type(val) is QtCore.QDateTime:
                return cls.DatesAsQDateTimes
            return cls.DatesAsStrings

    @classmethod
    def get_type_format(cls, typ):
        if typ in cls.nonQDateTypes:
            raise Exception
        else:
            if typ == cls.DatesAsQDates:
                return OGR_DATE_FORMAT
            if typ == cls.DatesAsQDateTimes:
                return OGR_DATETIME_FORMAT
        raise Exception


def _cast_to_int_or_float(val):
    if int(val) == float(val):
        return int(val)
    else:
        return float(val)


def _str_switch(str, substr1, substr2):
    """Switch the location in a string of two substrings"""
    i1 = str.find(substr1)
    i2 = str.find(substr2)
    if i1 < 0 or i2 < 0:
        return str
    if i1 < i2:
        return str[:i1] + substr2 + str[i1 + len(substr1):i2] + substr1 + str[i2 + len(substr2):]
    if i1 == i2:
        return str
    if i1 > i2:
        return str[:i2] + substr1 + str[i2 + len(substr2):i1] + substr2 + str[i1 + len(substr1):]


def generate_all_timezones(fmt):
    l = [fmt+" UTC"]
    for i in range(-12, 15):
        l.append(fmt + ("-" if i < 0 else "+") + str(abs(i)).zfill(2))
    return l


BASIC_SUPPORTED_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%MZ",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S.%f",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
    "%H:%M:%S",
    "%H:%M:%S.%f",
    "%Y.%m.%d %H:%M:%S.%f",
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y.%m.%d",
    "%Y%m%d%H%M%SED"
]

YMD_SUPPORTED_FORMATS = BASIC_SUPPORTED_FORMATS + generate_all_timezones("%Y-%m-%d %H:%M:%S")

DMY_SUPPORTED_FORMATS = map(lambda x: _str_switch(x, "%Y", "%d"), YMD_SUPPORTED_FORMATS)
MDY_SUPPORTED_FORMATS = map(lambda x: _str_switch(x, "%m", "%d"), DMY_SUPPORTED_FORMATS)

OTHER_FORMATS = ["%Y-%m"]

SUPPORTED_FORMATS = list(
    YMD_SUPPORTED_FORMATS + MDY_SUPPORTED_FORMATS + DMY_SUPPORTED_FORMATS + OTHER_FORMATS)


def is_date_object(val):
    return isinstance(val, datetime) or isinstance(val, bcdate_util.BCDate)


def updateUi(ui, val):
    if is_archaelogical():
        ui.setText(str(val))
        return
    else:
        ui.setDateTime(val)


def get_max_dt():
    if is_archaelogical():
        return bcdate_util.get_max_dt()
    return datetime(9999, 12, 31, 23, 59, 59, 999999)


def get_min_dt():
    if is_archaelogical():
        return bcdate_util.get_min_dt()
    return datetime(1, 1, 1, 0, 0, 0, 0)


def timeval_to_epoch(val, fmt):
    """Converts any string, number, datetime or Qdate or QDatetime to epoch"""
    if is_archaelogical():
        return bcdate_util.timeval_to_epoch(val)
    try:
        return int(val)
    except:
        try:
            return float(val)
        except:
            if type(val) in [QtCore.QDate, QtCore.QDateTime]:
                val = QDateTime_to_datetime(val)
            if type(val) in [str, basestring, unicode]:
                val = str_to_datetime(val, fmt)
            return datetime_to_epoch(val)


def timeval_to_datetime(val, fmt):
    if is_archaelogical():
        return bcdate_util.timeval_to_bcdate(val)
    epoch = timeval_to_epoch(val, fmt)
    return epoch_to_datetime(epoch)


def QDateTime_to_datetime(date):
    try:
        return date.toPyDateTime()
    except:
        return datetime_at_start_of_day(date.toPyDate())


def datetime_at_start_of_day(dt):
    return datetime.combine(dt, datetime.min.time())


def datetime_at_end_of_day(dt):
    return datetime.combine(dt, datetime.max.time())


def epoch_to_datetime(seconds_from_epoch):
    """Convert seconds since 1970-1-1 (UNIX epoch) to a datetime"""
    # This doesnt work on windows for negative timestamps
    # http://stackoverflow.com/questions/22082103/on-windows-how-to-convert-a-timestamps-before-1970-into-something-manageable # nopep8
    # return datetime.utcfromtimestamp(seconds_from_epoch)
    # but this should:
    if is_archaelogical():
        return bcdate_util.epoch_to_bcdate(seconds_from_epoch)
    else:
        return datetime(1970, 1, 1) + timedelta(seconds=seconds_from_epoch)


def epoch_to_str(seconds_from_epoch, fmt):
    return datetime_to_str(epoch_to_datetime(seconds_from_epoch), fmt)


def datetime_to_epoch(dt):
    """ convert a datetime to seconds after (or possibly before) 1970-1-1 """
    if is_archaelogical():
        return bcdate_util.bcdate_to_epoch(dt)
    res = ((dt - datetime(1970, 1, 1)).total_seconds())
    return _cast_to_int_or_float(res)


def datetime_to_str(dt, fmt):
    """ strftime has a bug for years<1900, so fixing it as well as we can """
    if is_archaelogical():
        return str(dt)
    if "%" not in fmt:
        raise Exception(
            "{} does not look like a time format for val {} of type {}".format(fmt, dt, type(dt)))
    if dt.year >= 1900:
        return datetime.strftime(dt, fmt)
    else:
        return _fixed_strftime(dt, fmt)

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
        i = j + 1
    return sites


def _fixed_strftime(dt, fmt):
    illegal_formatting = _illegal_formatting.search(fmt)
    if illegal_formatting:
        raise TypeError(
            "strftime of dates before 1900 does not handle" + illegal_formatting.group(0))
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
    s2 = time.strftime(fmt, (year + 28,) + timetuple[1:])
    sites2 = _findall(s2, str(year + 28))
    sites = []
    for site in sites1:
        if site in sites2:
            sites.append(site)
    s = s1
    syear = "%04d" % (dt.year,)
    for site in sites:
        s = s[:site] + syear + s[site + 4:]
    return s


def get_format_of_timeval(datetimeValue):
    typ = DateTypes.determine_type(datetimeValue)
    if typ == DateTypes.DatesAsStringsArchaelogical:
        return bcdate_util.BC_FORMAT
    if typ in DateTypes.QDateTypes:
        return DateTypes.get_type_format(typ)
    datetimeValue = str(datetimeValue)
    # is it an integer representing seconds?
    try:
        seconds = int(datetimeValue)
        return UTC
    except:
        pass
    # is it a float representing seconds and milliseconds after the floating point?
    try:
        seconds = float(datetimeValue)
        return UTC_FLOAT
    except:
        pass

    for format in SUPPORTED_FORMATS:
        try:
            datetime.strptime(datetimeValue, format)
            return format
        except:
            pass
    # If all fail, raise an exception
    raise UnsupportedFormatException(
        "Could not find a suitable time format for value {}".format(datetimeValue))


def createNiceMessage(dateStr, specified_fmt, is_arch, e):
    if is_arch:
        return "Data with value {} is not a valid archaelogical format. Cause: {}".format(dateStr,
                                                                                          e) + \
               "If you are trying to use a regular date, please disable archaelogical mode by clicking on the" + \
               "button next to Settings"

    if specified_fmt == PENDING:
        return "Could not match value {} with any of the supported formats. Tried: <br> {}".format(
            dateStr, '<br>'.join(OTHER_FORMATS + BASIC_SUPPORTED_FORMATS))
    else:
        return "You specified that the format of {} is {}, but this did not succeed. Please check again".format(
            dateStr, specified_fmt)


def str_to_datetime(datetimeString, fmt=PENDING):
    """convert a date/time string into a Python datetime object"""
    datetimeString = str(datetimeString)
    specified_fmt = fmt
    try:
        if is_archaelogical():
            return bcdate_util.str_to_bcdate(datetimeString)
        if fmt == PENDING:
            fmt = get_format_of_timeval(datetimeString)
        if fmt == UTC:
            return epoch_to_datetime(int(datetimeString))
        if fmt == UTC_FLOAT:
            return epoch_to_datetime(float(datetimeString))
        return datetime.strptime(datetimeString, fmt)
    except Exception, e:
        raise UnsupportedFormatException(
            createNiceMessage(datetimeString, specified_fmt, is_archaelogical(), e))


def get_frame_count(start, end, td):
    if not is_archaelogical():
        try:
            td1 = end - start
        except:  # hope this fixes #17 which I still cannot reproduce
            return 0

        td2 = td
        if isinstance(td2, relativedelta):
            # convert back to timedelta
            # approximately (it makes the interval <= the actual interval but this way around it doesn't matter)
            # for the frame count
            td2 = timedelta(weeks=4 * td2.months, days=365 * td2.years)
        # this is how you can devide two timedeltas (not supported by default):
        us1 = td1.total_seconds()
        us2 = td2.total_seconds()

        if us2 == 0:
            raise Exception("Cannot have zero length timeFrame")  # this should never happen
            # it's forbidden at UI level

        return int(us1 * 1.0 / us2)
    else:
        years = bcdate_util.BCDate.dist(end, start)
        return int(years / td.years)


def is_archaeological_layer(layer):
    return layer.getTimeFormat() in [bcdate_util.BC_FORMAT]


def to_discrete_datetime(extent, time_type, time_frame):
    """
    :param extent: current start end end time (as (datetime, datetime) tuple) from project extents
    :param time_type: one of "minutes", "years" etc
    :param time_frame: length of a time frame in the TimeManager plugin (in time_type units!)
    :return: an extent, being a tuple of a start datetiem and an end datetime

    Given the time_frame, time_type and time_start, return a new start/endtime in which current start_time fits,
    but is starting on a time_start (of type time_type) and within not more then one time_frame from current
    end_time.

    In other words: find the first (last) best discrete datetime before current start_time and best discrete
    endtime after current end_time
    """

    dt0 = extent[0]  # datetime 0 /start
    d0 = dt0.date()  # date 0 /start
    t0 = dt0.time()  # time 0 / start
    # dte, de and te stand for datetime-end, date-end, time-end

    if time_type == "microseconds":
        # first round start to hh:mm:ss.000000
        dt0 = datetime.combine(d0, t0.replace(microsecond=0))
        # determine new time_length
        time_length = (datetime_to_epoch(extent[1]) - datetime_to_epoch(dt0)) * 1000000  # microseconds
        # determine max possible frames in this time_length, round to top
        frames = ceil(time_length/time_frame)
        if frames == 0:
            frames = 1
        # how many seconds are there in these number of frames * frame_time
        microseconds = int(frames * time_frame)
        # add that number of seconds to the startdatetime to create a new enddatetime
        dte = dt0 + timedelta(microseconds=microseconds)
    elif time_type == "milliseconds":
        # first round start to hh:mm:ss.000000
        dt0 = datetime.combine(d0, t0.replace(microsecond=0))
        # determine new time_length
        time_length = (datetime_to_epoch(extent[1]) - datetime_to_epoch(dt0)) * 1000  # milliseconds
        # determine max possible frames in this time_length, round to top
        frames = ceil(time_length/time_frame)
        if frames == 0:
            frames = 1
        # how many seconds are there in these number of frames * frame_time
        milliseconds = int(frames * time_frame)
        # add that number of seconds to the startdatetime to create a new enddatetime
        dte = dt0 + timedelta(milliseconds=milliseconds)
    elif time_type == "seconds":
        # first round start to hh:mm:00.000000
        dt0 = datetime.combine(d0, t0.replace(second=0, microsecond=0))
        # determine new time_length
        time_length = datetime_to_epoch(extent[1]) - datetime_to_epoch(dt0)
        # determine max possible frames in this time_length, round to top
        frames = ceil(time_length/time_frame)
        if frames == 0:
            frames = 1
        # how many seconds are there in these number of frames * frame_time
        seconds = int(frames * time_frame)
        # add that number of seconds to the startdatetime to create a new enddatetime
        dte = dt0 + timedelta(seconds=seconds)
    elif time_type == "minutes":
        # first round start to yyyy-mm-ddThh:00:00.000000
        dt0 = datetime.combine(d0, t0.replace(minute=0, second=0, microsecond=0))
        # determine new time_length (in seconds, multiply by 60)
        time_length = (datetime_to_epoch(extent[1]) - datetime_to_epoch(dt0)) / (60)
        # determine max possible frames in this time_length, round to top
        frames = ceil(time_length / time_frame)
        if frames == 0:
            frames = 1
        # how many minutes are there in these number of frames * frame_time
        minutes = int(frames * time_frame)
        # add that number of minutes to the startdatetime to create a new enddatetime
        dte = dt0 + timedelta(minutes=minutes)
    elif time_type == "hours":
        # first round start to yyyy-mm-ddThh:00:00.000000
        dt0 = datetime.combine(d0, t0.replace(minute=0, second=0, microsecond=0))
        # determine new time_length (in seconds, multiply by 60*60)
        time_length = (datetime_to_epoch(extent[1]) - datetime_to_epoch(dt0)) / (60*60)
        # determine max possible frames in this time_length, round to top
        frames = ceil(time_length / time_frame)
        if frames == 0:
            frames = 1
        # how many hours are there in these number of frames * frame_time
        hours = int(frames * time_frame)
        # add that number of hours to the startdatetime to create a new enddatetime
        dte = dt0 + timedelta(hours=hours)
    else:
        # date based...
        t0 = t0.replace(hour=0, minute=0, second=0, microsecond=0)
        if time_type == "days":
            # first round start to yyyy-mm-ddT00:00:00.000000
            dt0 = datetime.combine(d0, t0)
            # determine new time_length (in seconds)
            time_length = datetime_to_epoch(extent[1]) - datetime_to_epoch(dt0)
            # determine max possible frames in this time_length, round to top
            frames = ceil(time_length / (time_frame * 24 * 60 * 60))
            if frames == 0:
                frames = 1
            # how many days are there in these number of frames * frame_time
            days = int(frames * time_frame)
            # add that number of hours to the startdatetime to create a new enddatetime
            dte = dt0 + relativedelta(days=days)
        elif time_type == "weeks":
            # first round start to yyyy-mm-ddT00:00:00.000000
            dt0 = datetime.combine(d0, t0)
            # determine new time_length (in seconds)
            time_length = datetime_to_epoch(extent[1]) - datetime_to_epoch(dt0)
            # determine max possible frames in this time_length, round to top
            frames = ceil(time_length / (time_frame * 7 * 24 * 60 * 60))
            if frames == 0:
                frames = 1
            # how many days are there in these number of frames * frame_time
            weeks = int(frames * time_frame)
            # add that number of hours to the startdatetime to create a new enddatetime
            dte = dt0 + relativedelta(weeks=weeks)
        elif time_type == "months":
            # first round start to yyyy-mm-ddT00:00:00.000000
            dt0 = datetime.combine(d0, t0)
            # determine new time_length (in seconds)
            time_length = datetime_to_epoch(extent[1]) - datetime_to_epoch(dt0)
            # determine max possible frames in this time_length, round to top
            frames = ceil(time_length / (time_frame * (365.25/12) * 24 * 60 * 60))
            if frames == 0:
                frames = 1
            # how many days are there in these number of frames * frame_time
            months = int(frames * time_frame)
            # add that number of hours to the startdatetime to create a new enddatetime
            dte = dt0 + relativedelta(months=months)
        elif time_type == "years":
            # first round start to yyyy-1-1T00:00:00.000000
            dt0 = datetime.combine(d0.replace(month=1, day=1), t0)
            # determine new time_length (in seconds)
            time_length = datetime_to_epoch(extent[1]) - datetime_to_epoch(dt0)
            # determine max possible frames in this time_length, round to top
            frames = ceil(time_length / (time_frame * 365.25 * 24 * 60 * 60))
            if frames == 0:
                frames = 1
            # how many years are there in these number of frames * frame_time
            years = int(frames * time_frame)
            # add that number of hours to the startdatetime to create a new enddatetime
            dte = dt0 + relativedelta(years=years)

    return (dt0, dte)


