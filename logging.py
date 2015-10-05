from qgis._core import QgsMessageLog

import conf


"""Logging utilities to log messages in qgis with
a separate tab just for Time Manager"""


def info(msg):  # pragma: no cover
    QgsMessageLog.logMessage(str(msg), conf.LOG_TAG, QgsMessageLog.INFO)


def warn(msg):  # pragma: no cover
    QgsMessageLog.logMessage(str(msg), conf.LOG_TAG)


def error(msg):  # pragma: no cover
    QgsMessageLog.logMessage(str(msg), conf.LOG_TAG, QgsMessageLog.CRITICAL)


def log_exceptions(func):  # pragma: no cover
    def log_after(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            error("Exception in function {}:{}".format(str(func), str(e)))
            return

    return log_after


def debug_on_exceptions(func):  # pragma: no cover
    """ Only used for debugging"""

    def debug_after(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, e:
            from PyQt4.QtCore import pyqtRemoveInputHook

            pyqtRemoveInputHook()
            import pdb
            pdb.set_trace()

    return debug_after
