__author__ = 'carolinux'

from datetime import datetime
import unittest

import TimeManager.time_util as time_util


__author__ = "Karolina Alexiou"
__email__ = "karolina.alexiou@teralytics.ch"


class TestTimeUtil(unittest.TestCase):
    def test_ambiguous_format_resolution_years_vs_epoch(self):
        val = "1600"
        dt = time_util.str_to_datetime(val, "%Y")
        assert (dt == datetime(1600, 1, 1))
        dt = time_util.str_to_datetime(val, time_util.UTC)
        assert (dt == datetime.utcfromtimestamp(int(val)))
        dt = time_util.str_to_datetime(val,
                                       time_util.PENDING)  # if not specified, will infer as epoch
        assert (dt == datetime.utcfromtimestamp(int(val)))

    def test_ambiguous_format_resolution_yyymmdd_vs_epoch(self):
        val = "20140306"
        dt = time_util.str_to_datetime(val, "%Y%m%d")
        assert (dt == datetime(2014, 3, 6))
        dt = time_util.str_to_datetime(val, time_util.UTC)
        assert (dt == datetime.utcfromtimestamp(int(val)))
        dt = time_util.str_to_datetime(val, time_util.PENDING)
        assert (dt == datetime.utcfromtimestamp(int(val)))

    def test_datetime_to_str_before_1900_works(self):
        dtstr = "01/12/0100"
        fmt = "%d/%m/%Y"
        dt = datetime.strptime(dtstr, fmt)
        assert (time_util.datetime_to_str(dt, fmt) == dtstr)

    def test_str_with_microseconds_returns_float(self):
        dtstr = "2013-06-14 11:30:23.100000"
        dt = time_util.str_to_datetime(dtstr,
                                       time_util.PENDING)  # test that inference works correctly
        assert (dt.microsecond == 100000)
        numeric = time_util.datetime_to_epoch(dt)
        assert (int(numeric) < float(numeric))
        assert (numeric == 1371209423.1)
