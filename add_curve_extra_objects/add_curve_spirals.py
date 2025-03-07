'''bl_info = {
    "name": "Spirals",
    "description": "Make spirals",
    "author": "Alejandro Omar Chocano Vasquez",
    "version": (1, 2),
    "blender": (2, 62, 0),
    "location": "View3D > Add > Curve",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.4/Py/"
                "Scripts/Object/Spirals",
    "tracker_url": "http://alexvaqp.googlepages.com?"
                   "func=detail&aid=<number>",
    "category": "Add Curve",
}
'''
from __future__ import division
from __future__ import absolute_import
import bpy, time
from bpy.props import *
from math import sin, cos, pi, exp
from bpy_extras.object_utils import AddObjectHelper, object_data_add

#make normal spiral
#-----------------------------------------------------------------------------
def make_spiral(props, context):                  #archemedian and logarithmic can be plottet in zylindrical coordinates
    #if props.spiral_type != 1 and props.spiral_type != 2:
    #    return None

    #INPUT: turns->degree->max_phi, steps, direction
    #Initialise Polar Coordinate Enviroment
    #-------------------------------
    props.degree = 360*props.turns                #If you want to make the slider for degree
    steps = props.steps * props.turns             #props.steps[per turn] -> steps[for the whole spiral]
    props.z_scale = props.dif_z * props.turns
    
    max_phi  = pi*props.degree/180                #max angle in radian
    step_phi = max_phi/steps                      #angle in radians between two vertices
    if props.spiral_direction == 1:
        step_phi *= -1                            #flip direction
        max_phi *= -1
    step_z   = props.z_scale/(steps-1)            #z increase in one step
    
    verts = []
    verts.extend([props.radius,0,0,1])
    
    cur_phi = 0
    cur_z   = 0
    #-------------------------------

    #Archemedean: dif_radius, radius
    cur_rad = props.radius
    step_rad = props.dif_radius/(steps * 360/props.degree)        #radius increase per angle for archemedean spiral| (steps * 360/props.degree)...Steps needed for 360 deg
    #Logarithmic: radius, B_force, ang_div, dif_z
    
    #print("max_phi:",max_phi,"step_phi:",step_phi,"step_rad:",step_rad,"step_z:",step_z)
    while abs(cur_phi) <= abs(max_phi):
        cur_phi += step_phi
        cur_z   += step_z
        
        #-------------------------------
        if props.spiral_type == 1:
            cur_rad += step_rad
        if props.spiral_type == 2:
            #r = a*e^{|theta| * b}
            cur_rad = props.radius * pow(props.B_force, abs(cur_phi)) 
        #-------------------------------
    
        px = cur_rad * cos(cur_phi)
        py = cur_rad * sin(cur_phi)
        verts.extend( [px,py,cur_z,1] )

    return verts


#make Spheric spiral
#-----------------------------------------------------------------------------
def make_spiral_spheric(props, context):
    #INPUT: turns, steps[per turn], radius
    #use spherical Coordinates
    step_phi = (2*pi) / props.steps               #Step of angle in radians for one turn
    steps = props.steps * props.turns             #props.steps[per turn] -> steps[for the whole spiral]
    
    max_phi  = 2*pi*props.turns                   #max angle in radian
    step_phi = max_phi/steps                      #angle in radians between two vertices
    if props.spiral_direction == 1:               #flip direction
        step_phi *= -1
        max_phi *= -1
    step_theta = pi / (steps-1)                   #theta increase in one step (pi == 180 deg)

    verts = []
    verts.extend([0,0,-props.radius,1])           #First vertex at south pole

    #cur_rad = props.radius = CONST

    cur_phi = 0
    cur_theta = -pi/2                             #Beginning at south pole

    while abs(cur_phi) <= abs(max_phi):
        #Coordinate Transformation sphere->rect
        px = props.radius * cos(cur_theta) * cos(cur_phi)
        py = props.radius * cos(cur_theta) * sin(cur_phi)
        pz = props.radius * sin(cur_theta)

        verts.extend([px,py,pz,1])
        cur_theta += step_theta
        cur_phi += step_phi

    return verts

#make torus spiral
#-----------------------------------------------------------------------------

def make_spiral_torus(props, context):
    #INPUT: turns, steps, inner_radius, curves_number, mul_height, dif_inner_radius, cycles
    max_phi  = 2*pi*props.turns * props.cycles    #max angle in radian
    step_phi = 2*pi/props.steps                   #Step of angle in radians between two vertices
    if props.spiral_direction == 1:               #flip direction
        step_phi *= -1
        max_phi *= -1
    step_theta = (2*pi / props.turns) / props.steps
    step_rad = props.dif_radius / (props.steps * props.turns)
    step_inner_rad = props.dif_inner_radius / props.steps
    step_z = props.dif_z / (props.steps * props.turns)

    verts = []
    
    cur_phi = 0                                   #Inner Ring Radius Angle
    cur_theta = 0                                 #Ring Radius Angle
    cur_rad = props.radius
    cur_inner_rad = props.inner_radius
    cur_z = 0
    n_cycle = 0
    
    while abs(cur_phi) <= abs(max_phi):
        #Torus Coordinates -> Rect
        px = ( cur_rad + cur_inner_rad * cos(cur_phi) ) * cos(props.curves_number * cur_theta)
        py = ( cur_rad + cur_inner_rad * cos(cur_phi) ) * sin(props.curves_number * cur_theta)
        pz = cur_inner_rad * sin(cur_phi) + cur_z

        verts.extend([px,py,pz,1])

        if props.touch == True and cur_phi >= n_cycle * 2*pi:
            step_z = ( (n_cycle+1) * props.dif_inner_radius + props.inner_radius ) * 2 / (props.steps * props.turns)
            n_cycle += 1

        cur_theta += step_theta
        cur_phi += step_phi
        cur_rad += step_rad
        cur_inner_rad += step_inner_rad
        cur_z += step_z

    return verts
