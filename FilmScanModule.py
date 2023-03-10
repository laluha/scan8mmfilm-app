# -*- coding: utf-8 -*-

import os, fnmatch
import cv2
import random
import glob
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QProcess
import configparser

dbg = 0

inifile = os.path.join(os.path.dirname(__file__),'scanner.ini')
defaultBaseDir = "c:\\data\\film8" if os.sep == "\\" else "/home/pi/film8"

class Ini:
    camera = 'camera'
    paths = 'paths'
    film = 'film'
    frame = 'frame'

    def loadConfig():
        config = configparser.ConfigParser()

        if len(config.read(inifile)) == 1:

            Film.filmFolder = config[Ini.paths]['film_folder']
            Film.scanFolder = config[Ini.paths]['scan_folder']
            Film.cropFolder = config[Ini.paths]['crop_folder']

            Camera.ViewWidth = config[Ini.camera].getint('view_width')
            Camera.ViewHeight = config[Ini.camera].getint('view_height')

            Film.Resolution = config[Ini.film]['resolution']
            Film.Framerate = config[Ini.film].getint('framerate')
            Film.StepsPrFrame = config[Ini.film].getint('steps_pr_frame')

            Frame.frameCrop.load(config)
            Frame.whiteCrop.load(config)
            Frame.holeCrop.load(config)

            Frame.holeMinArea = config[Ini.frame].getint('hole_min_area')
            Frame.midy = config[Ini.frame].getint('midy')

        else:
            Ini.saveConfig()

        Frame.initScaleFactor()
        
    def saveConfig():
        config = configparser.ConfigParser()

        if not config.has_section(Ini.paths):
            config[Ini.paths] = {}
        config[Ini.paths]['film_folder'] = Film.filmFolder
        config[Ini.paths]['scan_folder'] = Film.scanFolder
        config[Ini.paths]['crop_folder'] = Film.cropFolder
        
        if not config.has_section(Ini.camera):
            config[Ini.camera] = {}
        config[Ini.camera]['view_width'] = str(Camera.ViewWidth)
        config[Ini.camera]['view_height'] = str(Camera.ViewHeight)

        if not config.has_section(Ini.film):
            config[Ini.film] = {}
        config[Ini.film]['resolution'] = Film.Resolution
        config[Ini.film]['framerate']  = str(Film.Framerate)
        config[Ini.film]['steps_pr_frame'] = str(Film.StepsPrFrame)

        Frame.frameCrop.save(config)
        Frame.whiteCrop.save(config)
        Frame.holeCrop.save(config)

        if not config.has_section(Ini.frame):
            config[Ini.frame] = {}
        config[Ini.frame]['hole_min_area'] = str(Frame.holeMinArea) 
        config[Ini.frame]['midy'] = str(Frame.midy) 

        with open(inifile, 'w') as configfile:
            config.write(configfile)
        
def getAdjustableRects():
    return [Frame.frameCrop, Frame.holeCrop, Frame.whiteCrop]

class Camera:
    ViewWidth = 1640
    ViewHeight = 1232

class Rect:
    def __init__(self, name, x1, y1, x2, y2):
        self.name = name
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        
    def load(self, config):
        self.x1 = config[self.name].getint('x1')
        self.x2 = config[self.name].getint('x2')
        self.y1 = config[self.name].getint('y1')
        self.y2 = config[self.name].getint('y2')

    def save(self, config):
        if not config.has_section(self.name):
            config[self.name] = {}
        config[self.name]['x1'] = str(self.x1)
        config[self.name]['x2'] = str(self.x2)
        config[self.name]['y1'] = str(self.y1) 
        config[self.name]['y2'] = str(self.y2)

    def getXSize(self):
        return self.x2 - self.x1
    
    def getYSize(self):
        return self.y2 - self.y1
    
    def adjX(self, adj):
        if self.x1 + adj >= 0 :
            self.x1 = self.x1 + adj
            self.x2 = self.x2 + adj

    def adjY(self, adj):
        if self.y1 + adj >= 0 :
            self.y1 = self.y1 + adj
            self.y2 = self.y2 + adj
        
    def adjXSize(self, adj):
        if self.x2 + adj > self.x1 :
            self.x2 = self.x2 + adj
    
    def adjYSize(self, adj):
        if self.y2 + adj > self.y1 :
            self.y2 = self.y2 + adj 

