# -*- coding: utf-8 -*-
"""
Created on Sun Jan 15 18:45:07 2023

@author: B
"""
import os, fnmatch
import cv2
import random
import glob
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QProcess
import configparser

dbg = 0

inifile = os.path.join(os.path.dirname(__file__),'scanner.ini')
defaultBaseDir = "c:\\data\\film8\\" if os.sep == "\\" else "/home/pi/film8/"

def loadConfig():
    config = configparser.ConfigParser()
    if len(config.read(inifile)) == 1:
        Frame.rect.load(config)
        Frame.whiteBox.load(config)
        Frame.BLOB.load(config)
        Frame.BLOB_MIN_AREA = config['BLOB'].getint('blob_min_area')
        Film.filmFolder = config['PATHS']['filmfolder']
        Film.scanFolder = config['PATHS']['scanfolder']
        Film.cropFolder = config['PATHS']['cropfolder']
    else:
        saveConfig()
    
def saveConfig():
    config = configparser.ConfigParser()
    Frame.rect.save(config)
    Frame.whiteBox.save(config)
    Frame.BLOB.save(config)
    config['BLOB']['blob_min_area'] = str(Frame.BLOB_MIN_AREA) 
    if not config.has_section('PATHS'):
            config['PATHS'] = {}
    config['PATHS']['filmfolder'] = Film.filmFolder
    config['PATHS']['scanfolder'] = Film.scanFolder
    config['PATHS']['cropfolder'] = Film.cropFolder
    with open(inifile, 'w') as configfile:
       config.write(configfile)
       
def getAdjustableRects():
    return [Frame.rect, Frame.BLOB, Frame.whiteBox]

class Rect:
    def __init__(self, name, x1, y1, x2, y2):
        self.name = name
        self.X1 = x1
        self.Y1 = y1
        self.X2 = x2
        self.Y2 = y2
        
    def load(self, config):
        self.X1 = config[self.name].getint('x1')
        self.X2 = config[self.name].getint('x2')
        self.Y1 = config[self.name].getint('y1')
        self.Y2 = config[self.name].getint('y2')

    def save(self, config):
        if not config.has_section(self.name):
            config[self.name] = {}
        config[self.name]['x1'] = str(self.X1)
        config[self.name]['x2'] = str(self.X2)
        config[self.name]['y1'] = str(self.Y1) 
        config[self.name]['y2'] = str(self.Y2)

    def getXSize(self):
        return self.X2 - self.X1
    
    def getYSize(self):
        return self.Y2 - self.Y1
    
    def adjX(self, adj):
        if self.X1 + adj >= 0 :
            self.X1 = self.X1 + adj
            self.X2 = self.X2 + adj

    def adjY(self, adj):
        if self.Y1 + adj >= 0 :
            self.Y1 = self.Y1 + adj
            self.Y2 = self.Y2 + adj
        
    def adjXSize(self, adj):
        if self.X2 + adj > self.X1 :
            self.X2 = self.X2 + adj
    
    def adjYSize(self, adj):
        if self.Y2 + adj > self.Y1 :
            self.Y2 = self.Y2 + adj 

