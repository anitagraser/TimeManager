#!/usr/bin/python
# -*- coding: UTF-8 -*-


from __future__ import absolute_import

from qgis.PyQt.QtCore import QDir

import os


def classFactory(iface):
    QDir.addSearchPath("TimeManager", os.path.dirname(__file__))
    QDir.addSearchPath("timemanager", os.path.dirname(__file__))

    from timemanager import timemanager_obj
    return timemanager_obj.timemanager_obj(iface)
