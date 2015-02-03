# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 17:22:52 2010

@author: Anita
"""

from PyQt4.QtCore import *
from qgis.core import *

class TimeManagerProjectHandler(QObject):
    """This class manages reading from and writing to the QgsProject instance. 
    It's not aware of the context of the variables written/read.
    Variables read from a file have to be put into context by the calling class."""


    @classmethod
    def writeSettings(cls,settings):
        """write the list of settings to QgsProject instance"""
        QgsMessageLog.logMessage("Writing settings to project..")
        for (key, value) in settings.items():
            cls.writeSetting(key,value)

    @classmethod
    def writeSetting(cls,attribute,value):
        """write plugin settings to QgsProject instance"""
        QgsProject.instance().writeEntry("TimeManager",attribute, value)

    @classmethod
    def readSetting(cls,func,attribute):
        """read a plugin setting from QgsProject instance"""
        value,ok = func("TimeManager",attribute)
        if ok:
            return value
        else:
            return None

    @classmethod
    def readSettings(cls, metasettings):
        """read plugin settings from QgsProject instance
        :param settings: a dictionary of setting names mapped to the expected type
        """

        prj = QgsProject.instance()

        # use QProjects functions to extract the settings from the project XML
        type_to_read_function_mapping = { str : prj.readEntry,
                     int : prj.readNumEntry,
                     float : prj.readDoubleEntry,
                     long : prj.readDoubleEntry,
                     bool : prj.readBoolEntry,
                     list : prj.readListEntry,
                     }

        settings={}
        for (setting_name, type) in metasettings.items():

            try:
                setting_value = cls.readSetting(type_to_read_function_mapping[type],setting_name)
                if setting_value is None:
                    raise Exception
                settings[setting_name] = setting_value
            except:
                QgsMessageLog.logMessage("Could not extract setting {} from project xml. "
                                         "Expected type {}. Will use default value".format(setting_name, type))
        return settings