#-----------------------------------------------------------------------------

def draw_curve(props, context):
    if props.spiral_type == 1:
        verts = make_spiral(props, context)
    if props.spiral_type == 2:
        verts = make_spiral(props, context)
    if props.spiral_type == 3:
        verts = make_spiral_spheric(props, context)
    if props.spiral_type == 4:
        verts = make_spiral_torus(props, context)
    
    curve_data = bpy.data.curves.new(name='Spiral', type='CURVE')
    curve_data.dimensions = '3D'
    
    if props.curve_type == 0:
        spline = curve_data.splines.new(type='POLY')
    elif props.curve_type == 1:
        spline = curve_data.splines.new(type='NURBS')
    
    spline.points.add( len(verts)*0.25-1 )                          #Add only one quarter of points as elements in verts, because verts looks like: "x,y,z,?,x,y,z,?,x,..."
    spline.points.foreach_set('co', verts)
#    new_obj = object_data_add(bpy.context, curve_data)
    new_obj = object_data_add(context, curve_data)   

class spirals(bpy.types.Operator):
    bl_idname = "curve.spirals"
    bl_label = "Spirals"
    bl_options = set(['REGISTER','UNDO', 'PRESET'])            #UNDO needed for operator redo and therefore also to let the addobjecthelp appear!!!
    bl_description = "adds different types of spirals"

    spiral_type = IntProperty(default=1, min=1, max=4, description="1:archemedian, 2:logarithmic, 3:spheric, 4:torus")
    curve_type = IntProperty(default=0, min=0, max=1, description="0:Poly, 1:Nurb")
    spiral_direction = IntProperty(default=0, min=0, max=1, description="0:counter-clockwise, 1:clockwise")
    
    turns = IntProperty(default=1, min=1, max=1000, description="Length of Spiral in 360 deg")
    steps = IntProperty(default=24, min=2, max=1000, description="Number of Vertices per turn")

    
    radius = FloatProperty(default=1.00, min=0.00, max=100.00, description="radius for first turn")
    dif_z = FloatProperty(default=0, min=-10.00, max=100.00, description="increase in z axis per turn")            #needed for 1 and 2 spiral_type
    #ARCHMEDEAN variables
    dif_radius = FloatProperty(default=0.00, min=-50.00, max=50.00, description="radius increment in each turn")        #step between turns(one turn equals 360 deg)
    #LOG variables 
    B_force = FloatProperty(default=1.00, min=0.00, max=30.00, description="factor of exponent")
    #TORUS variables
    inner_radius = FloatProperty(default=0.20, min=0.00, max=100, description="Inner Radius of Torus")
    dif_inner_radius = FloatProperty(default=0, min=-10, max=100, description="Increase of inner Radius per Cycle")
    dif_radius = FloatProperty(default=0, min=-10, max=100, description="Increase of Torus Radius per Cycle")
    cycles = FloatProperty(default=1, min=0.00, max=1000, description="Number of Cycles")
    curves_number = IntProperty(default=1, min=1, max=400, description="Number of curves of spiral")
    touch = BoolProperty(default=False, description="No empty spaces between cycles")

    def draw(self, context):                #Function used by Blender to draw the menu
        layout = self.layout
        layout.prop(self, 'spiral_type', text="Spiral Type")
        layout.prop(self, 'curve_type', text="Curve Type")
        layout.prop(self, 'spiral_direction', text="Spiral Direction")
        
        layout.label(text="Spiral Parameters:")
        layout.prop(self, 'turns', text = "Turns")
        layout.prop(self, 'steps', text = "Steps")

        box = layout.box()
        if self.spiral_type == 1:
            box.prop(self, 'dif_radius', text = "Radius Growth")
            box.prop(self, 'radius', text = "Radius")
            box.prop(self, 'dif_z', text = "Height")
        if self.spiral_type == 2:
            box.prop(self, 'radius', text = "Radius")
            box.prop(self, 'B_force', text = "Expansion Force")
            box.prop(self, 'dif_z', text = "Height")
        if self.spiral_type == 3:
            box.prop(self, 'radius', text = "Radius")
        if self.spiral_type == 4:
            box.prop(self, 'cycles', text = "Number of Cycles")
            if self.dif_inner_radius == 0 and self.dif_z == 0:
                self.cycles = 1
            box.prop(self, 'radius', text = "Radius")
            if self.dif_z == 0:
                box.prop(self, 'dif_z', text = "Height per Cycle")
            else:
                box2 = box.box()
                box2.prop(self, 'dif_z', text = "Height per Cycle")
                box2.prop(self, 'touch', text = "Make Snail")
            box.prop(self, 'inner_radius', text = "Inner Radius")
            box.prop(self, 'curves_number', text = "Curves Number")
            box.prop(self, 'dif_radius', text = "Increase of Torus Radius")
            box.prop(self, 'dif_inner_radius', text = "Increase of Inner Radius")

    @classmethod
    def poll(cls, context):                            #method called by blender to check if the operator can be run
        return context.scene != None
    def execute(self, context):
        time_start = time.time()
        draw_curve(self, context)
        print "Drawing Spiral Finished: %.4f sec", time.time() - time_start
        return set(['FINISHED'])
