# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 17:28:19 2012

@author: Anita
"""
import traceback
from PyQt4 import QtCore
from datetime import timedelta

from PyQt4.QtGui import QMessageBox

from timelayer import *
from time_util import timeval_to_datetime, \
    datetime_to_str, QDateTime_to_datetime, str_to_datetime, DateTypes
import time_util
from query_builder import QueryIdioms
import query_builder
from conf import SAVE_DELIMITER
import layer_settings as ls
from tmlogging import info, warn, error


POSTGRES_TYPE = 'PostgreSQL database with PostGIS extension'
DELIMITED_TEXT_TYPE = 'Delimited text file'
STORAGE_TYPES_WITH_SQL = [POSTGRES_TYPE, DELIMITED_TEXT_TYPE]


class SubstringException(Exception):
    pass


def isNull(val):
    """Determine null values from providers"""
    return val is None or val == "NULL" or str(
        val) == "NULL"  # yes it's possible the string "NULL" is returned (!)


class TimeVectorLayer(TimeLayer):
    def getOriginalSubsetString(self):
        return self.originalSubsetString

    def geometriesCountForExport(self):
        return self.geometriesCount

    def accumulateFeatures(self):
        return self.accumulate

    def findValidValues(self, fieldName, fmt):
        uniques = self.getUniques(fieldName)
        at_least_one_valid = False
        last_exc = None
        for v in uniques:
            try:
                str_to_datetime(v, fmt)
                at_least_one_valid = True
                break
            except Exception, e:
                last_exc = e
                continue
        if not at_least_one_valid:
            raise Exception(last_exc)

    def __init__(self, settings, iface=None):
        TimeLayer.__init__(self, settings.layer, settings.isEnabled)

        try:
            self.layer = settings.layer
            self.iface = iface
            self.minValue, self.maxValue = None, None
            self.fromTimeAttribute = settings.startTimeAttribute
            self.toTimeAttribute = settings.endTimeAttribute if settings.endTimeAttribute != ""\
                else self.fromTimeAttribute
            self.accumulate = settings.accumulate
            self.originalSubsetString = settings.subsetStr
            self.currSubsetString = self.originalSubsetString
            self.setSubsetString(self.originalSubsetString)
            self.geometriesCount = settings.geometriesCount
            self.type = DateTypes.determine_type(self.getRawMinValue())
            if self.type not in DateTypes.QDateTypes:  # call to throw an exception early if no format can be found
                self.findValidValues(self.fromTimeAttribute, settings.timeFormat)
                if self.fromTimeAttribute != self.toTimeAttribute:
                    self.findValidValues(self.toTimeAttribute, settings.timeFormat)

            self.timeFormat = self.determine_format(self.getRawMinValue(), settings.timeFormat)
            if self.toTimeAttribute != self.fromTimeAttribute:
                type2 = DateTypes.determine_type(self.getRawMaxValue())
                tf2 = self.determine_format(self.getRawMaxValue(), settings.timeFormat)
                if self.type != type2 or self.timeFormat != tf2:
                    raise InvalidTimeLayerError(
                        "Invalid time layer: To and From attributes must have "
                        "exact same format")

            self.offset = int(settings.offset)
            assert (self.timeFormat != time_util.PENDING)
            extents = self.getTimeExtents()
            info("Layer extents" + str(extents))
        except ValueError:
            # ValueErrors appear for virtual layers, see https://github.com/anitagraser/TimeManager/issues/219
            raise InvalidTimeLayerError('This layer type is currently not supported.')
        except Exception, e:
            error(traceback.format_exc(e))
            raise InvalidTimeLayerError(e)

    def hasSubsetStr(self):
        return True

    def getDateType(self):
        """return the type of dates this layer has stored"""
        return self.type

    def getTimeAttributes(self):
        """return the tuple of timeAttributes (fromTimeAttribute,toTimeAttribute)"""
        return (self.fromTimeAttribute, self.toTimeAttribute)

    def getTimeFormat(self):
        """returns the layer's time format"""
        return self.timeFormat

    def getOffset(self):
        """returns the layer's offset, integer in seconds"""
        return self.offset

    def getProvider(self):
        return self.layer  # the layer itself can be the provider,
        # which means that it can now about joined fields

    def getRawMinValue(self):
        """returns the raw minimum value. May not be the expected minimum value semantically if we
        have dates that are saved as strings because of lexicographic comparisons"""
        fromTimeAttributeIndex = self.getProvider().fieldNameIndex(self.fromTimeAttribute)
        minValue = self.getProvider().minimumValue(fromTimeAttributeIndex)
        if isNull(
                minValue):  # if we are unlucky and have some null data we need to sort through the values
            minValue = min(filter(lambda x: not isNull(x),
                                  self.getProvider().uniqueValues(fromTimeAttributeIndex)))
        # info("Min value:"+str(minValue)+str(isNull(minValue)))
        return minValue

    def getRawMaxValue(self):
        """returns the raw maximum value. May not be the expected minimum value semantically if we
        have dates that are saved as strings because of lexicographic comparisons"""
        toTimeAttributeIndex = self.getProvider().fieldNameIndex(self.toTimeAttribute)
        maxValue = self.getProvider().maximumValue(toTimeAttributeIndex)
        if isNull(maxValue):
            maxValue = max(filter(lambda x: not isNull(x),
                                  self.getProvider().uniqueValues(toTimeAttributeIndex)))
        return maxValue

    def getUniques(self, fieldName):
        provider = self.getProvider()
        idx = provider.fieldNameIndex(fieldName)
        return provider.uniqueValues(idx)

    def getMinMaxValues(self):
        """Returns str"""
        if self.minValue is None or self.maxValue is None:  # if not already computed
            fmt = self.getTimeFormat()
            if self.getDateType() == DateTypes.IntegerTimestamps:
                self.minValue = self.getRawMinValue()
                self.maxValue = self.getRawMaxValue()
            else:
                # need to find min max by looking at all the unique values
                # QGIS doesn't get sorting right
                uniques = self.getUniques(self.fromTimeAttribute)
                # those can be either strings or qdate(time) values

                def vals_to_dt(vals, fmt):
                    res = []
                    for val in vals:
                        try:
                            dt = timeval_to_datetime(val, fmt)
                            res.append(dt)
                            # info("{} converted to {}".format(val, dt))
                        except Exception, e:
                            warn("Unparseable value {} in layer {} ignored. Cause {}".format(val,
                                                                                             self.layer.name(),
                                                                                             e))
                            pass
                    return res

                unique_vals = vals_to_dt(uniques, fmt)
                if len(unique_vals) == 0:
                    raise Exception("Could not parse any dates while trying to get time extents." +
                                    "None of the values (for example {}) matches the format {}"
                                    .format(uniques[-1], fmt))
                minValue = datetime_to_str(min(unique_vals), fmt)
                if self.fromTimeAttribute == self.toTimeAttribute:
                    maxValue = datetime_to_str(max(unique_vals), fmt)
                else:
                    unique_vals = self.getUniques(self.toTimeAttribute)
                    unique_vals = vals_to_dt(unique_vals, fmt)
                    maxValue = datetime_to_str(max(unique_vals), fmt)

                if type(minValue) in [QtCore.QDate, QtCore.QDateTime]:
                    minValue = datetime_to_str(QDateTime_to_datetime(minValue),
                                               self.getTimeFormat())
                    maxValue = datetime_to_str(QDateTime_to_datetime(maxValue),
                                               self.getTimeFormat())
                self.minValue = minValue
                self.maxValue = maxValue
        return self.minValue, self.maxValue

    def getTimeExtents(self):
        """Get layer's temporal extent in datetime format
         using the fields and the format defined in the layer"""
        start_str, end_str = self.getMinMaxValues()
        startTime = str_to_datetime(start_str, self.getTimeFormat())
        endTime = str_to_datetime(end_str, self.getTimeFormat())
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return startTime, endTime

    def getStartTime(self, timePosition, timeFrame):
        return timePosition + timedelta(seconds=self.offset)

    def getEndTime(self, timePosition, timeFrame):
        return timePosition + timeFrame + timedelta(seconds=self.offset)

    def setTimeRestriction(self, timePosition, timeFrame):
        """Constructs the query, including the original subset"""
        if not self.isEnabled():
            self.deleteTimeRestriction()
            return
        startTime = self.getStartTime(timePosition, timeFrame)
        endTime = self.getEndTime(timePosition, timeFrame)

        idioms_to_try = [QueryIdioms.SQL, QueryIdioms.OGR]

        if self.getDateType() in DateTypes.QDateTypes:
            idioms_to_try = [QueryIdioms.OGR]

        # use optimized query format for postgres + (timestamp|date) columns
        if self.layer.dataProvider().storageType()==POSTGRES_TYPE and self.getDateType() in DateTypes.QDateTypes:
            idioms_to_try = [QueryIdioms.SQL]

        tried = []
        for idiom in idioms_to_try:

            subsetString = query_builder.build_query(
                startTime, endTime, self.fromTimeAttribute,
                self.toTimeAttribute, date_type=self.getDateType(),
                date_format=self.getTimeFormat(), query_idiom=idiom,
                acc=self.accumulateFeatures()
                )
            try:
                self.setSubsetString(subsetString)
            except SubstringException:
                tried.append(subsetString)
                # try the other one
                # not sure if trying several idioms could make the screen flash
                continue
            # info("Subsetstring:"+subsetString)
            return

        raise SubstringException(
            "Could not update subset string for layer {}. Tried: {}".format(self.layer.name(),
                                                                            tried))

    def setSubsetString(self, subsetString):

        if self.originalSubsetString != '':
            subsetString = "{} AND {}".format(self.originalSubsetString, subsetString)
        success = self.layer.setSubsetString(subsetString)
        if not success:
            raise SubstringException("Could not set substring to {}".format(subsetString))
        else:
            self.currSubsetString = subsetString

    def subsetString(self):
        return self.layer.subsetString()

    def deleteTimeRestriction(self):
        """Restore original subset"""
        self.setSubsetString(self.originalSubsetString)

    def hasTimeRestriction(self):
        """returns true if current layer.subsetString is not equal to originalSubsetString"""
        return self.layer.subsetString() != self.originalSubsetString

    def getSaveString(self):
        """get string to save in project file"""
        settings = ls.getSettingsFromLayer(self)
        res = SAVE_DELIMITER.join([settings.layerId, settings.subsetStr,
                                   settings.startTimeAttribute, settings.endTimeAttribute,
                                   str(settings.isEnabled), settings.timeFormat,
                                   str(settings.offset), settings.idAttribute,
                                   str(settings.interpolationEnabled), settings.interpolationMode,
                                   str(settings.geometriesCount), str(settings.accumulate)])
        return res
