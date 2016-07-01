#!/usr/bin/python
# -*- coding: UTF-8 -*-
#=============================================================
#===================   TimeManager    ========================
#===================  a QGIS Plug-In  ========================
#=============================================================
#
# ***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# ***************************************************************************


from qgis.utils import qgsfunction, QgsExpression
from PyQt4.QtCore import QTranslator, QCoreApplication, qVersion, QSettings, QLocale
from timemanagercontrol import TimeManagerControl
import time_util
import resources  # loads the icons
import os
import locale
import conf
from tmlogging import info, warn, error

I18N_FOLDER = "i18n"


class timemanager:
    """ plugin information """
    name = "timemanager"
    longName = "TimeManager Plugin for QGIS >= 2.3"
    description = "Working with temporal vector data"
    author = "Anita Graser, Karolina Alexiou"
    pluginUrl = "https://github.com/anitagraser/TimeManager"

    def __init__(self, iface):
        """initialize the plugin"""
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
            except:
                lang = "en"  # could not get locale, OSX may have this bug
            info("Plugin language loaded: {}".format(lang))
            self.change_i18n(lang)
            control = TimeManagerControl(iface)

    def getController(self):
        return control

    def initGui(self):
        """initialize the gui"""
        control.load()

    def unload(self):
        """Unload the plugin"""
        control.unload()
        QgsExpression.unregisterFunction("$animation_datetime")
        QgsExpression.unregisterFunction("animation_datetime")

    def change_i18n(self, new_lang):
        """Change internationalisation for the plugin.

        Override the system locale  and then see if we can get a valid
        translation file for whatever locale is effectively being used.

        """
        #os.environ["LANG"] = str(new_lang)
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        translation_path = os.path.join(
            root, self.name, I18N_FOLDER,
            self.name+"_" + str(new_lang) + ".qm")
        if os.path.exists(translation_path):
            self.translator = QTranslator()
            result = self.translator.load(translation_path)
            if not result:
                error(
                    "Translation file {} for lang {} was not loaded properly,"
                    + "falling back to English".format(translation_path, new_lang)
                    )
                return
            if qVersion() > "4.3.3":
                QCoreApplication.installTranslator(self.translator)
            else:
                self.translator = None
                warn("Translation not supported for Qt <= {}".format(qVersion()))
        else:
            if new_lang != "en":
                warn("Translation failed for lang {}, falling back to English".format(new_lang))

    @qgsfunction(0, "TimeManager")
    def animation_datetime(values, feature, parent):
        """called by QGIS to determine the current animation time"""
        return time_util.datetime_to_str(control.getTimeLayerManager().getCurrentTimePosition(),
                                         time_util.DEFAULT_FORMAT)
