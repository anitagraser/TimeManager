# -*- coding: utf-8 -*-
"""
Created on Fri Oct 29 10:10:27 2010

@author: agraser
"""

from datetime import datetime

from qgis.core import *

from timemanagerguicontrol import *
from timelayer import *
from timelayermanager import *
from timemanagerprojecthandler import *

class TimeManagerControl(QObject):
    """Controls the logic behind the GUI. Signals are processed here."""

    def __init__(self,iface):
        """initialize the plugin control"""
        QObject.__init__(self)
        self.iface = iface       
        
        self.loopAnimation = False
        self.saveAnimationPath = os.path.expanduser('~')
        
        QObject.connect(self.iface,SIGNAL('projectRead ()'),self.readSettings)
        QObject.connect(self.iface,SIGNAL('newProjectCreated()'),self.restoreDefaults)
        QObject.connect(self.iface,SIGNAL('newProjectCreated()'),self.disableAnimationExport)
 
        
        # prepare animation
        self.timer = QTimer()
        QObject.connect(self.timer,SIGNAL('timeout()'),self.playAnimation)

        self.projectHandler = TimeManagerProjectHandler(self.iface)
        
        self.timeLayerManager = TimeLayerManager()
        # establish connections to QgsMapLayerRegistry
        QObject.connect(QgsMapLayerRegistry.instance(),SIGNAL('layerWillBeRemoved(QString)'),self.timeLayerManager.removeTimeLayer)
        QObject.connect(QgsMapLayerRegistry.instance(),SIGNAL('removedAll()'),self.timeLayerManager.clearTimeLayerList)   
        QObject.connect(QgsMapLayerRegistry.instance(),SIGNAL('removedAll()'),self.disableAnimationExport) 
        
        self.restoreDefaults()

    def disableAnimationExport(self):
        """disable the animation export button"""
        self.guiControl.disableAnimationExport()

    def restoreDefaults(self):
        """restore plugin default settings"""
        self.animationFrameLength = 2000 # default to 2000 milliseconds
        self.playBackwards = False # play forwards by default
        self.saveAnimation = False
        self.currentMapTimePosition = datetime.now()   
        self.projectHandler.writeSetting('active',True)
        self.setTimeFrameType('days')
        self.setTimeFrameSize(1)

    def initGui(self):
        """initialize the plugin dock"""
        self.guiControl = TimeManagerGuiControl(self.iface,self.timeLayerManager)
        
        QObject.connect(self.guiControl,SIGNAL('stopAnimation()'),self.stopAnimation)   
        QObject.connect(self.guiControl,SIGNAL('showOptions()'),self.showOptionsDialog) 
        QObject.connect(self.guiControl,SIGNAL('exportVideo()'),self.exportVideo)
        QObject.connect(self.guiControl,SIGNAL('toggleTime()'),self.toggleTimeManagement)
        QObject.connect(self.guiControl,SIGNAL('back()'),self.stepBackward)
        QObject.connect(self.guiControl,SIGNAL('forward()'),self.stepForward)
        QObject.connect(self.guiControl,SIGNAL('play()'),self.toggleAnimation)   
        QObject.connect(self.guiControl,SIGNAL('setCurrentTime(PyQt_PyObject)'),self.setCurrentTimePosition)
        QObject.connect(self.guiControl,SIGNAL('setTimeFrameType(QString)'),self.setTimeFrameType)
        QObject.connect(self.guiControl,SIGNAL('setTimeFrameSize(PyQt_PyObject)'),self.setTimeFrameSize)        
        QObject.connect(self.guiControl,SIGNAL('saveOptionsStart()'),self.timeLayerManager.clearTimeLayerList)        
        QObject.connect(self.guiControl,SIGNAL('saveOptionsEnd()'),self.writeSettings) 
        QObject.connect(self.guiControl,SIGNAL('saveOptionsEnd()'),self.timeLayerManager.refresh) # sets the time restrictions again              
        QObject.connect(self.guiControl,SIGNAL('setAnimationOptions(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),self.setAnimationOptions)
        QObject.connect(self.guiControl,SIGNAL('registerTimeLayer(PyQt_PyObject)'),self.timeLayerManager.registerTimeLayer)
        
        # create actions
        # F8 button press - show time manager settings
        self.actionShowSettings = QAction(u"Show Time Manager Settings", self.iface.mainWindow())
        self.iface.registerMainWindowAction(self.actionShowSettings, "F8")
        self.guiControl.addActionShowSettings(self.actionShowSettings)
        QObject.connect(self.actionShowSettings, SIGNAL('triggered()'),self.showOptionsDialog)
        
        # establish connections to timeLayerManager
        QObject.connect(self.timeLayerManager,SIGNAL('timeRestrictionsRefreshed(PyQt_PyObject)'),self.guiControl.refreshTimeRestrictions)
        QObject.connect(self.timeLayerManager,SIGNAL('projectTimeExtentsChanged(PyQt_PyObject)'),self.guiControl.updateTimeExtents)
        QObject.connect(self.timeLayerManager,SIGNAL('toggledManagement(PyQt_PyObject)'),self.toggleOnOff)  
        QObject.connect(self.timeLayerManager,SIGNAL('lastLayerRemoved()'),self.disableAnimationExport)  

    def setAnimationOptions(self,length,playBackwards,loopAnimation):
        """set length and play direction of the animation""" #animationFrameLength,playBackwards,loopAnimation
        self.animationFrameLength = length
        self.playBackwards = playBackwards
        self.loopAnimation = loopAnimation

    def showOptionsDialog(self):
        """show options dialog"""
        self.stopAnimation()
        self.guiControl.showOptionsDialog(self.timeLayerManager.getTimeLayerList(),self.animationFrameLength,self.playBackwards,self.loopAnimation)

    def exportVideo(self):
        """export 'video' - currently only image sequence"""
        self.saveAnimationPath = str(QFileDialog.getExistingDirectory (self.iface.mainWindow(),'Pick export destination',self.saveAnimationPath))
        if self.saveAnimationPath:
            self.saveAnimation = True
            self.loopAnimation = False # on export looping has to be deactivated
            self.toggleAnimation()
            QMessageBox.information(self.iface.mainWindow(),'Export Video','Image sequence is being saved to '+self.saveAnimationPath+'.\n\nPlease wait until the process is finished.')

    def unload(self):
        """unload the plugin"""
        self.timeLayerManager.deactivateTimeManagement() 
        self.iface.unregisterMainWindowAction(self.actionShowSettings) 
        self.guiControl.unload()
        
    def toggleAnimation(self):
        """toggle animation on/off"""
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(self.animationFrameLength) 
            self.animationFrameCounter = 0
            expectedNumberOfFrames = self.timeLayerManager.getFrameCount()
            if expectedNumberOfFrames == 0: # will be zero if no layer is time managed
                self.timer.stop()
            self.exportNameDigits = len(str(expectedNumberOfFrames))

    def toggleOnOff(self,turnOn):
        """write plugin status (on/off) to project settings"""
        if turnOn:
            self.projectHandler.writeSetting('active',True)
            #self.guiControl.showLabel = True
            pass
        else:
            self.projectHandler.writeSetting('active',False)
            #self.guiControl.showLabel = False
            pass
        self.guiControl.refreshMapCanvas('toggleOnOff')

    def playAnimation(self):
        """play animation in map window"""
        # check if the end of the project time extents has been reached
        projectTimeExtents = self.timeLayerManager.getProjectTimeExtents()
        currentTime = self.timeLayerManager.getCurrentTimePosition()
        
        if self.saveAnimation:
            fileName = os.path.join(self.saveAnimationPath,"frame"+str(self.animationFrameCounter).zfill(self.exportNameDigits)+".PNG")
            self.saveCurrentMap(fileName)
            self.animationFrameCounter += 1
        
        try:
            if self.playBackwards:
                if currentTime > projectTimeExtents[0]:
                    self.stepBackward()
                else:
                    if self.loopAnimation:
                        self.resetAnimation()
                    else:
                        self.stopAnimation()
            else:
                if currentTime < projectTimeExtents[1]:
                    self.stepForward()
                else:
                    if self.loopAnimation:
                        self.resetAnimation()
                    else:
                        self.stopAnimation()
        except TypeError:
            self.stopAnimation()

    def saveCurrentMap(self,fileName):
        """saves the content of the map canvas to file"""
        self.iface.mapCanvas().saveAsImage(fileName)

    def stopAnimation(self):
        """stop the animation in case it's running"""
        if self.saveAnimation:
            QMessageBox.information(self.iface.mainWindow(),'Export finished','The export finished successfully!')
            self.saveAnimation=False
        self.timer.stop()
        self.guiControl.turnPlayButtonOff()
        
    def resetAnimation(self):
        """reset animation to start over from the beginning"""
        projectTimeExtents = self.timeLayerManager.getProjectTimeExtents()
        self.setCurrentTimePosition(projectTimeExtents[0])

    def toggleTimeManagement(self):
        """toggle time management on/off"""
        self.stopAnimation()
        self.timeLayerManager.toggleTimeManagement()

    def stepBackward(self):
        """move one step backward in time"""
        self.timeLayerManager.stepBackward()
        self.writeSettings()

    def stepForward(self):
        """move one step forward in time"""
        self.timeLayerManager.stepForward()
        self.writeSettings()

    def setCurrentTimePosition(self,timePosition):
        """set timeLayerManager's current time position"""
        original = timePosition
        if type(timePosition) == QDateTime:
            # convert QDateTime to datetime :S
            timePosition = datetime.strptime( str(timePosition.toString('yyyy-MM-dd hh:mm:ss')) ,"%Y-%m-%d %H:%M:%S")
        elif type(timePosition) == int or type(timePosition) == float:
            timePosition = datetime.fromtimestamp(timePosition)
        if timePosition == self.currentMapTimePosition:
            return
        self.currentMapTimePosition = timePosition
        #QMessageBox.information(self.iface.mainWindow(),'Info','original = '+str(original)+' - timePosition = '+str(timePosition))
        self.guiControl.refreshTimeRestrictions(timePosition,'setCurrentTimePosition')
        self.timeLayerManager.setCurrentTimePosition(timePosition)

        if self.timeLayerManager.hasActiveLayers() and self.timeLayerManager.isEnabled():
            self.guiControl.refreshMapCanvas('setCurrentTimePosition'+str(timePosition))

        #if self.timeLayerManager.hasActiveLayers():
        #    self.guiControl.showLabel = True
        #else:
        #    self.guiControl.showLabel = False
    
    def setTimeFrameType(self,timeFrameType):
        """set timeLayerManager's time frame type"""
        self.timeLayerManager.setTimeFrameType(timeFrameType)
        self.writeSettings()
        if self.timeLayerManager.hasActiveLayers():
            self.guiControl.refreshMapCanvas('setTimeFrameType')

    def setTimeFrameSize(self,timeFrameSize):
        """set timeLayerManager's time frame size"""
        self.timeLayerManager.setTimeFrameSize(timeFrameSize)
        self.writeSettings()
        if self.timeLayerManager.hasActiveLayers():
            self.guiControl.refreshMapCanvas('setTimeFrameSize')
        
    def writeSettings(self):  
        """write all relevant settings to the project file """
        (timeLayerManagerSettings,timeLayerList) = self.timeLayerManager.getSaveString()
        
        settings= { 'animationFrameLength': self.animationFrameLength,
                 'playBackwards': self.playBackwards,
                 'loopAnimation': self.loopAnimation,
                 'timeLayerManager': timeLayerManagerSettings,
                 'timeLayerList': timeLayerList,
                 'currentMapTimePosition': self.currentMapTimePosition,
                 'timeFrameType': self.timeLayerManager.getTimeFrameType(),
                 'timeFrameSize': self.timeLayerManager.getTimeFrameSize() }
                 
        self.projectHandler.writeSettings(settings)
        
    def readSettings(self):
        """load and restore settings from project file"""
        # list of settings to restore
        settings= { 'animationFrameLength': self.animationFrameLength,
                 'playBackwards': self.playBackwards,
                 'loopAnimation': self.loopAnimation,
                 'timeLayerManager': '',
                 'timeLayerList': QStringList,
                 'currentMapTimePosition': self.currentMapTimePosition,
                 'timeFrameType': self.timeLayerManager.getTimeFrameType(),
                 'timeFrameSize': self.timeLayerManager.getTimeFrameSize(),
                 'active': True }
        settings = self.projectHandler.readSettings(settings)
        
        # list of restore functions and associated default values 
        functions = { 
                 'currentMapTimePosition': (self.restoreSettingCurrentMapTimePosition,None), # this has to be first, because otherwise it might get over-written by other methods
                 'animationFrameLength': (self.restoreSettingAnimationFrameLength,1),
                 'playBackwards': (self.restoreSettingPlayBackwards,0),
                 'loopAnimation': (self.restoreSettingLoopAnimation,0),
                 'timeLayerManager': (self.restoreSettingTimeLayerManager,None),
                 'timeLayerList': (self.restoreTimeLayers,None),
                 'timeFrameType': (self.restoreSettingTimeFrameType,'hours'),
                 'timeFrameSize': (self.restoreSettingTimeFrameSize,1),
                 'active': (self.restoreSettingActive,1)
                 }
                 
        savedTimePosition = datetime.fromtimestamp(1)
        try: # save the timePosition first because it might get over-written by successive functions
            savedTimePosition = datetime.fromtimestamp(settings['currentMapTimePosition'])
        except KeyError:
            pass
        except TypeError:
            pass
         
        # now restore all settings
        for setting,(func,value) in functions.items():
            try:
                value = settings[setting]
            except KeyError:
                pass
            try:
                func(value)
            except TypeError:
                QMessageBox.information(self.iface.mainWindow(),'Error','An error occured while loading: '+setting+'\nValue: '+str(value)+'\nType: '+str(type(value)))
        
        # finally, set the currentMapTimePosition         
        if savedTimePosition:
            #QMessageBox.information(self.iface.mainWindow(),'Info','savedTimePosition = '+str(savedTimePosition))
            self.restoreSettingCurrentMapTimePosition(savedTimePosition)
        
    def restoreSettingAnimationFrameLength(self,value):
        """restore animationFrameLength"""
        if value:
            self.animationFrameLength = value
    
    def restoreSettingPlayBackwards(self,value):
        """restore playBackwards"""
        if value:
            self.playBackwards = value   
        
    def restoreSettingLoopAnimation(self,value):
        """restore loopAnimation"""
        if value:
            self.loopAnimation = value
        
    def restoreSettingTimeLayerManager(self,value):
        """restore timeLayerManager"""
        if value:
            self.timeLayerManager.restoreFromSaveString(value)
  
    def restoreTimeLayers(self,value):
        """restore all time layers"""
        if value:
            layerInfo = value
            if len(layerInfo):
                self.guiControl.enableAnimationExport()
            for l in layerInfo: # for every layer entry
                l = l.split(';')
                layer = QgsMapLayerRegistry.instance().mapLayer(l[0]) # get the layer
                if not layer:
                    break
                layer.setSubsetString(l[1]) # restore the original subset string
                fromTimeAttribute=l[2]
                toTimeAttribute=l[3]
                enabled=l[4]
                timeFormat=l[5]
                try:
                    offset=l[6]
                except IndexError: # old versions didn't have an offset option
                    offset=0
                try:
                    timeLayer = TimeLayer(layer,fromTimeAttribute,toTimeAttribute,enabled=="True",timeFormat,offset) # create a new TimeLayer
                except InvalidTimeLayerError, e:
                    QMessageBox.information(self.iface.mainWindow(),'Error','An error occured while trying to add layer '+layer.name()+' to TimeManager.\n'+e.value)
                    return False
                self.timeLayerManager.registerTimeLayer(timeLayer) 
                self.guiControl.showLabel = True
                self.guiControl.refreshMapCanvas('restoreTimeLayer')
            return True          
             
    def restoreSettingCurrentMapTimePosition(self,value):
        """restore currentMapTimePosition"""
        if value:
            try:
                self.setCurrentTimePosition(value)
            except:
                QMessageBox.information(self.iface.mainWindow(),'Error','An error occured in self.setCurrentTimePosition')
            try:        
                self.guiControl.refreshTimeRestrictions(value,'readSettings')         
            except:
                QMessageBox.information(self.iface.mainWindow(),'Error','An error occured in self.guiControl.refreshTimeRestrictions')

        
    def restoreSettingTimeFrameType(self,value):
        """restore timeFrameType"""
        if value:
            self.guiControl.setTimeFrameType(value)
            self.setTimeFrameType(value)

    def restoreSettingTimeFrameSize(self,value):
        """restore timeFrameSize"""
        if value:
            self.guiControl.setTimeFrameSize(value)
    
    def restoreSettingActive(self,value):
        """restore activity setting"""
        if value: 
            self.timeLayerManager.activateTimeManagement()
            self.guiControl.setActive(True)            
        else: # if the status indicates "off"
            self.timeLayerManager.deactivateTimeManagement()
            self.guiControl.setActive(False)
            
    
