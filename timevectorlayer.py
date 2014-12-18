# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 17:28:19 2012

@author: Anita
"""

from PyQt4 import QtCore
from datetime import datetime, timedelta
from qgis.core import *
from timelayer import *

class TimeVectorLayer(TimeLayer):
    def __init__(self,layer,fromTimeAttribute,toTimeAttribute,enabled=True,timeFormat="%Y-%m-%d %H:%M:%S",offset=0):
        TimeLayer.__init__(self,layer,enabled)
        
        self.layer = layer
        self.fromTimeAttribute = fromTimeAttribute
        self.toTimeAttribute = toTimeAttribute
        self.timeEnabled = enabled
        self.originalSubsetString = self.layer.subsetString()
        self.timeFormat = str(timeFormat) # cast in case timeFormat comes as a QString
        self.supportedFormats = [
             "%Y-%m-%d %H:%M:%S.%f",
             "%Y-%m-%d %H:%M:%S",
             "%Y-%m-%d %H:%M",
             "%Y-%m-%d",
             "%Y/%m/%d %H:%M:%S.%f",
             "%Y/%m/%d %H:%M:%S",
             "%Y/%m/%d %H:%M",
             "%Y/%m/%d",
             "%d.%m.%Y %H:%M:%S.%f",
             "%d.%m.%Y %H:%M:%S",
             "%d.%m.%Y %H:%M",
             "%d.%m.%Y",
             "%d-%m-%Y %H:%M:%S.%f",
             "%d-%m-%Y %H:%M:%S",
             "%d-%m-%Y %H:%M",
             "%d-%m-%Y",
             "%d/%m/%Y %H:%M:%S.%f",
             "%d/%m/%Y %H:%M:%S",
             "%d/%m/%Y %H:%M",
             "%d/%m/%Y"
             ]
        if timeFormat not in self.supportedFormats:
            self.supportedFormats.append(timeFormat)
        self.offset = int(offset)
        try:
            self.getTimeExtents()
        except NotATimeAttributeError, e:
            raise InvalidTimeLayerError(e.value)
        self.fromTimeAttributeType = layer.dataProvider().fields().field(fromTimeAttribute).typeName()
        self.toTimeAttributeType = layer.dataProvider().fields().field(toTimeAttribute).typeName()

    def getTimeAttributes(self):
        """return the tuple of timeAttributes (fromTimeAttribute,toTimeAttribute)"""
        return (self.fromTimeAttribute,self.toTimeAttribute)

    def getTimeFormat(self):
        """returns the layer's time format"""
        return self.timeFormat
        
    def getOffset(self):
        """returns the layer's offset, integer in seconds"""
        return self.offset

    def strToDatetime(self, dtStr):
       """convert a date/time string into a Python datetime object"""
       try:
           # Try the last known format, if not, try all known formats.
           return datetime.strptime(dtStr, self.timeFormat)
       except:
           for fmt in self.supportedFormats:
               try:
                   self.timeFormat = fmt
                   return datetime.strptime(dtStr, self.timeFormat)
               except:
                   pass
       # If all fail, re-raise the exception
       raise

    def getTimeExtents(self):
        """Get layer's temporal extent using the fields and the format defined somewhere else!"""
        provider = self.layer.dataProvider()
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
                startTime = self.strToDatetime(startStr)
            except ValueError:
                raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as start time contains invalid data:\n\n'+startStr+'\n\nis not one of the supported formats:\n'+str(self.supportedFormats))
            try:
                endTime = self.strToDatetime(endStr)
            except ValueError:
                raise NotATimeAttributeError(str(self.getName())+': The attribute specified for use as end time contains invalid data:\n'+endStr)
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return (startTime, endTime)

    def setTimeRestriction(self, timePosition, timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return
        startTime = datetime.strftime(timePosition + timedelta(seconds=self.offset), self.timeFormat)
        if self.toTimeAttribute != self.fromTimeAttribute:
            """If an end time attribute is set for the layer, then only show features where the current time position
            falls between the feature's time from and time to attributes """
            endTime = startTime
        else:
            """If no end time attribute has been set for this layer, then show features with a time attribute
            which falls somewhere between the current time position and the start position of the next frame"""   
            endTime = datetime.strftime((timePosition + timeFrame + timedelta(seconds=self.offset)),self.timeFormat)
        if self.layer.dataProvider().storageType() == 'PostgreSQL database with PostGIS extension':
            # Use PostGIS query syntax (incompatible with OGR syntax)
            subsetString = "\"%s\" < '%s' AND \"%s\" >= '%s' " % (self.fromTimeAttribute,endTime,self.toTimeAttribute,startTime)
        else:
            # Use OGR query syntax
            subsetString = self.constructOGRSubsetString(startTime, endTime)
        if self.toTimeAttribute != self.fromTimeAttribute:
            """Change < to <= when and end time is specified, otherwise features starting at 15:00 would only 
            be displayed starting from 15:01"""
            subsetString = subsetString.replace('<','<=')
        if self.originalSubsetString != "":
            # Prepend original subset string 
            subsetString = "%s AND %s" % (self.originalSubsetString, subsetString)
        self.layer.setSubsetString(subsetString)
        #QMessageBox.information(self.iface.mainWindow(),"Test Output",subsetString)

    def constructOGRSubsetString(self, startTime, endTime):
        """Constructs the subset query depending on which time format was detected"""

        if self.fromTimeAttributeType == 'Date':
            # QDate in QGIS detects a format of YYYY-MM-DD, but OGR serializes its Date type as YYYY/MM/DD
            # See: https://github.com/anitagraser/TimeManager/issues/71
            startTime = startTime.replace('-', '/')
        if self.toTimeAttributeType == 'Date':
            endTime = endTime.replace('-', '/')

        if self.timeFormat[0:2] == '%Y' and self.timeFormat[3:5] == '%m' and self.timeFormat[6:8] == '%d':
            # Y-M-D format
            return "cast(\"%s\" as character) < '%s' AND cast(\"%s\" as character) >= '%s' " % \
                   (self.fromTimeAttribute, endTime, self.toTimeAttribute, startTime)

        elif self.timeFormat[0:2] == '%d' and self.timeFormat[3:5] == '%m' and self.timeFormat[6:8] == '%Y':
            # D-M-Y format
            s = "CONCAT(SUBSTR(cast(\"{0:s}\" as character),7,10),"\
                "SUBSTR(cast(\"{0:s}\" as character),4,5),"\
                "SUBSTR(cast(\"{0:s}\" as character),1,2)"\
                +(",SUBSTR(cast(\"{0:s}\" as character),11))", ")")[ len(self.timeFormat) <= 8]+\
                " < "\
                "CONCAT(SUBSTR('{1:s}',7,10),SUBSTR('{1:s}',4,5),SUBSTR('{1:s}',1,2)"\
                +(",SUBSTR('{1:s}',11))", ")")[len(self.timeFormat) <= 8]+\
                " AND "\
                "CONCAT(SUBSTR(cast(\"{2:s}\" as character),7,10),"\
                "SUBSTR(cast(\"{2:s}\" as character),4,5),"\
                "SUBSTR(cast(\"{2:s}\" as character),1,2)"\
                +(",SUBSTR(cast(\"{2:s}\" as character),11))", ")")[len(self.timeFormat) <= 8]+\
                " >= "\
                "CONCAT(SUBSTR('{3:s}',7,10),SUBSTR('{3:s}',4,5),SUBSTR('{3:s}',1,2)"\
                +(",SUBSTR('{3:s}',11))", ")")[len(self.timeFormat) <= 8]
            return s.format( self.fromTimeAttribute,endTime,self.toTimeAttribute,startTime)

        else:
            raise Exception('Unable to construct OGR subset query for time format: %s' % (self.timeFormat))

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
