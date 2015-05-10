import abc
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from PyQt4 import QtGui as QtGui
from qgis._core import QgsMapLayerRegistry

import qgis_utils as qgs
import layer_settings as ls
import conf
from logging import info, warn, error

class AddLayerDialog:
    __metaclass__ = abc.ABCMeta

    def __init__(self, ui_path, out_table):
        self.tempLayerIndexToId = {}
        self.dialog = uic.loadUi(ui_path)
        self.out_table = out_table
        # TODO assert it has a buttonbox and comboBoxLayers

    def getDialog(self):
        return self.dialog

    def getSelectedLayerName(self):
        return self.dialog.comboBoxLayers.currentText()

    def get_ids_already_in_out_table(self):
        """get list of layer ids listed in the tableWidget"""
        layerList=[]
        if self.out_table is None:
            return layerList
        for row in range(self.out_table.rowCount()):
            layerId=self.out_table.item(row,4).text()
            layerList.append(layerId)
        return layerList


    def add_layer_to_select(self, name):
        self.dialog.comboBoxLayers.addItem(name)

    def layer_count(self):
        return self.dialog.comboBoxLayers.count()

    def populate(self, layerIds):
        self.tempLayerIndexToId = {}
        i = 0
        for (id,layer) in QgsMapLayerRegistry.instance().mapLayers().iteritems():
            if id in layerIds:
                unicode_name = unicode(layer.name())
                self.add_layer_to_select(unicode_name)
                self.tempLayerIndexToId[i] = id
                i+=1

        if self.layer_count()== 0:
            msg = 'There are no unmanaged layers of requested type in the project!'
            QMessageBox.information(self.dialog,'Error', msg)
            raise Exception(msg)

        # add the attributes of the first layer in the select for gui initialization
        self.add_layer_attributes(0)
        self.add_connections()
     
    @abc.abstractmethod
    def add_layer_attributes(self, id):
       pass

    def add_layer_to_table(self):
        """Add selected layer attributes to table"""
        settings  = self.extract_settings()
        ls.addSettingsToRow(settings, self.out_table)
        

    @abc.abstractmethod
    def extract_settings(self):
        pass

    @abc.abstractmethod
    def show(self):
        pass

    def add_connections(self):
        self.dialog.comboBoxLayers.currentIndexChanged.connect(self.add_layer_attributes)
        self.dialog.buttonBox.accepted.connect(self.add_layer_to_table)

class VectorLayerDialog(AddLayerDialog):

    def __init__(self, *args):
        super(VectorLayerDialog, self).__init__(*args)
    
    def extract_settings(self):
        return ls.getSettingsFromAddVectorLayersUI(self.dialog, self.tempLayerIndexToId)
    
    def add_layer_attributes(self, idx):
        """get list layer attributes, fill the combo boxes"""
        layerId = self.tempLayerIndexToId[self.dialog.comboBoxLayers.currentIndex()]
        fieldmap = qgs.getLayerAttributes(layerId)
        if fieldmap is None:
            return
        self.dialog.comboBoxStart.clear()
        self.dialog.comboBoxEnd.clear()
        self.dialog.comboBoxID.clear()
        self.dialog.comboBoxEnd.addItem('') # this box is optional, so we add an empty item
        self.dialog.comboBoxID.addItem(conf.NO_ID_TEXT)
        for attr in fieldmap: 
            self.dialog.comboBoxStart.addItem(attr.name())
            self.dialog.comboBoxEnd.addItem(attr.name())
            self.dialog.comboBoxID.addItem(attr.name())

    def add_connections(self):

        super(VectorLayerDialog, self).add_connections()
        QObject.connect(self.dialog.comboBoxInterpolation,SIGNAL("currentIndexChanged(const QString &)"),
            self.maybeEnableIDBox)
        self.dialog.exportEmptyCheckbox.setChecked(Qt.Unchecked)

    def show(self):
        idsToIgnore = set(self.get_ids_already_in_out_table())
        allVectorIds = set(qgs.getAllLayerIds(lambda x:not qgs.isRaster(x)))
        try:
            self.populate(allVectorIds - idsToIgnore)
        except Exception,e:
            warn(e)
            return
        self.add_interpolation_modes(self.dialog.comboBoxInterpolation)
        self.dialog.show()
       

    def maybeEnableIDBox(self, interpolation_mode):
        if conf.INTERPOLATION_MODES[interpolation_mode]:
            self.dialog.comboBoxID.setEnabled(True)
            self.dialog.labelID1.setEnabled(True)
            self.dialog.labelID2.setEnabled(True)
            self.dialog.comboBoxEnd.setEnabled(False) # end field not yet supported when
            #  interpolating
        else:
            self.dialog.comboBoxID.setEnabled(False)
            self.dialog.labelID1.setEnabled(False)
            self.dialog.labelID2.setEnabled(False)
            self.dialog.comboBoxEnd.setEnabled(True) 

    def add_interpolation_modes(self, comboBox):
        comboBox.clear()
        comboBox.addItem(conf.NO_INTERPOLATION)
        for mode in conf.INTERPOLATION_MODE_TO_CLASS.keys():
            comboBox.addItem(mode)
