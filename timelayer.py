#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import
from builtins import object

from qgis.PyQt.QtCore import QCoreApplication

import abc

from . import conf
from utils import time_util
from future.utils import with_metaclass


class TimeLayer(with_metaclass(abc.ABCMeta, object)):
    """Manages the properties of a managed (managable) layer"""

    def __init__(self, layer, enabled=True):
        self.layer = layer
        self.timeEnabled = enabled

    def getOriginalSubsetString(self):
        return ''

    def determine_format(self, val, fmtGiven):
        if fmtGiven != time_util.PENDING:
            return fmtGiven
        else:
            res = time_util.get_format_of_timeval(val)
            return res

    @abc.abstractmethod
    def hasSubsetStr(self):
        pass

    def isInterpolationEnabled(self):
        return False

    def interpolationMode(self):
        return conf.NO_INTERPOLATION

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

    def getLayer(self):
        """Get the layer associated with the current timeLayer"""
        return self.layer

    def getName(self):
        """Get the layer name as it is shown in the layers dock"""
        return self.layer.name()

    def getLayerId(self):
        """Return the layerID as registered in QgisMapLayerRegistry"""
        try:
            return self.layer.id()  # function call for QGIS >= 1.7
        except AttributeError:
            return self.layer.getLayerID()

    def geometriesCountForExport(self):
        return True

    def isEnabled(self):
        """Whether timeManagement is enabled for this layer"""
        return self.timeEnabled


class NotATimeAttributeError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return QCoreApplication.translate('TimeManager', 'NotATimeAttributeError: invalid value {}').format(repr(self.value))
        return repr(self.value)


class InvalidTimeLayerError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return QCoreApplication.translate('TimeManager', 'InvalidTimeLayerError: invalid value {}').format(repr(self.value))
