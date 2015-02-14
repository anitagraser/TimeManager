__author__ = 'carolinux'

from timelayer import *
from timevectorlayer import TimeVectorLayer
from time_util import DEFAULT_FORMAT, datetime_to_epoch, timeval_to_epoch, epoch_to_str,UTC


from PyQt4.QtCore import *
from PyQt4.QtGui import *
from collections import defaultdict

try:
    import numpy as np
except:
    pass

DEFAULT_ID = 0

#TODO Modify ctrl.restoreTimeLayers to be able to recreate a TimeVectorInterpolated layer
#TODO: Just points types? Why not also lines or polygon move?
#TODO: What about totimeattr
#TODO: Why no exception thrown upon creation when there is sth wrong??

class TimeVectorInterpolatedLayer(TimeVectorLayer):

    def isInterpolationEnabled(self):
        return True

    def __init__(self,layer,fromTimeAttribute,toTimeAttribute,enabled=True,
                 timeFormat=DEFAULT_FORMAT,offset=0, iface=None, idAttribute=None):
        TimeVectorLayer.__init__(self,layer,fromTimeAttribute,toTimeAttribute,
                                 enabled=enabled,timeFormat=timeFormat,offset=offset,
                                 iface=iface)
        QgsMessageLog.logMessage("Making layer???")
        #pyqtRemoveInputHook()
        #import pdb
        #pdb.set_trace()
        try:
            import numpy as np
        except:
            raise Exception("Need to have numpy installed")
        if layer.geometryType() != QGis.Point:
            raise Exception("Want point geometry!")
        self.idAttribute = idAttribute

        self.memLayer = QgsVectorLayer("Point?crs=epsg:4326&index=yes",
                                       "interpolated_points_for_{}".format(
            self.layer.name()), "memory")
        #TODO: Set CRS without prompt
        #TODO: Make same style as original layer, only a bit moar transparent
        self.memLayer.setCrs(self.layer.crs())
        QgsMapLayerRegistry.instance().addMapLayer(self.memLayer)


        # this requires some memory, may not be suited to layers with too many features to fit into
        # memory.. but.. QGIS loads these anyway?
        # it is hard to do queries via qgis
        # Essentially creating a mini database which we can query to do the interpolations
        # without going through QGIS' kinda annoying sql querying system

        provider = self.getProvider()
        self.fromTimeAttributeIndex = provider.fieldNameIndex(self.fromTimeAttribute)
        self.toTimeAttributeIndex = provider.fieldNameIndex(self.toTimeAttribute)


        if self.hasIdAttribute():
            self.idAttributeIndex = provider.fieldNameIndex(self.idAttribute)
            self.uniqueIdValues = set(provider.uniqueValues(self.idAttributeIndex))

        else:
            self.uniqueIdValues = set([DEFAULT_ID])

        # create data structures for efficiently querying to interpolateg
        # create a hashmap (id, epoch_time)-> geometry feature
        self.id_time_to_geom = {}
        self.id_to_time = defaultdict(list)
        features = self.layer.getFeatures(QgsFeatureRequest() )
        for feat in features:
            from_time = timeval_to_epoch(feat[self.fromTimeAttributeIndex])
            to_time = timeval_to_epoch(feat[self.fromTimeAttributeIndex])
            geom = feat.geometry()
            if geom.type()!=QGis.Point:
                QgsMessageLog.logMessage("Ignoring 1 non-point geometry")
                continue
            coords = (geom.asPoint().x(), geom.asPoint().y())

            id = DEFAULT_ID if not self.hasIdAttribute() else feat[self.idAttributeIndex]
            self.id_time_to_geom[(id, from_time)] = coords
            self.id_to_time[id].append(from_time)

        # create a hashmap of id to sorted timestamps
        for id in self.id_to_time.keys():
            self.id_to_time[id].sort() # in place sorting


        self.n=0
        self.previous_ids = set()
        QgsMessageLog.logMessage("Created layer successfully!")


    def _getGeomForIdTime(self,id, epoch, attr="from"):
        if attr=="from":
            return self.id_time_to_geom[(id,epoch)]

    def getIdAttribute(self):
        return self.idAttribute

    def hasIdAttribute(self):
        return self.idAttribute is not None


    def getInterpolatedGeometries(self, start_epoch, end_epoch):
        # 1. Find current Ids shown
        idsInFrame = set()
        features = self.layer.getFeatures(QgsFeatureRequest() )
        for feat in features:
            id = DEFAULT_ID if not self.hasIdAttribute() else feat[self.idAttributeIndex]
            idsInFrame.add(id)

        idsNotInFrame = self.uniqueIdValues - idsInFrame
        if len(idsNotInFrame)==0:
            # all ids are present in the frame, no need to interpolate :)
            return []

        pts = []
        # 2.for every id, need to find the lastBefore and firstAfter and create a point

        for id in idsNotInFrame:
            lastBefore = self._getLastEpochBeforeForId(id, start_epoch)
            firstAfter = self._getFirstEpochAfterForId(id, end_epoch)
            time_values = [lastBefore, firstAfter]
            xpos1,ypos1 = self._getGeomForIdTime(DEFAULT_ID, lastBefore)
            xpos2,ypos2 = self._getGeomForIdTime(DEFAULT_ID, firstAfter)
            #pyqtRemoveInputHook()
            #import pdb
            #pdb.set_trace()


            # Interpolate
            x_pos = [xpos1, xpos2]
            y_pos = [ypos1, ypos2]
            #TODO probably if the point hasnt appeared yet, we shouldnt interpolate left or right
            interp_x = np.interp(start_epoch,time_values,x_pos)
            interp_y = np.interp(start_epoch,time_values,y_pos)

            #FIXME interpolation doesn't seem to work properly

            QgsMessageLog.logMessage("time1:{} time2:{},curr:{}".format(lastBefore,firstAfter,
                                                                   start_epoch))
            QgsMessageLog.logMessage("x1x2{}".format([xpos1,xpos2]))
            QgsMessageLog.logMessage("y1y2{}".format([ypos1,ypos2]))
            QgsMessageLog.logMessage("pt {}".format([interp_x,interp_y]))
            pt = QgsPoint(interp_x, interp_y)
            pts.append(pt)

        # 3. return  points list
        return pts

    def _getLastEpochBeforeForId(self, id, epoch):
        idx = np.searchsorted(self.id_to_time[id],epoch-1)
        if idx>0 and self.id_to_time[id][idx]>epoch:
            idx=idx-1
        return self.id_to_time[id][idx]

    def _getFirstEpochAfterForId(self, id, epoch):
        idx=np.searchsorted(self.id_to_time[id],epoch)
        if idx==len(self.id_to_time[id]):
            idx=idx-1
        return self.id_to_time[id][idx]

    def _clearMemoryLayer(self):
        #FIXME unclear how to get the layer feat ids exactly, so range works for now
        res = self.memLayer.dataProvider().deleteFeatures(range(self.n+1))
        assert(res)
        self.memLayer.triggerRepaint()

    def setTimeRestriction(self, timePosition, timeFrame):
        TimeVectorLayer.setTimeRestriction(self, timePosition, timeFrame)

        start_epoch = datetime_to_epoch(self.getStartTime(timePosition, timeFrame))
        end_epoch =  datetime_to_epoch(self.getEndTime(timePosition, timeFrame))

        QgsMessageLog.logMessage("setTimeRestriction Called {} times".format(self.n))
        QgsMessageLog.logMessage("size of layer at {}:{}".format(start_epoch,
                                                                 self.memLayer.featureCount(),
                                                              ))

        geoms = self.getInterpolatedGeometries(start_epoch, end_epoch)
        #Add the geometries as features
        self._clearMemoryLayer()

        self.previous_ids = set()

        features = []
        for i,geom in enumerate(geoms):

            feature = QgsFeature(id = start_epoch+i)
            feature.setGeometry(QgsGeometry.fromPoint(geom))
            #feature.setAttributes([start_epoch+i])
            features.append(feature) # if no attributes, it will fail
            self.previous_ids.add(feature.id())
            self.n = self.n + 1

        QgsMessageLog.logMessage("add {}features:".format(len(features)))
        res = self.memLayer.dataProvider().addFeatures(features)
        assert(res)
        self.memLayer.triggerRepaint()


    def deleteTimeRestriction(self):
        TimeVectorLayer.deleteTimeRestriction(self)
        self._clearMemoryLayer()


    def getSaveString(self):
        saveString = TimeVectorLayer.getSaveString(self)
        #TODO encode more info for interpolated layer to allow restoring from save string
        return saveString




