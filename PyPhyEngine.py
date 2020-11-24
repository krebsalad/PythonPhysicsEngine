from uuid import uuid1 as generateUuid
import sys
import cv2
import numpy as np
import time
import math

# main data class for positioning
class Vec2d:
    def __init__(self, _x, _y):
        self.x = _x
        self.y = _y

    def getRotatedVec(self, _angle=0):
        newX = math.cos(_angle) * self.x - math.sin(_angle) * self.y
        newY = math.sin(_angle) * self.x + math.cos(_angle) * self.y
        return Vec2d(newX, newY)
    
    def __getitem__(self, _key):
        if _key == 0:
            return self.x
        if _key == 1:
            return self.y
        return None

    def __setitem__(self, _key, _item):
        if _key == 0:
            self.x = _item
        if _key == 1:
            self.y = _item
    
    def __add__(self, _vec2d):
        return Vec2d(self.x + _vec2d.x, self.y + _vec2d.y)

    def __sub__(self, _vec2d):
        return Vec2d(self.x - _vec2d.x, self.y - _vec2d.y)

    def __truediv__(self, _num):
        return Vec2d(self.x/_num, self.y/_num)

    def asTuple(self, _round=False):
        if _round:
            return (int(self.x), int(self.y))
        return (self.x, self.y)
    
    def __mul__(self, _num):
        return Vec2d(self.x * _num, self.y * _num)

    def __str__(self):
        return str(self.x) + "," + str(self.y)

# utility functions for Vec2d
def InterpolatePositionsBetweenPoints(_vec1, _vec2, _points=5):
    positions = []
    step_x = (_vec2.x - _vec1.x) / _points
    step_y = (_vec2.y - _vec1.y) / _points
    for n in range(1, _points):
        positions.append(_vec1 + Vec2d(step_x * n, step_y * n))
    return positions

def CalcTriangleSignArea(_pos1, _pos2, _pos3):
    return (_pos1.x - _pos3.x) * (_pos2.y - _pos3.y) - (_pos2.x - _pos3.x) * (_pos1.y - _pos3.y)

def IsPositionWithinTriangle(_position, _trianglePos1, _trianglePos2, _trianglePos3):
    a1 = CalcTriangleSignArea(_position, _trianglePos1, _trianglePos2)
    a2 = CalcTriangleSignArea(_position, _trianglePos2, _trianglePos3)
    a3 = CalcTriangleSignArea(_position, _trianglePos3, _trianglePos1)
    return (a1 < 0) == (a2 < 0) and (a2 < 0) == (a3 < 0)

# A hitbox/rectangle used to detect collision
class HitBox2d:
    def __init__(self, _name, _ownerId, _shape, _relativePos=Vec2d(0,0), _relativeRot=0):
        self.ownerId = _ownerId                 # id of entity
        self.shape = _shape                     # the width and height of the hitbox
        self.relativePos = _relativePos         # the position of the hitbox relative to origin (0,0)
        self.relativeRot = _relativeRot
        self.name = _name                       # the name of the hitbox

    def getBoundingRect(self, _worldPosition=Vec2d(0,0), _worldRotation=0, _offset=Vec2d(0,0)):
        halfExtents = (self.shape/2)           
        leftTop = self.relativePos - halfExtents - _offset       
        rightBot = self.relativePos + halfExtents + _offset
        leftBot = Vec2d(leftTop.x - _offset.x, self.relativePos.y + halfExtents.y + _offset.y)
        rightTop = Vec2d(rightBot.x + _offset.x, self.relativePos.y - halfExtents.y - _offset.y)

        leftTop = leftTop.getRotatedVec(self.relativeRot + _worldRotation) + _worldPosition
        rightTop = rightTop.getRotatedVec(self.relativeRot + _worldRotation) + _worldPosition
        leftBot = leftBot.getRotatedVec(self.relativeRot + _worldRotation) + _worldPosition
        rightBot = rightBot.getRotatedVec(self.relativeRot + _worldRotation) + _worldPosition
        return (leftTop, rightTop, leftBot, rightBot)

