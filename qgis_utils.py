from PyQt4.QtGui import QColor
from qgis._core import QgsMapLayerRegistry, QgsMessageLog

__author__ = 'carolinux'


def getLayerAttributes(layerId):
    try:
        layer=QgsMapLayerRegistry.instance().mapLayers()[layerId]
        #QgsMessageLog.logMessage(str(QgsMapLayerRegistry.instance().mapLayers()))
        #QgsMessageLog.logMessage("layer"+str(layer))
        provider=layer.dataProvider() # this will crash on OpenLayers layers
        fieldmap=provider.fields() # this function will crash on raster layers
        return fieldmap
    except:
        QgsMessageLog.logMessage("Could not get attributes of layer {}".format(layerId))
        return None


def doesLayerNameExist(name):
    return getIdFromLayerName(name) is not None

def getIdFromLayerName(layerName):
    # Important: If multiple layers with same name exist, it will return the first one it finds
    for (id, layer) in QgsMapLayerRegistry.instance().mapLayers().iteritems():
        if unicode(layer.name())==layerName:
            return id
    return None

def getLayerFromLayerName(layerName):
    # Important: If multiple layers with same name exist, it will return the first one it finds
    for (id, layer) in QgsMapLayerRegistry.instance().mapLayers().iteritems():
        if unicode(layer.name())==layerName:
            return layer
    return None

def getNameFromLayerId(layerId):
    layer =  QgsMapLayerRegistry.instance().mapLayers()[layerId]
    return unicode(layer.name())

def getLayerColor(layer):
    renderer = layer.rendererV2()
    symbol = renderer.symbol()
    return symbol.color().name()

def getLayerSize(layer):
    renderer = layer.rendererV2()
    symbol = renderer.symbol()
    return symbol.size()

def setLayerColor(layer, color_name):
    renderer = layer.rendererV2()
    symbol = renderer.symbol()
    symbol.setColor(QColor(color_name))


def setLayerSize(layer, size):
    renderer = layer.rendererV2()
    symbol = renderer.symbol()
    symbol.setSize(size)

def setLayerTransparency(layer, alpha):
    renderer = layer.rendererV2()
    symbol = renderer.symbol()
    symbol.setAlpha(alpha)

def refreshSymbols(iface, layer):
    iface.legendInterface().refreshLayerSymbology(layer)
    iface.mapCanvas().refresh()
