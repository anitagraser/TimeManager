import re

from PyQt4.QtCore import *
from PyQt4.QtGui import QMessageBox

import qgis_utils as qgs
import layer_settings as ls
import conf
from vectorlayerdialog import AddLayerDialog
from tmlogging import info, warn
from raster.cdflayer import CDFRasterLayer


class RasterLayerDialog(AddLayerDialog):
    TIME_REGEX = "([^\d])*(\d[\d_:\\-\.]*\d)([^\d])*"

    startChecked = False
    endChecked = False
    textStart = ""
    textEnd = ""

    def __init__(self, *args):
        super(RasterLayerDialog, self).__init__(*args)
        self.dialog.textStart.setText(self.textStart)
        self.dialog.textEnd.setText(self.textEnd)

    def extract_settings(self):
        return ls.getSettingsFromAddRasterLayersUI(self.dialog, self.tempLayerIndexToId)

    def add_connections(self):
        super(RasterLayerDialog, self).add_connections()
        self.dialog.checkBoxStart.setChecked(
            Qt.Checked if RasterLayerDialog.startChecked else Qt.Unchecked)
        self.dialog.checkBoxEnd.setChecked(
            Qt.Checked if RasterLayerDialog.endChecked else Qt.Unchecked)
        self.dialog.spinBoxStart1.valueChanged.connect(self.refreshStart)
        self.dialog.spinBoxStart2.valueChanged.connect(self.refreshStart)
        self.dialog.spinBoxEnd1.valueChanged.connect(self.refreshEnd)
        self.dialog.spinBoxEnd2.valueChanged.connect(self.refreshEnd)

        self.dialog.checkBoxStart.stateChanged.connect(self.refreshStart)
        self.dialog.checkBoxEnd.stateChanged.connect(self.refreshEnd)
        self.dialog.isCDF.stateChanged.connect(self.handleCDF)

    def haveNetCDF(self):
        try:
            import netCDF4
            import netcdftime
            return True
        except:
            return False

    def handleCDF(self, checkState):
        isCDF = checkState == Qt.Checked
        if isCDF and qgs.getVersion() < conf.MIN_RASTER_MULTIBAND:
            QMessageBox.information(self.iface.mainWindow(), 'Info',
                                    'QGIS 2.10 and higher is recommended for this feature')
        if isCDF and not CDFRasterLayer.isSupportedRaster(self.getSelectedLayer()):
            self.dialog.isCDF.setCheckState(Qt.Unchecked)
            QMessageBox.information(self.iface.mainWindow(), 'Error',
                                    'To use this feature the raster should be using the ' +
                                    'QgsSingleBandPseudoColorRenderer (can choose from Properties)')
            return
        if isCDF and not self.haveNetCDF():
            QMessageBox.information(self.iface.mainWindow(), 'Info',
                                    'For full CDF support please pip install netCDF4')

        enable = not isCDF
        self.dialog.checkBoxEnd.setEnabled(enable)
        self.dialog.checkBoxStart.setEnabled(enable)
        self.dialog.spinBoxStart1.setEnabled(enable)
        self.dialog.spinBoxStart2.setEnabled(enable)
        self.dialog.spinBoxEnd1.setEnabled(enable)
        self.dialog.spinBoxEnd2.setEnabled(enable)
        self.dialog.textStart.setEnabled(enable)
        self.dialog.textEnd.setEnabled(enable)

    def show(self):
        idsToIgnore = set(self.get_ids_already_in_out_table())
        allRasterIds = set(qgs.getAllLayerIds(lambda x: qgs.isRaster(x)))
        self.clear()
        try:
            self.populate(allRasterIds - idsToIgnore)
        except Exception, e:
            warn(e)
            return
        self.dialog.show()

    @classmethod
    def guess_time_position_in_str(cls, str_with_time):
        try:
            m = re.match(cls.TIME_REGEX, str_with_time)
            return m.start(2), m.end(2)
        except Exception, e:
            info("Could not guess timestamp in raster filename. Cause {}".format(e))
            return (0, 0)

    def refreshStart(self, ignore_val=0):
        if self.dialog.checkBoxStart.checkState() == Qt.Checked:
            RasterLayerDialog.startChecked = True
            start = self.dialog.spinBoxStart1.value()
            end = self.dialog.spinBoxStart2.value()
            self.dialog.textStart.setText(self.getSelectedLayerName()[start:end])
        else:
            RasterLayerDialog.startChecked = False

    def refreshEnd(self, ignore_val=0):
        if self.dialog.checkBoxEnd.checkState() == Qt.Checked:
            RasterLayerDialog.endChecked = True
            start = self.dialog.spinBoxEnd1.value()
            end = self.dialog.spinBoxEnd2.value()
            self.dialog.textEnd.setText(self.getSelectedLayerName()[start:end])
        else:
            RasterLayerDialog.endChecked = False

    def add_layer_attributes(self, idx):
        """get list layer attributes, fill the combo boxes"""
        name = self.getSelectedLayerName()
        start, end = self.guess_time_position_in_str(name)
        self.dialog.spinBoxStart1.setValue(start)
        self.dialog.spinBoxStart2.setValue(end)
