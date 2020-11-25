from uuid import uuid1 as generateUuid
import sys
import cv2
import numpy as np
import time
import math

# main data class for positioning
class Vec:
    def __init__(self, _x=0, _y=0, _z=0):
        self.x = _x
        self.y = _y
        self.z = _z

    def getRotatedVecZ(self, _angle=0):
        newX = math.cos(_angle) * self.x - math.sin(_angle) * self.y
        newY = math.sin(_angle) * self.x + math.cos(_angle) * self.y
        newZ = self.z
        return Vec(newX, newY, newZ)
    
    def getRotatedVecY(self, _angle=0):
        newX = math.cos(_angle) * self.x + math.sin(_angle) * self.z
        newY = self.y
        newZ = math.sin(_angle) * (-self.x) + math.cos(_angle) * self.z
        return Vec(newX, newY, newZ)

    def getRotatedVecX(self, _angle=0):
        newX = self.x
        newY = math.cos(_angle) * self.y - math.sin(_angle) * self.z
        newZ = math.sin(_angle) * self.y + math.cos(_angle) * self.z
        return Vec(newX, newY, newZ)

    def getRotatedVec(self, _rotationX, _rotationY, _rotationZ):
        return self.getRotatedVecZ(_rotationZ).getRotatedVecY(_rotationY).getRotatedVecX(_rotationX)

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
    
    def __add__(self, _vec):
        return Vec(self.x + _vec.x, self.y + _vec.y, self.z + _vec.z)

    def __sub__(self, _vec):
        return Vec(self.x - _vec.x, self.y - _vec.y, self.z - _vec.z)

    def __truediv__(self, _num):
        return Vec(self.x/_num, self.y/_num, self.z/_num)
    
    def __mul__(self, _num):
        return Vec(self.x * _num, self.y * _num, self.z * _num)

    def __str__(self):
        return str(self.x) + "," + str(self.y) + "," + str(self.z)

# utility functions for Vec
def InterpolatePositionsBetweenPoints(_vec1, _vec2, _points=5):
    positions = []
    step_x = (_vec2.x - _vec1.x) / _points
    step_y = (_vec2.y - _vec1.y) / _points
    step_z = (_vec2.z - _vec1.z) / _points
    for n in range(1, _points):
        positions.append(_vec1 + Vec(step_x * n, step_y * n, step_z * n))
    return positions

def CalcTriangleSignArea(_pos1, _pos2, _pos3):
    return (_pos1.x - _pos3.x) * (_pos2.y - _pos3.y) - (_pos2.x - _pos3.x) * (_pos1.y - _pos3.y)

def IsPositionWithinTriangle(_position, _trianglePos1, _trianglePos2, _trianglePos3):
    a1 = CalcTriangleSignArea(_position, _trianglePos1, _trianglePos2)
    a2 = CalcTriangleSignArea(_position, _trianglePos2, _trianglePos3)
    a3 = CalcTriangleSignArea(_position, _trianglePos3, _trianglePos1)
    return (a1 < 0) == (a2 < 0) and (a2 < 0) == (a3 < 0)

