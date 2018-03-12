# use open cv to show new images from AirSim 

from AirSimClient import *
# requires Python 3.5.3 :: Anaconda 4.4.0
# pip install opencv-python
import cv2
import time
import sys
import numpy as np
import random as rnd
import PIL
print("hi")


def printUsage():
   print("Usage: python camera.py [depth|segmentation|scene]")

cameraType = "scene"

for arg in sys.argv[1:]:
  cameraType = arg.lower()

cameraTypeMap = { 
 "depth": AirSimImageType.DepthVis,
 "segmentation": AirSimImageType.Segmentation,
 "seg": AirSimImageType.Segmentation,
 "scene": AirSimImageType.Scene,
 "disparity": AirSimImageType.DisparityNormalized,
 "normals": AirSimImageType.SurfaceNormals
}

if (not cameraType in cameraTypeMap):
  printUsage()
  sys.exit(0)

#print (cameraTypeMap[cameraType])

client = MultirotorClient()
client.confirmConnection()
client.enableApiControl(True)
#client.armDisarm(True)
#client.takeoff()

help = False
bbox = None
fontFace = cv2.FONT_HERSHEY_SIMPLEX
fontScale = 0.5
thickness = 2
textSize, baseline = cv2.getTextSize("FPS", fontFace, fontScale, thickness)
print (textSize)
textOrg = (10, 10 + textSize[1])
frameCount = 0
startTime=time.clock()
fps = 0

lk_params = dict( winSize  = (15,15),
                  maxLevel = 2,
                  criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

img = None

def boundedbox(img):
    bbox = cv2.selectROI(img, False)
    frameGray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    roi = frameGray[bbox[1]:(bbox[1]+bbox[3]),bbox[0]:(bbox[0]+bbox[2])]
    new_corners = cv2.goodFeaturesToTrack(roi,50,0.01,10) 
    new_corners[:,0,0] = new_corners[:,0,0] + int(bbox[0])
    new_corners[:,0,1] = new_corners[:,0,1] + int(bbox[1])
    for corner in new_corners:
        print(corner)
    return frameGray,new_corners,bbox

time1 = time.time()
pos = [-50, 10, -8]
tracking = 0
client.moveToPosition(pos[0], pos[1], pos[2], 5, 10)
api = True
while True:
    # because this method returns std::vector<uint8>, msgpack decides to encode it as a string unfortunately.
    rawImage = client.simGetImage(0, cameraTypeMap[cameraType])
    if (rawImage == None):
        print("Camera is not returning image, please check airsim for error messages")
        sys.exit(0)
    else:
        img = cv2.imdecode(AirSimClientBase.stringToUint8Array(rawImage),cv2.IMREAD_UNCHANGED)
        #print(png.shape)
        cv2.putText(img,'FPS ' + str(fps),textOrg, fontFace, fontScale,(255,255,255),thickness)
        #cv2.imshow("Depth", png)
        # calculate
        
        if cv2.waitKey(1) & 0xFF == ord('s'):
            oldGray,corners,bbox = boundedbox(img)
            client.moveToPosition(-10, pos[1], pos[2], 1, 0)            
            continue
        if bbox is not None:
            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            new_corners, st, err = cv2.calcOpticalFlowPyrLK(oldGray, gray, corners, None, **lk_params)
            r_add,c_add = 0,0
            for corner in new_corners:
                r_add = r_add + corner[0][1]
                c_add = c_add + corner[0][0]
            centroid_row = int(1.0*r_add/len(new_corners))
            centroid_col = int(1.0*c_add/len(new_corners))
            #draw centroid
            print(img.shape)
            cv2.circle(img,(int(centroid_col),int(centroid_row)),5,(255,0,0)) 
            #add only those corners to new_corners_updated which are at a distance of 30 or lesse
            new_corners_updated = new_corners.copy()
            tobedel = []
            for index in range(len(new_corners)):
                if findDistance(new_corners[index][0][1],new_corners[index][0][0],int(centroid_row),int(centroid_col)) > 90:
                    tobedel.append(index)
            new_corners_updated = np.delete(new_corners_updated,tobedel,0)
        
        

            #drawing the new points
            for corner in new_corners_updated:
                cv2.circle(img, (int(corner[0][0]),int(corner[0][1])) ,5,(0,255,0))
            if len(new_corners_updated) < 1:
                print("OBJECT LOST, Reinitialize for tracking")
                break
            #finding the min enclosing circle
            ctr , rad = cv2.minEnclosingCircle(new_corners_updated)
        
            cv2.circle(img, (int(ctr[0]),int(ctr[1])) ,int(rad),(0,0,255),thickness = 5)	
            
            #updating old_corners and oldFrameGray 
            oldGray = gray.copy()
            corners = new_corners_updated.copy()

            #p1 = (int(bbox[0]), int(bbox[1]))
            #p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            #cv2.rectangle(img,p1,p2,color = (100,255,100),thickness = 4)
        cv2.imshow("Flow", img)
    frameCount  = frameCount  + 1
    endTime=time.clock()
    diff = endTime - startTime
    if (diff > 1):
        fps = frameCount
        frameCount = 0
        startTime = endTime

    if time.time() - time1 > 1.0 and api:
        # get new random place 
        #pos = [rnd.randint(-10, 10), rnd.randint(-10, 10), rnd.randint(-10, -3)]
        time1 = time.time()

    currPos = client.simGetPose().position
    
    #print( ((pos[0]-currPos.x_val)**2 + (pos[1]-currPos.y_val)**2 + (pos[2]-currPos.z_val)**2)**(1/2) )
    #client.rotateByYawRate(15, 0.1)

