# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 18:33:13 2012

@author: Anita
"""

from datetime import timedelta

from timelayer import *
from time_util import str_to_datetime
import conf


class TimeRasterLayer(TimeLayer):
    def __init__(self, settings, iface=None):
        TimeLayer.__init__(self, settings.layer, settings.isEnabled)
        self.layer = settings.layer
        self.fromTimeAttribute = settings.startTimeAttribute
        self.toTimeAttribute = settings.endTimeAttribute if settings.endTimeAttribute != "" else self.fromTimeAttribute
        self.timeFormat = self.determine_format(settings.startTimeAttribute, settings.timeFormat)
        self.offset = int(settings.offset)

        try:
            self.getTimeExtents()
        except NotATimeAttributeError, e:
            raise InvalidTimeLayerError(e)

    def hasSubsetStr(self):
        return False

    def accumulateFeatures(self):
        return False

    def getTimeAttributes(self):
        """return the tuple of timeAttributes (fromTimeAttribute,toTimeAttribute)"""
        return (self.fromTimeAttribute, self.toTimeAttribute)

    def getTimeFormat(self):
        """returns the layer's time format"""
        return self.timeFormat

    def getOffset(self):
        """returns the layer's offset, integer in seconds"""
        return self.offset

    def getTimeExtents(self):
        """Get layer's temporal extent using the fields and the format defined somewhere else!"""
        startStr = self.fromTimeAttribute
        endStr = self.toTimeAttribute
        startTime = str_to_datetime(startStr, self.getTimeFormat())
        endTime = str_to_datetime(endStr, self.getTimeFormat())
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return (startTime, endTime)

    def setTimeRestriction(self, timePosition, timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return

        startTime = timePosition + timedelta(seconds=self.offset)
        endTime = timePosition + timeFrame + timedelta(seconds=self.offset)
        layerStartTime = str_to_datetime(self.fromTimeAttribute, self.getTimeFormat())
        layerEndTime = str_to_datetime(self.toTimeAttribute, self.getTimeFormat())
        self.hideOrShowLayer(startTime, endTime, layerStartTime, layerEndTime)

    def hideOrShowLayer(self, startTime, endTime, layerStartTime, layerEndTime):
        if layerStartTime < endTime and layerEndTime >= startTime:
            # if the timestamp is within the extent --> show the raster
            self.show()
        else:  # hide the raster
            self.hide()

    def hide(self):
        self.layer.renderer().setOpacity(0)

    def show(self):
        self.layer.renderer().setOpacity(1)

    def deleteTimeRestriction(self):
        """The layer is removed from Time Manager and is therefore always shown"""
        self.show()

    def hasTimeRestriction(self):
        """returns true if current layer.subsetString is not equal to originalSubsetString"""
        return True  # self.layer.subsetString != self.originalSubsetString

    def getSaveString(self):
        """get string to save in project file"""
        delimiter = conf.SAVE_DELIMITER
        return delimiter.join([self.getLayerId(), '', self.fromTimeAttribute, self.toTimeAttribute,
                               str(self.timeEnabled),
                               self.timeFormat, str(self.offset)])