class Frame:

    # Default x,y values for hole mid relative to holeCrop (0,0) 
    # from camera view image resized to 640x480
    # N.B. The midy value is used to position the frame near the center of the camera view during scanning
    midx = 64   # always overwitten 
    midy = 120 
    
    # Needs to be adjusted to fit the a film frame as seen in the camera view image
    # x1,y1 are relative to the top sprocket hole center
    frameCrop = Rect("frame_crop", 146, 28, 146+814, 28+565)

    # Must be adjusted to an always white area in the camera view image resized to 640x480
    whiteCrop = Rect("white_crop", 562, 130, 562+12, 110+130)

    # Must be adjusted to the left top area of the film containing the 
    # upper sprocket hole in the camera view image resized to 640x480
    holeCrop = Rect("hole_crop", 90, 0, 240, 276)  

    holeMinArea = 6000 # Adust to a size safely less than the average sprocket hole area
        
    ScaleFactor = 1.0 # overwritten by initScaleFactor()

    def initScaleFactor():
        Frame.ScaleFactor = Camera.ViewWidth/640.0 

    def getHoleCropWidth():
        return Frame.holeCrop.x2 - Frame.holeCrop.x1
          
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
        
        self.locateHoleResult = 1
        self.whiteTreshold = 225 # always overwritten by call to getWhiteThreshold
        self.area = 0
        
        
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
        
    def getHoleCrop(self) :
        return self.convert_cv_qt(self.imageHoleCrop)

    def calcCrop(self):
        self.locateHoleResult = self.locateSprocketHole(Frame.holeMinArea)
        
        x = int((self.cX + Frame.holeCrop.x1) * Frame.ScaleFactor)+Frame.frameCrop.x1
        y = int((self.cY + Frame.holeCrop.y1) * Frame.ScaleFactor)+Frame.frameCrop.y1 
        self.p1 = (x, y)
        self.p2 = (x+Frame.frameCrop.getXSize(), y+Frame.frameCrop.getYSize())
        
    def getCropOutline(self, dest=None):
        self.calcCrop()
        cv2.rectangle(self.image, self.p1, self.p2, (0, 255, 0), 10)
        wp1 = (round(Frame.whiteCrop.x1 * Frame.ScaleFactor), round(Frame.whiteCrop.y1 * Frame.ScaleFactor))
        wp2 = (round(Frame.whiteCrop.x2 * Frame.ScaleFactor), round(Frame.whiteCrop.y2 * Frame.ScaleFactor))
        cv2.rectangle(self.image, wp1, wp2, (60, 240, 240), 10)
        return self.convert_cv_qt(self.image, dest)
        
    def cropPic(self):
        self.calcCrop()
        self.imageCropped = self.image[self.p1[1]:self.p2[1], self.p1[0]:self.p2[0]]
     
    def getWhiteThreshold(self, imageSmall):
        img = imageSmall[Frame.whiteCrop.y1:Frame.whiteCrop.y2, Frame.whiteCrop.x1:Frame.whiteCrop.x2]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        planes = cv2.split(img)
        histSize = 256 #  [Establish the number of bins]
        histRange = (0, 256) # Set the range
        hist = cv2.calcHist(planes, [0], None, [histSize], histRange, accumulate=False)    
        okPct = (Frame.whiteCrop.y2-Frame.whiteCrop.y1)*(Frame.whiteCrop.x2-Frame.whiteCrop.x1)/100.0*5
        wco = 220 # Default value - will work in most cases
        for i in range(128,256) :
            if hist[i] > okPct :
                wco = i-8 #6
                break
        return wco        
      
    # area size has to be set to identify the sprocket hole
    # if the sprocket hole area is around 8000, then 6000 should be a safe choice
    # the area size will trigger the exit from the loop
    # Return values:
    # 0: hole found, 1: hole not found, 2: hole to large, 3: no center
    def locateSprocketHole(self, area_size):
        self.imageSmall = cv2.resize(self.image, (640, 480))
        # the image crop with the sprocket hole 
        img = self.imageSmall[Frame.holeCrop.y1:Frame.holeCrop.y2, Frame.holeCrop.x1:Frame.holeCrop.x2]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        self.whiteTreshold = self.getWhiteThreshold(self.imageSmall)
        ret, self.imageHoleCrop = cv2.threshold(img, self.whiteTreshold, 255, 0) 
        contours, hierarchy = cv2.findContours(self.imageHoleCrop, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        # RETR_LIST: retrieves all of the contours without establishing any hierarchical relationships.
        # CHAIN_APPROX_SIMPLE: compresses horizontal, vertical, and diagonal segments and leaves only 
        # their end points. For example, an up-right rectangular contour is encoded with 4 points.
        
        lenContours = len(contours)
        locateHoleResult = 1 
        oldcX = self.cX
        oldcY = self.cY
        self.area = area_size
        for l in range(lenContours):
            cnt = contours[l]
            area = cv2.contourArea(cnt)
            if dbg >= 1 :
                print((l, area))
            if area > area_size:
                locateHoleResult = 0 # hole found
                self.area = area
                if area > 3*area_size:
                    locateHoleResult = 2 # very large contour found == no film
                # print("found")
                # print("area=", area)
                break
        if locateHoleResult == 0:      
            M = cv2.moments(cnt)
            # print(M)
            try:
                self.cX = int(M["m10"] / M["m00"])
                self.cY = int(M["m01"] / M["m00"])
                #holeDist = 225
                #if cY > holeDist : # distance between holes
                #    print("cY=", cY)
                #    locateHoleResult = 4 # 2. hole found
                #    cY = cY - holeDist
            except ZeroDivisionError:
                if dbg >= 2: print("no center")
                locateHoleResult = 3 # no center
                self.cX = oldcX
                self.cY = oldcY # midy
        else :
            self.cX = oldcX
            self.cY = oldcY  
                  
        if dbg >= 2: print("cY=", self.cY, "oldcY=", oldcY, "locateHoleResult=", locateHoleResult)
 
        p1 = (0, self.cY) 
        p2 = (Frame.holeCrop.x2-Frame.holeCrop.x1, self.cY)
        # print(p1, p2)
        cv2.line(self.imageHoleCrop, p1, p2, (0, 255, 0), 3)
        p1 = (self.cX, 0) 
        p2 = (self.cX, Frame.holeCrop.y2-Frame.holeCrop.y1) 
        # print(p1, p2)
        cv2.line(self.imageHoleCrop, p1, p2, (0, 255, 0), 3)
        
        # show target midy
        p1 = (0, self.midy) 
        p2 = (Frame.holeCrop.x2-Frame.holeCrop.x1, self.midy)
        cv2.line(self.imageHoleCrop, p1, p2, (0, 255, 0), 1)  # black line
        p1 = (0, self.midy+1)
        p2 = (Frame.holeCrop.x2-Frame.holeCrop.x1, self.midy+1)
        cv2.line(self.imageHoleCrop, p1, p2, (255, 255, 255), 1) # white line

        self.locateHoleResult = locateHoleResult
        return locateHoleResult
            
class Film:

    Resolution = "720x540"
    Framerate = 12
    StepsPrFrame = 80 # value for Standard 8

    filmFolder = os.path.join(defaultBaseDir, "film")
    scanFolder = os.path.join(defaultBaseDir, "scan")
    cropFolder = os.path.join(defaultBaseDir, "crop")

    def __init__(self, name = ""):
        self.name = name
        self.scanFileCount = Film.getFileCount(Film.scanFolder)  # - number of *.jpg files in scan directory
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
                "-i", os.path.join(Film.cropFolder, "frame%06d.jpg"),
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

