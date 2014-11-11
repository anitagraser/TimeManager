from mock import Mock
from timerasterlayer import TimeRasterLayer
from time_util import DEFAULT_FORMAT, UTC
from datetime import datetime, timedelta


def test_raster():
    layer = Mock()
    raster = TimeRasterLayer(layer,fromTimeAttribute="1970-01-01 00:00:01",
                             toTimeAttribute="1970-11-01 06:45:26",enabled=True,timeFormat=DEFAULT_FORMAT,offset=0)

    assert(raster.getTimeFormat() == DEFAULT_FORMAT)

    raster.setTimeRestriction(datetime(1970,1,1,0,0,2),timedelta(minutes=5))
    layer.setTransparency.assert_called_with(255)

    raster.setTimeRestriction(datetime(1980,1,1,0,0,2),timedelta(minutes=5))
    layer.setTransparency.assert_called_with(0)


def test_raster_with_int_timetstamps():
    layer = Mock()
    raster = TimeRasterLayer(layer,fromTimeAttribute=60,
                             toTimeAttribute=260,enabled=True,timeFormat=DEFAULT_FORMAT,offset=0)

    assert(raster.getTimeFormat() == UTC)
    raster.setTimeRestriction(datetime(1970,1,1,0,0,2),timedelta(minutes=5))
    layer.setTransparency.assert_called_with(255)

    raster.setTimeRestriction(datetime(1980,1,1,0,0,2),timedelta(minutes=5))
    layer.setTransparency.assert_called_with(0)

def test_vector():
    pass

if __name__=="__main__":
    test_vector()
    test_raster()
    test_raster_with_int_timetstamps()
