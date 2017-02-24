# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'label_options.ui'
#
# Created: Fri Feb 24 17:35:16 2017
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_labelOptions(object):
    def setupUi(self, labelOptions):
        labelOptions.setObjectName(_fromUtf8("labelOptions"))
        labelOptions.resize(239, 272)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(labelOptions.sizePolicy().hasHeightForWidth())
        labelOptions.setSizePolicy(sizePolicy)
        self.verticalLayout = QtGui.QVBoxLayout(labelOptions)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.label = QtGui.QLabel(labelOptions)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_4.addWidget(self.label)
        self.font = QtGui.QFontComboBox(labelOptions)
        self.font.setObjectName(_fromUtf8("font"))
        self.horizontalLayout_4.addWidget(self.font)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        self.label_2 = QtGui.QLabel(labelOptions)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_5.addWidget(self.label_2)
        self.fontsize = QtGui.QSpinBox(labelOptions)
        self.fontsize.setObjectName(_fromUtf8("fontsize"))
        self.horizontalLayout_5.addWidget(self.fontsize)
        self.verticalLayout_2.addLayout(self.horizontalLayout_5)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_3 = QtGui.QLabel(labelOptions)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_2.addWidget(self.label_3)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_6 = QtGui.QHBoxLayout()
        self.horizontalLayout_6.setObjectName(_fromUtf8("horizontalLayout_6"))
        self.radioButton_dt = QtGui.QRadioButton(labelOptions)
        self.radioButton_dt.setChecked(True)
        self.radioButton_dt.setObjectName(_fromUtf8("radioButton_dt"))
        self.horizontalLayout_6.addWidget(self.radioButton_dt)
        self.time_format = QtGui.QLineEdit(labelOptions)
        self.time_format.setObjectName(_fromUtf8("time_format"))
        self.horizontalLayout_6.addWidget(self.time_format)
        self.verticalLayout_2.addLayout(self.horizontalLayout_6)
        self.horizontalLayout_7 = QtGui.QHBoxLayout()
        self.horizontalLayout_7.setObjectName(_fromUtf8("horizontalLayout_7"))
        self.radioButton_beginning = QtGui.QRadioButton(labelOptions)
        self.radioButton_beginning.setObjectName(_fromUtf8("radioButton_beginning"))
        self.horizontalLayout_7.addWidget(self.radioButton_beginning)
        self.verticalLayout_2.addLayout(self.horizontalLayout_7)
        self.horizontalLayout_9 = QtGui.QHBoxLayout()
        self.horizontalLayout_9.setObjectName(_fromUtf8("horizontalLayout_9"))
        self.radioButton_epoch = QtGui.QRadioButton(labelOptions)
        self.radioButton_epoch.setObjectName(_fromUtf8("radioButton_epoch"))
        self.horizontalLayout_9.addWidget(self.radioButton_epoch)
        self.verticalLayout_2.addLayout(self.horizontalLayout_9)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label_5 = QtGui.QLabel(labelOptions)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.horizontalLayout.addWidget(self.label_5)
        self.placement = QtGui.QComboBox(labelOptions)
        self.placement.setObjectName(_fromUtf8("placement"))
        self.horizontalLayout.addWidget(self.placement)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label_6 = QtGui.QLabel(labelOptions)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.horizontalLayout_3.addWidget(self.label_6)
        self.text_color = gui.QgsColorButton(labelOptions)
        self.text_color.setObjectName(_fromUtf8("text_color"))
        self.horizontalLayout_3.addWidget(self.text_color)
        self.label_7 = QtGui.QLabel(labelOptions)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.horizontalLayout_3.addWidget(self.label_7)
        self.bg_color = gui.QgsColorButton(labelOptions)
        self.bg_color.setObjectName(_fromUtf8("bg_color"))
        self.horizontalLayout_3.addWidget(self.bg_color)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.verticalLayout.addLayout(self.verticalLayout_2)
        self.label_4 = QtGui.QLabel(labelOptions)
        self.label_4.setText(_fromUtf8(""))
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.verticalLayout.addWidget(self.label_4)
        self.buttonBox = QtGui.QDialogButtonBox(labelOptions)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(labelOptions)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), labelOptions.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), labelOptions.reject)
        QtCore.QMetaObject.connectSlotsByName(labelOptions)

    def retranslateUi(self, labelOptions):
        labelOptions.setWindowTitle(_translate("labelOptions", "Options", None))
        self.label.setText(_translate("labelOptions", "Font:", None))
        self.label_2.setText(_translate("labelOptions", "Font Size:", None))
        self.label_3.setText(_translate("labelOptions", "Time Format:", None))
        self.radioButton_dt.setText(_translate("labelOptions", "DateTime", None))
        self.radioButton_beginning.setText(_translate("labelOptions", "Seconds elapsed since beginning of data", None))
        self.radioButton_epoch.setText(_translate("labelOptions", "Seconds elapsed since 1970-01-01", None))
        self.label_5.setText(_translate("labelOptions", "Placement Direction:", None))
        self.label_6.setText(_translate("labelOptions", "Text Color:", None))
        self.label_7.setText(_translate("labelOptions", "Bg Color:", None))

from qgis import gui

