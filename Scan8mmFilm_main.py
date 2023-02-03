
from PyQt5.QtWidgets import (
    QApplication, QDialog, QMainWindow, QMessageBox,
    QGraphicsPixmapItem, QGraphicsScene
)
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtCore
from Scan8mmFilm_ui import Ui_MainWindow
from FilmScanModule import Frame, Film, loadConfig, saveConfig
import sys
from time import sleep
 
import cv2
import string
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
    # picam2.post_callback = post_callback
    preview_config = picam2.create_preview_configuration(main={"size": (1640, 1232)},transform=Transform(vflip=True,hflip=True))
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
            self.qpicamera2 = QGlPicamera2(picam2, width=800, height=600, keep_ar=False)
            self.horizontalLayout_3.addWidget(self.qpicamera2)
        self.connectSignalsSlots()
        self.film = Film("Slotshaven")
        self.frame = None
        # self.graphicsView.setSizeIncrement(QtCore.QSize(0, 0))
        # self.graphicsView.setFrameShadow(QtWidgets.QFrame.Raised)
        # self.graphicsView.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContentsOnFirstShow)
        # self.graphicsView.setAlignment(QtCore.Qt.AlignJustify|QtCore.Qt.AlignVCenter)
        self.lblFrameCount.setText(f"Number of frames = {self.film.max_pic_num}")
        self.lblFrameNo.setText("")
        self.lblBlob.setMinimumWidth(Frame.BLOB_W)
        

    def connectSignalsSlots(self):
        if picamera2_present:
            self.chkMotorOn.toggled.connect(self.motorModeChanged)
        else:
            self.chkMotorOn.setDisabled(True)
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
        # self.action_Exit.triggered.connect(self.close)
        # self.action_Find_Replace.triggered.connect(self.findAndReplace)
        # self.action_About.triggered.connect(self.about)
        if  picamera2_present:
            self.qpicamera2.done_signal.connect(self.capture_done)
        
    # def on_button_clicked():
    #    # button.setEnabled(False)
    #    cfg = picam2.create_still_configuration()
    #    picam2.switch_mode_and_capture_file(cfg, "test.jpg", signal_function=qpicamera2.signal_done)


    def capture_done(self,job):
        image = picam2.wait(job)
        # print("picture taken!", image)
        sleep(0.5)
        image = cv2.resize(image, (640, 480))
        self.frame = Frame(image=image)
        self.showCrop()

        # button.setEnabled(True)

    def on_info(self, info, i, frame = None ):
        self.lblFrameNo.setText(info)
        if frame is not None:
            self.lblImage.setPixmap(frame.getCropped())
            self.lblBlob.setPixmap(frame.getBlob())
            self.lblInfo1.setText(f"area={frame.area} edlWhiteCutoff={frame.ownWhiteCutoff}")
            self.lblInfo2.setText(f"cX={frame.cX} cY={frame.cY} bs={frame.blobState}")
    


    def start(self):
        self.showInfo("start")
        self.film.name = self.edlFilmName.text()
        self.film.curFrameNo = -1
        self.frame = self.film.getNextFrame()
        if self.rbtnScan.isChecked():
            if self.frame is not None:
                self.showScan()
            if picamera2_present:   
                self.startScanFilm()
        else:
            self.startCropAll()
            
    def motorModeChanged(self):
        if self.chkMotorOn.isChecked() :
            if self.rbtnScan.isChecked():
                # pidevi.setCamera()    
                pidevi.startScanner()
                pidevi.spoolStart()
            else:
                pidevi.rewind()
        else:
            pidevi.spoolStop()
            
    def down(self):
        if self.rbtnScan.isChecked():
            if picamera2_present:
                pidevi.stepCcw(2)
                pidevi.spoolStart()
                self.showBlob()
        else:
            Frame.ycal += 1
            self.refreshFrame() 
            
    def up(self):
        if self.rbtnScan.isChecked():
            if picamera2_present:
                pidevi.stepCw(2)  
                pidevi.spoolStart()
                self.showBlob()
        else:
            Frame.ycal -= 1
            self.refreshFrame()
            
    def left(self):
        if self.rbtnCrop.isChecked():
            Frame.xcal -= 1
            self.refreshFrame()
            
    def right(self):
        if self.rbtnCrop.isChecked():
            Frame.xcal += 1
            self.refreshFrame()
         
    def showBlob(self):
        capture_config = picam2.create_still_configuration({"format": "RGB888"},transform=Transform(vflip=True,hflip=True))
        image = picam2.switch_mode_and_capture_array(capture_config, "main", signal_function=self.qpicamera2.signal_done)
         
    def startCropAll(self):
        self.lblScanFrame.setText("")
        self.threadCrop = QThreadCrop(self.film)
        self.sigToCropTread.connect(self.threadCrop.on_source)
        self.sigToCropTread.emit(1) 
        self.threadCrop.sigProgress.connect(self.on_info)
        self.threadCrop.start()
        self.pbtnStart.setEnabled(False)

    def startScanFilm(self):
        self.lblScanFrame.setText("")
        self.threadScan = QThreadScan(self.film)
        self.sigToScanTread.connect(self.threadScan.on_source)
        self.sigToScanTread.emit(1) 
        self.threadScan.sigProgress.connect(self.on_info)
        self.threadScan.start()
        self.pbtnStart.setEnabled(False)
           
    def stop(self):
        self.showInfo("stop")
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
                
    def toValidFileName(self, s):
        valid_chars = "-_() %s%s" % (string.ascii_letters, string.digits)
        filename = ''.join(c for c in s if c in valid_chars)
        filename = filename.replace(' ','_') # I don't like spaces in filenames.
        return filename    
                    
    def makeFilm(self):
        self.showInfo("makeFilm")  
        fileName = self.toValidFileName(self.edlFilmName.text())
        if len(fileName) > 0 :
            self.lblScanFrame.setText("")
            self.film.name = fileName
            self.film.makeFilm(self.film.name)
        
    def modeChanged(self):
        if self.rbtnScan.isChecked():
            self.showInfo("Mode Scan")
            if picamera2_present:            
                self.lblImage.hide()
                self.qpicamera2.show()
            if self.frame is not None:
                self.showScan()
        else:
            self.showInfo("Mode Crop")
            self.lblImage.show()
            if picamera2_present:            
                self.qpicamera2.hide() 
            if self.frame is not None:
                self.showCrop()  

    def refreshFrame(self):
        self.frame = Frame(self.frame.imagePathName)
        self.showFrame()

    
    def nnext(self):
        self.showInfo("next")
        self.frame = self.film.getNextFrame()
        self.showFrame()

    def previous(self):
        self.showInfo("previous")
        self.frame = self.film.getPreviousFrame()
        self.showFrame()
        
    def random(self):
        self.showInfo("next")
        self.frame = self.film.getRandomFrame()
        self.showFrame()
        
    def showFrame(self):
        self.lblFrameCount.setText(f"Number of frames = {self.film.max_pic_num}")
        if self.frame is not None:
            self.lblFrameNo.setText(f"Current frame no = {self.film.curFrameNo}")
            self.lblScanFrame.setText(self.frame.imagePathName)       
            if self.rbtnScan.isChecked():
                self.showScan()
            else:
                self.showCrop() 
        
    def showScan(self):
        self.lblImage.setPixmap(self.frame.getQPixmap())
        # self.lblBlob.setPixmap(None)
        self.lblInfo1.setText("")
        self.lblInfo2.setText("")
        self.lblBlob.update()
        
    def showCrop(self):
        self.lblImage.setPixmap(self.frame.crop_pic())
        self.lblBlob.setPixmap(self.frame.getBlob())
        self.lblInfo1.setText(f"area={self.frame.area} edlWhiteCutoff={self.frame.ownWhiteCutoff}")
        self.lblInfo2.setText(f"cX={self.frame.cX} cY={self.frame.cY} bs={self.frame.blobState}")
    
    def showInfo(self,text):
        self.statusbar.showMessage(text)

    def about(self):
        QMessageBox.about(
            self,
            "Film Scanner App",
            "<p>Built with:</p>"
            "<p>- PyQt</p>"
            "<p>- Qt Designer</p>"
            "<p>- Python</p>",
        )

