#!/usr/bin/python
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from timelayer import NotATimeAttributeError
from time_util import *

class TimeLayerManager(QObject):
    """Class manages all layers that can be queried temporally and provides navigation in time. Parenthesized sections are not implemented yet. All functions, besides the get functions, trigger a redraw."""

    # the signal for when the current time position is changed
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
        for timeLayer in self.getTimeLayerList():
            layerList.append(timeLayer.layer)
        return layerList

    def getCurrentTimePosition(self):
        """returns the manager's currentTimePosition"""
        return self.currentTimePosition
        
    def debug(self, msg):
        QMessageBox.information(self.iface.mainWindow(),'Info', msg)

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
        if len(self.getTimeLayerList()) > 0:
            return True
        else:
            return False

    def hasActiveLayers(self):
        """returns true if the manager has at least one layer registered"""
        if len(self.getTimeLayerList()) > 0:
            for layer in self.getTimeLayerList():
                if layer.isEnabled():
                    return True
        return False

    def clearTimeLayerList(self):
        """clear the timeLayerList"""
        for timeLayer in self.getTimeLayerList():
            timeLayer.deleteTimeRestriction()
        self.timeLayerList = []

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
            for timeLayer in self.getTimeLayerList():
                #try:
                    timeLayer.setTimeRestriction(self.currentTimePosition,self.timeFrame())
                #except AttributeError: # if timeLayer is of NoneType
                #    pass
        else:
            for timeLayer in self.getTimeLayerList():
                if not timeLayer.hasTimeRestriction():
                    return
                timeLayer.deleteTimeRestriction()

        self.timeRestrictionsRefreshed.emit(self.currentTimePosition)
                
    def registerTimeLayer( self, timeLayer ):
        """Register a new layer for management and update the project's temporal extent"""
        self.getTimeLayerList().append( timeLayer )
        ##self.debug("registering timelayer")
        if len( self.getTimeLayerList() ) == 1:
            # update projectTimeExtents to first layer's timeExtents
            ##self.debug("will set time extents to {}".format(timeLayer.getTimeExtents()))
            self.setProjectTimeExtents(timeLayer.getTimeExtents())

            ##self.debug("updated project time extents to {}".format(timeLayer.getTimeExtents()))

            # Set current time to the earliest time record
            if self.isFirstRun:

                ##self.debug("!!!!!!!current pos:"+str(timeLayer.getTimeExtents()[0]))
                self.setCurrentTimePosition(timeLayer.getTimeExtents()[0])
                ##self.debug("start of layer when registering time layer:"+str(self.getCurrentTimePosition()))
                self.isFirstRun = False
        else:
            self.updateProjectTimeExtents()
        self.refresh()


    def removeTimeLayer(self,layerId):
        """remove the timeLayer with the given layerId"""
        for i in range(0,len(self.getTimeLayerList())):
            if self.getTimeLayerList()[i].getLayerId() == layerId:
                self.getTimeLayerList().pop(i)
                break

                
        # if the last layer was removed:
        if not self.hasLayers():
            self.setProjectTimeExtents((None,None))
            #self.emit(SIGNAL('lastLayerRemoved()'),)
            self.lastLayerRemoved.emit()
        else:
            self.updateProjectTimeExtents()
        self.refresh()

    def updateProjectTimeExtents(self):
        """Loop through all timeLayers and make sure that the projectTimeExtents cover all layers"""
        for i,timeLayer in enumerate(self.getTimeLayerList()):
            try:
                extents = timeLayer.getTimeExtents()
                if i==0:
                    self.setProjectTimeExtents(timeLayer.getTimeExtents())
                    continue
            except NotATimeAttributeError:
                continue # TODO: we should probably show something informative here
            if extents[0] < self.projectTimeExtents[0]:
                extents = (extents[0],self.projectTimeExtents[1])
            if extents[1] > self.projectTimeExtents[1]:
                extents = (self.projectTimeExtents[0],extents[1])

        self.setProjectTimeExtents(extents) # this fires the event that the extents where changed
        #self.debug("new project time extents:{}".format(self.projectTimeExtents))

    def setProjectTimeExtents(self,timeExtents):
        """set projectTimeExtents to given time extent and emit signal 'projectTimeExtentsChanged(list)'"""
        self.projectTimeExtents = timeExtents
        self.projectTimeExtentsChanged.emit(timeExtents)


    def getProjectTimeExtents( self ):
        """Get the overall temporal extent of all managable (managed?) layers"""
        return self.projectTimeExtents
    
    def getTimeLayerList( self ):
        """Get the list of time layers"""
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
        """Sets the currently selected point in time (a datetime), which is at the beginning of
        the time-frame."""
        if type(timePosition)!=datetime:
            raise Exception("Expected datetime got {} of type {} instead".format(timePosition,
                                                                                 type(timePosition)))
        self.currentTimePosition = timePosition
        self.timeRestrictionsRefreshed.emit(self.currentTimePosition)
        if self.isEnabled():
            self.refresh()

    def stepForward(self):
        """Shifts query forward in time by one time frame"""
        if self.currentTimePosition != None:
            self.currentTimePosition += self.timeFrame()
            self.timeRestrictionsRefreshed.emit(self.currentTimePosition)
        if self.isEnabled():
            self.refresh()

    def stepBackward(self):
        """Shifts query back in time by one time frame"""
        if self.currentTimePosition != None:
            self.currentTimePosition -= self.timeFrame()
            self.timeRestrictionsRefreshed.emit(self.currentTimePosition)
        if self.isEnabled():
            self.refresh()

    def toggleTimeManagement(self):
        #FIXME this doesnt work as expected
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
        tdfmt = SAVE_STRING_FORMAT
        saveString = ''
        saveListLayers = []
        
        if len(self.projectTimeExtents) > 0:
            try: # test if projectTimeExtens are populated with datetimes
                datetime_to_str(self.projectTimeExtents[0], tdfmt)
            except TypeError: # if Nonetypes:
                return (saveString,saveListLayers)
                
            saveString  = datetime_to_str(self.projectTimeExtents[0], tdfmt) + ';'
            saveString += datetime_to_str(self.projectTimeExtents[1], tdfmt) + ';'

            saveString += datetime_to_str(self.currentTimePosition, tdfmt) + ';'            
            ##self.debug("save string:"+saveString)
            for timeLayer in self.getTimeLayerList():
                saveListLayers.append(timeLayer.getSaveString())
        
        return (saveString,saveListLayers)
        
    def restoreFromSaveString(self, saveString):
        """restore settings from loaded project file"""
        tdfmt = SAVE_STRING_FORMAT
        if saveString:
            self.isFirstRun = False
            saveString = str(saveString).split(';')
            try:
                timeExtents = (datetime_to_str(saveString[0], tdfmt),
                               datetime_to_str(saveString[1], tdfmt))
            except ValueError:
                try:
                    # Try converting without the fractional seconds for
                    # backward compatibility.
                    tdfmt = DEFAULT_FORMAT
                    timeExtents = (datetime_to_str(saveString[0], tdfmt),
                                   datetime_to_str(saveString[1], tdfmt))
                except ValueError:
                    # avoid error message for projects without
                    # time-managed layers
                    return
            self.setProjectTimeExtents(timeExtents)
            pos = datetime_to_str(saveString[2], tdfmt)
            ##self.debug("tlmanager: set current time position to:"+str(pos))
            self.setCurrentTimePosition(pos)
            return saveString[3]
