from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from PyQt4 import QtGui as QtGui
from qgis._core import QgsMapLayerRegistry
import re

import qgis_utils as qgs
import layer_settings as ls
import conf
from vectorlayerdialog import AddLayerDialog
from logging import info, warn, error

class RasterLayerDialog(AddLayerDialog):
    TIME_REGEX = "([^\d])*(\d[\d_:\\-\.]*\d)([^\d])*"

    def __init__(self, *args):
        super(RasterLayerDialog, self).__init__(*args)
    
    def extract_settings(self):
        return ls.getSettingsFromAddRasterLayersUI(self.dialog, self.tempLayerIndexToId)

    def add_connections(self):
        super(RasterLayerDialog, self).add_connections()
        self.dialog.spinBoxStart1.valueChanged.connect(self.refreshStart)
        self.dialog.spinBoxStart2.valueChanged.connect(self.refreshStart)
        self.dialog.spinBoxEnd1.valueChanged.connect(self.refreshEnd)
        self.dialog.spinBoxEnd2.valueChanged.connect(self.refreshEnd)

        self.dialog.checkBoxStart.stateChanged.connect(self.refreshStart)
        self.dialog.checkBoxEnd.stateChanged.connect(self.refreshEnd)

    def show(self):
        idsToIgnore = set(self.get_ids_already_in_out_table())
        allRasterIds = set(qgs.getAllLayerIds(lambda x:qgs.isRaster(x)))
        try:
            self.populate(allRasterIds - idsToIgnore)
        except Exception,e:
            warn(e)
            return
        self.dialog.show()

    def guess_time_position_in_str(self, str_with_time):
        try:
            m = re.match(TIME_REGEX, str_with_time)
            return m.start(2), m.end(2)
        except:
            return (0,0)

    def refreshStart(self, ignore_val=0):
        if self.dialog.checkBoxStart.checkState() == Qt.Checked:
            start = self.dialog.spinBoxStart1.value()
            end = self.dialog.spinBoxStart2.value()
            self.dialog.textStart.setText(self.getSelectedLayerName()[start:end])

    def refreshEnd(self, ignore_val=0):
        if self.dialog.checkBoxEnd.checkState() == Qt.Checked:
            start = self.dialog.spinBoxEnd1.value()
            end = self.dialog.spinBoxEnd2.value()
            self.dialog.textEnd.setText(self.getSelectedLayerName()[start:end])

    def add_layer_attributes(self, idx):
        """get list layer attributes, fill the combo boxes"""
        name = self.getSelectedLayerName()
        start, end = self.guess_time_position_in_str(name)
        self.dialog.spinBoxStart1.setValue(start)
        self.dialog.spinBoxStart2.setValue(end)
