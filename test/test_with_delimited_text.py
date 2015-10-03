import sip

sip.setapi('QString', 2)  # strange things happen without this. Must import before PyQt imports
# if using ipython: do this on bash before
# export QT_API=pyqt
from qgis.core import *

from mock import Mock
import unittest
from test_functionality import TestForLayersWithOnePointPerSecond
import TimeManager.time_util as time_util
from TimeManager.timemanagercontrol import FRAME_FILENAME_PREFIX
import TimeManager.timevectorlayer as timevectorlayer
import TimeManager.layer_settings as ls

import os
import tempfile
import shutil
import glob

__author__ = 'carolinux'

DFT = "%Y-%m-%d %H:%M:%S+02"  # test timezone format
STARTTIME = 1422191211
DATE_COL = "timestamp"
LON_COL = "lon"
LAT_COL = "lat"
TEXT = """{},{},{}
{},1.01,2.0
{},1.02,2.0
{},1.01,2.0
{},1.02,2.01
{},1.01,2.03
{},1.05,2.0""".format(DATE_COL, LON_COL, LAT_COL, time_util.epoch_to_str(STARTTIME, DFT),
                      time_util.epoch_to_str(STARTTIME + 1, DFT),
                      time_util.epoch_to_str(STARTTIME + 2, DFT),
                      time_util.epoch_to_str(STARTTIME + 3, DFT),
                      time_util.epoch_to_str(STARTTIME + 4, DFT),
                      time_util.epoch_to_str(STARTTIME + 5, DFT))


class TestDelimitedText(TestForLayersWithOnePointPerSecond):
    def get_start_time(self):
        return STARTTIME

    def setUp(self):
        super(TestDelimitedText, self).setUp()
        self.file = tempfile.NamedTemporaryFile(mode="r", delete=False)
        with open(self.file.name, 'w') as f:
            f.write(TEXT)
        # Very good info on creating layers programmatically from the official docs
        # http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/loadlayer.html
        uri = "{}?type=csv&xField={}&yField={}&spatialIndex=no&subsetIndex=no&watchFile=no" \
              "".format(self.file.name, LON_COL, LAT_COL)
        self.layer = QgsVectorLayer(uri, "jumping_points", 'delimitedtext')
        self.assertTrue(self.layer.isValid())
        self.assertEquals(self.layer.featureCount(), 6)

    def tearDown(self):
        super(TestDelimitedText, self).tearDown()
        os.remove(self.file.name)


    def test_date_str(self):
        self._test_layer(self.layer, DATE_COL, timevectorlayer.DateTypes.DatesAsStrings,
                         DFT)
        self.assertEquals(len(self.tlm.getActiveDelimitedText()), 1)

    def test_export_exports_last_frame(self):
        settings = ls.LayerSettings()
        settings.layer = self.layer
        settings.startTimeAttribute = DATE_COL
        settings.endTimeAttribute = DATE_COL
        iface = Mock()
        timeLayer = timevectorlayer.TimeVectorLayer(settings, iface)
        self.tlm.registerTimeLayer(timeLayer)
        tmpdir = tempfile.mkdtemp()
        self.tlm.setTimeFrameType("seconds")
        start_time = time_util.str_to_datetime(timeLayer.getMinMaxValues()[0])
        end_time = time_util.str_to_datetime(timeLayer.getMinMaxValues()[1])
        self.ctrl.exportVideo(tmpdir, 100, False)
        screenshots_generated = glob.glob(os.path.join(tmpdir, FRAME_FILENAME_PREFIX + "*"))
        # import ipdb; ipdb.set_trace()
        last_fn = self.ctrl.generate_frame_filename(tmpdir, len(screenshots_generated) - 1,
                                                    end_time)
        self.assertEquals(6, len(screenshots_generated))
        self.assertIn(last_fn, screenshots_generated)
        print screenshots_generated
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    unittest.main()

