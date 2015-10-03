# -*- coding: utf-8 -*-

from datetime import timedelta
import re

from  qgis._core import QgsSingleBandPseudoColorRenderer

from .. import time_util
from ..timerasterlayer import TimeRasterLayer
from ..timelayer import TimeLayer, NotATimeAttributeError


class CDFRasterLayer(TimeRasterLayer):
    def __init__(self, settings, iface=None):
        TimeLayer.__init__(self, settings.layer, settings.isEnabled)

        self.fromTimeAttribute = "From Raster Band"
        self.toTimeAttribute = self.fromTimeAttribute
        self.timeFormat = time_util.NETCDF_BAND
        self.offset = int(settings.offset)
        self.band_to_dt = []

        try:
            self.getTimeExtents()
        except NotATimeAttributeError, e:
            raise InvalidTimeLayerError(e)

    @classmethod
    def isSupportedRaster(cls, layer):
        # multiband layers need to have a particular renderer
        # this has to do with qgis python bindings 
        # see https://github.com/qgis/QGIS/pull/2163
        return not cls.is_multiband(layer) or isinstance(layer.renderer(),
                                                         QgsSingleBandPseudoColorRenderer)

    @classmethod
    def extract_time_from_bandname(cls, bandName):
        pattern = "\s*\d+\s*\/\s*[^0-9]*(\d+)\s*.+"
        epoch = int(re.findall(pattern, bandName)[0])
        if "minute" in bandName.lower():
            epoch = epoch * 60  # the number is originally in minutes, so need to multiply by 60
        return time_util.epoch_to_datetime(epoch)


    @classmethod
    def get_first_band_between(cls, dts, start_dt, end_dt):
        """Get the index of the band whose timestamp is greater or equal to
        the starttime, but smaller than the endtime. If no such band is present,
        use the previous band"""
        # TODO find later a faster way which takes advantage of the sorting 
        # idx = np.searchsorted(self.band_to_dt, start_dt, side='right')

        for i, dt in enumerate(dts):
            if dt >= start_dt:
                if dt == start_dt or dt < end_dt:
                    return i + 1  # bands are 1-indexed
                else:
                    return max(i - 1, 0) + 1

        return len(dts)  # persist the last band forever

    @classmethod
    def is_multiband(cls, layer):
        return layer.dataProvider().bandCount() > 1

    def getTimeExtents(self):
        p = self.layer.dataProvider()
        cnt = p.bandCount()
        for i in range(1, cnt + 1):
            self.band_to_dt.append(self.extract_time_from_bandname(p.generateBandName(i)))

        startTime = self.band_to_dt[0]
        endTime = self.band_to_dt[-1]
        # apply offset
        startTime += timedelta(seconds=self.offset)
        endTime += timedelta(seconds=self.offset)
        return (startTime, endTime)

    def setTimeRestriction(self, timePosition, timeFrame):
        """Constructs the query, including the original subset"""
        if not self.timeEnabled:
            self.deleteTimeRestriction()
            return
        startTime = timePosition + timedelta(seconds=self.offset)
        endTime = timePosition + timeFrame + timedelta(seconds=self.offset)
        if not self.is_multiband(self.layer):
            # Note: opportunity to subclass here if logic becomes more complicated
            layerStartTime = self.extract_time_from_bandname(
                self.layer.dataProvider().generateBandName(1))
            self.hideOrShowLayer(startTime, endTime, layerStartTime, layerStartTime)
            return
        else:
            bandNo = self.get_first_band_between(self.band_to_dt, startTime, endTime)
            self.layer.renderer().setBand(bandNo)

    def deleteTimeRestriction(self):
        """The layer is removed from Time Manager and is therefore always shown"""
        if not self.is_multiband(self.layer):
            self.show()
            return
        else:
            self.layer.renderer().setBand(1)