# a Entity, holding pasic information about the positioning of the entity and how it interacts with the world
class Entity2d:
    def __init__(self, _name, _id, _position=Vec2d(0,0), _rotation=0, _physics2d=None, _updateCallBack=None):
        self.name = _name
        self.id = _id 

        self.hitBoxes = []
        self.position = _position
        self.rotation = _rotation
        self.velocity = Vec2d(0,0)             # the velocity to be applied on the position (pixels per second), only applied when a non fixed physics entity is existing
        
        self.physics2d = _physics2d            # the entity holding information about the physics (requires a member function update(_scene, _entity) function to work)
        self.blockedUp = False                 # applies restraints to the velocity
        self.blockedLeft = False
        self.blockedRight = False
        self.blockedDown = False

        self.updateCallBack = _updateCallBack   # a function to call after apply basic physics, is also called without having a physics2d if set

        self.color = (255,0,0) 
        
    def createHitBox(self, _shape=Vec2d(15, 20), _relativePos=Vec2d(0,0), _relativeRot=0, _name="HitBox"):
        name = _name
        if _name == "HitBox":
            name = self.name + "_" + _name + "_" + str(len(self.hitBoxes))
        else:
            name = self.name + "_" + "HitBox" + "_" + _name
        self.hitBoxes.append(HitBox2d(name, self.id, _shape, _relativePos, _relativeRot))
            
    def update(self, _scene):
        # pre update
        if self.physics2d != None:
            self.physics2d.preUpdate(_scene, self)

        # callback user update
        if self.updateCallBack != None:
            self.updateCallBack(_scene, self)

        # update physics
        if self.physics2d != None:
            self.physics2d.afterUpdate(_scene, self)
        return

    def getCollisionPositions(self, _points=5, _pixelOffset=Vec2d(3,3)):
        # Interpolates outer edges of all hitboxes and returns them as lists
        bottomPositions = []
        topPositions = []
        leftPositions = []
        rightPositions = []
        for hBox in self.hitBoxes:
            leftTop, rightTop, leftBot, rightBot = hBox.getBoundingRect(self.position, self.rotation, _pixelOffset)
            bottomPositions += InterpolatePositionsBetweenPoints(leftBot, rightBot)
            topPositions += InterpolatePositionsBetweenPoints(leftTop, rightTop)
            leftPositions += InterpolatePositionsBetweenPoints(leftTop, leftBot)
            rightPositions += InterpolatePositionsBetweenPoints(rightTop, rightBot)
        return (bottomPositions,topPositions,leftPositions,rightPositions)

