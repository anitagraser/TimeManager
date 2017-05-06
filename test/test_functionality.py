import sip

sip.setapi('QString', 2)  # strange things happen without this. Must import before PyQt imports
# if using ipython: do this on bash before
# export QT_API=pyqt
from qgis.core import *
from qgis.gui import *
import sys

sys.path.insert(0, '../..')
import os
from mock import Mock
from datetime import datetime, timedelta
from PyQt4 import QtCore, QtGui, QtTest
import TimeManager.timemanagercontrol as timemanagercontrol
from TimeManager.timemanagercontrol import FRAME_FILENAME_PREFIX
import TimeManager.timevectorlayer as timevectorlayer
from TimeManager.timelayermanager import TimeLayerManager
import testcfg
import TimeManager.time_util as time_util
import TimeManager.bcdate_util as bcdate_util
import TimeManager.os_util as os_util
import TimeManager.layer_settings as ls

from abc import ABCMeta, abstractmethod
import tempfile
import shutil
import unittest
from unittest import skip
import glob
import math

__author__ = "Karolina Alexiou"
__email__ = "karolina.alexiou@teralytics.ch"

PREFIX_PATH = None  # replace with path in case of problems


class RiggedTimeManagerControl(timemanagercontrol.TimeManagerControl):
    """A subclass of TimeManagerControl which makes testing easier (with the downside of not
    testing some signal behavior)"""

    def saveCurrentMap(self, fileName):
        """We can't export a real screenshot from the test harness, so we just create a blank
        file"""
        open(fileName, 'w').close()

    def load(self):
        """ Load the plugin"""
        # order matters
        self.timeLayerManager = TimeLayerManager(self.iface)
        self.guiControl = Mock()
        self.initViewConnections(test=True)
        self.initModelConnections()
        self.initQGISConnections()
        self.restoreDefaults()

    def playAnimation(self, painter=None):
        """We just continue the animation after playing until it stops via the
        self.animationActivated flag"""
        super(RiggedTimeManagerControl, self).playAnimation()
        if not self.animationActivated:
            return
        else:
            self.playAnimation()

    def showQMessagesEnabled(self):
        return False  # can't show gui boxes while testing


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

        # OLD (that is
        # prefix = os_util.get_possible_prefix_path() if PREFIX_PATH is None else PREFIX_PATH
        # QgsApplication.setPrefixPath(prefix, True)
        # QgsApplication.initQgis()
        #
        # if len(QgsProviderRegistry.instance().providerList()) == 0:
        #     raise Exception("Could not detect the QGIS prefix path. Maybe you installed "
        #                     "QGIS in a non standard location. It is possible to figure "
        #                     "this from the Python console within a running QGIS. Type  "
        #                     "QgsApplication.showSettings().split(\"\\t\") and look for a " \
        #                     "filepath after the " \
        #                     "word Prefix and "
        #                     "then set it as "
        #                     "PREFIX_PATH='foo' "
        #                     "on the top of the "
        #                     "file "
        #                     "test_functionality.py")

    def setUp(self):

        prefix = os_util.get_possible_prefix_path() if PREFIX_PATH is None else PREFIX_PATH

        self.qgs = QgsApplication(sys.argv, False)
        self.qgs.setPrefixPath(prefix, True)
        self.qgs.initQgis()

        self.iface = Mock()
        self.ctrl = RiggedTimeManagerControl(self.iface)
        self.ctrl.load()
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

    def _test_layer(self, layer, attr, typ, tf, attr2=None):
        if attr2 is None:
            attr2 = attr
        settings = ls.LayerSettings()
        settings.layer = layer
        settings.startTimeAttribute = attr
        settings.endTimeAttribute = attr2
        iface = Mock()
        timeLayer = timevectorlayer.TimeVectorLayer(settings, iface)
        # TODO
        # self.assertEqual(settings, ls.getSettingsFromLayer(timeLayer))
        self.tlm.registerTimeLayer(timeLayer)
        self.assertEquals(len(self.tlm.getActiveVectors()), 1)
        self.assertEquals(len(self.tlm.getActiveRasters()), 0)
        self.assertEquals(timeLayer.getDateType(), typ)
        if tf is not None:
            self.assertEquals(timeLayer.getTimeFormat(), tf)
        expected_datetime = time_util.epoch_to_datetime(self.get_start_time())
        self.assertEquals(self.tlm.getCurrentTimePosition(), expected_datetime)
        self.tlm.setTimeFrameType("seconds")
        self.assertEquals(layer.featureCount(), 1)
        self.assertEquals(self.tlm.getCurrentTimePosition(), expected_datetime)
        self.tlm.stepForward()
        self.assertEquals(layer.featureCount(), 1)
        expected_datetime = time_util.epoch_to_datetime(self.get_start_time() + 1)
        self.assertEquals(self.tlm.getCurrentTimePosition(), expected_datetime)
        self.tlm.setTimeFrameSize(2)
        self.assertEquals(layer.featureCount(), 2)


