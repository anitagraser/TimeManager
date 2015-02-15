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


    def test_existing_values_return_themselves(self):
        for tupl in tuples:
            id, start_time, geom = tupl
            result = self.lin.getInterpolatedValue(id, start_time, start_time + span)
            self.assertEquals(geom, result)

    def test_values_beyond_border_return_border(self):
        for id in [1,5,6]:
            values_for_id = []
            for (i,val,_) in tuples:
                if i==id:
                    values_for_id.append(val)
            maxval= max(values_for_id)
            minval = min(values_for_id)
            last_before_min = self.lin.getLastEpochBeforeForId(id,minval)
            first_after_max = self.lin.getFirstEpochAfterForId(id,maxval)
            self.assertEquals(maxval, first_after_max)
            self.assertEquals(minval, last_before_min)

