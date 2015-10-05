import unittest
from qgis.core import QgsVectorLayer, QgsRasterLayer
from PyQt4 import QtGui, QtCore
import os
from datetime import datetime, timedelta
from unittest import skip

from mock import Mock, patch
from PyQt4.QtGui import QApplication
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt, QDate, QDateTime, QCoreApplication, QTranslator

import TimeManager.timemanagerguicontrol as guicontrol
import TimeManager.rasterlayerdialog as rl
import TimeManager.vectorlayerdialog as vl
import TimeManager.time_util as time_util
import TimeManager.conf as conf
import testcfg


__author__ = "Karolina Alexiou"
__email__ = "karolina.alexiou@teralytics.ch"


class testGuiControl(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.app = QtGui.QApplication([])

    @classmethod
    def tearDownClass(self):
        self.app.quit()

    def test_UI_raw_text_and_translations(self):
        gui = self.window.getGui()
        settingsText = gui.dock.pushButtonOptions.text()
        self.assertEqual(settingsText, "Settings")
        for lang, expected_translation in zip(["de", "pl"], ["Einrichten", "Ustawienia"]):
            path = os.path.join("i18n", "timemanager_{}.qm".format(lang))
            translator = QTranslator()
            result = translator.load(path)
            translation = translator.translate(gui.dock.objectName(), settingsText)
            self.assertEqual(translation, expected_translation)


    def setUp(self):
        self.window = TestApp()
        self.path = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
        self.vector = vl.VectorLayerDialog(Mock(), os.path.join(self.path,
                                                                guicontrol.ADD_VECTOR_LAYER_WIDGET_FILE),
                                           Mock())
        self.raster = rl.RasterLayerDialog(Mock(), os.path.join(self.path,
                                                                guicontrol.ADD_RASTER_LAYER_WIDGET_FILE),
                                           Mock())
        self.vectorLayer = QgsVectorLayer(os.path.join(testcfg.TEST_DATA_DIR, 'tweets.shp'),
                                          'tweets', 'ogr')
        self.rasterLayer = QgsRasterLayer(os.path.join(testcfg.TEST_DATA_DIR, 'clouds.nc'))

    def test_vector_dialog_populate(self):
        self.assertIsNotNone(self.vector)
        self.assertEqual(self.vector.layer_count(), 0)
        self.vector.populateFromLayers([("greatlayer4242", self.vectorLayer)])
        self.assertEqual(self.vector.layer_count(), 1)

    def test_vector_dialog_idbox(self):
        self.vector.maybeEnableIDBox(conf.NO_INTERPOLATION)
        self.assertFalse(self.vector.dialog.comboBoxID.isEnabled())
        self.vector.maybeEnableIDBox(conf.LINEAR_POINT_INTERPOLATION)
        self.assertTrue(self.vector.dialog.comboBoxID.isEnabled())

    def test_raster_dialog_populate(self):
        self.assertIsNotNone(self.raster)
        self.assertEqual(self.raster.layer_count(), 0)
        self.raster.populateFromLayers([("lookatalltheseclouds4242", self.rasterLayer)])
        self.assertEqual(self.raster.layer_count(), 1)

    def test_options_dialog(self):
        # TODO more testing if the options dialog was created correctly
        gui = self.window.getGui()
        guicontrol.QgsMapLayerRegistry = Mock()
        gui.showOptionsDialog([], 100)
        self.assertEquals(gui.optionsDialog.spinBoxFrameLength.value(), 100)

    def test_slider_changed(self):
        gui = self.window.getGui()
        signal_mock = Mock()
        gui.signalSliderTimeChanged = signal_mock
        pct = 0.1
        gui.currentTimeChangedSlider(pct)
        # assert that the signal was called with the correct datetime
        signal_mock.emit.assert_called_with(pct * (conf.MAX_TIMESLIDER_DEFAULT -
                                                   conf.MIN_TIMESLIDER_DEFAULT))

    def test_datetime_textbox_changed(self):
        gui = self.window.getGui()
        signal_mock = Mock()
        gui.signalCurrentTimeUpdated = signal_mock
        qdate = QDateTime(2010, 1, 1, 1, 2)
        gui.currentTimeChangedDateText(qdate)
        # assert that the signal was called with the correct datetime
        signal_mock.emit.assert_called_with(qdate)

    @skip
    def test_add_extents_and_refresh(self):
        # TODO this should be in the controller's tests
        gui = self.window.getGui()
        start = datetime(2010, 1, 1)
        end = datetime(2010, 1, 5)
        gui.timeLayerManager.getProjectTimeExtents.return_value = (start, end)
        gui.updateTimeExtents((start, end))
        self.assertEqual(gui.dock.horizontalTimeSlider.maximum() -
                         gui.dock.horizontalTimeSlider.minimum(), (end - start).total_seconds())
        # refresh gui with current time
        time_offset = timedelta(hours=1)
        gui.refreshGuiWithCurrentTime(start + time_offset)
        # both the slider and the text box should have changed
        self.assertEqual(time_util.QDateTime_to_datetime(
            gui.dock.dateTimeEditCurrentTime.dateTime()),
                         start + time_offset)
        # the slider has as value the offset between current time and start
        self.assertEqual(gui.dock.horizontalTimeSlider.value(), time_offset.total_seconds())


class TestApp(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        iface = Mock()
        model = Mock()
        self.gui = guicontrol.TimeManagerGuiControl(iface, model)

    def getGui(self):
        return self.gui


if __name__ == "__main__":
    unittest.main()