# =============================================================================
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
# =============================================================================
class QThreadScan(QtCore.QThread):
    sigProgress = pyqtSignal(str, int, Frame)
    
    def __init__(self, film, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.film = film
        self.cmd = 1 # go
        self.midy = Frame.midy
        self.tolerance = 6
        self.frameNo = film.max_pic_num
        
    def on_source(self, cmd):
        self.cmd = cmd
        
    def progress(self, frame) :
        cnt = self.film.curFrameNo
        self.sigProgress.emit(f"{cnt} frames scanned", cnt, frame)    
        return self.cmd
            
    def run(self):
        self.running = True
        step_count = 80
        pidevi.startScanner()
        
        while self.cmd == 1 :
            try:
                pidevi.spoolStart()
                capture_config = picam2.create_still_configuration({"format": "RGB888"},transform=Transform(vflip=True,hflip=True))
                image = picam2.switch_mode_and_capture_array(capture_config, "main") #, signal_function=self.qpicamera2.signal_done)
                self.frame = Frame(image=image)
                self.frame.find_blob(Frame.BLOB_MIN_AREA)
                tolstep = 2
                
                if self.frame.cY > self.midy + self.tolerance:
                    pidevi.stepCw(tolstep)
                    sleep(.2)  

                if self.frame.cY < self.midy - self.tolerance:
                    pidevi.stepCcw(tolstep)
                    sleep(.2)  

                if (self.frame.cY <= self.midy + self.tolerance) and (self.frame.cY >= self.midy - self.tolerance):
                    imgname = self.film.scan_dir + 'scan' + ' - ' + format(self.frameNo, '06') + '.jpg'              
                    request = picam2.capture_request()
                    request.save("main", imgname)
                    print("imgname", imgname)
                    #print(request.get_metadata()) # this is the metadata for this image
                    request.release()
                    # signal progress
                    self.sigProgress.emit(f"{self.frameNo} frames scanned", self.frameNo, self.frame)    
                    pidevi.stepCw(step_count)
                    self.frameNo += 1

                sleep(0.1)  
                  
            except Exception as err:
                print("QThreadScan", err)
                # self.sigProgress.emit(str(err), 0, None)
            
        self.running = False
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
