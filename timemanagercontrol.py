#!/usr/bin/python
# -*- coding: UTF-8 -*-

from PyQt4 import QtCore, QtGui

from timemanagerguicontrol import *
from timelayerfactory import TimeLayerFactory
from timevectorlayer import * 
from timelayermanager import *
from timemanagerprojecthandler import TimeManagerProjectHandler
from time_util import *
import time_util
import bcdate_util
from bcdate_util import BCDate
from conf import *
from logging import info, warn, error, log_exceptions

import math
import traceback
from collections import OrderedDict


class TimeManagerControl(QObject):
    """Controls the logic behind the GUI. Signals are processed here."""

    @classmethod
    def isEqualToUntranslatedString(cks, potentiallyTranslatedString, comparisonBaseString,context):
        """This function checks for string equality when the UI strings may have been translated"""
        return potentiallyTranslatedString == QCoreApplication.translate(context ,comparisonBaseString)


    def __init__(self,iface):
        """initialize the plugin control. Function gets called even when plugin is inactive"""
        QObject.__init__(self)
        self.iface = iface
        self.setPropagateGuiChanges(True) # set this to False to be able to update the time in
        # the gui without signals getting emitted

    def load(self):
        """ Load the plugin"""
        # order matters
        self.timeLayerManager = TimeLayerManager(self.iface) # the model
        self.guiControl = TimeManagerGuiControl(self.iface, self.timeLayerManager) # the view
        self.initViewConnections()
        self.initModelConnections()
        self.initQGISConnections()
        self.restoreDefaults()

    def getGranularitySeconds(self):
        """Trick to make QtSlider support more than the integer range of seconds"""
        return self.granularity

    def setGranularitySeconds(self, granularity):
        self.granularity = granularity

    def unload(self):
        """unload the plugin"""
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
        self.guiControl.toggleArchaeology.connect(self.toggleArchaeology)
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

        self.guiControl.signalArchDigitsSpecified.connect(self.saveArchDigits)
        self.guiControl.signalArchCancelled.connect(self.setArchaeology)
        

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
        self.granularity = conf.DEFAULT_GRANULARITY_IN_SECONDS
        self.animationActivated = False
        self.loopAnimation = False
        self.playBackwards = False
        self.animationFrameCounter = 0
        self.saveAnimation = False
        self.saveAnimationPath = os.path.expanduser('~')
        self.animationFrameLength = DEFAULT_FRAME_LENGTH
        self.restoreTimeFrameType(DEFAULT_FRAME_UNIT)
        self.guiControl.setTimeFrameSize(DEFAULT_FRAME_SIZE)

    def setPropagateGuiChanges(self, val):
        self.propagateGuiChanges = val

    @log_exceptions
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

            if timeLength> MAX_TIME_LENGTH_SECONDS_SLIDER:
                new_granularity = int(math.ceil(1.0*timeLength/MAX_TIME_LENGTH_SECONDS_SLIDER))
                self.setGranularitySeconds(new_granularity)
                # trick because timeLength must fit in an integer
                # since it interfaces with a C++ class
                newTimeLength = int(math.ceil(1.0*timeLength/new_granularity))
                timeLength = newTimeLength

            else:
                self.setGranularitySeconds(1)

            self.guiControl.dock.horizontalTimeSlider.setMinimum(0)
            self.guiControl.dock.horizontalTimeSlider.setMaximum(timeLength)

        else: # set to default values
            self.setGranularitySeconds(1)
            self.guiControl.dock.labelStartTime.setText('not set')
            self.guiControl.dock.labelEndTime.setText('not set')
            self.guiControl.dock.horizontalTimeSlider.setMinimum(conf.MIN_TIMESLIDER_DEFAULT)
            self.guiControl.dock.horizontalTimeSlider.setMaximum(conf.MAX_TIMESLIDER_DEFAULT)

        self.setPropagateGuiChanges(True)

    @log_exceptions
    def refreshGuiWithCurrentTime(self,currentTimePosition,sender=None):
        """update the gui when time has changed by refreshing/repainting the layers
        and changing the time showing in dateTimeEditCurrentTime and horizontalTimeSlider"""
        # setting the gui elements should not fire the event for
        # timeChanged, since they were changed to be in sync with the rest of the system on
        # purpose, no need to sync the system again
        self.setPropagateGuiChanges(False)
        if currentTimePosition is None:
            self.setPropagateGuiChanges(True)
            return

        time_util.updateUi(self.guiControl.getTimeWidget(), currentTimePosition)
        timeval = datetime_to_epoch(currentTimePosition)
        timeExtents = self.getTimeLayerManager().getProjectTimeExtents()
        try:
            pct = (timeval - datetime_to_epoch(timeExtents[0]))*1.0 / (datetime_to_epoch(
                timeExtents[1]) - datetime_to_epoch(timeExtents[0]))

            sliderVal = self.guiControl.dock.horizontalTimeSlider.minimum() + int(pct * (
                self.guiControl.dock.horizontalTimeSlider.maximum()
                - self.guiControl.dock.horizontalTimeSlider.minimum()))
            self.guiControl.dock.horizontalTimeSlider.setValue(sliderVal)
            self.guiControl.repaintRasters()
            self.guiControl.repaintJoined()
            self.guiControl.repaintVectors()
            self.guiControl.refreshMapCanvas()
        except Exception,e:
            error(e)
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
        if self.animationActivated: 
            self.animationActivated = False 
        else:
            self.animationActivated = True

        self.animationFrameCounter = 0
        expectedNumberOfFrames = self.timeLayerManager.getFrameCount()
        if expectedNumberOfFrames == 0: # will be zero if no layer is time managed
            self.animationActivated = False
            if len(self.getTimeLayerManager().getTimeLayerList())>0:
                error("Have layers, but animation not possible")
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

    def exportEmpty(self):
        return self.guiControl.exportEmpty

    def playAnimation(self,painter=None):
        """play animation in map window"""
        if not self.animationActivated:
            return
        # check if the end of the project time extents has been reached
        projectTimeExtents = self.timeLayerManager.getProjectTimeExtents()
        currentTime = self.timeLayerManager.getCurrentTimePosition()
        if self.saveAnimation and (self.exportEmpty() or (not self.exportEmpty() and
                                                           self.timeLayerManager.haveVisibleFeatures())):
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

    def toggleArchaeology(self):
        if time_util.is_archaelogical():
            self.setArchaeology(False)
        else:
            self.guiControl.showArchOptions()

    def saveArchDigits(self, digits):
        self.setArchaeology(True)
        time_util.setArchDigits(digits)

    def setArchaeology(self, enabled=0):
        if enabled == 0 :
            if filter(lambda x:time_util.is_archaeological_layer(x), self.getTimeLayerManager().layers()):
                QMessageBox.information(self.iface.mainWindow(),'Error', "Already have archaeological layers in the project."+\
                "Please delete them to switch to normal mode")
                self.guiControl.setArchaeologyPressed(True)
                return
            time_util.setCurrentMode(time_util.NORMAL_MODE)
            self.guiControl.setWindowTitle("Time Manager")
            self.guiControl.setArchaeologyPressed(False)
            self.guiControl.disableArchaeologyTextBox()

        else:
            if filter(lambda x: not time_util.is_archaeological_layer(x), self.getTimeLayerManager().layers()):
                QMessageBox.information(self.iface.mainWindow(),'Error', "Already have non archaeological layers in the project."+\
                "Please delete them to switch to archaeological mode")
                self.guiControl.setArchaeologyPressed(False)
                return
            time_util.setCurrentMode(time_util.ARCHAELOGY_MODE)
            self.guiControl.setWindowTitle("Time Manager Archaeology Mode")
            self.guiControl.setArchaeologyPressed(True)
            ctx = self.guiControl.dock.objectName()
            try:
                self.guiControl.setTimeFrameType(QCoreApplication.translate(ctx,'years'))
            except:
                error("should only happen during testing")
            self.guiControl.enableArchaeologyTextBox()
            self.showMessage("Archaelogy mode enabled. Expecting data of the form YYYY BC or YYYY AD."+\
                    " Disable to work with regular datetimes from year 1 onwards")

    def stepBackward(self):
        """move one step backward in time"""
        self.timeLayerManager.stepBackward()

    def stepForward(self):
        """move one step forward in time"""
        self.timeLayerManager.stepForward()

    def setTimeFrameType(self,timeFrameType):
        """set timeLayerManager's time frame type from a potentially foreign languange string"""
        
        ctx = self.guiControl.dock.objectName()
        for frame_type in ['microseconds','milliseconds','seconds','minutes','hours','years',
                         'months','weeks','days']:
            if self.isEqualToUntranslatedString(timeFrameType,frame_type,
                                                context=ctx):
                self.timeLayerManager.setTimeFrameType(frame_type)
                self.guiControl.refreshMapCanvas('setTimeFrameType')
                if self.isEqualToUntranslatedString(timeFrameType,"microseconds",ctx) or \
                        self.isEqualToUntranslatedString(timeFrameType,"milliseconds",ctx):
                    QMessageBox.information(self.iface.mainWindow(),'Information',
                        "Microsecond and millisecond support works best when the input data "\
                        "contains millisecond information (ie, a decimal part)")

                return

        warn("Unrecognized time frame type : {}".format(timeFrameType))

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
            realEpochTime = int(pct  * (datetime_to_epoch(timeExtents[1]) - datetime_to_epoch(
                timeExtents[0]))  + datetime_to_epoch(timeExtents[0]))
        except:
            # extents are not set
            realEpochTime = 0

        self.getTimeLayerManager().setCurrentTimePosition(epoch_to_datetime(realEpochTime))

    @log_exceptions
    def updateTimePositionFromTextBox(self,date):
        if not self.propagateGuiChanges:
            return
        if time_util.is_archaelogical():
            bcdate = bcdate_util.BCDate.from_str(date, strict_zeros=False)
            bcdate.setDigits(bcdate_util.getGlobalDigitSetting())
            self.getTimeLayerManager().setCurrentTimePosition(bcdate)
        else:
            self.getTimeLayerManager().setCurrentTimePosition(QDateTime_to_datetime(date))

    def restoreTimeFrameType(self, text):
        try:
            self.guiControl.setTimeFrameType(QCoreApplication.translate(
                self.guiControl.dock.objectName(),text))
        except: # tests dont work with mocked qcoreapplications unfortunately
            pass
        
    def writeSettings(self, doc):
        """write all relevant settings to the project file XML """
        if not self.getTimeLayerManager().isEnabled():
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
                     'active': self.getTimeLayerManager().isEnabled(),
                     'mode': int(time_util.is_archaelogical()),
                     'digits': time_util.getArchDigits()}

            TimeManagerProjectHandler.writeSettings(settings)

    METASETTINGS= OrderedDict()
    METASETTINGS['mode']=int
    METASETTINGS['digits']=int
    METASETTINGS['animationFrameLength']= int
    METASETTINGS['playBackwards']= int
    METASETTINGS['loopAnimation']= int
    METASETTINGS['timeLayerManager']= str
    METASETTINGS['timeLayerList']= list
    METASETTINGS['currentMapTimePosition'] = str # can't store datetime in XML
    METASETTINGS['timeFrameType'] = str
    METASETTINGS['timeFrameSize'] = int
    METASETTINGS['active']= int
        
    def readSettings(self):
        """load and restore settings from project file"""
        # list of settings to restore and their types (needed so that project handler can read
        # them)

        settings = TimeManagerProjectHandler.readSettings(self.METASETTINGS)

        restore_functions={
                 'mode': (self.setArchaeology, 0),
                 'digits': (time_util.setArchDigits, conf.DEFAULT_DIGITS),
                 'currentMapTimePosition': (self.restoreTimePositionFromSettings,None),
                 'animationFrameLength': (self.setAnimationFrameLength,DEFAULT_FRAME_LENGTH),
                 'playBackwards': (self.setPlayBackwards,0),
                 'loopAnimation': (self.setLoopAnimation,0),
                 'timeLayerManager': (self.restoreSettingTimeLayerManager,None),
                 'timeLayerList': (self.restoreTimeLayers,None),
                 'timeFrameType': (self.restoreTimeFrameType,DEFAULT_FRAME_UNIT),
                 'timeFrameSize': (self.guiControl.setTimeFrameSize,DEFAULT_FRAME_SIZE),
                 'active': (self.setActive,0),
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
                    settings = ls.getSettingsFromSaveStr(l)
                    if settings.layer is None:
                        error_msg = "Could not restore layer with id {} from saved project line {}".\
                                format(settings.layerId, l)
                        error(error_msg)
                        self.showMessage(error_msg)
                        continue

                    timeLayer = TimeLayerFactory.get_timelayer_class_from_layer(settings.layer,
                                interpolate=settings.interpolationEnabled)(settings,iface=self.iface)

                except Exception, e:
                    layerId = "unknown"
                    try:
                        layerId = settings.layerId
                    except:
                        pass
                    error_msg = "An error occured while trying to restore layer "+layerId\
                            +" to TimeManager."+traceback.format_exc(e)
                    error(error_msg)
                    self.showMessage(error_msg)
                    continue
               
                self.timeLayerManager.registerTimeLayer(timeLayer)
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
                self.guiControl.exportEmpty = not \
                    self.guiControl.optionsDialog.checkBoxDontExportEmpty.isChecked()
                self.guiControl.showLabel = self.guiControl.optionsDialog.checkBoxLabel.isChecked()
                self.guiControl.refreshMapCanvas('saveOptions')
                self.guiControl.dock.pushButtonExportVideo.setEnabled(True)
            except:
                continue

            self.timeLayerManager.refreshTimeRestrictions()


    def createTimeLayerFromRow(self,row):
        """create a TimeLayer from options set in the table row"""
        try:
            settings = ls.getSettingsFromRow(self.guiControl.optionsDialog.tableWidget, row)
            timeLayer = TimeLayerFactory.get_timelayer_class_from_layer(settings.layer,
                                                    interpolate=settings.interpolationEnabled)(
                settings, self.iface)
        except Exception, e:
            layer_name = "unknown"
            try:
                layer_name = settings.layer.name()
            except:
                pass
            error_msg = "An error occured while trying to add layer "\
                    +layer_name+" to TimeManager. Cause: "+str(e)
            error(error_msg+traceback.format_exc(e))
            self.showMessage(error_msg)
            return None
        return timeLayer

    
    def setActive(self,value):
        """de/activate the whole thing"""
        if value:
            self.timeLayerManager.activateTimeManagement()
            self.guiControl.setActive(True)            
        else: # if the status indicates "off"
            self.timeLayerManager.deactivateTimeManagement()
            self.guiControl.setActive(False)
