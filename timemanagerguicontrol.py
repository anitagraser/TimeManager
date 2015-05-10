# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 10:13:39 2010

@author: agraser
"""
import os
from string import replace

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from PyQt4 import QtGui as QtGui

from timevectorlayer import *
from timerasterlayer import *
from time_util import QDateTime_to_datetime, \
    datetime_to_str, DEFAULT_FORMAT
import conf
import qgis_utils as qgs
from ui import label_options
import layer_settings as ls
from vectorlayerdialog import VectorLayerDialog, AddLayerDialog
from rasterlayerdialog import RasterLayerDialog

# The QTSlider only supports integers as the min and max, therefore the maximum maximum value
# is whatever can be stored in an int. Making it a signed int to be sure.
# (http://qt-project.org/doc/qt-4.8/qabstractslider.html)
MAX_TIME_LENGTH_SECONDS_SLIDER = 2**31-1
# according to the docs of QDateTime, the minimum date supported is the first day of
# year 100  (http://qt-project.org/doc/qt-4.8/qdatetimeedit.html#minimumDate-prop)
MIN_QDATE = QDate(100, 1, 1)

DOCK_WIDGET_FILE = "dockwidget2.ui"
ADD_VECTOR_LAYER_WIDGET_FILE ="addLayer.ui"
ADD_RASTER_LAYER_WIDGET_FILE ="addRasterLayer.ui"


class TimestampLabelConfig(object):
    """Object that has the settings for rendering timestamp labels. Can be customized via the UI"""
    PLACEMENTS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    DEFAULT_FONT_SIZE = 4
    font = "Arial"      # Font names or family, comma-separated CSS style
    size = DEFAULT_FONT_SIZE # Relative values between 1-7
    fmt = DEFAULT_FORMAT # Pythonic format (same as in the layers)
    placement = 'SE'    # Choose from
    color = 'black'     # Text color as name, rgb(RR,GG,BB), or #XXXXXX
    bgcolor = 'white'   # Background color as name, rgb(RR,GG,BB), or #XXXXXX

class TimeManagerGuiControl(QObject):
    """This class controls all plugin-related GUI elements. Emitted signals are defined here."""
    
    showOptions = pyqtSignal()
    exportVideo = pyqtSignal()
    toggleTime = pyqtSignal()
    back = pyqtSignal()
    forward = pyqtSignal()
    play = pyqtSignal()
    signalCurrentTimeUpdated = pyqtSignal(object)
    signalSliderTimeChanged = pyqtSignal(float)
    signalTimeFrameType = pyqtSignal(str)
    signalTimeFrameSize = pyqtSignal(int)
    signalSaveOptions = pyqtSignal()
    
    def __init__ (self,iface, model):
        """initialize the GUI control"""
        QObject.__init__(self)
        self.iface = iface
        self.model = model
        self.optionsDialog = None
        self.path = os.path.dirname( os.path.abspath( __file__ ) )
        
        # load the form
        self.dock = uic.loadUi( os.path.join(self.path, DOCK_WIDGET_FILE ) )
        self.iface.addDockWidget( Qt.BottomDockWidgetArea, self.dock )

        self.dock.pushButtonExportVideo.setEnabled(False) # only enabled if there are managed layers
        self.dock.pushButtonOptions.clicked.connect(self.optionsClicked) 
        self.dock.pushButtonExportVideo.clicked.connect(self.exportVideoClicked)
        self.dock.pushButtonToggleTime.clicked.connect(self.toggleTimeClicked)
        self.dock.pushButtonBack.clicked.connect(self.backClicked)
        self.dock.pushButtonForward.clicked.connect(self.forwardClicked)
        self.dock.pushButtonPlay.clicked.connect(self.playClicked)   
        self.dock.dateTimeEditCurrentTime.dateTimeChanged.connect(self.currentTimeChangedDateText)
        self.dock.horizontalTimeSlider.valueChanged.connect(self.currentTimeChangedSlider)
        self.dock.comboBoxTimeExtent.currentIndexChanged[str].connect(self.currentTimeFrameTypeChanged)
        self.dock.spinBoxTimeExtent.valueChanged.connect(self.currentTimeFrameSizeChanged)

        # this signal is responsible for rendering the label
        self.iface.mapCanvas().renderComplete.connect(self.renderLabel)

        # create shortcuts
        self.focusSC = QShortcut(QKeySequence("Ctrl+Space"), self.dock)
        self.connect(self.focusSC, QtCore.SIGNAL('activated()'),
                     self.dock.horizontalTimeSlider.setFocus)

        # put default values
        self.dock.horizontalTimeSlider.setMinimum(conf.MIN_TIMESLIDER_DEFAULT)
        self.dock.horizontalTimeSlider.setMaximum(conf.MAX_TIMESLIDER_DEFAULT)
        self.dock.dateTimeEditCurrentTime.setMinimumDate(MIN_QDATE)
        self.showLabel = conf.DEFAULT_SHOW_LABEL
        self.exportEmpty = conf.DEFAULT_EXPORT_EMPTY
        self.labelOptions = TimestampLabelConfig()

        # add to plugins toolbar
        try:
            self.action = QAction("Toggle visibility", self.iface.mainWindow())
            self.action.triggered.connect(self.toggleDock)
            self.iface.addPluginToMenu("&TimeManager", self.action)
        except:
            pass # OK for testing

    def toggleDock(self):
        self.dock.setVisible(not self.dock.isVisible())

    def getOptionsDialog(self):
        return self.optionsDialog

    def showLabelOptions(self):
        # TODO maybe more clearly
        self.dialog = QtGui.QDialog()
        self.labelOptionsDialog = label_options.Ui_labelOptions()
        self.labelOptionsDialog.setupUi(self.dialog)
        self.labelOptionsDialog.fontsize.setValue(self.labelOptions.size)
        self.labelOptionsDialog.time_format.setText(self.labelOptions.fmt)
        self.labelOptionsDialog.font.setCurrentFont(QFont(self.labelOptions.font))
        self.labelOptionsDialog.placement.addItems(TimestampLabelConfig.PLACEMENTS)
        self.labelOptionsDialog.placement.setCurrentIndex(TimestampLabelConfig.PLACEMENTS.index(
            self.labelOptions.placement))
        self.labelOptionsDialog.text_color.setColor(QColor(self.labelOptions.color))
        self.labelOptionsDialog.bg_color.setColor(QColor(self.labelOptions.bgcolor))
        self.labelOptionsDialog.buttonBox.accepted.connect(self.saveLabelOptions)

        self.dialog.show()

    def saveLabelOptions(self):
        self.labelOptions.font =  self.labelOptionsDialog.font.currentFont().family()
        self.labelOptions.size = self.labelOptionsDialog.fontsize.value()
        self.labelOptions.bgcolor = self.labelOptionsDialog.bg_color.color().name()
        self.labelOptions.color = self.labelOptionsDialog.text_color.color().name()
        self.labelOptions.placement = self.labelOptionsDialog.placement.currentText()
        self.labelOptions.fmt = self.labelOptionsDialog.time_format.text()

    def optionsClicked(self):
        self.showOptions.emit()
        
    def exportVideoClicked(self):
        self.exportVideo.emit()
        
    def toggleTimeClicked(self):
        self.toggleTime.emit()
        
    def backClicked(self):
        self.back.emit()
        
    def forwardClicked(self):
        self.forward.emit()
        
    def playClicked(self):
        self.play.emit()

    def currentTimeChangedSlider(self,sliderVal):
        try:
            pct = (sliderVal - self.dock.horizontalTimeSlider.minimum())*1.0/(
                self.dock.horizontalTimeSlider.maximum() - self.dock.horizontalTimeSlider.minimum())
        except:
            # slider is not properly initialized yet
            return
        self.signalSliderTimeChanged.emit(pct)
        
    def currentTimeChangedDateText(self,qdate):
        self.signalCurrentTimeUpdated.emit(qdate)
        
    def currentTimeFrameTypeChanged(self,frameType):
        self.signalTimeFrameType.emit(frameType)
        
    def currentTimeFrameSizeChanged(self,frameSize):
        if frameSize < 1: # time frame size = 0  is meaningless
            self.dock.spinBoxTimeExtent.setValue(1)
            return
        self.signalTimeFrameSize.emit(frameSize)
        
    def unload(self):
        """unload the plugin"""
        self.iface.removeDockWidget(self.dock)
        self.iface.removePluginMenu("TimeManager", self.action)

    def showOptionsDialog(self,layerList,animationFrameLength,playBackwards=False,
                          loopAnimation=False):
        """show the optionsDialog and populate it with settings from timeLayerManager"""
        
        # check if the dialog is already showing
        if self.optionsDialog is not None:
            self.optionsDialog.raise_()
            self.optionsDialog.activateWindow()
            return
        
        # load the form
        self.optionsDialog = uic.loadUi(os.path.join(self.path,"options.ui"))
       
        # restore settings from layerList:
        for layer in layerList:
            settings = ls.getSettingsFromLayer(layer)
            ls.addSettingsToRow(settings, self.optionsDialog.tableWidget)
        
        # restore animation options
        self.optionsDialog.spinBoxFrameLength.setValue(animationFrameLength)
        self.optionsDialog.checkBoxBackwards.setChecked(playBackwards)
        self.optionsDialog.checkBoxLabel.setChecked(self.showLabel)
        self.optionsDialog.checkBoxDontExportEmpty.setChecked(not self.exportEmpty)
        self.optionsDialog.checkBoxLoop.setChecked(loopAnimation)
        self.optionsDialog.show_label_options_button.clicked.connect(self.showLabelOptions)
        self.optionsDialog.checkBoxLabel.stateChanged.connect(self.showOrHideLabelOptions)

        # show dialog
        self.showOrHideLabelOptions()
        self.optionsDialog.show()

        # create raster and vector dialogs
        #self.rasterDialog = RasterLayerDialog()
        self.vectorDialog = VectorLayerDialog(os.path.join(self.path,ADD_VECTOR_LAYER_WIDGET_FILE), self.optionsDialog.tableWidget)
        self.rasterDialog = RasterLayerDialog(os.path.join(self.path,ADD_RASTER_LAYER_WIDGET_FILE), self.optionsDialog.tableWidget)
        # establish connections
        self.optionsDialog.pushButtonAddVector.clicked.connect(self.vectorDialog.show)
        self.optionsDialog.pushButtonAddRaster.clicked.connect(self.rasterDialog.show)
        self.optionsDialog.pushButtonRemove.clicked.connect(self.removeLayer)
        self.optionsDialog.buttonBox.accepted.connect(self.saveOptions)
        self.optionsDialog.buttonBox.accepted.connect(self.setOptionsDialogToNone)
        self.optionsDialog.buttonBox.rejected.connect(self.setOptionsDialogToNone)
        self.optionsDialog.rejected.connect(self.setOptionsDialogToNone)
        self.optionsDialog.buttonBox.helpRequested.connect(self.showHelp)

    def showOrHideLabelOptions(self):
        self.optionsDialog.show_label_options_button.setEnabled(self.optionsDialog.checkBoxLabel.isChecked())
        
    def showHelp(self):
        """show the help dialog"""
        self.helpDialog = uic.loadUi(os.path.join(self.path,"help.ui"))
        helpPath = QUrl('file:///'+replace(os.path.join(self.path,"help.htm"),'\\','/')) # windows
        # hack: Qt expects / instead of \
        #QMessageBox.information(self.iface.mainWindow(),'Error',str(helpPath))
        self.helpDialog.textBrowser.setSource(helpPath)
        self.helpDialog.show()

    def saveOptions(self):
        """save the options from optionsDialog to timeLayerManager"""
        self.signalSaveOptions.emit()

    def debug(self, msg):
            QMessageBox.information(self.iface.mainWindow(),'Info', msg)

    def setOptionsDialogToNone(self):
        """set self.optionsDialog to None"""
        self.optionsDialog = None

    def removeLayer(self):
        """removes the currently selected layer (= row) from options"""
        currentRow = self.optionsDialog.tableWidget.currentRow()
        try:
            layerName = self.optionsDialog.tableWidget.item(currentRow,0).text()
        except AttributeError: # if no row is selected
            return
        if QMessageBox.question(self.optionsDialog,'Remove Layer','Do you really want to remove layer '+layerName+'?',QMessageBox.Ok,QMessageBox.Cancel) == QMessageBox.Ok:
            self.optionsDialog.tableWidget.removeRow(self.optionsDialog.tableWidget.currentRow())     

    def disableAnimationExport(self):
        """disable the animation export button"""
        self.dock.pushButtonExportVideo.setEnabled(False)
        
    def enableAnimationExport(self):
        """enable the animation export button"""
        self.dock.pushButtonExportVideo.setEnabled(True)

    def refreshMapCanvas(self,sender=None):
        """refresh the map canvas"""
        #QMessageBox.information(self.iface.mainWindow(),'Test Output','Refresh!\n'+str(sender))
        self.iface.mapCanvas().refresh()

    def setTimeFrameSize(self,frameSize):
        """set spinBoxTimeExtent to given framzeSize"""
        self.dock.spinBoxTimeExtent.setValue(frameSize)
        
    def setTimeFrameType(self,frameType):
        """set comboBoxTimeExtent to given frameType"""
        i = self.dock.comboBoxTimeExtent.findText(frameType)
        self.dock.comboBoxTimeExtent.setCurrentIndex(i)        
        
    def setActive(self, isActive):
        """set pushButtonToggleTime active/inactive"""
        self.dock.pushButtonToggleTime.setChecked(isActive)
    
    def addActionShowSettings(self, action):
        """add action to pushButttonOptions"""
        self.dock.pushButtonOptions.addAction(action)
        
    def turnPlayButtonOff(self):
        """turn pushButtonPlay off"""
        if self.dock.pushButtonPlay.isChecked():
            self.dock.pushButtonPlay.toggle()


    def renderLabel(self, painter):
        """render the current timestamp on the map canvas"""        
        if not self.showLabel:
            return

        dt = self.model.getCurrentTimePosition()
        if dt is None:
            # this is only a fallback because QDateTime loses microsecond precision
            dt = QDateTime_to_datetime(self.dock.dateTimeEditCurrentTime.getDateTime())

        labelString = datetime_to_str(dt, self.labelOptions.fmt)

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
        html = '<span style="background-color:%s; padding: 5px;"><font face="%s" size="%s" color="%s">%s</font></span>' % \
               (self.labelOptions.bgcolor, self.labelOptions.font, self.labelOptions.size, self.labelOptions.color, labelString)
        txt.setHtml(html)
        layout = txt.documentLayout()
        size = layout.documentSize()
        
        x = width - 5 - size.width() if flags & Qt.AlignRight else 5
        y = height - 5 - size.height() if flags & Qt.AlignBottom else 5

        painter.translate(x, y)
        layout.draw(painter, QAbstractTextDocumentLayout.PaintContext())
        painter.translate(-x, -y)  # translate back

    def repaintRasters(self):
        rasters = self.model.getActiveRasters()
        map(lambda x: x.layer.triggerRepaint(), rasters)
