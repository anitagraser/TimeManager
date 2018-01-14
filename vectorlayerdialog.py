#!/usr/bin/python
# -*- coding: UTF-8 -*-

import abc
from PyQt4 import uic
from PyQt4.QtCore import QObject, SIGNAL, Qt
from PyQt4.QtGui import QMessageBox

from qgis._core import QgsMapLayerRegistry
from tmlogging import warn

import qgis_utils as qgs
import layer_settings 
import conf


class AddLayerDialog:
    __metaclass__ = abc.ABCMeta

    def __init__(self, iface, ui_path, out_table):
        self.iface = iface
        self.tempLayerIndexToId = {}
        self.dialog = uic.loadUi(ui_path)
        self.out_table = out_table
        self.addConnections()
        # TODO assert it has a buttonbox and comboBoxLayers

    def getDialog(self):
        return self.dialog

    def getSelectedLayerName(self):
        return self.dialog.comboBoxLayers.currentText()

    def clear(self):
        self.tempLayerIndexToId = {}
        self.dialog.comboBoxLayers.clear()

    def getSelectedLayer(self):
        idx = self.dialog.comboBoxLayers.currentIndex()
        layerId = self.tempLayerIndexToId[idx]
        return qgs.getLayerFromId(layerId)

    def getIdsAlreadyInOutTable(self):
        """Get list of layer ids listed in the tableWidget"""
        layerList = []
        if self.out_table is None:
            return layerList
        for row in range(self.out_table.rowCount()):
            layerId = self.out_table.item(row, 4).text()
            layerList.append(layerId)
        return layerList

    def addLayerToSelect(self, name):
        """Add layer name to layer combo box"""
        self.dialog.comboBoxLayers.addItem(name)

    def getLayerCount(self):
        return self.dialog.comboBoxLayers.count()

    def populate(self, layerIds):
        idlayers_it = QgsMapLayerRegistry.instance().mapLayers().iteritems()
        selected_idlayers = filter(lambda idlayer: idlayer[0] in layerIds, idlayers_it)
        self.populateFromLayers(selected_idlayers)

    def populateFromLayers(self, idlayers):
        """Populate layer combo box"""
        i = 0
        for (id, layer) in idlayers:
            unicode_name = unicode(layer.name())
            self.addLayerToSelect(unicode_name)
            self.tempLayerIndexToId[i] = id
            i += 1
        if self.getLayerCount() == 0:
            msg = 'All suitable project layers have already been added to TimeManager!'
            QMessageBox.information(self.dialog, 'Error', msg)
            raise Exception(msg)
        # add the attributes of the first layer in the select for gui initialization
        self.addLayerAttributes(0)

    @abc.abstractmethod
    def addLayerAttributes(self, id):
        pass

    def addLayerToTable(self):
        """Add selected layer attributes to table"""
        settings = self.extractSettings()
        layer_settings.addSettingsToRow(settings, self.out_table)

    @abc.abstractmethod
    def extractSettings(self):
        pass

    @abc.abstractmethod
    def show(self):
        pass

    def addConnections(self):
        self.dialog.comboBoxLayers.currentIndexChanged.connect(self.addLayerAttributes)
        self.dialog.buttonBox.accepted.connect(self.addLayerToTable)


class VectorLayerDialog(AddLayerDialog):
    def __init__(self, *args):
        super(VectorLayerDialog, self).__init__(*args)

    def extractSettings(self):
        return layer_settings.getSettingsFromAddVectorLayersUI(self.dialog, self.tempLayerIndexToId)

    def addLayerAttributes(self, idx):
        """Get layer attributes and fill the combo boxes"""
        if not self.tempLayerIndexToId:
            return
        layerId = self.tempLayerIndexToId[self.dialog.comboBoxLayers.currentIndex()]
        fieldmap = qgs.getLayerAttributes(layerId)
        if fieldmap is None:
            return
        self.dialog.comboBoxStart.clear()
        self.dialog.comboBoxEnd.clear()
        self.dialog.comboBoxID.clear()
        self.dialog.comboBoxEnd.addItem('Same as start')
        self.dialog.comboBoxEnd.addItem('No end time - accumulate features')
        self.dialog.comboBoxID.addItem(conf.NO_ID_TEXT)
        for attr in fieldmap:
            self.dialog.comboBoxStart.addItem(attr.name())
            self.dialog.comboBoxEnd.addItem(attr.name())
            self.dialog.comboBoxID.addItem(attr.name())

    def addConnections(self):
        super(VectorLayerDialog, self).addConnections()
        QObject.connect(self.dialog.comboBoxInterpolation,
                        SIGNAL("currentIndexChanged(const QString &)"),
                        self.maybeEnableIDBox)
        self.dialog.exportEmptyCheckbox.setChecked(Qt.Unchecked)

    def show(self):
        """Update GUI elements and show the dialog"""
        self.clear()
        # determine which layers are vector and can be time controlled
        idsToIgnore = set(self.getIdsAlreadyInOutTable())
        allVectorIds = set(qgs.getAllLayerIds(lambda x: not qgs.isRaster(x)))
        unsupportedVectorIds = set(qgs.getAllLayerIds(lambda x: qgs.isWFS(x)))
        # todo: plugin layers, e.g. from QuickMapServices should also be excluded
        try:
            self.populate(allVectorIds - idsToIgnore - unsupportedVectorIds)
        except Exception, e:
            warn(e)
            return
        # finalize and show dialog
        self.addInterpolationModes(self.dialog.comboBoxInterpolation)
        self.dialog.show()

    def maybeEnableIDBox(self, interpolation_mode):
        if interpolation_mode != '' and conf.INTERPOLATION_MODES[interpolation_mode]:
            self.dialog.comboBoxID.setEnabled(True)
            self.dialog.labelID1.setEnabled(True)
            self.dialog.labelID2.setEnabled(True)
            self.dialog.comboBoxEnd.setEnabled(False)  # end field not yet supported when interpolating
        else:
            self.dialog.comboBoxID.setEnabled(False)
            self.dialog.labelID1.setEnabled(False)
            self.dialog.labelID2.setEnabled(False)
            self.dialog.comboBoxEnd.setEnabled(True)

    def addInterpolationModes(self, comboBox):
        comboBox.clear()
        comboBox.addItem(conf.NO_INTERPOLATION)
        for mode in conf.INTERPOLATION_MODE_TO_CLASS.keys():
            comboBox.addItem(mode)
