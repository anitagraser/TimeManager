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


from qgis.core import *
from qgis.utils import qgsfunction
from PyQt4.QtCore import QTranslator, QCoreApplication, qVersion
from timemanagercontrol import TimeManagerControl
import resources # loads the icons
import os
import locale

I18N_FOLDER="i18n"


class timemanager:
    """ plugin information """
    name = "timemanager"
    longName = "TimeManager Plugin for QGIS >= 2.0"
    description = "Working with temporal vector data"
    version = "Version 1.0.2" 
    qgisMinimumVersion = '2.0' 
    author = "Anita Graser"
    pluginUrl = "https://github.com/anitagraser/TimeManager"

    def __init__( self, iface ):
        """initialize the plugin"""
        global control
        try:
            control
        except NameError:
            lang=locale.getdefaultlocale()[0].split("_")[0]
            self.change_i18n(lang)
            control = TimeManagerControl(iface)
        
    def initGui( self ):
        """initialize the gui"""
        control.initGui()

    def unload( self ):
        """Unload the plugin"""
        control.unload()

    def change_i18n(self, new_lang):
        """Change internationalisation for the plugin.

        Override the system locale  and then see if we can get a valid
        translation file for whatever locale is effectively being used.

        """
        os.environ['LANG'] = str(new_lang)
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        translation_path = os.path.join(
            root, self.name, I18N_FOLDER,
            self.name+'_' + str(new_lang) + '.qm')
        #QgsMessageLog.logMessage(translation_path)
        if os.path.exists(translation_path):
            self.translator = QTranslator()
            result = self.translator.load(translation_path)
            if not result:
                QgsMessageLog.logMessage(translation_path+" was not loaded properly, "
                                                          "using English" )
                return
            # QgsMessageLog.logMessage("Setting translator...{}".format(new_lang))
            if  qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
        else:
             QgsMessageLog.logMessage("Timemanager: No translation found for locale {}, "
                                      "using English".format(new_lang))

    @qgsfunction(0, "TimeManager")
    def animation_datetime(values, feature, parent):
        """called by QGIS to determine the current animation time"""
        #FIXME could use time_util instead of str() call
        return str(control.getCurrentTimePosition())
  

