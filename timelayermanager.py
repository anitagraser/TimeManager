#!/usr/bin/python
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from timelayer import NotATimeAttributeError
from time_util import *
import conf
from logging import info

class TimeLayerManager(QObject):
    """Manages all layers that can be queried temporally and provides navigation in time"""

    # the signal for when the current time position is changed
    timeRestrictionsRefreshed = pyqtSignal(datetime)
    # the signal when the start and end time are changed
    projectTimeExtentsChanged = pyqtSignal(object)
    # the signal for when we dont have any layers left managed by TimeManager
    lastLayerRemoved = pyqtSignal()

    def __init__(self,iface):
        QObject.__init__(self)
        self.iface = iface
        self.timeManagementEnabled = True
        self.timeLayerList = []
        self.setProjectTimeExtents((None, None))
        self.setCurrentTimePosition(None)
        self.timeFrameType = conf.DEFAULT_FRAME_UNIT
        self.timeFrameSize = conf.DEFAULT_FRAME_SIZE

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
        """returns the manager's currentTimePosition in datetime format"""
        return self.currentTimePosition
        
    def getTimeFrameType(self):
        """returns the type of the time frame, e.g. minutes, hours, days"""
        return self.timeFrameType
        
    def getTimeFrameSize(self):
        """returns the size of the time frame"""
        return self.timeFrameSize
        
    def getFrameCount(self):
        """returns the number of frames that can be generated using the current settings.
        It's actually an approximate number that errs on the high side."""
        if len(self.getManagedLayers()) == 0 or not self.isEnabled():
            return 0

        try:
            td1 = self.getProjectTimeExtents()[1]-self.getProjectTimeExtents()[0]
        except: # hope this fixes #17 which I still cannot reproduce
            return 0
            
        td2 = self.timeFrame()
        if type(td2) == relativedelta:
            # convert back to timedelta
            # approximately
            td2 = timedelta(weeks=4*td2.months, days=365*td2.years)
        # this is how you can devide two timedeltas (not supported by default):
        us1 = td1.total_seconds()
        us2 = td2.total_seconds()
        
        if us2 == 0:
            raise Exception("Cannot have zero length timeFrame") # this should never happen
            # it's forbidden at UI level
        
        return int(us1 *1.0 / us2)

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
            del timeLayer
        self.timeLayerList = []

    def timeFrame(self):
        """returns the current time frame as datetime.timedelta or compatible dateutil.relativedelta.relativedelta object"""
        if self.timeFrameType == 'years':
            return relativedelta(years=self.timeFrameSize)   # years are not supported by timedelta
        elif self.timeFrameType == 'months':
            return relativedelta(months=self.timeFrameSize)  # months are not supported by timedelta
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
        elif self.timeFrameType == 'milliseconds':
            return timedelta(milliseconds=self.timeFrameSize)
        elif self.timeFrameType == 'microseconds':
            return timedelta(microseconds=self.timeFrameSize)

    def refreshTimeRestrictions(self):
        """Refresh the subset strings of all enabled layers"""
        if not self.hasLayers():
            return
        if self.isEnabled():
            for timeLayer in self.getTimeLayerList():
                    timeLayer.setTimeRestriction(self.getCurrentTimePosition(),self.timeFrame())
        else:
            for timeLayer in self.getTimeLayerList():
                if not timeLayer.hasTimeRestriction():
                    continue
                timeLayer.deleteTimeRestriction()

        self.timeRestrictionsRefreshed.emit(self.getCurrentTimePosition())
                
    def registerTimeLayer( self, timeLayer ):
            """Register a new layer for management and update the project's temporal extent"""
            info("Registering time layer {} at {}".format(timeLayer.getLayerId(), datetime.now()))
            self.getTimeLayerList().append( timeLayer )
            if self.getCurrentTimePosition() is None:
                self.setCurrentTimePosition(timeLayer.getTimeExtents()[0])
            self.updateProjectTimeExtents()
            self.refreshTimeRestrictions()

    def removeTimeLayer(self,layerId):
        """remove the timeLayer with the given layerId"""
        for i in range(0,len(self.getTimeLayerList())):
            if self.getTimeLayerList()[i].getLayerId() == layerId:
                self.getTimeLayerList().pop(i)
                break
        # if the last layer was removed:
        if not self.hasLayers():
            self.setProjectTimeExtents((None,None))
            self.setCurrentTimePosition(None)
            #self.emit(SIGNAL('lastLayerRemoved()'),)
            self.lastLayerRemoved.emit()
        else:
            self.updateProjectTimeExtents()
        self.refreshTimeRestrictions()

    def updateProjectTimeExtents(self):
        """Loop through all timeLayers and make sure that the projectTimeExtents cover all layers"""
        for i,timeLayer in enumerate(self.getTimeLayerList()):
            try:
                extents = timeLayer.getTimeExtents()
                if i==0:
                    self.setProjectTimeExtents(timeLayer.getTimeExtents())
                    continue
            except NotATimeAttributeError, e:
                raise Exception(str(e))
            start = min(self.getProjectTimeExtents()[0],extents[0])
            end = max(self.getProjectTimeExtents()[1], extents[1])
            self.setProjectTimeExtents((start,end))


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
        """Defines the type of the time frame, accepts all values usable by timedelta/relativedelta objects:
        days, seconds, microseconds, milliseconds, minutes, hours, weeks, months, years"""
        self.timeFrameType = frameType
        self.refreshTimeRestrictions()

    def setTimeFrameSize( self, frameSize ):
        """Defines the size of the time frame"""
        self.timeFrameSize = frameSize
        self.refreshTimeRestrictions()

    def setCurrentTimePosition( self, timePosition ):
        """Sets the currently selected point in time (a datetime), which is at the beginning of
        the time-frame."""
        if timePosition is not None and type(timePosition)!=datetime:
            raise Exception("Expected datetime got {} of type {} instead".format(timePosition,
                                                                                 type(timePosition)))
        self.currentTimePosition = timePosition
        if self.isEnabled():
            self.refreshTimeRestrictions()

    def stepForward(self):
        """Shifts query forward in time by one time frame"""
        if self.getCurrentTimePosition() != None and self.isEnabled():
            self.setCurrentTimePosition(self.getCurrentTimePosition() + self.timeFrame())

    def stepBackward(self):
        """Shifts query back in time by one time frame"""
        if self.getCurrentTimePosition() != None and self.isEnabled():
            self.setCurrentTimePosition(self.getCurrentTimePosition() - self.timeFrame())

    def toggleTimeManagement(self):
        """toggle time management on/off"""
        if self.isEnabled():
            self.deactivateTimeManagement()
        else:
            self.activateTimeManagement()

    def activateTimeManagement(self):
        """Enable all temporal constraints on managed (and configured) layers. (Original subsets should still be active.)"""
        self.timeManagementEnabled = True
        self.refreshTimeRestrictions()

    def deactivateTimeManagement(self):
        """Disable all temporal constraints (and restore original subsets)"""
        self.timeManagementEnabled = False
        self.refreshTimeRestrictions()

    def getSaveString(self):
        """create a save string that can be put into project file"""
        tdfmt = SAVE_STRING_FORMAT
        saveListLayers = []

        try: # test if projectTimeExtens are populated with datetimes
            datetime_to_str(self.getProjectTimeExtents()[0], tdfmt)
        except:
            return (None,None)

        saveString = conf.SAVE_DELIMITER.join([datetime_to_str(self.getProjectTimeExtents()[0],tdfmt),
            datetime_to_str(self.getProjectTimeExtents()[1], tdfmt),
            datetime_to_str(self.getCurrentTimePosition())])
        for timeLayer in self.getTimeLayerList():
            saveListLayers.append(timeLayer.getSaveString())
        
        return (saveString,saveListLayers)
        
    def restoreFromSaveString(self, saveString):
        """restore settings from loaded project file"""
        tdfmt = SAVE_STRING_FORMAT
        if saveString:
            saveString = str(saveString).split(conf.SAVE_DELIMITER)
            try:
                timeExtents = (str_to_datetime(saveString[0], tdfmt),
                               str_to_datetime(saveString[1], tdfmt))
            except:
                try:
                    # Try converting without the fractional seconds for
                    # backward compatibility.
                    tdfmt = DEFAULT_FORMAT
                    timeExtents = (str_to_datetime(saveString[0], tdfmt),
                                   str_to_datetime(saveString[1], tdfmt))
                except:
                    # avoid error message for projects without
                    # time-managed layers
                    return
            self.setProjectTimeExtents(timeExtents)
            pos = str_to_datetime(saveString[2], tdfmt)
            self.setCurrentTimePosition(pos)

    def haveVisibleFeatures(self):
        """Return true if at least one of the time managed layers
        which are not ignored for emptiness detection in the project has
        featureCount>0"""
        all_layers = map(lambda x: x.layer,filter(lambda x: x.isEnabled() and x.geometriesCountForExport(),
                                                  self.getTimeLayerList()))
        total_features = 0
        for layer in all_layers:
            total_features+=layer.featureCount()
        return total_features>0
