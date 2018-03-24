#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""Helper functions that interface with the QGIS API"""
from __future__ import absolute_import
from builtins import str

__author__ = 'carolinux'

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QVariant

from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject

try:
    from qgis.core import QgsMapLayerRegistry, QGis as Qgis
except ImportError:
    from qgis.core import Qgis, QgsWkbTypes

from .tmlogging import warn


def getAllJoinIdsOfLayer(layer):
    if not hasattr(layer, 'vectorJoins'):
        # open layers don't have this
        return set()
    return set([x.joinLayerId for x in layer.vectorJoins()])


def isDelimitedText(layer):
    return not isRaster(layer) and layer.dataProvider().storageType() == "Delimited text file"


def isNumericField(layer, field):
    fields = getLayerFields(layer)
    idx = layer.fields().indexFromName(field)
    typ = fields[idx].type()
    return typ == QVariant.Int or typ == QVariant.LongLong or typ == QVariant.ULongLong or typ == QVariant.Double


def getVersion():
    return Qgis.QGIS_VERSION_INT


def getLayers():
    if hasattr(QgsProject, "mapLayers"):
        return QgsProject.instance().mapLayers()
    else:
        return QgsMapLayerRegistry.instance().mapLayers()


def getLayerFromId(layerId):
    if hasattr(QgsProject, "mapLayer"):
        layer = QgsProject.instance().mapLayer(layerId)
    else:
        layer = QgsMapLayerRegistry.instance().mapLayer(layerId)

    if layer is None:
        warn("Could not get layer for id {}".format(layerId))
        return None

    return layer


def getAllJoinedLayers(layerIds):
    """Get the ids of the layers that are joined on the given layerIds"""
    allJoined = set()
    allLayers = getLayers()
    for (id, layer) in list(allLayers.items()):
        if isRaster(layer):
            continue
        if id in layerIds:  # let's see what the given layers are joined on
            allJoined |= getAllJoinIdsOfLayer(layer)
        else:  # let's see if the other layers join with the given layers
            joinsOfCurrentLayer = getAllJoinIdsOfLayer(layer)
            if len(joinsOfCurrentLayer & layerIds) > 0:
                allJoined.add(id)

    return allJoined


def getLayerFields(layer):
    if hasattr(layer, "pendingFields"):
        return layer.pendingFields()
    else:
        return layer.fields()


def getLayerAttributes(layerId):
    try:
        layer = getLayerFromId(layerId)
        fieldmap = getLayerFields(layer)
        # TODO figure out what to do for fields with
        # fieldmap.fieldOrigin(idx) = QgsFields.OriginEdit/OriginExpression
        return fieldmap
    except Exception:
        # OpenLayers, Raster layers don't work with this
        warn("Could not get attributes of layer {}".format(layerId))
        return None


def getAllLayerIds(filter_func):
    res = []
    for (id, layer) in list(getLayers().items()):
        if filter_func(layer):
            res.append(id)
    return res


def isRaster(layer):
    return type(layer) == QgsRasterLayer


def isWFS(layer):
    if type(layer) == QgsVectorLayer:
        return layer.dataProvider().description() == u'WFS data provider'
    else:
        return False


def doesLayerNameExist(name):
    return getIdFromLayerName(name) is not None


def getIdFromLayerName(layerName):
    layer = getLayerFromLayerName(layerName)
    return layer.id() if layer is not None else None


def getLayerFromLayerName(layerName):
    if hasattr(QgsProject, "mapLayersByName"):
        layers = QgsProject.instance().mapLayersByName(layerName)
    else:
        layers = QgsMapLayerRegistry.instance().mapLayersByName(layerName)

    if len(layers) > 0:
        return layers[0]
    else:
        return None


def getNameFromLayerId(layerId):
    return str(getLayerFromId(layerId).name())


def getRenderer(layer):
    if hasattr(layer, "rendererV2"):
        return layer.rendererV2()
    else:
        return layer.renderer()


def getLayerColor(layer):
    renderer = getRenderer(layer)
    symbol = renderer.symbol()
    return symbol.color().name()


def getLayerSize(layer):
    renderer = getRenderer(layer)
    symbol = renderer.symbol()
    return symbol.size()


def setLayerColor(layer, color_name):
    renderer = getRenderer(layer)
    symbol = renderer.symbol()
    symbol.setColor(QColor(color_name))


def setLayerSize(layer, size):
    renderer = getRenderer(layer)
    symbol = renderer.symbol()
    symbol.setSize(size)


def setLayerTransparency(layer, alpha):
    renderer = getRenderer(layer)
    symbol = renderer.symbol()
    symbol.setAlpha(alpha)


def refreshSymbols(iface, layer):
    if hasattr(iface, "legendInterface"):
        iface.legendInterface().refreshLayerSymbology(layer)
    else:
        node = QgsProject.instance().layerTreeRoot().findLayer(layer)
        iface.layerTreeView().layerTreeModel().refreshLayerLegend(node)
    iface.mapCanvas().refresh()


def addLayer(layer):
    if hasattr(QgsProject, "addMapLayer"):
        QgsProject.instance().addLayer(layer)
    else:
        QgsMapLayerRegistry.instance().addLayer(layer)


def removeLayer(layerId):
    if hasattr(QgsProject, "removeMapLayer"):
        QgsProject.instance().removeMapLayer(layerId)
    else:
        QgsMapLayerRegistry.instance().removeMapLayer(layerId)


def isPointLayer(layer):
    if hasattr(Qgis, "Point"):
        return layer.geometryType() == Qgis.Point
    else:
        return layer.geometryType() == QgsWkbTypes.PointGeometry


def isPointGeometry(geom):
    if hasattr(Qgis, "Point"):
        return geom.type() == Qgis.Point
    else:
        return geom.type() == QgsWkbTypes.PointGeometry
