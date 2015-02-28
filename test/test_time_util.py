__author__ = 'carolinux'


import TimeManager.time_util as time_util
from datetime import datetime, timedelta

import unittest


__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"

class TestTimeUtil(unittest.TestCase):

    def test_str_with_microseconds_returns_float(self):
        dtstr ="2013-06-14 11:30:23.100000"
        dt = time_util.str_to_datetime(dtstr,time_util.DEFAULT_FORMAT)
        assert(dt.microsecond==100000)
        numeric = time_util.datetime_to_epoch(dt)
        assert(int(numeric)<float(numeric))
        assert(numeric == 1371209423.1)