# A hitbox/rectangle used to detect collision
class HitBox:
    def __init__(self, _name, _ownerId, _shape, _relativePos=Vec(0,0,0), _relativeRot=Vec(0,0,0)):
        self.ownerId = _ownerId                 # id of entity
        self.shape = _shape                     # the width and height of the hitbox
        self.relativePos = _relativePos         # the position of the hitbox relative to origin (0,0)
        self.relativeRot = _relativeRot
        self.name = _name                       # the name of the hitbox
        self.halfExtents = (self.shape/2)

    def editHitBox(self, _relativePos=None, _relativeRot=None, _shape=None):
        if _relativePos != None:
            self.relativePos = _relativePos
        if _relativeRot != None:
            self.relativeRot = _relativePos
        if _shape != None:
            self.shape = _shape

    def getBoundingRect(self, _worldPosition=Vec(0,0,0), _worldRotation=Vec(0,0,0), _offset=Vec(0,0,0)):
        self.halfExtents = (self.shape/2)

        f_leftTop = self.relativePos - self.halfExtents - _offset
        b_rightBot = self.relativePos + self.halfExtents + _offset

        f_rightTop = Vec(b_rightBot.x, f_leftTop.y, f_leftTop.z)
        f_leftBot = Vec(f_leftTop.x, b_rightBot.y, f_leftTop.z)
        f_rightBot = Vec(b_rightBot.x, b_rightBot.y, f_leftTop.z)

        b_leftTop = Vec(f_leftTop.x, f_leftTop.y, b_rightBot.z)
        b_rightTop = Vec(b_rightBot.x, f_leftTop.y, b_rightBot.z)
        b_leftBot = Vec(f_leftTop.x, b_rightBot.y, b_rightBot.z)

        rotation = self.relativeRot + _worldRotation
        f_leftTop = f_leftTop.getRotatedVec(rotation.x, rotation.y, rotation.z) + _worldPosition
        f_rightTop = f_rightTop.getRotatedVec(rotation.x, rotation.y, rotation.z) + _worldPosition
        f_leftBot = f_leftBot.getRotatedVec(rotation.x, rotation.y, rotation.z) + _worldPosition
        f_rightBot = f_rightBot.getRotatedVec(rotation.x, rotation.y, rotation.z) + _worldPosition

        b_leftTop = b_leftTop.getRotatedVec(rotation.x, rotation.y, rotation.z) + _worldPosition
        b_rightTop = b_rightTop.getRotatedVec(rotation.x, rotation.y, rotation.z) + _worldPosition
        b_leftBot = b_leftBot.getRotatedVec(rotation.x, rotation.y, rotation.z) + _worldPosition
        b_rightBot = b_rightBot.getRotatedVec(rotation.x, rotation.y, rotation.z) + _worldPosition

        return [f_leftTop, f_rightTop, f_leftBot, f_rightBot, b_leftTop, b_rightTop, b_leftBot, b_rightBot]

# a Entity, holding basic information about the positioning of the entity and how it interacts with the world
class Entity:
    def __init__(self, _name, _id, _position=Vec(0,0,0), _rotation=Vec(0,0,0), _physics=None, _updateCallBack=None):
        self.name = _name
        self.id = _id 

        self.hitBoxes = []
        self.position = _position
        self.rotation = _rotation
        self.velocity = Vec(0,0,0)             # the velocity to be applied on the position (pixels per second), only applied when a non fixed physics entity is existing
        
        self.physics = _physics            # the entity holding information about the physics (requires a member function update(_scene, _entity) function to work)
        self.blockedUp = False                 # applies restraints to the velocity
        self.blockedLeft = False
        self.blockedRight = False
        self.blockedDown = False
        self.blockedFront = False
        self.blockedBack = False

        self.updateCallBack = _updateCallBack   # a function to call after apply basic physics, is also called without having a physics if set

        self.color = (255,0,0) 
        
    def createHitBox(self, _shape, _relativePos=Vec(0,0,0), _relativeRot=Vec(0,0,0), _name="HitBox"):
        name = _name
        if _name == "HitBox":
            name = self.name + "_" + _name + "_" + str(len(self.hitBoxes))
        else:
            name = self.name + "_" + "HitBox" + "_" + _name
        self.hitBoxes.append(HitBox(name, self.id, _shape, _relativePos, _relativeRot))
            
    def update(self, _scene):
        # pre update
        if self.physics != None:
            self.physics.preUpdate(_scene, self)

        # callback user update
        if self.updateCallBack != None:
            self.updateCallBack(_scene, self)

        # update physics
        if self.physics != None:
            self.physics.afterUpdate(_scene, self)
        return

    def getCollisionPositions(self, _points=5, _pixelOffset=Vec(3,3,3)):
        # Interpolates outer edges of all hitboxes and returns them as lists
        bottomPositions = []
        topPositions = []
        leftPositions = []
        rightPositions = []
        frontPositions = []
        backPositions = []
        for hBox in self.hitBoxes:
            f_leftTop, f_rightTop, f_leftBot, f_rightBot, b_leftTop, b_rightTop, b_leftBot, b_rightBot = hBox.getBoundingRect(self.position, self.rotation, _pixelOffset)
            
            # bottom collision points
            bottomPositions += InterpolatePositionsBetweenPoints(f_leftBot, f_rightBot)
            bottomPositions += InterpolatePositionsBetweenPoints(f_leftBot, f_leftBot)
            bottomPositions += InterpolatePositionsBetweenPoints(f_rightBot, b_rightBot)
            bottomPositions += InterpolatePositionsBetweenPoints(b_rightBot, b_leftBot)

            # top collision points
            topPositions += InterpolatePositionsBetweenPoints(f_leftTop, f_rightTop)
            topPositions += InterpolatePositionsBetweenPoints(f_leftTop, f_leftTop)
            topPositions += InterpolatePositionsBetweenPoints(f_rightTop, b_rightTop)
            topPositions += InterpolatePositionsBetweenPoints(b_rightTop, b_leftTop)

            # left
            leftPositions += InterpolatePositionsBetweenPoints(f_leftTop, f_leftBot)
            leftPositions += InterpolatePositionsBetweenPoints(b_leftTop, b_leftBot)

            # right positions
            rightPositions += InterpolatePositionsBetweenPoints(f_rightTop, f_rightBot)        
            rightPositions += InterpolatePositionsBetweenPoints(b_leftTop, b_leftBot)

            # front positions
            frontPositions += InterpolatePositionsBetweenPoints(f_leftTop, f_leftBot)
            frontPositions += InterpolatePositionsBetweenPoints(f_rightTop, f_rightBot)

            # back positions
            backPositions += InterpolatePositionsBetweenPoints(b_leftTop, b_leftBot)
            backPositions += InterpolatePositionsBetweenPoints(b_rightTop, b_rightBot)

        return [bottomPositions,topPositions,leftPositions,rightPositions,frontPositions,backPositions]

