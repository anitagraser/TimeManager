# -*- coding: utf-8 -*-

from datetime import timedelta

from .. import time_util
from ..timerasterlayer import TimeRasterLayer
from ..timelayer import TimeLayer, NotATimeAttributeError


class WMSTRasterLayer(TimeRasterLayer):
    IGNORE_PREFIX = "IgnoreGetFeatureInfoUrl=1&IgnoreGetMapUrl=1&"

    def __init__(self, settings, iface=None):
        TimeLayer.__init__(self, settings.layer, settings.isEnabled)

        self.fromTimeAttribute = settings.startTimeAttribute
        self.toTimeAttribute = settings.endTimeAttribute
        self.timeFormat = self.determine_format(settings.startTimeAttribute, settings.timeFormat)
        self.offset = int(settings.offset)
        self.originalUri = self.layer.dataProvider().dataSourceUri()
        try:
            self.getTimeExtents()
        except NotATimeAttributeError, e:
            raise InvalidTimeLayerError(e)

    def _get_wmts_layer_name():
        return self.layer.subLayers(0)

    def _get_time_extents_from_uri(self):
        # TODO get url from original uri
        url = "http://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0r-t.cgi?&SERVICE=WMS&REQUEST=GetCapabilities"
        # TODO get extents from the xml somehow
        import urllib2

        raw_xml = urllib2.urlopen(url).read()
        name = self._get_wmts_layer_name()
        return None, None

    def getTimeExtents(self):
        startTime, endTime = time_util.str_to_datetime(self.fromTimeAttribute, self.timeFormat), \
                             time_util.str_to_datetime(self.toTimeAttribute, self.timeFormat)
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return (startTime, endTime)

    def addUrlMark(self):
        if "?" in self.originalUri:
            if self.originalUri.endswith('?'):
                # concatting a & behind ? is messing up QGIS wms parseUri: do NOT add anything behind it
                return ""
            else:
                return "&"
        else:
            return "?"

    def setTimeRestriction(self, timePosition, timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return
        startTime = timePosition + timedelta(seconds=self.offset)
        endTime = timePosition + timeFrame + timedelta(seconds=self.offset)
        self.layer.dataProvider().setDataSourceUri(self.IGNORE_PREFIX + \
                                                   self.originalUri + self.addUrlMark() + "TIME={}/{}" \
                                                   .format(
            time_util.datetime_to_str(startTime, self.timeFormat),
            time_util.datetime_to_str(endTime, self.timeFormat)))
        self.layer.dataProvider().reloadData()

    def deleteTimeRestriction(self):
        """The layer is removed from Time Manager and is therefore always shown"""
        self.layer.dataProvider().setDataSourceUri(self.originalUri)
        self.layer.dataProvider().reloadData()
        self.layer.triggerRepaint()

