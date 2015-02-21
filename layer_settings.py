__author__ = 'carolinux'

"""Helper functions that manage getting layer settings from a variety of sources - the timelayer 
layer, the addLayerOptions gui, the widget table and the save string"""
from qgis.core import *
from PyQt4.QtCore import *
from time_util import DEFAULT_FORMAT
import conf
import time_util


class LayerSettings:
    def __init__(self):
        self.layer = None
        self.layerName = ''
        self.layerId = ''
        self.startTimeAttribute = ''
        self.endTimeAttribute = ''
        self.isEnabled = True
        self.timeFormat = time_util.DEFAULT_FORMAT
        self.offset = 0
        self.interpolationEnabled = False
        self.interpolationMode = '' # TODO: when we have multiple modes, work on this
        self.idAttribute = ''
        self.subsetStr = ''

def getSettingsFromSaveStr(saveStr):
    l = saveStr.split(';')
    result = LayerSettings()
    result.layerId = l[0]
    result.layer = QgsMapLayerRegistry.instance().mapLayer(result.layerId) # get the layer
    result.startTimeAttribute=l[2]
    result.subsetStr = l[1]
    result.endTimeAttribute=l[3]
    result.isEnabled=l[4]
    result.timeFormat=l[5]

    try:
        result.offset=l[6]
    except IndexError: # old versions didn't have an offset option
        pass

    result.idAttribute=''
    result.interpolationEnabled = False #FFIXME, actually take values
    return result

def getSettingsFromAddLayersUI(ui,layerIndexToId):
    result = LayerSettings()
    result.layerName = ui.comboBoxLayers.currentText()
    result.startTimeAttribute = ui.comboBoxStart.currentText()
    result.endTimeAttribute = ui.comboBoxEnd.currentText()
    result.isEnabled = True
    result.layerId =  layerIndexToId[ui.comboBoxLayers.currentIndex()]
    result.timeFormat = DEFAULT_FORMAT
    result.offset = ui.spinBoxOffset.value()
    result.interpolationMode = ui.comboBoxInterpolation.currentText()
    result.interpolationEnabled = conf.INTERPOLATION_MODES[result.interpolationMode]
    result.idAttribute= ui.comboBoxID.currentText() if result.interpolationEnabled else None
    result.idAttribute = "" if result.idAttribute==conf.NO_ID_TEXT else result.idAttribute
    return result


def getSettingsFromRow(table, rowNum):
    """Get settings from table widget rowNum"""
    result = LayerSettings()
    result.layer=QgsMapLayerRegistry.instance().mapLayer(table.item(rowNum,4).text())
    result.subsetStr = result.layer.subsetString()
    result.isEnabled = (table.item(rowNum,3).checkState() ==
                 Qt.Checked)
    # offset
    result.offset = int(table.item(rowNum,6).text()) # currently

    result.startTimeAttribute = table.item(rowNum,1).text()
    # end time (optional)
    if table.item(rowNum,2).text() == "":
        result.endTimeAttribute = result.startTimeAttribute
    else:
        result.endTimeAttribute = table.item(rowNum,2).text()

    # time format
    result.timeFormat = table.item(rowNum,5).text()
    result.interpolationEnabled =(table.item(rowNum,7).checkState() ==  Qt.Checked)
    result.idAttribute = table.item(rowNum,8).text()
    
    return result

def getSettingsFromLayer(layer):
    """Get the timelayer's settings as a tuple"""
    result = LayerSettings()
    result.layer = layer
    result.layerName=layer.getName()
    result.isEnabled = layer.isEnabled()
    result.layerId=layer.getLayerId()
    result.offset=layer.getOffset()
    result.subsetStr = layer.getOriginalSubsetString()
    times=layer.getTimeAttributes()
    result.startTimeAttribute=times[0]
    result.endTimeAttribute = times[1]
    result.timeFormat= layer.getTimeFormat()
    result.InterpolationEnabled = layer.isInterpolationEnabled()
    if result.InterpolationEnabled:
        result.idAttribute = "" if not layer.hasIdAttribute() else layer.getIdAttribute()
    else:
        result.idAttribute = ""
    return result