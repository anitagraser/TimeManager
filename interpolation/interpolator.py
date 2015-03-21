import abc
from collections import defaultdict
from qgis.core import *
from .. import time_util as time_util
from .. import conf as conf
try:
    import numpy as np
except:
    pass
__author__ = 'carolinux'


from PyQt4.QtCore import *
from PyQt4.QtGui import *



class Interpolator:
    __metaclass__ = abc.ABCMeta
    """ Interpolation is done for a function/mapping f(z,x) -> Y
    where x = time and z is an ID and Y is a geometry type that corresponds
    to this timestamp and id (for instance a point). """

    def interpolate_left(self):
        return False

    def interpolate_right(self):
        return False

    def num_Tvalues_before(self):
        """The number of T values to use for the interpolation before the current t"""
        return 1

    def num_Tvalues_after(self):
        """The number of T values to use for the interpolation after the current t"""
        return 1

    def getInterpolatedValue(self, id, t1, t2):
        """Get the interpolated Y value given an id and a timestamp range"""

        QgsMessageLog.logMessage("value for id{}, start{}, end{}".format(id,t1,t2))

        before = self.get_Tvalues_before(id, t1)
        after = self.get_Tvalues_after(id, t2)
        if len(before) == 0  or len(after) == 0 :
            QgsMessageLog.logMessage("Could not interpolate")
            return None
        Tvalues = before + after
        Gvalues  = map(lambda x: self.get_Gvalue(id,x), Tvalues)

        return self.interpolate(t1, Tvalues, Gvalues)

    @abc.abstractmethod
    def load(self,layer, *args, **kwargs):
        """How to load the data from the layer/provider. Implementation is completely free.
        May choose to have a copy of the data in the class or just the info needed to query
        the provider"""
        pass

    @abc.abstractmethod
    def interpolate(self, Tvalue, Tvalues, Gvalues):
        pass

    def get_Tvalues_before(self,id, t):
        res = []
        lastt = t 
        for i in range(self.num_Tvalues_before()):
            lastt = self.get_Tvalue_before(id,lastt)
            if lastt is None:
                return res
            else: 
                res.append(lastt)
        return res


    def get_Tvalues_after(self,id, t ):
        res = []
        lastt = t 
        for i in range(self.num_Tvalues_after()):
            lastt = self.get_Tvalue_after(id,lastt)
            if lastt is None:
                return res
            else: 
                res.append(lastt)
        return res

    @abc.abstractmethod
    def get_Tvalue_before(self,id, timestamp):
        pass

    @abc.abstractmethod
    def get_Tvalue_after(self,id, timestamp):
        pass

    @abc.abstractmethod
    def get_Gvalue(self,id, timestamp):
        """Return the geometry for id and timestamp.
        The (id,timestamp) pair must exist in the data"""
        pass

class MemoryLoadInterpolator(Interpolator):

    @abc.abstractmethod
    def getGeometryFromFeature(feat):
        pass

    def __init__(self):
        self.id_time_to_geom = {}
        self.id_to_time = defaultdict(list)

    def load(self, timeLayer, *args, **kwargs):
        features = timeLayer.layer.getFeatures(QgsFeatureRequest() )
        for feat in features:
            from_time = time_util.timeval_to_epoch(feat[timeLayer.fromTimeAttributeIndex])
            to_time = time_util.timeval_to_epoch(feat[timeLayer.fromTimeAttributeIndex])
            geom = self.getGeometryFromFeature(feat) 
            if geom is None:
                continue
            id = conf.DEFAULT_ID if not timeLayer.hasIdAttribute() else feat[timeLayer.idAttributeIndex]
            self._addIdEpochTuple(id, from_time, geom)
        self._sort()

    def get_Gvalue(self, id, epoch):
        return self.id_time_to_geom[(id,epoch)]

    def _addIdEpochTuple(self, id, epoch, geom):
        self.id_time_to_geom[(id, epoch)] = geom
        self.id_to_time[id].append(epoch)

    def _sort(self):
        for id in self.id_to_time.keys():
            self.id_to_time[id].sort() # in place sorting

    def get_Tvalue_before(self, id, epoch):
        if self.id_to_time[id][0] > epoch:
            return None if not self.interpolate_left() else self.id_to_time[id][0] # already at smallest timestamp
        idx = np.searchsorted(self.id_to_time[id],epoch)
        if idx == len(self.id_to_time[id]):
            return self.id_to_time[id][-1]
        if idx>0 and self.id_to_time[id][idx]>epoch: # need to find a value smaller than current
            idx=idx-1
        return self.id_to_time[id][idx]

    def get_Tvalue_after(self, id, epoch):
        if self.id_to_time[id][-1] < epoch:
            return None if not self.interpolate_right() else self.id_to_time[id][-1] # already at largest timestamp
        idx=np.searchsorted(self.id_to_time[id],epoch)
        if idx == len(self.id_to_time[id]):
            return self.id_to_time[id][-1]
        return self.id_to_time[id][idx]

class LinearPointInterpolator(MemoryLoadInterpolator):

    def getGeometryFromFeature(self,feat):
        geom = feat.geometry()
        if geom.type()!=QGis.Point:
            QgsMessageLog.logMessage("Ignoring 1 non-point geometry")
            return None
        coords = (geom.asPoint().x(), geom.asPoint().y())
        return coords

    def interpolate(self, Tvalue, Tvalues, Gvalues):
        xpos1,ypos1 = Gvalues[0] 
        xpos2,ypos2 = Gvalues[1] 
        # Interpolate
        x_pos = [xpos1, xpos2]
        y_pos = [ypos1, ypos2]
        interp_x = np.interp(Tvalue,Tvalues,x_pos)
        interp_y = np.interp(Tvalue,Tvalues,y_pos)
        QgsMessageLog.logMessage(str(interp_x)+" "+str(interp_y))
        return [interp_x, interp_y]




