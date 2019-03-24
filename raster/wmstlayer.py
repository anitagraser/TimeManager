from future import standard_library
standard_library.install_aliases()
# -*- coding: utf-8 -*-

from datetime import timedelta

from timemanager.utils import time_util
from timemanager.layers.timerasterlayer import TimeRasterLayer
from timemanager.layers.timelayer import TimeLayer, NotATimeAttributeError

class WMSTRasterLayer(TimeRasterLayer):
    IGNORE_PREFIX = "IgnoreGetFeatureInfoUrl=1&IgnoreGetMapUrl=1&"

    def __init__(self, settings, iface=None):
        TimeLayer.__init__(self, settings.layer, settings.isEnabled)

        self.fromTimeAttribute = settings.startTimeAttribute
        self.toTimeAttribute = settings.endTimeAttribute
        self.offset = int(settings.offset)
        # TODO: better name this dataSourceUri ?
        self.originalUri = self.layer.dataProvider().dataSourceUri()

        # try to get the timeExtents from what user put into gui (difficult!)
        try:
            self.getTimeExtents()
            self.timeFormat = self.determine_format(
                settings.startTimeAttribute, settings.timeFormat)
            return
        except Exception as e:
            pass

        # if above failed, try to retrieve the capabilities from the service
        self.wmsUrl = ''
        # contextualWMSLegend=0 & crs=EPSG:3857 & dpiMode=7 & featureCount=10 & format=image/png & layers=layername & styles & url=http://example.com/geoserver/wms
        for key_val in self.originalUri.split('&'):
            kv = key_val.split('=')
            if len(kv) == 2 and kv[0].lower() == 'layers':
                self.layerName = kv[1]
            elif len(kv) == 2 and kv[0].lower() == 'url':
                self.wmsUrl = kv[1]
        try:
            if self._get_time_extents_from_capabilities():
                # succeeded in reading new from/to, save them in settings
                settings.startTimeAttribute = self.fromTimeAttribute
                settings.endTimeAttribute = self.toTimeAttribute
                self.timeFormat = self.determine_format(
                    self.fromTimeAttribute, settings.timeFormat)
        except NotATimeAttributeError as e:
            raise InvalidTimeLayerError(str(e))

    def _get_time_extents_from_capabilities(self):

        # A LOT OF different notations

        # http://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0r-t.cgi?&service=WMS&version=1.3.0&request=getcapabilities
        # <Dimension name="time" units="ISO8601" default="2006-06-23T03:10:00Z" nearestValue="0">1995-01-01/2019-12-31/PT5M</Dimension>
        # # http://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0r-t.cgi?&service=WMS&version=1.1.1&request=getcapabilities
        # <Dimension name="time" units="ISO8601"/><Extent name="time" default="2006-06-23T03:10:00Z" nearestValue="0">1995-01-01/2019-12-31/PT5M</Extent>

        # http://geoservices.knmi.nl/cgi-bin/RADNL_OPER_R___25PCPRR_L3.cgi?service=wms&version=1.3.0&request=getcapabilities
        # <Dimension name="time" units="ISO8601" default="2019-03-24T15:45:00Z" multipleValues="1" nearestValue="0" current="1">2012-01-01T00:00:00Z/2019-03-24T15:45:00Z/PT5M</Dimension>
        # http://geoservices.knmi.nl/cgi-bin/RADNL_OPER_R___25PCPRR_L3.cgi?service=wms&version=1.1.1&request=getcapabilities
        # <Dimension name="time" units="ISO8601"/><Extent name="time" default="2019-03-24T15:45:00Z" multipleValues="1" nearestValue="0">2012-01-01T00:00:00Z/2019-03-24T15:45:00Z/PT5M</Extent>

        # geoserver 1.3.0 - http://localhost:8080/geoserver/wms?version=1.3.0&request=getCapabilities
        # Interval and Resolution
        # <Dimension name="time" default="current" units="ISO8601">2018-09-25T13:10:00.000Z/2018-09-26T01:00:00.000Z/PT10M</Dimension>
        # Continues Interval:
        # <Dimension name="time" default="2018-09-26T01:00:00Z" units="ISO8601">2018-09-25T13:10:00.000Z/2018-09-26T01:00:00.000Z/PT1S</Dimension>
        # List
        # <Dimension name="time" default="2018-09-26T01:00:00Z" units="ISO8601">2018-09-25T13:10:00.000Z,2018-09-25T13:20:00.000Z,2018-09-25T13:30:00.000Z,2018-09-25T13:40:00.000Z,2018-09-25T13:50:00.000Z,2018-09-25T14:00:00.000Z,2018-09-25T14:10:00.000Z,2018-09-25T14:20:00.000Z,2018-09-25T14:30:00.000Z,2018-09-25T14:40:00.000Z,2018-09-25T14:50:00.000Z,2018-09-25T15:00:00.000Z,2018-09-25T15:10:00.000Z,2018-09-25T15:20:00.000Z,2018-09-25T15:30:00.000Z,2018-09-25T15:40:00.000Z,2018-09-25T15:50:00.000Z,2018-09-25T16:00:00.000Z,2018-09-25T16:10:00.000Z,2018-09-25T16:20:00.000Z,2018-09-25T16:30:00.000Z,2018-09-25T16:40:00.000Z,2018-09-25T16:50:00.000Z,2018-09-25T17:00:00.000Z,2018-09-25T17:10:00.000Z,2018-09-25T17:20:00.000Z,2018-09-25T17:30:00.000Z,2018-09-25T17:40:00.000Z,2018-09-25T17:50:00.000Z,2018-09-25T18:00:00.000Z,2018-09-25T18:10:00.000Z,2018-09-25T18:20:00.000Z,2018-09-25T18:30:00.000Z,2018-09-25T18:40:00.000Z,2018-09-25T18:50:00.000Z,2018-09-25T19:00:00.000Z,2018-09-25T19:10:00.000Z,2018-09-25T19:20:00.000Z,2018-09-25T19:30:00.000Z,2018-09-25T19:40:00.000Z,2018-09-25T19:50:00.000Z,2018-09-25T20:00:00.000Z,2018-09-25T20:10:00.000Z,2018-09-25T20:20:00.000Z,2018-09-25T20:30:00.000Z,2018-09-25T20:40:00.000Z,2018-09-25T20:50:00.000Z,2018-09-25T21:00:00.000Z,2018-09-25T21:10:00.000Z,2018-09-25T21:20:00.000Z,2018-09-25T21:30:00.000Z,2018-09-25T21:40:00.000Z,2018-09-25T21:50:00.000Z,2018-09-25T22:00:00.000Z,2018-09-25T22:10:00.000Z,2018-09-25T22:20:00.000Z,2018-09-25T22:30:00.000Z,2018-09-25T22:40:00.000Z,2018-09-25T22:50:00.000Z,2018-09-25T23:00:00.000Z,2018-09-25T23:10:00.000Z,2018-09-25T23:20:00.000Z,2018-09-25T23:30:00.000Z,2018-09-25T23:40:00.000Z,2018-09-25T23:50:00.000Z,2018-09-26T00:00:00.000Z,2018-09-26T00:10:00.000Z,2018-09-26T00:20:00.000Z,2018-09-26T00:30:00.000Z,2018-09-26T00:40:00.000Z,2018-09-26T00:50:00.000Z,2018-09-26T01:00:00.000Z</Dimension>
        #
        # geoserver 1.1.1 - http://localhost:8080/geoserver/wms?version=1.1.1&request=getCapabilities
        # Interval and Resolution
        # <Dimension name="time" units="ISO8601"/><Extent name="time" default="current">2018-09-25T13:10:00.000Z/2018-09-26T01:00:00.000Z/PT10M</Extent>
        # Continues Interval:
        # <Dimension name="time" units="ISO8601"/><Extent name="time" default="2018-09-26T01:00:00Z">2018-09-25T13:10:00.000Z/2018-09-26T01:00:00.000Z/PT1S</Extent>
        # List
        # <Dimension name="time" units="ISO8601"/><Extent name="time" default="2018-09-26T01:00:00Z">2018-09-25T13:10:00.000Z,2018-09-25T13:20:00.000Z,2018-09-25T13:30:00.000Z,2018-09-25T13:40:00.000Z,2018-09-25T13:50:00.000Z,2018-09-25T14:00:00.000Z,2018-09-25T14:10:00.000Z,2018-09-25T14:20:00.000Z,2018-09-25T14:30:00.000Z,2018-09-25T14:40:00.000Z,2018-09-25T14:50:00.000Z,2018-09-25T15:00:00.000Z,2018-09-25T15:10:00.000Z,2018-09-25T15:20:00.000Z,2018-09-25T15:30:00.000Z,2018-09-25T15:40:00.000Z,2018-09-25T15:50:00.000Z,2018-09-25T16:00:00.000Z,2018-09-25T16:10:00.000Z,2018-09-25T16:20:00.000Z,2018-09-25T16:30:00.000Z,2018-09-25T16:40:00.000Z,2018-09-25T16:50:00.000Z,2018-09-25T17:00:00.000Z,2018-09-25T17:10:00.000Z,2018-09-25T17:20:00.000Z,2018-09-25T17:30:00.000Z,2018-09-25T17:40:00.000Z,2018-09-25T17:50:00.000Z,2018-09-25T18:00:00.000Z,2018-09-25T18:10:00.000Z,2018-09-25T18:20:00.000Z,2018-09-25T18:30:00.000Z,2018-09-25T18:40:00.000Z,2018-09-25T18:50:00.000Z,2018-09-25T19:00:00.000Z,2018-09-25T19:10:00.000Z,2018-09-25T19:20:00.000Z,2018-09-25T19:30:00.000Z,2018-09-25T19:40:00.000Z,2018-09-25T19:50:00.000Z,2018-09-25T20:00:00.000Z,2018-09-25T20:10:00.000Z,2018-09-25T20:20:00.000Z,2018-09-25T20:30:00.000Z,2018-09-25T20:40:00.000Z,2018-09-25T20:50:00.000Z,2018-09-25T21:00:00.000Z,2018-09-25T21:10:00.000Z,2018-09-25T21:20:00.000Z,2018-09-25T21:30:00.000Z,2018-09-25T21:40:00.000Z,2018-09-25T21:50:00.000Z,2018-09-25T22:00:00.000Z,2018-09-25T22:10:00.000Z,2018-09-25T22:20:00.000Z,2018-09-25T22:30:00.000Z,2018-09-25T22:40:00.000Z,2018-09-25T22:50:00.000Z,2018-09-25T23:00:00.000Z,2018-09-25T23:10:00.000Z,2018-09-25T23:20:00.000Z,2018-09-25T23:30:00.000Z,2018-09-25T23:40:00.000Z,2018-09-25T23:50:00.000Z,2018-09-26T00:00:00.000Z,2018-09-26T00:10:00.000Z,2018-09-26T00:20:00.000Z,2018-09-26T00:30:00.000Z,2018-09-26T00:40:00.000Z,2018-09-26T00:50:00.000Z,2018-09-26T01:00:00.000Z</Extent>


        url = self.wmsUrl + self.addUrlMark() + 'service=wms&version=1.3.0&request=getCapabilities'
        # TODO: remove urllib dependency, use QgsNetworkManager !
        import urllib.request, urllib.parse
        import xml.etree.ElementTree as ET
        raw_xml = urllib.request.urlopen(url).read()
        root = ET.fromstring(raw_xml.decode("utf-8"))
        #print(root.tag)
        for lyr in root.iter('{http://www.opengis.net/wms}Layer'):
            # print(lyr)
            for name in lyr.findall('{http://www.opengis.net/wms}Name'):
                # print(name.text)
                if name.text == self.layerName:
                    dimension = lyr.find(
                        '{http://www.opengis.net/wms}Dimension')
                    if dimension is not None:
                        # TODO handle other notations
                        dims = dimension.text
                        # Geoserver 1.3.0 notation when 'Presentation' is set
                        #  to 'Interval and resolution' or 'Continues Interval'
                        # 2019-02-12T05:10:00.000Z/2019-02-12T17:00:00.000Z/PT10M
                        if len(dims.split('/')) == 3:
                            interval_start, interval_end, resolution = \
                                dimension.text.split('/')
                            # print(interval_start, interval_end, resolution)
                        # Geoserver 1.3.0 notation when 'Presentation' is set to 'List'
                        # 2018-09-25T13:10:00.000Z,2018-09-25T13:20:00.000Z,2018-09-25T13:30:00.000Z, ...
                        elif len(dims.split(',')) > 2:
                            interval_start = dims.split(',')[0]
                            interval_end = dims.split(',')[-1]
                            # print(interval_start, interval_end, resolution)
                        elif (len(dims.split(',')) == 1 and len(dims.split('/')) == 1):
                            # some services show dimension like
                            interval_start = dims
                            interval_end = dims
                        else:
                            # not yet implemented ?
                            return False

                        self.fromTimeAttribute = interval_start
                        self.toTimeAttribute = interval_end
                        # would be cool to be able to set or indicate a favoured timeFrameLength
                        # maybe in messagebar?
                        return True
        return False

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
                return "%26" # equals &
        else:
            return "?"

    def setTimeRestriction(self, timePosition, timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return
        startTime = timePosition + timedelta(seconds=self.offset)
        endTime = timePosition + timeFrame + timedelta(seconds=self.offset)
        if timeFrame == timedelta(0):
            # when timeFrame is set to 0 we can handle services which can serve
            # momentarily timeslices not sure what is better:
            # TIME=2019-03-01T10:00:00Z
            # or a range of zero by giving the same time as start and end:
            # TIME=2019-03-01T10:00:00Z/2019-03-01T10:00:00Z
            endTime = startTime # hope all services can handle a time-range of zero
        timeString = "TIME={}/{}".format(
            time_util.datetime_to_str(startTime, self.timeFormat),
            time_util.datetime_to_str(endTime, self.timeFormat))

        dataUrl = self.IGNORE_PREFIX + self.originalUri + self.addUrlMark() + timeString
        #print "original URL: " + self.originalUri
        #print "final URL: " + dataUrl
        self.layer.dataProvider().setDataSourceUri(dataUrl)
        self.layer.dataProvider().reloadData()


    def deleteTimeRestriction(self):
        """The layer is removed from Time Manager and is therefore always shown"""
        self.layer.dataProvider().setDataSourceUri(self.originalUri)
        self.layer.dataProvider().reloadData()
        self.layer.triggerRepaint()

