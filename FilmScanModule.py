# -*- coding: utf-8 -*-
"""
Created on Sun Jan 15 18:45:07 2023

@author: B
"""
import os.path
import cv2
import random
import glob
import sys
import subprocess
from PyQt5 import QtGui 
from PyQt5.QtCore import Qt
import configparser

dbg = 0

inifile = os.path.join(os.path.dirname(__file__),'scanner.ini')
defaultBaseDir = "c:\\data\\film8\\" if os.sep == "\\" else "/home/pi/film8/"

def loadConfig():
    global defaultBaseDir
    config = configparser.ConfigParser()
    if len(config.read(inifile)) == 1:
        Frame.xcal = config['FRAME'].getint('xcal')
        Frame.ycal = config['FRAME'].getint('ycal')
        Frame.xsize = config['FRAME'].getint('xsize')
        Frame.ysize = config['FRAME'].getint('ysize')
        defaultBaseDir = config['FRAME']['filmdir']
    else:
        saveConfig()
    
def saveConfig():
    global defaultBaseDir
    config = configparser.ConfigParser()
    config['FRAME'] = { 
        'xcal': str(Frame.xcal), 
        'ycal': str(Frame.ycal),
        'xsize': str(Frame.xsize), 
        'ysize': str(Frame.ysize),
        }
    config['PATHS'] = { 'filmdir': defaultBaseDir }
    with open(inifile, 'w') as configfile:
       config.write(configfile)

    
class Frame:
    ysize = 534 #  needs to be adjusted to fit the picture
    xsize = 764 
        
    ScaleFactor = 1640.0/640  
        
    whiteCutoff = 220
    
    # Top image edgeY = holeCenterY + imageBlackFrame thickness
    ycal = 30 # 34 + 267 # 534/2 # 500 calibrate camera frame y position 0=center of blob 
    
    # Left image edgeX = holeCenterX + holeW/2: 377 + 288/2 = (BLOB_X1 + cX) *ScaleFactor + holeW/2
    xcal = 144 
        
    midx = 64
    midy = 136 

    whiteBoxX1 = 544
    whiteBoxY1 = 130
    whiteBoxX2 = 544+12
    whiteBoxY2 = 110+130

    BLOB_Y1 = 0  
    BLOB_Y2 = 340
    BLOB_X1 = 90 # 130
    BLOB_X2 = 240 # 210
    BLOB_MIN_AREA = 4000 # 4000  
    
    BLOB_W = BLOB_X2 - BLOB_X1
        
    def __init__(self, imagePathName=None,*,image=None):
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
        
    def getQPixmap(self):
        #self.image = cv2.imread(self.imagePathName)
        return self.convert_cv_qt(self.image)
        # return QtGui.QPixmap(self.imagePathName)
        
    def getCropped(self):
        return self.convert_cv_qt(self.imageCropped)
        
    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        #p = convert_to_Qt_format.scaled(self.disply_width, self.display_height, Qt.KeepAspectRatio)
        return QtGui.QPixmap.fromImage(convert_to_Qt_format)        

    def crop_pic(self, doCreate=False):
        #img = cv2.imread(n)
        state = self.find_blob(Frame.BLOB_MIN_AREA)
        
        x = int((self.cX + Frame.BLOB_X1) * Frame.ScaleFactor)+Frame.xcal
        y = int(self.cY * Frame.ScaleFactor)+Frame.ycal 
        self.p1 = (x, y)
        self.p2 = (x+Frame.xsize, y+Frame.ysize)
        
        if dbg >= 2: print( self.p1,  self.p2) 
        if doCreate :
            self.imageCropped = self.image[y:y+Frame.ysize, x:x+Frame.xsize]
            return None
        cv2.rectangle(self.image, self.p1, self.p2, (0, 255, 0), 10)
        wp1 = (round(Frame.whiteBoxX1 * Frame.ScaleFactor), round(Frame.whiteBoxY1 * Frame.ScaleFactor))
        wp2 = (round(Frame.whiteBoxX2 * Frame.ScaleFactor), round(Frame.whiteBoxY2 * Frame.ScaleFactor))
        cv2.rectangle(self.image, wp1, wp2, (60, 240, 240), 10)
        #cv2waitKey(2)
        #if dbg > 1 :
        #    cv2imshow('Cal-Crop', img)
        #    cv2waitKey(2)
        return self.convert_cv_qt(self.image)
     
    def getWhiteCutoff(self, imageSmall):
        img = imageSmall[Frame.whiteBoxY1:Frame.whiteBoxY2, Frame.whiteBoxX1:Frame.whiteBoxX2]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        planes = cv2.split(img)
        histSize = 256 #  [Establish the number of bins]
        histRange = (0, 256) # Set the range
        hist = cv2.calcHist(planes, [0], None, [histSize], histRange, accumulate=False)    
        okPct = (Frame.whiteBoxY2-Frame.whiteBoxY1)*(Frame.whiteBoxX2-Frame.whiteBoxX1)/100.0*5
        wco = 220
        for i in range(128,256) :
            if hist[i] > okPct :
                wco = i-6
                break
        return wco        
      
    # area size has to be set to identify the sprocket hole blob
    # if the sprocket hole area is around 2500, then 2000 should be a safe choice
    # the area size will trigger the exit from the loop
    
    def find_blob(self, area_size):
        self.imageSmall = cv2.resize(self.image, (640, 480))
        # the image crop with the sprocket hole 
        img = self.imageSmall[Frame.BLOB_Y1:Frame.BLOB_Y2, Frame.BLOB_X1:Frame.BLOB_X2]
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
        p2 = (Frame.BLOB_X2-Frame.BLOB_X1, self.cY)
        #print(p1, p2)
        cv2.line(self.imageBlob, p1, p2, (0, 255, 0), 3) 
        p1 = (self.cX, 0) 
        p2 = (self.cX, Frame.BLOB_Y2-Frame.BLOB_Y1) 
        #print(p1, p2)
        cv2.line(self.imageBlob, p1, p2, (0, 255, 0), 3)
        self.blobState = blobState
        return blobState
        
    def getBlob(self) :
        return self.convert_cv_qt(self.imageBlob)
            