# A class that can be use to enable hitbox detection for entities and holds properties with the regards to interactions done by or to ther entities
class EntityPhysics:
    def __init__(self, _fixed=True, _maxVelocity=Vec(1000, 1000, 1000), _friction=Vec(0,0,0)):    
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
            if meetingEntity.physics != None and (meetingEntity.physics.fixed and _entityMeetingIsFixed) or (not meetingEntity.physics.fixed and not _entityMeetingIsFixed):
                return (True, meetingEntity)
        return (False, None)

    def preUpdate(self, _scene, _entity):
        # skip if fixed entity 
        if self.fixed:
            return

        # apply gravity
        _entity.velocity += _scene.gravity

        # get collision points to check on
        bottomPositions,topPositions,leftPositions,rightPositions,frontPositions,backPositions = _entity.getCollisionPositions()

        # check if touching ground or not and apply corresponding physics
        downFound, ground = self.getFirstMeetingPhysicsEntity(_scene, _entity, bottomPositions, True)
        if downFound:
            _entity.blockedDown = True

            if _entity.velocity.x < 0:
                _entity.velocity.x += ground.physics.friction.x
                if _entity.velocity.x > 0:
                    _entity.velocity.x = 0
                    
            elif _entity.velocity.x > 0:
                _entity.velocity.x -= ground.physics.friction.x
                if _entity.velocity.x < 0:
                    _entity.velocity.x = 0

            if _entity.velocity.y < 0:
                _entity.velocity.y += ground.physics.friction.y
                if _entity.velocity.y > 0:
                    _entity.velocity.y = 0
                    
            elif _entity.velocity.y > 0:
                _entity.velocity.y -= ground.physics.friction.y
                if _entity.velocity.y < 0:
                    _entity.velocity.y = 0

            if _entity.velocity.z < 0:
                _entity.velocity.z += ground.physics.friction.z
                if _entity.velocity.z > 0:
                    _entity.velocity.z = 0
                    
            elif _entity.velocity.z > 0:
                _entity.velocity.z -= ground.physics.friction.z
                if _entity.velocity.z < 0:
                    _entity.velocity.z = 0      

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

        # check if touching front
        frontFound = self.getFirstMeetingPhysicsEntity(_scene, _entity, frontPositions, True)[0]
        if frontFound:
            _entity.blockedFront = True

        if _entity.blockedFront and not frontFound:
            _entity.blockedFront = False

        # check if touching back
        backFound = self.getFirstMeetingPhysicsEntity(_scene, _entity, backPositions, True)[0]
        if backFound:
            _entity.blockedBack = True

        if _entity.blockedBack and not backFound:
            _entity.blockedBack = False


    def afterUpdate(self, _scene, _entity):
        # skip if fixed entity 
        if self.fixed:
            return

        # apply restraints <TODO> apply the restraints based on the direction of the entity is facing
        if _entity.blockedDown and _entity.velocity.y > 0:
            _entity.velocity.y = 0

        if _entity.blockedUp and _entity.velocity.y < 0:
            _entity.velocity.y = 0

        if _entity.blockedLeft and _entity.velocity.x < 0:
            _entity.velocity.x = 0

        if _entity.blockedRight and _entity.velocity.x > 0:
            _entity.velocity.x = 0

        if _entity.blockedBack and _entity.velocity.z > 0:
            _entity.velocity.z = 0

        if _entity.blockedFront and _entity.velocity.z < 0:
            _entity.velocity.z = 0

        # limit velocity <TODO, apply based on direction and norm>
        if _entity.velocity.y > self.maxVelocity.y:
            _entity.velocity.y = self.maxVelocity.y
        if _entity.velocity.y < 0 - self.maxVelocity.y:
            _entity.velocity.y = 0 - self.maxVelocity.y

        if _entity.velocity.x > self.maxVelocity.x:
            _entity.velocity.x = self.maxVelocity.x
        if _entity.velocity.x < 0 - self.maxVelocity.x:
            _entity.velocity.x = 0 - self.maxVelocity.x

        if _entity.velocity.z > self.maxVelocity.z:
            _entity.velocity.z = self.maxVelocity.z
        if _entity.velocity.z < 0 - self.maxVelocity.z:
            _entity.velocity.z = 0 - self.maxVelocity.z 

        return

