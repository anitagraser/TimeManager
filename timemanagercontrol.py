#!/usr/bin/python
# -*- coding: UTF-8 -*-


from timemanagerguicontrol import *
from timelayerfactory import TimeLayerFactory
from timevectorlayer import * 
from timelayermanager import *
from timemanagerprojecthandler import TimeManagerProjectHandler
from time_util import *
from conf import *



class TimeManagerControl(QObject):
    """Controls the logic behind the GUI. Signals are processed here."""

    def __init__(self,iface):
        """initialize the plugin control. Function gets called even when plugin is inactive"""
        QObject.__init__(self)
        self.iface = iface
        self.setPropagateGuiChanges(True) # set this to False to be able to update the time in
        # the gui without signals getting emitted

    def load(self):
        """ Load the plugin"""
        # order matters
        self.timeLayerManager = TimeLayerManager(self.iface)
        self.guiControl = TimeManagerGuiControl(self.iface)
        self.initViewConnections()
        self.initModelConnections()
        self.initQGISConnections()
        self.restoreDefaults()

    def unload(self):
        """unload the plugin"""
        # FIXME disabling the time manager plugin sometimes crashes QGIS
        # Maybe C related memory issues with slots
        self.getTimeLayerManager().deactivateTimeManagement()
        self.iface.unregisterMainWindowAction(self.actionShowSettings)
        self.guiControl.unload()

        self.iface.projectRead.disconnect(self.readSettings)
        self.iface.newProjectCreated.disconnect(self.restoreDefaults)
        self.iface.newProjectCreated.disconnect(self.disableAnimationExport)
        #QgsProject.instance().writeMapLayer.disconnect(self.writeSettings)
        QObject.disconnect(QgsProject.instance(), SIGNAL("writeProject(QDomDocument &)"),
                           self.writeSettings)

        QgsMapLayerRegistry.instance().layerWillBeRemoved.disconnect(self.timeLayerManager.removeTimeLayer)
        QgsMapLayerRegistry.instance().removeAll.disconnect(self.timeLayerManager.clearTimeLayerList)
        QgsMapLayerRegistry.instance().removeAll.disconnect(self.disableAnimationExport)

    def initQGISConnections(self):
        # QGIS iface connections
        self.iface.projectRead.connect(self.readSettings)
        self.iface.newProjectCreated.connect(self.restoreDefaults)
        self.iface.newProjectCreated.connect(self.disableAnimationExport)
        #QgsProject.instance().writeMapLayer.connect(self.writeSettings)
        QObject.connect(QgsProject.instance(), SIGNAL("writeProject(QDomDocument &)"),
                        self.writeSettings)
        # this signal is responsible for keeping the animation running
        self.iface.mapCanvas().mapCanvasRefreshed.connect(self.waitAfterRenderComplete)

        # establish connections to QgsMapLayerRegistry
        QgsMapLayerRegistry.instance().layerWillBeRemoved.connect(self.timeLayerManager.removeTimeLayer)
        QgsMapLayerRegistry.instance().removeAll.connect(self.timeLayerManager.clearTimeLayerList)
        QgsMapLayerRegistry.instance().removeAll.connect(self.disableAnimationExport)

    def initViewConnections(self, test=False):
        """initialize the View and its connections with everything. If in testing mode, skip the
        Gui"""

        self.guiControl.showOptions.connect(self.showOptionsDialog)
        self.guiControl.exportVideo.connect(self.exportVideo)
        self.guiControl.toggleTime.connect(self.toggleTimeManagement)
        self.guiControl.back.connect(self.stepBackward)
        self.guiControl.forward.connect(self.stepForward)
        self.guiControl.play.connect(self.toggleAnimation)

        self.guiControl.signalCurrentTimeUpdated.connect(
            self.updateTimePositionFromTextBox)
        self.guiControl.signalSliderTimeChanged.connect(
            self.updateTimePositionFromSliderPct)

        self.guiControl.signalTimeFrameType.connect(self.setTimeFrameType)
        self.guiControl.signalTimeFrameSize.connect(self.setTimeFrameSize)
        self.guiControl.signalSaveOptions.connect(self.saveOptions)

        # create actions
        # F8 button press - show time manager settings
        if not test: # Qt doesn't play well with Mock objects
            self.actionShowSettings = QAction(u"Show Time Manager Settings", self.iface.mainWindow())
            self.iface.registerMainWindowAction(self.actionShowSettings, "F8")
            self.guiControl.addActionShowSettings(self.actionShowSettings)
            self.actionShowSettings.triggered.connect(self.showOptionsDialog)

    def initModelConnections(self):

        # establish connections to timeLayerManager
        self.timeLayerManager.timeRestrictionsRefreshed.connect(self.refreshGuiWithCurrentTime)
        self.timeLayerManager.projectTimeExtentsChanged.connect(self.refreshGuiTimeExtents)
        self.timeLayerManager.lastLayerRemoved.connect(self.disableAnimationExport)

    def restoreDefaults(self):
        """restore plugin default settings"""
        self.animationActivated = False
        self.loopAnimation = False
        self.playBackwards = False
        self.animationFrameCounter = 0
        self.saveAnimation = False
        self.saveAnimationPath = os.path.expanduser('~')
        #self.getTimeLayerManager().setCurrentTimePosition(datetime.now()) #FIXME buggy
        self.animationFrameLength = DEFAULT_FRAME_LENGTH
        self.guiControl.setTimeFrameType(DEFAULT_FRAME_UNIT)
        self.guiControl.setTimeFrameSize(DEFAULT_FRAME_SIZE)

    def setPropagateGuiChanges(self, val):
        self.propagateGuiChanges = val


    def refreshGuiTimeExtents(self,timeExtents):
        """update time extents showing in labels and represented by horizontalTimeSlider
        :param timeExtents: a tuple of start and end datetimes
        """
        self.setPropagateGuiChanges(False)
        if timeExtents != (None,None):
            self.guiControl.dock.labelStartTime.setText(datetime_to_str(timeExtents[0],
                                                                     DEFAULT_FORMAT))
            self.guiControl.dock.labelEndTime.setText(datetime_to_str(timeExtents[1],
                                                                    DEFAULT_FORMAT))

            timeLength = datetime_to_epoch(timeExtents[1]) - datetime_to_epoch(timeExtents[0])

            if timeLength> MAX_TIME_LENGTH_SECONDS:
                raise Exception("Time length of {} seconds is too long for QT Slider to handle ("
                           "integer overflow). Maximum value allowed: {}".format(timeLength,
                                                                                 MAX_TIME_LENGTH_SECONDS))

            self.guiControl.dock.horizontalTimeSlider.setMinimum(0)
            self.guiControl.dock.horizontalTimeSlider.setMaximum(timeLength)

        else: # set to default values
            self.guiControl.dock.labelStartTime.setText('not set')
            self.guiControl.dock.labelEndTime.setText('not set')
            self.guiControl.dock.horizontalTimeSlider.setMinimum(conf.MIN_TIMESLIDER_DEFAULT)
            self.guiControl.dock.horizontalTimeSlider.setMaximum(conf.MAX_TIMESLIDER_DEFAULT)

        self.setPropagateGuiChanges(True)

    def refreshGuiWithCurrentTime(self,currentTimePosition,sender=None):
        """update current time showing in dateTimeEditCurrentTime and horizontalTimeSlider"""

        # setting the gui elements should not fire the event for
        # timeChanged, since they were changed to be in sync with the rest of the system on
        # purpose, no need to sync the system again
        self.setPropagateGuiChanges(False)
        if currentTimePosition is None:
            self.setPropagateGuiChanges(True)
            return

        self.guiControl.dock.dateTimeEditCurrentTime.setDateTime(currentTimePosition)
        timeval = datetime_to_epoch(currentTimePosition)
        timeExtents = self.getTimeLayerManager().getProjectTimeExtents()
        try:
            pct = (timeval - datetime_to_epoch(timeExtents[0]))*1.0 / (datetime_to_epoch(
                timeExtents[1]) - datetime_to_epoch(timeExtents[0]))

            sliderVal = self.guiControl.dock.horizontalTimeSlider.minimum() + int(pct * (
                self.guiControl.dock.horizontalTimeSlider.maximum()
                - self.guiControl.dock.horizontalTimeSlider.minimum()))
            #self.debug("Slider val at refresh:{}".format(sliderVal))
            self.guiControl.dock.horizontalTimeSlider.setValue(sliderVal)
            self.guiControl.refreshMapCanvas()
        except:
            pass
        finally:
            self.setPropagateGuiChanges(True)


    def disableAnimationExport(self):
        """disable the animation export button"""
        self.guiControl.disableAnimationExport()

    def getTimeLayerManager(self):
        return self.timeLayerManager

    def getGui(self):
        return self.guiControl

    def showMessage(self, msg, msg_type="Info"):
        if self.showQMessagesEnabled():
            QMessageBox.information(self.iface.mainWindow(),msg_type, msg)

    def showQMessagesEnabled(self):
        return True

    def setAnimationOptions(self,length,playBackwards,loopAnimation):
        """set length and play direction of the animation"""
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
        path = str(QFileDialog.getExistingDirectory (self.iface.mainWindow(),'Pick export '
                                                                       'destination',self.saveAnimationPath))

        self.exportVideoAtPath(path)

    def toggleAnimation(self):
        """toggle animation on/off"""
        #QgsMessageLog.logMessage("Toggle animation called with curr value = {}".format(
        #    self.animationActivated))
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
                #TODO: Friendlier exception, qgsbox etc
                raise Exception("Cannot write to file {}".format(fileName))
            self.saveCurrentMap(fileName)
            self.animationFrameCounter += 1

        resetToEnd = False
        canMakeNextStep = currentTime < projectTimeExtents[1]
        stepFunction = self.stepForward

        if self.playBackwards:
            canMakeNextStep =  currentTime > projectTimeExtents[0]
            resetToEnd = True
            stepFunction = self.stepBackward

        if canMakeNextStep:
            stepFunction()
        else:
            if self.loopAnimation:
                self.resetAnimation(toEnd=resetToEnd)
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
        
    def resetAnimation(self, toEnd=False):
        """reset animation to start over from the beginning"""
        projectTimeExtents = self.timeLayerManager.getProjectTimeExtents()
        if not toEnd:
            self.timeLayerManager.setCurrentTimePosition(projectTimeExtents[0])
        else:
            self.timeLayerManager.setCurrentTimePosition(projectTimeExtents[1])

    def toggleTimeManagement(self):
        """toggle time management on/off"""
        self.stopAnimation()
        self.timeLayerManager.toggleTimeManagement()

    def stepBackward(self):
        """move one step backward in time"""
        self.timeLayerManager.stepBackward()

    def stepForward(self):
        """move one step forward in time"""
        self.timeLayerManager.stepForward()

    def setTimeFrameType(self,timeFrameType):
        """set timeLayerManager's time frame type"""
        self.timeLayerManager.setTimeFrameType(timeFrameType)
        self.guiControl.refreshMapCanvas('setTimeFrameType')

    def setTimeFrameSize(self,timeFrameSize):
        """set timeLayerManager's time frame size"""
        self.timeLayerManager.setTimeFrameSize(timeFrameSize)
        self.guiControl.refreshMapCanvas('setTimeFrameSize')

    def updateTimePositionFromSliderPct(self, pct):
        """See the percentage the slider is at and determine the datetime"""
        if not self.propagateGuiChanges:
            return
        timeExtents = self.getTimeLayerManager().getProjectTimeExtents()
        try:
            realEpochTime = int(pct * (datetime_to_epoch(timeExtents[1]) - datetime_to_epoch(
                timeExtents[0])) + datetime_to_epoch(timeExtents[0]))
        except:
            # extents are not set
            realEpochTime = 0
        self.getTimeLayerManager().setCurrentTimePosition(epoch_to_datetime(realEpochTime))

    def updateTimePositionFromTextBox(self,qdate):
        if not self.propagateGuiChanges:
            return
        self.getTimeLayerManager().setCurrentTimePosition(QDateTime_to_datetime(qdate))
        
    def writeSettings(self, doc):
        """write all relevant settings to the project file XML """
        if not self.getTimeLayerManager().isEnabled():
            #QgsProject.instance().clearProperties() #FIXME this may clear non Time Manager
            # custom properties too
            return
        (timeLayerManagerSettings,timeLayerList) = self.getTimeLayerManager().getSaveString()
        
        if timeLayerManagerSettings is not None:

            settings= { 'animationFrameLength': self.animationFrameLength,
                     'playBackwards': self.playBackwards,
                     'loopAnimation': self.loopAnimation,
                     'timeLayerManager': timeLayerManagerSettings,
                     'timeLayerList': timeLayerList,
                     'currentMapTimePosition':
                         datetime_to_str(self.getTimeLayerManager().getCurrentTimePosition(),
                                                   DEFAULT_FORMAT),
                     'timeFrameType': self.getTimeLayerManager().getTimeFrameType(),
                     'timeFrameSize': self.getTimeLayerManager().getTimeFrameSize(),
                     'active': self.getTimeLayerManager().isEnabled()}

            TimeManagerProjectHandler.writeSettings(settings)

    METASETTINGS= { 'animationFrameLength': int,
             'playBackwards': int,
             'loopAnimation': int,
             'timeLayerManager': str,
             'timeLayerList': list,
             'currentMapTimePosition': str, # can't store datetime in XML
             'timeFrameType': str,
             'timeFrameSize': int,
             'active': int }
        
    def readSettings(self):
        """load and restore settings from project file"""
        # list of settings to restore and their types (needed so that project handler can read
        # them)

        settings = TimeManagerProjectHandler.readSettings(self.METASETTINGS)

        #QgsMessageLog.logMessage("Read settings "+str(settings))

        restore_functions={
                 'currentMapTimePosition': (self.restoreTimePositionFromSettings,None),
                 'animationFrameLength': (self.setAnimationFrameLength,DEFAULT_FRAME_LENGTH),
                 'playBackwards': (self.setPlayBackwards,0),
                 'loopAnimation': (self.setLoopAnimation,0),
                 'timeLayerManager': (self.restoreSettingTimeLayerManager,None),
                 'timeLayerList': (self.restoreTimeLayers,None),
                 'timeFrameType': (self.guiControl.setTimeFrameType,DEFAULT_FRAME_UNIT),
                 'timeFrameSize': (self.guiControl.setTimeFrameSize,DEFAULT_FRAME_SIZE),
                 'active': (self.setActive,0)
        }

        for setting_name in self.METASETTINGS.keys():
            restore_function,default_value = restore_functions[setting_name]
            if setting_name not in settings:
                setting_value = default_value
            else:
                setting_value = settings[setting_name]
            restore_function(setting_value)

    def setAnimationFrameLength(self,value):
        self.animationFrameLength = value
    
    def setPlayBackwards(self,value):
        self.playBackwards = value
        
    def setLoopAnimation(self,value):
        self.loopAnimation = value

    def restoreTimePositionFromSettings(self, value):
        """Restore the time position from settings"""
        if value:
            dt = str_to_datetime(value, DEFAULT_FORMAT) # this also works for integer values
            self.getTimeLayerManager().setCurrentTimePosition(dt)

    def restoreSettingTimeLayerManager(self,value):
        """restore timeLayerManager"""
        self.timeLayerManager.restoreFromSaveString(value)
  
    def restoreTimeLayers(self, layerInfos):
        """restore all time layers"""
        if layerInfos:
            if len(layerInfos)>0:
                self.guiControl.enableAnimationExport()
            for l in layerInfos: # for every layer entry
                try:
                    layer,isEnabled,offset,timeFormat,startTimeAttribute,\
                                  endTimeAttribute,interpolation_enabled, idAttr = ls.getSettingsFromSaveStr(l)

                    timeLayer = TimeLayerFactory.get_timelayer_class_from_layer(layer,interpolate=interpolation_enabled)(layer,
                                                startTimeAttribute,endTimeAttribute,isEnabled,timeFormat,offset)
                except InvalidTimeLayerError, e:
                    self.showMessage('An error occured while trying to add layer  to \
                            TimeManager.\n'+str(e))
                    continue
               
                self.timeLayerManager.registerTimeLayer(timeLayer) 
                self.guiControl.showLabel = True #FFIXME
                self.guiControl.refreshMapCanvas('restoreTimeLayer')

    def saveOptions(self):
        self.getTimeLayerManager().clearTimeLayerList()
        for row in range(self.guiControl.optionsDialog.tableWidget.rowCount()):
            try:
                # add layer from row information
                layer = self.createTimeLayerFromRow(row)
                if layer is None:
                    continue
                self.getTimeLayerManager().registerTimeLayer(layer)
                # save animation options
                animationFrameLength = self.guiControl.optionsDialog.spinBoxFrameLength.value()
                playBackwards = self.guiControl.optionsDialog.checkBoxBackwards.isChecked()
                loopAnimation = self.guiControl.optionsDialog.checkBoxLoop.isChecked()
                self.setAnimationOptions(animationFrameLength,playBackwards,loopAnimation)

                self.guiControl.showLabel = self.guiControl.optionsDialog.checkBoxLabel.isChecked()
                self.guiControl.refreshMapCanvas('saveOptions')
                self.guiControl.dock.pushButtonExportVideo.setEnabled(True)
            except:
                continue

            self.timeLayerManager.refreshTimeRestrictions()


    def createTimeLayerFromRow(self,row):
        """create a TimeLayer from options set in the table row"""
        layer,isEnabled,layerId,offset,timeFormat,\
            startTimeAttribute,endTimeAttribute,interpolation_enabled, \
            idAttr =ls.getSettingsFromRow(self.guiControl.optionsDialog.tableWidget, row)
        try:
            timeLayer = TimeLayerFactory.get_timelayer_class_from_layer(layer, interpolate=interpolation_enabled)(
                layer,startTimeAttribute,endTimeAttribute,enabled = isEnabled,
                timeFormat=timeFormat, offset=offset, iface=self.iface, idAttribute=idAttr)
        except Exception,e:
            QgsMessageLog.logMessage("Error creating timelayer:"+e)
            QMessageBox.information(self.optionsDialog,'Error',
                                    'An error occured while trying to add layer '+layer.name()+' to TimeManager.\n'+str(e))
            return None
        return timeLayer

    
    def setActive(self,value):
        """de/activate the whole thing"""
        if value==True:
            self.timeLayerManager.activateTimeManagement()
            self.guiControl.setActive(True)            
        else: # if the status indicates "off"
            self.timeLayerManager.deactivateTimeManagement()
            self.guiControl.setActive(False)
