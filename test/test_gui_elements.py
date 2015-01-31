import unittest
from mock import Mock, patch
from PyQt4.QtGui import QApplication
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt, QDate, QDateTime, QCoreApplication, QTranslator
import TimeManager.timemanagerguicontrol as guicontrol
import TimeManager.time_util as time_util
import TimeManager.conf as conf
from PyQt4 import QtGui, QtCore
import os


from datetime import datetime, timedelta
from unittest import skip

__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"


class testGuiControl(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.app = QtGui.QApplication([])

    def test_UI_raw_text_and_translations(self):
        gui = self.window.getGui()
        settingsText = gui.dock.pushButtonOptions.text()
        self.assertEqual(settingsText,"Settings")
        for lang,expected_translation in zip(["de","pl"],["Einrichten","Ustawienia"]):
            path = os.path.join("i18n","timemanager_{}.qm".format(lang))
            translator = QTranslator()
            result = translator.load(path)
            translation = translator.translate(gui.dock.objectName(),settingsText)
            self.assertEqual(translation, expected_translation)


    def setUp(self):
        self.window = TestApp()

    def test_options_dialog(self):
        #TODO more testing if the options dialog was created correctly
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
        signal_mock.emit.assert_called_with(pct* (conf.MAX_TIMESLIDER_DEFAULT -
                                                  conf.MIN_TIMESLIDER_DEFAULT))

    def test_datetime_textbox_changed(self):
        gui = self.window.getGui()
        signal_mock = Mock()
        gui.signalCurrentTimeUpdated = signal_mock
        qdate = QDateTime(2010,1,1,1,2)
        gui.currentTimeChangedDateText(qdate)
        # assert that the signal was called with the correct datetime
        signal_mock.emit.assert_called_with(qdate)

    @skip
    def test_add_extents_and_refresh(self):
        #TODO this should be in the controller's tests
        gui = self.window.getGui()
        start = datetime(2010,1,1)
        end = datetime(2010,1,5)
        gui.timeLayerManager.getProjectTimeExtents.return_value = (start, end)
        gui.updateTimeExtents((start,end))
        self.assertEqual(gui.dock.horizontalTimeSlider.maximum() -
        gui.dock.horizontalTimeSlider.minimum(), (end-start).total_seconds())
        # refresh gui with current time
        time_offset = timedelta(hours=1)
        gui.refreshGuiWithCurrentTime(start+time_offset)
        # both the slider and the text box should have changed
        self.assertEqual(time_util.QDateTime_to_datetime(
            gui.dock.dateTimeEditCurrentTime.dateTime()),
                         start+time_offset)
        # the slider has as value the offset between current time and start
        self.assertEqual(gui.dock.horizontalTimeSlider.value(), time_offset.total_seconds())


class TestApp(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        iface = Mock()
        self.gui = guicontrol.TimeManagerGuiControl(iface)

    def getGui(self):
        return self.gui

if __name__=="__main__":
    unittest.main()
