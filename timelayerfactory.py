__author__ = 'carolinux'

from qgis.core import QgsVectorLayer, QgsRasterLayer

from timevectorlayer import TimeVectorLayer
from timerasterlayer import TimeRasterLayer

class TimeLayerFactory:
    """Helper class to determine the class of the time layer ot create"""
    @classmethod
    def get_timelayer_class_from_layer(cls, layer):
        if type(layer) == QgsVectorLayer:
            return TimeVectorLayer
        elif type(layer) == QgsRasterLayer:
            return TimeRasterLayer