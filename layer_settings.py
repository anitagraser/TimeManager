__author__ = 'carolinux'

"""Helper functions that manage getting layer settings from a variety of sources - the timelayer
layer, the addLayerOptions gui, the widget table and the save string"""
from qgis.core import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from time_util import PENDING
import conf
import time_util


def textToBool(text):
    if text.lower() == "false":
        return False
    if text.lower() == "true":
        return True
    raise Exception("Invalid boolean string {}".format(text))


class LayerSettings:
    def __init__(self):
        self.layer = None
        self.layerName = ''
        self.layerId = ''
        self.startTimeAttribute = ''
        self.endTimeAttribute = ''
        self.isEnabled = True
        self.timeFormat = time_util.PENDING
        self.offset = 0
        self.interpolationEnabled = False
        self.interpolationMode = conf.NO_INTERPOLATION
        self.idAttribute = ''
        self.subsetStr = ''
        self.geometriesCount = True
        self.accumulate = False


def getSettingsFromSaveStr(saveStr):
    l = saveStr.split(conf.SAVE_DELIMITER)
    result = LayerSettings()
    result.layerId = l[0]
    result.layer = QgsMapLayerRegistry.instance().mapLayer(result.layerId)  # get the layer
    result.startTimeAttribute = l[2]
    result.subsetStr = l[1]
    result.endTimeAttribute = l[3]
    result.isEnabled = textToBool(l[4])
    result.timeFormat = l[5]
    try:
        result.offset = int(l[6])
        result.idAttribute = l[7]
        result.interpolationEnabled = textToBool(l[8])
        result.interpolationMode = l[9]
        result.geometriesCount = l[10]
        result.accumulate = textToBool(l[11])
    except IndexError:  # for backwards compatibility
        pass  # this will use default values
    return result


def extractEndTimeSettings(ui, startTime):
    """ Get the settings for endtime from the ui, according
    to how comboBoxEnd is initialized in vectorlayerdialog"""
    if ui.comboBoxEnd.currentIndex() == 0:
        return startTime, False
    if ui.comboBoxEnd.currentIndex() == 1:
        return "", True
    return ui.comboBoxEnd.currentText(), False


def getSettingsFromAddVectorLayersUI(ui, layerIndexToId):
    result = LayerSettings()
    result.layerName = ui.comboBoxLayers.currentText()
    result.startTimeAttribute = ui.comboBoxStart.currentText()
    result.endTimeAttribute, result.accumulate = extractEndTimeSettings(ui,
                                                                        result.startTimeAttribute)
    result.isEnabled = True
    result.layerId = layerIndexToId[ui.comboBoxLayers.currentIndex()]
    result.timeFormat = time_util.PENDING
    result.offset = ui.spinBoxOffset.value()
    result.interpolationMode = ui.comboBoxInterpolation.currentText()
    result.interpolationEnabled = conf.INTERPOLATION_MODES[result.interpolationMode]
    result.idAttribute = ui.comboBoxID.currentText() if result.interpolationEnabled else None
    result.idAttribute = "" if result.idAttribute == conf.NO_ID_TEXT else result.idAttribute
    result.geometriesCount = not ui.exportEmptyCheckbox.checkState() == Qt.Checked
    return result


def getSettingsFromAddRasterLayersUI(ui, layerIndexToId):
    result = LayerSettings()
    result.layerName = ui.comboBoxLayers.currentText()
    result.startTimeAttribute = ui.textStart.text()
    result.endTimeAttribute = ui.textEnd.text()
    result.isEnabled = True
    result.layerId = layerIndexToId[ui.comboBoxLayers.currentIndex()]
    result.timeFormat = time_util.PENDING if ui.isCDF.checkState() != Qt.Checked else time_util.NETCDF_BAND
    result.offset = ui.spinBoxOffset.value()
    return result


def addSettingsToRow(settings, out_table):
    s = settings
    row = out_table.rowCount()
    out_table.insertRow(row)
    s = settings
    # insert values
    for i, value in enumerate([s.layerName, s.startTimeAttribute, s.endTimeAttribute,
                               s.isEnabled, s.layerId, s.timeFormat,
                               str(s.offset), s.interpolationEnabled, s.idAttribute,
                               s.interpolationMode,
                               not s.geometriesCount, s.accumulate]):
        item = QTableWidgetItem()
        if type(value) != bool:
            item.setText(value)
        else:
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)
        out_table.setItem(row, i, item)


def getSettingsFromRow(table, rowNum):
    """Get settings from table widget rowNum"""
    result = LayerSettings()
    result.layer = QgsMapLayerRegistry.instance().mapLayer(table.item(rowNum, 4).text())
    try:
        result.subsetStr = result.layer.subsetString()
    except:
        # raster layers do not have subset strings
        pass
    result.isEnabled = (table.item(rowNum, 3).checkState() ==
                        Qt.Checked)
    # offset
    result.offset = int(table.item(rowNum, 6).text())  # currently

    result.startTimeAttribute = table.item(rowNum, 1).text()
    result.endTimeAttribute = table.item(rowNum, 2).text()
    # time format
    result.timeFormat = table.item(rowNum, 5).text()
    result.interpolationEnabled = (table.item(rowNum, 7).checkState() == Qt.Checked)
    result.idAttribute = table.item(rowNum, 8).text()
    result.interpolationMode = table.item(rowNum, 9).text()
    result.geometriesCount = not (table.item(rowNum, 10).checkState() == Qt.Checked)
    result.accumulate = (table.item(rowNum, 11).checkState() == Qt.Checked)

    return result


def getSettingsFromLayer(layer):
    """Get the timelayer's settings as a tuple"""
    result = LayerSettings()
    result.layer = layer
    result.layerName = layer.getName()
    result.isEnabled = layer.isEnabled()
    result.layerId = layer.getLayerId()
    result.offset = layer.getOffset()
    result.subsetStr = layer.getOriginalSubsetString()
    times = layer.getTimeAttributes()
    result.startTimeAttribute = times[0]
    result.endTimeAttribute = times[1]
    result.timeFormat = layer.getTimeFormat()
    result.interpolationEnabled = layer.isInterpolationEnabled()
    result.interpolationMode = layer.interpolationMode()
    if result.interpolationEnabled:
        result.idAttribute = "" if not layer.hasIdAttribute() else layer.getIdAttribute()
    else:
        result.idAttribute = ""
    result.geometriesCount = layer.geometriesCountForExport()
    result.accumulate = layer.accumulateFeatures()
    return result
