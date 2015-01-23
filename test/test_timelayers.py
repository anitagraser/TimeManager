from mock import Mock
from TimeManager.timerasterlayer import TimeRasterLayer
from TimeManager.timevectorlayer import TimeVectorLayer
from TimeManager.query_builder import INT_FORMAT, STRING_FORMAT
from TimeManager.time_util import DEFAULT_FORMAT, UTC, datetime_to_epoch
from datetime import datetime, timedelta
import unittest


__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"

class TestLayers(unittest.TestCase):

    to_attr="foo"
    from_attr="bar"
    comparison_op="<="

    def test_raster(self):
        layer = Mock()
        renderer = Mock()
        layer.renderer.return_value = renderer
        raster = TimeRasterLayer(layer,fromTimeAttribute="1970-01-01 00:00:01",
                             toTimeAttribute="1970-11-01 06:45:26",enabled=True,timeFormat=DEFAULT_FORMAT,offset=0)

        assert(raster.getTimeFormat() == DEFAULT_FORMAT)

        raster.setTimeRestriction(datetime(1970,1,1,0,0,2),timedelta(minutes=5))
        renderer.setOpacity.assert_called_with(1)


        raster.setTimeRestriction(datetime(1980,1,1,0,0,2),timedelta(minutes=5))
        renderer.setOpacity.assert_called_with(0)


    def test_raster_with_int_timetstamps(self):
        layer = Mock()
        renderer = Mock()
        layer.renderer.return_value = renderer
        raster = TimeRasterLayer(layer,fromTimeAttribute=60,
                             toTimeAttribute=260,enabled=True,timeFormat=DEFAULT_FORMAT,offset=0)

        assert(raster.getTimeFormat() == UTC)
        raster.setTimeRestriction(datetime(1970,1,1,0,0,2),timedelta(minutes=5))
        renderer.setOpacity.assert_called_with(1)
        raster.setTimeRestriction(datetime(1980,1,1,0,0,2),timedelta(minutes=5))
        renderer.setOpacity.assert_called_with(0)


    def test_vector(self):
        layer = Mock()
        provider = Mock()
        layer.dataProvider.return_value = provider
        layer.subsetString.return_value =""
        provider.minimumValue.return_value = "1970-01-01 00:01:00"
        provider.maximumValue.return_value = "1970-01-01 00:04:20"
        provider.storageType.return_value ='PostgreSQL database with PostGIS extension'

        vector = TimeVectorLayer(layer,fromTimeAttribute=self.from_attr,
                             toTimeAttribute=self.to_attr,enabled=True,timeFormat=DEFAULT_FORMAT,
                             offset=0)

        assert(vector.getTimeFormat() == DEFAULT_FORMAT)
        vector.setTimeRestriction(datetime(1970,1,1,0,0,2),timedelta(minutes=5))
        layer.setSubsetString.assert_called_with(STRING_FORMAT.format(self.from_attr,
                                                                      self.comparison_op,
                                                               "1970-01-01 00:00:02",
                                                               self.to_attr,"1970-01-01 "
                                                                     "00:00:02"))

        vector.setTimeRestriction(datetime(1980,1,1,0,0,2),timedelta(minutes=5))
        layer.setSubsetString.assert_called_with(STRING_FORMAT.format(self.from_attr,
                                                                      self.comparison_op,
                                                                   "1980-01-01 00:00:02",
                                                                   self.to_attr,
                                                                   "1980-01-01 "
                                                                   "00:00:02"))


    def test_vector_with_int_timestamps(self):
        layer = Mock()
        provider = Mock()
        layer.dataProvider.return_value = provider
        layer.subsetString.return_value =""
        provider.minimumValue.return_value = 60
        provider.maximumValue.return_value = 260
        provider.storageType.return_value ='PostgreSQL database with PostGIS extension'

        vector = TimeVectorLayer(layer,fromTimeAttribute=self.from_attr,
                             toTimeAttribute=self.to_attr,enabled=True,timeFormat=DEFAULT_FORMAT,
                             offset=0)

        assert(vector.getTimeFormat() == UTC)
        currTime = datetime(1970,1,1,0,3,0)
        vector.setTimeRestriction(currTime,timedelta(minutes=5))
        layer.setSubsetString.assert_called_with(INT_FORMAT.format(self.from_attr,
                                                                   self.comparison_op,datetime_to_epoch(currTime),
                                                                   self.to_attr,
                                                                   datetime_to_epoch(currTime)))

        currTime = datetime(1980,1,1,0,0,2)
        vector.setTimeRestriction(currTime, timedelta(minutes=5))
        layer.setSubsetString.assert_called_with(INT_FORMAT.format(self.from_attr,
                                                                   self.comparison_op,
                                                                   datetime_to_epoch(currTime),
                                                                   self.to_attr,
                                                                   datetime_to_epoch(currTime)))


if __name__=="__main__":
    unittest.main()
