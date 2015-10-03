__author__ = 'carolinux'

from datetime import datetime
import unittest

import TimeManager.query_builder as qb
import TimeManager.time_util as time_util


__author__ = "Karolina Alexiou"
__email__ = "karolina.alexiou@teralytics.ch"


class TestQueryBuilder(unittest.TestCase):
    to_attr = "foo"
    from_attr = "bar"
    start_dt = datetime(2014, 5, 6, 1, 0, 2)
    end_dt = datetime(2015, 4, 3, 11, 0, 2)

    def test_lexicographically_comparable(self):
        fmts = ["%Y/%m/%d", "%Y.%m.%d"]
        for fmt in fmts:
            self.assertTrue(qb.can_compare_lexicographically(fmt))

    def test_not_lexicographically_comparable(self):
        fmts = ["%m/%Y/%d", "%d.%m.%Y"]
        for fmt in fmts:
            self.assertTrue(not qb.can_compare_lexicographically(fmt))

    def test_query_for_lexicographically_comparable_format_(self):
        fmts = ["%d/%m/%Y %H:%M", "%m.%d.%Y %H:%M:%S"]

        for fmt in fmts:
            start_str = time_util.datetime_to_str(self.start_dt, fmt)
            end_str = time_util.datetime_to_str(self.end_dt, fmt)
            # assert that dates are not lexicographically comparable in this format
            self.assertTrue(end_str < start_str and self.start_dt < self.end_dt)

            result_sql = qb.build_query(self.start_dt, self.end_dt, self.from_attr, self.to_attr,
                                        qb.DateTypes.DatesAsStrings, fmt,
                                        qb.QueryIdioms.SQL, False)

            result_ogr = qb.build_query(self.start_dt, self.end_dt, self.from_attr, self.to_attr,
                                        qb.DateTypes.DatesAsStrings, fmt,
                                        qb.QueryIdioms.OGR, False)
            self.assertEqual(result_sql, result_ogr)
