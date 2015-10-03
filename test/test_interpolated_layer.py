import sip

sip.setapi('QString', 2)  # strange things happen without this. Must import before PyQt imports
# if using ipython: do this on bash before
# export QT_API=pyqt
from qgis.core import *

import os
from TimeManager.layer_settings import LayerSettings
import TimeManager.conf as conf
from TimeManager.timevectorinterpolatedlayer import TimeVectorInterpolatedLayer
from mock import Mock
import tempfile
from test_functionality import TestWithQGISLauncher

TIMESTAMP = "timestamp"
LON = "lon"
LAT = "lat"
ID = "id"

MULTIPLE_POINTS = """
{},{},{},{}
2014-01-01 01:00:10,1,1,1
2014-01-01 01:00:15,2,2,1
2014-01-01 01:00:20,3,3,1
2014-01-01 01:00:10,3,3,2
2014-01-01 01:00:15,2,2,2
2014-01-01 01:00:20,1,1,2
2014-01-01 01:00:10,1,3,3
2014-01-01 01:00:15,2,2,3
2014-01-01 01:00:20,3,1,3
2014-01-01 01:00:10,3,1,4
2014-01-01 01:00:15,2,2,4
2014-01-01 01:00:20,1,3,4
""".format(TIMESTAMP, LON, LAT, ID)

UNIQUE_IDS = 4


class TestInterpolatedLayer(TestWithQGISLauncher):
    def setUp(self):
        super(TestInterpolatedLayer, self).setUp()
        self.file = tempfile.NamedTemporaryFile(mode="r", delete=False)
        with open(self.file.name, 'w') as f:
            f.write(MULTIPLE_POINTS)
        uri = "{}?type=csv&xField={}&yField={}&spatialIndex=no&subsetIndex=no&watchFile=no" \
              "".format(self.file.name, LON, LAT)
        self.layer = QgsVectorLayer(uri, "crossing_points", 'delimitedtext')
        self.assertTrue(self.layer.isValid())
        self.assertTrue(self.layer.featureCount() == 12)


    def tearDown(self):
        super(TestInterpolatedLayer, self).tearDown()
        os.remove(self.file.name)

    def test_layer_always_has_a_feature_per_unique_id(self):
        settings = LayerSettings()
        settings.layer = self.layer
        settings.interpolationMode = conf.LINEAR_POINT_INTERPOLATION
        settings.startTimeAttribute = TIMESTAMP
        settings.endTimeAttribute = TIMESTAMP
        settings.interpolationEnabled = True
        settings.idAttribute = ID
        timeLayer = TimeVectorInterpolatedLayer(settings, iface=Mock())
        self.tlm.registerTimeLayer(timeLayer)
        self.tlm.setTimeFrameType("seconds")
        for i in range(11):
            self.assertTrue(timeLayer.layer.featureCount() + timeLayer.memLayer.featureCount() ==
                            UNIQUE_IDS)
            self.tlm.stepForward()
