__author__ = 'carolinux'

from qgis.core import *
import traceback

from timelayer import *
from timevectorlayer import TimeVectorLayer
from time_util import datetime_to_epoch
from conf import DEFAULT_ID
from interpolation import interpolator_factory as ifactory
import qgis_utils as qgs
from tmlogging import info


# Ideas for extending
# TODO: What about toTimeAttribute and interpolation? Right now it's ignored

class TimeVectorInterpolatedLayer(TimeVectorLayer):
    def isInterpolationEnabled(self):
        return True

    def interpolationMode(self):
        return self.mode

    def getMemLayer(self):
        """When restoring a project, the layer will already exist, so we shouldn't
         create a new one"""
        name = "interpolated_points_for_{}".format(self.layer.id())
        if not qgs.doesLayerNameExist(
                name):  # FIXME this will not work if the user renames the memory layer
            memLayer = QgsVectorLayer("Point?crs=epsg:4326&index=yes", name, "memory")
        else:
            memLayer = qgs.getLayerFromLayerName(name)
        return memLayer

    def __init__(self, settings, iface):
        TimeVectorLayer.__init__(self, settings, iface=iface)
        try:
            info("Trying to create time interpolated layer with interpolation mode: {}".format(
                settings.interpolationMode))
            try:
                import numpy as np
            except:
                raise Exception("Need to have numpy installed")

            if self.layer.geometryType() != QGis.Point:
                raise Exception("Want point geometry!")
            self.idAttribute = settings.idAttribute
            self.memLayer = self.getMemLayer()

            # adjust memLayer to have same crs and same color as original layer, only half transparent
            self.memLayer.setCrs(self.layer.crs())
            # copy the layer style to memLayer 
            renderer = self.layer.rendererV2()
            r2 = renderer.clone()
            self.memLayer.setRendererV2(r2)
            #qgs.setLayerTransparency(self.memLayer, 0.5)
            qgs.refreshSymbols(self.iface, self.memLayer)

            QgsMapLayerRegistry.instance().addMapLayer(self.memLayer)

            provider = self.getProvider()
            self.fromTimeAttributeIndex = provider.fieldNameIndex(self.fromTimeAttribute)
            self.toTimeAttributeIndex = provider.fieldNameIndex(self.toTimeAttribute)

            if self.hasIdAttribute():
                self.idAttributeIndex = provider.fieldNameIndex(self.idAttribute)
                self.uniqueIdValues = set(provider.uniqueValues(self.idAttributeIndex))
            else:
                self.uniqueIdValues = set([DEFAULT_ID])

            self.mode = settings.interpolationMode
            self.fromInterpolator = ifactory.get_interpolator_from_text(self.mode)
            self.fromInterpolator.load(self)
            self.n = 0
            info("Interpolated layer {} created successfully!".format(self.layer.name()))
        except Exception, e:
            raise InvalidTimeLayerError("Traceback:" + traceback.format_exc(e))

    def __del__(self):
        info("Cleaning up interpolated layer {}".format(self.layer.name()))
        QgsMapLayerRegistry.instance().removeMapLayer(self.memLayer.id())
        try:
            del self.memLayer
        except:
            pass

    def getIdAttribute(self):
        return self.idAttribute

    def hasIdAttribute(self):
        return self.idAttribute is not None and self.idAttribute != ""

    def getInterpolatedGeometries(self, start_epoch, end_epoch):
        # 1. Find current Ids shown
        idsInFrame = set()
        features = self.layer.getFeatures(QgsFeatureRequest())
        for feat in features:
            id = DEFAULT_ID if not self.hasIdAttribute() else feat[self.idAttributeIndex]
            idsInFrame.add(id)

        idsNotInFrame = self.uniqueIdValues - idsInFrame
        if len(idsNotInFrame) == 0:
            # all ids are present in the frame, no need to interpolate :)
            return []

        pts = []
        for id in idsNotInFrame:
            pt = self.fromInterpolator.getInterpolatedValue(id, start_epoch, end_epoch)
            if pt is not None:
                pts.append(QgsPoint(*pt))
        # 3. return  points list
        return pts

    def _clearMemoryLayer(self):
        try:  # theoretically, the user could have already removed the layer from the UI
            res = self.memLayer.dataProvider().deleteFeatures(range(self.n + 1))
            assert (res)
            self.memLayer.triggerRepaint()
        except:
            pass

    def setTimeRestriction(self, timePosition, timeFrame):
        TimeVectorLayer.setTimeRestriction(self, timePosition, timeFrame)

        start_epoch = datetime_to_epoch(self.getStartTime(timePosition, timeFrame))
        end_epoch = datetime_to_epoch(self.getEndTime(timePosition, timeFrame))

        #info("setTimeRestriction Called {} times".format(self.n))
        #info("size of layer at {}:{}".format(start_epoch,self.memLayer.featureCount(),))
        geoms = self.getInterpolatedGeometries(start_epoch, end_epoch)
        #Add the geometries as features
        self._clearMemoryLayer()

        features = []
        for i, geom in enumerate(geoms):
            feature = QgsFeature(id=start_epoch + i)
            feature.setGeometry(QgsGeometry.fromPoint(geom))
            #feature.setAttributes([start_epoch+i])
            features.append(feature)  # if no attributes, it will fail
            self.n = self.n + 1

        #info("add {}features:".format(len(features)))
        res = self.memLayer.dataProvider().addFeatures(features)
        assert (res)
        self.memLayer.triggerRepaint()

    def deleteTimeRestriction(self):
        TimeVectorLayer.deleteTimeRestriction(self)
        self._clearMemoryLayer()
