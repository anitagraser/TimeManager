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
from timemanagercontrol import TimeManagerControl
import resources # loads the icons

class timemanager:
    """ plugin information """
    name = "TimeManagerPlugin"
    longName = "TimeManager Plugin for QGIS >= 2.0"
    description = "Working with temporal vector data"
    version = "Version 1.0" # update in __init__.py too!
    qgisMinimumVersion = '2.0' 
    author = "Anita Graser"
    pluginUrl = "https://github.com/anitagraser/TimeManager"
    control = None

    def __init__( self, iface ):
        """initialize the plugin"""
        global control 
        control = TimeManagerControl(iface)
        
    def initGui( self ):
        """initialize the gui"""
        control.initGui()

    def unload( self ):
        """Unload the plugin"""
        control.unload()
        
    @qgsfunction(0, "TimeManager")
    def animation_datetime(values, feature, parent):
        """called by QGIS to determine the current animation time"""
        return str(control.getCurrentTimePosition())
  
            
