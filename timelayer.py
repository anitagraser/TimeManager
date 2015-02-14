#!/usr/bin/python
# -*- coding: UTF-8 -*-

import abc

class TimeLayer:
    """Manages the properties of a managed (managable) layer."""

    __metaclass__ = abc.ABCMeta # this class cannot be instantiated directly

    def __init__(self,layer,enabled=True):
        self.layer = layer
        self.timeEnabled = enabled

    def isInterpolationEnabled(self):
        return False

    @abc.abstractmethod
    def getOffset(self):
        pass

    @abc.abstractmethod
    def getTimeFormat(self):
        pass

    @abc.abstractmethod
    def getTimeAttributes(self):
        pass

    def hasIdAttribute(self):
        return False

    def getIdAttribute(self):
        return None

    def getSettings(self):
        """Get the layer's settings as a tuple"""

        layerName=self.getName()
        enabled = self.isEnabled()
        layerId=self.getLayerId()
        offset=self.getOffset()

        times=self.getTimeAttributes()
        startTime=times[0]
        if times[0] != times[1]: # end time equals start time for timeLayers of type timePoint
            endTime = times[1]
        else:
            endTime = ""
        timeFormat= self.getTimeFormat()
        interpolation_enabled = self.isInterpolationEnabled()
        if interpolation_enabled:
            idAttr = "" if not self.hasIdAttribute() else self.getIdAttribute()
        else:
            idAttr = ""

        return (layerName,enabled,layerId,offset,timeFormat,startTime,
                                      endTime,interpolation_enabled, idAttr)

    def getLayer(self):
        """Get the layer associated with the current timeLayer"""
        return self.layer
    
    def getName( self ):
        """Get the layer name as it is shown in the layers dock"""
        return self.layer.name()

    def getLayerId(self):
        """returns the layerID as registered in QgisMapLayerRegistry"""
        try:
            return self.layer.id() # function call for QGIS >= 1.7
        except AttributeError:
            return self.layer.getLayerID()

    def isEnabled(self):
        """whether timeManagement is enabled for this layer"""
        return self.timeEnabled

class NotATimeAttributeError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
         return repr(self.value)

class InvalidTimeLayerError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
         return repr(self.value)
