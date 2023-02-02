# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Workspaces\python\Scan8mmFilm\ui\Scan8mmFilm_ui.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(914, 694)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.gboxScanCrop = QtWidgets.QGroupBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.gboxScanCrop.sizePolicy().hasHeightForWidth())
        self.gboxScanCrop.setSizePolicy(sizePolicy)
        self.gboxScanCrop.setMinimumSize(QtCore.QSize(100, 109))
        self.gboxScanCrop.setObjectName("gboxScanCrop")
        self.rbtnCrop = QtWidgets.QRadioButton(self.gboxScanCrop)
        self.rbtnCrop.setGeometry(QtCore.QRect(30, 70, 95, 20))
        self.rbtnCrop.setObjectName("rbtnCrop")
        self.rbtnScan = QtWidgets.QRadioButton(self.gboxScanCrop)
        self.rbtnScan.setGeometry(QtCore.QRect(30, 30, 95, 20))
        self.rbtnScan.setChecked(True)
        self.rbtnScan.setObjectName("rbtnScan")
        self.verticalLayout_3.addWidget(self.gboxScanCrop)
        self.chkMotorOn = QtWidgets.QCheckBox(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chkMotorOn.sizePolicy().hasHeightForWidth())
        self.chkMotorOn.setSizePolicy(sizePolicy)
        self.chkMotorOn.setObjectName("chkMotorOn")
        self.verticalLayout_3.addWidget(self.chkMotorOn)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.pbtnStart = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnStart.setObjectName("pbtnStart")
        self.verticalLayout.addWidget(self.pbtnStart)
        self.pbtnStop = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnStop.setEnabled(True)
        self.pbtnStop.setObjectName("pbtnStop")
        self.verticalLayout.addWidget(self.pbtnStop)
        self.pbtnUp = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnUp.setObjectName("pbtnUp")
        self.verticalLayout.addWidget(self.pbtnUp)
        self.pbtnDown = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnDown.setObjectName("pbtnDown")
        self.verticalLayout.addWidget(self.pbtnDown)
        self.pbtnLeft = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnLeft.setObjectName("pbtnLeft")
        self.verticalLayout.addWidget(self.pbtnLeft)
        self.pbtnRight = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnRight.setObjectName("pbtnRight")
        self.verticalLayout.addWidget(self.pbtnRight)
        self.pbtnNext = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnNext.setObjectName("pbtnNext")
        self.verticalLayout.addWidget(self.pbtnNext)
        self.pbtnPrevious = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnPrevious.setObjectName("pbtnPrevious")
        self.verticalLayout.addWidget(self.pbtnPrevious)
        self.pbtnRandom = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnRandom.setObjectName("pbtnRandom")
        self.verticalLayout.addWidget(self.pbtnRandom)
        self.pbtnMakeFilm = QtWidgets.QPushButton(self.centralwidget)
        self.pbtnMakeFilm.setObjectName("pbtnMakeFilm")
        self.verticalLayout.addWidget(self.pbtnMakeFilm)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.verticalLayout_3.addLayout(self.verticalLayout)
        self.horizontalLayout_2.addLayout(self.verticalLayout_3)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.gridLayout.setObjectName("gridLayout")
        self.lblFrameNo = QtWidgets.QLabel(self.centralwidget)
        self.lblFrameNo.setText("")
        self.lblFrameNo.setObjectName("lblFrameNo")
        self.gridLayout.addWidget(self.lblFrameNo, 1, 1, 1, 1)
        self.lblScanFrame = QtWidgets.QLabel(self.centralwidget)
        self.lblScanFrame.setMinimumSize(QtCore.QSize(0, 22))
        self.lblScanFrame.setText("")
        self.lblScanFrame.setObjectName("lblScanFrame")
        self.gridLayout.addWidget(self.lblScanFrame, 1, 0, 1, 1)
        self.lblFrameCount = QtWidgets.QLabel(self.centralwidget)
        self.lblFrameCount.setText("")
        self.lblFrameCount.setObjectName("lblFrameCount")
        self.gridLayout.addWidget(self.lblFrameCount, 0, 1, 1, 1)
        self.lblInfo1 = QtWidgets.QLabel(self.centralwidget)
        self.lblInfo1.setText("")
        self.lblInfo1.setObjectName("lblInfo1")
        self.gridLayout.addWidget(self.lblInfo1, 0, 2, 1, 1)
        self.edlFilmName = QtWidgets.QLineEdit(self.centralwidget)
        self.edlFilmName.setFrame(False)
        self.edlFilmName.setObjectName("edlFilmName")
        self.gridLayout.addWidget(self.edlFilmName, 0, 0, 1, 1)
        self.lblInfo2 = QtWidgets.QLabel(self.centralwidget)
        self.lblInfo2.setText("")
        self.lblInfo2.setObjectName("lblInfo2")
        self.gridLayout.addWidget(self.lblInfo2, 1, 2, 1, 1)
        self.gridLayout.setColumnStretch(0, 2)
        self.gridLayout.setColumnStretch(1, 1)
        self.gridLayout.setColumnStretch(2, 1)
        self.verticalLayout_2.addLayout(self.gridLayout)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.lblBlob = QtWidgets.QLabel(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lblBlob.sizePolicy().hasHeightForWidth())
        self.lblBlob.setSizePolicy(sizePolicy)
        self.lblBlob.setMinimumSize(QtCore.QSize(100, 100))
        self.lblBlob.setText("")
        self.lblBlob.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.lblBlob.setObjectName("lblBlob")
        self.horizontalLayout_3.addWidget(self.lblBlob)
        self.line = QtWidgets.QFrame(self.centralwidget)
        self.line.setFrameShape(QtWidgets.QFrame.VLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.horizontalLayout_3.addWidget(self.line)
        self.lblImage = QtWidgets.QLabel(self.centralwidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lblImage.sizePolicy().hasHeightForWidth())
        self.lblImage.setSizePolicy(sizePolicy)
        self.lblImage.setMinimumSize(QtCore.QSize(200, 100))
        self.lblImage.setFrameShape(QtWidgets.QFrame.Panel)
        self.lblImage.setFrameShadow(QtWidgets.QFrame.Raised)
        self.lblImage.setText("")
        self.lblImage.setScaledContents(True)
        self.lblImage.setObjectName("lblImage")
        self.horizontalLayout_3.addWidget(self.lblImage)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_2.addLayout(self.verticalLayout_2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 914, 26))
        self.menubar.setObjectName("menubar")
        self.menuMain = QtWidgets.QMenu(self.menubar)
        self.menuMain.setObjectName("menuMain")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menubar.addAction(self.menuMain.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        MainWindow.setTabOrder(self.rbtnScan, self.rbtnCrop)
        MainWindow.setTabOrder(self.rbtnCrop, self.pbtnStart)
        MainWindow.setTabOrder(self.pbtnStart, self.pbtnStop)
        MainWindow.setTabOrder(self.pbtnStop, self.pbtnUp)
        MainWindow.setTabOrder(self.pbtnUp, self.pbtnDown)
        MainWindow.setTabOrder(self.pbtnDown, self.pbtnLeft)
        MainWindow.setTabOrder(self.pbtnLeft, self.pbtnRight)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "8mm Filmscanner"))
        self.gboxScanCrop.setTitle(_translate("MainWindow", "Operation mode"))
        self.rbtnCrop.setText(_translate("MainWindow", "Crop"))
        self.rbtnScan.setText(_translate("MainWindow", "Scan"))
        self.chkMotorOn.setText(_translate("MainWindow", "Motor On"))
        self.pbtnStart.setText(_translate("MainWindow", "Start"))
        self.pbtnStop.setText(_translate("MainWindow", "Stop"))
        self.pbtnUp.setText(_translate("MainWindow", "Up"))
        self.pbtnDown.setText(_translate("MainWindow", "Down"))
        self.pbtnLeft.setText(_translate("MainWindow", "Left"))
        self.pbtnRight.setText(_translate("MainWindow", "Right"))
        self.pbtnNext.setText(_translate("MainWindow", "Next"))
        self.pbtnPrevious.setText(_translate("MainWindow", "Previous"))
        self.pbtnRandom.setText(_translate("MainWindow", "Random"))
        self.pbtnMakeFilm.setText(_translate("MainWindow", "Make Film"))
        self.edlFilmName.setPlaceholderText(_translate("MainWindow", "<Enter film name>"))
        self.menuMain.setTitle(_translate("MainWindow", "Main"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())

