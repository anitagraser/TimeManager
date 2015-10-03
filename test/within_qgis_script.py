from PyQt4 import QtCore
import qgis
import os
from time import sleep
from datetime import datetime, timedelta
import tempfile

from PyQt4.QtCore import QSettings
from qgis._core import QgsApplication, QgsVectorLayer, QgsMapLayerRegistry, QgsProject


try:
    from timemanager.test import testcfg as testcfg
    import timemanager.conf as conf
    from timemanager import layer_settings as ls
    from timemanager import bcdate_util as bcdate_util
except:
    from TimeManager.test import testcfg as testcfg  # Mac0S needs the capitalized name
    import TimeManager.conf as conf
    from TimeManager import layer_settings as ls
    from TimeManager import bcdate_util as bcdate_util

__author__ = 'carolinux'

"""File that should be run within the QGIS Python console to test the application directly"""


# # Available actions with very readable names to facilitate scenario creation ##
def enableUseOfGlobalCrs():
    s = QSettings()
    s.setValue("/Projections/defaultBehaviour", "useGlobal")


def disableUseOfGlobalCrs():
    s = QSettings()
    s.setValue("/Projections/defaultBehaviour", "prompt")


def tm_dir():
    return os.path.join(QgsApplication.qgisSettingsDirPath(), "python", "plugins", "timemanager")


def new_project():
    iface.newProject()


def load_project(fn):
    QgsProject.instance().setFileName(fn)
    QgsProject.instance().read()
    iface.projectRead.emit()


def get_all_items(combobox):
    """Get all text items of a QtComboBox"""
    return [combobox.itemText(i) for i in range(combobox.count())]


def get_all_layer_names():
    return QgsMapLayerRegistry.instance().mapLayers().keys()


def get_index_of(combobox, text):
    """Get the index of a specifix text in a QtComboBox"""
    all = get_all_items(combobox)
    print all
    return all.index(text)


def getTweetsLayer():
    testfile_dir = os.path.join(tm_dir(), testcfg.TEST_DATA_DIR)
    tweets = QgsVectorLayer(os.path.join(testfile_dir, 'tweets.shp'), 'tweets', 'ogr')
    return tweets


def getTimeSpansLayer():
    testfile_dir = os.path.join(tm_dir(), testcfg.TEST_DATA_DIR)
    timespans = QgsVectorLayer(os.path.join(testfile_dir, 'timespans.shp'), 'timespans', 'ogr')
    return timespans


def getArchaelogicalLayer():
    testfile_dir = os.path.join(tm_dir(), testcfg.TEST_DATA_DIR)
    fn = os.path.join(testfile_dir, "archaelogical.txt")
    uri = "{}?type=csv&xField={}&yField={}&spatialIndex=no&subsetIndex=no&watchFile=no" \
          "".format(fn, "lon", "lat")
    layer = QgsVectorLayer(uri, "ancient_points", 'delimitedtext')
    return layer


def load_layer_to_qgis(layer):
    QgsMapLayerRegistry.instance().addMapLayer(layer)
    sleep(0.2)


def remove_layer_from_qgis(id):
    QgsMapLayerRegistry.instance().removeMapLayer(id)
    sleep(0.1)


def goForward(gui):
    gui.forwardClicked()
    sleep(0.1)


def goBackward(gui):
    gui.backClicked()
    sleep(0.1)


def clickPlay(gui):
    gui.playClicked()
    sleep(0.1)


def clickOnOff(gui):
    gui.dock.pushButtonToggleTime.clicked.emit(1)
    sleep(0.1)


def save_project_to_file(fn):
    QgsProject.instance().write(QtCore.QFileInfo(fn))
    sleep(0.1)


def get_temp_file():
    return tempfile.NamedTemporaryFile(delete=False)


def layer_count():
    return len(QgsMapLayerRegistry.instance().mapLayers())


def addUnmanagedLayerToTm(gui, column, interpolate=False, name=None):
    gui.dock.pushButtonOptions.clicked.emit(1)
    sleep(0.2)
    options = gui.getOptionsDialog()
    assert (options is not None)
    sleep(0.2)
    options.pushButtonAddVector.clicked.emit(1)
    if name is not None:
        # dont add the first layer, but the one specified by the name
        assert (name in get_all_items(gui.vectorDialog.getDialog().comboBoxLayers))
        gui.vectorDialog.getDialog().comboBoxLayers.setCurrentIndex(
            get_index_of(gui.vectorDialog.getDialog().comboBoxLayers, name))
        sleep(0.1)

    sleep(0.1)
    get_all_items(gui.vectorDialog.getDialog().comboBoxStart)
    sleep(0.3)
    gui.vectorDialog.getDialog().comboBoxStart.setCurrentIndex(
        get_index_of(gui.vectorDialog.getDialog().comboBoxStart, column))
    sleep(0.1)
    if interpolate is True:
        gui.vectorDialog.getDialog().comboBoxInterpolation \
            .setCurrentIndex(get_index_of(gui.vectorDialog.getDialog().comboBoxInterpolation,
                                          conf.LINEAR_POINT_INTERPOLATION))
        sleep(0.1)

    gui.vectorDialog.getDialog().buttonBox.accepted.emit()
    options.buttonBox.accepted.emit()


