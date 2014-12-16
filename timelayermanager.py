#!/usr/bin/python
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from timelayer import NotATimeAttributeError

class TimeLayerManager(QObject):
    """Class manages all layers that can be queried temporally and provides navigation in time. Parenthesized sections are not implemented yet. All functions, besides the get functions, trigger a redraw."""
    
    timeRestrictionsRefreshed = pyqtSignal(datetime)#object)
    projectTimeExtentsChanged = pyqtSignal(object)#tuple)
    lastLayerRemoved = pyqtSignal()
    toggledManagement = pyqtSignal(object)

    def __init__(self,iface):
        QObject.__init__(self)
        self.iface = iface
        self.timeLayerList = []
        self.projectTimeExtents = ()
        self.timeFrameType = 'days' # default
        self.timeFrameSize = 1 # some default value
        self.currentTimePosition = None
        self.timeManagementEnabled = True
        self.isFirstRun=True

    def isEnabled(self):
        """return true if the manager is enabled"""
        return self.timeManagementEnabled

    def getManagedLayers(self):
        """get the list of qgsMapLayers managed by the timeManager"""
        layerList = []
        for timeLayer in self.timeLayerList:
            layerList.append(timeLayer.layer)
        return layerList

    def getCurrentTimePosition(self):
        """returns the manager's currentTimePosition"""
        return self.currentTimePosition
        
    def getCurrentEpochPosition(self):
        """returns the manager's currentTimePosition"""
        epoch=datetime(1970,1,1)
        td = self.currentTimePosition - epoch
        return (td.microseconds + (td.seconds + td.days * 24 * 3600))
    
    def getTimeFrameType(self):
        """returns the type of the time frame, e.g. minutes, hours, days"""
        return self.timeFrameType
        
    def getTimeFrameSize(self):
        """returns the size of the time frame"""
        return self.timeFrameSize
        
    def getFrameCount(self):
        """returns the number of frames that can be generated using the current settings"""
        if len(self.getManagedLayers()) == 0:
            return 0
            
        try:
            td1 = self.projectTimeExtents[1]-self.projectTimeExtents[0]
        except TypeError: # hope this fixes #17 which I still cannot reproduce
            return 0
            
        td2 = self.timeFrame()
        # this is how you can devide two timedeltas (not supported by default):
        us1 = td1.microseconds + 1000000 * (td1.seconds + 86400 * td1.days)
        us2 = td2.microseconds + 1000000 * (td2.seconds + 86400 * td2.days)
        
        if us2 == 0:
            return 1000 # this is just a stupid default, TODO!
        
        return us1 / us2

    def hasLayers(self):
        """returns true if the manager has at least one layer registered"""
        if len(self.timeLayerList) > 0:
            return True
        else:
            return False

    def hasActiveLayers(self):
        """returns true if the manager has at least one layer registered"""
        if len(self.timeLayerList) > 0:
            for layer in self.timeLayerList:
                if layer.isEnabled():
                    return True
        return False

    def clearTimeLayerList(self):
        """clear the timeLayerList"""
        for timeLayer in self.timeLayerList:
            timeLayer.deleteTimeRestriction()
        self.timeLayerList=[]

    def timeFrame(self):
        """returns the current time frame as datetime.timedelta object"""
        if self.timeFrameType == 'months':
            return relativedelta(months=self.timeFrameSize) # months are not supported by timedelta
        elif self.timeFrameType == 'weeks':
            return timedelta(weeks=self.timeFrameSize)
        elif self.timeFrameType == 'days':
            return timedelta(days=self.timeFrameSize)
        elif self.timeFrameType == 'hours':
            return timedelta(hours=self.timeFrameSize)
        elif self.timeFrameType == 'minutes':
            return timedelta(minutes=self.timeFrameSize)
        elif self.timeFrameType == 'seconds':
            return timedelta(seconds=self.timeFrameSize)
        # current code only supports down to seconds!
        elif self.timeFrameType == 'milliseconds':
            return timedelta(milliseconds=self.timeFrameSize)
        elif self.timeFrameType == 'microseconds':
            return timedelta(microseconds=self.timeFrameSize)
        

    def refresh(self):
        """Applies or removes the temporal constraints for all managed (and enabled) layers"""
        if not self.hasLayers():
            return
        if self.timeManagementEnabled:
            for timeLayer in self.timeLayerList:
                #try:
                    timeLayer.setTimeRestriction(self.currentTimePosition,self.timeFrame())
                #except AttributeError: # if timeLayer is of NoneType
                #    pass
        else:
            for timeLayer in self.timeLayerList:
                if not timeLayer.hasTimeRestriction():
                    return
                timeLayer.deleteTimeRestriction()
        #self.emit(SIGNAL('timeRestrictionsRefreshed(PyQt_PyObject)'),self.currentTimePosition)   
        self.timeRestrictionsRefreshed.emit(self.currentTimePosition)
                
    def registerTimeLayer( self, timeLayer ):
        """Register a new layer for management and update the project's temporal extent"""
        self.timeLayerList.append( timeLayer )
        if len( self.timeLayerList ) == 1:
            # update projectTimeExtents to first layer's timeExtents
            self.setProjectTimeExtents(timeLayer.getTimeExtents())
            # Set current time to the earliest time record
            if self.isFirstRun:
                self.setCurrentTimePosition(self.projectTimeExtents[0])
                self.isFirstRun = False
        else:
            self.updateProjectTimeExtents()
        self.refresh()

    def removeTimeLayer(self,layerId):
        """remove the timeLayer with the given layerId"""
        for i in range(0,len(self.timeLayerList)):
            if self.timeLayerList[i].getLayerId() == layerId:
                self.timeLayerList.pop(i)
                
        # if the last layer was removed:
        if not self.hasLayers():
            self.setProjectTimeExtents((None,None))
            #self.emit(SIGNAL('lastLayerRemoved()'),)
            self.lastLayerRemoved.emit()
        self.refresh()

    def updateProjectTimeExtents(self):
        """Loop through all timeLayers and make sure that the projectTimeExtents cover all layers"""
        for timeLayer in self.timeLayerList:
            try:
                extents = timeLayer.getTimeExtents()
            except NotATimeAttributeError:
                continue # TODO: we should probably do something useful here
            if extents[0] < self.projectTimeExtents[0]:
                self.projectTimeExtents = (extents[0],self.projectTimeExtents[1])
            if extents[1] > self.projectTimeExtents[1]:
                self.projectTimeExtents = (self.projectTimeExtents[0],extents[1])

    def setProjectTimeExtents(self,timeExtents):
        """set projectTimeExtents to given time extent and emit signal 'projectTimeExtentsChanged(list)'"""
        self.projectTimeExtents = timeExtents
        #QMessageBox.information(self.iface.mainWindow(),'Debug Output','setProjectTimeExtents\nTime extents: '+str(timeExtents)+'\nType: '+str(type(timeExtents)))
        try:
            #self.emit(SIGNAL('projectTimeExtentsChanged(PyQt_PyObject)'),timeExtents)
            self.projectTimeExtentsChanged.emit(timeExtents)
        except TypeError: # if timeExtent is not specified
            pass

    def getProjectTimeExtents( self ):
        """Get the overall temporal extent of all managable (managed?) layers"""
        return self.projectTimeExtents
    
    def getTimeLayerList( self ):
        """Get the list of managed layers"""
        return self.timeLayerList

    def setTimeFrameType(self, frameType):
        """Defines the type of the time frame, accepts all values usable by timedelta objects:
        days, seconds, microseconds, milliseconds, minutes, hours, weeks"""
        #QMessageBox.information(self.iface.mainWindow(),'Debug Output','Time frame type: '+str(frameType))
        self.timeFrameType = frameType
        self.refresh()

    def setTimeFrameSize( self, frameSize ):
        """Defines the size of the time frame"""
        #QMessageBox.information(self.iface.mainWindow(),'Debug Output','Time frame size: '+str(frameSize))
        self.timeFrameSize = frameSize
        self.refresh()

    def setCurrentTimePosition( self, timePosition ):
        """Defines the currently selected point in time, which is at the beginning of the time-frame."""
         # TODO: Test
        if type(timePosition) == QDateTime:
            # convert QDateTime to datetime
            timePosition = datetime.strptime( str(timePosition.toString('yyyy-MM-dd hh:mm:ss.zzz')) ,"%Y-%m-%d %H:%M:%S.%f")
        elif type(timePosition) == int or type(timePosition) == float:
            timePosition = datetime.fromordinal(int(timePosition))
        self.currentTimePosition = timePosition
        #self.emit(SIGNAL('timeRestrictionsRefreshed(PyQt_PyObject)'),self.currentTimePosition) 
        self.timeRestrictionsRefreshed.emit(self.currentTimePosition)
        if self.isEnabled():
            self.refresh()

    def stepForward(self):
        """Shifts query forward in time by one time frame"""
        if self.currentTimePosition != None:
            self.currentTimePosition += self.timeFrame()
            #self.emit(SIGNAL('timeRestrictionsRefreshed(PyQt_PyObject)'),self.currentTimePosition) 
            self.timeRestrictionsRefreshed.emit(self.currentTimePosition)
        if self.isEnabled():
            self.refresh()

    def stepBackward(self):
        """Shifts query back in time by one time frame"""
        if self.currentTimePosition != None:
            self.currentTimePosition -= self.timeFrame()
            #self.emit(SIGNAL('timeRestrictionsRefreshed(PyQt_PyObject)'),self.currentTimePosition) 
            self.timeRestrictionsRefreshed.emit(self.currentTimePosition)
        if self.isEnabled():
            self.refresh()

    def toggleTimeManagement(self):
        """toggle time management on/off"""
        if self.timeManagementEnabled:
            self.deactivateTimeManagement()
        else:
            self.activateTimeManagement()
        #self.emit(SIGNAL('toggledManagement(PyQt_PyObject)'),self.timeManagementEnabled)
        self.toggledManagement.emit(self.timeManagementEnabled)

    def activateTimeManagement(self):
        """Enable all temporal constraints on managed (and configured) layers. (Original subsets should still be active.)"""
        self.timeManagementEnabled = True
        self.refresh()

    def deactivateTimeManagement(self):
        """Disable all temporal constraints (and restore original subsets)"""
        self.timeManagementEnabled = False
        self.refresh()
        
    def getSaveString(self):
        """create a save string that can be put into project file"""
        tdfmt = "%Y-%m-%d %H:%M:%S.%f"
        saveString = ''
        saveListLayers = []
        
        if len(self.projectTimeExtents) > 0:
            try: # test if projectTimeExtens are populated with datetimes
                datetime.strftime(self.projectTimeExtents[0], tdfmt)
            except TypeError: # if Nonetypes:
                return (saveString,saveListLayers)
                
            saveString  = datetime.strftime(self.projectTimeExtents[0], tdfmt) + ';'
            saveString += datetime.strftime(self.projectTimeExtents[1], tdfmt) + ';'
            saveString += datetime.strftime(self.currentTimePosition, tdfmt) + ';'            

            for timeLayer in self.timeLayerList:
                saveListLayers.append(timeLayer.getSaveString())
        
        return (saveString,saveListLayers)
        
    def restoreFromSaveString(self, saveString):
        """restore settings from loaded project file"""
        tdfmt = "%Y-%m-%d %H:%M:%S.%f"
        if saveString:
            self.isFirstRun = False
            saveString = str(saveString).split(';')
            try:
                timeExtents = (datetime.strptime(saveString[0], tdfmt),
                               datetime.strptime(saveString[1], tdfmt))
            except ValueError:
                try:
                    # Try converting without the fractional seconds for
                    # backward compatibility.
                    tdfmt = "%Y-%m-%d %H:%M:%S"
                    timeExtents = (datetime.strptime(saveString[0], tdfmt),
                                   datetime.strptime(saveString[1], tdfmt))
                except ValueError:
                    # avoid error message for projects without
                    # time-managed layers
                    return
            self.projectTimeExtents = timeExtents
            self.setCurrentTimePosition(datetime.strptime(saveString[2], tdfmt))
            return saveString[3]
