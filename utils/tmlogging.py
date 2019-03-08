#!/usr/bin/python
# -*- coding: UTF-8 -*-

"""
Logging utilities to log messages in QGIS with
a separate tab just for Time Manager
"""
from __future__ import absolute_import
from builtins import str

__author__ = 'carolinux'

from qgis.core import QgsMessageLog

import conf

try:
    from qgis.core import Qgis
except ImportError:
    from qgis.core import QGis as Qgis


def info(msg):  # pragma: no cover
    if hasattr(Qgis, "Info"):
        QgsMessageLog.logMessage(str(msg), conf.LOG_TAG, Qgis.Info)
    else:
        QgsMessageLog.logMessage(str(msg), conf.LOG_TAG, QgsMessageLog.INFO)


def warn(msg):  # pragma: no cover
    QgsMessageLog.logMessage(str(msg), conf.LOG_TAG)


def error(msg):  # pragma: no cover
    if hasattr(Qgis, "Critical"):
        QgsMessageLog.logMessage(str(msg), conf.LOG_TAG, Qgis.Critical)
    else:
        QgsMessageLog.logMessage(str(msg), conf.LOG_TAG, QgsMessageLog.CRITICAL)


def log_exceptions(func):  # pragma: no cover
    def log_after(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error("Exception in function {}:{}".format(str(func), str(e)))
            return

    return log_after


def debug_on_exceptions(func):  # pragma: no cover
    """ Only used for debugging"""

    def debug_after(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            from PyQt4.QtCore import pyqtRemoveInputHook

            pyqtRemoveInputHook()
            import pdb
            pdb.set_trace()

    return debug_after
