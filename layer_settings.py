__author__ = 'carolinux'

"""Helper functions that manage getting layer settings from a variety of sources - the timelayer 
layer, the addLayerOptions gui, the widget table and the save string"""
from qgis.core import *
from PyQt4.QtCore import *
from time_util import DEFAULT_FORMAT
import conf
from timelayerfactory import TimeLayerFactory
from timevectorlayer import TimeVectorLayer
from timevectorinterpolatedlayer import TimeVectorInterpolatedLayer
from timelayer import InvalidTimeLayerError

def getSettingsFromSaveStr(saveStr):
    l = saveStr.split(';')
    layer = QgsMapLayerRegistry.instance().mapLayer(l[0]) # get the layer
    if not layer:
        raise InvalidTimeLayerError(Exception())

    timeLayerClass = TimeLayerFactory.get_timelayer_class_from_layer(layer)
    if timeLayerClass == TimeVectorLayer:# FFIXME semantics
        layer.setSubsetString(l[1]) # restore the original subset string, only available for vector layers!

    startTimeAttribute=l[2]
    endTimeAttribute=l[3]
    isEnabled=l[4]
    timeFormat=l[5]

    try:
        offset=l[6]
    except IndexError: # old versions didn't have an offset option
        offset=0
    idAttr=None
    interpolation_enabled=False #FFIXME
    return (layer,isEnabled,offset,timeFormat,startTimeAttribute,
                                  endTimeAttribute,interpolation_enabled, idAttr)

def getSettingsFromAddLayersUI(ui, layerIdToIdxMap):
    layerName = ui.comboBoxLayers.currentText()
    startTime = ui.comboBoxStart.currentText()
    endTime = ui.comboBoxEnd.currentText()
    enabled = True
    layerId =  layerIdToIdxMap[ui.comboBoxLayers.currentIndex()] #???
    timeFormat = DEFAULT_FORMAT #FIXME huh?
    offset = ui.spinBoxOffset.value()
    interpolation_mode = ui.comboBoxInterpolation.currentText()
    interpolation_enabled = conf.INTERPOLATION_MODES[interpolation_mode]
    idAttr = ui.comboBoxID.currentText() if interpolation_enabled else None
    idAttr = "" if idAttr==conf.NO_ID_TEXT else idAttr
    return (layerName,enabled,layerId,offset,timeFormat,startTime,
                                  endTime,interpolation_enabled, idAttr)


def getSettingsFromRow(table, rowNum):
    """Get settings from table widget rowNum"""
    layer=QgsMapLayerRegistry.instance().mapLayer(table.item(rowNum,4).text())
    isEnabled = (table.item(rowNum,3).checkState() ==
                 Qt.Checked)
    # offset
    offset = int(table.item(rowNum,6).text()) # currently

    startTimeAttribute = table.item(rowNum,1).text()
    # end time (optional)
    if table.item(rowNum,2).text() == "":
        endTimeAttribute = startTimeAttribute
    else:
        endTimeAttribute = table.item(rowNum,2).text()

    # time format
    timeFormat = table.item(rowNum,5).text()
    interpolation_enabled =(table.item(rowNum,7).checkState()
                            ==  Qt.Checked)
    idAttr = table.item(rowNum,8).text()
    if idAttr =="":
        idAttr = None
    
    return (layer,isEnabled,None,offset,timeFormat,
            startTimeAttribute,endTimeAttribute,interpolation_enabled, idAttr)

def getSettingsFromLayer(layer):
    """Get the timelayer's settings as a tuple"""

    layerName=layer.getName()
    enabled = layer.isEnabled()
    layerId=layer.getLayerId()
    offset=layer.getOffset()

    times=layer.getTimeAttributes()
    startTime=times[0]
    if times[0] != times[1]: # end time equals start time for timeLayers of type timePoint
        endTime = times[1]
    else:
        endTime = ""
    timeFormat= layer.getTimeFormat()
    interpolation_enabled = layer.isInterpolationEnabled()
    if interpolation_enabled:
        idAttr = "" if not layer.hasIdAttribute() else layer.getIdAttribute()
    else:
        idAttr = ""

    return (layerName,enabled,layerId,offset,timeFormat,startTime,
                                  endTime,interpolation_enabled, idAttr)