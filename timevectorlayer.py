# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 17:28:19 2012

@author: Anita
"""
from __future__ import absolute_import
from builtins import str

import traceback
from datetime import timedelta
from qgis.PyQt.QtCore import QCoreApplication, QDate, QDateTime

from .timelayer import TimeLayer, InvalidTimeLayerError
from utils.tmlogging import info, warn, error

from . import conf
from utils import time_util
from . import layer_settings
from . import query_builder

POSTGRES_TYPE = 'PostgreSQL database with PostGIS extension'
DELIMITED_TEXT_TYPE = 'Delimited text file'
STORAGE_TYPES_WITH_SQL = [POSTGRES_TYPE, DELIMITED_TEXT_TYPE]


class SubstringException(Exception):
    pass


def isNull(val):
    """Determine null values from providers"""
    return val is None or val == "NULL" or str(val) == "NULL"  # yes it's possible the string "NULL" is returned (!)


class TimeVectorLayer(TimeLayer):

    def __init__(self, settings, iface=None):
        TimeLayer.__init__(self, settings.layer, settings.isEnabled)

        try:
            self.layer = settings.layer
            self.iface = iface
            self.minValue, self.maxValue = None, None
            self.fromTimeAttribute = settings.startTimeAttribute
            self.toTimeAttribute = settings.endTimeAttribute if settings.endTimeAttribute != "" \
                else self.fromTimeAttribute
            self.accumulate = settings.accumulate
            self.resetsss = settings.resetSubsetString
            self.originalSubsetString = settings.subsetStr
            self.currSubsetString = self.originalSubsetString
            if self.resetsss:
                self.setSubsetString("")
            else:
                self.setSubsetString(self.originalSubsetString)
            self.geometriesCount = settings.geometriesCount
            self.type = time_util.DateTypes.determine_type(self.getRawMinValue())
            if self.type not in time_util.DateTypes.QDateTypes:
                # call to throw an exception early if no format can be found
                self.findValidValues(self.fromTimeAttribute, settings.timeFormat)
                if self.fromTimeAttribute != self.toTimeAttribute:
                    self.findValidValues(self.toTimeAttribute, settings.timeFormat)

            self.timeFormat = self.determine_format(self.getRawMinValue(), settings.timeFormat)
            if self.toTimeAttribute != self.fromTimeAttribute:
                type2 = time_util.DateTypes.determine_type(self.getRawMaxValue())
                tf2 = self.determine_format(self.getRawMaxValue(), settings.timeFormat)
                if self.type != type2 or self.timeFormat != tf2:
                    raise InvalidTimeLayerError(
                        QCoreApplication.translate(
                            'TimeManager',
                            "Invalid time layer: To and From attributes must have "
                            "exact same format"
                        )
                    )

            self.offset = int(settings.offset)
            assert (self.timeFormat != time_util.PENDING)
            extents = self.getTimeExtents()
            info("Layer extents" + str(extents))
            if self.resetsss:
                self.setSubsetString(self.originalSubsetString)
        except ValueError as e:
            # ValueErrors appear for virtual layers, see https://github.com/anitagraser/TimeManager/issues/219
            error(traceback.format_exc(e))
            raise InvalidTimeLayerError(
                QCoreApplication.translate(
                    'TimeManager',
                    'This layer type is currently not supported. Cause:{}'
                ).format(str(e))
            )
        except Exception as e:
            error(traceback.format_exc(e))
            raise InvalidTimeLayerError(str(e))

    def getOriginalSubsetString(self):
        return self.originalSubsetString

    def getDateType(self):
        """Return the type of dates this layer has stored"""
        return self.type

    def getTimeAttributes(self):
        """Return the tuple of timeAttributes (fromTimeAttribute,toTimeAttribute)"""
        return (self.fromTimeAttribute, self.toTimeAttribute)

    def getTimeFormat(self):
        """Return the layer's time format"""
        return self.timeFormat

    def getOffset(self):
        """Return the layer's offset, integer in seconds"""
        return self.offset

    def getProvider(self):
        return self.layer  # the layer itself can be the provider,
        # which means that it can now about joined fields

    def getRawMinValue(self):
        """
        Return the raw minimum value. May not be the expected minimum value semantically if we
        have dates that are saved as strings because of lexicographic comparisons
        """
        fromTimeAttributeIndex = self.getProvider().fields().indexFromName(self.fromTimeAttribute)
        minValue = self.getProvider().minimumValue(fromTimeAttributeIndex)
        if isNull(minValue):
            values = [x for x in self.getProvider().uniqueValues(fromTimeAttributeIndex) if not isNull(x)]
            minValue = min(values) if values else None
        return minValue

    def getRawMaxValue(self):
        """
        Return the raw maximum value. May not be the expected minimum value semantically if we
        have dates that are saved as strings because of lexicographic comparisons
        """
        toTimeAttributeIndex = self.getProvider().fields().indexFromName(self.toTimeAttribute)
        maxValue = self.getProvider().maximumValue(toTimeAttributeIndex)
        if isNull(maxValue):
            values = [x for x in self.getProvider().uniqueValues(toTimeAttributeIndex) if not isNull(x)]
            maxValue = max(values) if values else None
        return maxValue

    def getUniques(self, fieldName):
        """Return unique values in given field"""
        provider = self.getProvider()
        idx = provider.fields().indexFromName(fieldName)
        return provider.uniqueValues(idx)

    def getMinMaxValues(self):
        """Return min and max value strings"""
        if self.minValue is None or self.maxValue is None:  # if not already computed
            fmt = self.getTimeFormat()
            if self.getDateType() == time_util.DateTypes.IntegerTimestamps:
                self.minValue = self.getRawMinValue()
                self.maxValue = self.getRawMaxValue()
            else:  # strings or qdate(time) values
                # need to find min max by looking at all the unique values
                # because QGIS doesn't get sorting right
                uniques = self.getUniques(self.fromTimeAttribute)

                def vals_to_dt(vals, fmt):
                    res = []
                    for val in vals:
                        try:
                            dt = time_util.timeval_to_datetime(val, fmt)
                            res.append(dt)
                            # info("{} converted to {}".format(val, dt))
                        except Exception as e:
                            error(traceback.format_exc(e))
                            warn(QCoreApplication.translate('TimeManager', "Unparseable value {0} in layer {1} ignored. Cause {2}").format(val, self.layer.name(), e))
                    return res

                unique_vals = vals_to_dt(uniques, fmt)
                if len(unique_vals) == 0:
                    raise Exception(
                        QCoreApplication.translate(
                            'TimeManager',
                            "Could not parse any dates while trying to get time extents."
                            "None of the values (for example {0}) matches the format {1}"
                        ).format(uniques[-1], fmt)
                    )
                minValue = time_util.datetime_to_str(min(unique_vals), fmt)
                if self.fromTimeAttribute == self.toTimeAttribute:
                    maxValue = time_util.datetime_to_str(max(unique_vals), fmt)
                else:
                    unique_vals = self.getUniques(self.toTimeAttribute)
                    unique_vals = vals_to_dt(unique_vals, fmt)
                    maxValue = time_util.datetime_to_str(max(unique_vals), fmt)

                if type(minValue) in [QDate, QDateTime]:
                    minValue = time_util.datetime_to_str(time_util.QDateTime_to_datetime(minValue), fmt)
                    maxValue = time_util.datetime_to_str(time_util.QDateTime_to_datetime(maxValue), fmt)
                self.minValue = minValue
                self.maxValue = maxValue
        return self.minValue, self.maxValue

    def getTimeExtents(self):
        """
        Return temporal extent in datetime format
        using the fields and the format defined in the layer
        """
        start_str, end_str = self.getMinMaxValues()
        startTime = time_util.str_to_datetime(start_str, self.getTimeFormat())
        endTime = time_util.str_to_datetime(end_str, self.getTimeFormat())
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return startTime, endTime

    def getStartTime(self, timePosition, timeFrame):
        return timePosition + timedelta(seconds=self.offset)

    def getEndTime(self, timePosition, timeFrame):
        return timePosition + timeFrame + timedelta(seconds=self.offset)

    def getGeometriesCountForExport(self):
        return self.geometriesCount

    def accumulateFeatures(self):
        return self.accumulate

    def resetSubsetString(self):
        return self.resetsss

    def findValidValues(self, fieldName, fmt):
        uniques = self.getUniques(fieldName)
        at_least_one_valid = False
        last_exc = None
        for v in uniques:
            try:
                time_util.str_to_datetime(v, fmt)
                at_least_one_valid = True
                break
            except Exception as e:
                error(traceback.format_exc(e))
                last_exc = e
                continue
        if not at_least_one_valid:
            raise Exception(last_exc)

    def hasSubsetStr(self):
        return True

    def setTimeRestriction(self, timePosition, timeFrame):
        """Construct the query, including the original subset"""
        if not self.isEnabled():
            self.deleteTimeRestriction()
            return
        startTime = self.getStartTime(timePosition, timeFrame)
        endTime = self.getEndTime(timePosition, timeFrame)
        dateType = self.getDateType()
        # determine which idioms should be tried
        # SQL
        idioms_to_try = [query_builder.QueryIdioms.SQL, query_builder.QueryIdioms.OGR]
        # OGR
        if dateType in time_util.DateTypes.QDateTypes:
            idioms_to_try = [query_builder.QueryIdioms.OGR]
        # Postgres
        # use optimized query format for postgres + (timestamp|date) columns
        if self.layer.dataProvider().storageType() == POSTGRES_TYPE and dateType in time_util.DateTypes.QDateTypes:
            idioms_to_try = [query_builder.QueryIdioms.SQL]

        tried = []
        # now try them
        for idiom in idioms_to_try:
            subsetString = query_builder.build_query(
                startTime, endTime, self.fromTimeAttribute, self.toTimeAttribute, date_type=dateType,
                date_format=self.getTimeFormat(), query_idiom=idiom, acc=self.accumulateFeatures()
            )
            try:
                self.setSubsetString(subsetString)
            except SubstringException:
                error(traceback.format_exc(e))
                tried.append(subsetString)
                # try the other one
                # not sure if trying several idioms could make the screen flash
                continue
            return

        raise SubstringException(
            "Could not update subset string for layer {}. Tried: {}".format(self.layer.name(), tried))

    def setSubsetString(self, subsetString):
        # info("setSubsetString:{}".format(subsetString))
        if self.originalSubsetString != '' and not self.resetsss:
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
        """Return true if current layer.subsetString is not equal to originalSubsetString"""
        return self.layer.subsetString() != self.originalSubsetString

    def getSaveString(self):
        """Get string to save in project file"""
        settings = layer_settings.getSettingsFromLayer(self)
        res = conf.SAVE_DELIMITER.join([
            settings.layerId, settings.subsetStr,
            settings.startTimeAttribute, settings.endTimeAttribute,
            str(settings.isEnabled), settings.timeFormat,
            str(settings.offset), settings.idAttribute,
            str(settings.interpolationEnabled), settings.interpolationMode,
            str(settings.geometriesCount),
            str(settings.accumulate),
            str(settings.resetSubsetString)
        ])
        return res
