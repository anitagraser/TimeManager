
from datetime import datetime, timedelta
from PyQt4.QtCore import QDateTime
import PyQt4.QtCore as QtCore


""" A module to support dates of BC/AD form"""

__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"


class CustomDate(object):
    pass

class BCDate(CustomDate):
    def __init__(self, y,m=1,d=1):
        self.y = y
        self.m = m
        self.d = d

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
        if (self.y< other.y or (self.y==other.y and self.m < other.m) or(self.y==other.y and self.d == other.d and self.d < other.d)):
            return True
        return False

    def __str__(self):
        return flexidate_to_str(self)

    def as_datetime(self):
        return datetime(self.y,self.m,self.d)

    @classmethod
    def from_str(cls, bc):
        y = int(bc[:4])
        #TODO v.17 use regex! not like this.. and informative error message
        bc = bc[-2:]
        if bc =="BC":
            y = -y
        return BCDate(y)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.y == other.y and self.m == other.m and self.d == other.d
        else:
            return False

    def __iadd__(self, td):
        #TODO: actually override, year 0 considerations
        self.y = self.y+1
        return self

    def __add__(self, td):
        #TODO: actually override, year 0 considerations
        return BCDate(self.y+1)

    def __hash__(self):
        return (self.y<<10)  + (self.m<<4) + self.d

BC_FORMAT="Y with BC/AD"
SECONDS_IN_YEAR = 60 * 60 *24 *365

def is_archaelogical(val):
    if isinstance(val,str) or isinstance(val,unicode):
        return "BC" in val or "AD" in val
    if isinstance(val, BCDate):
        return True
    if isinstance(val, int):
        return int<YEAR_ONE_EPOCH

def _year(fdate):
    return int(fdate.y)

def timeval_to_epoch(val):
    if isinstance(val,str) or isinstance(val,unicode):
        return flexidate_to_epoch(str_to_flexidate(val))
    if isinstance(val, BCDate):
        return flexidate_to_epoch(val)

def timeval_to_flexidate(val):
    epoch = timeval_to_epoch(val)
    return epoch_to_flexidate(epoch)

def epoch_to_flexidate(seconds_from_epoch):
    """Convert seconds since 1970-1-1 (UNIX epoch) to a FlexiDate object"""
    if seconds_from_epoch > YEAR_ONE_EPOCH :
        dt = datetime(1970, 1, 1) + timedelta(seconds=seconds_from_epoch)
        return BCDate(dt.year, dt.month, dt.day)
    else:
        seconds_bc = abs(seconds_from_epoch - YEAR_ONE_EPOCH)
        years_bc = seconds_bc/SECONDS_IN_YEAR
        return BCDate.from_str(str(years_bc).zfill(4)+" BC")

def flexidate_to_epoch(fd):
    """ convert a FlexiDate to seconds after (or possibly before) 1970-1-1 """
    if _year(fd)>0:
        res = (fd.as_datetime() - datetime(1970,1,1)).total_seconds()
    else:
        part1 =  (datetime(1,1,1) - datetime(1970,1,1)).total_seconds()
        # coarsely get the epoch time for time BC, people didn't have a normal
        # calendar back then anyway
        part2 = - abs(_year(fd)) * SECONDS_IN_YEAR 
        res = part1 + part2
    return int(res)


YEAR_ONE_EPOCH = flexidate_to_epoch(BCDate(1))

def flexidate_to_str(dt):
    year = _year(dt)
    if year>=0:
        return str(dt.y).zfill(4)+" AD"
    else:
        return str(dt.y).zfill(4) +" BC"

def str_to_flexidate(datetimeString):
    """convert a date/time string into a FlexiDate object"""
    return BCDate.from_str(datetimeString)

def epoch_to_str(seconds_from_epoch):
    return datetime_to_str(epoch_to_datetime(seconds_from_epoch))

