from datetime import datetime, timedelta
import unittest

from mock import Mock

from TimeManager.timerasterlayer import TimeRasterLayer
from TimeManager.timevectorlayer import TimeVectorLayer
from TimeManager.query_builder import INT_FORMAT, STRING_FORMAT
from TimeManager.time_util import DEFAULT_FORMAT, UTC, datetime_to_epoch
import TimeManager.layer_settings as ls


__author__ = "Karolina Alexiou"
__email__ = "karolina.alexiou@teralytics.ch"


class TestLayers(unittest.TestCase):
    to_attr = "foo"
    from_attr = "bar"
    comparison_op = "<="

    def test_raster(self):
        layer = Mock()
        renderer = Mock()
        layer.renderer.return_value = renderer
        settings = ls.LayerSettings()
        settings.layer = layer
        settings.startTimeAttribute = "1970-01-01 00:00:01"
        settings.endTimeAttribute = "1970-11-01 06:45:26"
        raster = TimeRasterLayer(settings, iface=Mock())

        assert (raster.getTimeFormat() == DEFAULT_FORMAT)

        raster.setTimeRestriction(datetime(1970, 1, 1, 0, 0, 2), timedelta(minutes=5))
        renderer.setOpacity.assert_called_with(1)

        raster.setTimeRestriction(datetime(1980, 1, 1, 0, 0, 2), timedelta(minutes=5))
        renderer.setOpacity.assert_called_with(0)


    def test_raster_with_int_timetstamps(self):
        layer = Mock()
        renderer = Mock()
        layer.renderer.return_value = renderer
        settings = ls.LayerSettings()
        settings.layer = layer
        settings.startTimeAttribute = 60
        settings.endTimeAttribute = 260
        raster = TimeRasterLayer(settings, iface=Mock())

        assert (raster.getTimeFormat() == UTC)
        raster.setTimeRestriction(datetime(1970, 1, 1, 0, 0, 2), timedelta(minutes=5))
        renderer.setOpacity.assert_called_with(1)
        raster.setTimeRestriction(datetime(1980, 1, 1, 0, 0, 2), timedelta(minutes=5))
        renderer.setOpacity.assert_called_with(0)


    def test_vector(self):
        layer = Mock()
        layer.subsetString.return_value = ""
        layer.minimumValue.return_value = "1970-01-01 00:01:00"
        layer.maximumValue.return_value = "1970-01-01 00:04:20"
        layer.uniqueValues.return_value = ["1970-01-01 00:04:20", "1970-01-01 00:01:00"]
        settings = ls.LayerSettings()
        settings.layer = layer
        settings.startTimeAttribute = self.from_attr
        settings.endTimeAttribute = self.to_attr

        vector = TimeVectorLayer(settings, iface=Mock())

        assert (vector.getTimeFormat() == DEFAULT_FORMAT)
        td = timedelta(minutes=5)
        vector.setTimeRestriction(datetime(1970, 1, 1, 0, 0, 2), td)
        layer.setSubsetString.assert_called_with(STRING_FORMAT.format(self.from_attr,
                                                                      self.comparison_op,
                                                                      "1970-01-01 00:05:02",
                                                                      self.to_attr, "1970-01-01 "
                                                                                    "00:00:02"))

        vector.setTimeRestriction(datetime(1980, 1, 1, 0, 0, 2), td)
        layer.setSubsetString.assert_called_with(STRING_FORMAT.format(self.from_attr,
                                                                      self.comparison_op,
                                                                      "1980-01-01 00:05:02",
                                                                      self.to_attr,
                                                                      "1980-01-01 "
                                                                      "00:00:02"))

    def test_vector_with_int_timestamps(self):
        layer = Mock()
        layer.subsetString.return_value = ""
        layer.minimumValue.return_value = 60
        layer.maximumValue.return_value = 260
        layer.uniqueValues.return_value = [60, 260]
        settings = ls.LayerSettings()
        settings.layer = layer
        settings.startTimeAttribute = self.from_attr
        settings.endTimeAttribute = self.to_attr
        vector = TimeVectorLayer(settings, iface=Mock())

        assert (vector.getTimeFormat() == UTC)
        td = timedelta(minutes=5)
        currTime = datetime(1970, 1, 1, 0, 3, 0)
        vector.setTimeRestriction(currTime, td)
        layer.setSubsetString.assert_called_with(INT_FORMAT.format(self.from_attr,
                                                                   self.comparison_op,
                                                                   datetime_to_epoch(
                                                                       currTime + td),
                                                                   self.to_attr,
                                                                   datetime_to_epoch(currTime)))

        currTime = datetime(1980, 1, 1, 0, 0, 2)

        vector.setTimeRestriction(currTime, td)
        layer.setSubsetString.assert_called_with(INT_FORMAT.format(self.from_attr,
                                                                   self.comparison_op,
                                                                   datetime_to_epoch(
                                                                       currTime + td),
                                                                   self.to_attr,
                                                                   datetime_to_epoch(
                                                                       currTime)))


if __name__ == "__main__":
    unittest.main()
