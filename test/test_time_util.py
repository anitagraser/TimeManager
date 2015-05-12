__author__ = 'carolinux'


import TimeManager.time_util as time_util
import TimeManager.flexidate_util as flexidate_util
from datetime import datetime, timedelta

import unittest


__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"

class TestTimeUtil(unittest.TestCase):

    #TODO: v1.7 test bcdate conversion to and from string and epoch

    def test_date_with_bc_is_detected_as_such(self):
        dtstr="0020 BC"
        assert(time_util.get_format_of_timeval(dtstr) == flexidate_util.BC_FORMAT)
        assert(time_util.timeval_to_datetime(dtstr,flexidate_util.BC_FORMAT) == flexidate_util.BCDate(-20,1,1))
        dtstr="0020 AD"
        assert(time_util.get_format_of_timeval(dtstr) == flexidate_util.BC_FORMAT)
        assert(time_util.timeval_to_datetime(dtstr,flexidate_util.BC_FORMAT) == flexidate_util.BCDate(20,1,1))
        assert(time_util.DateTypes.determine_type(dtstr) == time_util.DateTypes.DatesAsStringsArchaelogical)

    def test_datetime_to_str_before_1900_works(self):
        dtstr="01/12/0100"
        fmt="%d/%m/%Y"
        dt = datetime.strptime(dtstr,fmt)
        assert(time_util.datetime_to_str(dt, fmt)==dtstr)

    def test_str_with_microseconds_returns_float(self):
        dtstr ="2013-06-14 11:30:23.100000"
        dt = time_util.str_to_datetime(dtstr,time_util.DEFAULT_FORMAT)
        assert(dt.microsecond==100000)
        numeric = time_util.datetime_to_epoch(dt)
        assert(int(numeric)<float(numeric))
        assert(numeric == 1371209423.1)
