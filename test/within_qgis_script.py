import qgis
from qgis._core import QgsApplication, QgsVectorLayer, QgsMapLayerRegistry

from timemanager.test import testcfg as testcfg
import os
from time import sleep

__author__ = 'carolinux'

"""File that should be run within the QGIS Python console to test the application directly"""

## helper functions
def get_all_items(combobox):
    """Get all text items of a QtComboBox"""
    return [combobox.itemText(i) for i in range(combobox.count())]

def get_index_of(combobox, text):
    """Get the index of a specifix text in a QtComboBox"""
    all = get_all_items(combobox)
    print all
    return all.index(text)


## get references to timemanager controller
ctrl = qgis.utils.plugins['timemanager'].getController()
gui = ctrl.getGui()
tlm = ctrl.getTimeLayerManager()

## load tweets layer
tm_dir = os.path.join(QgsApplication.qgisSettingsDirPath(),"python","plugins","timemanager")
testfile_dir = os.path.join(tm_dir,testcfg.TEST_DATA_DIR)
tweets = QgsVectorLayer(os.path.join(testfile_dir, 'tweets.shp'), 'tweets', 'ogr')

## add layer to QGIS
QgsMapLayerRegistry.instance().addMapLayer(tweets)

## add layer to TimeManager via the GUI

gui.dock.pushButtonOptions.clicked.emit(1)
sleep(0.1)
options = gui.getOptionsDialog()
assert(options is not None)
options.pushButtonAdd.clicked.emit(1)
# select the 1965 timestamps
sleep(0.1)
gui.addLayerDialog.comboBoxStart.currentIndexChanged.emit(
    get_index_of(gui.addLayerDialog.comboBoxStart,"T1965"))
sleep(0.1)
gui.addLayerDialog.buttonBox.accepted.emit()
options.buttonBox.accepted.emit()

#TODO Scenarios:
#Animate scenario
#Save->Change->New Project ->Reload
#Delete layer and re-add scenario?



