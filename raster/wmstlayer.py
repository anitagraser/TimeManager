# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from  qgis._core import QgsSingleBandPseudoColorRenderer

from .. import time_util
from ..timerasterlayer import TimeRasterLayer
from ..timelayer import TimeLayer, NotATimeAttributeError
from ..logging import info

class WMSTRasterLayer(TimeRasterLayer):
    IGNORE_PREFIX = "IgnoreGetFeatureInfoUrl=1&IgnoreGetMapUrl=1&"
    def __init__(self, settings, iface=None):
        TimeLayer.__init__(self,settings.layer, settings.isEnabled)
        
        self.fromTimeAttribute = "From WMST time attribute"
        self.toTimeAttribute = self.fromTimeAttribute 
        self.timeFormat = "%Y-%m-%dT%H:%M:%SZ"
        self.offset = int(settings.offset)
        self.originalUri = self.layer.dataProvider().dataSourceUri()
        try:
            self.getTimeExtents()
        except NotATimeAttributeError, e:
            raise InvalidTimeLayerError(e)

    def _get_time_extents_from_uri(self):
        # url = http://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0r-t.cgi?&SERVICE=WMS&REQUEST=GetCapabilities
        pass

    def getTimeExtents(self):
        p = self.layer.dataProvider()

        startTime = # ??? how to get minimum and maximum time from wmst?
        endTime = # ??? 
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return (startTime,endTime)

    def setTimeRestriction(self,timePosition,timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return
        startTime = timePosition + timedelta(seconds=self.offset)
        endTime = timePosition + timeFrame + timedelta(seconds=self.offset) # end time is ignored here, what else to do?
        # the ? could be a problem
        self.layer.dataProvider().setDataSourceUri(IGNORE_PREFIX+\
                self.originalUri+"?&TIME%3D{}".format(time_util.datetime_to_str(startTime,self.timeFormat)))
        self.layer.dataProvider().reloadData()
            
    def deleteTimeRestriction(self):
        """The layer is removed from Time Manager and is therefore always shown"""
        self.layer.dataProvider().setDataSourceUri(self.originalUri)
        self.layer.dataProvider().reloadData()
        #self.layer.triggerRepaint()

