
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5 import QtCore, QtWidgets
from FilmScanModule import Frame, Film, loadConfig, saveConfig, getAdjustableRects
import sys
from time import sleep
import cv2
import string
from Scan8mmFilm_ui import Ui_MainWindow
import os

try:
    from picamera2 import Picamera2
    from picamera2.previews.qt import QGlPicamera2
    from libcamera import Transform
    import piDeviceInterface as pidevi
    picamera2_present = True
except ImportError:                                                                                                                                                                                            
    picamera2_present = False
 

if picamera2_present:
    picam2 = Picamera2()
    preview_config = picam2.create_preview_configuration(main={"size": (1640, 1232)},transform=Transform(vflip=True,hflip=True))
    # preview_config = picam2.create_preview_configuration(main={"size": (3280, 2464)},transform=Transform(vflip=True,hflip=True))
    picam2.configure(preview_config)
    
    pidevi.initGpio()

class Window(QMainWindow, Ui_MainWindow):
    
    sigToCropTread = pyqtSignal(int)
    sigToScanTread = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        loadConfig()
        if picamera2_present:
            self.lblImage.hide() 
            # self.qpicamera2 = QGlPicamera2(picam2, width=3280, height=2464, keep_ar=True)
            self.qpicamera2 = QGlPicamera2(picam2, width=800, height=600, keep_ar=True)
            self.horizontalLayout_4.addWidget(self.qpicamera2)
        self.connectSignalsSlots()
        self.lblBlob.setMinimumWidth(Frame.getBlobWidth())
        self.adjustableRects = getAdjustableRects()
        for r in self.adjustableRects:
            self.comboBox.addItem(r.name)
        self.adjRectIx = 0
        self.comboBox.currentIndexChanged.connect(self.adjustableRectChanged)
        self.doLblImagePrep = False

        QTimer.singleShot(100, self.initScanner)

    def connectSignalsSlots(self):
        if picamera2_present:
            self.chkRewind.toggled.connect(self.rewindChanged)
        else:
            self.chkRewind.setDisabled(True)
        self.pbtnStart.clicked.connect(self.start)
        self.pbtnStop.clicked.connect(self.stop)
        self.pbtnUp.clicked.connect(self.up)
        self.pbtnDown.clicked.connect(self.down)
        self.pbtnLeft.clicked.connect(self.left)
        self.pbtnRight.clicked.connect(self.right)
        self.rbtnScan.toggled.connect(self.modeChanged)
        self.pbtnNext.clicked.connect(self.nnext)
        self.pbtnPrevious.clicked.connect(self.previous)
        self.pbtnRandom.clicked.connect(self.random)
        self.pbtnMakeFilm.clicked.connect(self.makeFilm)
        self.edlMinBlobArea.editingFinished.connect(self.minBlobAreaChanged)
        self.actionExit.triggered.connect(self.doClose)
        self.actionAbout.triggered.connect(self.about)
        if  picamera2_present:
            self.qpicamera2.done_signal.connect(self.capture_done)

        self.actionSelect_Film_Folder.triggered.connect(self.selectFilmFolder)
        self.actionSelect_Scan_Folder.triggered.connect(self.selectScanFolder)
        self.actionSelect_Crop_Folder.triggered.connect(self.selectCropFolder)
        self.actionClear_Scan_Folder.triggered.connect( self.clearScanFolder)
        self.actionClear_Crop_Folder.triggered.connect( self.clearCropFolder)

    # Menu actions --------------------------------------------------------------------------------------------

    def selectFilmFolder(self):
        dir = QtWidgets.QFileDialog.getExistingDirectory(caption="Select Film Folder", directory=os.path.commonpath([Film.filmFolder]))
        if dir:
            Film.filmFolder = os.path.abspath(dir)
        os.path.commonpath

    def selectScanFolder(self):
        dir = QtWidgets.QFileDialog.getExistingDirectory(caption="Select Scan Folder", directory=os.path.commonpath([Film.scanFolder]))
        if dir:
            Film.scanFolder = os.path.abspath(dir)
            self.initScanner()

    def selectCropFolder(self):
        dir = QtWidgets.QFileDialog.getExistingDirectory(caption="Select Crop Folder", directory=os.path.commonpath([Film.cropFolder]))
        if dir:
            Film.cropFolder = os.path.abspath(dir)
            self.updateInfoPanel()

    def clearScanFolder(self):
        button = QMessageBox.question(self, "Delete",  f"Delete all {Film.getScanCount()} .jpg files in {Film.scanFolder}?",QMessageBox.Yes|QMessageBox.No)
        if button == QMessageBox.Yes:
            Film.deleteFilesInFolder(Film.scanFolder)
            self.initScanner()
       
    def clearCropFolder(self):
        button = QMessageBox.question(self, "Delete", f"Delete all {Film.getCropCount()} .jpg files in {Film.cropFolder}?",QMessageBox.Yes|QMessageBox.No)
        if button == QMessageBox.Yes:
            Film.deleteFilesInFolder(Film.cropFolder)
            self.updateInfoPanel()

    def about(self):
        QMessageBox.about(
            self,
            "8mm Film Scanner App",
            "<p>Built with:</p>"
            "<p>- PyQt5</p>"
            "<p>- Qt Designer</p>"
            "<p>- Python 3.9</p>"
            "<p>- OpenCV</p>",
        )

    def doClose(self):
        self.close()

    # Button actions ---------------------------------------------------------------------------------------------------------------
    
    def modeChanged(self):
        self.prepLblImage()
        self.enableButtons()
        if self.rbtnScan.isChecked():
            self.showInfo("Mode Scan")
            if picamera2_present:            
                self.lblImage.hide()
                self.qpicamera2.show()
            if self.frame is None:
                self.frame = self.film.getFirstFrame()
            if self.frame is not None:
                self.showScan()
        else:
            self.showInfo("Mode Crop")
            self.lblImage.show()
            if picamera2_present:            
                self.qpicamera2.hide() 
            if self.frame is not None and self.frame.imagePathName is not None:
                self.refreshFrame()
            else:
                self.frame = self.film.getFirstFrame()
                self.showFrame()  

    def start(self):
        self.showInfo("start")
        self.prepLblImage()
        self.film.name = self.edlFilmName.text()
        self.film.curFrameNo = -1
        self.frame = self.film.getNextFrame()
        if self.rbtnScan.isChecked():
            if self.frame is not None:
                self.showScan()
            if picamera2_present:   
                self.motorStart()
                self.startScanFilm()
        else:
            self.startCropAll()
           
    def stop(self):
        self.showInfo("Stop")
        try:
            if self.rbtnScan.isChecked():
                if picamera2_present:
                    self.sigToScanTread.emit(0)
                    self.threadScan.running = False
                    sleep(0.2)
            else:
                self.sigToCropTread.emit(0)
                self.threadCrop.running = False
                sleep(0.2)
            self.enableButtons(busy=False)
        except:
            pass
    
    def nnext(self):
        self.showInfo("Next")
        if self.rbtnScan.isChecked():
            if picamera2_present: 
                self.enableButtons(busy=True)  
                self.motorStart()
                pidevi.stepCw(pidevi.step_count)
                pidevi.spoolStart()
                self.showBlob()
        else:
            self.frame = self.film.getNextFrame()
            self.showFrame()

    def previous(self):
        self.showInfo("Previous")
        if self.rbtnScan.isChecked():
            if picamera2_present: 
                self.enableButtons(busy=True)  
                self.motorStart()
                pidevi.stepCcw(pidevi.step_count)
                pidevi.spoolStart()
                self.showBlob()
        else:
            self.frame = self.film.getPreviousFrame()
            self.showFrame()
            
    def random(self):
        self.showInfo("Random")
        self.frame = self.film.getRandomFrame()
        self.showFrame()
                                         
    def makeFilm(self):
        self.showInfo("Make Film")  
        fileName = self.toValidFileName(self.edlFilmName.text())
        if len(fileName) == 0 :
            self.showInfo("Enter a valid filneme!")  
        else:
            self.enableButtons(busy=True)
            self.horizontalLayout_4.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
            self.doLblImagePrep = True
            self.lblImage.clear()
            self.lblScanFrame.setText("")
            self.film.name = fileName
            self.messageText = ""
            self.film.makeFilm(self.film.name, self.filmMessage, self.filmDone)
        
    def down(self):
        if self.rbtnScan.isChecked():
            if picamera2_present:
                self.enableButtons(busy=True)  
                self.motorStart()
                pidevi.stepCcw(2)
                pidevi.spoolStart()
                self.showBlob()
        else:
            if self.rbtnPosition.isChecked() :
                self.adjustableRects[self.adjRectIx].adjY(1)
            else:
                self.adjustableRects[self.adjRectIx].adjYSize(1)
            self.refreshFrame() 
            
    def up(self):
        if self.rbtnScan.isChecked():
            if picamera2_present:
                self.enableButtons(busy=True)  
                self.motorStart()
                pidevi.stepCw(2)  
                pidevi.spoolStart()
                self.showBlob()
        else:
            if self.rbtnPosition.isChecked() :
                self.adjustableRects[self.adjRectIx].adjY(-1)
            else:
                self.adjustableRects[self.adjRectIx].adjYSize(-1)
            self.refreshFrame()
            
    def left(self):
        if self.rbtnCrop.isChecked():
            if self.rbtnPosition.isChecked() :
                self.adjustableRects[self.adjRectIx].adjX(-1)
            else:
                self.adjustableRects[self.adjRectIx].adjXSize(-1)
            self.refreshFrame()
            
    def right(self):
        if self.rbtnCrop.isChecked():
            if self.rbtnPosition.isChecked() :
                self.adjustableRects[self.adjRectIx].adjX(1)
            else:
                self.adjustableRects[self.adjRectIx].adjXSize(1)
            self.refreshFrame()

    def adjustableRectChanged(self, i):
        self.adjRectIx = i
        
    def minBlobAreaChanged(self):
        minArea = int(self.edlMinBlobArea.text())
        if minArea > 200 and minArea < 10000:
            Frame.BLOB_MIN_AREA = minArea
        
    def rewindChanged(self):
        if picamera2_present:
            if self.chkRewind.isChecked():
                pidevi.rewind()
            else:
                pidevi.spoolStop()
            
    # Process or timer actions ---------------------------------------------------------------------------------------------------------

    def motorTimeout(self) :
        self.motorTicks = self.motorTicks + 1 
        pidevi.spoolStart()
        if self.motorTicks > 3 :
            self.motorStop()
        
    def capture_done(self,job):
        image = picam2.wait(job)
        print("picture taken!")
        sleep(0.5)
        image = cv2.resize(image, (640, 480))
        self.frame = Frame(image=image)
        self.frame.calcCrop()
        self.lblBlob.setPixmap(self.frame.getBlob())
        self.updateInfoPanel()
        self.motorTicks = 0   
        if self.scanDone :
            self.enableButtons(busy=False)
            
    def scanProgress(self, info, i, frame ):
        self.lblScanInfo.setText(info)
        self.motorTicks = 0   
        if frame is not None:
            if self.lblImage.isVisible():
                self.lblImage.setPixmap(frame.getCropped())
            self.lblBlob.setPixmap(frame.getBlob())
            self.frame = frame

    def cropProgress(self, info, i, frame):
        self.lblCropInfo.setText(info)
        if frame is not None:
            if self.lblImage.isVisible():
                self.lblImage.setPixmap(frame.getCropped())
            self.lblBlob.setPixmap(frame.getBlob())
            self.frame = frame

    def cropStateChange(self, info, i):
        self.updateInfoPanel()        
        self.showInfo(info)
        self.enableButtons(busy=False)

    def scanStateChange(self, info, i):
        self.updateInfoPanel()
        self.showInfo(info)
        self.scanDone = True
        self.enableButtons(busy=False)
        self.motorStop()
            
    def filmMessage(self, s):
        self.messageText = self.messageText + "\n" + s
        self.lblImage.setText(self.messageText) 
            
    def filmDone(self):
        self.enableButtons(busy=False)
    
    # Shared GUI control methods ------------------------------------------------------------------------------------------------------------------------------

    def enableButtons(self, *, busy=False):
        idle = not busy
        pi = picamera2_present
        scan = self.rbtnScan.isChecked()
        crop = self.rbtnCrop.isChecked()
        frame = self.frame is not None # True if scan folder has frames

        self.pbtnStart.setEnabled(idle and (scan or frame))
        self.pbtnStop.setEnabled(busy)
        self.pbtnMakeFilm.setEnabled(idle and crop and frame)

        self.pbtnNext.setEnabled(idle and (pi or (crop and frame)))
        self.pbtnPrevious.setEnabled(idle and (pi or (crop and frame)))
        self.pbtnRandom.setEnabled(idle and crop and frame)
        
        self.pbtnUp.setEnabled(idle and (pi or (crop and frame)))
        self.pbtnDown.setEnabled(idle and (pi or (crop and frame)))
        self.pbtnLeft.setEnabled(idle and crop and frame)
        self.pbtnRight.setEnabled(idle and crop and frame)

        self.rbtnScan.setEnabled(idle and pi)
        self.rbtnCrop.setEnabled(idle)
        
        self.pbtnMakeFilm.setEnabled(idle and crop and frame)
        self.chkRewind.setEnabled(pi and crop)
        self.menuFile.setEnabled(idle)
        self.edlFilmName.setEnabled(idle)

        self.comboBox.setEnabled(idle and crop and frame)
        self.rbtnPosition.setEnabled(idle and crop and frame)
        self.rbtnSize.setEnabled(idle and crop and frame)

    # Shared GUI update methods ---------------------------------------------------------------------------------------------------------------------------     

    def initScanner(self):
        self.film = Film("")
        self.frame = None
        self.lblImage.clear()
        self.lblBlob.clear()
        if picamera2_present:
            self.timer = QTimer()
            self.timer.timeout.connect(self.motorTimeout)
            self.scanDone = True
            # Start in Scan mode
            if self.rbtnScan.isChecked():
                self.modeChanged() # was set - force action
            else:
                self.rbtnScan.setChecked(True)
        else:
            # Start in Crop Mode
            if self.rbtnCrop.isChecked():
                self.modeChanged() # was set - force action
            else:
                self.rbtnCrop.setChecked(True) 
        self.enableButtons(busy=False)


    def updateInfoPanel(self):
        self.lblCropInfo.setText(f"Cropped frame count {Film.getCropCount()}")
        self.edlMinBlobArea.setText(str(Frame.BLOB_MIN_AREA))
        if self.frame is not None:
            frame = self.frame
            self.lblScanInfo.setText(f"Frame {self.film.curFrameNo} of {self.film.scanFileCount}")
            if self.frame.imagePathName is None:
                self.lblScanFrame.setText(Film.scanFolder)
            else:
                self.lblScanFrame.setText(self.frame.imagePathName)       
            self.lblInfo1.setText(f"Frame W={Frame.rect.getXSize()} H={Frame.rect.getYSize()} cX={frame.cX} cY={frame.cY} ar={Frame.rect.getXSize()/Frame.rect.getYSize():.2f}")
            self.lblInfo2.setText(f"Blob area={frame.area} bs={frame.blobState} Wcut={frame.ownWhiteCutoff}")
        else:
            self.lblScanInfo.setText(f"Frame count = {self.film.scanFileCount}")
            self.lblScanFrame.setText(Film.scanFolder) 
            self.lblInfo1.setText("")
            self.lblInfo2.setText("")

    def refreshFrame(self):
        self.frame = Frame(self.frame.imagePathName)
        self.showFrame()
  
    def showFrame(self):
        if self.frame is not None:
            if self.rbtnScan.isChecked():
                self.showScan()
            else:
                self.showCrop() 
        self.updateInfoPanel()
        
    def showScan(self):
        if picamera2_present:  
            self.showBlob()
        else:
            self.prepLblImage()
            self.lblImage.setPixmap(self.frame.getQPixmap(self.scrollAreaWidgetContents) ) #self.lblImage.contentsRect()))
        self.lblBlob.update()
        
    def showCrop(self):
        self.prepLblImage()
        self.lblImage.setPixmap(self.frame.getCropOutline(self.scrollAreaWidgetContents) ) #self.lblImage.contentsRect()))
        self.lblBlob.setPixmap(self.frame.getBlob())
    
    def showInfo(self,text):
        self.statusbar.showMessage(text)

    def prepLblImage(self):
        if self.doLblImagePrep and self.horizontalLayout_4.SizeConstraint != QtWidgets.QLayout.SetMinimumSize :
            self.horizontalLayout_4.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
            self.lblImage.clear()
            elf.doLblImagePrep = False
 
    def showBlob(self): # ,"format": "RGB888"
        if picamera2_present:
            self.enableButtons(busy=True)
            capture_config = picam2.create_still_configuration(main={"format": "RGB888","size": (1640, 1232)},transform=Transform(vflip=True,hflip=True))
            # This causes a call to capture_done when done 
            picam2.switch_mode_and_capture_array(capture_config, "main", signal_function=self.qpicamera2.signal_done)

    # Shared device control ---------------------------------------------------------------------------------------------------------------------------------------
    
    def motorStart(self):
        if self.rbtnScan.isChecked():
            self.motorTicks = 0
            self.timer.start(2000)
            pidevi.startScanner()
            pidevi.spoolStart()

    def motorStop(self):
        pidevi.spoolStop()
        self.timer.stop()
         
    def startCropAll(self):
        self.enableButtons(busy=True)
        self.lblScanFrame.setText("")
        self.lblInfo1.setText("")
        self.lblInfo2.setText("")
        self.threadCrop = QThreadCrop(self.film)
        self.sigToCropTread.connect(self.threadCrop.on_source)
        self.sigToCropTread.emit(1) 
        self.threadCrop.sigProgress.connect(self.cropProgress)
        self.threadCrop.sigStateChange.connect(self.cropStateChange)
        self.threadCrop.start()

    def startScanFilm(self):
        self.scanDone = False
        self.enableButtons(busy=True)
        self.lblScanFrame.setText("")
        self.lblInfo1.setText("")
        self.lblInfo2.setText("")
        self.motorStart()
        self.threadScan = QThreadScan(self.film)
        self.sigToScanTread.connect(self.threadScan.on_source)
        self.sigToScanTread.emit(1) 
        self.threadScan.sigProgress.connect(self.scanProgress)
        self.threadScan.sigStateChange.connect(self.scanStateChange)
        self.threadScan.start()

    # Shared utility methods -----------------------------------------------------------------------------------------------
         
    def toValidFileName(self, s):
        valid_chars = "-_() %s%s" % (string.ascii_letters, string.digits)
        filename = ''.join(c for c in s if c in valid_chars)
        filename = filename.replace(' ','_') # I don't like spaces in filenames.
        return filename    

