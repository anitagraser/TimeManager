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
import TimeManager.timemanagercontrol as timemanagercontrol
from TimeManager.timemanagercontrol import FRAME_FILENAME_PREFIX
import TimeManager.timevectorlayer as timevectorlayer
import testcfg
import TimeManager.time_util as time_util
import TimeManager.os_util as os_util

from abc import ABCMeta, abstractmethod
import tempfile
import shutil
import unittest
import glob
import math

__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"



PREFIX_PATH=None # replace with path in case of problems

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

    def showQMessagesEnabled(self):
        return False # can't show gui boxes while testing

class TestWithQGISLauncher(unittest.TestCase):
    """
    All test classes who want to have a QGIS application available with the plugin set up should
    inherit this
    """

    @classmethod
    def setUpClass(cls):

        os.environ["QGIS_DEBUG"] = str(-1)

        QtCore.QCoreApplication.setOrganizationName('QGIS')
        QtCore.QCoreApplication.setApplicationName('QGIS2')

        prefix = os_util.get_possible_prefix_path() if PREFIX_PATH is None else PREFIX_PATH
        QgsApplication.setPrefixPath(prefix, True)

        QgsApplication.initQgis()

        if len(QgsProviderRegistry.instance().providerList()) == 0:
                    raise Exception("Could not detect the QGIS prefix path. Maybe you installed "
                                    "QGIS in a non standard location. It is possible to figure "
                                    "this from the Python console within a running QGIS. Type  "
                                    "QgsApplication.showSettings().split(\"\\t\") and look for a " \
                                                                            "filepath after the " \
                                                                            "word Prefix and "
                                                                            "then set it as "
                                                                            "PREFIX_PATH='foo' "
                                                                            "on the top of the "
                                                                            "file "
                                                                            "test_functionality.py")
    def setUp(self):
        iface = Mock()
        self.ctrl = RiggedTimeManagerControl(iface)
        self.ctrl.initGui(test=True)
        self.tlm = self.ctrl.getTimeLayerManager()


class TestForLayersWithOnePointPerSecond(TestWithQGISLauncher):
    """This class tests the functionality of layers for data that contains one point per second
    (our own convention to not have to write similar test code a lot of times). See the
    postgresql and delimited text tests for examples"""

    __metaclass__ = ABCMeta

    @abstractmethod
    def get_start_time(self):
        """Get first timestamp in epoch seconds"""
        pass

    def _test_layer(self,layer, attr, typ, tf, attr2=None):
        if attr2 is None:
            attr2=attr
        timeLayer = timevectorlayer.TimeVectorLayer(layer,attr,attr2,True,
                                                    time_util.DEFAULT_FORMAT,0)
        self.tlm.registerTimeLayer(timeLayer)

        self.assertEquals(timeLayer.getDateType(), typ)
        self.assertEquals(timeLayer.getTimeFormat(), tf)
        expected_datetime = time_util.epoch_to_datetime(self.get_start_time())
        self.assertEquals(self.tlm.getCurrentTimePosition(),expected_datetime)
        self.tlm.setTimeFrameType("seconds")
        self.assertEquals(layer.featureCount(),1)
        self.assertEquals(self.tlm.getCurrentTimePosition(),expected_datetime)
        self.tlm.stepForward()
        self.assertEquals(layer.featureCount(),1)
        expected_datetime = time_util.epoch_to_datetime(self.get_start_time()+1)
        self.assertEquals(self.tlm.getCurrentTimePosition(),expected_datetime)
        self.tlm.setTimeFrameSize(2)
        self.assertEquals(layer.featureCount(),2)


class testTimeManagerWithoutGui(TestWithQGISLauncher):


    def registerTweetsTimeLayer(self, fromAttr="T", toAttr="T"):
        self.layer = QgsVectorLayer(os.path.join(testcfg.TEST_DATA_DIR, 'tweets.shp'), 'tweets', 'ogr')
        self.timeLayer = timevectorlayer.TimeVectorLayer(self.layer,fromAttr,toAttr,True,
                                                    time_util.DEFAULT_FORMAT,0)
        self.assertTrue(not self.timeLayer.hasTimeRestriction())
        self.tlm.registerTimeLayer(self.timeLayer)
        #TODO: Why? Where is it set?
        self.assertTrue(self.timeLayer.hasTimeRestriction())

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
        assert( start_time == self.tlm.getCurrentTimePosition())
        self.tlm.setTimeFrameType("hours")
        self.tlm.stepForward()
        assert( start_time + timedelta(hours=1)==self.tlm.getCurrentTimePosition())
        self.tlm.stepForward()
        assert( start_time + timedelta(hours=2)==self.tlm.getCurrentTimePosition())
        self.tlm.stepBackward()
        assert( start_time + timedelta(hours=1)==self.tlm.getCurrentTimePosition())
        self.tlm.setTimeFrameType("seconds")
        self.tlm.stepForward()
        assert( start_time + timedelta(hours=1,seconds=1)==self.tlm.getCurrentTimePosition())

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
        #TODO this seems to have a bug, ie for the tweets, if time frame = 1day, no export,
        # no warning
        pass

    def test_with_two_layers(self):
        self.registerTweetsTimeLayer("T1765","T1765")
        self.assertEqual(self.tlm.getCurrentTimePosition().year,1765)
        self.registerTweetsTimeLayer("T1165","T1165")
        # the current position doesn't change when adding a new layer
        self.assertEqual(self.tlm.getCurrentTimePosition().year,1765)
        # but the extents do
        start, end = self.tlm.getProjectTimeExtents()
        self.assertEquals(start.year, 1165)
        self.assertEquals(end.year, 1765)
        # now remove the first layer (from 1765)
        self.tlm.removeTimeLayer(self.tlm.getTimeLayerList()[0].getLayerId())
        start, end = self.tlm.getProjectTimeExtents()
        self.assertEquals(start.year, 1165)
        self.assertEquals(end.year, 1165)
        # now remove the last one too
        self.tlm.removeTimeLayer(self.tlm.getTimeLayerList()[0].getLayerId())
        self.assertAlmostEqual(self.tlm.getProjectTimeExtents(), (None,None))


# Ideas for more tests:
# Test save string, settings, restoring, disabling timemanager
#TODO (low prio): Test what happens with impossible events ie:
#test what happens when trying to setCurrentTimePosition to sth wrong
#test layers with nulls



if __name__=="__main__":
    unittest.main()


