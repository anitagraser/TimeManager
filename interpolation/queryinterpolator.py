import abc
from collections import defaultdict
from qgis.core import *
from .. import time_util as time_util
from .. import conf as conf
from .. import logging as logging
from .. import qgis_utils as qgs
from logging import info, warn, error
from interpolator import Interpolator

try:
    import numpy as np
except:
    pass
__author__ = 'carolinux'


from PyQt4.QtCore import *
from PyQt4.QtGui import *


class QueryInterpolator(Interpolator):
    """Interpolator that sends qgsfeaturerequests for the data it needs.
    Hence uses very little memory, and can benefit from indexes in the data source"""

    def __init__(self):
        self.timeLayer = None

    def load(self, timeLayer, *args, **kwargs):
        self.timeLayer = timeLayer
        self.timeColumn  = self.timeLayer.getTimeAttributes()[0]

    def _value_for_query(self, val, col):
        if qgs.isNumericField(self.timeLayer.layer, col):
            return val
        else:
            return QgsExpression.quotedString(val)

    def _id_query_string(self, id):
        if self.timeLayer.hasIdAttribute():
            idColumn = self.timeLayer.getIdAttribute()
            return " AND {}={}".format(QgsExpression.quotedColumnRef(idColumn), self._value_for_query(id, idColumn)) 
        else:
            return ""

    def _time_query_string(self, epoch, col, symbol="="):
        if self.timeLayer.getDateType() == time_util.DateTypes.IntegerTimestamps: 
            return "{} {} {}".format(QgsExpression.quotedColumnRef(col), symbol,epoch)
        else:
            timeStr = time_util.epoch_to_str(epoch, self.timeLayer.getTimeFormat())
            return "{} {} {}".format(QgsExpression.quotedColumnRef(col), symbol,QgsExpression.quotedString(timeStr))

    def get_Gvalue(self, id, epoch):
        req = QgsFeatureRequest() 
        exp = self._time_query_string(epoch, self.timeColumn, '=')
        exp+= self._id_query_string(id)
        req.setFilterExpression(exp)
        info("Geom query Expression {}".format(exp))
        s = self.timeLayer.subsetString()
        self.timeLayer.setSubsetString("")
        featIt = self.timeLayer.layer.dataProvider().getFeatures(req)
        self.timeLayer.setSubsetString(s)
        for feat in featIt:
            return self.getGeometryFromFeature(feat)
        return None

    def _get_tvalue(self, id, epoch, symbol,func):
        req = QgsFeatureRequest() 
        exp = self._time_query_string(epoch, self.timeColumn, symbol)
        exp+= self._id_query_string(id)
        req.setFilterExpression(exp)
        #from PyQt4.QtCore import pyqtRemoveInputHook
        #pyqtRemoveInputHook()
        #import pdb;pdb.set_trace()
        s = self.timeLayer.subsetString()
        self.timeLayer.setSubsetString("")
        featIt = self.timeLayer.layer.dataProvider().getFeatures(req)
        self.timeLayer.setSubsetString(s)
        V = None
        for feat in featIt:
            curr_epoch = self.getStartEpochFromFeature(feat, self.timeLayer)
            if V is None:
                V = curr_epoch
            V = func(curr_epoch, V)
        return V

    def get_Tvalue_before(self, id, epoch):
        return self._get_tvalue(id, epoch, "<", max)

    def get_Tvalue_after(self, id, epoch):
        return self._get_tvalue(id, epoch, ">", min)


