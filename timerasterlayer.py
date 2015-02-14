# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 18:33:13 2012

@author: Anita
"""


from datetime import datetime, timedelta
from qgis.core import *
from timelayer import *
from time_util import SUPPORTED_FORMATS, DEFAULT_FORMAT, strToDatetimeWithFormatHint, getFormatOfDatetimeValue

class TimeRasterLayer(TimeLayer):
    def __init__(self,layer,fromTimeAttribute="",toTimeAttribute="",enabled=True,
                 timeFormat=DEFAULT_FORMAT,offset=0, iface=None, **kwargs):
        TimeLayer.__init__(self,layer,enabled)
        
        self.layer = layer
        self.iface = iface
        self.fromTimeAttribute = fromTimeAttribute
        self.toTimeAttribute = toTimeAttribute
        self.timeFormat = getFormatOfDatetimeValue(fromTimeAttribute, hint=timeFormat)
        self.supportedFormats = SUPPORTED_FORMATS
        self.offset = int(offset)
        
        try:
            self.getTimeExtents()
        except NotATimeAttributeError, e:
            raise InvalidTimeLayerError(e)
            
    def getTimeAttributes(self):
        """return the tuple of timeAttributes (fromTimeAttribute,toTimeAttribute)"""
        return(self.fromTimeAttribute,self.toTimeAttribute)

    def getTimeFormat(self):
        """returns the layer's time format"""
        return self.timeFormat
        
    def getOffset(self):
        """returns the layer's offset, integer in seconds"""
        return self.offset

    def getTimeExtents( self ):
        """Get layer's temporal extent using the fields and the format defined somewhere else!"""
        startStr = self.fromTimeAttribute
        endStr = self.toTimeAttribute
        try:
            startTime = strToDatetimeWithFormatHint(startStr, self.getTimeFormat())
        except ValueError:
            raise NotATimeAttributeError(str(self.fromTimeAttribute)+': The attribute specified for use as start time contains invalid data:\n\n'+startStr+'\n\nis not one of the supported formats:\n'+str(self.supportedFormats))
        try:
            endTime = strToDatetimeWithFormatHint(endStr, self.getTimeFormat())
        except ValueError:
            raise NotATimeAttributeError(str(self.toTimeAttribute)+': The attribute specified for use as end time contains invalid data:\n'+endStr)
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return (startTime,endTime)

    def setTimeRestriction(self,timePosition,timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return

        startTime = timePosition + timedelta(seconds=self.offset)
        endTime = timePosition + timeFrame + timedelta(seconds=self.offset)

        if strToDatetimeWithFormatHint(self.fromTimeAttribute, self.getTimeFormat()) < endTime and strToDatetimeWithFormatHint(self.toTimeAttribute, self.getTimeFormat()) >= startTime:
            # if the timestamp is within the extent --> show the raster
            self.layer.renderer().setOpacity(1) # no transparency  
        else: # hide the raster
            self.layer.renderer().setOpacity(0)   # total transparency
            
    def deleteTimeRestriction(self):
        """The layer is removed from Time Manager and is therefore always shown"""
        self.layer.renderer().setOpacity(1)

    def hasTimeRestriction(self):
        """returns true if current layer.subsetString is not equal to originalSubsetString"""
        return True #self.layer.subsetString != self.originalSubsetString
        
    def getSaveString(self):
        """get string to save in project file"""
        delimiter = ';'
        saveString = self.getLayerId() + delimiter
        saveString += '' + delimiter
        saveString += self.fromTimeAttribute + delimiter
        saveString += self.toTimeAttribute + delimiter
        saveString += str(self.timeEnabled) + delimiter
        saveString += self.timeFormat + delimiter
        saveString += str(self.offset)
        return saveString
