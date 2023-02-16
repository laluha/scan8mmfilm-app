
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
        self.film = Film("")
        self.frame = None
        self.lblScanInfo.setText("")
        self.lblBlob.setMinimumWidth(Frame.getBlobWidth())
        self.adjustableRects = getAdjustableRects()
        for r in self.adjustableRects:
            self.comboBox.addItem(r.name)
        self.adjRectIx = 0
        self.comboBox.currentIndexChanged.connect(self.adjustableRectChanged)
        if picamera2_present:
            self.timer = QTimer()
            self.timer.timeout.connect(self.motorTimeout)
            self.scanDone = True
            self.showBlob()
        else:
            self.rbtnCrop.setChecked(True)
            self.rbtnScan.setChecked(False)
            self.rbtnScan.setEnabled(False)
        self.showCropCount()

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
            self.lblScanInfo.setText(f"Frame count = {self.film.scanFileCount}")
            self.lblScanFrame.setText(Film.scanFolder) 

    def selectCropFolder(self):
        dir = QtWidgets.QFileDialog.getExistingDirectory(caption="Select Crop Folder", directory=os.path.commonpath([Film.cropFolder]))
        if dir:
            Film.cropFolder = os.path.abspath(dir)
            self.showCropCount()

    def clearScanFolder(self):
        button = QMessageBox.question(self, "Delete",  f"Delete all {Film.getScanCount()} .jpg files in {Film.scanFolder}?",QMessageBox.Yes|QMessageBox.No)
        if button == QMessageBox.Yes:
            Film.deleteFilesInFolder(Film.scanFolder)
            self.lblScanInfo.setText(f"Frame count = {self.film.scanFileCount}")
            self.lblScanFrame.setText(Film.scanFolder) 
       
    def clearCropFolder(self):
        button = QMessageBox.question(self, "Delete", f"Delete all {Film.getCropCount()} .jpg files in {Film.cropFolder}?",QMessageBox.Yes|QMessageBox.No)
        if button == QMessageBox.Yes:
            Film.deleteFilesInFolder(Film.cropFolder)
            self.showCropCount()

    def about(self):
        QMessageBox.about(
            self,
            "Film Scanner App",
            "<p>Built with:</p>"
            "<p>- PyQt</p>"
            "<p>- Qt Designer</p>"
            "<p>- Python</p>",
        )

    def doClose(self):
        self.close()

    # Button actions ---------------------------------------------------------------------------------------------------------------
    
    def modeChanged(self):
        self.prepLblImage()
        if self.rbtnScan.isChecked():
            self.showInfo("Mode Scan")
            if picamera2_present:            
                self.lblImage.hide()
                self.qpicamera2.show()
            if self.frame is not None:
                self.showScan()
        else:
            self.showInfo("Mode Crop")
            self.showCropCount()
            self.lblImage.show()
            if picamera2_present:            
                self.qpicamera2.hide() 
            if self.frame is not None:
                if self.frame.imagePathName is not None:
                    self.refreshFrame()
                else:
                    self.frame = self.film.getNextFrame()
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
                self.pbtnStart.setEnabled(True)
            else:
                self.sigToCropTread.emit(0)
                self.threadCrop.running = False
                sleep(0.2)
                self.pbtnStart.setEnabled(True)
        except:
            pass
    
    def nnext(self):
        self.showInfo("Next")
        if self.rbtnScan.isChecked():
            if picamera2_present: 
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
            self.pbtnMakeFilm.setEnabled(False)
            self.horizontalLayout_4.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
            self.lblImage.clear()
            self.lblScanFrame.setText("")
            self.film.name = fileName
            self.messageText = ""
            self.film.makeFilm(self.film.name, self.filmMessage, self.filmDone)
        
    def down(self):
        if self.rbtnScan.isChecked():
            if picamera2_present:
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
        self.showCropInfo(self.frame)
        self.motorTicks = 0   
        if self.scanDone :
            self.setEnabledScanButtons(True)
            
    def on_info(self, info, i, frame = None ):
        self.lblScanInfo.setText(info)
        self.motorTicks = 0
        if frame is not None:
            if self.lblImage.isVisible():
                self.lblImage.setPixmap(frame.getCropped())
            self.lblBlob.setPixmap(frame.getBlob())
            self.showCropInfo(frame)

    def cropStateChanged(self, info, i):
        self.showCropCount()

    def scanStateChange(self, info, i):
        self.lblScanInfo.setText(info)
        self.showInfo(info)
        self.scanFinished()
            
    def filmMessage(self, s):
        self.messageText = self.messageText + "\n" + s
        self.lblImage.setText(self.messageText) 
            
    def filmDone(self):
        self.pbtnMakeFilm.setEnabled(True)
    
    # Shared GUI control methods ------------------------------------------------------------------------------------------------------------------------------

    def setEnabledScanButtons(self, enab):
        self.pbtnStart.setEnabled(enab)
        self.pbtnUp.setEnabled(enab)
        self.pbtnDown.setEnabled(enab)
        self.pbtnNext.setEnabled(enab)
        self.pbtnPrevious.setEnabled(enab)
        
        self.pbtnStop.setEnabled(not enab)
        self.pbtnLeft.setEnabled(enab)
        self.pbtnRight.setEnabled(enab)
        self.rbtnScan.setEnabled(enab)
        self.rbtnCrop.setEnabled(enab)
        self.pbtnRandom.setEnabled(enab)
        self.pbtnMakeFilm.setEnabled(enab)
                
    def scanFinished(self):
        self.scanDone = True
        self.setEnabledScanButtons(True)
        self.motorStop()

    # Shared GUI update methods ---------------------------------------------------------------------------------------------------------------------------     

    def showCropCount(self):
        self.lblCropInfo = f"Cropped frame count {Film.getCropCount()}"

    def refreshFrame(self):
        self.frame = Frame(self.frame.imagePathName)
        self.showFrame()
  
    def showFrame(self):
        if self.frame is not None:
            self.lblScanInfo.setText(f"Frame {self.film.curFrameNo} of {self.film.scanFileCount}")
            self.lblScanFrame.setText(self.frame.imagePathName)       
            if self.rbtnScan.isChecked():
                self.showScan()
            else:
                self.showCrop() 
        else:
            self.lblScanInfo.setText(f"Frame count = {self.film.scanFileCount}")
            self.lblScanFrame.setText(Film.scanFolder) 
        
    def showScan(self):
        if picamera2_present:  
            self.showBlob()
        else:
            self.prepLblImage()
            self.lblImage.setPixmap(self.frame.getQPixmap(self.scrollArea) ) #self.lblImage.contentsRect()))
        # self.lblBlob.setPixmap(None)
        self.lblInfo1.setText("")
        self.lblInfo2.setText("")
        self.lblBlob.update()
        
    def showCrop(self):
        self.prepLblImage()
        self.lblImage.setPixmap(self.frame.getCropOutline(self.scrollArea) ) #self.lblImage.contentsRect()))
        self.lblBlob.setPixmap(self.frame.getBlob())
        self.showCropInfo(self.frame)
    
    def showInfo(self,text):
        self.statusbar.showMessage(text)

    def showCropInfo(self, frame):    
        self.lblInfo1.setText(f"Frame W={Frame.rect.getXSize()} H={Frame.rect.getYSize()} cX={frame.cX} cY={frame.cY} ar={Frame.rect.getXSize()/Frame.rect.getYSize():.2f}")
        self.lblInfo2.setText(f"Blob area={frame.area} bs={frame.blobState} Wcut={frame.ownWhiteCutoff}")
        self.edlMinBlobArea.setText(str(Frame.BLOB_MIN_AREA))

    def prepLblImage(self):
        if self.horizontalLayout_4.SizeConstraint != QtWidgets.QLayout.SetMinimumSize :
            self.horizontalLayout_4.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
            self.lblImage.clear()
            # self.lblImage.setText("")
            # self.lblImage.update()
 
    def showBlob(self): # ,"format": "RGB888"
        if picamera2_present:
            self.setEnabledScanButtons(False)
            capture_config = picam2.create_still_configuration(main={"format": "RGB888","size": (1640, 1232)},transform=Transform(vflip=True,hflip=True))
            #    image = 
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
        self.lblScanFrame.setText("")
        self.threadCrop = QThreadCrop(self.film)
        self.sigToCropTread.connect(self.threadCrop.on_source)
        self.sigToCropTread.emit(1) 
        self.threadCrop.sigProgress.connect(self.on_info)
        self.threadCrop.start()
        self.pbtnStart.setEnabled(False)

    def startScanFilm(self):
        self.scanDone = False
        self.pbtnStart.setEnabled(False)
        self.lblScanFrame.setText("")
        self.motorStart()
        self.threadScan = QThreadScan(self.film)
        self.sigToScanTread.connect(self.threadScan.on_source)
        self.sigToScanTread.emit(1) 
        self.threadScan.sigProgress.connect(self.on_info)
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
            # self.sigProgress.emit(str(err), 0, 1)
            print("QThreadScan", err)
            
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
