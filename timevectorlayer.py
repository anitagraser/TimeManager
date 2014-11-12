# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 17:28:19 2012

@author: Anita
"""

from PyQt4 import QtCore
from datetime import datetime, timedelta
from qgis.core import *
from timelayer import *
from time_util import strToDatetime, getFormatOfStr, DEFAULT_FORMAT, UTC, SUPPORTED_FORMATS

class TimeVectorLayer(TimeLayer):
    def __init__(self,layer,fromTimeAttribute,toTimeAttribute,enabled=True,timeFormat="%Y-%m-%d %H:%M:%S",offset=0):
        TimeLayer.__init__(self,layer,enabled)
        
        self.layer = layer
        self.fromTimeAttribute = fromTimeAttribute
        self.toTimeAttribute = toTimeAttribute
        self.timeEnabled = enabled
        self.originalSubsetString = self.layer.subsetString()
       # self.timeFormat = str(timeFormat) # cast in case timeFormat comes as a QString
        self.supportedFormats = SUPPORTED_FORMATS
        if timeFormat not in self.supportedFormats:
            self.supportedFormats.append(timeFormat)
        self.offset = int(offset)
        self.timeFormat = getFormatOfStr(fromTimeAttribute, timeFormat)
        self.fromTimeAttribute = fromTimeAttribute
        self.toTimeAttribute = toTimeAttribute
        try:
            self.getTimeExtents()
        except NotATimeAttributeError, e:
            raise InvalidTimeLayerError(e.value)

            
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
        provider=self.layer.dataProvider()
        fromTimeAttributeIndex = provider.fieldNameIndex(self.fromTimeAttribute)
        toTimeAttributeIndex = provider.fieldNameIndex(self.toTimeAttribute)
        minValue = provider.minimumValue(fromTimeAttributeIndex)
        maxValue = provider.maximumValue(toTimeAttributeIndex)
        if type(minValue) is QtCore.QDate:
            startTime = datetime.combine(minValue.toPyDate(), datetime.min.time())
            endTime = datetime.combine(maxValue.toPyDate(), datetime.min.time())
        else:
            startStr = str(minValue)
            endStr = str(maxValue)
            try:
                startTime = strToDatetime(startStr, self.getTimeFormat())
            except ValueError:
                raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as start time contains invalid data:\n\n'+startStr+'\n\nis not one of the supported formats:\n'+str(self.supportedFormats))
            try:
                endTime = strToDatetime(endStr, self.getTimeFormat())
            except ValueError:
                raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as end time contains invalid data:\n'+endStr)
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return (startTime,endTime)


    def setTimeRestrictionForInts(self,timePosition,timeFrame):
        """Constructs the query, including the original subset when dealing with int timestamps"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return
        startTime = timePosition + timedelta(seconds=self.offset)
        endTime =timePosition + timeFrame + timedelta(seconds=self.offset)
        fromTime, toTime = self.getTimeExtents()
        startTime = datetime.strftime(startTime, DEFAULT_FORMAT)
        endTime = datetime.strftime(endTime, DEFAULT_FORMAT)
        toTime = datetime.strftime(toTime, DEFAULT_FORMAT)
        fromTime = datetime.strftime(fromTime, DEFAULT_FORMAT)
        if self.originalSubsetString == "":
            subsetString = "\"%s\" < '%s' AND \"%s\" >= '%s' " % ( fromTime,endTime,toTime,startTime)
        else:
            subsetString = "%s AND \"%s\" < '%s' AND \"%s\" >= '%s' " % ( self.originalSubsetString,fromTime,endTime,toTime,startTime)
        self.layer.setSubsetString( subsetString )


    def setTimeRestriction(self,timePosition,timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return
        if self.getTimeFormat()!=UTC:
            startTime = datetime.strftime(timePosition + timedelta(seconds=self.offset),self.timeFormat)
            endTime = datetime.strftime((timePosition + timeFrame + timedelta(seconds=self.offset)),self.timeFormat)
            toTime = self.toTimeAttribute
            fromTime = self.fromTimeAttribute
        else:
            startTime = datetime.strftime(timePosition + timedelta(seconds=self.offset), DEFAULT_FORMAT)
            endTime = datetime.strftime((timePosition + timeFrame + timedelta(seconds=self.offset)),DEFAULT_FORMAT)
            toTime = datetime.strftime(strToDatetime(self.toTimeAttribute, self.getTimeFormat()), DEFAULT_FORMAT)
            fromTime = datetime.strftime(strToDatetime(self.fromTimeAttribute,  self.getTimeFormat()), DEFAULT_FORMAT)

        if self.layer.dataProvider().storageType() == 'PostgreSQL database with PostGIS extension':
            if self.originalSubsetString == "":
                subsetString = "\"%s\" < '%s' AND \"%s\" >= '%s' " % ( fromTime,endTime,toTime,startTime)
            else:
                subsetString = "%s AND \"%s\" < '%s' AND \"%s\" >= '%s' " % ( self.originalSubsetString,fromTime,endTime,toTime,startTime)
        else:
            if self.originalSubsetString == "":
                subsetString = "cast(\"%s\" as character) < '%s' AND cast(\"%s\" as character) >= '%s' " % ( self.fromTimeAttribute,endTime,self.toTimeAttribute,startTime)
            else:
                subsetString = "%s AND cast(\"%s\" as character) < '%s' AND cast(\"%s\" as character) >= '%s' " % ( self.originalSubsetString,self.fromTimeAttribute,endTime,self.toTimeAttribute,startTime)
        self.layer.setSubsetString( subsetString )
        #QMessageBox.information(self.iface.mainWindow(),"Test Output",subsetString)

    def deleteTimeRestriction(self):
        """Restore original subset"""
        self.layer.setSubsetString( self.originalSubsetString )

    def hasTimeRestriction(self):
        """returns true if current layer.subsetString is not equal to originalSubsetString"""
        return self.layer.subsetString != self.originalSubsetString
        
    def getSaveString(self):
        """get string to save in project file"""
        delimiter = ';'
        saveString = self.getLayerId() + delimiter
        saveString += self.originalSubsetString + delimiter
        saveString += self.fromTimeAttribute + delimiter
        saveString += self.toTimeAttribute + delimiter
        saveString += str(self.timeEnabled) + delimiter
        saveString += self.timeFormat + delimiter
        saveString += str(self.offset)
        return saveString
