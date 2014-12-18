from mock import Mock
from timerasterlayer import TimeRasterLayer
from timevectorlayer import TimeVectorLayer
from time_util import DEFAULT_FORMAT, UTC
from datetime import datetime, timedelta
import unittest


class TestLayers(unittest.TestCase):

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

        vector = TimeVectorLayer(layer,fromTimeAttribute="1970-01-01 00:01:00",
                             toTimeAttribute="1970-01-01 00:04:20",enabled=True,timeFormat=DEFAULT_FORMAT,offset=0)

        assert(vector.getTimeFormat() == DEFAULT_FORMAT)
        vector.setTimeRestriction(datetime(1970,1,1,0,0,2),timedelta(minutes=5))
        layer.setSubsetString.assert_called_with('"1970-01-01 00:01:00" <= \'1970-01-01 00:00:02\' AND "1970-01-01 00:04:20" >= \'1970-01-01 00:00:02\' ')

        vector.setTimeRestriction(datetime(1980,1,1,0,0,2),timedelta(minutes=5))
        layer.setSubsetString.assert_called_with('"1970-01-01 00:01:00" <= \'1980-01-01 00:00:02\' AND "1970-01-01 00:04:20" >= \'1980-01-01 00:00:02\' ')


    def test_vector_with_int_timestamps(self):
        layer = Mock()
        provider = Mock()
        layer.dataProvider.return_value = provider
        layer.subsetString.return_value =""
        provider.minimumValue.return_value = 60
        provider.maximumValue.return_value = 260
        provider.storageType.return_value ='PostgreSQL database with PostGIS extension'

        vector = TimeVectorLayer(layer,fromTimeAttribute=60,
                             toTimeAttribute=260,enabled=True,timeFormat=DEFAULT_FORMAT,offset=0)

        assert(vector.getTimeFormat() == UTC)
        vector.setTimeRestriction(datetime(1970,1,1,0,3,0),timedelta(minutes=5))
        layer.setSubsetString.assert_called_with('60 <= 180 AND 260 >= 180 ')

        vector.setTimeRestriction(datetime(1980,1,1,0,0,2),timedelta(minutes=5))
        layer.setSubsetString.assert_called_with('60 <= 315532802 AND 260 >= 315532802 ')


if __name__=="__main__":
    unittest.main()
