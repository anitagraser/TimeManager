# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 17:28:19 2012

@author: Anita
"""

from PyQt4 import QtCore

from PyQt4.QtGui import QMessageBox
from timelayer import *
from time_util import SUPPORTED_FORMATS, DEFAULT_FORMAT, strToDatetimeWithFormatHint, \
    getFormatOfDatetimeValue, datetime_to_str, QDateTime_to_datetime, str_to_datetime
from query_builder import  QueryIdioms, DateTypes
import query_builder

POSTGRES_TYPE='PostgreSQL database with PostGIS extension'
DELIMITED_TEXT_TYPE='Delimited text file'
STORAGE_TYPES_WITH_SQL=[POSTGRES_TYPE, DELIMITED_TEXT_TYPE]

class SubstringException(Exception):
    pass

class TimeVectorLayer(TimeLayer):

    def _infer_time_format(self,val, hint):
        if self.type in DateTypes.nonQDateTypes:
            tf = getFormatOfDatetimeValue(val, hint=hint)
        else:
            tf = DateTypes.get_type_format(self.type)
        return tf

    def __init__(self,layer,fromTimeAttribute,toTimeAttribute,enabled=True,
                 timeFormat=DEFAULT_FORMAT,offset=0, iface=None):
        TimeLayer.__init__(self,layer,enabled)
        
        self.layer = layer
        self.iface = iface
        self.minValue,self.maxValue = None,None
        self.fromTimeAttribute = fromTimeAttribute
        self.toTimeAttribute = toTimeAttribute
        self.timeEnabled = enabled
        self.originalSubsetString = self.layer.subsetString()
        self.type = DateTypes.determine_type(self.getRawMinValue())
        type2 = DateTypes.determine_type(self.getRawMaxValue())
        self.timeFormat = self._infer_time_format(self.getRawMinValue(),hint=str(timeFormat))
        tf2 = self._infer_time_format(self.getRawMaxValue(),hint=str(timeFormat))

        if self.type!=type2 or self.timeFormat!=tf2:
            raise InvalidTimeLayerError("Invalid time layer: To and From attributes must have "
                                        "exact same format")

        self.offset = int(offset)
        try:
            self.getTimeExtents()
        except Exception, e:
            raise InvalidTimeLayerError(e.value)

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
        """returns the raw minimum value. May not be the expected minimum value semantically if we
        have dates that are saves as strings because of lexicographic comparisons"""
        provider = self.layer.dataProvider()
        fromTimeAttributeIndex = provider.fieldNameIndex(self.fromTimeAttribute)
        minValue =  provider.minimumValue(fromTimeAttributeIndex)
        return minValue

    def getRawMaxValue(self):
        """returns the raw minimum value. May not be the expected minimum value semantically if we
        have dates that are saves as strings because of lexicographic comparisons"""
        provider = self.layer.dataProvider()
        toTimeAttributeIndex = provider.fieldNameIndex(self.toTimeAttribute)
        maxValue =  provider.minimumValue(toTimeAttributeIndex)
        return maxValue

    def getMinMaxValues(self):
        """Returns str"""
        if self.minValue is None or self.maxValue is None: # if not already computed
            provider = self.layer.dataProvider()
            fmt = self.getTimeFormat()
            fromTimeAttributeIndex = provider.fieldNameIndex(self.fromTimeAttribute)
            toTimeAttributeIndex = provider.fieldNameIndex(self.toTimeAttribute)
            if query_builder.can_compare_lexicographically(fmt):
                minValue =  provider.minimumValue(fromTimeAttributeIndex)
                maxValue = provider.maximumValue(toTimeAttributeIndex)
            else:
                # need to find min max by looking at all the unique values
                # QGIS doesn't get sorting right

                unique_vals = provider.uniqueValues(fromTimeAttributeIndex)
                unique_vals = map(lambda x:str_to_datetime(x,fmt),unique_vals)
                minValue= datetime_to_str(min(unique_vals),fmt)
                if fromTimeAttributeIndex == toTimeAttributeIndex:
                    maxValue =  datetime_to_str(max(unique_vals),fmt)
                else:
                    unique_vals = provider.uniqueValues(toTimeAttributeIndex)
                    unique_vals = map(lambda x:str_to_datetime(x,fmt),unique_vals)
                    maxValue= datetime_to_str(max(unique_vals),fmt)

            if type(minValue) in [QtCore.QDate, QtCore.QDateTime]:
                minValue = datetime_to_str(QDateTime_to_datetime(minValue), self.getTimeFormat())
                maxValue = datetime_to_str(QDateTime_to_datetime(maxValue), self.getTimeFormat())
            self.minValue = minValue
            self.maxValue = maxValue
        return self.minValue, self.maxValue

    def getTimeExtents(self):
        """Get layer's temporal extent in datetime format
         using the fields and the format defined in the layer"""
        start_str, end_str = self.getMinMaxValues()
        try:
            startTime = strToDatetimeWithFormatHint(start_str,  self.getTimeFormat())
        except ValueError:
            raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as start time contains invalid data:\n\n'+start_str+'\n\nis not one of the supported formats:\n'+str(self.supportedFormats))
        try:
            endTime = strToDatetimeWithFormatHint(end_str,  self.getTimeFormat())
        except ValueError:
            raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as end time contains invalid data:\n'+end_str)
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return startTime, endTime

    def setTimeRestriction(self, timePosition, timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return

        startTime = timePosition + timedelta(seconds=self.offset)

        if self.toTimeAttribute != self.fromTimeAttribute:
            # If an end time attribute is set for the layer, then only show features where the \
            # current time position falls between the feature'sget time from and time to
            # attributes
            endTime = startTime
        else:
            # If no end time attribute has been set for this layer, then show features with a time\
            # attribute which falls somewhere between the current time position and the start
            # position of the next frame"""
            endTime = timePosition + timeFrame + timedelta(seconds=self.offset)

        idioms_to_try = [QueryIdioms.SQL, QueryIdioms.OGR]

        if self.getDateType() in DateTypes.QDateTypes:
            idioms_to_try = [QueryIdioms.OGR]

        if self.layer.dataProvider().storageType() in STORAGE_TYPES_WITH_SQL:
            idioms_to_try = [QueryIdioms.SQL]

        for idiom in idioms_to_try:

            subsetString = query_builder.build_query(startTime, endTime, self.fromTimeAttribute,
                                                     self.toTimeAttribute, date_type =
                self.getDateType(), date_format=self.getTimeFormat(), query_idiom=idiom)
            try:
                self.setSubsetString(subsetString)
            except SubstringException:
                # try the other one
                # not sure if trying several idioms could make the screen flash
                continue
            return

        raise SubstringException



    def setSubsetString(self,subsetString):
        success = self.layer.setSubsetString(subsetString)
        if not success:
            raise SubstringException("Could not set substring to".format(subsetString))

    def deleteTimeRestriction(self):
        """Restore original subset"""
        self.setSubsetString(self.originalSubsetString)


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