class testTimeManagerWithoutGui(TestWithQGISLauncher):
    def registerTweetsTimeLayer(self, fromAttr="T", toAttr="T"):
        self.layer = QgsVectorLayer(os.path.join(testcfg.TEST_DATA_DIR, 'tweets.shp'), 'tweets',
                                    'ogr')
        settings = ls.LayerSettings()
        settings.layer = self.layer
        settings.startTimeAttribute = fromAttr
        settings.endTimeAttribute = toAttr
        self.timeLayer = timevectorlayer.TimeVectorLayer(settings, iface=Mock())
        self.assertTrue(not self.timeLayer.hasTimeRestriction())
        self.tlm.registerTimeLayer(self.timeLayer)
        # refresh will have set the time restriction
        self.assertTrue(self.timeLayer.hasTimeRestriction())

    def test_go_back_and_forth_2011(self):
        self.go_back_and_forth("T", "T")

    def test_go_back_and_forth_1965(self):
        self.go_back_and_forth("T1965", "T1965")

    def test_go_back_and_forth_1765(self):
        self.go_back_and_forth("T1765", "T1765")

    def test_go_back_and_forth_1165(self):
        self.go_back_and_forth("T1165", "T1165")


    def test_disable_and_reenable(self):
        self.go_back_and_forth("T1765", "T1765")
        initial_time = self.tlm.getCurrentTimePosition()
        feature_subset_size = self.layer.featureCount()
        self.ctrl.toggleTimeManagement()
        # time management is disabled
        self.assertTrue(self.layer.featureCount() > feature_subset_size)
        self.tlm.stepForward()
        self.assertEquals(self.tlm.getCurrentTimePosition(), initial_time)
        self.ctrl.toggleTimeManagement()
        # time management is enabled again
        self.assertEquals(self.ctrl.animationActivated, False)
        self.ctrl.toggleAnimation()
        self.assertEquals(self.ctrl.animationActivated, True)
        self.assertEquals(self.tlm.getCurrentTimePosition(), initial_time)
        self.assertEquals(self.layer.featureCount(), feature_subset_size)
        self.tlm.stepForward()
        self.assertTrue(self.tlm.getCurrentTimePosition() > initial_time)

    def test_write_and_read_settings(self):
        self.go_back_and_forth("T1165", "T1165")
        initial_time = self.tlm.getCurrentTimePosition()
        self.ctrl.setLoopAnimation(True)
        test_file = os.path.join(testcfg.TEST_DATA_DIR, "sample_project.qgs")
        if os.path.exists(test_file):
            os.remove(test_file)
        label_fmt = "Time flies  %Y-%m-%d"
        self.ctrl.guiControl.getLabelFormat.return_value = label_fmt
        self.ctrl.guiControl.getLabelFont.return_value = "Courier"
        self.ctrl.guiControl.getLabelSize.return_value = 10
        self.ctrl.guiControl.getLabelColor.return_value = "#000000"
        self.ctrl.guiControl.getLabelBgColor.return_value = "#ffffff"
        self.ctrl.guiControl.getLabelPlacement.return_value = "SE"        
        self.ctrl.writeSettings()
        QgsProject.instance().write(QtCore.QFileInfo(test_file))

        # change settings
        self.tlm.stepForward()
        self.assertEqual(self.tlm.getTimeFrameType(), "seconds")
        self.assertEquals(self.tlm.getCurrentTimePosition(), initial_time + timedelta(seconds=
                                                                                      self.tlm.getTimeFrameSize()))
        self.tlm.setTimeFrameType('minutes')
        self.ctrl.setLoopAnimation(False)
        # restore previous settings
        QgsProject.instance().read(QtCore.QFileInfo(test_file))
        self.ctrl.readSettings()
        # check that the settings were restored properly
        self.assertEquals(self.tlm.isEnabled(), True)
        self.assertEquals(self.tlm.getCurrentTimePosition(), initial_time)
        self.assertEquals(self.ctrl.loopAnimation, True)
        self.ctrl.guiControl.setTimeFrameSize.assert_called_with(1)
        self.ctrl.guiControl.setLabelFormat.assert_called_with(label_fmt)


    @skip
    def test_write_and_read_settings_when_disabled(self):
        self.go_back_and_forth("T1165", "T1165")
        self.assertTrue(self.tlm.isEnabled() == True)
        self.ctrl.toggleTimeManagement()
        self.assertTrue(self.tlm.isEnabled() == False)
        test_file = os.path.join(testcfg.TEST_DATA_DIR, "sample_project_disabled.qgs")
        if os.path.exists(test_file):
            os.remove(test_file)
        self.ctrl.writeSettings(None)
        QgsProject.instance().write(QtCore.QFileInfo(test_file))
        # restore previous settings
        QgsProject.instance().read(QtCore.QFileInfo(test_file))
        self.ctrl.readSettings()
        # check that the settings were restored properly
        self.assertEquals(self.tlm.isEnabled(), False)


    def go_back_and_forth(self, fromAttr, toAttr):

        self.registerTweetsTimeLayer(fromAttr, toAttr)
        # The currentTimePosition should now be the first date in the shapefile
        start_time = time_util.str_to_datetime(self.timeLayer.getMinMaxValues()[0])
        assert ( start_time == self.tlm.getCurrentTimePosition())
        self.tlm.setTimeFrameType("hours")
        self.tlm.stepForward()
        assert ( start_time + timedelta(hours=1) == self.tlm.getCurrentTimePosition())
        self.tlm.stepForward()
        assert ( start_time + timedelta(hours=2) == self.tlm.getCurrentTimePosition())
        self.tlm.stepBackward()
        assert ( start_time + timedelta(hours=1) == self.tlm.getCurrentTimePosition())
        self.tlm.setTimeFrameType("seconds")
        self.tlm.stepForward()
        assert ( start_time + timedelta(hours=1, seconds=1) == self.tlm.getCurrentTimePosition())


    def test_export_with_empty(self):
        """The tweets layer doesn't have tweets for every second. Test that when exporting part
        of it with exportEmpty = False, not all possible frames are exported"""
        self.registerTweetsTimeLayer()
        tmpdir = tempfile.mkdtemp()
        self.tlm.setTimeFrameType("seconds")
        self.ctrl.exportEmpty = lambda: False
        assert (self.ctrl.exportEmpty() == False)
        end_time = time_util.str_to_datetime(self.timeLayer.getMinMaxValues()[1])
        start_time = end_time - timedelta(seconds=100)
        self.tlm.setCurrentTimePosition(start_time)
        layer_duration_in_seconds = (end_time - start_time).total_seconds()
        self.ctrl.exportVideo(tmpdir, 100, False)
        screenshots_generated = glob.glob(os.path.join(tmpdir, FRAME_FILENAME_PREFIX + "*"))
        self.assertTrue(len(screenshots_generated) < math.ceil(layer_duration_in_seconds + 1))
        shutil.rmtree(tmpdir)

    def test_export(self):
        self.registerTweetsTimeLayer()
        tmpdir = tempfile.mkdtemp()
        self.tlm.setTimeFrameType("hours")
        start_time = time_util.str_to_datetime(self.timeLayer.getMinMaxValues()[0])
        end_time = time_util.str_to_datetime(self.timeLayer.getMinMaxValues()[1])
        layer_duration_in_hours = (end_time - start_time).total_seconds() / 3600.0
        self.ctrl.exportVideo(tmpdir, 100, False)
        screenshots_generated = glob.glob(os.path.join(tmpdir, FRAME_FILENAME_PREFIX + "*"))
        self.assertEqual(len(screenshots_generated), math.ceil(layer_duration_in_hours + 1))
        for i in range(int(math.ceil(layer_duration_in_hours + 1))):
            fn = self.ctrl.generate_frame_filename(tmpdir, i, start_time + timedelta(hours=i))
            self.assertIn(fn, screenshots_generated)
        shutil.rmtree(tmpdir)

    def test_export_when_not_starting_from_beginning(self):
        pass

    def test_with_interval_bigger_than_range(self):
        # TODO this seems to have a bug, ie for the tweets, if time frame = 1day, no export,
        # no warning
        pass

    def test_with_two_layers(self):
        self.registerTweetsTimeLayer("T", "T")  # year 2011
        laterYear = 2011
        earlierYear = 1965
        self.assertEqual(self.tlm.getCurrentTimePosition().year, laterYear)
        self.registerTweetsTimeLayer("T1965", "T1965")
        # the current position doesn't change when adding a new layer
        self.assertEqual(self.tlm.getCurrentTimePosition().year, laterYear)
        # but the extents do
        start, end = self.tlm.getProjectTimeExtents()
        self.assertEquals(start.year, earlierYear)
        self.assertEquals(end.year, laterYear)
        # now remove the first layer (from 1765)
        self.tlm.removeTimeLayer(self.tlm.getTimeLayerList()[0].getLayerId())
        start, end = self.tlm.getProjectTimeExtents()
        self.assertEquals(start.year, earlierYear)
        self.assertEquals(end.year, earlierYear)
        # now remove the last one too
        self.tlm.removeTimeLayer(self.tlm.getTimeLayerList()[0].getLayerId())
        self.assertAlmostEqual(self.tlm.getProjectTimeExtents(), (None, None))

    def getArchaelogicalLayer(self):
        testfile_dir = testcfg.TEST_DATA_DIR
        fn = os.path.join(testfile_dir, "archaelogical2.txt")
        uri = "{}?type=csv&xField={}&yField={}&spatialIndex=no&subsetIndex=no&watchFile=no" \
              "".format(fn, "lon", "lat")
        layer = QgsVectorLayer(uri, "ancient_points", 'delimitedtext')
        return layer

    def test_archaeological_range_queries(self):
        try:
            layer = self.getArchaelogicalLayer()
            self.ctrl.setArchaeology(1)
            assert (time_util.is_archaelogical())
            settings = ls.LayerSettings()
            settings.layer = layer
            settings.startTimeAttribute = "year"
            settings.endTimeAttribute = "endyear"
            iface = Mock()
            timeLayer = timevectorlayer.TimeVectorLayer(settings, iface)
            self.tlm.registerTimeLayer(timeLayer)
            self.assertEquals(len(self.tlm.getActiveVectors()), 1)
            self.assertEquals(timeLayer.getDateType(),
                              time_util.DateTypes.DatesAsStringsArchaelogical)
            self.assertEquals(timeLayer.getTimeFormat(), bcdate_util.BC_FORMAT)
            self.tlm.setTimeFrameType("years")
            self.tlm.setCurrentTimePosition(bcdate_util.BCDate(-452))
            self.assertEquals(layer.featureCount(), 0)
            self.tlm.setCurrentTimePosition(bcdate_util.BCDate(-400))
            self.assertEquals(layer.featureCount(), 1)
            self.tlm.setCurrentTimePosition(bcdate_util.BCDate(-352))
            self.assertEquals(layer.featureCount(), 2)
            self.tlm.setCurrentTimePosition(bcdate_util.BCDate(-9))
            self.assertEquals(layer.featureCount(), 2)
            self.tlm.setCurrentTimePosition(bcdate_util.BCDate(180))
            self.assertEquals(layer.featureCount(), 0)
            self.tlm.setCurrentTimePosition(bcdate_util.BCDate(1))
            self.assertEquals(layer.featureCount(), 2)
            self.tlm.setCurrentTimePosition(bcdate_util.BCDate(333))
            self.assertEquals(layer.featureCount(), 1)
            self.tlm.setCurrentTimePosition(bcdate_util.BCDate(-450))
            self.tlm.setTimeFrameSize(500)
            self.assertEquals(layer.featureCount(), 4)
            self.tlm.setTimeFrameSize(1000)
            self.assertEquals(layer.featureCount(), 5)

            # expected_datetime = time_util.epoch_to_datetime(self.get_start_time())
            #self.assertEquals(self.tlm.getCurrentTimePosition(),expected_datetime)
            #self.assertEquals(layer.featureCount(),1)
            #self.tlm.stepForward()
            #self.tlm.setTimeFrameSize(2)
            self.tlm.clearTimeLayerList()
            self.ctrl.setArchaeology(0)
        except Exception, e:
            self.tlm.clearTimeLayerList()
            self.ctrl.setArchaeology(0)
            raise e


