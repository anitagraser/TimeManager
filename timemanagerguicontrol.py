#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Created on Fri Oct 29 10:13:39 2010

@author: agraser
"""
from __future__ import absolute_import
from builtins import object
import os
import time
from datetime import datetime
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QObject, QDate, QDateTime, pyqtSignal, Qt, QTimer, QCoreApplication
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QShortcut, QAction, QLineEdit, QMessageBox
from qgis.PyQt.QtGui import QKeySequence, QFont, QColor, QIcon, QTextDocument, QAbstractTextDocumentLayout

from utils import qgis_utils as qgs, bcdate_util, time_util

from .vectorlayerdialog import VectorLayerDialog  # , AddLayerDialog
from .rasterlayerdialog import RasterLayerDialog
from .timemanagerprojecthandler import TimeManagerProjectHandler
from utils.tmlogging import warn  # , info

from . import conf
from . import layer_settings

"""
The QTSlider only supports integers as the min and max, therefore the maximum maximum value
is whatever can be stored in an int. Making it a signed int to be sure.
(http://qt-project.org/doc/qt-4.8/qabstractslider.html)
"""
MAX_TIME_LENGTH_SECONDS_SLIDER = 2 ** 31 - 1
"""
according to the docs of QDateTime, the minimum date supported is the first day of
year 100  (http://qt-project.org/doc/qt-4.8/qdatetimeedit.html#minimumDate-prop)
"""
MIN_QDATE = QDate(100, 1, 1)

DOCK_WIDGET_FILE = "dockwidget2.ui"
ADD_VECTOR_LAYER_WIDGET_FILE = "addLayer.ui"
ADD_RASTER_LAYER_WIDGET_FILE = "addRasterLayer.ui"
ARCH_WIDGET_FILE = "arch.ui"
OPTIONS_WIDGET_FILE = "options.ui"
ANIMATION_WIDGET_FILE = "animate.ui"


class TimestampLabelConfig(object):
    """Object that has the settings for rendering timestamp labels. Can be customized via the UI"""
    PLACEMENTS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    DEFAULT_FONT_SIZE = 25
    font = "Arial"  # Font names or family, comma-separated CSS style
    size = DEFAULT_FONT_SIZE  # Relative values between 1-7
    fmt = time_util.DEFAULT_FORMAT  # Pythonic format (same as in the layers)
    placement = 'SE'  # Choose from
    color = 'black'  # Text color as name, rgb(RR,GG,BB), or #XXXXXX
    bgcolor = 'white'  # Background color as name, rgb(RR,GG,BB), or #XXXXXX
    type = "dt"

    def __init__(self, model):
        self.model = model

    def getLabel(self, dt):
        if self.type == "dt":
            return time_util.datetime_to_str(dt, self.fmt)
        if self.type == "epoch":
            return QCoreApplication.translate("TimeManagerGuiControl", "Seconds elapsed: {}").format((dt - datetime(1970, 1, 1, 0, 0)).total_seconds())
        if self.type == "beginning":
            min_dt = self.model.getProjectTimeExtents()[0]
            return QCoreApplication.translate("TimeManagerGuiControl", "Seconds elapsed: {}").format((dt - min_dt).total_seconds())
        else:
            raise Exception("Unsupported type {}".format(self.type))


class TimeManagerGuiControl(QObject):
    """This class controls all plugin-related GUI elements. Emitted signals are defined here."""

    showOptions = pyqtSignal()
    signalExportVideo = pyqtSignal(str, int, bool, bool, bool)
    toggleTime = pyqtSignal()
    toggleArchaeology = pyqtSignal()
    back = pyqtSignal()
    forward = pyqtSignal()
    play = pyqtSignal()
    signalCurrentTimeUpdated = pyqtSignal(QDateTime)
    signalSliderTimeChanged = pyqtSignal(float)
    signalTimeFrameType = pyqtSignal(str)
    signalTimeFrameSize = pyqtSignal(int)
    signalSaveOptions = pyqtSignal()
    signalArchDigitsSpecified = pyqtSignal(int)
    signalArchCancelled = pyqtSignal()

    def __init__(self, iface, model):
        """Initialize the GUI control"""
        QObject.__init__(self)
        self.iface = iface
        self.model = model
        self.optionsDialog = None
        self.path = os.path.dirname(os.path.abspath(__file__))

        # load the form
        self.dock = uic.loadUi(os.path.join(self.path, DOCK_WIDGET_FILE))
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dock)

        self.dock.pushButtonExportVideo.setEnabled(False)  # only enabled if there are managed layers
        self.dock.pushButtonOptions.clicked.connect(self.optionsClicked)
        self.dock.pushButtonExportVideo.clicked.connect(self.exportVideoClicked)
        self.dock.pushButtonToggleTime.clicked.connect(self.toggleTimeClicked)
        self.dock.pushButtonArchaeology.clicked.connect(self.archaeologyClicked)
        self.dock.pushButtonBack.clicked.connect(self.backClicked)
        self.dock.pushButtonForward.clicked.connect(self.forwardClicked)
        self.dock.pushButtonPlay.clicked.connect(self.playClicked)
        self.dock.dateTimeEditCurrentTime.dateTimeChanged.connect(self.currentTimeChangedDateText)
        # self.dock.horizontalTimeSlider.valueChanged.connect(self.currentTimeChangedSlider)

        self.sliderTimer = QTimer(self)
        self.sliderTimer.setInterval(250)
        self.sliderTimer.setSingleShot(True)
        self.sliderTimer.timeout.connect(self.currentTimeChangedSlider)
        self.dock.horizontalTimeSlider.valueChanged.connect(self.startTimer)

        self.dock.comboBoxTimeExtent.currentIndexChanged[str].connect(self.currentTimeFrameTypeChanged)
        self.dock.spinBoxTimeExtent.valueChanged.connect(self.currentTimeFrameSizeChanged)

        # this signal is responsible for rendering the label
        self.iface.mapCanvas().renderComplete.connect(self.renderLabel)

        # create shortcuts
        self.focusSC = QShortcut(QKeySequence("Ctrl+Space"), self.dock)
        self.focusSC.activated.connect(self.dock.horizontalTimeSlider.setFocus)

        # put default values
        self.dock.horizontalTimeSlider.setMinimum(conf.MIN_TIMESLIDER_DEFAULT)
        self.dock.horizontalTimeSlider.setMaximum(conf.MAX_TIMESLIDER_DEFAULT)
        self.dock.dateTimeEditCurrentTime.setMinimumDate(MIN_QDATE)
        self.showLabel = conf.DEFAULT_SHOW_LABEL
        self.exportEmpty = conf.DEFAULT_EXPORT_EMPTY
        self.labelOptions = TimestampLabelConfig(self.model)

        # placeholders for widgets that are added dynamically
        self.bcdateSpinBox = None

        # add to plugins toolbar
        try:
            self.action = QAction(QCoreApplication.translate("TimeManagerGuiControl", "Toggle visibility"), self.iface.mainWindow())
            self.action.triggered.connect(self.toggleDock)
            self.iface.addPluginToMenu(QCoreApplication.translate("TimeManagerGuiControl", "&TimeManager"), self.action)
        except Exception as e:
            pass  # OK for testing

    def startTimer(self):
        self.sliderTimer.start()

    def getLabelFormat(self):
        return self.labelOptions.fmt

    def getLabelFont(self):
        return self.labelOptions.font

    def getLabelSize(self):
        return self.labelOptions.size

    def getLabelColor(self):
        return self.labelOptions.color

    def getLabelBgColor(self):
        return self.labelOptions.bgcolor

    def getLabelPlacement(self):
        return self.labelOptions.placement

    def setLabelFormat(self, fmt):
        if not fmt:
            return
        self.labelOptions.fmt = fmt

    def setLabelFont(self, font):
        if not font:
            return
        self.labelOptions.font = font

    def setLabelSize(self, size):
        if not size:
            return
        self.labelOptions.size = size

    def setLabelColor(self, color):
        if not color:
            return
        self.labelOptions.color = color

    def setLabelBgColor(self, bgcolor):
        if not bgcolor:
            return
        self.labelOptions.bgcolor = bgcolor

    def setLabelPlacement(self, placement):
        if not placement:
            return
        self.labelOptions.placement = placement

    def toggleDock(self):
        self.dock.setVisible(not self.dock.isVisible())

    def getOptionsDialog(self):
        return self.optionsDialog

    def showAnimationOptions(self):
        self.animationDialog = uic.loadUi(os.path.join(self.path, ANIMATION_WIDGET_FILE))

        def selectFile():
            self.animationDialog.lineEdit.setText(QFileDialog.getOpenFileName())

        self.animationDialog.pushButton.clicked.connect(self.selectAnimationFolder)
        self.animationDialog.buttonBox.accepted.connect(self.sendAnimationOptions)
        self.animationDialog.show()

    def selectAnimationFolder(self):
        prev_directory = TimeManagerProjectHandler.plugin_setting(conf.LAST_ANIMATION_PATH_TAG)
        if prev_directory:
            self.animationDialog.lineEdit.setText(QFileDialog.getExistingDirectory(directory=prev_directory))
        else:
            self.animationDialog.lineEdit.setText(QFileDialog.getExistingDirectory())

    def sendAnimationOptions(self):
        path = self.animationDialog.lineEdit.text()
        if path == "":
            self.showAnimationOptions()
        TimeManagerProjectHandler.set_plugin_setting(conf.LAST_ANIMATION_PATH_TAG, path)
        delay_millis = self.animationDialog.spinBoxDelay.value()
        export_gif = self.animationDialog.radioAnimatedGif.isChecked()
        export_video = self.animationDialog.radioVideo.isChecked()
        do_clear = self.animationDialog.clearCheckBox.isChecked()
        self.signalExportVideo.emit(path, delay_millis, export_gif, export_video, do_clear)

    def showLabelOptions(self):
        options = self.labelOptions
        self.dialog = QDialog()

        lo = uic.loadUiType(os.path.join(self.path, 'label_options.ui'))[0]
        self.labelOptionsDialog = lo()
        self.labelOptionsDialog.setupUi(self.dialog)

        self.labelOptionsDialog.fontsize.setValue(options.size)
        self.labelOptionsDialog.time_format.setText(options.fmt)
        self.labelOptionsDialog.font.setCurrentFont(QFont(options.font))
        self.labelOptionsDialog.placement.addItems(TimestampLabelConfig.PLACEMENTS)
        self.labelOptionsDialog.placement.setCurrentIndex(TimestampLabelConfig.PLACEMENTS.index(options.placement))
        self.labelOptionsDialog.text_color.setColor(QColor(options.color))
        self.labelOptionsDialog.bg_color.setColor(QColor(options.bgcolor))
        self.labelOptionsDialog.buttonBox.accepted.connect(self.saveLabelOptions)
        self.dialog.show()

    def saveLabelOptions(self):
        self.labelOptions.font = self.labelOptionsDialog.font.currentFont().family()
        self.labelOptions.size = self.labelOptionsDialog.fontsize.value()
        self.labelOptions.bgcolor = self.labelOptionsDialog.bg_color.color().name()
        self.labelOptions.color = self.labelOptionsDialog.text_color.color().name()
        self.labelOptions.placement = self.labelOptionsDialog.placement.currentText()
        self.labelOptions.fmt = self.labelOptionsDialog.time_format.text()
        if self.labelOptionsDialog.radioButton_dt.isChecked():
            self.labelOptions.type = "dt"
        if self.labelOptionsDialog.radioButton_beginning.isChecked():
            self.labelOptions.type = "beginning"
        if self.labelOptionsDialog.radioButton_epoch.isChecked():
            self.labelOptions.type = "epoch"

    def enableArchaeologyTextBox(self):
        self.dock.dateTimeEditCurrentTime.dateTimeChanged.connect(self.currentTimeChangedDateText)
        if self.bcdateSpinBox is None:
            self.bcdateSpinBox = self.createBCWidget(self.dock)
            self.bcdateSpinBox.editingFinished.connect(self.currentBCYearChanged)
        self.replaceWidget(self.dock.horizontalLayout, self.dock.dateTimeEditCurrentTime, self.bcdateSpinBox, 5)

    def getTimeWidget(self):
        if time_util.is_archaelogical():
            return self.bcdateSpinBox
        else:
            return self.dock.dateTimeEditCurrentTime

    def currentBCYearChanged(self):
        val = self.bcdateSpinBox.text()
        try:
            bcdate_util.BCDate.from_str(val, strict_zeros=False)
            self.signalCurrentTimeUpdated.emit(val)
        except Exception as e:
            warn("Invalid bc date: {}".format(val))  # how to mark as such?
            return

    def disableArchaeologyTextBox(self):
        if self.bcdateSpinBox is None:
            return
        self.replaceWidget(self.dock.horizontalLayout, self.bcdateSpinBox, self.dock.dateTimeEditCurrentTime, 5)

    def createBCWidget(self, mainWidget):
        newWidget = QLineEdit(mainWidget)  # QtGui.QSpinBox(mainWidget)
        # newWidget.setMinimum(-1000000)
        # newWidget.setValue(-1)
        newWidget.setText("0001 BC")
        return newWidget

    def replaceWidget(self, layout, oldWidget, newWidget, idx):
        """
        Replaces oldWidget with newWidget at layout at index idx
        The way it is done, the widget is not destroyed and the connections to it remain
        """

        layout.removeWidget(oldWidget)
        oldWidget.close()  # I wonder if this has any memory leaks? </philosoraptor>
        layout.insertWidget(idx, newWidget)
        newWidget.show()
        layout.update()

    def optionsClicked(self):
        self.showOptions.emit()

    def exportVideoClicked(self):
        self.showAnimationOptions()

    def toggleTimeClicked(self):
        self.toggleTime.emit()

    def archaeologyClicked(self):
        self.toggleArchaeology.emit()

    def showArchOptions(self):
        self.archMenu = uic.loadUi(os.path.join(self.path, ARCH_WIDGET_FILE))
        self.archMenu.buttonBox.accepted.connect(self.saveArchOptions)
        self.archMenu.buttonBox.rejected.connect(self.cancelArch)
        self.archMenu.show()

    def saveArchOptions(self):
        self.signalArchDigitsSpecified.emit(self.archMenu.numDigits.value())

    def cancelArch(self):
        self.signalArchCancelled.emit()

    def backClicked(self):
        self.back.emit()

    def forwardClicked(self):
        self.forward.emit()

    def playClicked(self):
        if self.dock.pushButtonPlay.isChecked():
            self.dock.pushButtonPlay.setIcon(QIcon("TimeManager:images/pause.png"))
        else:
            self.dock.pushButtonPlay.setIcon(QIcon("TimeManager:images/play.png"))
        self.play.emit()

    def currentTimeChangedSlider(self):
        sliderVal = self.dock.horizontalTimeSlider.value()
        try:
            pct = (sliderVal - self.dock.horizontalTimeSlider.minimum()) * 1.0 / (
                self.dock.horizontalTimeSlider.maximum() - self.dock.horizontalTimeSlider.minimum())
        except Exception as e:
            # slider is not properly initialized yet
            return
        if self.model.getActiveDelimitedText() and qgs.getVersion() < conf.MIN_DTEXT_FIXED:
            time.sleep(0.1)  # hack to fix issue in qgis core with delimited text which was fixed in 2.9
        self.signalSliderTimeChanged.emit(pct)

    def currentTimeChangedDateText(self, qdate):
        # info("changed time via text")
        self.signalCurrentTimeUpdated.emit(qdate)

    def currentTimeFrameTypeChanged(self, frameType):
        self.signalTimeFrameType.emit(frameType)

    def currentTimeFrameSizeChanged(self, frameSize):
        if frameSize < 1:  # time frame size = 0  is meaningless
            self.dock.spinBoxTimeExtent.setValue(1)
            return
        self.signalTimeFrameSize.emit(frameSize)

    def unload(self):
        """Unload the plugin"""
        self.iface.removeDockWidget(self.dock)
        self.iface.removePluginMenu("TimeManager", self.action)

    def setWindowTitle(self, title):
        self.dock.setWindowTitle(title)

    def showOptionsDialog(self, layerList, animationFrameLength, playBackwards=False, loopAnimation=False):
        """Show the optionsDialog and populate it with settings from timeLayerManager"""

        # load the form
        self.optionsDialog = uic.loadUi(os.path.join(self.path, OPTIONS_WIDGET_FILE))

        # restore settings from layerList:
        for layer in layerList:
            settings = layer_settings.getSettingsFromLayer(layer)
            layer_settings.addSettingsToRow(settings, self.optionsDialog.tableWidget)
        self.optionsDialog.tableWidget.resizeColumnsToContents()

        # restore animation options
        self.optionsDialog.spinBoxFrameLength.setValue(animationFrameLength)
        self.optionsDialog.checkBoxBackwards.setChecked(playBackwards)
        self.optionsDialog.checkBoxLabel.setChecked(self.showLabel)
        self.optionsDialog.checkBoxDontExportEmpty.setChecked(not self.exportEmpty)
        self.optionsDialog.checkBoxLoop.setChecked(loopAnimation)
        self.optionsDialog.show_label_options_button.clicked.connect(self.showLabelOptions)
        self.optionsDialog.checkBoxLabel.stateChanged.connect(self.showOrHideLabelOptions)

        self.optionsDialog.textBrowser.setHtml(QCoreApplication.translate('TimeManager', """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN" "http://www.w3.org/TR/REC-html40/strict.dtd">
<html>
<head>
    <meta name="qrichtext" content="1"/>

    <style>
    li.mono {
    font-family: Consolas, Courier New, Courier, monospace;
}
    </style>
</head>
<body>

<h1>Time Manager</h1>

<p>Time Manager filters your layers and displays only layers and features that match the specified time frame. Time Manager supports vector layers and raster layers (including WMS-T).</p>

<p>Timestamps have to be in one of the following formats:</p>

<ul>
<li class="mono">%Y-%m-%d %H:%M:%S.%f</li>
<li class="mono">%Y-%m-%d %H:%M:%S</li>
<li class="mono">%Y-%m-%d %H:%M</li>
<li class="mono">%Y-%m-%dT%H:%M:%S</li>
<li class="mono">%Y-%m-%dT%H:%M:%SZ</li>
<li class="mono">%Y-%m-%dT%H:%M</li>
<li class="mono">%Y-%m-%dT%H:%MZ</li>
<li class="mono">%Y-%m-%d</li>
<li class="mono">%Y/%m/%d %H:%M:%S.%f</li>
<li class="mono">%Y/%m/%d %H:%M:%S</li>
<li class="mono">%Y/%m/%d %H:%M</li>
<li class="mono">%Y/%m/%d</li>
<li class="mono">%H:%M:%S</li>
<li class="mono">%H:%M:%S.%f</li>
<li class="mono">%Y.%m.%d %H:%M:%S.%f</li>
<li class="mono">%Y.%m.%d %H:%M:%S</li>
<li class="mono">%Y.%m.%d %H:%M</li>
<li class="mono">%Y.%m.%d</li>
<li class="mono">%Y%m%d%H%M%SED</li>
<li>Integer timestamp in seconds after or before the epoch (1970-1-1)</li>
</ul>


<p>The layer list contains all layers managed by Time Manager.
To add a vector layer, press [Add layer].
To add a raster layer, press [Add raster].
If you want to remove a layer from the list, select it and press [Remove layer].</p>


<p>Below the layer list, you'll find the following <b>animation options</b>:</p>

<p><b>Show frame for x milliseconds</b>...
allows you to adjust for how long a frame will be visible during the animation</p>

<p><b>Play animation backwards</b>...
if checked, the animation will run in reverse direction</p>

<p><b>Display frame start time on map</b>...
if checked, displays the start time of the visible frame in the lower right corner of the map</p>

<h2>Add Layer dialog</h2>

<p>Here, you are asked to select the layer that should be added and specify the columns containing
start and (optionally) end time.</p>

<p>The <b>offset</b> option allows you to further time the appearance of features. If you specify
an offset of -1, the features will appear one second later than they would by default.</p>

<h2>Dock widget</h2>

<p>The dock was designed to attach to the bottom of the QGIS main window. It offers the following tools:</p>

<ul>
<li><img src="images/power_on.png" alt="power"/> ... On/Off switch, allows you to turn Time Manager's functionality on/off with the click of only one button</li>
<li><span class="hidden">[Settings]</span><input type="button" value="Settings"/> ... opens the Settings dialog where you can manage your spatio-temporal layers</li>
<li><span class="hidden">[Export Video]</span><input type="button" value="Export Video"/> ... exports an image series based on current settings (This button is only enabled if there are layers registered in Time Manager "Settings")</li>
<li><b>Time frame start: <span class="hidden">[2000-01-01 00:00:00]</span></b><input type="text" value="2000-01-01 00:00:00"/> ... shows the start time of the currently active frame. Allows you to precisely specify your desired analysis time.</li>
<li><b>Time frame size: </b><input type="text" value="1"/><span class="hidden">[x]</span><select><option value="days">days</option></select> ... allow you to choose the size of the time frame</li>
<li><img src="images/back.png" alt="back"/> ... go to the previous time frame</li>
<li><img src="images/forward.png" alt="forward"/> ... go to the next time frame</li>
<li><b>Slider</b> ... shows the position of current frame relative to the whole dataset and allows you to seamlessly scroll through the dataset</li>
<li><img src="images/play.png" alt="play"/> ... start an automatic animation based on your current settings</li>
</ul>

</body>
</html>"""))

        # show dialog
        self.showOrHideLabelOptions()
        self.optionsDialog.show()

        # create raster and vector dialogs
        self.vectorDialog = VectorLayerDialog(self.iface, os.path.join(self.path, ADD_VECTOR_LAYER_WIDGET_FILE),
                                              self.optionsDialog.tableWidget)
        self.rasterDialog = RasterLayerDialog(self.iface, os.path.join(self.path, ADD_RASTER_LAYER_WIDGET_FILE),
                                              self.optionsDialog.tableWidget)
        # establish connections
        self.optionsDialog.pushButtonAddVector.clicked.connect(self.vectorDialog.show)
        self.optionsDialog.pushButtonAddRaster.clicked.connect(self.rasterDialog.show)
        self.optionsDialog.pushButtonRemove.clicked.connect(self.removeLayer)
        self.optionsDialog.buttonBox.accepted.connect(self.saveOptions)
        # self.optionsDialog.buttonBox.helpRequested.connect(self.showHelp)

    def showOrHideLabelOptions(self):
        self.optionsDialog.show_label_options_button.setEnabled(
            self.optionsDialog.checkBoxLabel.isChecked())

    def saveOptions(self):
        """Save the options from optionsDialog to timeLayerManager"""
        self.signalSaveOptions.emit()

    def removeLayer(self):
        """Remove currently selected layer (= row) from options"""
        currentRow = self.optionsDialog.tableWidget.currentRow()
        try:
            layerName = self.optionsDialog.tableWidget.item(currentRow, 0).text()
        except AttributeError:  # if no row is selected
            return
        if QMessageBox.question(self.optionsDialog,
                                QCoreApplication.translate("TimeManagerGuiControl", "Remove Layer"),
                                QCoreApplication.translate("TimeManagerGuiControl", "Do you really want to remove layer {}?").format(layerName),
                                QMessageBox.Ok, QMessageBox.Cancel) == QMessageBox.Ok:
            self.optionsDialog.tableWidget.removeRow(self.optionsDialog.tableWidget.currentRow())

    def disableAnimationExport(self):
        """Disable the animation export button"""
        self.dock.pushButtonExportVideo.setEnabled(False)

    def enableAnimationExport(self):
        """Enable animation export button"""
        self.dock.pushButtonExportVideo.setEnabled(True)

    def refreshMapCanvas(self, sender=None):
        """Refresh the map canvas"""
        # QMessageBox.information(self.iface.mainWindow(),'Test Output','Refresh!\n'+str(sender))
        self.iface.mapCanvas().refresh()

    def setTimeFrameSize(self, frameSize):
        """Set spinBoxTimeExtent to given frameSize"""
        self.dock.spinBoxTimeExtent.setValue(frameSize)

    def setTimeFrameType(self, frameType):
        """Set comboBoxTimeExtent to given frameType"""
        i = self.dock.comboBoxTimeExtent.findText(frameType)
        self.dock.comboBoxTimeExtent.setCurrentIndex(i)

    def setActive(self, isActive):
        """Toggle pushButtonToggleTime"""
        self.dock.pushButtonToggleTime.setChecked(isActive)

    def setArchaeologyPressed(self, isActive):
        """Toggle pushButtonArchaeology"""
        self.dock.pushButtonArchaeology.setChecked(isActive)

    def addActionShowSettings(self, action):
        """Add action to pushButttonOptions"""
        self.dock.pushButtonOptions.addAction(action)

    def turnPlayButtonOff(self):
        """Turn pushButtonPlay off"""
        if self.dock.pushButtonPlay.isChecked():
            self.dock.pushButtonPlay.toggle()
            self.dock.pushButtonPlay.setIcon(QIcon("TimeManager:images/play.png"))

    def renderLabel(self, painter):
        """Render the current timestamp on the map canvas"""
        if not self.showLabel or not self.model.hasLayers() or not self.dock.pushButtonToggleTime.isChecked():
            return

        dt = self.model.getCurrentTimePosition()
        if dt is None:
            return

        labelString = self.labelOptions.getLabel(dt)

        # Determine placement of label given cardinal directions
        flags = 0
        for direction, flag in ('N', Qt.AlignTop), ('S', Qt.AlignBottom), ('E', Qt.AlignRight), ('W', Qt.AlignLeft):
            if direction in self.labelOptions.placement:
                flags |= flag

        # Get canvas dimensions
        width = painter.device().width()
        height = painter.device().height()

        painter.setRenderHint(painter.Antialiasing, True)
        txt = QTextDocument()
        html = """<span style="background-color:%s; padding: 5px; font-size: %spx;">
                    <font face="%s" color="%s">%s</font>
                  </span> """\
               % (self.labelOptions.bgcolor, self.labelOptions.size, self.labelOptions.font,
                  self.labelOptions.color, labelString)
        txt.setHtml(html)
        layout = txt.documentLayout()
        size = layout.documentSize()

        if flags & Qt.AlignRight:
            x = width - 5 - size.width()
        elif flags & Qt.AlignLeft:
            x = 5
        else:
            x = width / 2 - size.width() / 2

        if flags & Qt.AlignBottom:
            y = height - 5 - size.height()
        elif flags & Qt.AlignTop:
            y = 5
        else:
            y = height / 2 - size.height() / 2

        painter.translate(x, y)
        layout.draw(painter, QAbstractTextDocumentLayout.PaintContext())
        painter.translate(-x, -y)  # translate back

    def repaintRasters(self):
        rasters = self.model.getActiveRasters()
        list([x.layer.triggerRepaint() for x in rasters])

    def repaintVectors(self):
        list([x.layer.triggerRepaint() for x in self.model.getActiveVectors()])

    def repaintJoined(self):
        layerIdsToRefresh = qgs.getAllJoinedLayers(set([x.layer.id() for x in self.model.getActiveVectors()]))
        # info("to refresh {}".format(layerIdsToRefresh))
        layersToRefresh = [qgs.getLayerFromId(x) for x in layerIdsToRefresh]
        list([x.triggerRepaint() for x in layersToRefresh])
