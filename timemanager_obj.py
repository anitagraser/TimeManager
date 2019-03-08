#!/usr/bin/python
# -*- coding: UTF-8 -*-
# =============================================================
# ===================   TimeManager    ========================
# ===================  a QGIS Plug-In  ========================
# =============================================================
#
# ***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# ***************************************************************************

from __future__ import absolute_import
from builtins import object

import os
from qgis.PyQt.QtCore import QTranslator, QCoreApplication, qVersion, QSettings, QLocale

from qgis.core import qgsfunction, QgsExpression

from timemanager.timemanagercontrol import TimeManagerControl
from timemanager.utils.tmlogging import info, warn, error

from timemanager.utils import time_util


class timemanager_obj(object):
    """Plugin information"""
    name = "timemanager"
    longName = "TimeManager Plugin for QGIS >= 2.3"
    description = "Working with temporal vector data"
    author = "Anita Graser, Karolina Alexiou"
    pluginUrl = "https://github.com/anitagraser/TimeManager"

    def __init__(self, iface):
        """Initialize the plugin"""
        global control
        try:
            control
        except NameError:
            try:
                overrideLocale = bool(QSettings().value("locale/overrideFlag", False))
                if not overrideLocale:
                    lang = QLocale.system().name().split("_")[0]
                else:
                    lang = QSettings().value("locale/userLocale", "").split("_")[0]
            except Exception:
                lang = "en"  # could not get locale, OSX may have this bug
            info("Plugin language loaded: {}".format(lang))
            self.changeI18n(lang)
            control = TimeManagerControl(iface)

    def getController(self):
        return control

    def initGui(self):
        """Initialize the gui"""
        control.load()

    def changeI18n(self, new_lang):
        """
        Change internationalisation for the plugin.
        Override the system locale  and then see if we can get a valid
        translation file for whatever locale is effectively being used.
        """
        # os.environ["LANG"] = str(new_lang)
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        translation_path = "TimeManager:i18n/{}_{}.qm".format(self.name, new_lang)
        self.translator = QTranslator()
        result = self.translator.load(translation_path)
        if not result:
            error(
                "Translation file {} for lang {} was not loaded properly," +
                "falling back to English".format(translation_path, new_lang)
            )
            return
        if qVersion() > "4.3.3":
            QCoreApplication.installTranslator(self.translator)
        else:
            self.translator = None
            warn("Translation not supported for Qt <= {}".format(qVersion()))

    def unload(self):
        """Unload the plugin"""
        control.unload()
        QgsExpression.unregisterFunction("$animation_datetime")
        QgsExpression.unregisterFunction("animation_datetime")
        QgsExpression.unregisterFunction("$animation_time_frame_size")
        QgsExpression.unregisterFunction("animation_time_frame_size")
        QgsExpression.unregisterFunction("$animation_time_frame_type")
        QgsExpression.unregisterFunction("animation_time_frame_type")
        QgsExpression.unregisterFunction("$animation_start_datetime")
        QgsExpression.unregisterFunction("animation_start_datetime")
        QgsExpression.unregisterFunction("$animation_end_datetime")
        QgsExpression.unregisterFunction("animation_end_datetime")

    @qgsfunction(0, "TimeManager")
    def animation_datetime(values, feature, parent):
        """Current animation time"""
        return time_util.datetime_to_str(control.getTimeLayerManager().getCurrentTimePosition(),
                                         time_util.DEFAULT_FORMAT)

    @qgsfunction(0, "TimeManager")
    def animation_time_frame_size(values, feature, parent):
        """Animation time frame size"""
        return control.getTimeLayerManager().getTimeFrameSize()

    @qgsfunction(0, "TimeManager")
    def animation_time_frame_type(values, feature, parent):
        """Unit of time frame, i.e. days, hours, minutes, seconds, ..."""
        return control.getTimeLayerManager().getTimeFrameType()

    @qgsfunction(0, "TimeManager")
    def animation_start_datetime(values, feature, parent):
        """Earliest time stamp"""
        return time_util.datetime_to_str(control.getTimeLayerManager().getProjectTimeExtents()[0],
                                         time_util.DEFAULT_FORMAT)

    @qgsfunction(0, "TimeManager")
    def animation_end_datetime(values, feature, parent):
        """Last time stamp"""
        return time_util.datetime_to_str(control.getTimeLayerManager().getProjectTimeExtents()[1],
                                         time_util.DEFAULT_FORMAT)