def set_time_frame_type(gui, typ):
    gui.dock.comboBoxTimeExtent.setCurrentIndex(get_index_of(gui.dock.comboBoxTimeExtent, typ))

## get reference to timemanager modules before starting scenario execution
try:
    ctrl = qgis.utils.plugins['timemanager'].getController()
except:
    ctrl = qgis.utils.plugins['TimeManager'].getController()  # MacOS needs the capitalized name

gui = ctrl.getGui()
tlm = ctrl.getTimeLayerManager()
assert (tlm.isEnabled())

## senario 0 -> disable timemanager, see that saving project works normally, reenable
print "Start scenario 1"
new_project()
clickOnOff(gui)
assert (not tlm.isEnabled())
load_layer_to_qgis(getTweetsLayer())
save_project_to_file(get_temp_file().name)
assert (layer_count() == 1)
clickOnOff(gui)
assert (tlm.isEnabled())


## senario 1 -> simple back and forth within a layer, writing settings, adding 2nd layer
print "Start scenario 2"
new_project()
load_layer_to_qgis(getTweetsLayer())
addUnmanagedLayerToTm(gui, "T1965")
initial_time = tlm.getCurrentTimePosition()
set_time_frame_type(gui, "minutes")
goForward(gui)
goForward(gui)
goForward(gui)
goBackward(gui)
assert (initial_time.year == 1965)
assert (tlm.timeFrameType == "minutes")
assert (tlm.getCurrentTimePosition() == initial_time + timedelta(minutes=2) )
time_before_animation = tlm.getCurrentTimePosition()
clickPlay(gui)
clickPlay(gui)
assert (ctrl.animationActivated == False)
time_before_save = tlm.getCurrentTimePosition()
tmp_file = get_temp_file()
save_project_to_file(tmp_file.name)
with open(tmp_file.name) as f:
    text = f.read()
assert ("TimeManager" in text)
assert ("active" in text)
assert ("currentMapTimePosition" in text)
#os.remove(tmp_file.name)

# add second layer with 2011 timestamps
load_layer_to_qgis(getTweetsLayer())
addUnmanagedLayerToTm(gui, "T")
extents = tlm.getProjectTimeExtents()
assert (extents[0].year == 1965 and extents[1].year == 2011)
assert ("T" in iface.activeLayer().subsetString())
assert ("T965" not in iface.activeLayer().subsetString())
set_time_frame_type(gui, "years")
goForward(gui)
assert (tlm.getCurrentTimePosition().year == 1966)

# delete it
remove_layer_from_qgis(iface.activeLayer().id())
extents = tlm.getProjectTimeExtents()
assert (extents[0].year == 1965 and extents[1].year == 1965)



## senario 3
print "Start scenario 3"
new_project()
set_time_frame_type(gui, "seconds")
load_layer_to_qgis(getTimeSpansLayer())
addUnmanagedLayerToTm(gui, "ARRIVAL", interpolate=True)
assert (
len(get_all_layer_names()) == 2)  # the normal layer and the layer with the interpolated geometries
assert (iface.activeLayer().featureCount() == 0)
goForward(gui)
assert (iface.activeLayer().featureCount() == 1)  # now we have 1 interpolated point
goForward(gui)
assert (iface.activeLayer().featureCount() == 1)  # now we have 1 interpolated point
load_layer_to_qgis(getTweetsLayer())
addUnmanagedLayerToTm(gui, "T", name="tweets")
assert (ls.getSettingsFromLayer(tlm.getTimeLayerList()[0]).interpolationEnabled == True)
assert (len(get_all_layer_names()) == 3)
tmp_file = get_temp_file().name
save_project_to_file(tmp_file)
new_project()
load_project(tmp_file)
assert (len(get_all_layer_names()) == 3)

print "Start scenario 4 (archaelogy)"
new_project()
enableUseOfGlobalCrs()
ctrl.setArchaeology(1)
load_layer_to_qgis(getArchaelogicalLayer())
addUnmanagedLayerToTm(gui, "year")
assert (tlm.getCurrentTimePosition() == bcdate_util.BCDate(-20))
map(lambda x: goForward(gui), range(19))
assert (iface.activeLayer().featureCount() == 2)
goForward(gui)
assert (tlm.getCurrentTimePosition() == bcdate_util.BCDate(1))
goBackward(gui)
assert (tlm.getCurrentTimePosition() == bcdate_util.BCDate(-1))
disableUseOfGlobalCrs()
tlm.clearTimeLayerList()
ctrl.toggleArchaeology()

