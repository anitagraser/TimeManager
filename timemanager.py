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
from timemanagercontrol import TimeManagerControl
import resources # loads the icons

class timemanager:
    """ plugin information """
    name = "TimeManagerPlugin"
    longName = "TimeManager Plugin for QGIS >= 1.7"
    description = "Working with temporal vector data"
    version = "Version 0.7" # update in __init__.py too!
    qgisMinimumVersion = '1.7.0' 
    author = "Anita Graser"
    pluginUrl = "https://github.com/anitagraser/TimeManager"

    def __init__( self, iface ):
        """initialize the plugin"""
        self.iface = iface
        self.control = TimeManagerControl(self.iface)
        
    def initGui( self ):
        """initialize the gui"""
        self.control.initGui()

    def unload( self ):
        """Unload the plugin"""
        self.control.unload()
  

  
            
