__author__ = 'carolinux'

from PyQt4 import QtCore

from time_util import DateTypes
import time_util


STRINGCAST_FORMAT = 'cast("{}" as character) {} \'{}\' AND cast("{}" as character) >= \'{}\' '
INT_FORMAT = "{} {} {} AND {} >= {} "
STRING_FORMAT = "\"{}\" {} '{}' AND \"{}\" >= '{}' "


class QueryIdioms:
    OGR = "OGR"
    SQL = "SQL"


class QueryBuildingException(Exception):
    pass


def can_compare_lexicographically(date_format):
    """Can only compare lexicographically when the order of appearance in the string
    is year, month, date"""
    # fortunately, valid date formats cannot have the same %x twice
    ioy = date_format.find("%Y")
    iom = date_format.find("%m")
    iod = date_format.find("%d")
    ioh = date_format.find("%H")
    iomin = date_format.find("%M")
    ios = date_format.find("%S")
    return ioy <= iom and iom <= iod and (iod <= ioh or ioh == -1) and\
        (ioh <= iomin or iomin == -1) and (iomin <= ios or ios == -1)


def create_ymd_substring(ioy, iom, iod, ioh, col, quote_type):
    q = quote_type
    ystr = "SUBSTR({}{}{},{},{})".format(q, col, q, ioy + 1,
                                         ioy + 5) if ioy >= 0 else None  # adding 1
    # because SQL indexing is 1-based
    mstr = "SUBSTR({}{}{},{},{})".format(q, col, q, iom + 1, iom + 3) if iom >= 0 else None
    dstr = "SUBSTR({}{}{},{},{})".format(q, col, q, iod + 1, iod + 3) if iod >= 0 else None
    max_index = max(ioy, iom, iod)
    ior = max_index + (2 if max_index != ioy else 4)  # find where the rest of the string is
    reststr = "SUBSTR({}{}{},{},{})".format(q, col, q, ior + 1,
                                            ior + 1 + 8 + 1 + 6) if ioh >= 0 else None
    string_components = filter(lambda x: x is not None, [ystr, mstr, dstr, reststr])
    return ",".join(string_components)


def likeBC(attr, cast=False):
    if not cast:
        return '"{}" LIKE  \'%BC\''.format(attr)
    else:
        return ' cast("{}" as character) LIKE  \'%BC\''.format(attr)


def likeAD(attr, cast=False):
    if not cast:
        return '"{}" LIKE  \'%AD\''.format(attr)
    else:
        return ' cast("{}" as character) LIKE  \'%AD\''.format(attr)


AND = " AND "
OR = " OR "


def NOT(q):
    return "NOT ({})".format(q)


def lessThan(val, col, equals=False, cast=False):
    comparison = '<' if not equals else '<='
    if not cast:
        return " '{}' {} \"{}\" ".format(val, comparison, col)
    else:
        return " '{}' {} cast(\"{}\" as character) ".format(val, comparison, col)


def greaterThan(val, col, equals=False, cast=False):
    comparison = '>' if not equals else '>='
    if not cast:
        return " '{}' {} \"{}\" ".format(val, comparison, col)
    else:
        return " '{}' {} cast(\"{}\" as character) ".format(val, comparison, col)


def isAfter(col, val, equals=False, bc=False, cast=False):
    if not bc:
        return lessThan(val, col, equals, cast=False)
    else:
        return greaterThan(val, col, equals, cast)


def isBefore(col, val, equals=False, bc=False, cast=False):
    return isAfter(col, val, equals, not bc, cast)


def paren(q):
    return "( " + q + " )"


# start_attr <- from_attr, end_attr <- to_attr
def build_query_archaelogical(start_str, end_str, start_attr, end_attr, comparison, query_idiom):
    cast = query_idiom == QueryIdioms.OGR  # if it's OGR need to cast as string
    if "BC" in start_str and "BC" in end_str:
        # for BC need to invert the order of comparisons
        return paren(paren(
            likeBC(end_attr, cast=cast) + AND + isAfter(col=end_attr, val=start_str, equals=True,
                                                        bc=True, cast=cast)) + OR + likeAD(
            end_attr, cast=cast)) \
                + AND \
                + paren(likeBC(start_attr, cast=cast) + AND + isBefore(col=start_attr, val=end_str,
                                                                      equals=('=' in comparison),
                                                                      bc=True, cast=cast))

    if "AD" in start_str and "AD" in end_str:
        return paren(
            likeAD(end_attr, cast=cast) + AND + isAfter(col=end_attr, val=start_str, equals=True,
                                                        bc=False, cast=cast)) \
               + AND \
               + paren(likeBC(start_attr, cast=cast) + OR + paren(
            isBefore(col=start_attr, val=end_str, equals=('=' in comparison), bc=False, cast=cast) \
            + AND + likeAD(start_attr, cast=cast)))

    # can only be start_attr = BC and end_attr = AD
    return paren(
        NOT(likeAD(start_attr, cast=cast)) + OR + paren(likeAD(start_attr, cast=cast) + AND \
                                                        + greaterThan(val=end_str, col=start_attr,
                                                                      equals=('=' in comparison),
                                                                      cast=cast))) \
           + AND \
           + paren(NOT(likeBC(end_attr, cast=cast)) + OR + paren(likeBC(end_attr, cast=cast) + AND \
                                                                 + greaterThan(val=start_str,
                                                                               col=end_attr,
                                                                               equals=True,
                                                                               cast=cast)))


def build_query(start_dt, end_dt, from_attr, to_attr, date_type, date_format, query_idiom, acc):
    """Build subset query"""

    if acc:
        # features never die
        start_dt = time_util.get_min_dt()

    comparison = "<" if to_attr == from_attr else "<="

    if date_type == DateTypes.IntegerTimestamps:
        start_epoch = time_util.datetime_to_epoch(start_dt)
        end_epoch = time_util.datetime_to_epoch(end_dt)
        return INT_FORMAT.format(from_attr, comparison, end_epoch, to_attr,
                                 start_epoch)

    start_str = time_util.datetime_to_str(start_dt, date_format)
    end_str = time_util.datetime_to_str(end_dt, date_format)

    if date_type == DateTypes.DatesAsStringsArchaelogical:
        return build_query_archaelogical(start_str, end_str, from_attr, to_attr, comparison,
                                         query_idiom)

    if can_compare_lexicographically(date_format):
        if query_idiom == QueryIdioms.OGR:
            return STRINGCAST_FORMAT.format(from_attr, comparison, end_str, to_attr, start_str)
        else:
            return STRING_FORMAT.format(from_attr, comparison, end_str, to_attr, start_str)

    else:
        # thankfully, SQL & OGR syntax agree on substr and concat
        if date_type != DateTypes.DatesAsStrings:
            raise QueryBuildingException()
        ioy = date_format.find("%Y")
        iom = date_format.find("%m")
        iod = date_format.find("%d")
        ioh = date_format.find("%H")

        sub1 = create_ymd_substring(ioy, iom, iod, ioh, from_attr,
                                    quote_type='"')  # quote type for column
        # names
        sub2 = create_ymd_substring(ioy, iom, iod, ioh, end_str,
                                    quote_type='\'')  # quote type for values
        sub3 = create_ymd_substring(ioy, iom, iod, ioh, to_attr, quote_type='"')
        sub4 = create_ymd_substring(ioy, iom, iod, ioh, start_str, quote_type='\'')
        query = "CONCAT({}) {} CONCAT({}) AND CONCAT({})>=CONCAT({})".format(sub1, comparison,
                                                                             sub2, sub3, sub4)
        return query
