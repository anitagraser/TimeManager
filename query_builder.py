__author__ = 'carolinux'


from PyQt4 import QtCore
import time_util
from time_util import OGR_DATETIME_FORMAT, OGR_DATE_FORMAT
STRINGCAST_FORMAT='cast("{}" as character) {} \'{}\' AND cast("{}" as character) >= \'{}\' '
INT_FORMAT="{} {} {} AND {} >= {} "
STRING_FORMAT="\"{}\" {} '{}' AND \"{}\" >= '{}' "

class QueryIdioms:
    OGR="OGR"
    SQL="SQL"


class DateTypes:
    IntegerTimestamps="IntegerTimestamps"
    DatesAsStrings="DatesAsStrings"
    DatesAsQDates="DatesAsQDates"
    DatesAsQDateTimes="DatesAsQDateTimes"
    nonQDateTypes = [IntegerTimestamps,DatesAsStrings]
    QDateTypes = [DatesAsQDates, DatesAsQDateTimes]

    @classmethod
    def determine_type(cls, val):
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
            if typ==cls.DatesAsQDates:
                return OGR_DATE_FORMAT
            if typ==cls.DatesAsQDateTimes:
                return OGR_DATETIME_FORMAT
        raise Exception


def can_compare_lexicographically(date_format):
    # Date formats cannot have the same %x twice
    # But they can have %x and %X
    return True

def build_query(start_dt, end_dt, from_attr, to_attr, date_type, date_format, query_idiom):
    """Build subset query"""

    comparison ="<" if to_attr==from_attr else "<="

    if date_type==DateTypes.IntegerTimestamps:
        start_epoch = time_util.datetime_to_epoch(start_dt)
        end_epoch = time_util.datetime_to_epoch(end_dt)
        return INT_FORMAT.format(from_attr,comparison,end_epoch, to_attr,
                                      start_epoch)

    start_str = time_util.datetime_to_str(start_dt,date_format)
    end_str = time_util.datetime_to_str(end_dt,date_format)

    if can_compare_lexicographically(date_format):
        if query_idiom == QueryIdioms.OGR:
            return STRINGCAST_FORMAT.format(from_attr,comparison,end_str,to_attr,start_str)
        else:
            return STRING_FORMAT.format(from_attr,comparison,end_str,to_attr,start_str)

    else:
        raise Exception("Not Implemented yet")