# A class that can be use to enable hitbox detection for entities and holds properties with the regards to interactions done by or to ther entities
class EntityPhysics2d:
    def __init__(self, _fixed=True, _maxVelocity=Vec2d(1000, 1000), _friction=Vec2d(0,0)):    
        self.fixed = _fixed                     # false if the entity is supposed to move
        self.friction = _friction               # the amount of friction to apply to other moving entities
        self.maxVelocity = _maxVelocity         # the maximum velocity (pixels per second) of an entity 
              
    def getFirstMeetingPhysicsEntity(self, _scene, _entity, _positions, _entityMeetingIsFixed=True):
        # returns the first entity a given entity collides with
        entitiesMeetingIds = _scene.getEntitysMeetingPositions(_positions)
        for i in entitiesMeetingIds:
            if i == _entity.id:
                continue
            meetingEntity = _scene.getEntity(i)
            if meetingEntity.physics2d != None and (meetingEntity.physics2d.fixed and _entityMeetingIsFixed) or (not meetingEntity.physics2d.fixed and not _entityMeetingIsFixed):
                return (True, meetingEntity)
        return (False, None)

    def preUpdate(self, _scene, _entity):
        # skip if fixed entity 
        if self.fixed:
            return

        # apply gravity
        _entity.velocity += _scene.gravity

        # get collision points to check on
        bottomPositions,topPositions,leftPositions,rightPositions = _entity.getCollisionPositions()

        # check if touching ground or not and apply corresponding physics
        downFound, ground = self.getFirstMeetingPhysicsEntity(_scene, _entity, bottomPositions, True)
        if downFound:
            _entity.blockedDown = True

            # apply friction when touching ground
            if _entity.velocity.x < 0:
                _entity.velocity += ground.physics2d.friction
                if _entity.velocity.x > 0:
                    _entity.velocity.x = 0
                    
            elif _entity.velocity.x > 0:
                _entity.velocity -= ground.physics2d.friction
                if _entity.velocity.x < 0:
                    _entity.velocity.x = 0

        if _entity.blockedDown and not downFound:
            _entity.blockedDown = False

        # check if touching right
        rightFound = self.getFirstMeetingPhysicsEntity(_scene, _entity, rightPositions, True)[0]
        if rightFound:
            _entity.blockedRight = True

        if _entity.blockedRight and not rightFound:
            _entity.blockedRight = False

        # check if touching top
        topFound = self.getFirstMeetingPhysicsEntity(_scene, _entity, topPositions, True)[0]
        if topFound:
            _entity.blockedUp = True

        if _entity.blockedUp and not topFound:
            _entity.blockedUp = False

        # check if touching left
        leftFound = self.getFirstMeetingPhysicsEntity(_scene, _entity, leftPositions, True)[0]
        if leftFound:
            _entity.blockedLeft = True

        if _entity.blockedLeft and not leftFound:
            _entity.blockedLeft = False

    def afterUpdate(self, _scene, _entity):
        # skip if fixed entity 
        if self.fixed:
            return

        # apply restraints
        if _entity.blockedDown and _entity.velocity.y > 0:
            _entity.velocity.y = 0

        if _entity.blockedUp and _entity.velocity.y < 0:
            _entity.velocity.y = 0

        if _entity.blockedLeft and _entity.velocity.x < 0:
            _entity.velocity.x = 0

        if _entity.blockedRight and _entity.velocity.x > 0:
            _entity.velocity.x = 0

        # limit velocity
        if _entity.velocity.y > self.maxVelocity.y:
            _entity.velocity.y = self.maxVelocity.y
        if _entity.velocity.y < 0 - self.maxVelocity.y:
            _entity.velocity.y = 0 - self.maxVelocity.y

        if _entity.velocity.x > self.maxVelocity.x:
            _entity.velocity.x = self.maxVelocity.x
        if _entity.velocity.x < 0 - self.maxVelocity.x:
            _entity.velocity.x = 0 - self.maxVelocity.x    

        return

# In the works!!!!
class Animation2d:
    def __init__(self, _id, _center=(0,0), _imagePaths=[], _playBackSpeed=1):
        for path in _imagePaths:
            self.addImage(path)
        self.images = []
        self.center = _center
        self.playBackSpeed = _playBackSpeed
        self.currentImageIndex = -1
        self.startTime = time.time()
    
    def addImage(self, _path):
        return False

    def getOpencvImage(self):
        return None

    def draw(self, _position, _inFrame):
        if self.currentImageIndex == -1:
            return None
        
        timePerFrame = self.playBackSpeed / self.currentImageIndex
        if time.time() > self.startTime + (timePerFrame * (self.currentImageIndex + 1)):
            self.startTime = time.time()
            self.currentImageIndex += 1
            if self.currentImageIndex > len(self.images):
                self.currentImageIndex = 0

        return self.images[self.currentImageIndex]

