#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Created on Fri Oct 29 17:22:52 2010

@author: Anita
"""

from qgis.PyQt.QtCore import QObject, QSettings

try:
    from qgis.PyQt.QtCore import QPyNullVariant
except ImportError:
    QPyNullVariant = None

from qgis.core import QgsProject


class TimeManagerProjectHandler(QObject):
    """This class manages reading from and writing to the QgsProject instance.
    It's not aware of the context of the variables written/read.
    Variables read from a file have to be put into context by the calling class."""

    @classmethod
    def set_plugin_setting(cls, name, value):
        """Set temporary settings"""
        QSettings().setValue("TimeManager/" + name, value)

    @classmethod
    def plugin_setting(cls, name, default=None):
        return QSettings().value("TimeManager/" + name, default)

    @classmethod
    def writeSettings(cls, settings):
        """write the list of settings to QgsProject instance"""
        for (key, value) in list(settings.items()):
            cls.writeSetting(key, value)

    @classmethod
    def writeSetting(cls, attribute, value):
        """write plugin settings to QgsProject instance"""
        try:
            QgsProject.instance().writeEntry("TimeManager", attribute, value)
        except Exception:
            pass

    @classmethod
    def readSetting(cls, func, attribute):
        """read a plugin setting from QgsProject instance"""
        value, ok = func("TimeManager", attribute)
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
        type_to_read_function_mapping = {
            str: prj.readEntry,
            int: prj.readNumEntry,
            float: prj.readDoubleEntry,
            # int: prj.readDoubleEntry,
            bool: prj.readBoolEntry,
            list: prj.readListEntry,
        }

        settings = {}
        for (setting_name, setting_type) in list(metasettings.items()):

            try:
                setting_value = cls.readSetting(type_to_read_function_mapping[setting_type], setting_name)
                if setting_value is None:
                    raise Exception
                settings[setting_name] = setting_value
            except Exception:
                pass
        return settings
