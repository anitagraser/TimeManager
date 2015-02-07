from PyQt4 import QtCore
import qgis
from qgis._core import QgsApplication, QgsVectorLayer, QgsMapLayerRegistry, QgsProject

from timemanager.test import testcfg as testcfg
import os
from time import sleep
from datetime import datetime, timedelta
import tempfile

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

def getTweetsLayer():
    tm_dir = os.path.join(QgsApplication.qgisSettingsDirPath(),"python","plugins","timemanager")
    testfile_dir = os.path.join(tm_dir,testcfg.TEST_DATA_DIR)
    tweets = QgsVectorLayer(os.path.join(testfile_dir, 'tweets.shp'), 'tweets', 'ogr')
    return tweets

def addFirstUnmanagedLayerToTm(gui, column):
    gui.dock.pushButtonOptions.clicked.emit(1)
    sleep(0.1)
    options = gui.getOptionsDialog()
    assert(options is not None)
    options.pushButtonAdd.clicked.emit(1)
    # select the 1965 timestamps
    sleep(0.1)
    gui.addLayerDialog.comboBoxStart.setCurrentIndex(
        get_index_of(gui.addLayerDialog.comboBoxStart,column))
    sleep(0.1)
    gui.addLayerDialog.buttonBox.accepted.emit()
    options.buttonBox.accepted.emit()




## get references to timemanager controller
ctrl = qgis.utils.plugins['timemanager'].getController()
gui = ctrl.getGui()
tlm = ctrl.getTimeLayerManager()

## load tweets layer
QgsMapLayerRegistry.instance().addMapLayer(getTweetsLayer())

## add layer to TimeManager via the GUI
addFirstUnmanagedLayerToTm(gui, "T1965")

sleep(0.1)
initial_time = tlm.getCurrentTimePosition()
assert(initial_time.year==1965)
gui.dock.comboBoxTimeExtent.setCurrentIndex(get_index_of(gui.dock.comboBoxTimeExtent,"minutes"))
sleep(0.1)
assert(tlm.timeFrameType=="minutes")
gui.forwardClicked()
gui.forwardClicked()
gui.forwardClicked()
gui.backClicked()
sleep(0.1)
assert(tlm.getCurrentTimePosition() == initial_time + timedelta(minutes=2) )
time_before_animation = tlm.getCurrentTimePosition()
gui.playClicked()
assert(0.1)
gui.playClicked()
sleep(0.1)
# no easy way to let animate here
assert(ctrl.animationActivated==False)
time_before_save = tlm.getCurrentTimePosition()
tmp_file = tempfile.NamedTemporaryFile(delete=False)
QgsProject.instance().write(QtCore.QFileInfo(tmp_file.name))
sleep(0.1)
with open(tmp_file.name) as f:
    text = f.read()

assert("TimeManager" in text)
assert("active" in text)
os.remove(tmp_file.name)

# add second layer
## load tweets layer again but with 2011 timestamps
QgsMapLayerRegistry.instance().addMapLayer(getTweetsLayer())
addFirstUnmanagedLayerToTm(gui, "T")
sleep(0.1)
extents = tlm.getProjectTimeExtents()
assert(extents[0].year ==1965 and extents[1].year==2011)

#TODO Scenarios:
#Delete layer and re-add scenario?



