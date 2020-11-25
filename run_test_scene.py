from PyPhyEngine import Engine, Scene, Entity, EntityPhysics, HitBox, Vec, generateUuid

# init
engine = Engine()

# loading
scene = Scene(_id=generateUuid(), _gravity=Vec(0, 3, 0))

# setup movevable character
character_moveSpeed = Vec(75, 300, 75)
jumping_timer = 0
def test_char_movement_callback(_scene, _entity): # executed 1000 times a second
    global jumping_timer
    # apply movement input
    if engine.checkKeyPress('a'):
        if _entity.velocity.x > 0 - _entity.physics.maxVelocity.x:
            _entity.velocity.x -= character_moveSpeed.x
    
    if engine.checkKeyPress('d'):       
        if _entity.velocity.x < _entity.physics.maxVelocity.x:
            _entity.velocity.x += character_moveSpeed.x
    
    if engine.checkKeyPress('w') and _entity.blockedDown and jumping_timer == 0:    
        _entity.velocity.y -= character_moveSpeed.y
        jumping_timer = 15

    if jumping_timer > 0:
        jumping_timer -= 1


# create the character object with physics
test_char_physics = EntityPhysics(_fixed=False, _maxVelocity=Vec(250, 1000, 250))
test_char = Entity(_name="test_character", _id=generateUuid(), _position=Vec(0, 0, 0), _physics=test_char_physics, _updateCallBack=test_char_movement_callback)
test_char.createHitBox(Vec(20, 40, 20), Vec(0, 0, 0), _name="torso")
test_char.createHitBox(Vec(10, 15, 20), Vec(-10, 25, 0), _name="feetl")
test_char.createHitBox(Vec(10, 15, 20), Vec(10, 25, 0), _name="feetr")
test_char.createHitBox(Vec(20, 10, 20), Vec(-20, -20, 0), _name="handl")
test_char.createHitBox(Vec(20, 10, 20), Vec(20, -20, 0), _name="handr")
test_char.createHitBox(Vec(15, 20, 20), Vec(0, -30, 0), _name="head")

# create the ground
fixed_obj_physics = EntityPhysics( _fixed=True, _friction=Vec(3, 0, 3))
ground_obj = Entity(_name="ground", _id=generateUuid(), _position=Vec(0, 300, 0), _physics=fixed_obj_physics)
ground_obj.createHitBox(Vec(600, 20, 600))

# create a box using same object physics as ground
box_obj1 = Entity(_name="box1", _id=generateUuid(), _position=Vec(0, 150, 0), _physics=fixed_obj_physics)
box_obj1.createHitBox(Vec(100, 100, 100))

beam_obj1 = Entity(_name="beam1", _id=generateUuid(), _position=Vec(-300, 190, 0), _physics=fixed_obj_physics)
beam_obj1.createHitBox(Vec(300, 10, 100), Vec(0,0,0), Vec(0,0,1))

# add objects to scene and configure as current scene
scene.addEntity(ground_obj)
scene.addEntity(test_char)
scene.addEntity(box_obj1)
scene.addEntity(beam_obj1)
engine.addScene(scene, True)

# run
engine.run()