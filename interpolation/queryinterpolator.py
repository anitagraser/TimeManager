from qgis.core import *

from .. import time_util as time_util
from .. import qgis_utils as qgs
from ..tmlogging import warn
from interpolator import Interpolator


try:
    import numpy as np
except:
    pass
__author__ = 'carolinux'


class QueryInterpolator(Interpolator):
    """Interpolator that sends qgsfeaturerequests for the data it needs.
    Hence uses very little memory, and can benefit from indexes in the data source"""

    def __init__(self):
        self.timeLayer = None

    def load(self, timeLayer, *args, **kwargs):
        warn("loaded??")
        self.timeLayer = timeLayer
        self.timeColumn = self.timeLayer.getTimeAttributes()[0]

    def _value_for_query(self, val, col):
        if qgs.isNumericField(self.timeLayer.layer, col):
            return val
        else:
            return QgsExpression.quotedString(val)

    def _id_query_string(self, id):
        if self.timeLayer.hasIdAttribute():
            idColumn = self.timeLayer.getIdAttribute()
            return " AND {}={}".format(QgsExpression.quotedColumnRef(idColumn),
                                       self._value_for_query(id, idColumn))
        else:
            return ""

    def _time_query_string(self, epoch, col, symbol="="):
        if self.timeLayer.getDateType() == time_util.DateTypes.IntegerTimestamps:
            return "{} {} {}".format(QgsExpression.quotedColumnRef(col), symbol, epoch)
        else:
            timeStr = time_util.epoch_to_str(epoch, self.timeLayer.getTimeFormat())
            return "{} {} {}".format(QgsExpression.quotedColumnRef(col), symbol,
                                     QgsExpression.quotedString(timeStr))

    def get_Gvalue(self, id, epoch):
        req = QgsFeatureRequest()
        exp = self._time_query_string(epoch, self.timeColumn, '=')
        exp += self._id_query_string(id)
        req.setFilterExpression(exp)
        warn("Geom query Expression {}".format(exp))
        s = self.timeLayer.subsetString()
        self.timeLayer.setSubsetString("")
        featIt = self.timeLayer.layer.dataProvider().getFeatures(req)
        self.timeLayer.setSubsetString(s)
        for feat in featIt:
            return self.getGeometryFromFeature(feat)
        return None

    def _get_tvalue(self, id, epoch, symbol, get_first):
        req = QgsFeatureRequest()
        exp = self._time_query_string(epoch, self.timeColumn, symbol)
        exp += self._id_query_string(id)
        req.setFilterExpression(exp)
        warn(exp)
        s = self.timeLayer.subsetString()
        self.timeLayer.setSubsetString("")
        featIt = self.timeLayer.layer.dataProvider().getFeatures(req)
        self.timeLayer.setSubsetString(s)
        l = list(featIt)
        if get_first:
            subList = l[:min(20, len(l))]
        else:
            subList = l[-min(20, len(l)):]
        feats = sorted(subList,
                       key=lambda feat: self.getStartEpochFromFeature(feat, self.timeLayer))
        if not feats:
            return None
        if get_first:
            feat = feats[0]
        else:
            feat = feats[-1]
        curr_epoch = self.getStartEpochFromFeature(feat, self.timeLayer)
        return curr_epoch

    def get_Tvalue_before(self, id, epoch):
        return self._get_tvalue(id, epoch, "<", False)

    def get_Tvalue_after(self, id, epoch):
        return self._get_tvalue(id, epoch, ">", True)


