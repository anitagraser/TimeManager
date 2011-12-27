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
#
# $Id: timemanager.py 122 2011-11-20 12:59:18Z anita_ $

"""
Time-Manager by Anita Graser and Volker Fröhlich
"""

from qgis.core import *

import resources

from timemanagercontrol import TimeManagerControl


class timemanager:
    """ plugin information """
    name = "TimeManagerPlugin"
    longName = "Time Manager plugin"
    description = "Working with temporal data"
    version = "Version 0.4"
    qgisMinimumVersion = '1.6.0' 
    author = "Anita Graser & Volker Fröhlich"
    pluginUrl = "http://www.geofrogger.net/trac/"

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

        

  
            