class Frame:
    ###
    # ysize = 534 #  needs to be adjusted to fit the picture
    # xsize = 764 
        
    # Top image edgeY = holeCenterY + imageBlackFrame thickness
    # ycal = 30 # 34 + 267 # 534/2 # 500 calibrate camera frame y position 0=center of blob 
    
    # Left image edgeX = holeCenterX + holeW/2: 377 + 288/2 = (BLOB.X1 + cX) *ScaleFactor + holeW/2
    # xcal = 144 
    ###
    
    midx = 64
    midy = 136 
    
    rect = Rect("FRAME", 144, 30, 144+764, 30+534)

    whiteBox = Rect("white_box", 544, 130, 544+12, 110+130)

    BLOB = Rect("BLOB", 90, 0, 240, 276)  
    BLOB_MIN_AREA = 4000 # 4000  
        
    ScaleFactor = 1640.0/640  
        
    whiteCutoff = 220
    
    def getBlobWidth():
        return Frame.BLOB.X2 - Frame.BLOB.X1
          
    def __init__(self, imagePathName=None,*,image=None):
        self.imagePathName = imagePathName
        if image is None and imagePathName is not None :
            self.imagePathName = imagePathName
            self.image = cv2.imread(imagePathName)
        elif image is not None :
            self.image = image
        
        # cX is important in order to crop the frame correctly 
        # (the film can move slightly from side to side in its track or the holes placement might be off)
        self.cX = Frame.midx 
        # cY is used to position a film frame at scan position
        self.cY = Frame.midy    
        
        self.blobState = 1
        self.ownWhiteCutoff = Frame.whiteCutoff
        
        
    def convert_cv_qt(self, cv_img, dest=None):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        if dest is None:
            return QtGui.QPixmap.fromImage(convert_to_Qt_format) 
        else:
            im = convert_to_Qt_format.scaled(dest.width(), dest.height(), QtCore.Qt.KeepAspectRatio)
            return QtGui.QPixmap.fromImage(im)
        
    def getQPixmap(self, dest=None):
        return self.convert_cv_qt(self.image, dest)
        
    def getCropped(self, dest=None):
        return self.convert_cv_qt(self.imageCropped, dest)
        
    def getBlob(self) :
        return self.convert_cv_qt(self.imageBlob)

    def calcCrop(self):
        self.blobState = self.find_blob(Frame.BLOB_MIN_AREA)
        
        x = int((self.cX + Frame.BLOB.X1) * Frame.ScaleFactor)+Frame.rect.X1
        y = int(self.cY * Frame.ScaleFactor)+Frame.rect.Y1 
        self.p1 = (x, y)
        self.p2 = (x+Frame.rect.getXSize(), y+Frame.rect.getYSize())
        
    def getCropOutline(self, dest=None):
        self.calcCrop()
        cv2.rectangle(self.image, self.p1, self.p2, (0, 255, 0), 10)
        wp1 = (round(Frame.whiteBox.X1 * Frame.ScaleFactor), round(Frame.whiteBox.Y1 * Frame.ScaleFactor))
        wp2 = (round(Frame.whiteBox.X2 * Frame.ScaleFactor), round(Frame.whiteBox.Y2 * Frame.ScaleFactor))
        cv2.rectangle(self.image, wp1, wp2, (60, 240, 240), 10)
        return self.convert_cv_qt(self.image, dest)
        
    def cropPic(self):
        self.calcCrop()
        self.imageCropped = self.image[self.p1[1]:self.p2[1], self.p1[0]:self.p2[0]]
     
    def getWhiteCutoff(self, imageSmall):
        img = imageSmall[Frame.whiteBox.Y1:Frame.whiteBox.Y2, Frame.whiteBox.X1:Frame.whiteBox.X2]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        planes = cv2.split(img)
        histSize = 256 #  [Establish the number of bins]
        histRange = (0, 256) # Set the range
        hist = cv2.calcHist(planes, [0], None, [histSize], histRange, accumulate=False)    
        okPct = (Frame.whiteBox.Y2-Frame.whiteBox.Y1)*(Frame.whiteBox.X2-Frame.whiteBox.X1)/100.0*5
        wco = 220
        for i in range(128,256) :
            if hist[i] > okPct :
                wco = i-8 #6
                break
        return wco        
      
    # area size has to be set to identify the sprocket hole blob
    # if the sprocket hole area is around 2500, then 2000 should be a safe choice
    # the area size will trigger the exit from the loop
    
    def find_blob(self, area_size):
        self.imageSmall = cv2.resize(self.image, (640, 480))
        # the image crop with the sprocket hole 
        img = self.imageSmall[Frame.BLOB.Y1:Frame.BLOB.Y2, Frame.BLOB.X1:Frame.BLOB.X2]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.ownWhiteCutoff = self.getWhiteCutoff(self.imageSmall)
        ret, self.imageBlob = cv2.threshold(img, self.ownWhiteCutoff, 255, 0) # 220 # 200,255,0
        contours, hierarchy = cv2.findContours(self.imageBlob, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        # RETR_LIST: retrieves all of the contours without establishing any hierarchical relationships.
        # CHAIN_APPROX_SIMPLE: compresses horizontal, vertical, and diagonal segments and leaves only 
        # their end points. For example, an up-right rectangular contour is encoded with 4 points.
        
        lenContours = len(contours)
        blobState = 1 
        oldcX = self.cX
        oldcY = self.cY
        self.area = area_size
        for l in range(lenContours):
            cnt = contours[l]
            area = cv2.contourArea(cnt)
            if dbg >= 1 :
                print((l, area))
            if area > area_size:
                blobState = 0 # blob found
                self.area = area
                # print("found")
                # print("area=", area)
                break
        if blobState == 0:      
            M = cv2.moments(cnt)
            #print(M)
            try:
                self.cX = int(M["m10"] / M["m00"])
                self.cY = int(M["m01"] / M["m00"])
                #blobDist = 225
                #if cY > blobDist : # distance between blobs
                #    print("cY=", cY)
                #    blobState = 2 # 2. blob found
                #    cY = cY - blobDist
            except ZeroDivisionError:
                if dbg >= 2: print("no center")
                blobState = 3 # no center
                self.cX = oldcX
                self.cY = oldcY # midy
        else :
            if dbg >= 2: print("no blob")
            blobState = 1
            self.cX = oldcX
            self.cY = oldcY        
        if dbg >= 2: print("cY=", self.cY, "oldcY=", oldcY, "blobState=", blobState)
        # if dbg >= 2:
            # ui = input("press return")   
        p1 = (0, self.cY) 
        p2 = (Frame.BLOB.X2-Frame.BLOB.X1, self.cY)
        #print(p1, p2)
        cv2.line(self.imageBlob, p1, p2, (0, 255, 0), 3)
        p1 = (self.cX, 0) 
        p2 = (self.cX, Frame.BLOB.Y2-Frame.BLOB.Y1) 
        #print(p1, p2)
        cv2.line(self.imageBlob, p1, p2, (0, 255, 0), 3)
        
        #show target midy
        p1 = (0, self.midy) 
        p2 = (Frame.BLOB.X2-Frame.BLOB.X1, self.midy)
        cv2.line(self.imageBlob, p1, p2, (0, 255, 0), 1)  # black line
        p1 = (0, self.midy+1)
        p2 = (Frame.BLOB.X2-Frame.BLOB.X1, self.midy+1)
        cv2.line(self.imageBlob, p1, p2, (255, 255, 255), 1) # white line

        self.blobState = blobState
        return blobState
            
class Film:

    Resolution = "720x540"
    Framerate = 12
    filmFolder = defaultBaseDir + "film" + os.sep
    scanFolder = defaultBaseDir + "scan" + os.sep
    cropFolder = defaultBaseDir + "crop" + os.sep

    def __init__(self, name = ""):
        self.name = name
        self.scanFileCount = len(Film.getFileList(Film.scanFolder))  # - number of *.jpg files in scan directory
        self.curFrameNo = -1
        self.p = None
     
    def getCurrentFrame(self):
        self.curFrameNo -= 1
        return self.getNextFrame()
    
    def getFileList(dir):
        list = [f for f in os.listdir(dir) if 
                    fnmatch.fnmatch(f, "*.jpg") and
                    os.path.isfile(os.path.join(dir, f))]
        if len(list) > 1 :
            return sorted(list)
        return list

    def getFileCount(dir):
        n = 0
        for f in os.listdir(dir):
             if fnmatch.fnmatch(f, "*.jpg") and os.path.isfile(os.path.join(dir, f)):
                n = n + 1
        return n

    def deleteFilesInFolder(dir):
        for f in os.listdir(dir):
             if fnmatch.fnmatch(f, "*.jpg") and os.path.isfile(os.path.join(dir, f)):
                os.remove(os.path.join(dir, f))

    def getCropCount():
        return Film.getFileCount(Film.cropFolder)

    def getScanCount():
        return Film.getFileCount(Film.scanFolder)

    def getRandomFrame(self):
        fileList = Film.getFileList(Film.scanFolder)
        cnt = len(fileList)
        self.scanFileCount = cnt
        if cnt > 0 :
            rn = random.randint(0,cnt-1)
            randomf = os.path.join(Film.scanFolder,fileList[rn])
            self.curFrameNo = rn  
            return Frame(randomf)
        else:
            self.curFrameNo = -1
            return None

    def getLastFrame(self):
        fileList = Film.getFileList(Film.scanFolder)
        cnt = len(fileList)
        self.scanFileCount = cnt
        if cnt > 0 :
            self.curFrameNo = cnt-1
            return Frame(os.path.join(Film.scanFolder,fileList[self.curFrameNo]))
        else:
            self.curFrameNo = -1
            return None 

    def getFirstFrame(self):
        fileList = Film.getFileList(Film.scanFolder)
        cnt = len(fileList)
        self.scanFileCount = cnt
        if cnt > 0 :
            self.curFrameNo = 0
            return Frame(os.path.join(Film.scanFolder,fileList[self.curFrameNo]))
        else:
            self.curFrameNo = -1
            return None 

    def getNextFrame(self):
        fileList = Film.getFileList(Film.scanFolder)
        cnt = len(fileList)
        self.scanFileCount = cnt
        if cnt > 0 :
            if self.curFrameNo+1 >= cnt :
                self.curFrameNo = cnt-1
            elif self.curFrameNo+1 >= 0 :
                self.curFrameNo = self.curFrameNo+1
            else :
                self.curFrameNo = 0
            return Frame(os.path.join(Film.scanFolder,fileList[self.curFrameNo]))
        else:
            self.curFrameNo = -1
            return None   

    def getPreviousFrame(self):
        self.getTargetFrame(self.curFrameNo-1)
        fileList = Film.getFileList(Film.scanFolder)
        cnt = len(fileList)
        self.scanFileCount = cnt
        if cnt > 0 :
            if self.curFrameNo-1 >= cnt :
                self.curFrameNo = cnt-1
            elif self.curFrameNo-1 >= 0 :
                self.curFrameNo = self.curFrameNo-1
            else :
                self.curFrameNo = 0
            return Frame(os.path.join(Film.scanFolder,fileList[self.curFrameNo]))
        else:
            self.curFrameNo = -1
            return None   

    def getTargetFrame(self, target):
        fileList = Film.getFileList(Film.scanFolder)
        cnt = len(fileList)
        self.scanFileCount = cnt
        if cnt > 0 :
            if target >= cnt :
                self.curFrameNo = cnt-1
            elif target >= 0 :
                self.curFrameNo = target
            else :
                self.curFrameNo = 0
            return Frame(os.path.join(Film.scanFolder,fileList[self.curFrameNo]))
        else:
            self.curFrameNo = -1
            return None   

    def cropAll(self, progress) :
        frameNo = 0
        os.chdir(Film.scanFolder)
        fileList = sorted(glob.glob('*.jpg'))
        self.scanFileCount = len(fileList)
        for fn in fileList:
            frame = Frame(os.path.join(Film.scanFolder, fn))
            frame.cropPic()
            cv2.imwrite(os.path.join(Film.cropFolder, f"frame{frameNo:06}.jpg"), frame.imageCropped)
            self.curFrameNo = frameNo
            if progress is not None:
                if progress(frame) == 0:
                    break
            frameNo = frameNo+1
                    
    def makeFilm(self, filmName, progressReport, filmDone) :
        self.progressReport = progressReport
        self.filmDone = filmDone
        os.chdir(Film.cropFolder)
        filmPathName = os.path.join(Film.filmFolder, filmName) + '.mp4'
        if os.path.isfile(filmPathName):
            os.remove(filmPathName)
        
        if self.p is None:  # No process running.
            self.progressReport("Executing process")
            self.p = QProcess()  # Keep a reference to the QProcess (e.g. on self) while it's running.
            self.p.readyReadStandardOutput.connect(self.handle_stdout)
            self.p.readyReadStandardError.connect(self.handle_stderr)
            self.p.stateChanged.connect(self.handle_state)
            self.p.finished.connect(self.process_finished)  # Clean up once complete.
            self.p.start("ffmpeg", [
                "-framerate", str(Film.Framerate), 
                "-f", "image2",
                "-pattern_type", "sequence",
                "-i", Film.cropFolder + "frame%06d.jpg",
                "-s", Film.Resolution,
                "-preset", "ultrafast", filmPathName
                ])
  
 
    def handle_stderr(self):
        data = self.p.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.progressReport(stderr)

    def handle_stdout(self):
        data = self.p.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.progressReport(stdout)

    def handle_state(self, state):
        states = {
            QProcess.NotRunning: 'Not running',
            QProcess.Starting: 'Starting',
            QProcess.Running: 'Running',
        }
        state_name = states[state]
        self.progressReport(f"State changed: {state_name}")

    def process_finished(self):
        self.progressReport("Process finished.")
        self.filmDone()
        self.p = None        

