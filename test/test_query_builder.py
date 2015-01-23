__author__ = 'carolinux'


from mock import Mock
from TimeManager.timerasterlayer import TimeRasterLayer
from TimeManager.timevectorlayer import TimeVectorLayer
from TimeManager.query_builder import INT_FORMAT, STRING_FORMAT
from TimeManager.time_util import DEFAULT_FORMAT, UTC, datetime_to_epoch
import TimeManager.query_builder as qb
import TimeManager.time_util as time_util
from datetime import datetime, timedelta

import unittest


__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"

class TestQueryBuilder(unittest.TestCase):

    to_attr="foo"
    from_attr="bar"
    start_dt = datetime(2014,5,6,1,0,2)
    end_dt = datetime(2015,4,3,11,0,2)

    def test_query_for_lexicographically_comparable_format_(self):
        fmts=["%d/%m/%Y %H:%M","%m.%d.%Y %H:%M:%S"]

        for fmt in fmts:
            start_str = time_util.datetime_to_str(self.start_dt,fmt)
            end_str = time_util.datetime_to_str(self.end_dt,fmt)
            # assert that dates are not lexicographically comparable in this format
            self.assertTrue(end_str<start_str and self.start_dt<self.end_dt)

            result_sql = qb.build_query(self.start_dt, self.end_dt, self.from_attr, self.to_attr,
                                    qb.DateTypes.DatesAsStrings,fmt,
                                    qb.QueryIdioms.SQL)

            result_ogr = qb.build_query(self.start_dt, self.end_dt, self.from_attr, self.to_attr,
                                    qb.DateTypes.DatesAsStrings,fmt,
                                    qb.QueryIdioms.OGR)
            self.assertEqual(result_sql,result_ogr)
            #TODO more assertions wrt to the end format