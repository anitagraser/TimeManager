#!/usr/bin/python
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from qgis.core import *

class TimeLayer:
    """Manages the properties of a managed (managable) layer."""

    def __init__(self,layer,enabled=True):
        self.layer = layer
        self.timeEnabled = enabled

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
