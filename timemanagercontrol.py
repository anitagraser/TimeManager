#!/usr/bin/python
# -*- coding: UTF-8 -*-


from timemanagerguicontrol import *
from timelayerfactory import TimeLayerFactory
from timevectorlayer import * 
from timelayermanager import *
from timemanagerprojecthandler import *
from time_util import *

DEFAULT_FRAME_LENGTH = 2000
FRAME_FILENAME_PREFIX = "frame"

class TimeManagerControl(QObject):
    """Controls the logic behind the GUI. Signals are processed here."""

    animationFrameCounter = 0


    def __init__(self,iface):
        """initialize the plugin control"""
        QObject.__init__(self)
        self.iface = iface       
        self.loopAnimation = False
        self.saveAnimation = False
        self.animationActivated = False
        self.animationFrameLength = DEFAULT_FRAME_LENGTH
        self.playBackwards = False
        self.saveAnimationPath = os.path.expanduser('~')

        self.projectHandler = TimeManagerProjectHandler(self.iface)
        self.timeLayerManager = TimeLayerManager(self.iface)

    def disableAnimationExport(self):
        """disable the animation export button"""
        try:
            self.guiControl.disableAnimationExport()
        except AttributeError:
            pass
          
    def restoreDefaults(self):
        """restore plugin default settings"""
        QgsMessageLog.logMessage("resoted defaults")
        self.saveAnimation = False
        self.currentMapTimePosition = datetime.utcnow() # this sets the current time position to
        #  the current *UTC* system time
        self.projectHandler.writeSetting('active',True)
        self.setTimeFrameType('days')
        self.setTimeFrameSize(1)
        self.animationActivated = False


    def getTimeLayerManager(self):
        return self.timeLayerManager

    def showMessage(self, msg, msg_type="Info"):
        if self.showQMessagesEnabled():
            QMessageBox.information(self.iface.mainWindow(),msg_type, msg)

    def showQMessagesEnabled(self):
        return True

    def initGui(self, test=False):
        """initialize the plugin dock. If in testingb mode, skip the Gui"""

        if test:
            from mock import Mock
        if test:
            self.guiControl = Mock()
        else:
            self.guiControl = TimeManagerGuiControl(self.iface,self.timeLayerManager)

        self.guiControl.showOptions.connect(self.showOptionsDialog) 
        self.guiControl.exportVideo.connect(self.exportVideo)
        self.guiControl.toggleTime.connect(self.toggleTimeManagement)
        self.guiControl.back.connect(self.stepBackward)
        self.guiControl.forward.connect(self.stepForward)
        self.guiControl.play.connect(self.toggleAnimation)   
        self.guiControl.signalCurrentTimeUpdated.connect(self.setCurrentTimePosition)
        self.guiControl.signalTimeFrameType.connect(self.setTimeFrameType)
        self.guiControl.signalTimeFrameSize.connect(self.setTimeFrameSize)        
        self.guiControl.saveOptionsStart.connect(self.timeLayerManager.clearTimeLayerList)        
        self.guiControl.saveOptionsEnd.connect(self.writeSettings) 
        self.guiControl.saveOptionsEnd.connect(self.timeLayerManager.refresh) # sets the time restrictions again              
        self.guiControl.signalAnimationOptions.connect(self.setAnimationOptions)
        self.guiControl.registerTimeLayer.connect(self.timeLayerManager.registerTimeLayer)
        
        # create actions
        # F8 button press - show time manager settings
        if not test:
            self.actionShowSettings = QAction(u"Show Time Manager Settings", self.iface.mainWindow())
            self.iface.registerMainWindowAction(self.actionShowSettings, "F8")
            self.guiControl.addActionShowSettings(self.actionShowSettings)
            self.actionShowSettings.triggered.connect(self.showOptionsDialog)

        # establish connections to timeLayerManager
        self.timeLayerManager.timeRestrictionsRefreshed.connect(self.guiControl.refreshGuiWithCurrentTime)
        self.timeLayerManager.projectTimeExtentsChanged.connect(self.guiControl.updateTimeExtents)
        self.timeLayerManager.toggledManagement.connect(self.toggleOnOff)
        self.timeLayerManager.lastLayerRemoved.connect(self.disableAnimationExport)

        
    def setAnimationOptions(self,length,playBackwards,loopAnimation):
        """set length and play direction of the animation""" #animationFrameLength,playBackwards,loopAnimation
        self.animationFrameLength = length
        self.playBackwards = playBackwards
        self.loopAnimation = loopAnimation

    def showOptionsDialog(self):
        """show options dialog"""
        self.stopAnimation()
        self.guiControl.showOptionsDialog(self.timeLayerManager.getTimeLayerList(),self.animationFrameLength,self.playBackwards,self.loopAnimation)


    def exportVideoAtPath(self, path):
        self.saveAnimationPath = path
        if self.saveAnimationPath:
            self.saveAnimation = True
            self.loopAnimation = False # on export looping has to be deactivated
            self.toggleAnimation()
            self.showMessage('Image sequence from current position onwards is being saved to '+self.saveAnimationPath+'.\n\nPlease wait until the process is finished.')

    def exportVideo(self):
        """export 'video' - currently only image sequence"""
        path = str(QFileDialog.getExistingDirectory (self.iface.mainWindow(),
                                                                       'Pick export '
                                                                       'destination',self.saveAnimationPath))
        self.exportVideoAtPath(path)

    def load(self):
        """ Load the plugin"""

        # QGIS iface connections
        self.iface.projectRead.connect(self.readSettings)
        self.iface.newProjectCreated.connect(self.restoreDefaults)
        self.iface.newProjectCreated.connect(self.disableAnimationExport)

        # this signal is responsible for keeping the animation running
        self.iface.mapCanvas().mapCanvasRefreshed.connect(self.waitAfterRenderComplete)

        # establish connections to QgsMapLayerRegistry
        QgsMapLayerRegistry.instance().layerWillBeRemoved.connect(self.timeLayerManager.removeTimeLayer)
        QgsMapLayerRegistry.instance().removeAll.connect(self.timeLayerManager.clearTimeLayerList)
        QgsMapLayerRegistry.instance().removeAll.connect(self.disableAnimationExport)

    def unload(self):
        """unload the plugin"""
        #FIXME unloading time manager sometimes crashes QGIS
        self.timeLayerManager.deactivateTimeManagement() 
        self.iface.unregisterMainWindowAction(self.actionShowSettings) 
        self.guiControl.unload()
        
        self.iface.projectRead.disconnect(self.readSettings)
        self.iface.newProjectCreated.disconnect(self.restoreDefaults)
        self.iface.newProjectCreated.disconnect(self.disableAnimationExport)
        QgsMapLayerRegistry.instance().layerWillBeRemoved.disconnect(self.timeLayerManager.removeTimeLayer)
        QgsMapLayerRegistry.instance().removeAll.disconnect(self.timeLayerManager.clearTimeLayerList)   
        QgsMapLayerRegistry.instance().removeAll.disconnect(self.disableAnimationExport)
        
    def toggleAnimation(self):
        """toggle animation on/off"""
        if self.animationActivated: 
            self.animationActivated = False 
        else:
            self.animationActivated = True

        self.animationFrameCounter = 0
        expectedNumberOfFrames = self.timeLayerManager.getFrameCount()
        if expectedNumberOfFrames == 0: # will be zero if no layer is time managed
            self.animationActivated = False
        self.exportNameDigits = len(str(expectedNumberOfFrames))
        self.startAnimation() # if animation is activated, it will start



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

    def startAnimation(self):
        """kick-start the animation, afterwards the animation will run based on signal chains"""
        self.waitAfterRenderComplete()
        
    def waitAfterRenderComplete(self, painter=None):
        """when the map canvas signals renderComplete, wait defined millisec until next animation step"""
        if self.saveAnimation: # make animation/export run as fast as possible
            self.playAnimation(painter)
        else:
            QTimer.singleShot(self.animationFrameLength,self.playAnimation)

    def generate_frame_filename(self, path, frame_index, currentTime):
         return os.path.join(path,"{}{}_{}.png".format(FRAME_FILENAME_PREFIX,
                                                       str(frame_index).zfill(self.exportNameDigits), str(currentTime).replace(" ","_").replace(":","_")))
        
    def playAnimation(self,painter=None):
        """play animation in map window"""
        if not self.animationActivated:
            return
        
        # check if the end of the project time extents has been reached
        projectTimeExtents = self.timeLayerManager.getProjectTimeExtents()
        currentTime = self.timeLayerManager.getCurrentTimePosition()
        
        if self.saveAnimation:
            fileName = self.generate_frame_filename(self.saveAnimationPath,
                                                    self.animationFrameCounter, currentTime)

            # try accessing the file or fail with informative exception
            try:
                 open(fileName, 'a').close()
            except:
                raise Exception("Cannot write to file {}".format(fileName))
            self.saveCurrentMap(fileName)
            #self.debug("saving animation for time: {}".format(currentTime))
            self.animationFrameCounter += 1

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


    def saveCurrentMap(self,fileName):
        """saves the content of the map canvas to file"""
        self.iface.mapCanvas().saveAsImage(fileName)

    def stopAnimation(self):
        """stop the animation in case it's running"""
        if self.saveAnimation:

            self.showMessage('The export finished successfully!')
            self.saveAnimation = False
        self.animationActivated = False 
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
        
    def getCurrentTimePosition(self):
        """get timeLayerManager's current time position in datetime"""
        return self.timeLayerManager.getCurrentTimePosition()

    def setCurrentTimePosition(self,timePosition):
        """set timeLayerManager's current time position"""

        self.currentMapTimePosition = timePosition
        self.guiControl.refreshGuiWithCurrentTime(timePosition,
                                                'timemanagercontrol.setCurrentTimePosition')
        self.timeLayerManager.setCurrentTimePosition(timePosition)

        if self.timeLayerManager.hasActiveLayers() and self.timeLayerManager.isEnabled():
            self.guiControl.refreshMapCanvas('setCurrentTimePosition'+str(
                timePosition))

    
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
        
        if timeLayerManagerSettings:    
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
                 'timeLayerList': [], #QStringList,
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
                 'timeFrameType': (self.restoreSettingTimeFrameType,'days'),
                 'timeFrameSize': (self.restoreSettingTimeFrameSize,1),
                 'active': (self.restoreSettingActive,1)
                 }
                 
        savedTimePosition = datetime.utcfromtimestamp(1)
        try: # save the timePosition first because it might get over-written by successive functions
            savedTimePosition = datetime.utcfromtimestamp(settings['currentMapTimePosition'])
        except KeyError:
            pass
        except TypeError:
            pass
         
        # now restore all settings
        for setting,(func,value) in functions.items():
            if setting =='currentMapTimePosition':
                continue
            try:
                value = settings[setting]
            except KeyError:
                pass
            try:
                func(value)
            except Exception as e:
                self.showMessage('An error occured while loading: '+setting+'\nValue: '+str(value)+'\nType: '+str(type(value))+", error"+str(e))
                #TODO also log
                #FIXME some bugs lurking here
        
        # finally, set the currentMapTimePosition         
        if savedTimePosition:
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
  
    def restoreTimeLayers(self, value):
        """restore all time layers"""
        #FIXME What is value here?
        if value:
            layerInfo = value
            if len(layerInfo):
                self.guiControl.enableAnimationExport()
            for l in layerInfo: # for every layer entry
                l = l.split(';')
                layer = QgsMapLayerRegistry.instance().mapLayer(l[0]) # get the layer
                if not layer:
                    continue

                timeLayerClass = TimeLayerFactory.get_timelayer_class_from_layer(layer)
                if timeLayerClass == TimeVectorLayer:
                    layer.setSubsetString(l[1]) # restore the original subset string, only available for vector layers!
                    
                startTimeAttribute=l[2]
                endTimeAttribute=l[3]
                isEnabled=l[4]
                timeFormat=l[5]
                
                try:
                    offset=l[6]
                except IndexError: # old versions didn't have an offset option
                    offset=0
                    
                try: # here we use the previously determined class
                    timeLayer = timeLayerClass(layer,startTimeAttribute,endTimeAttribute,isEnabled,timeFormat,offset)
                except InvalidTimeLayerError, e:
                    self.showMessage('An error occured while trying to add layer '+layer.name()+' to \
                            TimeManager.\n'+e.value)
                    return
               
                self.timeLayerManager.registerTimeLayer(timeLayer) 
                self.guiControl.showLabel = True
                self.guiControl.refreshMapCanvas('restoreTimeLayer')
    
    def restoreSettingCurrentMapTimePosition(self,value):
        """restore currentMapTimePosition"""
        if value:
            self.setCurrentTimePosition(value)       
            self.guiControl.refreshGuiWithCurrentTime(value,'readSettings')
        
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
            
    
