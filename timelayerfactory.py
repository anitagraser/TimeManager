__author__ = 'carolinux'

from qgis.core import QgsVectorLayer, QgsRasterLayer

from timevectorlayer import TimeVectorLayer
from timerasterlayer import TimeRasterLayer
from timevectorinterpolatedlayer import TimeVectorInterpolatedLayer
from raster.cdflayer import CDFRasterLayer
from raster.wmstlayer import WMSTRasterLayer
import time_util


class TimeLayerFactory:
    """Helper class to determine the class of the time layer to create"""

    @classmethod
    def get_timelayer_class_from_settings(cls, settings):
        layer = settings.layer
        interpolate = settings.interpolationEnabled
        isNetCDF = settings.timeFormat == time_util.NETCDF_BAND
        if type(layer) == QgsVectorLayer and not interpolate:
            return TimeVectorLayer
        elif type(layer) == QgsVectorLayer and interpolate:
            return TimeVectorInterpolatedLayer
        elif type(layer) == QgsRasterLayer:
            if "Web Map Service" in layer.dataProvider().description():
                return WMSTRasterLayer
            if isNetCDF:
                return CDFRasterLayer
            else:
                return TimeRasterLayer
        raise Exception("Invalid layer type {}".format(type(layer)))
