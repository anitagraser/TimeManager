__author__ = 'carolinux'

from qgis.core import QgsVectorLayer, QgsRasterLayer

from timevectorlayer import TimeVectorLayer
from timerasterlayer import TimeRasterLayer
from timevectorinterpolatedlayer import TimeVectorInterpolatedLayer


classes_with_subsetStr = [TimeVectorLayer,]

class TimeLayerFactory:
    """Helper class to determine the class of the time layer ot create"""
    @classmethod
    def get_timelayer_class_from_layer(cls, layer, interpolate=False):
        if type(layer) == QgsVectorLayer and not interpolate:
            return TimeVectorLayer
        elif type(layer) == QgsVectorLayer and interpolate:
            return TimeVectorInterpolatedLayer
        elif type(layer) == QgsRasterLayer:
            return TimeRasterLayer
        raise Exception("Invalid layer type {}".format(type(layer)))
