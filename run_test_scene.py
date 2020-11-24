from PyPhyEngine import Engine, Scene2d, Entity2d, EntityPhysics2d, HitBox2d, Vec2d, generateUuid

# init
engine = Engine()

# loading
scene = Scene2d(_id=generateUuid(), _gravity=Vec2d(0, 3))

# setup movevable character
character_moveSpeed = Vec2d(75, 300)
jumping_timer = 0
def test_char_movement_callback(_scene, _entity): # executed 1000 times a second
    global jumping_timer
    # apply movement input
    if engine.checkKeyPress('a'):
        if _entity.velocity.x > 0 - _entity.physics2d.maxVelocity.x:
            _entity.velocity.x -= character_moveSpeed.x
    
    if engine.checkKeyPress('d'):       
        if _entity.velocity.x < _entity.physics2d.maxVelocity.x:
            _entity.velocity.x += character_moveSpeed.x
    
    if engine.checkKeyPress('w') and _entity.blockedDown and jumping_timer == 0:    
        _entity.velocity.y -= character_moveSpeed.y
        jumping_timer = 15

    if jumping_timer > 0:
        jumping_timer -= 1


# create the character object with physics
test_char_physics = EntityPhysics2d(_fixed=False, _maxVelocity=Vec2d(250, 1000))
test_char = Entity2d(_name="test_character", _id=generateUuid(), _position=Vec2d(510, 360), _physics2d=test_char_physics, _updateCallBack=test_char_movement_callback)
test_char.createHitBox(Vec2d(20, 40), Vec2d(0, 0), _name="torso")
test_char.createHitBox(Vec2d(10, 15), Vec2d(-10, 25), _name="feetl")
test_char.createHitBox(Vec2d(10, 15), Vec2d(10, 25), _name="feetr")
test_char.createHitBox(Vec2d(20, 10), Vec2d(-20, -20), _name="handl")
test_char.createHitBox(Vec2d(20, 10), Vec2d(20, -20), _name="handr")
test_char.createHitBox(Vec2d(15, 20), Vec2d(0, -30), _name="head")

# create the ground
fixed_obj_physics = EntityPhysics2d( _fixed=True, _friction=Vec2d(3, 0))
ground_obj = Entity2d(_name="ground", _id=generateUuid(), _position=Vec2d(500, 700), _physics2d=fixed_obj_physics)
ground_obj.createHitBox(Vec2d(600, 20))

# create a box using same object physics as ground
box_obj1 = Entity2d(_name="box1", _id=generateUuid(), _position=Vec2d(500, 500), _physics2d=fixed_obj_physics)
box_obj1.createHitBox(Vec2d(100, 100))

beam_obj1 = Entity2d(_name="beam1", _id=generateUuid(), _position=Vec2d(200, 550), _physics2d=fixed_obj_physics)
beam_obj1.createHitBox(Vec2d(300, 10), Vec2d(0,0), 1)

# add objects to scene and configure as current scene
scene.addEntity(ground_obj)
scene.addEntity(test_char)
scene.addEntity(box_obj1)
scene.addEntity(beam_obj1)
engine.addScene(scene, True)

# run
engine.run()