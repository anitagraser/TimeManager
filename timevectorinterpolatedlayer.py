#!/usr/bin/python
# -*- coding: UTF-8 -*-

from __future__ import absolute_import
from builtins import range

__author__ = 'carolinux'

import traceback

from qgis.core import QgsVectorLayer, QgsFeatureRequest, QgsPoint, QgsFeature, QgsGeometry

from .timelayer import InvalidTimeLayerError
from .timevectorlayer import TimeVectorLayer
from .interpolation import interpolator_factory as ifactory
from .tmlogging import info

from . import time_util
from . import conf
from . import qgis_utils as qgs


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
                import numpy as np  # NOQA
            except ImportError:
                raise Exception("Need to have numpy installed")

            if not qgs.isPointLayer(self.layer):
                raise Exception("Want point geometry!")

            self.idAttribute = settings.idAttribute
            self.memLayer = self.getMemLayer()

            # adjust memLayer to have same crs and same color as original layer, only half transparent
            self.memLayer.setCrs(self.layer.crs())
            # copy the layer style to memLayer
            renderer = self.layer.renderer()
            r2 = renderer.clone()
            self.memLayer.setRenderer(r2)
            # qgs.setLayerTransparency(self.memLayer, 0.5)
            qgs.refreshSymbols(self.iface, self.memLayer)

            qgs.addLayer(self.memLayer)

            provider = self.getProvider()
            self.fromTimeAttributeIndex = provider.fields().indexFromName(self.fromTimeAttribute)
            self.toTimeAttributeIndex = provider.fields().indexFromName(self.toTimeAttribute)

            info("ID Attriute set to `{}`".format(self.idAttribute))

            if self.hasIdAttribute():
                self.idAttributeIndex = provider.fields().indexFromName(self.idAttribute)
                self.uniqueIdValues = set(provider.uniqueValues(self.idAttributeIndex))

                # Add the field used for interpolation to the new layer
                attributeField = provider.fields().field(self.idAttributeIndex)
                res = self.memLayer.dataProvider().addAttributes([attributeField])
                assert (res)
                self.memLayer.updateFields()

                info("Added the attribute {}".format(self.idAttributeIndex))

            else:
                self.uniqueIdValues = set([conf.DEFAULT_ID])

            self.mode = settings.interpolationMode
            self.fromInterpolator = ifactory.get_interpolator_from_text(self.mode)
            self.fromInterpolator.load(self)
            self.n = 0
            info("Interpolated layer {} created successfully!".format(self.layer.name()))
        except Exception as e:
            raise InvalidTimeLayerError("Traceback:" + traceback.format_exc(e))

    def __del__(self):
        info("Cleaning up interpolated layer {}".format(self.layer.name()))
        qgs.removeLayer(self.memLayer.id())
        try:
            del self.memLayer
        except Exception:
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
            ident = conf.DEFAULT_ID if not self.hasIdAttribute() else feat[self.idAttributeIndex]
            idsInFrame.add(ident)

        idsNotInFrame = self.uniqueIdValues - idsInFrame
        if len(idsNotInFrame) == 0:
            # all ids are present in the frame, no need to interpolate :)
            return []

        pts = []
        for ident in idsNotInFrame:
            pt = self.fromInterpolator.getInterpolatedValue(ident, start_epoch, end_epoch)
            if pt is not None:
                pts.append((ident, QgsPoint(*pt)))
        # 3. return  points list
        return pts

    def _clearMemoryLayer(self):
        try:  # theoretically, the user could have already removed the layer from the UI
            res = self.memLayer.dataProvider().deleteFeatures(list(range(self.n + 1)))
            assert (res)
            self.memLayer.triggerRepaint()
        except Exception:
            pass

    def setTimeRestriction(self, timePosition, timeFrame):
        TimeVectorLayer.setTimeRestriction(self, timePosition, timeFrame)

        start_epoch = time_util.datetime_to_epoch(self.getStartTime(timePosition, timeFrame))
        end_epoch = time_util.datetime_to_epoch(self.getEndTime(timePosition, timeFrame))

        # info("setTimeRestriction Called {} times".format(self.n))
        # info("size of layer at {}:{}".format(start_epoch,self.memLayer.featureCount(),))
        geoms = self.getInterpolatedGeometries(start_epoch, end_epoch)
        # Add the geometries as features
        self._clearMemoryLayer()

        if self.hasIdAttribute():
            idAttributeIndex = self.memLayer.dataProvider().fields().indexFromName(self.idAttribute)

        features = []
        for i, (ident, geom) in enumerate(geoms):
            feature = QgsFeature(id=start_epoch + i)
            if self.hasIdAttribute():
                feature.initAttributes(1)
                feature.setAttribute(idAttributeIndex, ident)
            feature.setGeometry(QgsGeometry.fromQPointF(geom.toQPointF()))
            features.append(feature)  # if no attributes, it will fail
            self.n = self.n + 1

        # info("add {}features:".format(len(features)))
        res = self.memLayer.dataProvider().addFeatures(features)
        assert (res)
        self.memLayer.triggerRepaint()

    def deleteTimeRestriction(self):
        TimeVectorLayer.deleteTimeRestriction(self)
        self._clearMemoryLayer()
