import sys
import unittest
from mock import Mock, patch
from PyQt4.QtGui import QApplication
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt, QDate, QDateTime
import timemanagerguicontrol as guicontrol
import time_util
from PyQt4 import QtGui


from datetime import datetime, timedelta

__author__="Karolina Alexiou"
__email__="karolina.alexiou@teralytics.ch"


class testGuiControl(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        self.app = QtGui.QApplication([])

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
        start = datetime(2010,1,1)
        end = datetime(2010,1,5)
        gui.updateTimeExtents((start, end))
        td = timedelta(seconds=54)
        signal_mock = Mock()
        gui.signalCurrentTimeUpdated = signal_mock
        gui.currentTimeChangedSlider(td.total_seconds())
        # assert that the signal was called with the correct datetime
        signal_mock.emit.assert_called_with(start+td)

    def test_datetime_textbox_changed(self):
        gui = self.window.getGui()
        start = datetime(2010,1,1)
        end = datetime(2010,1,5)
        gui.updateTimeExtents((start, end))
        signal_mock = Mock()
        gui.signalCurrentTimeUpdated = signal_mock
        gui.currentTimeChangedDateText(QDateTime(2010,1,1,1,2))
        # assert that the signal was called with the correct datetime
        signal_mock.emit.assert_called_with(start+timedelta(hours=1, minutes=2))

    def test_add_extents_and_refresh(self):
        gui = self.window.getGui()
        start = datetime(2010,1,1)
        end = datetime(2010,1,5)
        gui.updateTimeExtents((start, end))
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
        tlm = Mock()
        self.gui = guicontrol.TimeManagerGuiControl(iface,tlm)

    def getGui(self):
        return self.gui

if __name__=="__main__":
    unittest.main()
