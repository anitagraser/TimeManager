__author__ = 'carolinux'

from datetime import datetime
from dateutil.relativedelta import relativedelta

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

    def test_discrete_boundaries(self):

        dte = datetime.now()
        te = dte.time()
        te.replace(hour=8)
        de = dte.date()

        dte = datetime.combine(de, te.replace(hour=8, minute=33, second=3))
        self.assertEquals(dte.time().minute, 33)
        self.assertEquals(dte.time().second, 3)

        ## SECONDS

        time_frame = 90                        # timeframe 90 secs
        t0 = te.replace(hour=8, minute=31, second=33)  # create an extent of 2 minutes
        dt0 = datetime.combine(de, t0)
        r = time_util.to_discrete_datetime((dt0, dte), "seconds", time_frame)
        self.assertEquals(r[0].time().hour, 8)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].time().minute, 31)
        self.assertEquals(r[1].time().minute, 34)
        self.assertEquals((r[1]-r[0]).seconds, 180)

        # Test to check if we go back over hour boundary
        t0 = t0.replace(hour=1, minute=59, second=33)
        dt0 = datetime.combine(de, t0)
        te = te.replace(hour=2, minute=0, second=33)
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "seconds", time_frame)
        self.assertEquals(r[0].time().hour, 1)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].time().minute, 59)
        self.assertEquals(r[1].time().minute, 2)
        self.assertEquals((r[1] - r[0]).seconds, 180)

        # Test to check if we go back over day boundary
        d0 = dt0.date().replace(day=1,month=1,year=2000)
        t0 = t0.replace(hour=23, minute=59, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=2,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=33)
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "seconds", time_frame)
        self.assertEquals(r[0].time().hour, 23)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].time().minute, 59)
        self.assertEquals(r[0].date().day, 1)
        self.assertEquals(r[1].time().minute, 2)
        self.assertEquals(r[1].date().day, 2)
        self.assertEquals((r[1] - r[0]).seconds, 180)

        # Test to check if we go back over year boundary
        d0 = dt0.date().replace(day=31,month=12,year=1999)
        t0 = t0.replace(hour=23, minute=59, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=1,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=33)
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "seconds", time_frame)
        self.assertEquals(r[0].time().hour, 23)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].time().minute, 59)
        self.assertEquals(r[0].date().day, 31)
        self.assertEquals(r[1].time().minute, 2)
        self.assertEquals(r[1].date().day, 1)
        self.assertEquals((r[1] - r[0]).seconds, 180)

        ## MILLISECONDS

        time_frame = 10  # milliseconds
        d0 = dt0.date().replace(day=31,month=12,year=1999)
        t0 = t0.replace(hour=23, minute=59, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=1,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=0, microsecond=10000 )
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "milliseconds", time_frame)
        self.assertEquals(r[0].time().hour, 23)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].time().minute, 59)
        self.assertEquals(r[0].date().day, 31)
        self.assertEquals(r[1].time().microsecond, 10000)
        self.assertEquals(r[1].time().minute, 0)
        self.assertEquals(r[1].time().hour, 0)
        self.assertEquals(r[1].date().day, 1)
        self.assertEquals((r[1] - r[0]).seconds + ((r[1] - r[0]).microseconds/1000000.0), 27.01)

        ## MICROSECONDS

        time_frame = 1000  # microseconds
        d0 = dt0.date().replace(day=31,month=12,year=1999)
        t0 = t0.replace(hour=23, minute=59, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=1,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=0, microsecond=10000 )
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "microseconds", time_frame)
        self.assertEquals(r[0].time().hour, 23)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].time().minute, 59)
        self.assertEquals(r[0].date().day, 31)
        self.assertEquals(r[1].time().microsecond, 10000)
        self.assertEquals(r[1].time().minute, 0)
        self.assertEquals(r[1].time().hour, 0)
        self.assertEquals(r[1].date().day, 1)
        self.assertEquals((r[1] - r[0]).seconds + ((r[1] - r[0]).microseconds/1000000.0), 27.01)

        ## MINUTES

        time_frame = 5  # minutes
        d0 = dt0.date().replace(day=31,month=12,year=1999)
        t0 = t0.replace(hour=23, minute=57, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=1,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=33)
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "minutes", time_frame)
        self.assertEquals(r[0].time().hour, 23)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].time().minute, 0)
        self.assertEquals(r[0].date().day, 31)
        self.assertEquals(r[1].time().minute, 5)
        self.assertEquals(r[1].time().hour, 0)
        self.assertEquals(r[1].date().day, 1)
        self.assertEquals((r[1] - r[0]).seconds, 65*60)


        ## HOURS

        time_frame = 1 # hour
        d0 = dt0.date().replace(day=31,month=12,year=1999)
        t0 = t0.replace(hour=23, minute=59, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=1,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=33)
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "hours", time_frame)
        self.assertEquals(r[0].time().hour, 23)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].time().minute, 0)
        self.assertEquals(r[0].date().day, 31)
        self.assertEquals(r[1].time().minute, 0)
        self.assertEquals(r[1].date().day, 1)
        self.assertEquals((r[1] - r[0]).seconds, 2*60*60)

        ## DAYS

        time_frame = 2 # day
        d0 = dt0.date().replace(day=31,month=12,year=1999)
        t0 = t0.replace(hour=23, minute=59, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=1,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=33)
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "days", time_frame)
        self.assertEquals(r[0].time().hour, 0)
        self.assertEquals(r[0].time().minute, 0)
        self.assertEquals(r[0].time().second, 0)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].date().day, 31)
        self.assertEquals(r[1].time().minute, 0)
        self.assertEquals(r[1].date().day, 2)
        self.assertEquals((r[1] - r[0]).days, 2)

        ## WEEKS

        time_frame = 1 # week
        d0 = dt0.date().replace(day=31,month=12,year=1999)
        t0 = t0.replace(hour=23, minute=59, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=1,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=33)
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "weeks", time_frame)
        self.assertEquals(r[0].time().hour, 0)
        self.assertEquals(r[0].time().minute, 0)
        self.assertEquals(r[0].time().second, 0)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].date().day, 31)
        self.assertEquals(r[1].time().minute, 0)
        self.assertEquals(r[1].date().day, 7)
        self.assertEquals((r[1] - r[0]).days, time_frame * 7)

        time_frame = 2  # 2 weeks (grow extent to 2 weeks)
        r = time_util.to_discrete_datetime((dt0, dte), "weeks", time_frame)
        self.assertEquals((r[1] - r[0]).days, time_frame * 7)

        ## MONTHS

        time_frame = 1 # month
        d0 = dt0.date().replace(day=31,month=12,year=1999)
        t0 = t0.replace(hour=23, minute=59, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=1,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=33)
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "months", time_frame)
        self.assertEquals(r[0].time().hour, 0)
        self.assertEquals(r[0].time().minute, 0)
        self.assertEquals(r[0].time().second, 0)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].date().day, 31)
        self.assertEquals(r[1].time().minute, 0)
        self.assertEquals(relativedelta(r[1], r[0]), relativedelta(months=+1))

        time_frame = 2  # 2 months (grow extent to 2 month)
        r = time_util.to_discrete_datetime((dt0, dte), "months", time_frame)
        self.assertEquals(relativedelta(r[1], r[0]), relativedelta(months=+2))

        ## YEARS
        time_frame = 3 # year
        d0 = dt0.date().replace(day=31,month=12,year=1999)
        t0 = t0.replace(hour=23, minute=59, second=33)
        dt0 = datetime.combine(d0, t0)
        de = de.replace(day=1,month=1,year=2000)
        te = te.replace(hour=0, minute=0, second=33)
        dte = datetime.combine(de, te)
        r = time_util.to_discrete_datetime((dt0, dte), "years", time_frame)
        self.assertEquals(r[0].time().hour, 0)
        self.assertEquals(r[0].time().microsecond, 0)
        self.assertEquals(r[0].time().minute, 0)
        self.assertEquals(r[0].date().day, 1)
        self.assertEquals(r[1].time().minute, 0)
        self.assertEquals(r[1].date().day, 1)
        self.assertEquals(relativedelta(r[1], r[0]), relativedelta(years=+3))

