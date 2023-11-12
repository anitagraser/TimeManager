from builtins import range
# -*- coding: utf-8 -*-

from datetime import timedelta
import re

from qgis._core import QgsSingleBandPseudoColorRenderer

from timemanager.utils import time_util
from timemanager.layers.timerasterlayer import TimeRasterLayer
from timemanager.layers.timelayer import TimeLayer, NotATimeAttributeError
from timemanager.utils.tmlogging import warn

DEFAULT_CALENDAR = "proleptic_gregorian"


class CDFRasterLayer(TimeRasterLayer):

    def get_dataset_time(self):
        try:
            from netCDF4 import Dataset, date2index
            nc = Dataset(self.get_filename(), mode='r')
            time = nc.variables["time"]
            return time
        except:
            return None

    def get_filename(self):
        uri = self.layer.dataProvider().dataSourceUri()
        if "NETCDF" in uri:
            # something like u'NETCDF:"/home/carolinux/Downloads/ex_jak_velsurf_mag (1).nc":velsurf_mag'
            return uri.split('"')[1]
        else:
            return uri

    def __init__(self, settings, iface=None):
        TimeLayer.__init__(self, settings.layer, settings.isEnabled)

        self.fromTimeAttribute = "From Raster Band"
        self.toTimeAttribute = self.fromTimeAttribute
        self.timeFormat = time_util.NETCDF_BAND
        self.offset = int(settings.offset)
        self.band_to_dt = []
        self.dataset_time = self.get_dataset_time()
        self.calendar = DEFAULT_CALENDAR
        try:
            if self.dataset_time.calendar is not None:
                self.calendar = self.dataset_time.calendar
            self.getTimeExtents()
        except NotATimeAttributeError as e:
            raise InvalidTimeLayerError(str(e))

    @classmethod
    def isSupportedRaster(cls, layer):
        # multiband layers need to have a particular renderer
        # this has to do with qgis python bindings 
        # see https://github.com/qgis/QGIS/pull/2163
        return not cls.is_multiband(layer) or isinstance(layer.renderer(),
                                                         QgsSingleBandPseudoColorRenderer)

    @classmethod
    def extract_time_from_bandname(cls, bandName, calendar=DEFAULT_CALENDAR):
        try:
            from netcdftime import utime
            return cls.extract_netcdf_time(bandName, calendar)
        except:
            warn("Could not import netcdftime. Using fallback computation")
            return cls.extract_netcdf_time_fallback(bandName)

    @classmethod
    def extract_netcdf_time(cls, bandName, calendar):
        """Convert netcdf time to datetime using appropriate library"""
        from netcdftime import utime
        epoch, units = cls.extract_epoch_units(bandName)
        cdftime = utime(units, calendar)
        timestamps = cdftime.num2date([epoch])
        return timestamps[0]

    @classmethod
    def extract_epoch_units(cls, bandName):
        # Band name expected to be like: 'Band 1: time=20116800 (minutes since 1970-01-01 00:00:00)'
        pattern = "time=(\d+)\s*[(](.+)[)]"
        matches = re.findall(pattern, bandName)[0]
        return int(matches[0]), matches[1]

    @classmethod
    def extract_netcdf_time_fallback(cls, bandName):
        """Fallback when netcdftime module isn't installed"""
        epoch, units = cls.extract_epoch_units(bandName)
        if "minutes" in units or "minutes" in bandName:
            epoch = epoch * 60  # the number is originally in minutes, so need to multiply by 60
        return time_util.epoch_to_datetime(epoch)

    @classmethod
    def extract_netcdf_time_using_netcdf4_library(cls, bandnum, dataset_time):
        time = dataset_time
        try:
            units, start_date = time.units.split(
                ' since ')  # ex: minutes since 1970-01-01 00:00:00 or 'days since 2002-01-01T00:00:00Z'
        except:
            units, start_date = time.Units.split(
                ' since ')  # Handle exception for NASA products(Units instead of units) Like:CSR_GRACE_GRACE-FO_RL06_Mascons_all-corrections_v02.nc
        decimal_offset = float(time[bandnum])
        this_date = time_util.date_offset_from_start(start_date, units, decimal_offset)
        return this_date

    @classmethod
    def get_first_band_between(cls, dts_time, dts, start_dt, end_dt):
        """Get the index of the band whose timestamp is greater or equal to
        the starttime, but smaller than the endtime. If no such band is present,
        use the previous band"""
        # TODO find later a faster way which takes advantage of the sorting 
        # idx = np.searchsorted(self.band_to_dt, start_dt, side='right')
        # from netCDF4 import date2index
        # idx = date2index(start_dt, dts_time, select='after')
        # return idx

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
        # TODO
        # More precise work and examples are needed
        p = self.layer.dataProvider()
        cnt = p.bandCount()
        try:

            self.band_to_dt = []
            for i in range(0, cnt):
                self.band_to_dt.append(
                    self.extract_netcdf_time_using_netcdf4_library(i, self.dataset_time))
        except:
            self.band_to_dt = []
            for i in range(1, cnt + 1):
                self.band_to_dt.append(self.extract_time_from_bandname(p.generateBandName(i), self.calendar))

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
            try:
                layerStartTime = self.extract_netcdf_time_using_netcdf4_library(1, self.dataset_time)
            except:
                layerStartTime = self.extract_time_from_bandname(
                    self.layer.dataProvider().generateBandName(1))
            self.hideOrShowLayer(startTime, endTime, layerStartTime, layerStartTime)
            return
        else:
            # TODO
            # More work is needed to handle decimal time units like 1236.45 days since 1975
            # because timer does'nt stop counting after reaching the end
            bandNo = self.get_first_band_between(self.dataset_time, self.band_to_dt, startTime, endTime)
            self.layer.renderer().setBand(bandNo)

    def deleteTimeRestriction(self):
        """The layer is removed from Time Manager and is therefore always shown"""
        if not self.is_multiband(self.layer):
            self.show()
            return
        else:
            self.layer.renderer().setBand(1)
