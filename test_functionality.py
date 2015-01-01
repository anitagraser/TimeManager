import sip
sip.setapi('QString', 2) # strange things happen without this. Must import before PyQt imports
# if using ipython: do this on bash before
# export QT_API=pyqt
from qgis.core import *
from qgis.gui import *
import os
from mock import Mock
from datetime import datetime, timedelta
from PyQt4 import QtCore, QtGui, QtTest
import timemanagercontrol
from timemanagercontrol import FRAME_FILENAME_PREFIX
import timevectorlayer
import time_util
import os_util

import tempfile
import shutil
import unittest
import glob
import math

__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"


TEST_DATA_DIR="testdata"


class RiggedTimeManagerControl(timemanagercontrol.TimeManagerControl):
    """A subclass of TimeManagerControl which makes testing easier (with the downside of not
    testing some signal behavior)"""

    def saveCurrentMap(self,fileName):
        """We can't export a real screenshot from the test harness, so we just create a blank
        file"""
        print fileName
        open(fileName, 'w').close()

    def playAnimation(self,painter=None):
        """We just continue the animation after playing until it stops via the
        self.animationActivated flag"""
        super(RiggedTimeManagerControl, self).playAnimation()
        if not self.animationActivated:
            return
        else:
            self.playAnimation()


class Foo(unittest.TestCase):

    def setUp(self):
        iface = Mock()
        self.ctrl = RiggedTimeManagerControl(iface)
        self.ctrl.initGui(test=True)
        self.tlm = self.ctrl.getTimeLayerManager()


    @classmethod
    def setUpClass(cls):
        # FIXME discover your prefix by loading the Python console from within QGIS and
        # running QgsApplication.showSettings().split("\t")
        # and looking for Prefix
        QgsApplication.setPrefixPath("/usr", True)

        QgsApplication.initQgis()
        QtCore.QCoreApplication.setOrganizationName('QGIS')
        QtCore.QCoreApplication.setApplicationName('QGIS2')

        if len(QgsProviderRegistry.instance().providerList()) == 0:
            raise RuntimeError('No data providers available.')

    def registerTweetsTimeLayer(self, fromAttr="T", toAttr="T"):
        self.layer = QgsVectorLayer(os.path.join(TEST_DATA_DIR, 'tweets.shp'), 'tweets', 'ogr')
        self.timeLayer = timevectorlayer.TimeVectorLayer(self.layer,fromAttr,toAttr,True,
                                                    time_util.DEFAULT_FORMAT,0)
        self.tlm.registerTimeLayer(self.timeLayer)

    def test_go_back_and_forth_2011(self):
        self.go_back_and_forth("T","T")

    def test_go_back_and_forth_1965(self):
        self.go_back_and_forth("T1965","T1965")

    def test_go_back_and_forth_1765(self):
        self.go_back_and_forth("T1765","T1765")

    def test_go_back_and_forth_1165(self):
        self.go_back_and_forth("T1165","T1165")

    def go_back_and_forth(self,fromAttr, toAttr):

        self.registerTweetsTimeLayer(fromAttr, toAttr)
        # The currentTimePosition should now be the first date in the shapefile
        start_time = time_util.strToDatetime(self.timeLayer.getMinMaxValues()[0])
        assert( start_time ==self.tlm.getCurrentTimePosition())
        self.tlm.setTimeFrameType("hours")
        self.tlm.stepForward()
        assert( start_time + timedelta(hours=1)==self.tlm.getCurrentTimePosition())
        self.tlm.stepForward()
        assert( start_time + timedelta(hours=2)==self.tlm.getCurrentTimePosition())
        self.tlm.stepBackward()
        assert( start_time + timedelta(hours=1)==self.tlm.getCurrentTimePosition())

    def test_export(self):
        self.registerTweetsTimeLayer()
        tmpdir = tempfile.mkdtemp()
        self.tlm.setTimeFrameType("hours")
        start_time = time_util.strToDatetime(self.timeLayer.getMinMaxValues()[0])
        end_time = time_util.strToDatetime(self.timeLayer.getMinMaxValues()[1])
        layer_duration_in_hours = (end_time-start_time).total_seconds() / 3600.0
        self.ctrl.exportVideoAtPath(tmpdir)
        screenshots_generated =  glob.glob(os.path.join(tmpdir, FRAME_FILENAME_PREFIX+"*"))
        self.assertEqual(len(screenshots_generated), math.ceil(layer_duration_in_hours + 1))
        for i in range(int(math.ceil(layer_duration_in_hours + 1))):
            fn = self.ctrl.generate_frame_filename(tmpdir,i, start_time + timedelta(hours=i))
            self.assertIn(fn, screenshots_generated)
        shutil.rmtree(tmpdir)

    def test_export_when_not_starting_from_beginning(self):
        pass

    def test_with_interval_bigger_than_range(self):
        #TODO
        pass


 #   def test_fail(self):
 #       assert(False)

    @classmethod
    def tearDownClass(cls):
        QgsApplication.exitQgis()


if __name__=="__main__":
    unittest.main()


