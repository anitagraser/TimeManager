# need to do that because importing from the ui file
# doesn't work out of the box on all OS
# namely, widgets that QGIS itself uses are somehow not available
# in the path at loading time and we need QgsColorButton as a color picker
# pyuic4 is available in Ubuntu in the package pyqt4-dev-tools
pyuic4 label_options.ui > ui/label_options.py
# then need to change the imports to use qgis.gui.QgsColorButton
# and (less important) adjust the # pragma no cover to exclude file from test coverage
