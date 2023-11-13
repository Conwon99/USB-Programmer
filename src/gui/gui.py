# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gui.ui'
#
# Created by: PyQt5 UI code generator 5.15.7
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.setFixedSize(604, 480)
        Dialog.setAutoFillBackground(False)
        Dialog.setStyleSheet("")
        self.bootloader_result_2 = QtWidgets.QLabel(Dialog)
        self.bootloader_result_2.setGeometry(QtCore.QRect(350, 230, 111, 16))
        self.bootloader_result_2.setText("")
        self.bootloader_result_2.setObjectName("bootloader_result_2")
        self.browseButton = QtWidgets.QPushButton(Dialog)
        self.browseButton.setGeometry(QtCore.QRect(510, 120, 81, 51))
        self.browseButton.setObjectName("browseButton")
        self.label_65 = QtWidgets.QLabel(Dialog)
        self.label_65.setGeometry(QtCore.QRect(10, 100, 111, 16))
        self.label_65.setObjectName("label_65")
        self.programButton = QtWidgets.QPushButton(Dialog)
        self.programButton.setGeometry(QtCore.QRect(10, 180, 581, 41))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.programButton.setFont(font)
        self.programButton.setObjectName("programButton")
        self.log = QtWidgets.QTextBrowser(Dialog)
        self.log.setGeometry(QtCore.QRect(10, 260, 581, 211))
        self.log.setObjectName("log")
        self.label_69 = QtWidgets.QLabel(Dialog)
        self.label_69.setGeometry(QtCore.QRect(10, 240, 91, 16))
        self.label_69.setObjectName("label_69")
        self.label_66 = QtWidgets.QLabel(Dialog)
        self.label_66.setGeometry(QtCore.QRect(10, 70, 51, 16))
        self.label_66.setObjectName("label_66")
        self.com_port = QtWidgets.QLineEdit(Dialog)
        self.com_port.setEnabled(True)
        self.com_port.setGeometry(QtCore.QRect(70, 70, 61, 20))
        self.com_port.setReadOnly(True)
        self.com_port.setObjectName("com_port")
        self.label_64 = QtWidgets.QLabel(Dialog)
        self.label_64.setGeometry(QtCore.QRect(10, 30, 51, 16))
        self.label_64.setObjectName("label_64")
        self.label_67 = QtWidgets.QLabel(Dialog)
        self.label_67.setGeometry(QtCore.QRect(10, 50, 91, 16))
        self.label_67.setObjectName("label_67")
        self.firmware = QtWidgets.QLineEdit(Dialog)
        self.firmware.setEnabled(True)
        self.firmware.setGeometry(QtCore.QRect(70, 50, 61, 20))
        self.firmware.setReadOnly(True)
        self.firmware.setObjectName("firmware")
        self.device_name = QtWidgets.QLineEdit(Dialog)
        self.device_name.setEnabled(True)
        self.device_name.setGeometry(QtCore.QRect(70, 30, 61, 20))
        self.device_name.setReadOnly(True)
        self.device_name.setObjectName("device_name")
        self.line_2 = QtWidgets.QFrame(Dialog)
        self.line_2.setGeometry(QtCore.QRect(10, 90, 581, 16))
        self.line_2.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_2.setObjectName("line_2")
        self.file_selection = QtWidgets.QTextBrowser(Dialog)
        self.file_selection.setGeometry(QtCore.QRect(10, 120, 491, 51))
        self.file_selection.setObjectName("file_selection")
        self.line_3 = QtWidgets.QFrame(Dialog)
        self.line_3.setGeometry(QtCore.QRect(10, 20, 581, 16))
        self.line_3.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_3.setObjectName("line_3")
        self.line_4 = QtWidgets.QFrame(Dialog)
        self.line_4.setGeometry(QtCore.QRect(10, 230, 581, 16))
        self.line_4.setFrameShape(QtWidgets.QFrame.HLine)
        self.line_4.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line_4.setObjectName("line_4")
        self.label_68 = QtWidgets.QLabel(Dialog)
        self.label_68.setGeometry(QtCore.QRect(10, 10, 71, 16))
        self.label_68.setObjectName("label_68")

        self.programButton.clicked.connect(Dialog.program_clicked) # type: ignore
        self.browseButton.clicked.connect(Dialog.browse_clicked) # type: ignore

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.browseButton.setText(_translate("Dialog", "Browse"))
        self.label_65.setText(_translate("Dialog", "File Selection "))
        self.programButton.setText(_translate("Dialog", "Program Device"))
        self.label_69.setText(_translate("Dialog", "Log"))
        self.label_66.setText(_translate("Dialog", "COM"))
        self.label_64.setText(_translate("Dialog", "Device"))
        self.label_67.setText(_translate("Dialog", "Firmware"))
        self.label_68.setText(_translate("Dialog", "Device Status"))