class Film:
    name = ""
    
    def __init__(self, name = "", baseDir = None):
        self.name = name
        if baseDir == None:
            self.baseDir = defaultBaseDir
        else:
            self.baseDir = baseDir
        self.scan_dir = self.baseDir + "scan" + os.sep
        self.crop_dir = self.baseDir + "crop" + os.sep
        self.max_pic_num = len([f for f in os.listdir(self.scan_dir) if 
            os.path.isfile(os.path.join(self.scan_dir, f))])  # - number of files in scan directory
        self.curFrameNo = -1

    def cropAll(self, progress) :
                frameNo = 0
                os.chdir(self.scan_dir)
                fileList = sorted(glob.glob('*.jpg'))
                self.max_pic_num = len(fileList)
                for fn in fileList:
                    frame = Frame(os.path.join(self.scan_dir, fn))
                    frame.crop_pic(True)
                    cv2.imwrite(os.path.join(self.crop_dir, f"frame{frameNo:06}.jpg"), frame.imageCropped)
                    self.curFrameNo = frameNo
                    if progress is not None:
                        if progress(frame) == 0:
                            break
                    frameNo = frameNo+1
                    
    def makeFilm(self, name) :
        os.chdir(self.crop_dir)
        filmPathName = os.path.join(self.baseDir, name) + '.mp4'
        subprocess.check_output(
            'ffmpeg  -framerate 12 -f image2 -pattern_type sequence -i "' + self.crop_dir + 'frame%06d.jpg"  -s 720x540  -preset ultrafast ' + filmPathName, shell=True)

    def getCurrentFrame(self):
        self.curFrameNo -= 1
        return self.getNextFrame()

    def getRandomFrame(self):
        fileList = sorted([f for f in os.listdir(self.scan_dir) if 
                    os.path.isfile(os.path.join(self.scan_dir, f))])
        cnt = len(fileList)
        self.max_pic_num = cnt
        if cnt > 0 :
            rn = random.randint(0,cnt-1)
            randomf = os.path.join(self.scan_dir,fileList[rn])
            self.curFrameNo = rn  
            return Frame(randomf)
        else:
            self.curFrameNo = -1
            return None
        
    def getNextFrame(self):
        fileList = sorted([f for f in os.listdir(self.scan_dir) if 
                    os.path.isfile(os.path.join(self.scan_dir, f))])
        cnt = len(fileList)
        self.max_pic_num = cnt
        if cnt > 0 :
            if self.curFrameNo+1 >= cnt :
                self.curFrameNo = cnt-1
            elif self.curFrameNo+1 >= 0 :
                self.curFrameNo = self.curFrameNo+1
            else :
                self.curFrameNo = 0
            return Frame(os.path.join(self.scan_dir,fileList[self.curFrameNo]))
        else:
            self.curFrameNo = -1
            return None   

    def getPreviousFrame(self):
        fileList = sorted([f for f in os.listdir(self.scan_dir) if 
                    os.path.isfile(os.path.join(self.scan_dir, f))])
        cnt = len(fileList)
        self.max_pic_num = cnt
        if cnt > 0 :
            if self.curFrameNo-1 >= cnt :
                self.curFrameNo = cnt-1
            elif self.curFrameNo-1 >= 0 :
                self.curFrameNo = self.curFrameNo-1
            else :
                self.curFrameNo = 0
            return Frame(os.path.join(self.scan_dir,fileList[self.curFrameNo]))
        else:
            self.curFrameNo = -1
            return None   
     
