import abc
from collections import defaultdict
from qgis.core import *

from .. import time_util as time_util
from .. import conf as conf
from  ..tmlogging import info, warn, error


try:
    import numpy as np
except:
    pass
__author__ = 'carolinux'

from PyQt4.QtCore import *
from PyQt4.QtGui import *

STEP = 0.0000001


class Interpolator:
    __metaclass__ = abc.ABCMeta
    """ Interpolation is done for a function/mapping f(I,T) -> G
    where T = time and I is an ID and G is a geometry type that corresponds
    to this timestamp and id (for instance a point). Given an id and some timestamps
    with corresponding geometries (2 or more) for every value T between Tmin and Tmax we can
    return an interpolated G value. For T values outside Tmin and Tmax, behavior is
    determined by interpolate_left and interpolate_right"""

    @abc.abstractmethod
    def load(self, timeLayer, *args, **kwargs):
        """How to load the data from the layer/provider. Implementation is completely up to the developer.
        May choose to have a copy of the data in the class or just the info needed to query
        the provider"""
        pass

    @abc.abstractmethod
    def interpolate(self, Tvalue, Tvalues, Gvalues):
        """How to find the interpolated geometry value for a
        time value, given the neighboring time values
        and associated geometry values"""
        pass

    @abc.abstractmethod
    def get_Tvalue_before(self, id, timestamp):
        """Get the largest T value in the data where T <= timestamp"""
        pass

    @abc.abstractmethod
    def get_Tvalue_after(self, id, timestamp):
        """Get the smallest T value in the data where T >= timestamp"""
        pass

    @abc.abstractmethod
    def get_Gvalue(self, id, timestamp):
        """Return the actual geometry for id and timestamp.
        The (id,timestamp) pair must exist in the data"""
        pass

    @abc.abstractmethod
    def getGeometryFromFeature(feat):
        pass

    def interpolate_left(self):
        """Whether to do interpolation for T values < min(T) (otherwise will return None)"""
        return False

    def interpolate_right(self):
        """Whether to do interpolation for T values > max(T) (otherwise will return None)"""
        return False

    def num_Tvalues_before(self):
        """The number of T values to use for the interpolation before the current t"""
        return 1

    def num_Tvalues_after(self):
        """The number of T values to use for the interpolation after the current t"""
        return 1

    def getInterpolatedValue(self, id, t1, t2):
        """Get the interpolated G value given an id and a timestamp range"""

        # info("value for id{}, start{}, end{}".format(id,t1,t2))
        before = self.get_Tvalues_before(id, t1)
        after = self.get_Tvalues_after(id, t2)
        if len(before) == 0 or len(after) == 0:
            warn(
                "Could not interpolate for time range: {}-{}. Not enough values before or after".format(
                    t1, t2))
            return None
        before.reverse()
        Tvalues = before + after
        Gvalues = map(lambda x: self.get_Gvalue(id, x), Tvalues)

        return self.interpolate(t1, Tvalues, Gvalues)

    def get_Tvalues_before(self, id, t):
        """Get a sequence of T values <= t"""
        res = []
        lastt = t
        first = True
        for i in range(self.num_Tvalues_before()):
            if not first:
                lastt = lastt - STEP
            lastt = self.get_Tvalue_before(id, lastt)
            first = False
            if lastt is None:
                return res
            else:
                res.append(lastt)
        return res


    def get_Tvalues_after(self, id, t):
        """ Get a sequence of T values >= t"""
        res = []
        lastt = t
        first = True
        for i in range(self.num_Tvalues_after()):
            if not first:
                lastt = lastt + STEP
            lastt = self.get_Tvalue_after(id, lastt)
            first = False
            if lastt is None:
                return res
            else:
                res.append(lastt)
        return res

    def getStartEpochFromFeature(self, feat, layer):
        # TODO: is pending the correct choice?
        return time_util.timeval_to_epoch(feat[layer.fromTimeAttributeIndex], time_util.PENDING)

    def getEndEpochFromFeature(self, feat, layer):
        # TODO: from??
        pass


class MemoryLoadInterpolator(Interpolator):
    """Interpolator that loads all the data it needs and stores it in
    internal data structures. Will be less than ideal when dealing with 
    Big Data"""

    def __init__(self):
        self.id_time_to_geom = {}
        self.id_to_time = defaultdict(list)
        self.max_epoch = None
        self.min_epoch = None

    def load(self, timeLayer, *args, **kwargs):
        features = timeLayer.layer.getFeatures(QgsFeatureRequest())
        hasLimit = "limit" in kwargs
        i = 0
        for feat in features:
            from_time = self.getStartEpochFromFeature(feat, timeLayer)
            to_time = from_time
            geom = self.getGeometryFromFeature(feat)
            if geom is None:
                continue
            if i == 0:
                self.max_epoch = to_time
                self.min_epoch = to_time
            else:
                self.max_epoch = max(self.max_epoch, to_time)
                self.min_epoch = max(self.min_epoch, to_time)
            id = conf.DEFAULT_ID if not timeLayer.hasIdAttribute() else feat[
                timeLayer.idAttributeIndex]
            self._addIdEpochTuple(id, from_time, geom)
            i = i + 1
            if hasLimit and i > kwargs["limit"]:
                break

        self._sort()

    def get_Gvalue(self, id, epoch):
        return self.id_time_to_geom[(id, epoch)]

    def ids(self):
        return self.id_to_time.keys()

    def minmax(self):
        """ return min and max epoch stored"""
        return (self.min_epoch, self.max_epoxh)

    def _addIdEpochTuple(self, id, epoch, geom):
        self.id_time_to_geom[(id, epoch)] = geom
        self.id_to_time[id].append(epoch)

    def _sort(self):
        for id in self.id_to_time.keys():
            self.id_to_time[id].sort()  # in place sorting

    def get_Tvalue_before(self, id, epoch):
        if self.id_to_time[id][0] > epoch:
            return None if not self.interpolate_left() else self.id_to_time[id][
                0]  # already at smallest timestamp
        idx = np.searchsorted(self.id_to_time[id], epoch)
        if idx == len(self.id_to_time[id]):
            return self.id_to_time[id][-1]
        if idx > 0 and self.id_to_time[id][
            idx] > epoch:  # need to find a value smaller than current
            idx = idx - 1
        return self.id_to_time[id][idx]

    def get_Tvalue_after(self, id, epoch):
        if self.id_to_time[id][-1] < epoch:
            return None if not self.interpolate_right() else self.id_to_time[id][
                -1]  # already at largest timestamp
        idx = np.searchsorted(self.id_to_time[id], epoch)
        if idx == len(self.id_to_time[id]):
            return self.id_to_time[id][-1]
        return self.id_to_time[id][idx]

