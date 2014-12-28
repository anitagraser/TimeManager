# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 10:13:39 2010

@author: agraser
"""

import os, sys
sys.path.append("~/.qgis/python")

from string import replace

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

from qgis.core import *

from timelayer import *
from timevectorlayer import *
from timerasterlayer import *
from time_util import datetime_to_epoch

# The QTSlider only supports integers as the min and max, therefore the maximum maximum value
# is whatever can be stored in an int. Making it a signed int to be sure.
# (http://qt-project.org/doc/qt-4.8/qabstractslider.html)
MAX_TIME_LENGTH_SECONDS = 2**31-1
# according to the docs of QDateTime, the minimum date supported is the first day of
# year 100  (http://qt-project.org/doc/qt-4.8/qdatetimeedit.html#minimumDate-prop)
MIN_QDATE = QDate(100, 1, 1)

class TimestampLabelConfig(object):
    """Edit configuration for the timestamp label here, in liu of GUI control"""
    font = "Arial"      # Font names or family, comma-separated CSS style
    size = 4            # Relative values between 1-7
    fmt = "yyyy-MM-dd hh:mm:ss.zzz"  # Uses Qt's QDate format, see: http://qt-project.org/doc/qt-4.8/qdate.html#toString
    placement = 'SE'    # Choose from N, NE, E, SE, S, SW, W, NW
    color = 'black'     # Text color as name, rgb(RR,GG,BB), or #XXXXXX
    bgcolor = 'white'   # Background color as name, rgb(RR,GG,BB), or #XXXXXX

class TimeManagerGuiControl(QObject):
    """This class controls all plugin-related GUI elements. Emitted signals are defined here.
    New TimeLayers are created here, in createTimeLayer()"""
    
    showOptions = pyqtSignal()
    exportVideo = pyqtSignal()
    toggleTime = pyqtSignal()
    back = pyqtSignal()
    forward = pyqtSignal()
    play = pyqtSignal()
    signalCurrentTime = pyqtSignal(object)
    signalTimeFrameType = pyqtSignal(str)
    signalTimeFrameSize = pyqtSignal(int)
    signalOptionsStart = pyqtSignal()
    signalAnimationOptions = pyqtSignal(int,bool,bool)
    saveOptionsStart = pyqtSignal()
    saveOptionsEnd = pyqtSignal()
    registerTimeLayer = pyqtSignal(object)
    
    def __init__ (self,iface,timeLayerManager):
        """initialize the GUI control"""
        QObject.__init__(self)
        self.iface = iface   
        self.timeLayerManager = timeLayerManager
        self.showLabel = False
        self.labelOptions = TimestampLabelConfig()  # placeholder until config is in GUI
        
        self.optionsDialog = None
        
        # load the form
        path = os.path.dirname( os.path.abspath( __file__ ) )
        self.dock = uic.loadUi( os.path.join( path, "dockwidget2.ui" ) )
        self.iface.addDockWidget( Qt.BottomDockWidgetArea, self.dock )

        
        self.dock.pushButtonExportVideo.setEnabled(False) # only enabled if there are managed layers
        self.setTimeFrameType('days') # should be 'days'
        
        self.dock.pushButtonOptions.clicked.connect(self.optionsClicked) 
        self.dock.pushButtonExportVideo.clicked.connect(self.exportVideoClicked)
        self.dock.pushButtonToggleTime.clicked.connect(self.toggleTimeClicked)
        self.dock.pushButtonBack.clicked.connect(self.backClicked)
        self.dock.pushButtonForward.clicked.connect(self.forwardClicked)
        self.dock.pushButtonPlay.clicked.connect(self.playClicked)   
        self.dock.dateTimeEditCurrentTime.dateTimeChanged.connect(self.currentTimeChanged)
        self.dock.dateTimeEditCurrentTime.setMinimumDate(MIN_QDATE)
        self.dock.horizontalTimeSlider.valueChanged.connect(self.currentTimeChangedSlider)
        self.dock.comboBoxTimeExtent.currentIndexChanged[str].connect(self.currentTimeFrameTypeChanged)
        self.dock.spinBoxTimeExtent.valueChanged.connect(self.currentTimeFrameSizeChanged)          
        self.iface.mapCanvas().renderComplete.connect(self.renderLabel)
        #self.debug("initiali value:{} ".format(self.dock.horizontalTimeSlider.value()))

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
        """Needs special handling because the Qtslider can only hold integer values, resulting
        in silent overflow when passing long values from Python.
        So we see the percentage the slider is at and determine the epoch time (which can be a
        long if it's sufficiently in the past or in the future)."""

        #self.debug("slider val {}".format(sliderVal))

        try:

            pct = (sliderVal - self.dock.horizontalTimeSlider.minimum())*1.0/(
                self.dock.horizontalTimeSlider.maximum() - self.dock.horizontalTimeSlider.minimum())
        except:
            # slider is not properly initialized yet
            return

        try:
            realEpochTime = int(pct * (datetime_to_epoch(self.timeExtents[1]) - datetime_to_epoch(
                self.timeExtents[0])) + datetime_to_epoch(self.timeExtents[0]))
        except:
            # extents are not set
            realEpochTime = 0

        #self.debug("pct:{}, epoch:{} ".format(pct,realEpochTime))

        self.signalCurrentTime.emit(realEpochTime)
        
    def currentTimeChanged(self,datetime):
        self.signalCurrentTime.emit(datetime)
        
    def currentTimeFrameTypeChanged(self,frameType):
        self.signalTimeFrameType.emit(frameType)
        
    def currentTimeFrameSizeChanged(self,frameSize):
        self.signalTimeFrameSize.emit(frameSize)
        
    def unload(self):
        """unload the plugin"""
        self.iface.removeDockWidget(self.dock)
        
    def showOptionsDialog(self,layerList,animationFrameLength,playBackwards,loopAnimation):
        """show the optionsDialog and populate it with settings from timeLayerManager"""
        
        # check if the dialog is already showing
        if self.optionsDialog is not None:
            self.optionsDialog.raise_()
            self.optionsDialog.activateWindow()
            return
        
        # load the form
        path = os.path.dirname( os.path.abspath( __file__ ) )
        self.optionsDialog = uic.loadUi(os.path.join(path,"options.ui"))
       
        # restore options from layerList:
        for layer in layerList:
            
            layerName=layer.getName()
            if layer.isEnabled():
                checkState=Qt.Checked
            else:
                checkState=Qt.Unchecked
            layerId=layer.getLayerId()
            
            offset=layer.getOffset()

            times=layer.getTimeAttributes()
            startTime=times[0]
            if times[0] != times[1]: # end time equals start time for timeLayers of type timePoint
                endTime = times[1]
            else:
                endTime = ""
            timeFormat=layer.getTimeFormat()
            self.addRowToOptionsTable(layerName,checkState,layerId,offset,timeFormat,startTime,endTime)
        
        # restore animation options
        self.optionsDialog.spinBoxFrameLength.setValue(animationFrameLength)
        self.optionsDialog.checkBoxBackwards.setChecked(playBackwards)
        self.optionsDialog.checkBoxLabel.setChecked(self.showLabel)
        self.optionsDialog.checkBoxLoop.setChecked(loopAnimation)

        # show diaolg
        self.optionsDialog.show()

        # establish connections
        self.optionsDialog.pushButtonAdd.clicked.connect(self.showAddLayerDialog)
        self.optionsDialog.pushButtonRemove.clicked.connect(self.removeLayer)
        self.optionsDialog.buttonBox.accepted.connect(self.saveOptions)
        self.optionsDialog.buttonBox.accepted.connect(self.setOptionsDialogToNone)
        self.optionsDialog.buttonBox.rejected.connect(self.setOptionsDialogToNone)
        self.optionsDialog.rejected.connect(self.setOptionsDialogToNone)
        self.optionsDialog.buttonBox.helpRequested.connect(self.showHelp)
        
        self.mapLayers=QgsMapLayerRegistry.instance().mapLayers()
        
    def showHelp(self):
        """show the help dialog"""
        path = os.path.dirname( os.path.abspath( __file__ ) )
        self.helpDialog = uic.loadUi(os.path.join(path,"help.ui"))
        helpPath = QUrl('file:///'+replace(os.path.join(path,"help.htm"),'\\','/')) # windows hack: Qt expects / instead of \
        #QMessageBox.information(self.iface.mainWindow(),'Error',str(helpPath))
        self.helpDialog.textBrowser.setSource(helpPath)
        self.helpDialog.show()

    def saveOptions(self):
        """save the options from optionsDialog to timeLayerManager"""
        #self.emit(SIGNAL('saveOptionsStart()'),)
        self.saveOptionsStart.emit()
        
        # loop through the rows in the table widget and add all layers accordingly
        for row in range(0,self.optionsDialog.tableWidget.rowCount()):

        
            if self.createTimeLayer(row):
                # save animation options
                animationFrameLength = self.optionsDialog.spinBoxFrameLength.value()
                playBackwards = self.optionsDialog.checkBoxBackwards.isChecked()
                self.showLabel = self.optionsDialog.checkBoxLabel.isChecked()
                loopAnimation = self.optionsDialog.checkBoxLoop.isChecked()
                self.signalAnimationOptions.emit(animationFrameLength,playBackwards,loopAnimation)
                
                self.refreshMapCanvas('saveOptions')
                
                if len(self.getManagedLayers()) > 0:
                    self.dock.pushButtonExportVideo.setEnabled(True)
                else:
                    self.dock.pushButtonExportVideo.setEnabled(False)
                
                self.saveOptionsEnd.emit()
            else:
                break

    def debug(self, msg):
            QMessageBox.information(self.iface.mainWindow(),'Info', msg)
            
    def createTimeLayer(self,row):
        """create a TimeLayer from options set in the table row"""
        # layer
        ##self.debug("Creating time layer")
        layer=QgsMapLayerRegistry.instance().mapLayer(self.optionsDialog.tableWidget.item(row,4).text())
        if self.optionsDialog.tableWidget.item(row,3).checkState() == Qt.Checked:
            isEnabled = True
        else:
            isEnabled = False
        # offset
        offset = int(self.optionsDialog.tableWidget.item(row,6).text()) # currently only seconds!        

        # start time
        startTimeAttribute = self.optionsDialog.tableWidget.item(row,1).text()
        # end time (optional)
        if self.optionsDialog.tableWidget.item(row,2).text() == "": #QString(""):
            endTimeAttribute = startTimeAttribute # end time equals start time for timeLayers of type timePoint
        else:
            endTimeAttribute = self.optionsDialog.tableWidget.item(row,2).text()
        # time format
        timeFormat = self.optionsDialog.tableWidget.item(row,5).text()
            
        # this should be a python class factory
        if type(layer).__name__ == "QgsVectorLayer":
            timeLayerClass = TimeVectorLayer
        elif type(layer).__name__ == "QgsRasterLayer":
            timeLayerClass = TimeRasterLayer           
            
        try: # here we use the selected class
            timeLayer = timeLayerClass(layer,startTimeAttribute,endTimeAttribute,isEnabled,
                                       timeFormat,offset, self.iface)
        except InvalidTimeLayerError, e:
            QMessageBox.information(self.iface.mainWindow(),'Error','An error occured while trying to add layer '+layer.name()+' to TimeManager.\n'+e.value)
            return False

        ##self.debug("registering time layer")
        self.registerTimeLayer.emit(timeLayer)
        return True

        
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
            
    def showAddLayerDialog(self):
        """show the addLayerDialog and populate it with QgsVectorLayers from QgsMapLayerRegistry"""
        path = os.path.dirname( os.path.abspath( __file__ ) )
        self.addLayerDialog = uic.loadUi(os.path.join(path,"addLayer.ui"))

        self.mapLayers=QgsMapLayerRegistry.instance().mapLayers()
        self.layerIds=[]
        managedLayers=self.getManagedLayers()
        tempname=''
        # fill the combo box with all available vector layers
        for (name,layer) in self.mapLayers.iteritems():
            #if type(layer).__name__ == "QgsVectorLayer" and layer not in managedLayers:
            if layer not in managedLayers:
                self.layerIds.append(name)
                tempname = unicode(layer.name())#.rstrip('01234567890') # stripping out the trailing numeric code
                self.addLayerDialog.comboBoxLayers.addItem(tempname)

        if len(self.layerIds) == 0:
            QMessageBox.information(self.optionsDialog,'Error','There are no unmanaged vector layers in the project!')
            return

        # get attributes of the first layer for gui initialization
        self.getLayerAttributes(0)

        self.addLayerDialog.show()

        # establish connections
        self.addLayerDialog.comboBoxLayers.currentIndexChanged.connect(self.getLayerAttributes)
        self.addLayerDialog.buttonBox.accepted.connect(self.addLayerToOptions)

    def getManagedLayers(self):
        """get list of QgsMapLayers listed in optionsDialog.tableWidget"""
        layerList=[]
            
        for row in range(0,self.optionsDialog.tableWidget.rowCount()):
            # layer
            layer=self.mapLayers[self.optionsDialog.tableWidget.item(row,4).text()]
            layerList.append(layer)
        return layerList

    def getLayerAttributes(self,comboIndex):
        """get list layer attributes and fill the combo boxes"""
        try: 
            layer=self.mapLayers[self.layerIds[comboIndex]]
        except: 
            #QMessageBox.information(self.iface.mainWindow(),'Test Output','Error at: self.mapLayers[self.layerIds[comboIndex]]')
            return
        try: 
            provider=layer.dataProvider() # this will crash on OpenLayers layers
        except AttributeError:
            return
        try:
            fieldmap=provider.fields() # this function will crash on raster layers
        except:
            #QMessageBox.information(self.iface.mainWindow(),'Test Output','Error at: provider.fields()')
            return
        self.addLayerDialog.comboBoxStart.clear()
        self.addLayerDialog.comboBoxEnd.clear()
        self.addLayerDialog.comboBoxEnd.addItem('') # this box is optional, so we add an empty item
        for attr in fieldmap: 
            self.addLayerDialog.comboBoxStart.addItem(attr.name())
            self.addLayerDialog.comboBoxEnd.addItem(attr.name())

    def addLayerToOptions(self):
        """write information from addLayerDialog to optionsDialog.tableWidget"""
        layerName = self.addLayerDialog.comboBoxLayers.currentText()
        startTime = self.addLayerDialog.comboBoxStart.currentText()
        endTime = self.addLayerDialog.comboBoxEnd.currentText()
        checkState = Qt.Checked
        layerId = self.layerIds[self.addLayerDialog.comboBoxLayers.currentIndex()]
        timeFormat = "%Y-%m-%d %H:%M:%S" # default
        offset = self.addLayerDialog.spinBoxOffset.value()

        self.addRowToOptionsTable(layerName,checkState,layerId,offset,timeFormat,startTime,endTime)

    def addRowToOptionsTable(self,layerName,checkState,layerId,offset,timeFormat="",startTime="",endTime=""):
        """insert a new row into optionsDialog.tableWidget"""
        # insert row
        row=self.optionsDialog.tableWidget.rowCount()
        self.optionsDialog.tableWidget.insertRow(row)
        
        # insert values
        layerItem = QTableWidgetItem()
        layerItem.setText(layerName)
        self.optionsDialog.tableWidget.setItem(row,0,layerItem)

        startItem = QTableWidgetItem()
        startItem.setText(startTime)
        self.optionsDialog.tableWidget.setItem(row,1,startItem)

        endItem = QTableWidgetItem()
        endItem.setText(endTime)
        self.optionsDialog.tableWidget.setItem(row,2,endItem)

        checkBoxItem = QTableWidgetItem()
        checkBoxItem.setCheckState(checkState)
        self.optionsDialog.tableWidget.setItem(row,3,checkBoxItem)

        indexItem = QTableWidgetItem()
        indexItem.setText(layerId)
        self.optionsDialog.tableWidget.setItem(row,4,indexItem)

        timeFormatItem = QTableWidgetItem()
        timeFormatItem.setText(timeFormat)
        self.optionsDialog.tableWidget.setItem(row,5,timeFormatItem)   
    
        offsetItem = QTableWidgetItem()
        offsetItem.setText(str(offset))
        self.optionsDialog.tableWidget.setItem(row,6,offsetItem)

    def updateTimeExtents(self,timeExtents):
        """update time extents showing in labels and represented by horizontalTimeSlider"""
        self.timeExtents = timeExtents
        if timeExtents != (None,None):
            #self.debug("extents:{}".format(timeExtents))
            self.dock.labelStartTime.setText(str(timeExtents[0])[0:23])
            self.dock.labelEndTime.setText(str(timeExtents[1])[0:23])

            timeLength = datetime_to_epoch(timeExtents[1]) - datetime_to_epoch(timeExtents[0])

            if timeLength> MAX_TIME_LENGTH_SECONDS:
                self.debug("Time length of {} seconds is too long for QT Slider to handle ("
                           "integer overflow). Maximum value allowed: {}".format(timeLength,
                                                                                 MAX_TIME_LENGTH_SECONDS))

            self.dock.horizontalTimeSlider.setMinimum(0)
            self.dock.horizontalTimeSlider.setMaximum(timeLength)

        else: # set to default values
            #self.debug("No extents available yet")
            self.dock.labelStartTime.setText('not set')
            self.dock.labelEndTime.setText('not set')
            self.dock.horizontalTimeSlider.setMinimum(0)
            self.dock.horizontalTimeSlider.setMaximum(1)

    def refreshTimeRestrictions(self,currentTimePosition,sender=None):
        """update current time showing in dateTimeEditCurrentTime and horizontalTimeSlider"""

        if currentTimePosition is None:
            return
        self.dock.dateTimeEditCurrentTime.setDateTime(currentTimePosition)
        timeval = datetime_to_epoch(currentTimePosition)
        try:
            pct = (timeval - datetime_to_epoch(self.timeExtents[0]))*1.0 / (datetime_to_epoch(
                self.timeExtents[1]) - datetime_to_epoch(self.timeExtents[0]))

            sliderVal = self.dock.horizontalTimeSlider.minimum() + int(pct * (
                self.dock.horizontalTimeSlider.maximum()
                - self.dock.horizontalTimeSlider.minimum()))
            #self.debug("Slider val at refresh:{}".format(sliderVal))
            self.dock.horizontalTimeSlider.setValue(sliderVal)
        except:
            pass



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

        labelString = str(self.dock.dateTimeEditCurrentTime.dateTime().toString(self.labelOptions.fmt))

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
