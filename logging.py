from qgis._core import QgsMessageLog
import conf

"""Logging utilities to log messages in qgis with 
a separate tab just for Time Manager"""

def info(msg):
    QgsMessageLog.logMessage(str(msg), conf.LOG_TAG, QgsMessageLog.INFO)

def warn(msg):
    QgsMessageLog.logMessage(str(msg), conf.LOG_TAG)

def error(msg):
    QgsMessageLog.logMessage(str(msg), conf.LOG_TAG, QgsMessageLog.CRITICAL)

