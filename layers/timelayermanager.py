#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import
from builtins import str
from builtins import range

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from qgis.PyQt.QtCore import QObject, pyqtSignal

from timemanager.layers.timelayer import NotATimeAttributeError
from timemanager.utils.tmlogging import log_exceptions

from timemanager import conf
from timemanager.utils import qgis_utils as qgs, time_util


class TimeLayerManager(QObject):
    """Manages all layers that can be queried temporally and provides navigation in time"""

    # the signal for when the current time position is changed
    timeRestrictionsRefreshed = pyqtSignal(object)
    # the signal when the start and end time are changed
    projectTimeExtentsChanged = pyqtSignal(object)
    # the signal for when we don't have any layers left managed by TimeManager
    lastLayerRemoved = pyqtSignal()

    def __init__(self, iface):
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

        extents = self.getProjectTimeExtents()
        return time_util.get_frame_count(extents[0], extents[1], self.timeFrame())

    def hasLayers(self):
        """returns true if the manager has at least one layer registered"""
        return len(self.getTimeLayerList()) > 0

    def hasActiveLayers(self):
        """returns true if the manager has at least one active layer registered"""
        return len([x for x in self.getTimeLayerList() if x.isEnabled()]) > 0

    def clearTimeLayerList(self):
        """clear the timeLayerList"""
        for timeLayer in self.getTimeLayerList():
            timeLayer.deleteTimeRestriction()
            del timeLayer
        self.timeLayerList = []

    def timeFrame(self):
        """Returns the current time frame as datetime.timedelta
        or compatible dateutil.relativedelta.relativedelta object.
        But when self.timeFrameSize is 0 (that is not working with frames but with
        moments (eg possible in some wms-t services) return the timeframe of
        1 (one timeFrameType). That makes it possible to set the timeFrameSize
        to zero but still go over the timerange in steps of 1 timeFrameType."""
        timeFrameSize = self.timeFrameSize
        if self.timeFrameSize == 0:
            timeFrameSize = 1  # so we can still step in steps of 'timeFrameType'
        if self.timeFrameType == 'years':
            return relativedelta(years=timeFrameSize)  # years are not supported by timedelta
        elif self.timeFrameType == 'months':
            return relativedelta(
                months=self.timeFrameSize)  # months are not supported by timedelta
        elif self.timeFrameType == 'weeks':
            return timedelta(weeks=timeFrameSize)
        elif self.timeFrameType == 'days':
            return timedelta(days=timeFrameSize)
        elif self.timeFrameType == 'hours':
            return timedelta(hours=timeFrameSize)
        elif self.timeFrameType == 'minutes':
            return timedelta(minutes=timeFrameSize)
        elif self.timeFrameType == 'seconds':
            return timedelta(seconds=timeFrameSize)
        elif self.timeFrameType == 'milliseconds':
            return timedelta(milliseconds=timeFrameSize)
        elif self.timeFrameType == 'microseconds':
            return timedelta(microseconds=timeFrameSize)

    @log_exceptions
    def refreshTimeRestrictions(self):
        """Refresh the subset strings of all enabled layers"""
        if not self.hasLayers():
            return
        if self.isEnabled():
            for timeLayer in self.getTimeLayerList():
                if self.timeFrameSize == 0:
                    timeLayer.setTimeRestriction(self.getCurrentTimePosition(),  timedelta(0))
                else:
                    timeLayer.setTimeRestriction(self.getCurrentTimePosition(), self.timeFrame())
        else:
            for timeLayer in self.getTimeLayerList():
                if not timeLayer.hasTimeRestriction():
                    continue
                timeLayer.deleteTimeRestriction()

        self.timeRestrictionsRefreshed.emit(self.getCurrentTimePosition())

    @log_exceptions
    def registerTimeLayer(self, timeLayer):
        """Register a new layer for management and update the project's temporal extent"""
        self.getTimeLayerList().append(timeLayer)
        if self.getCurrentTimePosition() is None:
            self.setCurrentTimePosition(timeLayer.getTimeExtents()[0])
            # info("Set the time position to {}".format(self.getCurrentTimePosition()))
        self.updateProjectTimeExtents()
        self.refreshTimeRestrictions()

    def removeTimeLayer(self, layerId):
        """remove the timeLayer with the given layerId"""
        for i in range(len(self.getTimeLayerList())):
            if self.getTimeLayerList()[i].getLayerId() == layerId:
                self.getTimeLayerList().pop(i)
                break
        # if the last layer was removed:
        if not self.hasLayers():
            self.setProjectTimeExtents((None, None))
            self.setCurrentTimePosition(None)
            # self.emit(SIGNAL('lastLayerRemoved()'),)
            self.lastLayerRemoved.emit()
        else:
            self.updateProjectTimeExtents()
        self.refreshTimeRestrictions()

    @log_exceptions
    def updateProjectTimeExtents(self):
        """Loop through all timeLayers and make sure that the projectTimeExtents cover all layers"""
        for i, timeLayer in enumerate(self.getTimeLayerList()):
            try:
                extents = timeLayer.getTimeExtents()
                if i == 0:
                    self.setProjectTimeExtents(timeLayer.getTimeExtents())
                    continue
            except NotATimeAttributeError as e:
                raise Exception(str(e))
            start = min(self.getProjectTimeExtents()[0], extents[0])
            end = max(self.getProjectTimeExtents()[1], extents[1])
            self.setProjectTimeExtents((start, end))

    def setProjectTimeExtents(self, timeExtents):
        """set projectTimeExtents to given time extent and emit signal 'projectTimeExtentsChanged(list)'"""
        self.projectTimeExtents = timeExtents
        self.projectTimeExtentsChanged.emit(timeExtents)

    def getProjectTimeExtents(self):
        """Get the overall temporal extent of all managable (managed?) layers"""
        return self.projectTimeExtents

    def getTimeLayerList(self):
        """Get the list of time layers"""
        return self.timeLayerList

    def setTimeFrameType(self, frameType):
        """Defines the type of the time frame, accepts all values usable by timedelta/relativedelta objects:
        days, seconds, microseconds, milliseconds, minutes, hours, weeks, months, years"""
        self.timeFrameType = frameType
        self.refreshTimeRestrictions()

    def setTimeFrameSize(self, frameSize):
        """Defines the size of the time frame"""
        self.timeFrameSize = frameSize
        self.refreshTimeRestrictions()

    @log_exceptions
    def setCurrentTimePosition(self, timePosition):
        """Sets the currently selected point in time (a datetime), which is at the beginning of
        the time-frame."""
        if timePosition is not None and not time_util.is_date_object(timePosition):
            raise Exception("Expected datetime got {} of type {} instead".format(timePosition,
                                                                                 type(
                                                                                     timePosition)))
        self.currentTimePosition = timePosition
        if self.isEnabled():
            self.refreshTimeRestrictions()

    @log_exceptions
    def stepForward(self):
        """Shifts query forward in time by one time frame"""
        if self.getCurrentTimePosition() is not None and self.isEnabled():
            self.setCurrentTimePosition(self.getCurrentTimePosition() + self.timeFrame())

    @log_exceptions
    def stepBackward(self):
        """Shifts query back in time by one time frame"""
        if self.getCurrentTimePosition() is not None and self.isEnabled():
            self.setCurrentTimePosition(self.getCurrentTimePosition() - self.timeFrame())

    def toggleTimeManagement(self):
        """toggle time management on/off"""
        if self.isEnabled():
            self.deactivateTimeManagement()
        else:
            self.activateTimeManagement()

    def activateTimeManagement(self):
        """Enable all temporal constraints on managed (and configured) layers.
        (Original subsets should still be active.)"""
        self.timeManagementEnabled = True
        self.refreshTimeRestrictions()

    def deactivateTimeManagement(self):
        """Disable all temporal constraints (and restore original subsets)"""
        self.timeManagementEnabled = False
        self.refreshTimeRestrictions()

    def getSaveString(self):
        """create a save string that can be put into project file"""
        tdfmt = time_util.SAVE_STRING_FORMAT
        saveListLayers = []

        try:  # test if projectTimeExtens are populated with datetimes
            time_util.datetime_to_str(self.getProjectTimeExtents()[0], tdfmt)
        except Exception:
            return (None, None)

        saveString = conf.SAVE_DELIMITER.join(
            [time_util.datetime_to_str(self.getProjectTimeExtents()[0], tdfmt),
             time_util.datetime_to_str(self.getProjectTimeExtents()[1], tdfmt),
             time_util.datetime_to_str(self.getCurrentTimePosition(), tdfmt)])
        for timeLayer in self.getTimeLayerList():
            saveListLayers.append(timeLayer.getSaveString())

        return (saveString, saveListLayers)

    def restoreFromSaveString(self, saveString):
        """restore settings from loaded project file"""
        tdfmt = time_util.SAVE_STRING_FORMAT
        if saveString:
            saveString = str(saveString).split(conf.SAVE_DELIMITER)
            try:
                timeExtents = (time_util.str_to_datetime(saveString[0], tdfmt),
                               time_util.str_to_datetime(saveString[1], tdfmt))
            except Exception:
                try:
                    # Try converting without the fractional seconds for
                    # backward compatibility.
                    tdfmt = time_util.DEFAULT_FORMAT
                    timeExtents = (time_util.str_to_datetime(saveString[0], tdfmt),
                                   time_util.str_to_datetime(saveString[1], tdfmt))
                except Exception:
                    # avoid error message for projects without
                    # time-managed layers
                    return
            self.setProjectTimeExtents(timeExtents)
            pos = time_util.str_to_datetime(saveString[2], tdfmt)
            self.setCurrentTimePosition(pos)

    def haveVisibleFeatures(self):
        """Return true if at least one of the time managed layers
        which are not ignored for emptiness detection in the project has
        featureCount>0 (or if we have active raster layers)"""
        all_layers = [x.layer for x in [x for x in self.getTimeLayerList() if x.isEnabled() and (not qgs.isRaster(x.layer)) and x.geometriesCountForExport()]]
        total_features = 0
        for layer in all_layers:
            total_features += layer.featureCount()
        return total_features > 0 or self.getActiveRasters()

    def getActive(self, func=lambda x: True):
        return [x for x in self.getTimeLayerList() if func(x) and x.isEnabled()]

    def getActiveRasters(self):
        return self.getActive(func=lambda x: qgs.isRaster(x.layer))

    def getActiveVectors(self):
        return self.getActive(func=lambda x: not qgs.isRaster(x.layer))

    def getActiveDelimitedText(self):
        return self.getActive(func=lambda x: qgs.isDelimitedText(x.layer))

    def layers(self):
        return self.getTimeLayerList()
