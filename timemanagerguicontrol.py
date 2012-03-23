# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 10:13:39 2010

@author: agraser
"""

import os, sys
sys.path.append("~/.qgis/python")

from string import replace
from time import mktime

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic

from qgis.core import *

from timelayer import *
from timevectorlayer import *
from timerasterlayer import *

class TimeManagerGuiControl(QObject):
    """This class controls all plugin-related GUI elements. Emitted signals are defined here.
    New TimeLayers are created here, in createTimeLayer()"""
    
    def __init__ (self,iface,timeLayerManager):
        """initialize the GUI control"""
        QObject.__init__(self)
        self.iface = iface   
        self.timeLayerManager = timeLayerManager
        self.showLabel = False
        
        self.optionsDialog = None
        
        # load the form
        path = os.path.dirname( os.path.abspath( __file__ ) )
        self.dock = uic.loadUi( os.path.join( path, "dockwidget2.ui" ) )
        self.iface.addDockWidget( Qt.BottomDockWidgetArea, self.dock )
        
        self.dock.pushButtonExportVideo.setEnabled(False) # only enabled if there are managed layers
        self.setTimeFrameType('days') # should be 'days'
        
        QObject.connect(self.dock.pushButtonOptions, SIGNAL('clicked()'),self.optionsClicked) 
        QObject.connect(self.dock.pushButtonExportVideo, SIGNAL('clicked()'),self.exportVideoClicked)
        QObject.connect(self.dock.pushButtonToggleTime,SIGNAL('clicked()'),self.toggleTimeClicked)
        QObject.connect(self.dock.pushButtonBack,SIGNAL('clicked()'),self.backClicked)
        QObject.connect(self.dock.pushButtonForward,SIGNAL('clicked()'),self.forwardClicked)
        QObject.connect(self.dock.pushButtonPlay,SIGNAL('clicked()'),self.playClicked)   
        QObject.connect(self.dock.dateTimeEditCurrentTime,SIGNAL('dateTimeChanged(QDateTime)'),self.currentTimeChanged)
        QObject.connect(self.dock.horizontalTimeSlider,SIGNAL('valueChanged(int)'),self.currentTimeChanged)
        QObject.connect(self.dock.comboBoxTimeExtent,SIGNAL('currentIndexChanged(QString)'),self.currentTimeFrameTypeChanged)
        QObject.connect(self.dock.spinBoxTimeExtent,SIGNAL('valueChanged(int)'),self.currentTimeFrameSizeChanged)          

        QObject.connect(self.iface.mapCanvas(), SIGNAL("renderComplete(QPainter *)"), self.renderLabel)

    def optionsClicked(self):
        self.emit(SIGNAL('showOptions()'),)
        
    def exportVideoClicked(self):
        self.emit(SIGNAL('exportVideo()'),)
        
    def toggleTimeClicked(self):
        self.emit(SIGNAL('toggleTime()'),)
        
    def backClicked(self):
        self.emit(SIGNAL('back()'),)
        
    def forwardClicked(self):
        self.emit(SIGNAL('forward()'),)
        
    def playClicked(self):
        self.emit(SIGNAL('play()'),)
        
    def currentTimeChanged(self,datetime):
        self.emit(SIGNAL('setCurrentTime(PyQt_PyObject)'),datetime)
        
    def currentTimeFrameTypeChanged(self,frameType):
        self.emit(SIGNAL('setTimeFrameType(QString)'),frameType)
        
    def currentTimeFrameSizeChanged(self,frameSize):
        self.emit(SIGNAL('setTimeFrameSize(PyQt_PyObject)'),frameSize)

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
        QObject.connect(self.optionsDialog.pushButtonAdd,SIGNAL('clicked()'),self.showAddLayerDialog)
        QObject.connect(self.optionsDialog.pushButtonRemove,SIGNAL('clicked()'),self.removeLayer)
        QObject.connect(self.optionsDialog.buttonBox,SIGNAL('accepted()'),self.saveOptions)
        QObject.connect(self.optionsDialog.buttonBox,SIGNAL('accepted()'),self.setOptionsDialogToNone)
        QObject.connect(self.optionsDialog.buttonBox,SIGNAL('rejected()'),self.setOptionsDialogToNone)
        QObject.connect(self.optionsDialog,SIGNAL('rejected()'),self.setOptionsDialogToNone)
        QObject.connect(self.optionsDialog.buttonBox,SIGNAL('helpRequested()'),self.showHelp)
        
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
        self.emit(SIGNAL('saveOptionsStart()'),)
        
        # loop through the rows in the table widget and add all layers accordingly
        for row in range(0,self.optionsDialog.tableWidget.rowCount()):

        
            if self.createTimeLayer(row):
                # save animation options
                animationFrameLength = self.optionsDialog.spinBoxFrameLength.value()
                playBackwards = self.optionsDialog.checkBoxBackwards.isChecked()
                self.showLabel = self.optionsDialog.checkBoxLabel.isChecked()
                loopAnimation = self.optionsDialog.checkBoxLoop.isChecked()
                self.emit(SIGNAL('setAnimationOptions(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),animationFrameLength,playBackwards,loopAnimation)
                
                self.refreshMapCanvas('saveOptions')
                
                if len(self.getManagedLayers()) > 0:
                    self.dock.pushButtonExportVideo.setEnabled(True)
                else:
                    self.dock.pushButtonExportVideo.setEnabled(False)
                
                self.emit(SIGNAL('saveOptionsEnd()'),)
            else:
                break
            
    def createTimeLayer(self,row):
        """create a TimeLayer from options set in the table row"""
        # layer
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
        if self.optionsDialog.tableWidget.item(row,2).text() == QString(""):
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
            timeLayer = timeLayerClass(layer,startTimeAttribute,endTimeAttribute,isEnabled,timeFormat,offset)
        except InvalidTimeLayerError, e:
            QMessageBox.information(self.iface.mainWindow(),'Error','An error occured while trying to add layer '+layer.name()+' to TimeManager.\n'+e.value)
            return False
            
        self.emit(SIGNAL('registerTimeLayer(PyQt_PyObject)'),timeLayer) 
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
                tempname = str(layer.name())#.rstrip('01234567890') # stripping out the trailing numeric code
                self.addLayerDialog.comboBoxLayers.addItem(tempname)

        if len(self.layerIds) == 0:
            QMessageBox.information(self.optionsDialog,'Error','There are no unmanaged vector layers in the project!')
            return

        # get attributes of the first layer for gui initialization
        self.getLayerAttributes(0)

        self.addLayerDialog.show()

        # establish connections
        QObject.connect(self.addLayerDialog.comboBoxLayers,SIGNAL('currentIndexChanged (int)'),self.getLayerAttributes)
        QObject.connect(self.addLayerDialog.buttonBox,SIGNAL('accepted()'),self.addLayerToOptions)

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
        provider=layer.dataProvider()
        try: # this function will crash on raster layers
            fieldmap=provider.fields()
        except:
            #QMessageBox.information(self.iface.mainWindow(),'Test Output','Error at: provider.fields()')
            return
        self.addLayerDialog.comboBoxStart.clear()
        self.addLayerDialog.comboBoxEnd.clear()
        self.addLayerDialog.comboBoxEnd.addItem('') # this box is optional, so we add an empty item
        for (k,attr) in fieldmap.iteritems():
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
        if timeExtents != (None,None):
            self.dock.labelStartTime.setText(str(timeExtents[0])[0:23])
            self.dock.labelEndTime.setText(str(timeExtents[1])[0:23])
            self.dock.horizontalTimeSlider.setMinimum(mktime(timeExtents[0].timetuple())) 
            self.dock.horizontalTimeSlider.setMaximum(mktime(timeExtents[1].timetuple())) 
        else: # set to default values
            self.dock.labelStartTime.setText('not set')
            self.dock.labelEndTime.setText('not set')
            self.dock.horizontalTimeSlider.setMinimum(0)
            self.dock.horizontalTimeSlider.setMaximum(1)

    def refreshTimeRestrictions(self,currentTimePosition,sender=None):
        """update current time showing in dateTimeEditCurrentTime and horizontalTimeSlider"""
        #QMessageBox.information(self.iface.mainWindow(),'Test Output','Refresh!\n'+str(sender)+'\n'+str(currentTimePosition))
        try:
            self.dock.dateTimeEditCurrentTime.setDateTime(currentTimePosition)
            self.dock.horizontalTimeSlider.setValue(mktime(currentTimePosition.timetuple())) 
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
            
        self.font = QFont("Arial")         
        self.labelString = str(self.dock.dateTimeEditCurrentTime.dateTime().toString("yyyy-MM-dd hh:mm:ss.zzz"))
        self.placementIndex = 3
        
        fm = QFontMetrics(self.font, painter.device())
        rect = fm.boundingRect(self.labelString)
        
        # Determine placement of label from form combo box
        index = self.placementIndex
        flags = 0
        if index == 0: # Bottom Left
          flags = Qt.AlignBottom | Qt.AlignLeft
        elif index == 1: # Top left
          flags = Qt.AlignTop | Qt.AlignLeft
        elif index == 2: # Top Right
          flags = Qt.AlignTop | Qt.AlignRight
        elif index == 3: # Bottom Right
          flags = Qt.AlignBottom | Qt.AlignRight
        else:
          print "Unknown placement index of " + str(index)
    
        # Get canvas dimensions
        width = painter.device().width()
        height = painter.device().height()
        
        # TODO: set font, color
    
        txt = QTextDocument()
        txt.setHtml('<span style="background-color:#ffffff;">'+self.labelString+"</span>")
        layout = txt.documentLayout()
        size = layout.documentSize()
        
        if flags & Qt.AlignRight:
          x = width - 5 - size.width()
        else:
          x = 5
    
        if flags & Qt.AlignBottom:
          y = height - 5 - size.height()
        else:
          y = 5
        
        painter.translate(x, y)
        layout.draw(painter, QAbstractTextDocumentLayout.PaintContext())
        painter.translate(-x, -y) # translate back
