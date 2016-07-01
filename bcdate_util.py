import re
from datetime import datetime, timedelta

from PyQt4.QtCore import QDateTime
import PyQt4.QtCore as QtCore

from tmlogging import warn
import conf


""" A module to support dates of BC/AD form"""

__author__ = "Karolina Alexiou"
__email__ = "karolina.alexiou@teralytics.ch"


class CustomDate(object):
    pass


_DIGITS = conf.DEFAULT_DIGITS  # default digits for archaeology mode


def getGlobalDigitSetting():
    return _DIGITS


def setGlobalDigitSetting(digits):
    global _DIGITS
    _DIGITS = digits


class ZeroFormatException(Exception):
    pass


def get_max_dt():
    return BCDate((10 ** getGlobalDigitSetting()) - 1)


def get_min_dt():
    return BCDate(-1 * ((10 ** getGlobalDigitSetting()) - 1))


class BCDate(CustomDate):
    def __init__(self, y, m=1, d=1):
        self.digits = getGlobalDigitSetting()
        self.y = y
        self.m = m
        self.d = d

    def setDigits(self, d):
        self.d = d

    def isBC(self):
        return self.y < 0

    def __cmp__(self, other):
        if not isinstance(other, self.__class__):
            return -1
        if self.__lt__(other):
            return -1
        if self.__eq__(other):
            return 0
        return 1

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return True
        if (self.y < other.y or (self.y == other.y and self.m < other.m) or (
                self.y == other.y and self.d == other.d and self.d < other.d)):
            return True
        return False

    def __str__(self):
        year = self.y
        if year >= 0:
            return str(year).zfill(self.digits) + " AD"
        else:
            return str(-year).zfill(self.digits) + " BC"

    def __repr__(self):
        return self.__str__()

    def as_datetime(self):
        return datetime(self.y, self.m, self.d)

    @classmethod
    def from_str(cls, bc, strict_zeros=True):
        try:
            m = re.match("(\d*)\s(AD|BC)", bc)
            year_str = m.group(1)
            if strict_zeros and len(year_str) != getGlobalDigitSetting():
                raise ZeroFormatException(
                    "{} is an invalid date. Need a date string with exactly {} digits, for example {}"
                    .format(bc, getGlobalDigitSetting(),
                            "22".zfill(getGlobalDigitSetting()) + " BC"))
            y = int(year_str)
            bc = m.group(2)
            if bc == "BC":
                y = -y
            if bc not in ("BC", "AD") or y == 0:
                raise Exception
            return BCDate(y)
        except ZeroFormatException, z:
            raise z
        except Exception, e:
            raise Exception(
                "{} is an invalid archaelogical date, should be 'number AD' or 'number BC'".format(
                    bc) +
                "and year 0 (use {} AD or BC instead) doesn't exist.".format(
                    "1".zfill(getGlobalDigitSetting())))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.y == other.y and self.m == other.m and self.d == other.d
        else:
            return False

    def _get_years_from_timedelta(self, td):
        try:
            return td.years
        except Exception, e:
            # FIXME v.1.7 what about offset?
            msg = "BC dates can only be used with year intervals, found {}".format(td)
            warn(msg)
            return 0

    @classmethod
    def dist(cls, bc1, bc2):
        if (bc1.y * bc2.y > 0):
            return bc1.y - bc2.y
        else:
            return bc1.y - bc2.y - 1

    def __isub__(self, td):
        return self._iadd__(td * -1)

    def __sub__(self, td):
        return self.__add__(td * -1)

    def __iadd__(self, td):
        if isinstance(td, BCDate):
            to_add = td.y
        else:  # some sort of timedelta/relativedelta
            to_add = self._get_years_from_timedelta(td)
        self.y = self._get_new_year_value(self.y, to_add)
        return self

    def _get_new_year_value(self, old_y, to_add):
        """Adjust for absence of year zero"""
        new_y = old_y + to_add
        if (new_y == 0 or new_y * old_y < 0) and new_y < old_y:
            # if we went from AD to BC substract one for non-existant year 0
            new_y -= 1
        elif (new_y == 0 or new_y * old_y < 0) and new_y > old_y:
            # if we went from BC to AD add one for non-existant year 0
            new_y += 1
        return new_y

    def __add__(self, td):
        if isinstance(td, BCDate):
            to_add = td.y
        else:  # some sort of timedelta/relativedelta
            to_add = self._get_years_from_timedelta(td)
        return BCDate(self._get_new_year_value(self.y, to_add))

    def __hash__(self):
        return (self.y << 10) + (self.m << 4) + self.d


BC_FORMAT = "Y with BC/AD"
SECONDS_IN_YEAR = 60 * 60 * 24 * 365


def _year(fdate):
    return int(fdate.y)


def timeval_to_epoch(val):
    if isinstance(val, str) or isinstance(val, unicode):
        return bcdate_to_epoch(str_to_bcdate(val))
    if isinstance(val, BCDate):
        return bcdate_to_epoch(val)


def timeval_to_bcdate(val):
    epoch = timeval_to_epoch(val)
    return epoch_to_bcdate(epoch)


def epoch_to_bcdate(seconds_from_epoch):
    """Convert seconds since 1970-1-1 (UNIX epoch) to a FlexiDate object"""
    if seconds_from_epoch >= YEAR_ONE_EPOCH:
        dt = datetime(1970, 1, 1) + timedelta(seconds=seconds_from_epoch)
        return BCDate(dt.year, dt.month, dt.day)
    else:
        seconds_bc = abs(seconds_from_epoch - YEAR_ONE_EPOCH)
        years_bc = seconds_bc / SECONDS_IN_YEAR
        years_bc += 1  # for year 0
        return BCDate.from_str(str(years_bc).zfill(getGlobalDigitSetting()) + " BC")


def bcdate_to_epoch(fd):
    """ convert a FlexiDate to seconds after (or possibly before) 1970-1-1 """
    if _year(fd) > 0:
        res = (fd.as_datetime() - datetime(1970, 1, 1)).total_seconds()
    else:
        part1 = (datetime(1, 1, 1) - datetime(1970, 1, 1)).total_seconds()
        # coarsely get the epoch time for time BC, people didn't have a normal
        # calendar back then anyway
        part2 = - (abs(_year(fd)) - 1) * SECONDS_IN_YEAR  # -1 because year 0 doesn't exist
        res = part1 + part2
    return int(res)


YEAR_ONE_EPOCH = bcdate_to_epoch(BCDate(1))


def str_to_bcdate(datetimeString):
    """convert a date/time string into a FlexiDate object"""
    return BCDate.from_str(datetimeString)


def epoch_to_str(seconds_from_epoch):
    return datetime_to_str(epoch_to_datetime(seconds_from_epoch))