# The
class Scene2d:
    def __init__(self, _id, _gravity=Vec2d(0, 1), _ticksPerSecond=1000):
        self.id = _id                               # a unique id of the scene

        self.entities = []                       # a list of enties to draw in the scene

        self.gravity = _gravity                     # the gravity applied to physics entities
        
        self.lastTickTime = time.time()             # saves the time the last tick (loop) was done
        self.lastUpdateTime = time.time()           # save the time the last update was done

        self.ticksPerSecond = _ticksPerSecond       # amount of ticks to update in a update phase

    def getHitBoxesMeetingPosition(self, _position): # <TO FIX, doesnt work with rotated rectangles>
        hitBoxes = []
        for gEntity in self.entities:
            for hBox in gEntity.hitBoxes:
                leftTop, rightTop, leftBot, rightBot = hBox.getBoundingRect(gEntity.position)
                
                if IsPositionWithinTriangle(_position, leftBot, rightBot, rightTop) or IsPositionWithinTriangle(_position, rightTop, leftTop, leftBot):
                # if _position.x >= leftTop.x and _position.x <= rightBot.x and _position.y >= leftTop.y and _position.y <= rightBot.y: 
                    hitBoxes.append(hBox)  
        return hitBoxes

    def getEntitysMeetingPositions(self, _positions):
        entityIds = []
        for position in _positions:
            hitBoxesMeeting = self.getHitBoxesMeetingPosition(position)
            for hBox in hitBoxesMeeting:
                entityIds.append(hBox.ownerId)
        return entityIds

    def addEntity(self, _entity):
        for gEntity in self.entities:
            if _entity.id == gEntity.id:
                print("could not add entity with id %i because already existing" % gEntity.id)
                return False

        self.entities.append(_entity)
        return True

    def removeEntity(self, _id):
        for i, gEntity in enumerate(self.entities):
            if _id == gEntity.id:
                self.entities.pop(i)
                return True
        
        print("could not find entity to remove with id %i" % gEntity.id)
        return False

    def getEntity(self, _id):
        for gEntity in self.entities:
            if _id == gEntity.id:
                return gEntity
        return None

    def update(self):
        # run update of entities
        if (time.time() - self.lastTickTime) > (1/self.ticksPerSecond):
            self.lastTickTime = time.time()
            for gEntity in self.entities:
                gEntity.update(self)
            
        # apply physics timely
        timePassed = time.time() - self.lastUpdateTime
        self.lastUpdateTime = time.time()
        for gEntity in self.entities:
            if gEntity.physics2d != None and not gEntity.physics2d.fixed:
                gEntity.position += gEntity.velocity * timePassed
        return

# The renderer class (opencv for ease)
class RendererCv:
    def __init__(self, _windowShape=Vec2d(720, 1020)):
        self.windowShape = _windowShape                                         # the size of the window/ image to draw
        self.baseFrame = np.zeros(self.windowShape.asTuple(True), np.uint8)     # a default image corresponding the window sizes
        self.lastFrame = self.baseFrame                                         # the frame to be presented                                     
        self.keyBuffer = [''] * 5                                              # currently pressed keys, a maximum of 10
        self.backBuffer = []                                                    # the images that are ready to be presented
    
    def show(self):
        # show the image
        if len(self.backBuffer) != 0:
            self.lastFrame = self.backBuffer.pop(0)
 
        cv2.imshow("Window", self.lastFrame)

    def update(self, _scene):
        # update input
        key = cv2.waitKey(1) & 0xFF
        self.keyBuffer.append(key)
        self.keyBuffer.pop(0)

        # draw the entities
        newFrame = self.baseFrame.copy()
        for gEntity in _scene.entities:
            for hBox in gEntity.hitBoxes:
                leftTop, rightTop, leftBot, rightBot = hBox.getBoundingRect(gEntity.position)
                cv2.line(newFrame, leftTop.asTuple(True), rightTop.asTuple(True), gEntity.color, 1)
                cv2.line(newFrame, leftTop.asTuple(True), leftBot.asTuple(True), gEntity.color, 1)
                cv2.line(newFrame, rightBot.asTuple(True), rightTop.asTuple(True), gEntity.color, 1)
                cv2.line(newFrame, rightBot.asTuple(True), leftBot.asTuple(True), gEntity.color, 1)
                 
        self.backBuffer.append(newFrame)
        return True


# The controller class
class Engine:
    def __init__(self, _renderer=RendererCv()):
        self.scenes = []                                                        # the scenes that be loaded
        self.currentSceneIndex = -1                                             # the scene to be shown, if -1 nothing is shown and engine stops
        self.renderer = _renderer
        
    def addScene(self, _newScene, _setAsCurrentScene=False):
        self.scenes.append(_newScene)
        scene_index = len(self.scenes) - 1
        if _setAsCurrentScene:
            self.currentSceneIndex = scene_index
        return scene_index

    def checkKeyPress(self, _key_str):
        for key in self.renderer.keyBuffer:
            if key == ord(_key_str):
                return True
        return False

    def update(self):
        # ensure scene configured
        if self.currentSceneIndex == -1:
            print("no scene configured...")
            return False

        # check for exit
        if self.checkKeyPress('\x1b'):
            print("exit key pressed...")
            return False    

        # update the scene
        self.scenes[self.currentSceneIndex].update()

        # update the renderer with the new scene
        return self.renderer.update(self.scenes[self.currentSceneIndex])

    def run(self):
        while True:
            if not self.update():
                break
            self.renderer.show()