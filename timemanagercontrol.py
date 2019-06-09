from __future__ import absolute_import
from builtins import str
from builtins import range

import os
import math
import traceback
from qgis.PyQt.QtCore import QObject, QCoreApplication, QTimer
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from collections import OrderedDict

from qgis.core import QgsProject

try:
    from qgis.core import QgsMapLayerRegistry
except ImportError:
    pass

from timemanager.utils.tmlogging import info, warn, error, log_exceptions

from timemanager.utils import bcdate_util, time_util


from timemanager.timemanagerguicontrol import TimeManagerGuiControl, MAX_TIME_LENGTH_SECONDS_SLIDER
from timemanager.layers.timelayerfactory import TimeLayerFactory
from timemanager.layers.timelayermanager import TimeLayerManager
from timemanager.timemanagerprojecthandler import TimeManagerProjectHandler
from timemanager.animation import animate

from timemanager import conf
from timemanager.layers import layer_settings


class TimeManagerControl(QObject):
    """Controls the logic behind the GUI. Signals are processed here."""

    @classmethod
    def isEqualToUntranslatedString(cks, potentiallyTranslatedString, comparisonBaseString, context):
        """Check for string equality when the UI strings may have been translated"""
        return potentiallyTranslatedString == QCoreApplication.translate(context, comparisonBaseString)

    def __init__(self, iface):
        """Initialize the plugin control. Function gets called even when plugin is inactive"""
        QObject.__init__(self)
        self.iface = iface
        # set the following to False to be able to update the time in the GUI without signals getting emitted
        self.setPropagateGuiChanges(True)

    def load(self):
        """Load the plugin"""
        # Order matters!
        self.timeLayerManager = TimeLayerManager(self.iface)
        self.guiControl = TimeManagerGuiControl(self.iface, self.timeLayerManager)
        self.initGuiConnections()
        self.initLayerManagerConnections()
        self.initQGISConnections()
        self.restoreDefaults()
        info("TimeManager: $Id$ loaded!")

    def getGranularitySeconds(self):
        """Trick to make QtSlider support more than the integer range of seconds"""
        return self.granularity

    def setGranularitySeconds(self, granularity):
        self.granularity = granularity

    def unload(self):
        """Unload the plugin"""
        self.getTimeLayerManager().deactivateTimeManagement()
        self.iface.unregisterMainWindowAction(self.actionShowSettings)
        self.guiControl.unload()
        del self.guiControl # actually remove the gui panel
        self.iface.projectRead.disconnect(self.readSettings)
        self.iface.newProjectCreated.disconnect(self.restoreDefaults)
        self.iface.newProjectCreated.disconnect(self.disableAnimationExport)
        # QgsProject.instance().writeMapLayer.disconnect(self.writeSettings)
        QgsProject.instance().writeProject.disconnect(self.writeSettings)

        if hasattr(QgsProject, "layerWillBeRemoved"):
            instance = QgsProject.instance()
        else:
            instance = QgsMapLayerRegistry.instance()

        instance.layerWillBeRemoved.disconnect(self.timeLayerManager.removeTimeLayer)
        instance.removeAll.disconnect(self.timeLayerManager.clearTimeLayerList)
        instance.removeAll.disconnect(self.disableAnimationExport)

        self.timeLayerManager.clearTimeLayerList()

    def initQGISConnections(self):
        """Initialize QGIS iface and layer registry connections """
        self.iface.projectRead.connect(self.readSettings)
        self.iface.newProjectCreated.connect(self.restoreDefaults)
        self.iface.newProjectCreated.connect(self.disableAnimationExport)
        # QgsProject.instance().writeMapLayer.connect(self.writeSettings)
        QgsProject.instance().writeProject.connect(self.writeSettings)
        # this signal is responsible for keeping the animation running
        self.iface.mapCanvas().mapCanvasRefreshed.connect(self.waitAfterRenderComplete)

        # establish connections to map registry
        if hasattr(QgsProject, "layerWillBeRemoved"):
            instance = QgsProject.instance()
        else:
            instance = QgsMapLayerRegistry.instance()

        instance.layerWillBeRemoved.connect(self.timeLayerManager.removeTimeLayer)
        instance.removeAll.connect(self.timeLayerManager.clearTimeLayerList)
        instance.removeAll.connect(self.disableAnimationExport)

    def initGuiConnections(self, test=False):
        """Initialize the GUI and its connections with everything"""
        self.guiControl.showOptions.connect(self.showOptionsDialog)
        self.guiControl.signalExportVideo.connect(self.exportVideo)
        self.guiControl.toggleTime.connect(self.toggleTimeManagement)
        self.guiControl.toggleArchaeology.connect(self.toggleArchaeology)
        self.guiControl.back.connect(self.stepBackward)
        self.guiControl.forward.connect(self.stepForward)
        self.guiControl.play.connect(self.toggleAnimation)

        self.guiControl.signalCurrentTimeUpdated.connect(self.updateTimePositionFromTextBox)
        self.guiControl.signalSliderTimeChanged.connect(self.updateTimePositionFromSliderPct)

        self.guiControl.signalTimeFrameType.connect(self.setTimeFrameType)
        self.guiControl.signalTimeFrameSize.connect(self.setTimeFrameSize)
        self.guiControl.signalSaveOptions.connect(self.saveOptions)

        self.guiControl.signalArchDigitsSpecified.connect(self.saveArchDigits)
        self.guiControl.signalArchCancelled.connect(self.setArchaeology)

        # create actions
        # F8 button press - show time manager settings
        if not test:  # Qt doesn't play well with Mock objects
            self.actionShowSettings = QAction(u"Show Time Manager Settings", self.iface.mainWindow())
            self.iface.registerMainWindowAction(self.actionShowSettings, "F8")
            self.guiControl.addActionShowSettings(self.actionShowSettings)
            self.actionShowSettings.triggered.connect(self.showOptionsDialog)

    def initLayerManagerConnections(self):
        """Establish connections to timeLayerManager"""
        self.timeLayerManager.timeRestrictionsRefreshed.connect(self.refreshGuiWithCurrentTime)
        self.timeLayerManager.projectTimeExtentsChanged.connect(self.refreshGuiTimeExtents)
        self.timeLayerManager.lastLayerRemoved.connect(self.disableAnimationExport)

    def restoreDefaults(self):
        """Restore plugin default settings"""
        self.granularity = conf.DEFAULT_GRANULARITY_IN_SECONDS
        self.animationActivated = False
        self.loopAnimation = False
        self.playBackwards = False
        self.animationFrameCounter = 0
        self.saveAnimation = False
        self.saveAnimationPath = os.path.expanduser('~')
        self.animationFrameLength = conf.DEFAULT_FRAME_LENGTH
        self.restoreTimeFrameType(conf.DEFAULT_FRAME_UNIT)
        self.guiControl.setTimeFrameSize(conf.DEFAULT_FRAME_SIZE)

    def setPropagateGuiChanges(self, val):
        self.propagateGuiChanges = val

    @log_exceptions
    def refreshGuiTimeExtents(self, timeExtents):
        """Update time extents showing in labels and represented by horizontalTimeSlider
        :param timeExtents: a tuple of start and end datetimes
        """
        self.setPropagateGuiChanges(False)
        if timeExtents[1] is not None:  # timeExtents[0] is set in different places, so only check timeExtents[1]
            startText = time_util.datetime_to_str(timeExtents[0], time_util.DEFAULT_FORMAT)
            endText = time_util.datetime_to_str(timeExtents[1], time_util.DEFAULT_FORMAT)
            self.guiControl.dock.labelStartTime.setText(startText)
            self.guiControl.dock.labelEndTime.setText(endText)

            timeLength = time_util.datetime_to_epoch(timeExtents[1]) - time_util.datetime_to_epoch(timeExtents[0])

            if timeLength > MAX_TIME_LENGTH_SECONDS_SLIDER:
                new_granularity = int(math.ceil(1.0 * timeLength / MAX_TIME_LENGTH_SECONDS_SLIDER))
                self.setGranularitySeconds(new_granularity)
                # trick because timeLength must fit in an integer
                # since it interfaces with a C++ class
                newTimeLength = int(math.ceil(1.0 * timeLength / new_granularity))
                timeLength = newTimeLength

            else:
                self.setGranularitySeconds(conf.DEFAULT_GRANULARITY_IN_SECONDS)

            self.guiControl.dock.horizontalTimeSlider.setMinimum(0)
            self.guiControl.dock.horizontalTimeSlider.setMaximum(timeLength)

        else:  # set to default values
            self.setGranularitySeconds(conf.DEFAULT_GRANULARITY_IN_SECONDS)
            self.guiControl.dock.labelStartTime.setText('not set')
            self.guiControl.dock.labelEndTime.setText('not set')
            self.guiControl.dock.horizontalTimeSlider.setMinimum(conf.MIN_TIMESLIDER_DEFAULT)
            self.guiControl.dock.horizontalTimeSlider.setMaximum(conf.MAX_TIMESLIDER_DEFAULT)

        self.setPropagateGuiChanges(True)

    @log_exceptions
    def refreshGuiWithCurrentTime(self, currentTimePosition, sender=None):
        """
        Update the gui when time has changed by refreshing/repainting the layers
        and changing the time showing in dateTimeEditCurrentTime and horizontalTimeSlider

        Setting the gui elements should not fire the event for
        timeChanged, since they were changed to be in sync with the rest of the system on
        purpose, no need to sync the system again
        """
        self.setPropagateGuiChanges(False)
        timeExtent = self.getTimeLayerManager().getProjectTimeExtents()
        if currentTimePosition is None or timeExtent[0] is None or timeExtent[1] is None:
            self.setPropagateGuiChanges(True)
            return

        time_util.updateUi(self.guiControl.getTimeWidget(), currentTimePosition)
        timeval = time_util.datetime_to_epoch(currentTimePosition)
        timeExtents = self.getTimeLayerManager().getProjectTimeExtents()
        try:
            pct = (timeval - time_util.datetime_to_epoch(timeExtents[0])) * 1.0 / (time_util.datetime_to_epoch(
                timeExtents[1]) - time_util.datetime_to_epoch(timeExtents[0]))
            sliderVal = self.guiControl.dock.horizontalTimeSlider.minimum() + int(pct * (
                self.guiControl.dock.horizontalTimeSlider.maximum() -
                self.guiControl.dock.horizontalTimeSlider.minimum()))
            self.guiControl.dock.horizontalTimeSlider.setValue(sliderVal)
            self.guiControl.repaintRasters()
            self.guiControl.repaintJoined()
            self.guiControl.repaintVectors()
            self.guiControl.refreshMapCanvas()
            self.updateLegendCount()
        except Exception as e:
            error(e)
        finally:
            self.setPropagateGuiChanges(True)

    def updateLegendCount(self):
        """
        This method is actually a hack/fix for http://hub.qgis.org/issues/14756.
        Untill this is fixed via some signal/action in the legend(tree), below is needed.
        :return:
        """
        root = QgsProject.instance().layerTreeRoot()
        model = self.iface.layerTreeView().model()
        for l in self.getTimeLayerManager().getActiveVectors():
            model.refreshLayerLegend(root.findLayer(l.getLayer().id()))

    def disableAnimationExport(self):
        """Disable the animation export button"""
        self.guiControl.disableAnimationExport()

    def getTimeLayerManager(self):
        return self.timeLayerManager

    def getGui(self):
        return self.guiControl

    def showMessage(self, msg, msg_type="Info"):
        if self.showQMessagesEnabled():
            QMessageBox.information(self.iface.mainWindow(), msg_type, msg)

    def showQMessagesEnabled(self):
        return True

    def setAnimationOptions(self, length, playBackwards, loopAnimation):
        """Set length and play direction of the animation"""
        self.animationFrameLength = length
        self.playBackwards = playBackwards
        self.loopAnimation = loopAnimation

    def showOptionsDialog(self):
        """Show options dialog"""
        self.stopAnimation()
        self.guiControl.showOptionsDialog(self.timeLayerManager.getTimeLayerList(),
                                          self.animationFrameLength, self.playBackwards,
                                          self.loopAnimation)

    def exportFramesAtPath(self, path):
        self.saveAnimationPath = path
        if self.saveAnimationPath:
            self.saveAnimation = True
            self.loopAnimation = False  # on export looping has to be deactivated
            self.toggleAnimation()
            self.showMessage(
                QCoreApplication.translate(
                    'TimeManager',
                    'Image sequence from current position onwards is being saved to {}.\n\nPlease wait until the process is finished.'
                ).format(self.saveAnimationPath)
            )

    def exportVideo(self, path, delay_millis, exportGif, exportVideo=False, clearFrames=False):
        """Export video frames and optionally creates an animated gif or video from them"""
        if clearFrames:
            animate.clear_frames(path)
            animate.clear_frames(path, '*PNGw')
            animate.clear_frames(path, '*pgw')  # from 2.18, QGIS creates .pgw files
        self.exportFramesAtPath(path)
        if exportGif:
            self.showMessage(QCoreApplication.translate('TimeManager', "Creating animated gif at {}").format(self.saveAnimationPath))
            animate.make_animation(path, delay_millis)
        if exportVideo:
            self.showMessage(QCoreApplication.translate('TimeManager', "Creating video at {}").format(self.saveAnimationPath))
            animate.make_video(path, self.exportNameDigits)

    def toggleAnimation(self):
        """Toggle animation on/off"""
        if self.animationActivated:
            self.animationActivated = False
        else:
            self.animationActivated = True

        self.animationFrameCounter = 0
        expectedNumberOfFrames = self.timeLayerManager.getFrameCount()
        if expectedNumberOfFrames == 0:  # will be zero if no layer is time managed
            self.animationActivated = False
            if len(self.getTimeLayerManager().getTimeLayerList()) > 0:
                error(QCoreApplication.translate('TimeManager', "Have layers, but animation not possible"))
        self.exportNameDigits = len(str(expectedNumberOfFrames)) + 1  # add 1 to deal with cornercases (hacky fix)
        self.startAnimation()  # if animation is activated, it will start

    def startAnimation(self):
        """Kick-start the animation, afterwards the animation will run based on signal chains"""
        self.waitAfterRenderComplete()

    def waitAfterRenderComplete(self, painter=None):
        """When the map canvas signals renderComplete, wait defined millisec until next animation step"""
        if self.saveAnimation:  # make animation/export run as fast as possible
            self.playAnimation(painter)
        else:
            QTimer.singleShot(self.animationFrameLength, self.playAnimation)

    def generateFrameFilename(self, path, FrameIndex, currentTime):
        """Generate the file name for a given frame"""
        return os.path.join(path, "{}{}.{}".format(
            conf.FRAME_FILENAME_PREFIX,
            str(FrameIndex).zfill(self.exportNameDigits),
            conf.FRAME_EXTENSION
        ))

    def exportEmpty(self):
        return self.guiControl.exportEmpty

    def playAnimation(self, painter=None):
        """Play animation in map window"""
        if not self.animationActivated:
            return
        # check if the end of the project time extents has been reached
        projectTimeExtents = self.timeLayerManager.getProjectTimeExtents()
        currentTime = self.timeLayerManager.getCurrentTimePosition()

        haveVisibleFeatures = self.timeLayerManager.haveVisibleFeatures()
        if self.saveAnimation and (self.exportEmpty() or haveVisibleFeatures):
            fileName = self.generateFrameFilename(self.saveAnimationPath, self.animationFrameCounter, currentTime)
            # try accessing the file or fail with informative exception
            try:
                open(fileName, 'a').close()
            except Exception:
                # TODO: Friendlier exception, qgsbox etc
                raise Exception("Cannot write to file {}".format(fileName))
            self.saveCurrentMap(fileName)
            self.animationFrameCounter += 1

        resetToEnd = False
        canMakeNextStep = currentTime < projectTimeExtents[1]
        stepFunction = self.stepForward

        if self.playBackwards:
            canMakeNextStep = currentTime > projectTimeExtents[0]
            resetToEnd = True
            stepFunction = self.stepBackward

        if canMakeNextStep:
            stepFunction()
        else:
            if self.loopAnimation:
                self.resetAnimation(toEnd=resetToEnd)
            else:
                self.stopAnimation()

    def saveCurrentMap(self, fileName):
        """Save the content of the map canvas to file"""
        self.iface.mapCanvas().saveAsImage(fileName)

    def stopAnimation(self):
        """Stop the animation in case it's running"""
        if self.saveAnimation:
            self.showMessage(QCoreApplication.translate('TimeManager', 'The export finished successfully!'))
            self.saveAnimation = False
        self.animationActivated = False
        self.guiControl.turnPlayButtonOff()

    def resetAnimation(self, toEnd=False):
        """Reset the animation to start over from the beginning"""
        projectTimeExtents = self.timeLayerManager.getProjectTimeExtents()
        if not toEnd:
            self.timeLayerManager.setCurrentTimePosition(projectTimeExtents[0])
        else:
            self.timeLayerManager.setCurrentTimePosition(projectTimeExtents[1])

    def toggleTimeManagement(self):
        """Toggle time management on/off"""
        self.stopAnimation()
        self.timeLayerManager.toggleTimeManagement()

    def toggleArchaeology(self):
        """Toggle archaeology mode on/off"""
        if time_util.is_archaelogical():
            self.setArchaeology(False)
        else:
            self.guiControl.showArchOptions()

    def saveArchDigits(self, digits):
        self.setArchaeology(True)
        time_util.setArchDigits(digits)

    def setArchaeology(self, enabled=0):
        if enabled == 0:
            if [x for x in self.getTimeLayerManager().layers() if time_util.is_archaeological_layer(x)]:
                QMessageBox.information(self.iface.mainWindow(),
                                        QCoreApplication.translate('TimeManager', 'Error'),
                                        QCoreApplication.translate('TimeManager', "Already have archaeological layers in the project."
                                        "Please delete them to switch to normal mode"))
                self.guiControl.setArchaeologyPressed(True)
                return
            time_util.setCurrentMode(time_util.NORMAL_MODE)
            self.guiControl.setWindowTitle("Time Manager")
            self.guiControl.setArchaeologyPressed(False)
            self.guiControl.disableArchaeologyTextBox()

        else:
            if [x for x in self.getTimeLayerManager().layers() if not time_util.is_archaeological_layer(x)]:
                QMessageBox.information(self.iface.mainWindow(),
                                        QCoreApplication.translate('TimeManager', 'Error'),
                                        QCoreApplication.translate('TimeManager', "Already have non archaeological layers in the project."
                                        "Please delete them to switch to archaeological mode"))
                self.guiControl.setArchaeologyPressed(False)
                return
            time_util.setCurrentMode(time_util.ARCHAELOGY_MODE)
            self.guiControl.setWindowTitle(QCoreApplication.translate('TimeManager', "Time Manager Archaeology Mode"))
            self.guiControl.setArchaeologyPressed(True)
            ctx = self.guiControl.dock.objectName()
            try:
                self.guiControl.setTimeFrameType(QCoreApplication.translate(ctx, 'years'))
            except Exception:
                error(
                    QCoreApplication.translate(
                        'TimeManager',
                        "should only happen during testing"
                    )
                )
            self.guiControl.enableArchaeologyTextBox()
            self.showMessage(
                QCoreApplication.translate(
                    'TimeManager',
                    "Archaelogy mode enabled. Expecting data of the form {0} BC or {0} AD."
                    " Disable to work with regular datetimes from year 1 onwards"
                ).format(
                    "Y" * time_util.getArchDigits()
                )
            )

    def stepBackward(self):
        """Move one step backward in time"""
        self.timeLayerManager.stepBackward()

    def stepForward(self):
        """Move one step forward in time"""
        self.timeLayerManager.stepForward()

    def setTimeFrameType(self, timeFrameType):
        """Set timeLayerManager's time frame type from a potentially foreign languange string"""

        ctx = self.guiControl.dock.objectName()
        for frame_type in ['microseconds', 'milliseconds', 'seconds', 'minutes', 'hours', 'years',
                           'months', 'weeks', 'days']:
            if self.isEqualToUntranslatedString(timeFrameType, frame_type, context=ctx):
                self.timeLayerManager.setTimeFrameType(frame_type)
                self.guiControl.refreshMapCanvas('setTimeFrameType')
                if self.isEqualToUntranslatedString(timeFrameType, "microseconds", ctx) or \
                        self.isEqualToUntranslatedString(timeFrameType, "milliseconds", ctx):
                    QMessageBox.information(
                        self.iface.mainWindow(),
                        QCoreApplication.translate('TimeManager', 'Information'),
                        QCoreApplication.translate(
                            'TimeManager',
                            "Microsecond and millisecond support works best when the input data "
                            "contains millisecond information (ie, a decimal part)"
                        )
                    )

                return

        warn("Unrecognized time frame type : {}".format(timeFrameType))

    def setTimeFrameSize(self, timeFrameSize):
        """Set timeLayerManager's time frame size"""
        self.timeLayerManager.setTimeFrameSize(timeFrameSize)
        self.guiControl.refreshMapCanvas('setTimeFrameSize')

    def updateTimePositionFromSliderPct(self, pct):
        """See the percentage the slider is at and determine the datetime"""
        if not self.propagateGuiChanges:
            return
        timeExtents = self.getTimeLayerManager().getProjectTimeExtents()
        try:
            realEpochTime = int(pct * (time_util.datetime_to_epoch(timeExtents[1]) - time_util.datetime_to_epoch(
                timeExtents[0])) + time_util.datetime_to_epoch(timeExtents[0]))
        except Exception:
            # extents are not set yet?
            return

        self.getTimeLayerManager().setCurrentTimePosition(time_util.epoch_to_datetime(realEpochTime))

    @log_exceptions
    def updateTimePositionFromTextBox(self, date):
        if not self.propagateGuiChanges:
            return
        if time_util.is_archaelogical():
            bcdate = bcdate_util.BCDate.from_str(date, strict_zeros=False)
            bcdate.setDigits(bcdate_util.getGlobalDigitSetting())
            self.getTimeLayerManager().setCurrentTimePosition(bcdate)
        else:
            self.getTimeLayerManager().setCurrentTimePosition(time_util.QDateTime_to_datetime(date))

    def restoreTimeFrameType(self, text):
        try:
            self.guiControl.setTimeFrameType(QCoreApplication.translate(
                self.guiControl.dock.objectName(), text))
        except Exception:  # tests don't work with mocked QCoreApplications unfortunately
            pass

    def writeSettings(self):
        """Write all relevant settings to the project file XML """
        if not self.getTimeLayerManager().isEnabled():
            return
        (timeLayerManagerSettings, timeLayerList) = self.getTimeLayerManager().getSaveString()

        if timeLayerManagerSettings is not None:
            settings = {'animationFrameLength': self.animationFrameLength,
                        'playBackwards': self.playBackwards,
                        'loopAnimation': self.loopAnimation,
                        'timeLayerManager': timeLayerManagerSettings,
                        'timeLayerList': timeLayerList,
                        'currentMapTimePosition':
                        time_util.datetime_to_str(
                            self.getTimeLayerManager().getCurrentTimePosition(),
                            time_util.DEFAULT_FORMAT
                        ),
                        'timeFrameType': self.getTimeLayerManager().getTimeFrameType(),
                        'timeFrameSize': self.getTimeLayerManager().getTimeFrameSize(),
                        'active': self.getTimeLayerManager().isEnabled(),
                        'mode': int(time_util.is_archaelogical()),
                        'digits': time_util.getArchDigits(),
                        'labelFormat': self.guiControl.getLabelFormat(),
                        'labelFont': self.guiControl.getLabelFont(),
                        'labelSize': self.guiControl.getLabelSize(),
                        'labelColor': self.guiControl.getLabelColor(),
                        'labelBgColor': self.guiControl.getLabelBgColor(),
                        'labelPlacement': self.guiControl.getLabelPlacement()}

            TimeManagerProjectHandler.writeSettings(settings)

    METASETTINGS = OrderedDict()
    METASETTINGS['mode'] = int
    METASETTINGS['digits'] = int
    METASETTINGS['animationFrameLength'] = int
    METASETTINGS['playBackwards'] = int
    METASETTINGS['loopAnimation'] = int
    METASETTINGS['timeLayerManager'] = str
    METASETTINGS['timeLayerList'] = list
    METASETTINGS['currentMapTimePosition'] = str  # can't store datetime in XML
    METASETTINGS['timeFrameType'] = str
    METASETTINGS['timeFrameSize'] = int
    METASETTINGS['active'] = int
    METASETTINGS['labelFormat'] = str
    METASETTINGS['labelFont'] = str
    METASETTINGS['labelSize'] = int
    METASETTINGS['labelColor'] = str
    METASETTINGS['labelBgColor'] = str
    METASETTINGS['labelPlacement'] = str

    def readSettings(self):
        """Load and restore settings from project file"""
        settings = TimeManagerProjectHandler.readSettings(self.METASETTINGS)
        restore_functions = {
            'mode': (self.setArchaeology, 0),
            'digits': (time_util.setArchDigits, conf.DEFAULT_DIGITS),
            'currentMapTimePosition': (self.restoreTimePositionFromSettings, None),
            'animationFrameLength': (self.setAnimationFrameLength, conf.DEFAULT_FRAME_LENGTH),
            'playBackwards': (self.setPlayBackwards, 0),
            'loopAnimation': (self.setLoopAnimation, 0),
            'timeLayerManager': (self.restoreSettingTimeLayerManager, None),
            'timeLayerList': (self.restoreTimeLayers, None),
            'timeFrameType': (self.restoreTimeFrameType, conf.DEFAULT_FRAME_UNIT),
            'timeFrameSize': (self.guiControl.setTimeFrameSize, conf.DEFAULT_FRAME_SIZE),
            'active': (self.setActive, 0),
            'labelFormat': (self.guiControl.setLabelFormat, time_util.DEFAULT_FORMAT),
            'labelFont': (self.guiControl.setLabelFont, time_util.DEFAULT_LABEL_FONT),
            'labelSize': (self.guiControl.setLabelSize, time_util.DEFAULT_LABEL_SIZE),
            'labelColor': (self.guiControl.setLabelColor, time_util.DEFAULT_LABEL_COLOR),
            'labelBgColor': (self.guiControl.setLabelBgColor, time_util.DEFAULT_LABEL_BGCOLOR),
            'labelPlacement': (self.guiControl.setLabelPlacement, time_util.DEFAULT_LABEL_PLACEMENT),
        }

        for setting_name in list(self.METASETTINGS.keys()):
            if setting_name in restore_functions:
                restore_function, default_value = restore_functions[setting_name]
                if setting_name not in settings:
                    setting_value = default_value
                else:
                    setting_value = settings[setting_name]
                restore_function(setting_value)

    def setAnimationFrameLength(self, value):
        self.animationFrameLength = value

    def setPlayBackwards(self, value):
        self.playBackwards = value

    def setLoopAnimation(self, value):
        self.loopAnimation = value

    def restoreTimePositionFromSettings(self, value):
        """Restore the time position from settings"""
        if value:
            dt = time_util.str_to_datetime(value, time_util.DEFAULT_FORMAT)  # this also works for integer values
            self.getTimeLayerManager().setCurrentTimePosition(dt)

    def restoreSettingTimeLayerManager(self, value):
        """Restore timeLayerManager"""
        self.timeLayerManager.restoreFromSaveString(value)

    def restoreTimeLayers(self, layerInfos):
        """Restore all time layers"""
        if layerInfos:
            if len(layerInfos) > 0:
                self.guiControl.enableAnimationExport()
            for l in layerInfos:  # for every layer entry
                try:
                    settings = layer_settings.getSettingsFromSaveStr(l)
                    if settings.layer is None:
                        error_msg = QCoreApplication.translate('TimeManager', "Could not restore layer with id {} from saved project line {}").format(
                            settings.layerId, l
                        )
                        error(error_msg)
                        self.showMessage(error_msg)
                        continue

                    timeLayer = TimeLayerFactory.get_timelayer_class_from_settings(settings)(
                        settings, iface=self.iface)

                except Exception as e:
                    layerId = "unknown"
                    try:
                        layerId = settings.layerId
                    except Exception:
                        pass
                    error_msg = QCoreApplication.translate('TimeManager', "An error occured while trying to restore layer {} to TimeManager. {}").format(
                        layerId, str(e)
                    )
                    error(error_msg + traceback.format_exc(e))
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
                self.setAnimationOptions(animationFrameLength, playBackwards, loopAnimation)
                self.guiControl.exportEmpty = not self.guiControl.optionsDialog.checkBoxDontExportEmpty.isChecked()
                self.guiControl.showLabel = self.guiControl.optionsDialog.checkBoxLabel.isChecked()
                self.guiControl.refreshMapCanvas('saveOptions')
                self.guiControl.dock.pushButtonExportVideo.setEnabled(True)
            except Exception:
                continue

            self.timeLayerManager.refreshTimeRestrictions()

    def createTimeLayerFromRow(self, row):
        """Create a TimeLayer from options set in the table row"""
        settings = layer_settings.getSettingsFromRow(self.guiControl.optionsDialog.tableWidget, row)
        try:
            timeLayer = TimeLayerFactory.get_timelayer_class_from_settings(settings)(settings, self.iface)
        except Exception as e:
            layer_name = "unknown"
            try:
                layer_name = settings.layer.name()
            except Exception:
                pass
            error_msg = QCoreApplication.translate(
                'TimeManager',
                "An error occurred while trying to add layer {0} to TimeManager. Cause: {1}"
            ).format(layer_name, str(e))
            #error(error_msg + traceback.format_exc(e))
            self.showMessage(error_msg)
            return None
        return timeLayer

    def setActive(self, value):
        """De/activate TimeManager"""
        if value:
            self.timeLayerManager.activateTimeManagement()
            self.guiControl.setActive(True)
        else:  # if the status indicates "off"
            self.timeLayerManager.deactivateTimeManagement()
            self.guiControl.setActive(False)
