from mock import Mock

from TimeManager.interpolation import interpolator

import unittest


__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"


# test tuples of id,timestamp, point coords
tuples = [(1,100, [0,0]), (1,200,[1,1]), (1,400,[2,2]),
          (5,120,[0,0]),(5,240,[1,1]),
          (6,50,[3,3])]

span = 10

class TestLinearInterpolatorBuilder(unittest.TestCase):


    def setUp(self):
        self.lin = interpolator.LinearInterpolator()
        for tupl in tuples:
            self.lin.addIdEpochTuple(*tupl)

        self.lin.sort()

    def testInterpolation(self):
        result = self.lin.getInterpolatedValue(1, 150, 160)
        expected = [0.5,0.5]
        self.assertEquals(result, expected)

    def testInterpolationWhenPointIsInInterval(self):
        # when point is in interval we shouldn't try to interpolate
        # if we do interpolates between previous position and next, ie here
        # 100 and 400 and [0,0],[2,2] fr val = 150
        result = self.lin.getInterpolatedValue(1, 150, 210)
        expected = [2*50/300.0, 2*50/300.0]
        self.assertAlmostEqual(result[0], expected[0], 5)
        self.assertAlmostEqual(result[1], expected[1], 5)

    def test_existing_values_return_themselves(self):
        for tupl in tuples:
            id, start_time, geom = tupl
            result = self.lin.getInterpolatedValue(id, start_time, start_time + span)
            self.assertEquals(geom, result)

    def test_values_beyond_border_return_border(self):
        for id in [1,5,6]:
            values_for_id = map(lambda (i,v,g):v, filter(lambda (i,v,g):i==id,tuples))
            maxval= max(values_for_id)
            minval = min(values_for_id)
            last_before_min = self.lin.getLastEpochBeforeForId(id,minval)
            first_after_max = self.lin.getFirstEpochAfterForId(id,maxval)
            self.assertEquals(maxval, first_after_max)
            self.assertEquals(minval, last_before_min)

