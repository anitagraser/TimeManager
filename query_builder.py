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
            if typ==cls.DatesAsQDates:
                return OGR_DATE_FORMAT
            if typ==cls.DatesAsQDateTimes:
                return OGR_DATETIME_FORMAT
        raise Exception


class QueryBuildingException(Exception):
    pass

def can_compare_lexicographically(date_format):
    """Can only compare lexicographically when the order of appearance in the string
    is year, month, date"""
    # fortunately, date formats cannot have the same %x twice
    ioy=date_format.find("%Y")
    iom=date_format.find("%m")
    iod=date_format.find("%d")
    ioh=date_format.find("%H")
    iomin=date_format.find("%M")
    ios=date_format.find("%S")
    return ioy<=iom and iom<=iod and (iod<=ioh or ioh==-1) and (ioh<=iomin or iomin==-1) and \
    (iomin<=ios or ios==-1)

def create_ymd_substring(ioy,iom,iod,ioh,col, quote_type):
    q=quote_type
    ystr = "SUBSTR({}{}{},{},{})".format(q,col,q, ioy+1,ioy+5) if ioy>=0 else None # adding 1
    # because SQL indexing is 1-based
    mstr = "SUBSTR({}{}{},{},{})".format(q,col,q, iom+1,iom+3)  if iom>=0 else None
    dstr = "SUBSTR({}{}{},{},{})".format(q,col,q, iod+1,iod+3)  if iod>=0 else None
    max_index = max(ioy,iom,iod)
    ior = max_index + (2 if max_index!=ioy else 4) # find where the rest of the string is
    reststr = "SUBSTR({}{}{},{},{})".format(q,col,q, ior+1, ior+1+6+6)  if ioh>=0 else None
    string_components = filter(lambda x: x is not None,[ystr,mstr,dstr,reststr])
    return ",".join(string_components)


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
        # thankfully, SQL & OGR syntax agree on substr and concat
        if date_type!=DateTypes.DatesAsStrings:
            raise QueryBuildingException()
        ioy=date_format.find("%Y")
        iom=date_format.find("%m")
        iod=date_format.find("%d")
        ioh=date_format.find("%H")

        sub1=create_ymd_substring(ioy,iom,iod,ioh,from_attr,quote_type='"') # quote type for column
        # names
        sub2=create_ymd_substring(ioy,iom,iod,ioh,end_str, quote_type='\'') # quote type for values
        sub3=create_ymd_substring(ioy,iom,iod,ioh,to_attr, quote_type='"')
        sub4=create_ymd_substring(ioy,iom,iod,ioh,start_str, quote_type='\'')
        query = "CONCAT({}) {} CONCAT({}) AND CONCAT({})>=CONCAT({})".format(sub1,comparison,
                                                                            sub2,sub3,sub4)
        return query

