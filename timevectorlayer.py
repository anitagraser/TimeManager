# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 17:28:19 2012

@author: Anita
"""

from PyQt4 import QtCore
from datetime import datetime, timedelta
from qgis.core import *
from PyQt4.QtGui import QMessageBox
from timelayer import *
from time_util import SUPPORTED_FORMATS, DEFAULT_FORMAT, strToDatetimeWithFormatHint, \
    getFormatOfDatetimeValue, UTC, datetime_to_epoch, datetime_to_str, datetime_at_start_of_day, \
    datetime_at_end_of_day, QDateTime_to_datetime, OGR_DATE_FORMAT, OGR_DATETIME_FORMAT

POSTGRES_TYPE='PostgreSQL database with PostGIS extension'
DELIMITED_TEXT_TYPE='Delimited text file'

# Queries
STRINGCAST_FORMAT='cast("{}" as character) < \'{}\' AND cast("{}" as character) >= \'{}\' '
INT_FORMAT="{} < {} AND {} >= {} "
STRING_FORMAT="\"{}\" < '{}' AND \"{}\" >= '{}' "

class DateTypes:
    IntegerTimestamps="IntegerTimestamps"
    DatesAsStrings="DatesAsStrings"
    DatesAsQDates="DatesAsQDates"
    DatesAsQDateTimes="DatesAsQDateTimes"

    nonQDateTypes = [IntegerTimestamps,DatesAsStrings]

    @classmethod
    def determine_type(cls, val):
        try:
            int(val)
            return cls.IntegerTimestamps
        except:
            if type(val) is QtCore.QDate:
                return cls.DatesAsQDates
            if type(val) is QtCore.QDateTime:
                return cls.DatesAsQDateTimes
            return cls.DatesAsStrings

    @classmethod
    def get_type_format(cls, typ):
        if typ in cls.nonQDateTypes:
            raise Exception
        else:
            if typ==cls.DatesAsQDates:
                return OGR_DATE_FORMAT
            if typ==cls.DatesAsQDateTimes:
                return OGR_DATETIME_FORMAT
        raise Exception


class SubstringException(Exception):
    pass

class TimeVectorLayer(TimeLayer):
    def __init__(self,layer,fromTimeAttribute,toTimeAttribute,enabled=True,
                 timeFormat=DEFAULT_FORMAT,offset=0, iface=None):
        TimeLayer.__init__(self,layer,enabled)
        
        self.layer = layer
        self.iface = iface
        self.fromTimeAttribute = fromTimeAttribute
        self.toTimeAttribute = toTimeAttribute
        self.timeEnabled = enabled
        self.originalSubsetString = self.layer.subsetString()
        self.type = DateTypes.determine_type(self.getRawMinValue())
        if self.type in DateTypes.nonQDateTypes:
            self.timeFormat = getFormatOfDatetimeValue(self.getMinMaxValues()[0], hint=str(timeFormat))
        else:
            self.timeFormat = DateTypes.get_type_format(self.type)

        self.supportedFormats = SUPPORTED_FORMATS
        self.offset = int(offset)
        try:
            self.getTimeExtents()
        except NotATimeAttributeError, e:
            raise InvalidTimeLayerError(e.value)
        self.fromTimeAttributeType = layer.dataProvider().fields().field(fromTimeAttribute).typeName()
        self.toTimeAttributeType = layer.dataProvider().fields().field(toTimeAttribute).typeName()

    def getDateType(self):
        """return the type of dates this layer has stored"""
        return self.type

    def getTimeAttributes(self):
        """return the tuple of timeAttributes (fromTimeAttribute,toTimeAttribute)"""
        return (self.fromTimeAttribute,self.toTimeAttribute)

    def getTimeFormat(self):
        """returns the layer's time format"""
        return self.timeFormat
        
    def getOffset(self):
        """returns the layer's offset, integer in seconds"""
        return self.offset

    def debug(self, msg):
            QMessageBox.information(self.iface.mainWindow(),'Info', msg)

    def getRawMinValue(self):
        provider = self.layer.dataProvider()
        fromTimeAttributeIndex = provider.fieldNameIndex(self.fromTimeAttribute)
        minValue =  provider.minimumValue(fromTimeAttributeIndex)
        return minValue

    def getMinMaxValues(self):
        """Returns str"""
        provider = self.layer.dataProvider()
        fromTimeAttributeIndex = provider.fieldNameIndex(self.fromTimeAttribute)
        toTimeAttributeIndex = provider.fieldNameIndex(self.toTimeAttribute)
        minValue =  provider.minimumValue(fromTimeAttributeIndex)
        maxValue = provider.maximumValue(toTimeAttributeIndex)
        if type(minValue) in [QtCore.QDate, QtCore.QDateTime]:
            minValue = str(QDateTime_to_datetime(minValue))
            maxValue = str(QDateTime_to_datetime(maxValue))
        return minValue, maxValue

    def getTimeExtents(self):
        """Get layer's temporal extent using the fields and the format defined somewhere else!"""
        startStr, endStr = self.getMinMaxValues()
        try:
            startTime = strToDatetimeWithFormatHint(startStr,  self.getTimeFormat())
        except ValueError:
            raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as start time contains invalid data:\n\n'+startStr+'\n\nis not one of the supported formats:\n'+str(self.supportedFormats))
        try:
            endTime = strToDatetimeWithFormatHint(endStr,  self.getTimeFormat())
        except ValueError:
            raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as end time contains invalid data:\n'+endStr)
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return startTime, endTime


    def setTimeRestrictionInts(self, timePosition, timeFrame):
        """Constucts the query on integer attributes (ie time represented as seconds since the epoch)"""
        startTime = datetime_to_epoch(timePosition + timedelta(seconds=self.offset))
        if self.toTimeAttribute != self.fromTimeAttribute:
            endTime = startTime
        else:
            endTime =  datetime_to_epoch(timePosition + timeFrame + timedelta(seconds=self.offset))

        subsetString = INT_FORMAT.format(self.fromTimeAttribute,endTime,self.toTimeAttribute,
                                      startTime)
        if self.toTimeAttribute != self.fromTimeAttribute:
            """Change < to <= when and end time is specified, otherwise features starting at 15:00 would only 
            be displayed starting from 15:01"""
            subsetString = subsetString.replace('<','<=')
        if self.originalSubsetString != "":
            # Prepend original subset string 
            subsetString = "%s AND %s" % (self.originalSubsetString, subsetString)
        self.layer.setSubsetString(subsetString)


    def setTimeRestriction(self, timePosition, timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return
        if self.timeFormat==UTC:
           self.setTimeRestrictionInts(timePosition, timeFrame)
           return
        startTime = timePosition + timedelta(seconds=self.offset)
        startTimeStr = datetime_to_str(startTime, self.getTimeFormat())
        if self.toTimeAttribute != self.fromTimeAttribute:
            # If an end time attribute is set for the layer, then only show features where the \
            # current time position falls between the feature'sget time from and time to
            # attributes
            endTimeStr = startTimeStr
        else:
            # If no end time attribute has been set for this layer, then show features with a time\
            # attribute which falls somewhere between the current time position and the start
            # position of the next frame"""
            endTime = timePosition + timeFrame + timedelta(seconds=self.offset)
            endTimeStr = datetime_to_str(endTime,  self.getTimeFormat())

        # TODO redesign without need for explicit if?
        # TODO: Postgresql test here
        if self.layer.dataProvider().storageType() == POSTGRES_TYPE or \
                        self.layer.dataProvider().storageType()== DELIMITED_TEXT_TYPE:
            # Use PostGIS query syntax (incompatible with OGR syntax)
            # Works also on delimited text layers
            subsetString = STRING_FORMAT.format(self.fromTimeAttribute,
                                                                  endTimeStr,
                                                                  self.toTimeAttribute,
                                                                  startTimeStr)
        else:
            # Use OGR query syntax
            subsetString = self.constructOGRSubsetString(startTimeStr, endTimeStr)

        if self.toTimeAttribute != self.fromTimeAttribute:
            """Change < to <= when and end time is specified, otherwise features starting at 15:00 would only 
            be displayed starting from 15:01"""
            subsetString = subsetString.replace('<','<=')
        if self.originalSubsetString != "":
            # Prepend original subset string
            subsetString = "%s AND %s" % (self.originalSubsetString, subsetString)
        success = self.layer.setSubsetString(subsetString)
        if not success:
            raise SubstringException("Could not set substring to".format(subsetString))

    def constructOGRSubsetString(self, startTimeStr, endTimeStr):
        """Constructs the subset query depending on which time format was detected"""
        return STRINGCAST_FORMAT.format(self.fromTimeAttribute, endTimeStr, self.toTimeAttribute,
                                  startTimeStr)

    def deleteTimeRestriction(self):
        """Restore original subset"""
        success = self.layer.setSubsetString(self.originalSubsetString)
        if not success:
            raise SubstringException("Could not set substring  to {}".format(
                self.originalSubsetString))

    def hasTimeRestriction(self):
        """returns true if current layer.subsetString is not equal to originalSubsetString"""
        return self.layer.subsetString() != self.originalSubsetString
        
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