# Thread =============================================================================

class QThreadCrop(QtCore.QThread):
    sigProgress = pyqtSignal(str, int, Frame)
    sigStateChange = pyqtSignal(str, int)
    
    def __init__(self, film, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.film = film
        self.cmd = 1 # run
        
    def on_source(self, cmd):
        self.cmd = cmd
        
    def progress(self, frame) :
        cnt = self.film.curFrameNo
        self.sigProgress.emit(f"{cnt} frames cropped", cnt, frame)    
        return self.cmd
            
    def run(self):
        self.running = True

        try:
            self.film.cropAll(self.progress)
            sleep(1)    
        except Exception as err:
            self.sigStateChange.emit(str(err), -2)
            print("QThreadScan", err)
            
        self.sigStateChange.emit("Done", -1)
        self.running = False

# Thread =============================================================================

class QThreadScan(QtCore.QThread):
    sigProgress = pyqtSignal(str, int, Frame)
    sigStateChange = pyqtSignal(str, int)
    
    def __init__(self, film, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.film = film
        self.cmd = 1 # go
        self.midy = Frame.midy
        self.tolerance = 6
        self.frameNo = film.scanFileCount
        
    def on_source(self, cmd):
        self.cmd = cmd
        
    def progress(self, frame) :
        cnt = self.film.curFrameNo
        self.sigProgress.emit(f"{cnt} frames scanned", cnt, frame)    
        return self.cmd
            
    def run(self):
        self.running = True
        pidevi.startScanner()
        
        while self.cmd == 1 :
            try:
                pidevi.spoolStart()
                capture_config = picam2.create_still_configuration(main={"format": "RGB888","size": (1640, 1232)},transform=Transform(vflip=True,hflip=True))
                image = picam2.switch_mode_and_capture_array(capture_config, "main") #, signal_function=self.qpicamera2.signal_done)
                self.frame = Frame(image=image)
                blobState = self.frame.find_blob(Frame.BLOB_MIN_AREA)
                if blobState != 0 :
                    self.cmd = 0
                    break
                tolstep = 2
                
                if self.frame.cY > self.midy + self.tolerance:
                    pidevi.stepCw(tolstep)
                    sleep(.2)  

                if self.frame.cY < self.midy - self.tolerance:
                    pidevi.stepCcw(tolstep)
                    sleep(.2)  

                if (self.frame.cY <= self.midy + self.tolerance) and (self.frame.cY >= self.midy - self.tolerance):
                    imgname = Film.scanFolder + 'scan' + ' - ' + format(self.frameNo, '06') + '.jpg'              
                    request = picam2.capture_request()
                    request.save("main", imgname)
                    print("imgname", imgname)
                    #print(request.get_metadata()) # this is the metadata for this image
                    request.release()
                    # signal progress
                    self.sigProgress.emit(f"{self.frameNo} frames scanned", self.frameNo, self.frame)    
                    pidevi.stepCw(pidevi.step_count)
                    self.frameNo += 1

                sleep(0.1)  
                  
            except Exception as err:
                print("QThreadScan", err)
                self.sigStateChange.emit(str(err), -2)
            
        self.running = False
        self.sigStateChange.emit("Done", -1)

# =============================================================================

if __name__ == "__main__":
    try:
        
        app = QApplication(sys.argv) 
        win = Window()
        if  picamera2_present:
            picam2.start()
        win.show()
        sys.exit(app.exec())
    except:
        if  picamera2_present:
            pidevi.cleanup()
    saveConfig()
    sys.exit(0)
