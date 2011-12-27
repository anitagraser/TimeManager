# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 17:22:52 2010

@author: Anita
"""

from datetime import datetime
from time import mktime 
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

class TimeManagerProjectHandler(QObject):
    """This class manages reading from and writing to the QgsProject instance. 
    It's not aware of the context of the variables written/read.
    Variables read from a file have to be put into context by the calling class."""
    
    def __init__(self,iface):
        QObject.__init__(self)
        self.iface = iface 
        self.readingSettings = False
        
    def writeSettings(self,settings):
        """write the list of settings to QgsProject instance"""
        if not self.readingSettings:
            for (key, value) in settings.items():
                self.writeSetting(key,value)

    def writeSetting(self,attribute,value):
        """write plugin settings to QgsProject instance"""
        # there is no writeEntry() for datetime!
        if type(value) == datetime:
            value = mktime(value.timetuple()) # convert datetime to float 
        try: # write plugin settings to QgsProject
            QgsProject.instance().writeEntry("TimeManager",attribute, value )
        except TypeError:
            QMessageBox.information(self.iface.mainWindow(),'Debug Output','Wrong type for '+attribute+'!\nType: '+str(type(value)))
            
    def readSetting(self,func,attribute,value):
        """read a plugin setting from QgsProject instance"""
        value,ok = func("TimeManager",attribute)
        if ok:
            return value
        else:
            return None
            
    def readSettings(self,settings):
        """read plugin settings from QgsProject instance"""
        self.readingSettings = True        
        
        # map data types to function names
        prj = QgsProject.instance()
        functions = { 'str' : prj.readEntry,
                     'QString' : prj.readEntry,
                     'int' : prj.readNumEntry,
                     'float' : prj.readDoubleEntry,
                     'bool' : prj.readBoolEntry,
                     'datetime' : prj.readDoubleEntry, # we converted datetimes to float in writeSetting()
                     'QStringList' : prj.readListEntry,
                     'pyqtWrapperType' : prj.readListEntry # strange name for QStringList
                     }
        
        output = {}
        
        for (key, value) in settings.items():
            dataType = type(value).__name__
            try:
                output[key] = self.readSetting(functions[dataType],key,value)
            except KeyError:
                QMessageBox.information(self.iface.mainWindow(),'Debug Output','Key: '+key+'\nData type: '+dataType)
        
        #self.emit(SIGNAL('settingsRead(dict)'),output)
 
        self.readingSettings = False
        
        return output
