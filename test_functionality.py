import sip
sip.setapi('QString', 2) # strange things happen without this. Must import before PyQt imports
# if using ipython: do this on bash before
# export QT_API=pyqt
from qgis.core import *
#from qgis.gui import *
import os
from mock import Mock
from datetime import datetime, timedelta
from PyQt4 import QtCore, QtGui, QtTest

import unittest


TEST_DATA_DIR="testdata"

# discover your prefix by loading the Python console from within QGIS and
# running QgsApplication.showSettings().split("\t")
# and looking for Prefix
QgsApplication.setPrefixPath("/usr", True)

QgsApplication.initQgis()
QtCore.QCoreApplication.setOrganizationName('QGIS')
QtCore.QCoreApplication.setApplicationName('QGIS2')


if len(QgsProviderRegistry.instance().providerList()) == 0:
    raise RuntimeError('No data providers available.')
print "QGIS loaded"

iface = Mock()
import timemanagercontrol
import timevectorlayer
import time_util
ctrl = timemanagercontrol.TimeManagerControl(iface)
tlm = ctrl.getTimeLayerManager()
layer = QgsVectorLayer(os.path.join(TEST_DATA_DIR, 'tweets.shp'), 'tweets', 'ogr')
assert(layer.isValid())
timeLayer = timevectorlayer.TimeVectorLayer(layer,"T","T",True,time_util.DEFAULT_FORMAT,0)
tlm.registerTimeLayer(timeLayer)
# The currentTimePosition should now be the first date in the shapefile
START_TIME = datetime(2011, 10, 8, 17, 44, 21)
assert( START_TIME ==tlm.getCurrentTimePosition())
tlm.setTimeFrameType("hours")
tlm.stepForward()
assert( START_TIME + timedelta(hours=1)==tlm.getCurrentTimePosition())

#print dir(layer)
# QgsMapLayerRegistry().instance().addMapLayer(layer) doesnt werk :((


QgsApplication.exitQgis()
