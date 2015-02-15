import abc
from collections import defaultdict
from qgis.core import *
try:
    import numpy as np
except:
    pass
__author__ = 'carolinux'



class Interpolator:
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def getInterpolatedValue(self, id, timestamp):
        pass


class LinearInterpolator(Interpolator):

    def __init__(self):
        # initiate helper data strucutres
        self.id_time_to_geom = {}
        self.id_to_time = defaultdict(list)

    def getGeomForIdEpoch(self, id, epoch):
        return self.id_time_to_geom[(id,epoch)]


    def addIdEpochTuple(self, id, epoch, geom):
        self.id_time_to_geom[(id, epoch)] = geom
        self.id_to_time[id].append(epoch)

    def sort(self):
        for id in self.id_to_time.keys():
            self.id_to_time[id].sort() # in place sorting


    def getInterpolatedValue(self, id, start_epoch, end_epoch):

        lastBefore = self.getLastEpochBeforeForId(id, start_epoch)
        firstAfter = self.getFirstEpochAfterForId(id, end_epoch)
        time_values = [lastBefore, firstAfter]
        #QgsMessageLog.logMessage(str(lastBefore)+"..."+str(firstAfter))
        #QgsMessageLog.logMessage(str(self.id_time_to_geom))
        xpos1,ypos1 = self.getGeomForIdEpoch(id, lastBefore)
        xpos2,ypos2 = self.getGeomForIdEpoch(id, firstAfter)
        # Interpolate
        #TODO could also work for non points?
        x_pos = [xpos1, xpos2]
        y_pos = [ypos1, ypos2]
        #TODO probably if the point hasnt appeared yet, we shouldnt interpolate left or right
        interp_x = np.interp(start_epoch,time_values,x_pos)
        interp_y = np.interp(start_epoch,time_values,y_pos)
        return (interp_x, interp_y)


    def getLastEpochBeforeForId(self, id, epoch):
        idx = np.searchsorted(self.id_to_time[id],epoch-1)
        if idx>0 and self.id_to_time[id][idx]>epoch:
            idx=idx-1
        return self.id_to_time[id][idx]

    def getFirstEpochAfterForId(self, id, epoch):
        idx=np.searchsorted(self.id_to_time[id],epoch)
        if idx==len(self.id_to_time[id]):
            idx=idx-1
        return self.id_to_time[id][idx]