# The
class Scene:
    def __init__(self, _id, _gravity=Vec(0, 1, 0), _ticksPerSecond=1000):
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
                    # 

                    continue
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
            if gEntity.physics != None and not gEntity.physics.fixed:
                gEntity.position += gEntity.velocity * timePassed
        return

# The renderer class (opencv for ease)
class RendererCv:
    def __init__(self, _2d=False, _windowShape=Vec(1020, 720)):
        self.windowShape = _windowShape                                         # the size of the window/ image to draw
        self.baseFrame = np.zeros((self.windowShape.y, self.windowShape.x), np.uint8)     # a default image corresponding the window sizes
        self.lastFrame = self.baseFrame                                         # the frame to be presented                                     
        self.keyBuffer = [''] * 5                                              # currently pressed keys, a maximum of 10
        self.backBuffer = []                                                    # the images that are ready to be presented
        self.twoD = _2d
    
    def transformPositionToViewPoint(self, _position):
        position = _position

        # apply aspectratio
        position.y *= self.windowShape.y/self.windowShape.x

        # apply perspective transformation in case of 3D, assuming view will never rotate but rather the world
        if not self.twoD:
            if position.z <= 0:
                position /= -(position.z/100)
            else:
                position *= (position.z * 100)
        
        # move coordinates to window space
        position += (self.windowShape/2)
        point = (int(position.x), int(position.y))
        return point

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
                f_leftTop, f_rightTop, f_leftBot, f_rightBot, b_leftTop, b_rightTop, b_leftBot, b_rightBot = hBox.getBoundingRect(gEntity.position)

                p_flT = self.transformPositionToViewPoint(f_leftTop)
                p_frT = self.transformPositionToViewPoint(f_rightTop)
                p_frB = self.transformPositionToViewPoint(f_rightBot)
                p_flB = self.transformPositionToViewPoint(f_leftBot)

                p_blT = self.transformPositionToViewPoint(b_leftTop)
                p_brT = self.transformPositionToViewPoint(b_rightTop)
                p_brB = self.transformPositionToViewPoint(b_rightBot)
                p_blB = self.transformPositionToViewPoint(b_leftBot)

                # draw front
                cv2.line(newFrame, p_flT, p_frT, gEntity.color, 1)
                cv2.line(newFrame, p_flT, p_flB, gEntity.color, 1)
                cv2.line(newFrame, p_frB, p_frT, gEntity.color, 1)
                cv2.line(newFrame, p_flB, p_frB, gEntity.color, 1)

                # draw back
                cv2.line(newFrame, p_blT, p_brT, gEntity.color, 1)
                cv2.line(newFrame, p_blT, p_blB, gEntity.color, 1)
                cv2.line(newFrame, p_brB, p_brT, gEntity.color, 1)
                cv2.line(newFrame, p_blB, p_brB, gEntity.color, 1)

                # draw sides
                cv2.line(newFrame, p_flT, p_blT, gEntity.color, 1)
                cv2.line(newFrame, p_frT, p_brT, gEntity.color, 1)
                cv2.line(newFrame, p_flB, p_blB, gEntity.color, 1)
                cv2.line(newFrame, p_frB, p_brB, gEntity.color, 1)

                # <TODO draw z axis in smaller scale>
                 
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