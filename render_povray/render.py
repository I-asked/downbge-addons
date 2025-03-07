# ***** BEGIN GPL LICENSE BLOCK *****
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# #**** END GPL LICENSE BLOCK #****

# <pep8 compliant>

from __future__ import division
from __future__ import absolute_import
import bpy
import subprocess
import os
import sys
import time
from math import atan, pi, degrees, sqrt
import re
import random
import platform#
import subprocess#
from bpy.types import(Operator)#all added for render preview
from . import df3 # for smoke rendering
from io import open
from itertools import izip
##############################SF###########################
##############find image texture
def imageFormat(imgF):
    ext = {
        'JPG': "jpeg",
        'JPEG': "jpeg",
        'GIF': "gif",
        'TGA': "tga",
        'IFF': "iff",
        'PPM': "ppm",
        'PNG': "png",
        'SYS': "sys",
        'TIFF': "tiff",
        'TIF': "tiff",
        'EXR': "exr",
        'HDR': "hdr",
    }.get(os.path.splitext(imgF)[-1].upper(), "")

    if not ext:
        print " WARNING: texture image format not supported "

    return ext


def imgMap(ts):
    image_map = ""
    if ts.mapping == 'FLAT':
        image_map = "map_type 0 "
    elif ts.mapping == 'SPHERE':
        image_map = "map_type 1 " 
    elif ts.mapping == 'TUBE':
        image_map = "map_type 2 "

    ## map_type 3 and 4 in development (?)
    ## for POV-Ray, currently they just seem to default back to Flat (type 0)
    #elif ts.mapping=="?":
    #    image_map = " map_type 3 "
    #elif ts.mapping=="?":
    #    image_map = " map_type 4 "
    if ts.texture.use_interpolation:
        image_map += " interpolate 2 "
    if ts.texture.extension == 'CLIP':
        image_map += " once "
    #image_map += "}"
    #if ts.mapping=='CUBE':
    #    image_map+= "warp { cubic } rotate <-90,0,180>"
    # no direct cube type mapping. Though this should work in POV 3.7
    # it doesn't give that good results(best suited to environment maps?)
    #if image_map == "":
    #    print(" No texture image  found ")
    return image_map


def imgMapTransforms(ts):
    # XXX TODO: unchecked textures give error of variable referenced before assignment XXX
    # POV-Ray "scale" is not a number of repetitions factor, but ,its
    # inverse, a standard scale factor.
    # 0.5 Offset is needed relatively to scale because center of the
    # scale is 0.5,0.5 in blender and 0,0 in POV
    image_map_transforms = ""
    image_map_transforms = ("scale <%.4g,%.4g,%.4g> translate <%.4g,%.4g,%.4g>" % \
                  ( 1.0 / ts.scale.x,
                  1.0 / ts.scale.y,
                  1.0 / ts.scale.z,
                  0.5-(0.5/ts.scale.x) - (ts.offset.x),
                  0.5-(0.5/ts.scale.y) - (ts.offset.y),
                  ts.offset.z))    
    # image_map_transforms = (" translate <-0.5,-0.5,0.0> scale <%.4g,%.4g,%.4g> translate <%.4g,%.4g,%.4g>" % \
                  # ( 1.0 / ts.scale.x,
                  # 1.0 / ts.scale.y,
                  # 1.0 / ts.scale.z,
                  # (0.5 / ts.scale.x) + ts.offset.x,
                  # (0.5 / ts.scale.y) + ts.offset.y,
                  # ts.offset.z))
    # image_map_transforms = ("translate <-0.5,-0.5,0> scale <-1,-1,1> * <%.4g,%.4g,%.4g> translate <0.5,0.5,0> + <%.4g,%.4g,%.4g>" % \
                  # (1.0 / ts.scale.x, 
                  # 1.0 / ts.scale.y,
                  # 1.0 / ts.scale.z,
                  # ts.offset.x,
                  # ts.offset.y,
                  # ts.offset.z))
    return image_map_transforms

def imgMapBG(wts):
    image_mapBG = ""
    # texture_coords refers to the mapping of world textures:
    if wts.texture_coords == 'VIEW' or wts.texture_coords == 'GLOBAL':
        image_mapBG = " map_type 0 "
    elif wts.texture_coords == 'ANGMAP':
        image_mapBG = " map_type 1 "
    elif wts.texture_coords == 'TUBE':
        image_mapBG = " map_type 2 "

    if wts.texture.use_interpolation:
        image_mapBG += " interpolate 2 "
    if wts.texture.extension == 'CLIP':
        image_mapBG += " once "
    #image_mapBG += "}"
    #if wts.mapping == 'CUBE':
    #   image_mapBG += "warp { cubic } rotate <-90,0,180>"
    # no direct cube type mapping. Though this should work in POV 3.7
    # it doesn't give that good results(best suited to environment maps?)
    #if image_mapBG == "":
    #    print(" No background texture image  found ")
    return image_mapBG
    
    
def path_image(image):
    return bpy.path.abspath(image.filepath, library=image.library)

# end find image texture
# -----------------------------------------------------------------------------


def string_strip_hyphen(name):
    return name.replace("-", "")


def safety(name, Level):
    # safety string name material
    #
    # Level=1 is for texture with No specular nor Mirror reflection
    # Level=2 is for texture with translation of spec and mir levels
    # for when no map influences them
    # Level=3 is for texture with Maximum Spec and Mirror

    try:
        if int(name) > 0:
            prefix = "shader"
    except:
        prefix = ""
    prefix = "shader_"
    name = string_strip_hyphen(name)
    if Level == 2:
        return prefix + name
    elif Level == 1:
        return prefix + name + "0"  # used for 0 of specular map
    elif Level == 3:
        return prefix + name + "1"  # used for 1 of specular map


##############end safety string name material
##############################EndSF###########################

def is_renderable(ob):
    return (ob.hide_render==False)


def renderable_objects():
    return [ob for ob in bpy.data.objects if is_renderable(ob)]


tabLevel = 0
unpacked_images=[]

workDir = bpy.utils.resource_path('USER')   
previewDir=os.path.join(workDir, "preview")
## Make sure Preview directory exists and is empty
if not os.path.isdir(previewDir):
    os.mkdir(previewDir)
smokePath = os.path.join(previewDir, "smoke.df3")
    
def exportPattern(texture):
    tex=texture
    pat = tex.pov
    PATname = "PAT_%s"%string_strip_hyphen(bpy.path.clean_name(tex.name))
    mappingDif = ("translate <%.4g,%.4g,%.4g> scale <%.4g,%.4g,%.4g>" % \
          (pat.tex_mov_x, pat.tex_mov_y, pat.tex_mov_z,
           1.0 / pat.tex_scale_x, 1.0 / pat.tex_scale_y, 1.0 / pat.tex_scale_z))
    texStrg=""
    def exportColorRamp(texture):
        tex=texture
        pat = tex.pov      
        colRampStrg="color_map {\n"
        numColor=0
        for el in tex.color_ramp.elements:
            numColor+=1
            pos = el.position
            col=el.color
            colR,colG,colB,colA = col[0],col[1],col[2],1-col[3]
            if pat.tex_pattern_type not in set(['checker', 'hexagon', 'square', 'triangular', 'brick']) :
                colRampStrg+="[%.4g color rgbf<%.4g,%.4g,%.4g,%.4g>] \n"%(pos,colR,colG,colB,colA)
            if pat.tex_pattern_type in set(['brick','checker']) and numColor < 3:
                colRampStrg+="color rgbf<%.4g,%.4g,%.4g,%.4g> \n"%(colR,colG,colB,colA)
            if pat.tex_pattern_type == 'hexagon' and numColor < 4 :
                colRampStrg+="color rgbf<%.4g,%.4g,%.4g,%.4g> \n"%(colR,colG,colB,colA)
            if pat.tex_pattern_type == 'square' and numColor < 5 :
                colRampStrg+="color rgbf<%.4g,%.4g,%.4g,%.4g> \n"%(colR,colG,colB,colA)
            if pat.tex_pattern_type == 'triangular' and numColor < 7 :
                colRampStrg+="color rgbf<%.4g,%.4g,%.4g,%.4g> \n"%(colR,colG,colB,colA)
                      
        colRampStrg+="} \n"
        #end color map
        return colRampStrg
    #much work to be done here only defaults translated for now:
    #pov noise_generator 3 means perlin noise
    if pat.tex_pattern_type == 'emulator':
        texStrg+="pigment {\n"
        ####################### EMULATE BLENDER VORONOI TEXTURE ####################
        if tex.type == 'VORONOI':  
            texStrg+="crackle\n"
            texStrg+="    offset %.4g\n"%tex.nabla
            texStrg+="    form <%.4g,%.4g,%.4g>\n"%(tex.weight_1, tex.weight_2, tex.weight_3)
            if tex.distance_metric == 'DISTANCE':
                texStrg+="    metric 2.5\n"          
            if tex.distance_metric == 'DISTANCE_SQUARED':
                texStrg+="    metric 2.5\n"
                texStrg+="    poly_wave 2\n"                
            if tex.distance_metric == 'MINKOVSKY': 
                texStrg+="    metric %s\n"%tex.minkovsky_exponent             
            if tex.distance_metric == 'MINKOVSKY_FOUR': 
                texStrg+="    metric 4\n"
            if tex.distance_metric == 'MINKOVSKY_HALF': 
                texStrg+="    metric 0.5\n"
            if tex.distance_metric == 'CHEBYCHEV': 
                texStrg+="    metric 10\n"
            if tex.distance_metric == 'MANHATTAN': 
                texStrg+="    metric 1\n"

            if tex.color_mode == 'POSITION':
                texStrg+="solid\n"
            texStrg+="scale 0.25\n"
            
            if tex.use_color_ramp == True:
                texStrg+=exportColorRamp(tex)
            else:
                texStrg+="color_map {\n"
                texStrg+="[0 color rgbt<0,0,0,1>]\n"
                texStrg+="[1 color rgbt<1,1,1,0>]\n" 
                texStrg+="}\n"            
        ####################### EMULATE BLENDER CLOUDS TEXTURE ####################
        if tex.type == 'CLOUDS':  
            if tex.noise_type == 'SOFT_NOISE':
                texStrg+="wrinkles\n"
                texStrg+="scale 0.25\n"
            else:
                texStrg+="granite\n"
            if tex.use_color_ramp == True:
                texStrg+=exportColorRamp(tex)
            else:
                texStrg+="color_map {\n"
                texStrg+="[0 color rgbt<0,0,0,1>]\n"
                texStrg+="[1 color rgbt<1,1,1,0>]\n" 
                texStrg+="}\n"
        ####################### EMULATE BLENDER WOOD TEXTURE ####################
        if tex.type == 'WOOD':
            if tex.wood_type == 'RINGS':
                texStrg+="wood\n"
                texStrg+="scale 0.25\n"
            if tex.wood_type == 'RINGNOISE':
                texStrg+="wood\n"
                texStrg+="scale 0.25\n"
                texStrg+="turbulence %.4g\n"%(tex.turbulence/100)
            if tex.wood_type == 'BANDS':
                texStrg+="marble\n"
                texStrg+="scale 0.25\n"
                texStrg+="rotate <45,-45,45>\n"
            if tex.wood_type == 'BANDNOISE':
                texStrg+="marble\n"
                texStrg+="scale 0.25\n"
                texStrg+="rotate <45,-45,45>\n"
                texStrg+="turbulence %.4g\n"%(tex.turbulence/10)
            
            if tex.noise_basis_2 == 'SIN':
                texStrg+="sine_wave\n"
            if tex.noise_basis_2 == 'TRI':
                texStrg+="triangle_wave\n"
            if tex.noise_basis_2 == 'SAW':
                texStrg+="ramp_wave\n"
            if tex.use_color_ramp == True:
                texStrg+=exportColorRamp(tex)
            else:
                texStrg+="color_map {\n"
                texStrg+="[0 color rgbt<0,0,0,0>]\n"
                texStrg+="[1 color rgbt<1,1,1,0>]\n" 
                texStrg+="}\n"
        ####################### EMULATE BLENDER STUCCI TEXTURE ####################
        if tex.type == 'STUCCI':  
            texStrg+="bozo\n"
            texStrg+="scale 0.25\n"
            if tex.noise_type == 'HARD_NOISE':
                texStrg+="triangle_wave\n"
                if tex.use_color_ramp == True:
                    texStrg+=exportColorRamp(tex)
                else:
                    texStrg+="color_map {\n"
                    texStrg+="[0 color rgbf<1,1,1,0>]\n"
                    texStrg+="[1 color rgbt<0,0,0,1>]\n"
                    texStrg+="}\n"
            else:
                if tex.use_color_ramp == True:
                    texStrg+=exportColorRamp(tex)
                else:
                    texStrg+="color_map {\n"
                    texStrg+="[0 color rgbf<0,0,0,1>]\n"
                    texStrg+="[1 color rgbt<1,1,1,0>]\n"
                    texStrg+="}\n"
        ####################### EMULATE BLENDER MAGIC TEXTURE ####################
        if tex.type == 'MAGIC':  
            texStrg+="leopard\n"
            if tex.use_color_ramp == True:
                texStrg+=exportColorRamp(tex)
            else:
                texStrg+="color_map {\n"
                texStrg+="[0 color rgbt<1,1,1,0.5>]\n"
                texStrg+="[0.25 color rgbf<0,1,0,0.75>]\n"
                texStrg+="[0.5 color rgbf<0,0,1,0.75>]\n"
                texStrg+="[0.75 color rgbf<1,0,1,0.75>]\n"
                texStrg+="[1 color rgbf<0,1,0,0.75>]\n"
                texStrg+="}\n"
            texStrg+="scale 0.1\n"            
        ####################### EMULATE BLENDER MARBLE TEXTURE ####################
        if tex.type == 'MARBLE':  
            texStrg+="marble\n"
            texStrg+="turbulence 0.5\n"
            texStrg+="noise_generator 3\n"
            texStrg+="scale 0.75\n"
            texStrg+="rotate <45,-45,45>\n"
            if tex.use_color_ramp == True:
                texStrg+=exportColorRamp(tex)
            else:
                if tex.marble_type == 'SOFT':
                    texStrg+="color_map {\n"
                    texStrg+="[0 color rgbt<0,0,0,0>]\n"
                    texStrg+="[0.05 color rgbt<0,0,0,0>]\n"
                    texStrg+="[1 color rgbt<0.9,0.9,0.9,0>]\n"
                    texStrg+="}\n"
                elif tex.marble_type == 'SHARP':
                    texStrg+="color_map {\n"
                    texStrg+="[0 color rgbt<0,0,0,0>]\n"
                    texStrg+="[0.025 color rgbt<0,0,0,0>]\n"
                    texStrg+="[1 color rgbt<0.9,0.9,0.9,0>]\n"
                    texStrg+="}\n"
                else:
                    texStrg+="[0 color rgbt<0,0,0,0>]\n"
                    texStrg+="[1 color rgbt<1,1,1,0>]\n"            
                    texStrg+="}\n"
            if tex.noise_basis_2 == 'SIN':
                texStrg+="sine_wave\n"
            if tex.noise_basis_2 == 'TRI':
                texStrg+="triangle_wave\n"
            if tex.noise_basis_2 == 'SAW':
                texStrg+="ramp_wave\n"
        ####################### EMULATE BLENDER BLEND TEXTURE ####################
        if tex.type == 'BLEND':
            if tex.progression=='RADIAL':
                texStrg+="radial\n"
                if tex.use_flip_axis=='HORIZONTAL':
                    texStrg+="rotate x*90\n"
                else:
                    texStrg+="rotate <-90,0,90>\n"
                texStrg+="ramp_wave\n"
            elif tex.progression=='SPHERICAL':
                texStrg+="spherical\n"
                texStrg+="scale 3\n"
                texStrg+="poly_wave 1\n"
            elif tex.progression=='QUADRATIC_SPHERE':
                texStrg+="spherical\n"
                texStrg+="scale 3\n"
                texStrg+="    poly_wave 2\n"
            elif tex.progression=='DIAGONAL':
                texStrg+="gradient <1,1,0>\n"
                texStrg+="scale 3\n"
            elif tex.use_flip_axis=='HORIZONTAL':        
                texStrg+="gradient x\n"
                texStrg+="scale 2.01\n"
            elif tex.use_flip_axis=='VERTICAL':
                texStrg+="gradient y\n"
                texStrg+="scale 2.01\n"
            #texStrg+="ramp_wave\n"
            #texStrg+="frequency 0.5\n"
            texStrg+="phase 0.5\n"
            if tex.use_color_ramp == True:
                texStrg+=exportColorRamp(tex)
            else:
                texStrg+="color_map {\n"
                texStrg+="[0 color rgbt<1,1,1,0>]\n"
                texStrg+="[1 color rgbf<0,0,0,1>]\n"
                texStrg+="}\n"
            if tex.progression == 'LINEAR': 
                texStrg+="    poly_wave 1\n"
            if tex.progression == 'QUADRATIC': 
                texStrg+="    poly_wave 2\n"
            if tex.progression == 'EASING':
                texStrg+="    poly_wave 1.5\n"            
        ####################### EMULATE BLENDER MUSGRAVE TEXTURE ####################
        # if tex.type == 'MUSGRAVE':  
            # texStrg+="function{ f_ridged_mf( x, y, 0, 1, 2, 9, -0.5, 3,3 )*0.5}\n"
            # texStrg+="color_map {\n"
            # texStrg+="[0 color rgbf<0,0,0,1>]\n"
            # texStrg+="[1 color rgbf<1,1,1,0>]\n"
            # texStrg+="}\n"
        # simplified for now:

        if tex.type == 'MUSGRAVE':
            texStrg+="bozo scale 0.25 \n"
            if tex.use_color_ramp == True:
                texStrg+=exportColorRamp(tex)
            else: 
                texStrg+="color_map {[0.5 color rgbf<0,0,0,1>][1 color rgbt<1,1,1,0>]}ramp_wave \n"            
        ####################### EMULATE BLENDER DISTORTED NOISE TEXTURE ####################
        if tex.type == 'DISTORTED_NOISE':  
            texStrg+="average\n"
            texStrg+="  pigment_map {\n"
            texStrg+="  [1 bozo scale 0.25 turbulence %.4g\n" %tex.distortion
            if tex.use_color_ramp == True:
                texStrg+=exportColorRamp(tex)
            else: 
                texStrg+="color_map {\n"
                texStrg+="[0 color rgbt<1,1,1,0>]\n"
                texStrg+="[1 color rgbf<0,0,0,1>]\n"
                texStrg+="}\n"
            texStrg+="]\n"

            if tex.noise_distortion == 'CELL_NOISE':
                texStrg+="  [1 cells scale 0.1\n"
                if tex.use_color_ramp == True:
                    texStrg+=exportColorRamp(tex)
                else: 
                    texStrg+="color_map {\n"
                    texStrg+="[0 color rgbt<1,1,1,0>]\n"
                    texStrg+="[1 color rgbf<0,0,0,1>]\n"
                    texStrg+="}\n"
                texStrg+="]\n"                
            if tex.noise_distortion=='VORONOI_CRACKLE':
                texStrg+="  [1 crackle scale 0.25\n"
                if tex.use_color_ramp == True:
                    texStrg+=exportColorRamp(tex)
                else: 
                    texStrg+="color_map {\n"
                    texStrg+="[0 color rgbt<1,1,1,0>]\n"
                    texStrg+="[1 color rgbf<0,0,0,1>]\n"
                    texStrg+="}\n"
                texStrg+="]\n"                
            if tex.noise_distortion in ['VORONOI_F1','VORONOI_F2','VORONOI_F3','VORONOI_F4','VORONOI_F2_F1']:
                texStrg+="  [1 crackle metric 2.5 scale 0.25 turbulence %.4g\n" %(tex.distortion/2)
                if tex.use_color_ramp == True:
                    texStrg+=exportColorRamp(tex)
                else: 
                    texStrg+="color_map {\n"
                    texStrg+="[0 color rgbt<1,1,1,0>]\n"
                    texStrg+="[1 color rgbf<0,0,0,1>]\n"
                    texStrg+="}\n"
                texStrg+="]\n"                
            else:
                texStrg+="  [1 wrinkles scale 0.25\n" 
                if tex.use_color_ramp == True:
                    texStrg+=exportColorRamp(tex)
                else: 
                    texStrg+="color_map {\n"
                    texStrg+="[0 color rgbt<1,1,1,0>]\n"
                    texStrg+="[1 color rgbf<0,0,0,1>]\n"
                    texStrg+="}\n"
                texStrg+="]\n"
            texStrg+="  }\n"
        ####################### EMULATE BLENDER NOISE TEXTURE ####################
        if tex.type == 'NOISE':  
            texStrg+="cells\n"
            texStrg+="turbulence 3\n"
            texStrg+="omega 3\n"
            if tex.use_color_ramp == True:
                texStrg+=exportColorRamp(tex)
            else: 
                texStrg+="color_map {\n"
                texStrg+="[0.75 color rgb<0,0,0,>]\n"
                texStrg+="[1 color rgb<1,1,1,>]\n"
                texStrg+="}\n"

        ####################### IGNORE OTHER BLENDER TEXTURE ####################
        else: #non translated textures
            pass
        texStrg+="}\n\n"            

        texStrg+="#declare f%s=\n"%PATname
        texStrg+="function{pigment{%s}}\n"%PATname       
        texStrg+="\n"
        
    else:
        texStrg+="pigment {\n"
        texStrg+="%s\n"%pat.tex_pattern_type
        if pat.tex_pattern_type == 'agate': 
            texStrg+="agate_turb %.4g\n"%pat.modifier_turbulence                           
        if pat.tex_pattern_type in set(['spiral1', 'spiral2', 'tiling']): 
            texStrg+="%s\n"%pat.modifier_numbers
        if pat.tex_pattern_type == 'quilted': 
            texStrg+="control0 %s control1 %s\n"%(pat.modifier_control0, pat.modifier_control1)                           
        if pat.tex_pattern_type == 'mandel': 
            texStrg+="%s exponent %s \n"%(pat.f_iter, pat.f_exponent)  
        if pat.tex_pattern_type == 'julia': 
            texStrg+="<%.4g, %.4g> %s exponent %s \n"%(pat.julia_complex_1, pat.julia_complex_2, pat.f_iter, pat.f_exponent)   
        if pat.tex_pattern_type == 'magnet' and pat.magnet_style == 'mandel': 
            texStrg+="%s mandel %s \n"%(pat.magnet_type, pat.f_iter)
        if pat.tex_pattern_type == 'magnet' and pat.magnet_style == 'julia':  
            texStrg+="%s julia <%.4g, %.4g> %s\n"%(pat.magnet_type, pat.julia_complex_1, pat.julia_complex_2, pat.f_iter) 
        if pat.tex_pattern_type in set(['mandel', 'julia', 'magnet']):
            texStrg+="interior %s, %.4g\n"%(pat.f_ior, pat.f_ior_fac) 
            texStrg+="exterior %s, %.4g\n"%(pat.f_eor, pat.f_eor_fac)
        if pat.tex_pattern_type == 'gradient': 
            texStrg+="<%s, %s, %s> \n"%(pat.grad_orient_x, pat.grad_orient_y, pat.grad_orient_z)
        if pat.tex_pattern_type == 'pavement':
            numTiles=pat.pave_tiles
            numPattern=1
            if pat.pave_sides == '4' and pat.pave_tiles == 3: 
                 numPattern = pat.pave_pat_2
            if pat.pave_sides == '6' and pat.pave_tiles == 3: 
                numPattern = pat.pave_pat_3
            if pat.pave_sides == '3' and pat.pave_tiles == 4: 
                numPattern = pat.pave_pat_3
            if pat.pave_sides == '3' and pat.pave_tiles == 5: 
                numPattern = pat.pave_pat_4
            if pat.pave_sides == '4' and pat.pave_tiles == 4: 
                numPattern = pat.pave_pat_5
            if pat.pave_sides == '6' and pat.pave_tiles == 4: 
                numPattern = pat.pave_pat_7
            if pat.pave_sides == '4' and pat.pave_tiles == 5: 
                numPattern = pat.pave_pat_12
            if pat.pave_sides == '3' and pat.pave_tiles == 6: 
                numPattern = pat.pave_pat_12
            if pat.pave_sides == '6' and pat.pave_tiles == 5: 
                numPattern = pat.pave_pat_22
            if pat.pave_sides == '4' and pat.pave_tiles == 6: 
                numPattern = pat.pave_pat_35
            if pat.pave_sides == '6' and pat.pave_tiles == 6: 
                numTiles = 5                                
            texStrg+="number_of_sides %s number_of_tiles %s pattern %s form %s \n"%(pat.pave_sides, numTiles, numPattern, pat.pave_form)
        ################ functions #####################################################################################################
        if pat.tex_pattern_type == 'function':                 
            texStrg+="{ %s"%pat.func_list
            texStrg+="(x"
            if pat.func_plus_x != "NONE":
                if pat.func_plus_x =='increase':
                    texStrg+="*"                                    
                if pat.func_plus_x =='plus':
                    texStrg+="+"
                texStrg+="%.4g"%pat.func_x
            texStrg+=",y"
            if pat.func_plus_y != "NONE":
                if pat.func_plus_y =='increase':
                    texStrg+="*"                                   
                if pat.func_plus_y =='plus':
                    texStrg+="+"
                texStrg+="%.4g"%pat.func_y
            texStrg+=",z"
            if pat.func_plus_z != "NONE":
                if pat.func_plus_z =='increase':
                    texStrg+="*"                                    
                if pat.func_plus_z =='plus':
                    texStrg+="+"
                texStrg+="%.4g"%pat.func_z
            sort = -1
            if pat.func_list in set(["f_comma","f_crossed_trough","f_cubic_saddle","f_cushion","f_devils_curve",
                                 "f_enneper","f_glob","f_heart","f_hex_x","f_hex_y","f_hunt_surface",
                                 "f_klein_bottle","f_kummer_surface_v1","f_lemniscate_of_gerono","f_mitre",
                                 "f_nodal_cubic","f_noise_generator","f_odd","f_paraboloid","f_pillow",
                                 "f_piriform","f_quantum","f_quartic_paraboloid","f_quartic_saddle",
                                 "f_sphere","f_steiners_roman","f_torus_gumdrop","f_umbrella"]):
                sort = 0
            if pat.func_list in set(["f_bicorn","f_bifolia","f_boy_surface","f_superellipsoid","f_torus"]):
                sort = 1
            if pat.func_list in set(["f_ellipsoid","f_folium_surface","f_hyperbolic_torus",
                                 "f_kampyle_of_eudoxus","f_parabolic_torus","f_quartic_cylinder","f_torus2"]):
                sort = 2
            if pat.func_list in set(["f_blob2","f_cross_ellipsoids","f_flange_cover","f_isect_ellipsoids",
                                 "f_kummer_surface_v2","f_ovals_of_cassini","f_rounded_box","f_spikes_2d","f_strophoid"]):
                sort = 3
            if pat.func_list in set(["f_algbr_cyl1","f_algbr_cyl2","f_algbr_cyl3","f_algbr_cyl4","f_blob","f_mesh1","f_poly4","f_spikes"]):
                sort = 4
            if pat.func_list in set(["f_devils_curve_2d","f_dupin_cyclid","f_folium_surface_2d","f_hetero_mf","f_kampyle_of_eudoxus_2d",
                                 "f_lemniscate_of_gerono_2d","f_polytubes","f_ridge","f_ridged_mf","f_spiral","f_witch_of_agnesi"]):
                sort = 5
            if pat.func_list in set(["f_helix1","f_helix2","f_piriform_2d","f_strophoid_2d"]):
                sort = 6
            if pat.func_list == "f_helical_torus":
                sort = 7
            if sort > -1:
                texStrg+=",%.4g"%pat.func_P0
            if sort > 0:
                texStrg+=",%.4g"%pat.func_P1
            if sort > 1:
                texStrg+=",%.4g"%pat.func_P2
            if sort > 2:
                texStrg+=",%.4g"%pat.func_P3
            if sort > 3:
                texStrg+=",%.4g"%pat.func_P4
            if sort > 4:
                texStrg+=",%.4g"%pat.func_P5
            if sort > 5:
                texStrg+=",%.4g"%pat.func_P6
            if sort > 6:
                texStrg+=",%.4g"%pat.func_P7
                texStrg+=",%.4g"%pat.func_P8
                texStrg+=",%.4g"%pat.func_P9
            texStrg+=")}\n"
        ############## end functions ###############################################################
        if pat.tex_pattern_type not in set(['checker', 'hexagon', 'square', 'triangular', 'brick']):                        
            texStrg+="color_map {\n"
        numColor=0
        if tex.use_color_ramp == True:
            for el in tex.color_ramp.elements:
                numColor+=1
                pos = el.position
                col=el.color
                colR,colG,colB,colA = col[0],col[1],col[2],1-col[3]
                if pat.tex_pattern_type not in set(['checker', 'hexagon', 'square', 'triangular', 'brick']) :
                    texStrg+="[%.4g color rgbf<%.4g,%.4g,%.4g,%.4g>] \n"%(pos,colR,colG,colB,colA)
                if pat.tex_pattern_type in set(['brick','checker']) and numColor < 3:
                    texStrg+="color rgbf<%.4g,%.4g,%.4g,%.4g> \n"%(colR,colG,colB,colA)
                if pat.tex_pattern_type == 'hexagon' and numColor < 4 :
                    texStrg+="color rgbf<%.4g,%.4g,%.4g,%.4g> \n"%(colR,colG,colB,colA)
                if pat.tex_pattern_type == 'square' and numColor < 5 :
                    texStrg+="color rgbf<%.4g,%.4g,%.4g,%.4g> \n"%(colR,colG,colB,colA)
                if pat.tex_pattern_type == 'triangular' and numColor < 7 :
                    texStrg+="color rgbf<%.4g,%.4g,%.4g,%.4g> \n"%(colR,colG,colB,colA)
        else:
            texStrg+="[0 color rgbf<0,0,0,1>]\n"
            texStrg+="[1 color rgbf<1,1,1,0>]\n"
        if pat.tex_pattern_type not in set(['checker', 'hexagon', 'square', 'triangular', 'brick']) :                        
            texStrg+="} \n"                       
        if pat.tex_pattern_type == 'brick':                        
            texStrg+="brick_size <%.4g, %.4g, %.4g> mortar %.4g \n"%(pat.brick_size_x, pat.brick_size_y, pat.brick_size_z, pat.brick_mortar)
        texStrg+="%s \n"%mappingDif
        texStrg+="rotate <%.4g,%.4g,%.4g> \n"%(pat.tex_rot_x, pat.tex_rot_y, pat.tex_rot_z)
        texStrg+="turbulence <%.4g,%.4g,%.4g> \n"%(pat.warp_turbulence_x, pat.warp_turbulence_y, pat.warp_turbulence_z)
        texStrg+="octaves %s \n"%pat.modifier_octaves
        texStrg+="lambda %.4g \n"%pat.modifier_lambda
        texStrg+="omega %.4g \n"%pat.modifier_omega
        texStrg+="frequency %.4g \n"%pat.modifier_frequency
        texStrg+="phase %.4g \n"%pat.modifier_phase                       
        texStrg+="}\n\n"
        texStrg+="#declare f%s=\n"%PATname
        texStrg+="function{pigment{%s}}\n"%PATname       
        texStrg+="\n"
    return(texStrg)

def write_pov(filename, scene=None, info_callback=None):
    import mathutils
    #file = filename
    file = open(filename, "w")

    # Only for testing
    if not scene:
        scene = bpy.data.scenes[0]

    render = scene.render
    world = scene.world
    global_matrix = mathutils.Matrix.Rotation(-pi / 2.0, 4, 'X')
    comments = scene.pov.comments_enable and not scene.pov.tempfiles_enable
    linebreaksinlists = scene.pov.list_lf_enable and not scene.pov.tempfiles_enable
    feature_set = bpy.context.user_preferences.addons[__package__].preferences.branch_feature_set_povray
    using_uberpov = (feature_set=='uberpov')
    pov_binary = PovrayRender._locate_binary()

    if using_uberpov:
        print "Unofficial UberPOV feature set chosen in preferences"
    else:
        print "Official POV-Ray 3.7 feature set chosen in preferences"
    if 'uber' in pov_binary: 
        print "The name of the binary suggests you are probably rendering with Uber POV engine"
    else:
        print "The name of the binary suggests you are probably rendering with standard POV engine"
    def setTab(tabtype, spaces):
        TabStr = ""
        if tabtype == 'NONE':
            TabStr = ""
        elif tabtype == 'TAB':
            TabStr = "\t"
        elif tabtype == 'SPACE':
            TabStr = spaces * " "
        return TabStr

    tab = setTab(scene.pov.indentation_character, scene.pov.indentation_spaces)
    if not scene.pov.tempfiles_enable:
        def tabWrite(str_o):
            global tabLevel
            brackets = str_o.count("{") - str_o.count("}") + str_o.count("[") - str_o.count("]")
            if brackets < 0:
                tabLevel = tabLevel + brackets
            if tabLevel < 0:
                print "Indentation Warning: tabLevel = %s" % tabLevel
                tabLevel = 0
            if tabLevel >= 1:
                file.write("%s" % tab * tabLevel)
            file.write(str_o)
            if brackets > 0:
                tabLevel = tabLevel + brackets
    else:
        def tabWrite(str_o):
            file.write(str_o)

    def uniqueName(name, nameSeq):

        if name not in nameSeq:
            name = string_strip_hyphen(name)
            return name

        name_orig = name
        i = 1
        while name in nameSeq:
            name = "%s_%.3d" % (name_orig, i)
            i += 1
        name = string_strip_hyphen(name)
        return name

    def writeMatrix(matrix):
        tabWrite("matrix <%.6f, %.6f, %.6f,  %.6f, %.6f, %.6f,  %.6f, %.6f, %.6f,  %.6f, %.6f, %.6f>\n" %
                 (matrix[0][0], matrix[1][0], matrix[2][0],
                  matrix[0][1], matrix[1][1], matrix[2][1],
                  matrix[0][2], matrix[1][2], matrix[2][2],
                  matrix[0][3], matrix[1][3], matrix[2][3]))

    def MatrixAsPovString(matrix):
        sMatrix = ("matrix <%.6f, %.6f, %.6f,  %.6f, %.6f, %.6f,  %.6f, %.6f, %.6f,  %.6f, %.6f, %.6f>\n" %
                   (matrix[0][0], matrix[1][0], matrix[2][0],
                    matrix[0][1], matrix[1][1], matrix[2][1],
                    matrix[0][2], matrix[1][2], matrix[2][2],
                    matrix[0][3], matrix[1][3], matrix[2][3]))
        return sMatrix

    def writeObjectMaterial(material, ob):

        # DH - modified some variables to be function local, avoiding RNA write
        # this should be checked to see if it is functionally correct

        # Commented out: always write IOR to be able to use it for SSS, Fresnel reflections...
        #if material and material.transparency_method == 'RAYTRACE':
        if material:
            # But there can be only one!
            if material.subsurface_scattering.use:  # SSS IOR get highest priority
                tabWrite("interior {\n")
                tabWrite("ior %.6f\n" % material.subsurface_scattering.ior)
            # Then the raytrace IOR taken from raytrace transparency properties and used for
            # reflections if IOR Mirror option is checked.
            elif material.pov.mirror_use_IOR:
                tabWrite("interior {\n")
                tabWrite("ior %.6f\n" % material.raytrace_transparency.ior)
            else:
                tabWrite("interior {\n")
                tabWrite("ior %.6f\n" % material.raytrace_transparency.ior)

            pov_fake_caustics = False
            pov_photons_refraction = False
            pov_photons_reflection = False

            if material.pov.photons_reflection:
                pov_photons_reflection = True
            if material.pov.refraction_type == "0":
                pov_fake_caustics = False
                pov_photons_refraction = False
            elif material.pov.refraction_type == "1":
                pov_fake_caustics = True
                pov_photons_refraction = False
            elif material.pov.refraction_type == "2":
                pov_fake_caustics = False
                pov_photons_refraction = True

            # If only Raytrace transparency is set, its IOR will be used for refraction, but user
            # can set up 'un-physical' fresnel reflections in raytrace mirror parameters.
            # Last, if none of the above is specified, user can set up 'un-physical' fresnel
            # reflections in raytrace mirror parameters. And pov IOR defaults to 1.
            if material.pov.caustics_enable:
                if pov_fake_caustics:
                    tabWrite("caustics %.3g\n" % material.pov.fake_caustics_power)
                if pov_photons_refraction:
                    # Default of 1 means no dispersion
                    tabWrite("dispersion %.6f\n" % material.pov.photons_dispersion)
                    tabWrite("dispersion_samples %.d\n" % material.pov.photons_dispersion_samples)
            #TODO
            # Other interior args
            if material.use_transparency and material.transparency_method == 'RAYTRACE':
                # fade_distance
                # In Blender this value has always been reversed compared to what tooltip says.
                # 100.001 rather than 100 so that it does not get to 0
                # which deactivates the feature in POV
                tabWrite("fade_distance %.3g\n" % \
                         (100.001 - material.raytrace_transparency.depth_max))
                # fade_power
                tabWrite("fade_power %.3g\n" % material.raytrace_transparency.falloff)
                # fade_color
                tabWrite("fade_color <%.3g, %.3g, %.3g>\n" % material.pov.interior_fade_color[:])

            # (variable) dispersion_samples (constant count for now)
            tabWrite("}\n")
            if material.pov.photons_reflection or material.pov.refraction_type=="2":
                tabWrite("photons{")
                tabWrite("target %.3g\n" % ob.pov.spacing_multiplier)
                if not ob.pov.collect_photons:
                    tabWrite("collect off\n")
                if pov_photons_refraction:
                    tabWrite("refraction on\n")
                if pov_photons_reflection:
                    tabWrite("reflection on\n")
                tabWrite("}\n")

    materialNames = {}
    DEF_MAT_NAME = "" #or "Default"?

    def writeMaterial(material):
        # Assumes only called once on each material
        if material:
            name_orig = material.name
            name = materialNames[name_orig] = uniqueName(bpy.path.clean_name(name_orig), materialNames)
        else:
            name = name_orig = DEF_MAT_NAME


        if material:
            # If saturation(.s) is not zero, then color is not grey, and has a tint
            colored_specular_found = (material.specular_color.s > 0.0)

        ##################
        # Several versions of the finish: Level conditions are variations for specular/Mirror
        # texture channel map with alternative finish of 0 specular and no mirror reflection.
        # Level=1 Means No specular nor Mirror reflection
        # Level=2 Means translation of spec and mir levels for when no map influences them
        # Level=3 Means Maximum Spec and Mirror

        def povHasnoSpecularMaps(Level):
            if Level == 1:
                tabWrite("#declare %s = finish {" % safety(name, Level=1))
                if comments:
                    file.write("  //No specular nor Mirror reflection\n")
                else:
                    tabWrite("\n")
            elif Level == 2:
                tabWrite("#declare %s = finish {" % safety(name, Level=2))
                if comments:
                    file.write("  //translation of spec and mir levels for when no map " \
                               "influences them\n")
                else:
                    tabWrite("\n")
            elif Level == 3:
                tabWrite("#declare %s = finish {" % safety(name, Level=3))
                if comments:
                    file.write("  //Maximum Spec and Mirror\n")
                else:
                    tabWrite("\n")

            if material:
                # POV-Ray 3.7 now uses two diffuse values respectively for front and back shading
                # (the back diffuse is like blender translucency)
                frontDiffuse = material.diffuse_intensity
                backDiffuse = material.translucency

                if material.pov.conserve_energy:

                    #Total should not go above one
                    if (frontDiffuse + backDiffuse) <= 1.0:
                        pass
                    elif frontDiffuse == backDiffuse:
                        # Try to respect the user's 'intention' by comparing the two values but
                        # bringing the total back to one.
                        frontDiffuse = backDiffuse = 0.5
                    # Let the highest value stay the highest value.
                    elif frontDiffuse > backDiffuse:
                        # clamps the sum below 1
                        backDiffuse = min(backDiffuse, (1.0 - frontDiffuse))
                    else:
                        frontDiffuse = min(frontDiffuse, (1.0 - backDiffuse))

                # map hardness between 0.0 and 1.0
                roughness = ((1.0 - ((material.specular_hardness - 1.0) / 510.0)))
                ## scale from 0.0 to 0.1
                roughness *= 0.1
                # add a small value because 0.0 is invalid.
                roughness += (1.0 / 511.0)

                ################################Diffuse Shader######################################
                # Not used for Full spec (Level=3) of the shader.
                if material.diffuse_shader == 'OREN_NAYAR' and Level != 3:
                    # Blender roughness is what is generally called oren nayar Sigma,
                    # and brilliance in POV-Ray.
                    tabWrite("brilliance %.3g\n" % (0.9 + material.roughness))

                if material.diffuse_shader == 'TOON' and Level != 3:
                    tabWrite("brilliance %.3g\n" % (0.01 + material.diffuse_toon_smooth * 0.25))
                    # Lower diffuse and increase specular for toon effect seems to look better
                    # in POV-Ray.
                    frontDiffuse *= 0.5

                if material.diffuse_shader == 'MINNAERT' and Level != 3:
                    #tabWrite("aoi %.3g\n" % material.darkness)
                    pass  # let's keep things simple for now
                if material.diffuse_shader == 'FRESNEL' and Level != 3:
                    #tabWrite("aoi %.3g\n" % material.diffuse_fresnel_factor)
                    pass  # let's keep things simple for now
                if material.diffuse_shader == 'LAMBERT' and Level != 3:
                    # trying to best match lambert attenuation by that constant brilliance value
                    tabWrite("brilliance 1.8\n")

                if Level == 2:
                    ###########################Specular Shader######################################
                    # No difference between phong and cook torrence in blender HaHa!
                    if (material.specular_shader == 'COOKTORR' or
                        material.specular_shader == 'PHONG'):
                        tabWrite("phong %.3g\n" % (material.specular_intensity))
                        tabWrite("phong_size %.3g\n" % (material.specular_hardness / 2 + 0.25))

                    # POV-Ray 'specular' keyword corresponds to a Blinn model, without the ior.
                    elif material.specular_shader == 'BLINN':
                        # Use blender Blinn's IOR just as some factor for spec intensity
                        tabWrite("specular %.3g\n" % (material.specular_intensity *
                                                      (material.specular_ior / 4.0)))
                        tabWrite("roughness %.3g\n" % roughness)
                        #Could use brilliance 2(or varying around 2 depending on ior or factor) too.

                    elif material.specular_shader == 'TOON':
                        tabWrite("phong %.3g\n" % (material.specular_intensity * 2.0))
                        # use extreme phong_size
                        tabWrite("phong_size %.3g\n" % (0.1 + material.specular_toon_smooth / 2.0))

                    elif material.specular_shader == 'WARDISO':
                        # find best suited default constant for brilliance Use both phong and
                        # specular for some values.
                        tabWrite("specular %.3g\n" % (material.specular_intensity /
                                                      (material.specular_slope + 0.0005)))
                        # find best suited default constant for brilliance Use both phong and
                        # specular for some values.
                        tabWrite("roughness %.4g\n" % (0.0005 + material.specular_slope / 10.0))
                        # find best suited default constant for brilliance Use both phong and
                        # specular for some values.
                        tabWrite("brilliance %.4g\n" % (1.8 - material.specular_slope * 1.8))

                ####################################################################################
                elif Level == 1:
                    tabWrite("specular 0\n")
                elif Level == 3:
                    tabWrite("specular 1\n")
                tabWrite("diffuse %.3g %.3g\n" % (frontDiffuse, backDiffuse))

                tabWrite("ambient %.3g\n" % material.ambient)
                # POV-Ray blends the global value
                #tabWrite("ambient rgb <%.3g, %.3g, %.3g>\n" % \
                #         tuple([c*material.ambient for c in world.ambient_color]))
                tabWrite("emission %.3g\n" % material.emit)  # New in POV-Ray 3.7

                #POV-Ray just ignores roughness if there's no specular keyword
                #tabWrite("roughness %.3g\n" % roughness)

                if material.pov.conserve_energy:
                    # added for more realistic shading. Needs some checking to see if it
                    # really works. --Maurice.
                    tabWrite("conserve_energy\n")

                if colored_specular_found == True:
                     tabWrite("metallic\n")          

                # 'phong 70.0 '
                if Level != 1:
                    if material.raytrace_mirror.use:
                        raytrace_mirror = material.raytrace_mirror
                        if raytrace_mirror.reflect_factor:
                            tabWrite("reflection {\n")
                            tabWrite("rgb <%.3g, %.3g, %.3g>\n" % material.mirror_color[:])                          
                            if material.pov.mirror_metallic:
                                tabWrite("metallic %.3g\n" % (raytrace_mirror.reflect_factor))
                            # Blurry reflections for UberPOV
                            if using_uberpov and raytrace_mirror.gloss_factor < 1.0:
                                #tabWrite("#ifdef(unofficial) #if(unofficial = \"patch\") #if(patch(\"upov-reflection-roughness\") > 0)\n")
                                tabWrite("roughness %.6f\n" % \
                                         (0.000001/raytrace_mirror.gloss_factor))
                                #tabWrite("#end #end #end\n") # This and previous comment for backward compatibility, messier pov code
                            if material.pov.mirror_use_IOR:  # WORKING ?
                                # Removed from the line below: gives a more physically correct
                                # material but needs proper IOR. --Maurice
                                tabWrite("fresnel 1 ")
                            tabWrite("falloff %.3g exponent %.3g} " % \
                                     (raytrace_mirror.fresnel, raytrace_mirror.fresnel_factor))
                                
                if material.subsurface_scattering.use:
                    subsurface_scattering = material.subsurface_scattering
                    tabWrite("subsurface { translucency <%.3g, %.3g, %.3g> }\n" % (
                             (subsurface_scattering.radius[0]),
                             (subsurface_scattering.radius[1]),
                             (subsurface_scattering.radius[2]),
                             )
                            )

                if material.pov.irid_enable:
                    tabWrite("irid { %.4g thickness %.4g turbulence %.4g }" % \
                             (material.pov.irid_amount, material.pov.irid_thickness,
                              material.pov.irid_turbulence))

            else:
                tabWrite("diffuse 0.8\n")
                tabWrite("phong 70.0\n")

                #tabWrite("specular 0.2\n")

            # This is written into the object
            '''
            if material and material.transparency_method=='RAYTRACE':
                'interior { ior %.3g} ' % material.raytrace_transparency.ior
            '''

            #tabWrite("crand 1.0\n") # Sand granyness
            #tabWrite("metallic %.6f\n" % material.spec)
            #tabWrite("phong %.6f\n" % material.spec)
            #tabWrite("phong_size %.6f\n" % material.spec)
            #tabWrite("brilliance %.6f " % (material.specular_hardness/256.0) # Like hardness

            tabWrite("}\n\n")

        # Level=2 Means translation of spec and mir levels for when no map influences them
        povHasnoSpecularMaps(Level=2)

        if material:
            special_texture_found = False
            for t in material.texture_slots:
                if t and t.use:
                    if (t.texture.type == 'IMAGE' and t.texture.image) or t.texture.type != 'IMAGE':
                        validPath=True
                else:
                    validPath=False
                if(t and t.use and validPath and
                   (t.use_map_specular or t.use_map_raymir or t.use_map_normal or t.use_map_alpha)):
                    special_texture_found = True
                    continue  # Some texture found

            if special_texture_found or colored_specular_found:
                # Level=1 Means No specular nor Mirror reflection
                povHasnoSpecularMaps(Level=1)

                # Level=3 Means Maximum Spec and Mirror
                povHasnoSpecularMaps(Level=3)

    def exportCamera():
        camera = scene.camera

        # DH disabled for now, this isn't the correct context
        active_object = None  # bpy.context.active_object # does not always work  MR
        matrix = global_matrix * camera.matrix_world
        focal_point = camera.data.dof_distance

        # compute resolution
        Qsize = render.resolution_x / render.resolution_y
        tabWrite("#declare camLocation  = <%.6f, %.6f, %.6f>;\n" %
                 matrix.translation[:])
        tabWrite("#declare camLookAt = <%.6f, %.6f, %.6f>;\n" %
                 tuple([degrees(e) for e in matrix.to_3x3().to_euler()]))

        tabWrite("camera {\n")
        if scene.pov.baking_enable and active_object and active_object.type == 'MESH':
            tabWrite("mesh_camera{ 1 3\n")  # distribution 3 is what we want here
            tabWrite("mesh{%s}\n" % active_object.name)
            tabWrite("}\n")
            tabWrite("location <0,0,.01>")
            tabWrite("direction <0,0,-1>")
        # Using standard camera otherwise
        else:
            tabWrite("location  <0, 0, 0>\n")
            tabWrite("look_at  <0, 0, -1>\n")
            tabWrite("right <%s, 0, 0>\n" % - Qsize)
            tabWrite("up <0, 1, 0>\n")
            tabWrite("angle  %f\n" % (360.0 * atan(16.0 / camera.data.lens) / pi))

            tabWrite("rotate  <%.6f, %.6f, %.6f>\n" % \
                     tuple([degrees(e) for e in matrix.to_3x3().to_euler()]))
            tabWrite("translate <%.6f, %.6f, %.6f>\n" % matrix.translation[:])
            if camera.data.pov.dof_enable and focal_point != 0:
                tabWrite("aperture %.3g\n" % camera.data.pov.dof_aperture)
                tabWrite("blur_samples %d %d\n" % \
                         (camera.data.pov.dof_samples_min, camera.data.pov.dof_samples_max))
                tabWrite("variance 1/%d\n" % camera.data.pov.dof_variance)
                tabWrite("confidence %.3g\n" % camera.data.pov.dof_confidence)
                tabWrite("focal_point <0, 0, %f>\n" % focal_point)
        tabWrite("}\n")

    def exportLamps(lamps):
        # Incremented after each lamp export to declare its target
        # currently used for Fresnel diffuse shader as their slope vector:
        global lampCount
        lampCount = 0
        # Get all lamps
        for ob in lamps:
            lamp = ob.data

            matrix = global_matrix * ob.matrix_world

            # Color is modified by energy #muiltiplie by 2 for a better match --Maurice
            color = tuple([c * lamp.energy * 2.0 for c in lamp.color])

            tabWrite("light_source {\n")
            tabWrite("< 0,0,0 >\n")
            tabWrite("color rgb<%.3g, %.3g, %.3g>\n" % color)

            if lamp.type == 'POINT':
                pass
            elif lamp.type == 'SPOT':
                tabWrite("spotlight\n")

                # Falloff is the main radius from the centre line
                tabWrite("falloff %.2f\n" % (degrees(lamp.spot_size) / 2.0))  # 1 TO 179 FOR BOTH
                tabWrite("radius %.6f\n" % \
                         ((degrees(lamp.spot_size) / 2.0) * (1.0 - lamp.spot_blend)))

                # Blender does not have a tightness equivilent, 0 is most like blender default.
                tabWrite("tightness 0\n")  # 0:10f

                tabWrite("point_at  <0, 0, -1>\n")
            elif lamp.type == 'SUN':
                tabWrite("parallel\n")
                tabWrite("point_at  <0, 0, -1>\n")  # *must* be after 'parallel'

            elif lamp.type == 'AREA':
                tabWrite("area_illumination\n")
                tabWrite("fade_distance %.6f\n" % (lamp.distance / 2.0))
                # Area lights have no falloff type, so always use blenders lamp quad equivalent
                # for those?
                tabWrite("fade_power %d\n" % 2)
                size_x = lamp.size
                samples_x = lamp.shadow_ray_samples_x
                if lamp.shape == 'SQUARE':
                    size_y = size_x
                    samples_y = samples_x
                else:
                    size_y = lamp.size_y
                    samples_y = lamp.shadow_ray_samples_y

                tabWrite("area_light <%.6f,0,0>,<0,%.6f,0> %d, %d\n" % \
                         (size_x, size_y, samples_x, samples_y))
                if lamp.shadow_ray_sample_method == 'CONSTANT_JITTERED':
                    if lamp.use_jitter:
                        tabWrite("jitter\n")
                else:
                    tabWrite("adaptive 1\n")
                    tabWrite("jitter\n")

            # HEMI never has any shadow_method attribute
            if(not scene.render.use_shadows or lamp.type == 'HEMI' or
               (lamp.type != 'HEMI' and lamp.shadow_method == 'NOSHADOW')):
                tabWrite("shadowless\n")

            # Sun shouldn't be attenuated. Hemi and area lights have no falloff attribute so they
            # are put to type 2 attenuation a little higher above.
            if lamp.type not in set(['SUN', 'AREA', 'HEMI']):
                tabWrite("fade_distance %.6f\n" % (lamp.distance / 2.0))
                if lamp.falloff_type == 'INVERSE_SQUARE':
                    tabWrite("fade_power %d\n" % 2)  # Use blenders lamp quad equivalent
                elif lamp.falloff_type == 'INVERSE_LINEAR':
                    tabWrite("fade_power %d\n" % 1)  # Use blenders lamp linear
                # supposing using no fade power keyword would default to constant, no attenuation.
                elif lamp.falloff_type == 'CONSTANT':
                    pass
                # Using Custom curve for fade power 3 for now.
                elif lamp.falloff_type == 'CUSTOM_CURVE':
                    tabWrite("fade_power %d\n" % 4)

            writeMatrix(matrix)

            tabWrite("}\n")

            lampCount += 1

            # v(A,B) rotates vector A about origin by vector B.
            file.write("#declare lampTarget%s= vrotate(<%.4g,%.4g,%.4g>,<%.4g,%.4g,%.4g>);\n" % \
                       (lampCount, -(ob.location.x), -(ob.location.y), -(ob.location.z),
                        ob.rotation_euler.x, ob.rotation_euler.y, ob.rotation_euler.z))

####################################################################################################

    def exportMeta(metas):

        # TODO - blenders 'motherball' naming is not supported.

        if comments and len(metas) >= 1:
            file.write("//--Blob objects--\n\n")

        for ob in metas:
            meta = ob.data

            # important because no elements will break parsing.
            elements = [elem for elem in meta.elements if elem.type in set(['BALL', 'ELLIPSOID'])]

            if elements:
                tabWrite("blob {\n")
                tabWrite("threshold %.4g\n" % meta.threshold)
                importance = ob.pov.importance_value

                try:
                    material = meta.materials[0]  # lame! - blender cant do enything else.
                except:
                    material = None

                for elem in elements:
                    loc = elem.co

                    stiffness = elem.stiffness
                    if elem.use_negative:
                        stiffness = - stiffness

                    if elem.type == 'BALL':

                        tabWrite("sphere { <%.6g, %.6g, %.6g>, %.4g, %.4g }\n" % \
                                 (loc.x, loc.y, loc.z, elem.radius, stiffness))

                        # After this wecould do something simple like...
                        #     "pigment {Blue} }"
                        # except we'll write the color

                    elif elem.type == 'ELLIPSOID':
                        # location is modified by scale
                        tabWrite("sphere { <%.6g, %.6g, %.6g>, %.4g, %.4g }\n" % \
                                 (loc.x / elem.size_x, loc.y / elem.size_y, loc.z / elem.size_z,
                                  elem.radius, stiffness))
                        tabWrite("scale <%.6g, %.6g, %.6g> \n" % \
                                 (elem.size_x, elem.size_y, elem.size_z))

                if material:
                    diffuse_color = material.diffuse_color
                    trans = 1.0 - material.alpha
                    if material.use_transparency and material.transparency_method == 'RAYTRACE':
                        povFilter = material.raytrace_transparency.filter * (1.0 - material.alpha)
                        trans = (1.0 - material.alpha) - povFilter
                    else:
                        povFilter = 0.0

                    material_finish = materialNames[material.name]

                    tabWrite("pigment {rgbft<%.3g, %.3g, %.3g, %.3g, %.3g>} \n" % \
                             (diffuse_color[0], diffuse_color[1], diffuse_color[2],
                              povFilter, trans))
                    tabWrite("finish {%s}\n" % safety(material_finish, Level=2))

                else:
                    tabWrite("pigment {rgb<1 1 1>} \n")
                    # Write the finish last.
                    tabWrite("finish {%s}\n" % (safety(DEF_MAT_NAME, Level=2)))

                writeObjectMaterial(material, ob)

                writeMatrix(global_matrix * ob.matrix_world)
                # Importance for radiosity sampling added here
                tabWrite("radiosity { \n")
                tabWrite("importance %3g \n" % importance)
                tabWrite("}\n")

                tabWrite("}\n")  # End of Metaball block

                if comments and len(metas) >= 1:
                    file.write("\n")

#    objectNames = {}
    DEF_OBJ_NAME = "Default"

    def exportMeshes(scene, sel):
#        obmatslist = []
#        def hasUniqueMaterial():
#            # Grab materials attached to object instances ...
#            if hasattr(ob, 'material_slots'):
#                for ms in ob.material_slots:
#                    if ms.material is not None and ms.link == 'OBJECT':
#                        if ms.material in obmatslist:
#                            return False
#                        else:
#                            obmatslist.append(ms.material)
#                            return True
#        def hasObjectMaterial(ob):
#            # Grab materials attached to object instances ...
#            if hasattr(ob, 'material_slots'):
#                for ms in ob.material_slots:
#                    if ms.material is not None and ms.link == 'OBJECT':
#                        # If there is at least one material slot linked to the object
#                        # and not the data (mesh), always create a new, "private" data instance.
#                        return True
#            return False
        # For objects using local material(s) only!
        # This is a mapping between a tuple (dataname, materialnames, ...), and the POV dataname.
        # As only objects using:
        #     * The same data.
        #     * EXACTLY the same materials, in EXACTLY the same sockets.
        # ... can share a same instance in POV export.
        obmats2data = {}

        def checkObjectMaterials(ob, name, dataname):
            if hasattr(ob, 'material_slots'):
                has_local_mats = False
                key = [dataname]
                for ms in ob.material_slots:
                    if ms.material is not None:
                        key.append(ms.material.name)
                        if ms.link == 'OBJECT' and not has_local_mats:
                            has_local_mats = True
                    else:
                        # Even if the slot is empty, it is important to grab it...
                        key.append("")
                if has_local_mats:
                    # If this object uses local material(s), lets find if another object
                    # using the same data and exactly the same list of materials
                    # (in the same slots) has already been processed...
                    # Note that here also, we use object name as new, unique dataname for Pov.
                    key = tuple(key)  # Lists are not hashable...
                    if key not in obmats2data:
                        obmats2data[key] = name
                    return obmats2data[key]
            return None

        data_ref = {}

        def store(scene, ob, name, dataname, matrix):
            # The Object needs to be written at least once but if its data is
            # already in data_ref this has already been done.
            # This func returns the "povray" name of the data, or None
            # if no writing is needed.
            if ob.is_modified(scene, 'RENDER'):
                # Data modified.
                # Create unique entry in data_ref by using object name
                # (always unique in Blender) as data name.
                data_ref[name] = [(name, MatrixAsPovString(matrix))]
                return name
            # Here, we replace dataname by the value returned by checkObjectMaterials, only if
            # it is not evaluated to False (i.e. only if the object uses some local material(s)).
            dataname = checkObjectMaterials(ob, name, dataname) or dataname
            if dataname in data_ref:
                # Data already known, just add the object instance.
                data_ref[dataname].append((name, MatrixAsPovString(matrix)))
                # No need to write data
                return None
            else:
                # Data not yet processed, create a new entry in data_ref.
                data_ref[dataname] = [(name, MatrixAsPovString(matrix))]
                return dataname
           
             
        def exportSmoke(smoke_obj_name):
            #if LuxManager.CurrentScene.name == 'preview':
                #return 1, 1, 1, 1.0
            #else:
            flowtype = -1
            smoke_obj = bpy.data.objects[smoke_obj_name]
            domain = None

            # Search smoke domain target for smoke modifiers
            for mod in smoke_obj.modifiers:
                if mod.name == 'Smoke':
                    if mod.smoke_type == 'FLOW':
                        if mod.flow_settings.smoke_flow_type == 'BOTH':
                            flowtype = 2
                        else:
                            if mod.flow_settings.smoke_flow_type == 'SMOKE':
                                flowtype = 0
                            else:
                                if mod.flow_settings.smoke_flow_type == 'FIRE':
                                    flowtype = 1

                    if mod.smoke_type == 'DOMAIN':
                        domain = smoke_obj
                        smoke_modifier = mod

            eps = 0.000001
            if domain is not None:
                #if bpy.app.version[0] >= 2 and bpy.app.version[1] >= 71:
                # Blender version 2.71 supports direct access to smoke data structure
                set = mod.domain_settings
                channeldata = []
                for v in set.density_grid:
                    channeldata.append(v.real)
                    print v.real
                ## Usage en voxel texture:
                # channeldata = []
                # if channel == 'density':
                    # for v in set.density_grid:
                        # channeldata.append(v.real)

                # if channel == 'fire':
                    # for v in set.flame_grid:
                        # channeldata.append(v.real)

                resolution = set.resolution_max
                big_res = []
                big_res.append(set.domain_resolution[0])
                big_res.append(set.domain_resolution[1])
                big_res.append(set.domain_resolution[2])

                if set.use_high_resolution:
                    big_res[0] = big_res[0] * (set.amplify + 1)
                    big_res[1] = big_res[1] * (set.amplify + 1)
                    big_res[2] = big_res[2] * (set.amplify + 1)
                # else:
                    # p = []
                    ##gather smoke domain settings
                    # BBox = domain.bound_box
                    # p.append([BBox[0][0], BBox[0][1], BBox[0][2]])
                    # p.append([BBox[6][0], BBox[6][1], BBox[6][2]])
                    # set = mod.domain_settings
                    # resolution = set.resolution_max
                    # smokecache = set.point_cache
                    # ret = read_cache(smokecache, set.use_high_resolution, set.amplify + 1, flowtype)
                    # res_x = ret[0]
                    # res_y = ret[1]
                    # res_z = ret[2]
                    # density = ret[3]
                    # fire = ret[4]

                    # if res_x * res_y * res_z > 0:
                        ##new cache format
                        # big_res = []
                        # big_res.append(res_x)
                        # big_res.append(res_y)
                        # big_res.append(res_z)
                    # else:
                        # max = domain.dimensions[0]
                        # if (max - domain.dimensions[1]) < -eps:
                            # max = domain.dimensions[1]

                        # if (max - domain.dimensions[2]) < -eps:
                            # max = domain.dimensions[2]

                        # big_res = [int(round(resolution * domain.dimensions[0] / max, 0)),
                                   # int(round(resolution * domain.dimensions[1] / max, 0)),
                                   # int(round(resolution * domain.dimensions[2] / max, 0))]

                    # if set.use_high_resolution:
                        # big_res = [big_res[0] * (set.amplify + 1), big_res[1] * (set.amplify + 1),
                                   # big_res[2] * (set.amplify + 1)]

                    # if channel == 'density':
                        # channeldata = density

                    # if channel == 'fire':
                        # channeldata = fire

                        # sc_fr = '%s/%s/%s/%05d' % (efutil.export_path, efutil.scene_filename(), bpy.context.scene.name, bpy.context.scene.frame_current)
                        #		        if not os.path.exists( sc_fr ):
                        #			        os.makedirs(sc_fr)
                        #
                        #       		smoke_filename = '%s.smoke' % bpy.path.clean_name(domain.name)
                        #	        	smoke_path = '/'.join([sc_fr, smoke_filename])
                        #
                        #		        with open(smoke_path, 'wb') as smoke_file:
                        #			        # Binary densitygrid file format
                        #			        #
                        #			        # File header
                        #	        		smoke_file.write(b'SMOKE')        #magic number
                        #		        	smoke_file.write(struct.pack('<I', big_res[0]))
                        #			        smoke_file.write(struct.pack('<I', big_res[1]))
                        #       			smoke_file.write(struct.pack('<I', big_res[2]))
                        # Density data
                        #       			smoke_file.write(struct.pack('<%df'%len(channeldata), *channeldata))
                        #
                        #	        	LuxLog('Binary SMOKE file written: %s' % (smoke_path))

        #return big_res[0], big_res[1], big_res[2], channeldata

                mydf3 = df3.df3(big_res[0],big_res[1],big_res[2])
                sim_sizeX, sim_sizeY, sim_sizeZ = mydf3.size()
                for x in xrange(sim_sizeX):
                    for y in xrange(sim_sizeY):
                        for z in xrange(sim_sizeZ):
                            mydf3.set(x, y, z, channeldata[((z * sim_sizeY + y) * sim_sizeX + x)])

                mydf3.exportDF3(smokePath)
                print 'Binary smoke.df3 file written in preview directory'
                if comments:
                    file.write("\n//--Smoke--\n\n")

                # Note: We start with a default unit cube.
                #       This is mandatory to read correctly df3 data - otherwise we could just directly use bbox
                #       coordinates from the start, and avoid scale/translate operations at the end...
                file.write("box{<0,0,0>, <1,1,1>\n")
                file.write("    pigment{ rgbt 1 }\n")
                file.write("    hollow\n")
                file.write("    interior{ //---------------------\n")
                file.write("        media{ method 3\n")
                file.write("               emission <1,1,1>*1\n")# 0>1 for dark smoke to white vapour
                file.write("               scattering{ 1, // Type\n")
                file.write("                  <1,1,1>*0.1\n")
                file.write("                } // end scattering\n")
                file.write("                density{density_file df3 \"%s\"\n" % (smokePath))
                file.write("                        color_map {\n")
                file.write("                        [0.00 rgb 0]\n")
                file.write("                        [0.05 rgb 0]\n")
                file.write("                        [0.20 rgb 0.2]\n")
                file.write("                        [0.30 rgb 0.6]\n")
                file.write("                        [0.40 rgb 1]\n")
                file.write("                        [1.00 rgb 1]\n")
                file.write("                       } // end color_map\n")
                file.write("               } // end of density\n")
                file.write("               samples %i // higher = more precise\n" % resolution)
                file.write("         } // end of media --------------------------\n")
                file.write("    } // end of interior\n")

                # START OF TRANSFORMATIONS

                # Size to consider here are bbox dimensions (i.e. still in object space, *before* applying
                # loc/rot/scale and other transformations (like parent stuff), aka matrix_world).
                bbox = smoke_obj.bound_box
                dim = [abs(bbox[6][0] - bbox[0][0]), abs(bbox[6][1] - bbox[0][1]), abs(bbox[6][2] - bbox[0][2])]

                # We scale our cube to get its final size and shapes but still in *object* space (same as Blender's bbox).
                file.write("scale<%.6g,%.6g,%.6g>\n" % (dim[0], dim[1], dim[2]))

                # We offset our cube such that (0,0,0) coordinate matches Blender's object center.
                file.write("translate<%.6g,%.6g,%.6g>\n" % (bbox[0][0], bbox[0][1], bbox[0][2]))

                # We apply object's transformations to get final loc/rot/size in world space!
                # Note: we could combine the two previous transformations with this matrix directly...
                writeMatrix(global_matrix * smoke_obj.matrix_world)

                # END OF TRANSFORMATIONS

                file.write("}\n")

                
                #file.write("	            interpolate 1\n")
                #file.write("	            frequency 0\n")
                #file.write("	}\n")
                #file.write("}\n")                            
                
        ob_num = 0
        for ob in sel:
            ob_num += 1

            # XXX I moved all those checks here, as there is no need to compute names
            #     for object we won't export here!
            if ob.type in set(['LAMP', 'CAMERA', 'EMPTY', 'META', 'ARMATURE', 'LATTICE']):
                continue
            smokeFlag=False
            for mod in ob.modifiers:
                if mod and hasattr(mod, 'smoke_type'):
                    smokeFlag=True
                    if (mod.smoke_type == 'DOMAIN'):
                        exportSmoke(ob.name)
                    break # don't render domain mesh or flow emitter mesh, skip to next object.
            if not smokeFlag:    
                # Export Hair
                renderEmitter = True
                if hasattr(ob, 'particle_systems'):
                    renderEmitter = False
                    for pSys in ob.particle_systems:
                        if pSys.settings.use_render_emitter:
                            renderEmitter = True
                        for mod in [m for m in ob.modifiers if (m is not None) and (m.type == 'PARTICLE_SYSTEM')]:
                            if (pSys.settings.render_type == 'PATH') and mod.show_render and (pSys.name == mod.particle_system.name):
                                tstart = time.time()
                                texturedHair=0
                                if ob.active_material is not None:
                                    pmaterial = ob.material_slots[pSys.settings.material - 1].material
                                    for th in pmaterial.texture_slots:
                                        if th and th.use:
                                            if (th.texture.type == 'IMAGE' and th.texture.image) or th.texture.type != 'IMAGE':
                                                if th.use_map_color_diffuse:
                                                    texturedHair=1
                                    if pmaterial.strand.use_blender_units:
                                        strandStart = pmaterial.strand.root_size
                                        strandEnd = pmaterial.strand.tip_size
                                        strandShape = pmaterial.strand.shape 
                                    else:  # Blender unit conversion
                                        strandStart = pmaterial.strand.root_size / 200.0
                                        strandEnd = pmaterial.strand.tip_size / 200.0
                                        strandShape = pmaterial.strand.shape
                                else:
                                    pmaterial = "default"  # No material assigned in blender, use default one
                                    strandStart = 0.01
                                    strandEnd = 0.01
                                    strandShape = 0.0
                                # Set the number of particles to render count rather than 3d view display    
                                pSys.set_resolution(scene, ob, 'RENDER')    
                                steps = pSys.settings.draw_step
                                steps = 3 ** steps # or (power of 2 rather than 3) + 1 # Formerly : len(particle.hair_keys)
                                
                                totalNumberOfHairs = ( len(pSys.particles) + len(pSys.child_particles) )
                                #hairCounter = 0
                                file.write('#declare HairArray = array[%i] {\n' % totalNumberOfHairs)
                                for pindex in xrange(0, totalNumberOfHairs):

                                    #if particle.is_exist and particle.is_visible:
                                        #hairCounter += 1
                                        #controlPointCounter = 0
                                        # Each hair is represented as a separate sphere_sweep in POV-Ray.
                                        
                                        file.write('sphere_sweep{')
                                        if pSys.settings.use_hair_bspline:
                                            file.write('b_spline ')
                                            file.write('%i,\n' % (steps + 2))  # +2 because the first point needs tripling to be more than a handle in POV
                                        else:
                                            file.write('linear_spline ')
                                            file.write('%i,\n' % (steps))
                                        #changing world coordinates to object local coordinates by multiplying with inverted matrix    
                                        initCo = ob.matrix_world.inverted()*(pSys.co_hair(ob, pindex, 0))
                                        if ob.active_material is not None:
                                            pmaterial = ob.material_slots[pSys.settings.material-1].material
                                            for th in pmaterial.texture_slots:
                                                if th and th.use and th.use_map_color_diffuse:
                                                    #treat POV textures as bitmaps
                                                    if (th.texture.type == 'IMAGE' and th.texture.image and th.texture_coords == 'UV' and ob.data.uv_textures != None): # or (th.texture.pov.tex_pattern_type != 'emulator' and th.texture_coords == 'UV' and ob.data.uv_textures != None):
                                                        image=th.texture.image
                                                        image_width = image.size[0]
                                                        image_height = image.size[1]
                                                        image_pixels = image.pixels[:]
                                                        uv_co = pSys.uv_on_emitter(mod, pSys.particles[pindex], pindex, 0)
                                                        x_co = round(uv_co[0] * (image_width - 1))
                                                        y_co = round(uv_co[1] * (image_height - 1))
                                                        pixelnumber = (image_width * y_co) + x_co
                                                        r = image_pixels[pixelnumber*4]
                                                        g = image_pixels[pixelnumber*4+1]
                                                        b = image_pixels[pixelnumber*4+2]
                                                        a = image_pixels[pixelnumber*4+3]
                                                        initColor=(r,g,b,a)                                              
                                                    else:
                                                        #only overwrite variable for each competing texture for now
                                                        initColor=th.texture.evaluate((initCo[0],initCo[1],initCo[2]))
                                        for step in xrange(0, steps):
                                            co = pSys.co_hair(ob, pindex, step)
                                        #for controlPoint in particle.hair_keys:
                                            if pSys.settings.clump_factor != 0:
                                                hDiameter = pSys.settings.clump_factor / 200.0 * random.uniform(0.5, 1)
                                            elif step == 0:
                                                hDiameter = strandStart
                                            else:
                                                hDiameter += (strandEnd-strandStart)/(pSys.settings.draw_step+1) #XXX +1 or not?
                                            if step == 0 and pSys.settings.use_hair_bspline:
                                                # Write three times the first point to compensate pov Bezier handling
                                                file.write('<%.6g,%.6g,%.6g>,%.7g,\n' % (co[0], co[1], co[2], abs(hDiameter)))
                                                file.write('<%.6g,%.6g,%.6g>,%.7g,\n' % (co[0], co[1], co[2], abs(hDiameter)))                                          
                                                #file.write('<%.6g,%.6g,%.6g>,%.7g' % (particle.location[0], particle.location[1], particle.location[2], abs(hDiameter))) # Useless because particle location is the tip, not the root.
                                                #file.write(',\n')
                                            #controlPointCounter += 1
                                            #totalNumberOfHairs += len(pSys.particles)# len(particle.hair_keys)
                                                 
                                          # Each control point is written out, along with the radius of the
                                          # hair at that point.
                                            file.write('<%.6g,%.6g,%.6g>,%.7g' % (co[0], co[1], co[2], abs(hDiameter)))

                                          # All coordinates except the last need a following comma.

                                            if step != steps - 1:
                                                file.write(',\n')
                                            else:
                                                if texturedHair:
                                                    # Write pigment and alpha (between Pov and Blender alpha 0 and 1 are reversed)
                                                    file.write('\npigment{ color rgbf < %.3g, %.3g, %.3g, %.3g> }\n' %(initColor[0], initColor[1], initColor[2], 1.0-initColor[3]))
                                                # End the sphere_sweep declaration for this hair
                                                file.write('}\n')
                                            
                                          # All but the final sphere_sweep (each array element) needs a terminating comma.

                                        if pindex != totalNumberOfHairs:
                                            file.write(',\n')
                                        else:
                                            file.write('\n')

                                # End the array declaration.

                                file.write('}\n')
                                file.write('\n')
                                
                                if not texturedHair:
                                    # Pick up the hair material diffuse color and create a default POV-Ray hair texture.

                                    file.write('#ifndef (HairTexture)\n')
                                    file.write('  #declare HairTexture = texture {\n')
                                    file.write('    pigment {rgbt <%s,%s,%s,%s>}\n' % (pmaterial.diffuse_color[0], pmaterial.diffuse_color[1], pmaterial.diffuse_color[2], (pmaterial.strand.width_fade + 0.05)))
                                    file.write('  }\n')
                                    file.write('#end\n')
                                    file.write('\n')

                                # Dynamically create a union of the hairstrands (or a subset of them).
                                # By default use every hairstrand, commented line is for hand tweaking test renders.
                                file.write('//Increasing HairStep divides the amount of hair for test renders.\n')
                                file.write('#ifndef(HairStep) #declare HairStep = 1; #end\n')
                                file.write('union{\n')
                                file.write('  #local I = 0;\n')
                                file.write('  #while (I < %i)\n' % totalNumberOfHairs)
                                file.write('    object {HairArray[I]')
                                if not texturedHair:
                                    file.write(' texture{HairTexture}\n')
                                else:
                                    file.write('\n')
                                # Translucency of the hair:
                                file.write('        hollow\n')
                                file.write('        double_illuminate\n')
                                file.write('        interior {\n')
                                file.write('            ior 1.45\n')
                                file.write('            media {\n')
                                file.write('                scattering { 1, 10*<0.73, 0.35, 0.15> /*extinction 0*/ }\n')
                                file.write('                absorption 10/<0.83, 0.75, 0.15>\n')
                                file.write('                samples 1\n')
                                file.write('                method 2\n')
                                file.write('                density {\n')
                                file.write('                    color_map {\n')
                                file.write('                        [0.0 rgb <0.83, 0.45, 0.35>]\n')
                                file.write('                        [0.5 rgb <0.8, 0.8, 0.4>]\n')
                                file.write('                        [1.0 rgb <1,1,1>]\n')
                                file.write('                    }\n')
                                file.write('                }\n')
                                file.write('            }\n')
                                file.write('        }\n')
                                file.write('    }\n')
                                
                                file.write('    #local I = I + HairStep;\n')
                                file.write('  #end\n')
                                
                                writeMatrix(global_matrix * ob.matrix_world)

                                
                                file.write('}')
                                print 'Totals hairstrands written: %i' % totalNumberOfHairs
                                print 'Number of tufts (particle systems)', len(ob.particle_systems)
                                
                                # Set back the displayed number of particles to preview count
                                pSys.set_resolution(scene, ob, 'PREVIEW')
                                
                                if renderEmitter == False:
                                    continue #don't render mesh, skip to next object.
                try:
                    me = ob.to_mesh(scene, True, 'RENDER')
                except:
                    # happens when curves cant be made into meshes because of no-data
                    continue

                importance = ob.pov.importance_value
                me_materials = me.materials
                me_faces = me.tessfaces[:]
                
                if not me or not me_faces:
                    continue

    #############################################
                # Generating a name for object just like materials to be able to use it
                # (baking for now or anything else).
                # XXX I don't understand that:&nbsp;if we are here, sel if a non-empty iterable,
                #     so this condition is always True, IMO -- mont29
                if sel:
                    name_orig = "OB" + ob.name
                    dataname_orig = "DATA" + ob.data.name
                else:
                    name_orig = DEF_OBJ_NAME
                    dataname_orig = DEF_OBJ_NAME
                name = string_strip_hyphen(bpy.path.clean_name(name_orig))
                dataname = string_strip_hyphen(bpy.path.clean_name(dataname_orig))
    ##            for slot in ob.material_slots:
    ##                if slot.material is not None and slot.link == 'OBJECT':
    ##                    obmaterial = slot.material

    #############################################

                if info_callback:
                    info_callback("Object %2.d of %2.d (%s)" % (ob_num, len(sel), ob.name))

                #if ob.type != 'MESH':
                #    continue
                # me = ob.data

                matrix = global_matrix * ob.matrix_world
                povdataname = store(scene, ob, name, dataname, matrix)
                if povdataname is None:
                    print "This is an instance"
                    continue

                print "Writing Down First Occurence"

                uv_textures = me.tessface_uv_textures
                if len(uv_textures) > 0:
                    if me.uv_textures.active and uv_textures.active.data:
                        uv_layer = uv_textures.active.data
                else:
                    uv_layer = None

                try:
                    #vcol_layer = me.vertex_colors.active.data
                    vcol_layer = me.tessface_vertex_colors.active.data
                except AttributeError:
                    vcol_layer = None

                faces_verts = [f.vertices[:] for f in me_faces]
                faces_normals = [f.normal[:] for f in me_faces]
                verts_normals = [v.normal[:] for v in me.vertices]

                # quads incur an extra face
                quadCount = sum(1 for f in faces_verts if len(f) == 4)

                # Use named declaration to allow reference e.g. for baking. MR
                file.write("\n")
                tabWrite("#declare %s =\n" % povdataname)
                tabWrite("mesh2 {\n")
                tabWrite("vertex_vectors {\n")
                tabWrite("%d" % len(me.vertices))  # vert count

                tabStr = tab * tabLevel
                for v in me.vertices:
                    if linebreaksinlists:
                        file.write(",\n")
                        file.write(tabStr + "<%.6f, %.6f, %.6f>" % v.co[:])  # vert count
                    else:
                        file.write(", ")
                        file.write("<%.6f, %.6f, %.6f>" % v.co[:])  # vert count
                    #tabWrite("<%.6f, %.6f, %.6f>" % v.co[:])  # vert count
                file.write("\n")
                tabWrite("}\n")

                # Build unique Normal list
                uniqueNormals = {}
                for fi, f in enumerate(me_faces):
                    fv = faces_verts[fi]
                    # [-1] is a dummy index, use a list so we can modify in place
                    if f.use_smooth:  # Use vertex normals
                        for v in fv:
                            key = verts_normals[v]
                            uniqueNormals[key] = [-1]
                    else:  # Use face normal
                        key = faces_normals[fi]
                        uniqueNormals[key] = [-1]

                tabWrite("normal_vectors {\n")
                tabWrite("%d" % len(uniqueNormals))  # vert count
                idx = 0
                tabStr = tab * tabLevel
                for no, index in uniqueNormals.items():
                    if linebreaksinlists:
                        file.write(",\n")
                        file.write(tabStr + "<%.6f, %.6f, %.6f>" % no)  # vert count
                    else:
                        file.write(", ")
                        file.write("<%.6f, %.6f, %.6f>" % no)  # vert count
                    index[0] = idx
                    idx += 1
                file.write("\n")
                tabWrite("}\n")

                # Vertex colors
                vertCols = {}  # Use for material colors also.

                if uv_layer:
                    # Generate unique UV's
                    uniqueUVs = {}
                    #n = 0
                    for fi, uv in enumerate(uv_layer):

                        if len(faces_verts[fi]) == 4:
                            uvs = uv_layer[fi].uv[0], uv_layer[fi].uv[1], uv_layer[fi].uv[2], uv_layer[fi].uv[3]
                        else:
                            uvs = uv_layer[fi].uv[0], uv_layer[fi].uv[1], uv_layer[fi].uv[2]

                        for uv in uvs:
                            uniqueUVs[uv[:]] = [-1]

                    tabWrite("uv_vectors {\n")
                    #print unique_uvs
                    tabWrite("%d" % len(uniqueUVs))  # vert count
                    idx = 0
                    tabStr = tab * tabLevel
                    for uv, index in uniqueUVs.items():
                        if linebreaksinlists:
                            file.write(",\n")
                            file.write(tabStr + "<%.6f, %.6f>" % uv)
                        else:
                            file.write(", ")
                            file.write("<%.6f, %.6f>" % uv)
                        index[0] = idx
                        idx += 1
                    '''
                    else:
                        # Just add 1 dummy vector, no real UV's
                        tabWrite('1') # vert count
                        file.write(',\n\t\t<0.0, 0.0>')
                    '''
                    file.write("\n")
                    tabWrite("}\n")

                if me.vertex_colors:
                    #Write down vertex colors as a texture for each vertex
                    tabWrite("texture_list {\n")
                    tabWrite("%d\n" % (((len(me_faces)-quadCount) * 3 )+ quadCount * 4)) # works only with tris and quad mesh for now
                    VcolIdx=0
                    if comments:
                        file.write("\n  //Vertex colors: one simple pigment texture per vertex\n")
                    for fi, f in enumerate(me_faces):
                        # annoying, index may be invalid
                        material_index = f.material_index
                        try:
                            material = me_materials[material_index]
                        except:
                            material = None
                        if material: #and material.use_vertex_color_paint: #Always use vertex color when there is some for now
                         
                            col = vcol_layer[fi]

                            if len(faces_verts[fi]) == 4:
                                cols = col.color1, col.color2, col.color3, col.color4
                            else:
                                cols = col.color1, col.color2, col.color3

                            for col in cols:
                                key = col[0], col[1], col[2], material_index  # Material index!
                                VcolIdx+=1
                                vertCols[key] = [VcolIdx]
                                if linebreaksinlists:
                                    tabWrite("texture {pigment{ color rgb <%6f,%6f,%6f> }}\n" % (col[0], col[1], col[2]))
                                else:
                                    tabWrite("texture {pigment{ color rgb <%6f,%6f,%6f> }}" % (col[0], col[1], col[2]))
                                    tabStr = tab * tabLevel
                        else:
                            if material:
                                # Multiply diffuse with SSS Color
                                if material.subsurface_scattering.use:
                                    diffuse_color = [i * j for i, j in izip(material.subsurface_scattering.color[:], material.diffuse_color[:])]
                                    key = diffuse_color[0], diffuse_color[1], diffuse_color[2], \
                                          material_index
                                    vertCols[key] = [-1]
                                else:
                                    diffuse_color = material.diffuse_color[:]
                                    key = diffuse_color[0], diffuse_color[1], diffuse_color[2], \
                                          material_index
                                    vertCols[key] = [-1]

                    tabWrite("\n}\n")                
                    # Face indices
                    tabWrite("\nface_indices {\n")
                    tabWrite("%d" % (len(me_faces) + quadCount))  # faces count
                    tabStr = tab * tabLevel

                    for fi, f in enumerate(me_faces):
                        fv = faces_verts[fi]
                        material_index = f.material_index
                        if len(fv) == 4:
                            indices = (0, 1, 2), (0, 2, 3)
                        else:
                            indices = ((0, 1, 2),)

                        if vcol_layer:
                            col = vcol_layer[fi]

                            if len(fv) == 4:
                                cols = col.color1, col.color2, col.color3, col.color4
                            else:
                                cols = col.color1, col.color2, col.color3

                        if not me_materials or me_materials[material_index] is None:  # No materials
                            for i1, i2, i3 in indices:
                                if linebreaksinlists:
                                    file.write(",\n")
                                    # vert count
                                    file.write(tabStr + "<%d,%d,%d>" % (fv[i1], fv[i2], fv[i3]))
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>" % (fv[i1], fv[i2], fv[i3]))  # vert count
                        else:
                            material = me_materials[material_index]
                            for i1, i2, i3 in indices:
                                if me.vertex_colors: #and material.use_vertex_color_paint:
                                    # Color per vertex - vertex color

                                    col1 = cols[i1]
                                    col2 = cols[i2]
                                    col3 = cols[i3]

                                    ci1 = vertCols[col1[0], col1[1], col1[2], material_index][0]
                                    ci2 = vertCols[col2[0], col2[1], col2[2], material_index][0]
                                    ci3 = vertCols[col3[0], col3[1], col3[2], material_index][0]
                                else:
                                    # Color per material - flat material color
                                    if material.subsurface_scattering.use:
                                        diffuse_color = [i * j for i, j in izip(material.subsurface_scattering.color[:], material.diffuse_color[:])]
                                    else:
                                        diffuse_color = material.diffuse_color[:]
                                    ci1 = ci2 = ci3 = vertCols[diffuse_color[0], diffuse_color[1], \
                                                      diffuse_color[2], f.material_index][0]
                                    # ci are zero based index so we'll subtract 1 from them
                                if linebreaksinlists:
                                    file.write(",\n")
                                    file.write(tabStr + "<%d,%d,%d>, %d,%d,%d" % \
                                               (fv[i1], fv[i2], fv[i3], ci1-1, ci2-1, ci3-1))  # vert count 
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>, %d,%d,%d" % \
                                               (fv[i1], fv[i2], fv[i3], ci1-1, ci2-1, ci3-1))  # vert count

                    file.write("\n")
                    tabWrite("}\n")

                    # normal_indices indices
                    tabWrite("normal_indices {\n")
                    tabWrite("%d" % (len(me_faces) + quadCount))  # faces count
                    tabStr = tab * tabLevel
                    for fi, fv in enumerate(faces_verts):

                        if len(fv) == 4:
                            indices = (0, 1, 2), (0, 2, 3)
                        else:
                            indices = ((0, 1, 2),)

                        for i1, i2, i3 in indices:
                            if me_faces[fi].use_smooth:
                                if linebreaksinlists:
                                    file.write(",\n")
                                    file.write(tabStr + "<%d,%d,%d>" %\
                                    (uniqueNormals[verts_normals[fv[i1]]][0],\
                                     uniqueNormals[verts_normals[fv[i2]]][0],\
                                     uniqueNormals[verts_normals[fv[i3]]][0]))  # vert count
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>" %\
                                    (uniqueNormals[verts_normals[fv[i1]]][0],\
                                     uniqueNormals[verts_normals[fv[i2]]][0],\
                                     uniqueNormals[verts_normals[fv[i3]]][0]))  # vert count
                            else:
                                idx = uniqueNormals[faces_normals[fi]][0]
                                if linebreaksinlists:
                                    file.write(",\n")
                                    file.write(tabStr + "<%d,%d,%d>" % (idx, idx, idx))  # vert count
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>" % (idx, idx, idx))  # vert count

                    file.write("\n")
                    tabWrite("}\n")

                    if uv_layer:
                        tabWrite("uv_indices {\n")
                        tabWrite("%d" % (len(me_faces) + quadCount))  # faces count
                        tabStr = tab * tabLevel
                        for fi, fv in enumerate(faces_verts):

                            if len(fv) == 4:
                                indices = (0, 1, 2), (0, 2, 3)
                            else:
                                indices = ((0, 1, 2),)

                            uv = uv_layer[fi]
                            if len(faces_verts[fi]) == 4:
                                uvs = uv.uv[0][:], uv.uv[1][:], uv.uv[2][:], uv.uv[3][:]
                            else:
                                uvs = uv.uv[0][:], uv.uv[1][:], uv.uv[2][:]

                            for i1, i2, i3 in indices:
                                if linebreaksinlists:
                                    file.write(",\n")
                                    file.write(tabStr + "<%d,%d,%d>" % (
                                             uniqueUVs[uvs[i1]][0],\
                                             uniqueUVs[uvs[i2]][0],\
                                             uniqueUVs[uvs[i3]][0]))
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>" % (
                                             uniqueUVs[uvs[i1]][0],\
                                             uniqueUVs[uvs[i2]][0],\
                                             uniqueUVs[uvs[i3]][0]))

                        file.write("\n")
                        tabWrite("}\n")

                    if me.materials:
                        try:
                            material = me.materials[0]  # dodgy
                            writeObjectMaterial(material, ob)
                        except IndexError:
                            print me

                    #Importance for radiosity sampling added here:
                    tabWrite("radiosity { \n")
                    tabWrite("importance %3g \n" % importance)
                    tabWrite("}\n")

                    tabWrite("}\n")  # End of mesh block
                else:
                    # No vertex colors, so write material colors as vertex colors
                    for i, material in enumerate(me_materials):

                        if material:
                            # Multiply diffuse with SSS Color
                            if material.subsurface_scattering.use:
                                diffuse_color = [i * j for i, j in izip(material.subsurface_scattering.color[:], material.diffuse_color[:])]
                                key = diffuse_color[0], diffuse_color[1], diffuse_color[2], i  # i == f.mat
                                vertCols[key] = [-1]
                            else:
                                diffuse_color = material.diffuse_color[:]
                                key = diffuse_color[0], diffuse_color[1], diffuse_color[2], i  # i == f.mat
                                vertCols[key] = [-1]

                            idx = 0
                            LocalMaterialNames = []                       
                            for col, index in vertCols.items():
                                #if me_materials:
                                mater = me_materials[col[3]]
                                if me_materials is None: #XXX working?
                                    material_finish = DEF_MAT_NAME  # not working properly,
                                    trans = 0.0

                                else:
                                    material_finish = materialNames[mater.name]                        
                                    if mater.use_transparency:
                                        trans = 1.0 - mater.alpha
                                    else:
                                        trans = 0.0                            
                                    if (mater.specular_color.s == 0.0):
                                        colored_specular_found = False
                                    else:
                                        colored_specular_found = True

                                    if mater.use_transparency and mater.transparency_method == 'RAYTRACE':
                                        povFilter = mater.raytrace_transparency.filter * (1.0 - mater.alpha)
                                        trans = (1.0 - mater.alpha) - povFilter
                                    else:
                                        povFilter = 0.0
                                        
                                    ##############SF
                                    texturesDif = ""
                                    texturesSpec = ""
                                    texturesNorm = ""
                                    texturesAlpha = ""
                                    #proceduralFlag=False
                                    for t in mater.texture_slots:
                                        if t and t.use and t.texture.type != 'IMAGE' and t.texture.type != 'NONE':
                                            proceduralFlag=True
                                            image_filename = "PAT_%s"%string_strip_hyphen(bpy.path.clean_name(t.texture.name))
                                            if image_filename:
                                                if t.use_map_color_diffuse:
                                                    texturesDif = image_filename
                                                    # colvalue = t.default_value  # UNUSED
                                                    t_dif = t
                                                    if t_dif.texture.pov.tex_gamma_enable:
                                                        imgGamma = (" gamma %.3g " % t_dif.texture.pov.tex_gamma_value)
                                                if t.use_map_specular or t.use_map_raymir:
                                                    texturesSpec = image_filename
                                                    # colvalue = t.default_value  # UNUSED
                                                    t_spec = t
                                                if t.use_map_normal:
                                                    texturesNorm = image_filename
                                                    # colvalue = t.normal_factor * 10.0  # UNUSED
                                                    #textNormName=t.texture.image.name + ".normal"
                                                    #was the above used? --MR
                                                    t_nor = t
                                                if t.use_map_alpha:
                                                    texturesAlpha = image_filename
                                                    # colvalue = t.alpha_factor * 10.0  # UNUSED
                                                    #textDispName=t.texture.image.name + ".displ"
                                                    #was the above used? --MR
                                                    t_alpha = t

                                        if t and t.texture.type == 'IMAGE' and t.use and t.texture.image and t.texture.pov.tex_pattern_type == 'emulator':
                                            proceduralFlag=False
                                            if t.texture.image.packed_file:
                                                orig_image_filename=t.texture.image.filepath_raw
                                                workDir = bpy.utils.resource_path('USER')
                                                previewDir=os.path.join(workDir, "preview")
                                                unpackedfilename= os.path.join(previewDir,("unpacked_img_"+(string_strip_hyphen(bpy.path.clean_name(t.texture.name)))))
                                                if not os.path.exists(unpackedfilename):
                                                    # record which images that were newly copied and can be safely
                                                    # cleaned up
                                                    unpacked_images.append(unpackedfilename)                                            
                                                t.texture.image.filepath_raw=unpackedfilename
                                                t.texture.image.save()
                                                image_filename = unpackedfilename
                                                t.texture.image.filepath_raw=orig_image_filename
                                            else:
                                                image_filename = path_image(t.texture.image)
                                            # IMAGE SEQUENCE BEGINS
                                            if image_filename:
                                                if bpy.data.images[t.texture.image.name].source == 'SEQUENCE':
                                                    korvaa = "." + str(bpy.data.textures[t.texture.name].image_user.frame_offset + 1).zfill(3) + "."
                                                    image_filename = image_filename.replace(".001.", korvaa)
                                                    print " seq debug "
                                                    print image_filename
                                            # IMAGE SEQUENCE ENDS
                                            imgGamma = ""
                                            if image_filename:
                                                if t.use_map_color_diffuse:
                                                    texturesDif = image_filename
                                                    # colvalue = t.default_value  # UNUSED
                                                    t_dif = t
                                                    if t_dif.texture.pov.tex_gamma_enable:
                                                        imgGamma = (" gamma %.3g " % t_dif.texture.pov.tex_gamma_value)
                                                if t.use_map_specular or t.use_map_raymir:
                                                    texturesSpec = image_filename
                                                    # colvalue = t.default_value  # UNUSED
                                                    t_spec = t
                                                if t.use_map_normal:
                                                    texturesNorm = image_filename
                                                    # colvalue = t.normal_factor * 10.0  # UNUSED
                                                    #textNormName=t.texture.image.name + ".normal"
                                                    #was the above used? --MR
                                                    t_nor = t
                                                if t.use_map_alpha:
                                                    texturesAlpha = image_filename
                                                    # colvalue = t.alpha_factor * 10.0  # UNUSED
                                                    #textDispName=t.texture.image.name + ".displ"
                                                    #was the above used? --MR
                                                    t_alpha = t

                                    ####################################################################################


                                    file.write("\n")
                                    # THIS AREA NEEDS TO LEAVE THE TEXTURE OPEN UNTIL ALL MAPS ARE WRITTEN DOWN.
                                    # --MR
                                    currentMatName = string_strip_hyphen(materialNames[mater.name])
                                    LocalMaterialNames.append(currentMatName)
                                    file.write("\n #declare MAT_%s = \ntexture{\n" % currentMatName)

                                    ################################################################################
                                    
                                    if mater.pov.replacement_text != "":
                                        file.write("%s\n" % mater.pov.replacement_text)
                                    #################################################################################
                                    if mater.diffuse_shader == 'MINNAERT':
                                        tabWrite("\n")
                                        tabWrite("aoi\n")
                                        tabWrite("texture_map {\n")
                                        tabWrite("[%.3g finish {diffuse %.3g}]\n" % \
                                                 (mater.darkness / 2.0, 2.0 - mater.darkness))
                                        tabWrite("[%.3g\n" % (1.0 - (mater.darkness / 2.0)))

                                    if mater.diffuse_shader == 'FRESNEL':
                                        # For FRESNEL diffuse in POV, we'll layer slope patterned textures
                                        # with lamp vector as the slope vector and nest one slope per lamp
                                        # into each texture map's entry.

                                        c = 1
                                        while (c <= lampCount):
                                            tabWrite("slope { lampTarget%s }\n" % (c))
                                            tabWrite("texture_map {\n")
                                            # Diffuse Fresnel value and factor go up to five,
                                            # other kind of values needed: used the number 5 below to remap
                                            tabWrite("[%.3g finish {diffuse %.3g}]\n" % \
                                                     ((5.0 - mater.diffuse_fresnel) / 5,
                                                      (mater.diffuse_intensity *
                                                       ((5.0 - mater.diffuse_fresnel_factor) / 5))))
                                            tabWrite("[%.3g\n" % ((mater.diffuse_fresnel_factor / 5) *
                                                                  (mater.diffuse_fresnel / 5.0)))
                                            c += 1

                                    # if shader is a 'FRESNEL' or 'MINNAERT': slope pigment pattern or aoi
                                    # and texture map above, the rest below as one of its entry

                                    if texturesSpec != "" or texturesAlpha != "":
                                        if texturesSpec != "":
                                            # tabWrite("\n")
                                            tabWrite("pigment_pattern {\n")
                                            if texturesSpec and texturesSpec.startswith("PAT_"):
                                                tabWrite("function{f%s(x,y,z).grey}" %texturesSpec) 
                                            else:
                                                # POV-Ray "scale" is not a number of repetitions factor, but its
                                                # inverse, a standard scale factor.
                                                # Offset seems needed relatively to scale so probably center of the
                                                # scale is not the same in blender and POV
                                                mappingSpec =imgMapTransforms(t_spec)
                                                # mappingSpec = "translate <%.4g,%.4g,%.4g> scale <%.4g,%.4g,%.4g>\n" % \
                                                              # (-t_spec.offset.x, t_spec.offset.y, t_spec.offset.z,
                                                               # 1.0 / t_spec.scale.x, 1.0 / t_spec.scale.y,
                                                               # 1.0 / t_spec.scale.z)
                                                tabWrite("uv_mapping image_map{%s \"%s\" %s}\n" % \
                                                         (imageFormat(texturesSpec), texturesSpec, imgMap(t_spec)))
                                                tabWrite("%s\n" % mappingSpec)
                                            tabWrite("}\n")
                                            tabWrite("texture_map {\n")
                                            tabWrite("[0 \n")

                                        if texturesDif == "":
                                            if texturesAlpha != "":
                                                tabWrite("\n")
                                                if texturesAlpha and texturesAlpha.startswith("PAT_"):
                                                    tabWrite("function{f%s(x,y,z).transmit}\n" %texturesAlpha) 
                                                else:
                                                    # POV-Ray "scale" is not a number of repetitions factor, but its
                                                    # inverse, a standard scale factor.
                                                    # Offset seems needed relatively to scale so probably center of the
                                                    # scale is not the same in blender and POV
                                                    mappingAlpha = imgMapTransforms(t_alpha)
                                                    # mappingAlpha = " translate <%.4g, %.4g, %.4g> " \
                                                                   # "scale <%.4g, %.4g, %.4g>\n" % \
                                                                   # (-t_alpha.offset.x, -t_alpha.offset.y,
                                                                    # t_alpha.offset.z, 1.0 / t_alpha.scale.x,
                                                                    # 1.0 / t_alpha.scale.y, 1.0 / t_alpha.scale.z)
                                                    tabWrite("pigment {pigment_pattern {uv_mapping image_map" \
                                                             "{%s \"%s\" %s}%s" % \
                                                             (imageFormat(texturesAlpha), texturesAlpha,
                                                              imgMap(t_alpha), mappingAlpha))
                                                tabWrite("}\n")
                                                tabWrite("pigment_map {\n")
                                                tabWrite("[0 color rgbft<0,0,0,1,1>]\n")
                                                tabWrite("[1 color rgbft<%.3g, %.3g, %.3g, %.3g, %.3g>]\n" % \
                                                         (col[0], col[1], col[2], povFilter, trans))
                                                tabWrite("}\n")
                                                tabWrite("}\n")

                                            else:

                                                tabWrite("pigment {rgbft<%.3g, %.3g, %.3g, %.3g, %.3g>}\n" % \
                                                         (col[0], col[1], col[2], povFilter, trans))

                                            if texturesSpec != "":
                                                # Level 1 is no specular
                                                tabWrite("finish {%s}\n" % (safety(material_finish, Level=1)))

                                            else:
                                                # Level 2 is translated spec
                                                tabWrite("finish {%s}\n" % (safety(material_finish, Level=2)))

                                        else:
                                            mappingDif = imgMapTransforms(t_dif)

                                            if texturesAlpha != "":
                                                mappingAlpha = imgMapTransforms(t_alpha)
                                                # mappingAlpha = " translate <%.4g,%.4g,%.4g> " \
                                                               # "scale <%.4g,%.4g,%.4g>" % \
                                                               # (-t_alpha.offset.x, -t_alpha.offset.y,
                                                                # t_alpha.offset.z, 1.0 / t_alpha.scale.x,
                                                                # 1.0 / t_alpha.scale.y, 1.0 / t_alpha.scale.z)
                                                tabWrite("pigment {\n")
                                                tabWrite("pigment_pattern {\n")
                                                if texturesAlpha and texturesAlpha.startswith("PAT_"):
                                                    tabWrite("function{f%s(x,y,z).transmit}\n" %texturesAlpha) 
                                                else:
                                                    tabWrite("uv_mapping image_map{%s \"%s\" %s}%s}\n" % \
                                                             (imageFormat(texturesAlpha), texturesAlpha,
                                                              imgMap(t_alpha), mappingAlpha))
                                                tabWrite("pigment_map {\n")
                                                tabWrite("[0 color rgbft<0,0,0,1,1>]\n")
                                                #if texturesAlpha and texturesAlpha.startswith("PAT_"):
                                                    #tabWrite("[1 pigment{%s}]\n" %texturesDif) 
                                                if texturesDif and not texturesDif.startswith("PAT_"):
                                                    tabWrite("[1 uv_mapping image_map {%s \"%s\" %s} %s]\n" % \
                                                             (imageFormat(texturesDif), texturesDif,
                                                              (imgGamma + imgMap(t_dif)), mappingDif))
                                                elif texturesDif and texturesDif.startswith("PAT_"):
                                                    tabWrite("[1 %s]\n" %texturesDif)                                                          
                                                tabWrite("}\n")
                                                tabWrite("}\n")
                                                if texturesAlpha and texturesAlpha.startswith("PAT_"):
                                                    tabWrite("}\n")

                                            else:
                                                if texturesDif and texturesDif.startswith("PAT_"):
                                                    tabWrite("pigment{%s}\n" %texturesDif) 
                                                else:
                                                    tabWrite("pigment {uv_mapping image_map {%s \"%s\" %s}%s}\n" % \
                                                             (imageFormat(texturesDif), texturesDif,
                                                              (imgGamma + imgMap(t_dif)), mappingDif))

                                            if texturesSpec != "":
                                                # Level 1 is no specular
                                                tabWrite("finish {%s}\n" % (safety(material_finish, Level=1)))

                                            else:
                                                # Level 2 is translated specular
                                                tabWrite("finish {%s}\n" % (safety(material_finish, Level=2)))

                                            ## scale 1 rotate y*0
                                            #imageMap = ("{image_map {%s \"%s\" %s }\n" % \
                                            #            (imageFormat(textures),textures,imgMap(t_dif)))
                                            #tabWrite("uv_mapping pigment %s} %s finish {%s}\n" % \
                                            #         (imageMap,mapping,safety(material_finish)))
                                            #tabWrite("pigment {uv_mapping image_map {%s \"%s\" %s}%s} " \
                                            #         "finish {%s}\n" % \
                                            #         (imageFormat(texturesDif), texturesDif, imgMap(t_dif),
                                            #          mappingDif, safety(material_finish)))
                                        if texturesNorm != "":
                                            ## scale 1 rotate y*0
                                            # POV-Ray "scale" is not a number of repetitions factor, but its
                                            # inverse, a standard scale factor.
                                            # Offset seems needed relatively to scale so probably center of the
                                            # scale is not the same in blender and POV
                                            mappingNor =imgMapTransforms(t_nor)
                                            # mappingNor = " translate <%.4g,%.4g,%.4g> scale <%.4g,%.4g,%.4g>" % \
                                                         # (-t_nor.offset.x, -t_nor.offset.y, t_nor.offset.z,
                                                          # 1.0 / t_nor.scale.x, 1.0 / t_nor.scale.y,
                                                          # 1.0 / t_nor.scale.z)
                                            #imageMapNor = ("{bump_map {%s \"%s\" %s mapping}" % \
                                            #               (imageFormat(texturesNorm),texturesNorm,imgMap(t_nor)))
                                            #We were not using the above maybe we should?
                                            if texturesNorm and texturesNorm.startswith("PAT_"):
                                                tabWrite("normal{function{f%s(x,y,z).grey} bump_size %.4g}\n" %(texturesNorm, t_nor.normal_factor * 10)) 
                                            else:
                                                tabWrite("normal {uv_mapping bump_map " \
                                                         "{%s \"%s\" %s  bump_size %.4g }%s}\n" % \
                                                         (imageFormat(texturesNorm), texturesNorm, imgMap(t_nor),
                                                          t_nor.normal_factor * 10, mappingNor))
                                        if texturesSpec != "":
                                            tabWrite("]\n")
                                        ##################Second index for mapping specular max value###############
                                            tabWrite("[1 \n")

                                    if texturesDif == "" and mater.pov.replacement_text == "":
                                        if texturesAlpha != "":
                                            # POV-Ray "scale" is not a number of repetitions factor, but its inverse,
                                            # a standard scale factor.
                                            # Offset seems needed relatively to scale so probably center of the scale
                                            # is not the same in blender and POV
                                            # Strange that the translation factor for scale is not the same as for
                                            # translate.
                                            # TODO: verify both matches with blender internal.
                                            mappingAlpha = imgMapTransforms(t_alpha)
                                            # mappingAlpha = " translate <%.4g,%.4g,%.4g> scale <%.4g,%.4g,%.4g>\n" % \
                                                           # (-t_alpha.offset.x, -t_alpha.offset.y, t_alpha.offset.z,
                                                            # 1.0 / t_alpha.scale.x, 1.0 / t_alpha.scale.y,
                                                            # 1.0 / t_alpha.scale.z)
                                            if texturesAlpha and texturesAlpha.startswith("PAT_"):
                                                tabWrite("function{f%s(x,y,z).transmit}\n" %texturesAlpha) 
                                            else:
                                                tabWrite("pigment {pigment_pattern {uv_mapping image_map" \
                                                         "{%s \"%s\" %s}%s}\n" % \
                                                         (imageFormat(texturesAlpha), texturesAlpha, imgMap(t_alpha),
                                                          mappingAlpha))
                                            tabWrite("pigment_map {\n")
                                            tabWrite("[0 color rgbft<0,0,0,1,1>]\n")
                                            tabWrite("[1 color rgbft<%.3g, %.3g, %.3g, %.3g, %.3g>]\n" % \
                                                     (col[0], col[1], col[2], povFilter, trans))
                                            tabWrite("}\n")
                                            tabWrite("}\n")

                                        else:
                                            tabWrite("pigment {rgbft<%.3g, %.3g, %.3g, %.3g, %.3g>}\n" % \
                                                     (col[0], col[1], col[2], povFilter, trans))
                                                     
                                                                    
                                        if texturesSpec != "":
                                            # Level 3 is full specular
                                            tabWrite("finish {%s}\n" % (safety(material_finish, Level=3)))
                                            
                                        elif colored_specular_found:
                                            # Level 1 is no specular
                                            tabWrite("finish {%s}\n" % (safety(material_finish, Level=1)))

                                        else:
                                            # Level 2 is translated specular
                                            tabWrite("finish {%s}\n" % (safety(material_finish, Level=2)))

                                    elif mater.pov.replacement_text == "":
                                        mappingDif = imgMapTransforms(t_dif)
                                        # mappingDif = ("scale <%.4g,%.4g,%.4g> translate <%.4g,%.4g,%.4g>" % \
                                                      # ( 1.0 / t_dif.scale.x, 
                                                      # 1.0 / t_dif.scale.y,
                                                      # 1.0 / t_dif.scale.z, 
                                                      # 0.5-(0.5/t_dif.scale.x) + t_dif.offset.x,
                                                      # 0.5-(0.5/t_dif.scale.y) + t_dif.offset.y,
                                                      # 0.5-(0.5/t_dif.scale.z) + t_dif.offset.z))
                                        if texturesAlpha != "":
                                            # Strange that the translation factor for scale is not the same as for
                                            # translate.
                                            # TODO: verify both matches with blender internal.
                                            mappingAlpha = imgMapTransforms(t_alpha)
                                            # mappingAlpha = "translate <%.4g,%.4g,%.4g> scale <%.4g,%.4g,%.4g>" % \
                                                           # (-t_alpha.offset.x, -t_alpha.offset.y, t_alpha.offset.z,
                                                            # 1.0 / t_alpha.scale.x, 1.0 / t_alpha.scale.y,
                                                            # 1.0 / t_alpha.scale.z)
                                            if texturesAlpha and texturesAlpha.startswith("PAT_"):
                                                tabWrite("pigment{pigment_pattern {function{f%s(x,y,z).transmit}}\n" %texturesAlpha)
                                            else:
                                                tabWrite("pigment {pigment_pattern {uv_mapping image_map" \
                                                         "{%s \"%s\" %s}%s}\n" % \
                                                         (imageFormat(texturesAlpha), texturesAlpha, imgMap(t_alpha),
                                                          mappingAlpha))
                                            tabWrite("pigment_map {\n")
                                            tabWrite("[0 color rgbft<0,0,0,1,1>]\n")
                                            if texturesAlpha and texturesAlpha.startswith("PAT_"):
                                                tabWrite("[1 function{f%s(x,y,z).transmit}]\n" %texturesAlpha) 
                                            elif texturesDif and not texturesDif.startswith("PAT_"):                                       
                                                tabWrite("[1 uv_mapping image_map {%s \"%s\" %s} %s]\n" % \
                                                         (imageFormat(texturesDif), texturesDif,
                                                          (imgMap(t_dif) + imgGamma), mappingDif))
                                            elif texturesDif and texturesDif.startswith("PAT_"):
                                                tabWrite("[1 %s]\n" %texturesDif)
                                            tabWrite("}\n")
                                            tabWrite("}\n")

                                        else:
                                            if texturesDif and texturesDif.startswith("PAT_"):
                                                tabWrite("pigment{%s}\n" %texturesDif) 
                                            else:                                    
                                                tabWrite("pigment {\n")
                                                tabWrite("uv_mapping image_map {\n")
                                                #tabWrite("%s \"%s\" %s}%s\n" % \
                                                #         (imageFormat(texturesDif), texturesDif,
                                                #         (imgGamma + imgMap(t_dif)),mappingDif))
                                                tabWrite("%s \"%s\" \n" % (imageFormat(texturesDif), texturesDif))
                                                tabWrite("%s\n" % (imgGamma + imgMap(t_dif)))
                                                tabWrite("}\n")
                                                tabWrite("%s\n" % mappingDif)
                                                tabWrite("}\n")
                                              
                                        if texturesSpec != "":
                                            # Level 3 is full specular
                                            tabWrite("finish {%s}\n" % (safety(material_finish, Level=3)))                  
                                        else:
                                            # Level 2 is translated specular
                                            tabWrite("finish {%s}\n" % (safety(material_finish, Level=2)))

                                        ## scale 1 rotate y*0
                                        #imageMap = ("{image_map {%s \"%s\" %s }" % \
                                        #            (imageFormat(textures), textures,imgMap(t_dif)))
                                        #file.write("\n\t\t\tuv_mapping pigment %s} %s finish {%s}" % \
                                        #           (imageMap, mapping, safety(material_finish)))
                                        #file.write("\n\t\t\tpigment {uv_mapping image_map " \
                                        #           "{%s \"%s\" %s}%s} finish {%s}" % \
                                        #           (imageFormat(texturesDif), texturesDif,imgMap(t_dif),
                                        #            mappingDif, safety(material_finish)))
                                    if texturesNorm != "" and mater.pov.replacement_text == "":
                                        ## scale 1 rotate y*0
                                        # POV-Ray "scale" is not a number of repetitions factor, but its inverse,
                                        # a standard scale factor.
                                        # Offset seems needed relatively to scale so probably center of the scale is
                                        # not the same in blender and POV
                                        mappingNor =imgMapTransforms(t_nor)
                                        # mappingNor = (" translate <%.4g,%.4g,%.4g> scale <%.4g,%.4g,%.4g>" % \
                                                      # (-t_nor.offset.x, -t_nor.offset.y, t_nor.offset.z,
                                                       # 1.0 / t_nor.scale.x, 1.0 / t_nor.scale.y, 1.0 / t_nor.scale.z))
                                        #imageMapNor = ("{bump_map {%s \"%s\" %s mapping}" % \
                                        #               (imageFormat(texturesNorm),texturesNorm,imgMap(t_nor)))
                                        #We were not using the above maybe we should?
                                        if texturesNorm and texturesNorm.startswith("PAT_"):
                                            tabWrite("normal{function{f%s(x,y,z).grey} bump_size %.4g}\n" %(texturesNorm, t_nor.normal_factor * 10))
                                        else:                                    
                                            tabWrite("normal {uv_mapping bump_map {%s \"%s\" %s  bump_size %.4g }%s}\n" % \
                                                     (imageFormat(texturesNorm), texturesNorm, imgMap(t_nor),
                                                      t_nor.normal_factor * 10.0, mappingNor))
                                    if texturesSpec != "" and mater.pov.replacement_text == "":
                                        tabWrite("]\n")

                                        tabWrite("}\n")

                                    #End of slope/ior texture_map
                                    if mater.diffuse_shader == 'MINNAERT' and mater.pov.replacement_text == "":
                                        tabWrite("]\n")
                                        tabWrite("}\n")
                                    if mater.diffuse_shader == 'FRESNEL' and mater.pov.replacement_text == "":
                                        c = 1
                                        while (c <= lampCount):
                                            tabWrite("]\n")
                                            tabWrite("}\n")
                                            c += 1

                                      
                                            
                                    # Close first layer of POV "texture" (Blender material)
                                    tabWrite("}\n")
                                    
                                    if (mater.specular_color.s > 0.0):
                                        colored_specular_found = True
                                    else:
                                        colored_specular_found = False
                                        
                                    # Write another layered texture using invisible diffuse and metallic trick 
                                    # to emulate colored specular highlights
                                    special_texture_found = False
                                    for t in mater.texture_slots:
                                        if(t and t.use and ((t.texture.type == 'IMAGE' and t.texture.image) or t.texture.type != 'IMAGE') and
                                           (t.use_map_specular or t.use_map_raymir)):
                                            # Specular mapped textures would conflict with colored specular
                                            # because POV can't layer over or under pigment patterned textures
                                            special_texture_found = True
                                    
                                    if colored_specular_found and not special_texture_found:
                                        if comments:
                                            file.write("  // colored highlights with a stransparent metallic layer\n")
                                        else:
                                            tabWrite("\n")
                                    
                                        tabWrite("texture {\n")
                                        tabWrite("pigment {rgbft<%.3g, %.3g, %.3g, 0, 1>}\n" % \
                                                         (mater.specular_color[0], mater.specular_color[1], mater.specular_color[2]))
                                        tabWrite("finish {%s}\n" % (safety(material_finish, Level=2))) # Level 2 is translated spec

                                        texturesNorm = ""
                                        for t in mater.texture_slots:

                                            if t and t.texture.pov.tex_pattern_type != 'emulator':
                                                proceduralFlag=True
                                                image_filename = string_strip_hyphen(bpy.path.clean_name(t.texture.name))
                                            if t and t.texture.type == 'IMAGE' and t.use and t.texture.image and t.texture.pov.tex_pattern_type == 'emulator':
                                                proceduralFlag=False 
                                                image_filename = path_image(t.texture.image)
                                                imgGamma = ""
                                                if image_filename:
                                                    if t.use_map_normal:
                                                        texturesNorm = image_filename
                                                        # colvalue = t.normal_factor * 10.0  # UNUSED
                                                        #textNormName=t.texture.image.name + ".normal"
                                                        #was the above used? --MR
                                                        t_nor = t
                                                        if proceduralFlag:
                                                            tabWrite("normal{function{f%s(x,y,z).grey} bump_size %.4g}\n" %(texturesNorm, t_nor.normal_factor * 10))
                                                        else:
                                                            tabWrite("normal {uv_mapping bump_map " \
                                                                     "{%s \"%s\" %s  bump_size %.4g }%s}\n" % \
                                                                     (imageFormat(texturesNorm), texturesNorm, imgMap(t_nor),
                                                                      t_nor.normal_factor * 10, mappingNor))
                                                                      
                                        tabWrite("}\n") # THEN IT CAN CLOSE LAST LAYER OF TEXTURE   --MR


                                ####################################################################################
                                index[0] = idx
                                idx += 1
                                


                        
                    # Vert Colors
                    tabWrite("texture_list {\n")
                    # In case there's is no material slot, give at least one texture (empty so it uses pov default)
                    if len(vertCols)==0:
                        file.write(tabStr + "1")
                    else:
                        file.write(tabStr + "%s" % (len(vertCols)))  # vert count
                    if material is not None:    
                        if material.pov.replacement_text != "":
                            file.write("\n")
                            file.write(" texture{%s}\n" % material.pov.replacement_text)

                        else:
                            # Loop through declared materials list
                            for cMN in LocalMaterialNames:
                                if material != "Default":
                                    file.write("\n texture{MAT_%s}\n" % cMN)#string_strip_hyphen(materialNames[material])) # Something like that
                    else:
                        file.write(" texture{}\n")                
                    tabWrite("}\n")

                    # Face indices
                    tabWrite("face_indices {\n")
                    tabWrite("%d" % (len(me_faces) + quadCount))  # faces count
                    tabStr = tab * tabLevel

                    for fi, f in enumerate(me_faces):
                        fv = faces_verts[fi]
                        material_index = f.material_index
                        if len(fv) == 4:
                            indices = (0, 1, 2), (0, 2, 3)
                        else:
                            indices = ((0, 1, 2),)

                        if vcol_layer:
                            col = vcol_layer[fi]

                            if len(fv) == 4:
                                cols = col.color1, col.color2, col.color3, col.color4
                            else:
                                cols = col.color1, col.color2, col.color3

                        if not me_materials or me_materials[material_index] is None:  # No materials
                            for i1, i2, i3 in indices:
                                if linebreaksinlists:
                                    file.write(",\n")
                                    # vert count
                                    file.write(tabStr + "<%d,%d,%d>" % (fv[i1], fv[i2], fv[i3]))
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>" % (fv[i1], fv[i2], fv[i3]))  # vert count
                        else:
                            material = me_materials[material_index]
                            for i1, i2, i3 in indices:
                                if me.vertex_colors: #and material.use_vertex_color_paint:
                                    # Color per vertex - vertex color

                                    col1 = cols[i1]
                                    col2 = cols[i2]
                                    col3 = cols[i3]

                                    ci1 = vertCols[col1[0], col1[1], col1[2], material_index][0]
                                    ci2 = vertCols[col2[0], col2[1], col2[2], material_index][0]
                                    ci3 = vertCols[col3[0], col3[1], col3[2], material_index][0]
                                else:
                                    # Color per material - flat material color
                                    if material.subsurface_scattering.use:
                                        diffuse_color = [i * j for i, j in izip(material.subsurface_scattering.color[:], material.diffuse_color[:])]
                                    else:
                                        diffuse_color = material.diffuse_color[:]
                                    ci1 = ci2 = ci3 = vertCols[diffuse_color[0], diffuse_color[1], \
                                                      diffuse_color[2], f.material_index][0]

                                if linebreaksinlists:
                                    file.write(",\n")
                                    file.write(tabStr + "<%d,%d,%d>, %d,%d,%d" % \
                                               (fv[i1], fv[i2], fv[i3], ci1, ci2, ci3))  # vert count
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>, %d,%d,%d" % \
                                               (fv[i1], fv[i2], fv[i3], ci1, ci2, ci3))  # vert count

                    file.write("\n")
                    tabWrite("}\n")

                    # normal_indices indices
                    tabWrite("normal_indices {\n")
                    tabWrite("%d" % (len(me_faces) + quadCount))  # faces count
                    tabStr = tab * tabLevel
                    for fi, fv in enumerate(faces_verts):

                        if len(fv) == 4:
                            indices = (0, 1, 2), (0, 2, 3)
                        else:
                            indices = ((0, 1, 2),)

                        for i1, i2, i3 in indices:
                            if me_faces[fi].use_smooth:
                                if linebreaksinlists:
                                    file.write(",\n")
                                    file.write(tabStr + "<%d,%d,%d>" %\
                                    (uniqueNormals[verts_normals[fv[i1]]][0],\
                                     uniqueNormals[verts_normals[fv[i2]]][0],\
                                     uniqueNormals[verts_normals[fv[i3]]][0]))  # vert count
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>" %\
                                    (uniqueNormals[verts_normals[fv[i1]]][0],\
                                     uniqueNormals[verts_normals[fv[i2]]][0],\
                                     uniqueNormals[verts_normals[fv[i3]]][0]))  # vert count
                            else:
                                idx = uniqueNormals[faces_normals[fi]][0]
                                if linebreaksinlists:
                                    file.write(",\n")
                                    file.write(tabStr + "<%d,%d,%d>" % (idx, idx, idx))  # vert count
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>" % (idx, idx, idx))  # vert count

                    file.write("\n")
                    tabWrite("}\n")

                    if uv_layer:
                        tabWrite("uv_indices {\n")
                        tabWrite("%d" % (len(me_faces) + quadCount))  # faces count
                        tabStr = tab * tabLevel
                        for fi, fv in enumerate(faces_verts):

                            if len(fv) == 4:
                                indices = (0, 1, 2), (0, 2, 3)
                            else:
                                indices = ((0, 1, 2),)

                            uv = uv_layer[fi]
                            if len(faces_verts[fi]) == 4:
                                uvs = uv.uv[0][:], uv.uv[1][:], uv.uv[2][:], uv.uv[3][:]
                            else:
                                uvs = uv.uv[0][:], uv.uv[1][:], uv.uv[2][:]

                            for i1, i2, i3 in indices:
                                if linebreaksinlists:
                                    file.write(",\n")
                                    file.write(tabStr + "<%d,%d,%d>" % (
                                             uniqueUVs[uvs[i1]][0],\
                                             uniqueUVs[uvs[i2]][0],\
                                             uniqueUVs[uvs[i3]][0]))
                                else:
                                    file.write(", ")
                                    file.write("<%d,%d,%d>" % (
                                             uniqueUVs[uvs[i1]][0],\
                                             uniqueUVs[uvs[i2]][0],\
                                             uniqueUVs[uvs[i3]][0]))

                        file.write("\n")
                        tabWrite("}\n")

                    if me.materials:
                        try:
                            material = me.materials[0]  # dodgy
                            writeObjectMaterial(material, ob)
                        except IndexError:
                            print me

                    #Importance for radiosity sampling added here:
                    tabWrite("radiosity { \n")
                    tabWrite("importance %3g \n" % importance)
                    tabWrite("}\n")

                    tabWrite("}\n")  # End of mesh block

                bpy.data.meshes.remove(me)

        for data_name, inst in data_ref.items():
            for ob_name, matrix_str in inst:
                tabWrite("//----Blender Object Name:%s----\n" % ob_name)
                tabWrite("object { \n")
                tabWrite("%s\n" % data_name)
                tabWrite("%s\n" % matrix_str)
                tabWrite("}\n")

    def exportWorld(world):
        render = scene.render
        camera = scene.camera
        matrix = global_matrix * camera.matrix_world
        if not world:
            return
        #############Maurice####################################
        #These lines added to get sky gradient (visible with PNG output)
        if world:
            #For simple flat background:
            if not world.use_sky_blend:
                # Non fully transparent background could premultiply alpha and avoid anti-aliasing
                # display issue:
                if render.alpha_mode == 'TRANSPARENT':
                    tabWrite("background {rgbt<%.3g, %.3g, %.3g, 0.75>}\n" % \
                             (world.horizon_color[:]))
                #Currently using no alpha with Sky option:
                elif render.alpha_mode == 'SKY':
                    tabWrite("background {rgbt<%.3g, %.3g, %.3g, 0>}\n" % (world.horizon_color[:]))
                #StraightAlpha:
                # XXX Does not exists anymore
                #else:
                    #tabWrite("background {rgbt<%.3g, %.3g, %.3g, 1>}\n" % (world.horizon_color[:]))

            worldTexCount = 0
            #For Background image textures
            for t in world.texture_slots:  # risk to write several sky_spheres but maybe ok.
                if t and t.texture.type is not None:
                    worldTexCount += 1
                # XXX No enable checkbox for world textures yet (report it?)
                #if t and t.texture.type == 'IMAGE' and t.use:
                if t and t.texture.type == 'IMAGE':
                    image_filename = path_image(t.texture.image)
                    if t.texture.image.filepath != image_filename:
                        t.texture.image.filepath = image_filename
                    if image_filename != "" and t.use_map_blend:
                        texturesBlend = image_filename
                        #colvalue = t.default_value
                        t_blend = t

                    # Commented below was an idea to make the Background image oriented as camera
                    # taken here:
#http://news.povray.org/povray.newusers/thread/%3Cweb.4a5cddf4e9c9822ba2f93e20@news.povray.org%3E/
                    # Replace 4/3 by the ratio of each image found by some custom or existing
                    # function
                    #mappingBlend = (" translate <%.4g,%.4g,%.4g> rotate z*degrees" \
                    #                "(atan((camLocation - camLookAt).x/(camLocation - " \
                    #                "camLookAt).y)) rotate x*degrees(atan((camLocation - " \
                    #                "camLookAt).y/(camLocation - camLookAt).z)) rotate y*" \
                    #                "degrees(atan((camLocation - camLookAt).z/(camLocation - " \
                    #                "camLookAt).x)) scale <%.4g,%.4g,%.4g>b" % \
                    #                (t_blend.offset.x / 10 , t_blend.offset.y / 10 ,
                    #                 t_blend.offset.z / 10, t_blend.scale.x ,
                    #                 t_blend.scale.y , t_blend.scale.z))
                    #using camera rotation valuesdirectly from blender seems much easier
                    if t_blend.texture_coords == 'ANGMAP':
                        mappingBlend = ""
                    else:
                        # POV-Ray "scale" is not a number of repetitions factor, but its
                        # inverse, a standard scale factor.
                        # 0.5 Offset is needed relatively to scale because center of the
                        # UV scale is 0.5,0.5 in blender and 0,0 in POV
                        # Further Scale by 2 and translate by -1 are 
                        # required for the sky_sphere not to repeat
                  
                        mappingBlend = "scale 2 scale <%.4g,%.4g,%.4g> translate -1 translate <%.4g,%.4g,%.4g> " \
                                       "rotate<0,0,0> " % \
                                       ((1.0 / t_blend.scale.x), 
                                       (1.0 / t_blend.scale.y),
                                       (1.0 / t_blend.scale.z), 
                                       0.5-(0.5/t_blend.scale.x)- t_blend.offset.x,
                                       0.5-(0.5/t_blend.scale.y)- t_blend.offset.y,
                                       t_blend.offset.z)

                        # The initial position and rotation of the pov camera is probably creating
                        # the rotation offset should look into it someday but at least background
                        # won't rotate with the camera now.
                    # Putting the map on a plane would not introduce the skysphere distortion and
                    # allow for better image scale matching but also some waay to chose depth and
                    # size of the plane relative to camera.
                    tabWrite("sky_sphere {\n")
                    tabWrite("pigment {\n")
                    tabWrite("image_map{%s \"%s\" %s}\n" % \
                             (imageFormat(texturesBlend), texturesBlend, imgMapBG(t_blend)))
                    tabWrite("}\n")
                    tabWrite("%s\n" % (mappingBlend))
                    # The following layered pigment opacifies to black over the texture for
                    # transmit below 1 or otherwise adds to itself
                    tabWrite("pigment {rgb 0 transmit %s}\n" % (t.texture.intensity))
                    tabWrite("}\n")
                    #tabWrite("scale 2\n")
                    #tabWrite("translate -1\n")

            #For only Background gradient

            if worldTexCount == 0:
                if world.use_sky_blend:
                    tabWrite("sky_sphere {\n")
                    tabWrite("pigment {\n")
                    # maybe Should follow the advice of POV doc about replacing gradient
                    # for skysphere..5.5
                    tabWrite("gradient y\n")
                    tabWrite("color_map {\n")
                    # XXX Does not exists anymore
                    #if render.alpha_mode == 'STRAIGHT':
                        #tabWrite("[0.0 rgbt<%.3g, %.3g, %.3g, 1>]\n" % (world.horizon_color[:]))
                        #tabWrite("[1.0 rgbt<%.3g, %.3g, %.3g, 1>]\n" % (world.zenith_color[:]))
                    if render.alpha_mode == 'TRANSPARENT':
                        tabWrite("[0.0 rgbt<%.3g, %.3g, %.3g, 0.99>]\n" % (world.horizon_color[:]))
                        # aa premult not solved with transmit 1
                        tabWrite("[1.0 rgbt<%.3g, %.3g, %.3g, 0.99>]\n" % (world.zenith_color[:]))
                    else:
                        tabWrite("[0.0 rgbt<%.3g, %.3g, %.3g, 0>]\n" % (world.horizon_color[:]))
                        tabWrite("[1.0 rgbt<%.3g, %.3g, %.3g, 0>]\n" % (world.zenith_color[:]))
                    tabWrite("}\n")
                    tabWrite("}\n")
                    tabWrite("}\n")
                    # Sky_sphere alpha (transmit) is not translating into image alpha the same
                    # way as 'background'

            #if world.light_settings.use_indirect_light:
            #    scene.pov.radio_enable=1

            # Maybe change the above to a funtion copyInternalRenderer settings when
            # user pushes a button, then:
            #scene.pov.radio_enable = world.light_settings.use_indirect_light
            # and other such translations but maybe this would not be allowed either?

        ###############################################################

        mist = world.mist_settings

        if mist.use_mist:
            tabWrite("fog {\n")
            tabWrite("distance %.6f\n" % mist.depth)
            tabWrite("color rgbt<%.3g, %.3g, %.3g, %.3g>\n" % \
                     (world.horizon_color[:] + (1.0 - mist.intensity,)))
            #tabWrite("fog_offset %.6f\n" % mist.start)
            #tabWrite("fog_alt 5\n")
            #tabWrite("turbulence 0.2\n")
            #tabWrite("turb_depth 0.3\n")
            tabWrite("fog_type 1\n")
            tabWrite("}\n")
        if scene.pov.media_enable:
            tabWrite("media {\n")
            tabWrite("scattering { 1, rgb <%.4g, %.4g, %.4g>}\n" % scene.pov.media_color[:])
            tabWrite("samples %.d\n" % scene.pov.media_samples)
            tabWrite("}\n")

    def exportGlobalSettings(scene):

        tabWrite("global_settings {\n")
        tabWrite("assumed_gamma 1.0\n")
        tabWrite("max_trace_level %d\n" % scene.pov.max_trace_level)

        if scene.pov.radio_enable:
            tabWrite("radiosity {\n")
            tabWrite("adc_bailout %.4g\n" % scene.pov.radio_adc_bailout)
            tabWrite("always_sample %d\n" % scene.pov.radio_always_sample)
            tabWrite("brightness %.4g\n" % scene.pov.radio_brightness)
            tabWrite("count %d\n" % scene.pov.radio_count)
            tabWrite("error_bound %.4g\n" % scene.pov.radio_error_bound)
            tabWrite("gray_threshold %.4g\n" % scene.pov.radio_gray_threshold)
            tabWrite("low_error_factor %.4g\n" % scene.pov.radio_low_error_factor)
            tabWrite("media %d\n" % scene.pov.radio_media)
            tabWrite("minimum_reuse %.4g\n" % scene.pov.radio_minimum_reuse)
            tabWrite("nearest_count %d\n" % scene.pov.radio_nearest_count)
            tabWrite("normal %d\n" % scene.pov.radio_normal)
            tabWrite("pretrace_start %.3g\n" % scene.pov.radio_pretrace_start)
            tabWrite("pretrace_end %.3g\n" % scene.pov.radio_pretrace_end)
            tabWrite("recursion_limit %d\n" % scene.pov.radio_recursion_limit)
            tabWrite("}\n")
        onceSss = 1
        onceAmbient = 1
        oncePhotons = 1
        for material in bpy.data.materials:
            if material.subsurface_scattering.use and onceSss:
                # In pov, the scale has reversed influence compared to blender. these number
                # should correct that
                tabWrite("mm_per_unit %.6f\n" % \
                         (material.subsurface_scattering.scale * 1000.0))# formerly ...scale * (-100.0) + 15.0))
                # In POV-Ray, the scale factor for all subsurface shaders needs to be the same
                sslt_samples = (11 - material.subsurface_scattering.error_threshold) * 10 # formerly ...*100
                tabWrite("subsurface { samples %d, %d }\n" % (sslt_samples, sslt_samples / 10))
                onceSss = 0

            if world and onceAmbient:
                tabWrite("ambient_light rgbt<%.3g, %.3g, %.3g,1>\n" % world.ambient_color[:])
                onceAmbient = 0

            if (material.pov.refraction_type == "2" or material.pov.photons_reflection == True) and oncePhotons:
                tabWrite("photons {\n")
                tabWrite("spacing %.6f\n" % scene.pov.photon_spacing)
                tabWrite("max_trace_level %d\n" % scene.pov.photon_max_trace_level)
                tabWrite("adc_bailout %.3g\n" % scene.pov.photon_adc_bailout)
                tabWrite("gather %d, %d\n" % (scene.pov.photon_gather_min, scene.pov.photon_gather_max))
                tabWrite("}\n")
                oncePhotons = 0

        tabWrite("}\n")

    def exportCustomCode():
        # Write CurrentAnimation Frame for use in Custom POV Code
        file.write("#declare CURFRAMENUM = %d;\n" % bpy.context.scene.frame_current)
        #Change path and uncomment to add an animated include file by hand:
        file.write("//#include \"/home/user/directory/animation_include_file.inc\"\n")
        for txt in bpy.data.texts:
            if txt.pov.custom_code:
                # Why are the newlines needed?
                file.write("\n")
                file.write(txt.as_string())
                file.write("\n")

    sel = renderable_objects()
    if comments:
        file.write("//----------------------------------------------\n" \
                   "//--Exported with POV-Ray exporter for Blender--\n" \
                   "//----------------------------------------------\n\n")
    file.write("#version 3.7;\n")

    if comments:
        file.write("\n//--Global settings--\n\n")

    exportGlobalSettings(scene)

    
    if comments:
        file.write("\n//--Custom Code--\n\n")
    exportCustomCode()

    if comments:
        file.write("\n//--Patterns Definitions--\n\n")
    LocalPatternNames = []
    for texture in bpy.data.textures: #ok?
        if texture.users > 0:
            currentPatName = string_strip_hyphen(bpy.path.clean_name(texture.name)) #string_strip_hyphen(patternNames[texture.name]) #maybe instead
            LocalPatternNames.append(currentPatName) #use this list to prevent writing texture instances several times and assign in mats?
            file.write("\n #declare PAT_%s = \n" % currentPatName)
            file.write(exportPattern(texture))
            file.write("\n")                
    if comments:
        file.write("\n//--Background--\n\n")

    exportWorld(scene.world)

    if comments:
        file.write("\n//--Cameras--\n\n")

    exportCamera()

    if comments:
        file.write("\n//--Lamps--\n\n")

    exportLamps([l for l in sel if l.type == 'LAMP'])

    if comments:
        file.write("\n//--Material Definitions--\n\n")
    # write a default pigment for objects with no material (comment out to show black)
    file.write("#default{ pigment{ color rgb 0.8 }}\n")
    # Convert all materials to strings we can access directly per vertex.
    #exportMaterials()
    writeMaterial(None)  # default material
    for material in bpy.data.materials:
        if material.users > 0:
            writeMaterial(material)
    if comments:
        file.write("\n")

    exportMeta([l for l in sel if l.type == 'META'])

    if comments:
        file.write("//--Mesh objects--\n")

    exportMeshes(scene, sel)
    #What follow used to happen here:
    #exportCamera()
    #exportWorld(scene.world)
    #exportGlobalSettings(scene)
    # MR:..and the order was important for an attempt to implement pov 3.7 baking
    #      (mesh camera) comment for the record
    # CR: Baking should be a special case than. If "baking", than we could change the order.

    #print("pov file closed %s" % file.closed)
    file.close()
    #print("pov file closed %s" % file.closed)


def write_pov_ini(scene, filename_ini, filename_pov, filename_image):
    feature_set = bpy.context.user_preferences.addons[__package__].preferences.branch_feature_set_povray
    using_uberpov = (feature_set=='uberpov')
    #scene = bpy.data.scenes[0]
    render = scene.render

    x = int(render.resolution_x * render.resolution_percentage * 0.01)
    y = int(render.resolution_y * render.resolution_percentage * 0.01)

    file = open(filename_ini, "w")
    file.write("Version=3.7\n")
    file.write("Input_File_Name='%s'\n" % filename_pov)
    file.write("Output_File_Name='%s'\n" % filename_image)

    file.write("Width=%d\n" % x)
    file.write("Height=%d\n" % y)

    # Border render.
    if render.use_border:
        file.write("Start_Column=%4g\n" % render.border_min_x)
        file.write("End_Column=%4g\n" % (render.border_max_x))

        file.write("Start_Row=%4g\n" % (1.0 - render.border_max_y))
        file.write("End_Row=%4g\n" % (1.0 - render.border_min_y))

    file.write("Bounding_Method=2\n")  # The new automatic BSP is faster in most scenes

    # Activated (turn this back off when better live exchange is done between the two programs
    # (see next comment)
    file.write("Display=1\n")
    file.write("Pause_When_Done=0\n")
    # PNG, with POV-Ray 3.7, can show background color with alpha. In the long run using the
    # POV-Ray interactive preview like bishop 3D could solve the preview for all formats.
    file.write("Output_File_Type=N\n")
    #file.write("Output_File_Type=T\n") # TGA, best progressive loading
    file.write("Output_Alpha=1\n")

    if scene.pov.antialias_enable:
        # method 2 (recursive) with higher max subdiv forced because no mipmapping in POV-Ray
        # needs higher sampling.
        # aa_mapping = {"5": 2, "8": 3, "11": 4, "16": 5}
        if using_uberpov:
            method = {"0": 1, "1": 2, "2": 3}
        else:
            method = {"0": 1, "1": 2, "2": 2}
        file.write("Antialias=on\n")
        file.write("Antialias_Depth=%d\n" % scene.pov.antialias_depth)
        file.write("Antialias_Threshold=%.3g\n" % scene.pov.antialias_threshold)
        if using_uberpov and scene.pov.antialias_method == '2':
            file.write("Sampling_Method=%s\n" % method[scene.pov.antialias_method])
            file.write("Antialias_Confidence=%.3g\n" % scene.pov.antialias_confidence)
        else:
            file.write("Sampling_Method=%s\n" % method[scene.pov.antialias_method])
        file.write("Antialias_Gamma=%.3g\n" % scene.pov.antialias_gamma)
        if scene.pov.jitter_enable:
            file.write("Jitter=on\n")
            file.write("Jitter_Amount=%3g\n" % scene.pov.jitter_amount)
        else:
            file.write("Jitter=off\n")  # prevent animation flicker

    else:
        file.write("Antialias=off\n")
    #print("ini file closed %s" % file.closed)
    file.close()
    #print("ini file closed %s" % file.closed)


class PovrayRender(bpy.types.RenderEngine):
    bl_idname = 'POVRAY_RENDER'
    bl_label = "POV-Ray 3.7"
    DELAY = 0.5

    @staticmethod
    def _locate_binary():
        addon_prefs = bpy.context.user_preferences.addons[__package__].preferences

        # Use the system preference if its set.
        pov_binary = addon_prefs.filepath_povray
        if pov_binary:
            if os.path.exists(pov_binary):
                return pov_binary
            else:
                print "User Preferences path to povray %r NOT FOUND, checking $PATH" % pov_binary

        # Windows Only
        # assume if there is a 64bit binary that the user has a 64bit capable OS
        if sys.platform[:3] == "win":
            import _winreg
            win_reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\POV-Ray\\v3.7\\Windows")
            win_home = winreg.QueryValueEx(win_reg_key, "Home")[0]

            # First try 64bits UberPOV
            pov_binary = os.path.join(win_home, "bin", "uberpov64.exe")
            if os.path.exists(pov_binary):
                return pov_binary
                
            # Then try 64bits POV
            pov_binary = os.path.join(win_home, "bin", "pvengine64.exe")
            if os.path.exists(pov_binary):
                return pov_binary

            # Then try 32bits UberPOV
            pov_binary = os.path.join(win_home, "bin", "uberpov32.exe")
            if os.path.exists(pov_binary):
                return pov_binary 
                
            # Then try 32bits POV
            pov_binary = os.path.join(win_home, "bin", "pvengine.exe")
            if os.path.exists(pov_binary):
                return pov_binary

        # search the path all os's
        pov_binary_default = "povray"

        os_path_ls = os.getenv("PATH").split(':') + [""]

        for dir_name in os_path_ls:
            pov_binary = os.path.join(dir_name, pov_binary_default)
            if os.path.exists(pov_binary):
                return pov_binary
        return ""

    def _export(self, scene, povPath, renderImagePath):
        import tempfile

        if scene.pov.tempfiles_enable:
            self._temp_file_in = tempfile.NamedTemporaryFile(suffix=".pov", delete=False).name
            # PNG with POV 3.7, can show the background color with alpha. In the long run using the
            # POV-Ray interactive preview like bishop 3D could solve the preview for all formats.
            self._temp_file_out = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
            #self._temp_file_out = tempfile.NamedTemporaryFile(suffix=".tga", delete=False).name
            self._temp_file_ini = tempfile.NamedTemporaryFile(suffix=".ini", delete=False).name
        else:
            self._temp_file_in = povPath + ".pov"
            # PNG with POV 3.7, can show the background color with alpha. In the long run using the
            # POV-Ray interactive preview like bishop 3D could solve the preview for all formats.
            self._temp_file_out = renderImagePath + ".png"
            #self._temp_file_out = renderImagePath + ".tga"
            self._temp_file_ini = povPath + ".ini"
            '''
            self._temp_file_in = "/test.pov"
            # PNG with POV 3.7, can show the background color with alpha. In the long run using the
            # POV-Ray interactive preview like bishop 3D could solve the preview for all formats.
            self._temp_file_out = "/test.png"
            #self._temp_file_out = "/test.tga"
            self._temp_file_ini = "/test.ini"
            '''

        def info_callback(txt):
            self.update_stats("", "POV-Ray 3.7: " + txt)

        write_pov(self._temp_file_in, scene, info_callback)

    def _render(self, scene):
        try:
            os.remove(self._temp_file_out)  # so as not to load the old file
        except OSError:
            pass

        pov_binary = PovrayRender._locate_binary()
        if not pov_binary:
            print "POV-Ray 3.7: could not execute povray, possibly POV-Ray isn't installed"
            return False

        write_pov_ini(scene, self._temp_file_ini, self._temp_file_in, self._temp_file_out)

        print "***-STARTING-***"

        extra_args = []

        if scene.pov.command_line_switches != "":
            for newArg in scene.pov.command_line_switches.split(" "):
                extra_args.append(newArg)

        self._is_windows = False
        if sys.platform[:3] == "win":
            self._is_windows = True
            if"/EXIT" not in extra_args and not scene.pov.pov_editor:
                extra_args.append("/EXIT")
        else:
            # added -d option to prevent render window popup which leads to segfault on linux
            extra_args.append("-d")

        # Start Rendering!
        try:
            self._process = subprocess.Popen([pov_binary, self._temp_file_ini] + extra_args,
                                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError:
            # TODO, report api
            print "POV-Ray 3.7: could not execute '%s'" % pov_binary
            import traceback
            traceback.print_exc()
            print "***-DONE-***"
            return False

        else:
            print "Engine ready!..."
            print "Command line arguments passed: " + str(extra_args)
            return True

        # Now that we have a valid process

    def _cleanup(self):
        for f in (self._temp_file_in, self._temp_file_ini, self._temp_file_out):
            for i in xrange(5):
                try:
                    os.unlink(f)
                    break
                except OSError:
                    # Wait a bit before retrying file might be still in use by Blender,
                    # and Windows does not know how to delete a file in use!
                    time.sleep(self.DELAY)
        for i in unpacked_images:
            for c in xrange(5):
                try:
                    os.unlink(i)
                    break
                except OSError:
                    # Wait a bit before retrying file might be still in use by Blender,
                    # and Windows does not know how to delete a file in use!
                    time.sleep(self.DELAY)
    def render(self, scene):
        import tempfile

        print "***INITIALIZING***"

##WIP output format
##        if r.image_settings.file_format == 'OPENEXR':
##            fformat = 'EXR'
##            render.image_settings.color_mode = 'RGBA'
##        else:
##            fformat = 'TGA'
##            r.image_settings.file_format = 'TARGA'
##            r.image_settings.color_mode = 'RGBA'

        blendSceneName = bpy.data.filepath.split(os.path.sep)[-1].split(".")[0]
        povSceneName = ""
        povPath = ""
        renderImagePath = ""

        # has to be called to update the frame on exporting animations
        scene.frame_set(scene.frame_current)

        if not scene.pov.tempfiles_enable:

            # check paths
            povPath = bpy.path.abspath(scene.pov.scene_path).replace('\\', '/')
            if povPath == "":
                if bpy.data.is_saved:
                    povPath = bpy.path.abspath("//")
                else:
                    povPath = tempfile.gettempdir()
            elif povPath.endswith("/"):
                if povPath == "/":
                    povPath = bpy.path.abspath("//")
                else:
                    povPath = bpy.path.abspath(scene.pov.scene_path)

            if not os.path.exists(povPath):
                try:
                    os.makedirs(povPath)
                except:
                    import traceback
                    traceback.print_exc()

                    print "POV-Ray 3.7: Cannot create scenes directory: %r" % povPath
                    self.update_stats("", "POV-Ray 3.7: Cannot create scenes directory %r" % \
                                      povPath)
                    time.sleep(2.0)
                    return

            '''
            # Bug in POV-Ray RC3
            renderImagePath = bpy.path.abspath(scene.pov.renderimage_path).replace('\\','/')
            if renderImagePath == "":
                if bpy.data.is_saved:
                    renderImagePath = bpy.path.abspath("//")
                else:
                    renderImagePath = tempfile.gettempdir()
                #print("Path: " + renderImagePath)
            elif path.endswith("/"):
                if renderImagePath == "/":
                    renderImagePath = bpy.path.abspath("//")
                else:
                    renderImagePath = bpy.path.abspath(scene.pov.renderimage_path)
            if not os.path.exists(path):
                print("POV-Ray 3.7: Cannot find render image directory")
                self.update_stats("", "POV-Ray 3.7: Cannot find render image directory")
                time.sleep(2.0)
                return
            '''

            # check name
            if scene.pov.scene_name == "":
                if blendSceneName != "":
                    povSceneName = blendSceneName
                else:
                    povSceneName = "untitled"
            else:
                povSceneName = scene.pov.scene_name
                if os.path.isfile(povSceneName):
                    povSceneName = os.path.basename(povSceneName)
                povSceneName = povSceneName.split('/')[-1].split('\\')[-1]
                if not povSceneName:
                    print "POV-Ray 3.7: Invalid scene name"
                    self.update_stats("", "POV-Ray 3.7: Invalid scene name")
                    time.sleep(2.0)
                    return
                povSceneName = os.path.splitext(povSceneName)[0]

            print "Scene name: " + povSceneName
            print "Export path: " + povPath
            povPath = os.path.join(povPath, povSceneName)
            povPath = os.path.realpath(povPath)

            # for now this has to be the same like the pov output. Bug in POV-Ray RC3.
            # renderImagePath = renderImagePath + "\\" + povSceneName
            renderImagePath = povPath  # Bugfix for POV-Ray RC3 bug
            # renderImagePath = os.path.realpath(renderImagePath)  # Bugfix for POV-Ray RC3 bug

            #print("Export path: %s" % povPath)
            #print("Render Image path: %s" % renderImagePath)

        # start export
        self.update_stats("", "POV-Ray 3.7: Exporting data from Blender")
        self._export(scene, povPath, renderImagePath)
        self.update_stats("", "POV-Ray 3.7: Parsing File")

        if not self._render(scene):
            self.update_stats("", "POV-Ray 3.7: Not found")
            return

        r = scene.render
        # compute resolution
        x = int(r.resolution_x * r.resolution_percentage * 0.01)
        y = int(r.resolution_y * r.resolution_percentage * 0.01)

        # This makes some tests on the render, returning True if all goes good, and False if
        # it was finished one way or the other.
        # It also pauses the script (time.sleep())
        def _test_wait():
            time.sleep(self.DELAY)

            # User interrupts the rendering
            if self.test_break():
                try:
                    self._process.terminate()
                    print "***POV INTERRUPTED***"
                except OSError:
                    pass
                return False

            poll_result = self._process.poll()
            # POV process is finisehd, one way or the other
            if poll_result is not None:
                if poll_result < 0:
                    print "***POV PROCESS FAILED : %s ***" % poll_result
                    self.update_stats("", "POV-Ray 3.7: Failed")
                return False

            return True

        # Wait for the file to be created
        # XXX This is no more valid, as 3.7 always creates output file once render is finished!
        parsing = re.compile(r"= \[Parsing\.\.\.\] =")
        rendering = re.compile(r"= \[Rendering\.\.\.\] =")
        percent = re.compile(r"\(([0-9]{1,3})%\)")
        # print("***POV WAITING FOR FILE***")

        data = ""
        last_line = ""
        while _test_wait():
            # POV in Windows does not output its stdout/stderr, it displays them in its GUI
            if self._is_windows:
                self.update_stats("", "POV-Ray 3.7: Rendering File")
            else:
                t_data = self._process.stdout.read(10000)
                if not t_data:
                    continue

                data += t_data
                # XXX This is working for UNIX, not sure whether it might need adjustments for
                #     other OSs
                # First replace is for windows
                t_data = str(t_data).replace('\\r\\n', '\\n').replace('\\r', '\r')
                lines = t_data.split('\\n')
                last_line += lines[0]
                lines[0] = last_line
                print '\n'.join(lines),; sys.stdout.write("")
                last_line = lines[-1]

                if rendering.search(data):
                    _pov_rendering = True
                    match = percent.findall(str(data))
                    if match:
                        self.update_stats("", "POV-Ray 3.7: Rendering File (%s%%)" % match[-1])
                    else:
                        self.update_stats("", "POV-Ray 3.7: Rendering File")

                elif parsing.search(data):
                    self.update_stats("", "POV-Ray 3.7: Parsing File")

        if os.path.exists(self._temp_file_out):
            # print("***POV FILE OK***")
            #self.update_stats("", "POV-Ray 3.7: Rendering")

            # prev_size = -1

            xmin = int(r.border_min_x * x)
            ymin = int(r.border_min_y * y)
            xmax = int(r.border_max_x * x)
            ymax = int(r.border_max_y * y)

            # print("***POV UPDATING IMAGE***")
            result = self.begin_result(0, 0, x, y)
            # XXX, tests for border render.
            #result = self.begin_result(xmin, ymin, xmax - xmin, ymax - ymin)
            #result = self.begin_result(0, 0, xmax - xmin, ymax - ymin)
            lay = result.layers[0]

            # This assumes the file has been fully written We wait a bit, just in case!
            time.sleep(self.DELAY)
            try:
                lay.load_from_file(self._temp_file_out)
                # XXX, tests for border render.
                #lay.load_from_file(self._temp_file_out, xmin, ymin)
            except RuntimeError:
                print "***POV ERROR WHILE READING OUTPUT FILE***"

            # Not needed right now, might only be useful if we find a way to use temp raw output of
            # pov 3.7 (in which case it might go under _test_wait()).
            '''
            def update_image():
                # possible the image wont load early on.
                try:
                    lay.load_from_file(self._temp_file_out)
                    # XXX, tests for border render.
                    #lay.load_from_file(self._temp_file_out, xmin, ymin)
                    #lay.load_from_file(self._temp_file_out, xmin, ymin)
                except RuntimeError:
                    pass

            # Update while POV-Ray renders
            while True:
                # print("***POV RENDER LOOP***")

                # test if POV-Ray exists
                if self._process.poll() is not None:
                    print("***POV PROCESS FINISHED***")
                    update_image()
                    break

                # user exit
                if self.test_break():
                    try:
                        self._process.terminate()
                        print("***POV PROCESS INTERRUPTED***")
                    except OSError:
                        pass

                    break

                # Would be nice to redirect the output
                # stdout_value, stderr_value = self._process.communicate() # locks

                # check if the file updated
                new_size = os.path.getsize(self._temp_file_out)

                if new_size != prev_size:
                    update_image()
                    prev_size = new_size

                time.sleep(self.DELAY)
            '''

            self.end_result(result)

        else:
            print "***POV FILE NOT FOUND***"

        print "***POV FINISHED***"

        self.update_stats("", "")

        if scene.pov.tempfiles_enable or scene.pov.deletefiles_enable:
            self._cleanup()


    
#################################Operators#########################################
class RenderPovTexturePreview(Operator):
    bl_idname = "tex.preview_update"
    bl_label = "Update preview"
    def execute(self, context):
        tex=bpy.context.object.active_material.active_texture #context.texture
        texPrevName=string_strip_hyphen(bpy.path.clean_name(tex.name))+"_prev"
        workDir = bpy.utils.resource_path('USER')    
        previewDir=os.path.join(workDir, "preview")
        
        ## Make sure Preview directory exists and is empty
        if not os.path.isdir(previewDir):
            os.mkdir(previewDir)
        
        iniPrevFile=os.path.join(previewDir, "Preview.ini")
        inputPrevFile=os.path.join(previewDir, "Preview.pov")
        outputPrevFile=os.path.join(previewDir, texPrevName)
        ##################### ini ##########################################
        fileIni=open("%s"%iniPrevFile,"w")
        fileIni.write('Version=3.7\n')
        fileIni.write('Input_File_Name="%s"\n'%inputPrevFile)
        fileIni.write('Output_File_Name="%s.png"\n'%outputPrevFile)
        fileIni.write('Library_Path="%s"\n'%previewDir)
        fileIni.write('Width=256\n')
        fileIni.write('Height=256\n')
        fileIni.write('Pause_When_Done=0\n')
        fileIni.write('Output_File_Type=N\n')
        fileIni.write('Output_Alpha=1\n')
        fileIni.write('Antialias=on\n')
        fileIni.write('Sampling_Method=2\n')
        fileIni.write('Antialias_Depth=3\n')
        fileIni.write('-d\n')
        fileIni.close()
        ##################### pov ##########################################
        filePov=open("%s"%inputPrevFile,"w")
        PATname = "PAT_"+string_strip_hyphen(bpy.path.clean_name(tex.name))
        filePov.write("#declare %s = \n"%PATname)
        filePov.write(exportPattern(tex))

        filePov.write("#declare Plane =\n")
        filePov.write("mesh {\n")
        filePov.write("    triangle {<-2.021,-1.744,2.021>,<-2.021,-1.744,-2.021>,<2.021,-1.744,2.021>}\n")
        filePov.write("    triangle {<-2.021,-1.744,-2.021>,<2.021,-1.744,-2.021>,<2.021,-1.744,2.021>}\n")
        filePov.write("    texture{%s}\n"%PATname)
        filePov.write("}\n")
        filePov.write("object {Plane}\n")
        filePov.write("light_source {\n")
        filePov.write("    <0,4.38,-1.92e-07>\n")
        filePov.write("    color rgb<4, 4, 4>\n")
        filePov.write("    parallel\n")
        filePov.write("    point_at  <0, 0, -1>\n")
        filePov.write("}\n")
        filePov.write("camera {\n")
        filePov.write("    location  <0, 0, 0>\n")
        filePov.write("    look_at  <0, 0, -1>\n")
        filePov.write("    right <-1.0, 0, 0>\n")
        filePov.write("    up <0, 1, 0>\n")
        filePov.write("    angle  96.805211\n")
        filePov.write("    rotate  <-90.000003, -0.000000, 0.000000>\n")
        filePov.write("    translate <0.000000, 0.000000, 0.000000>\n")
        filePov.write("}\n")
        filePov.close()
        ##################### end write ##########################################

        pov_binary = PovrayRender._locate_binary()
        
        if sys.platform[:3] == "win":
            p1=subprocess.Popen(["%s"%pov_binary,"/EXIT","%s"%iniPrevFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        else:
            p1=subprocess.Popen(["%s"%pov_binary,"-d","%s"%iniPrevFile],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        p1.wait()

        tex.use_nodes = True
        tree = tex.node_tree
        links = tree.links
        for n in tree.nodes:
            tree.nodes.remove(n)
        im = tree.nodes.new("TextureNodeImage")  
        pathPrev="%s.png"%outputPrevFile
        im.image = bpy.data.images.load(pathPrev)
        name=pathPrev
        name=name.split("/")
        name=name[len(name)-1]
        im.name = name  
        im.location = 200,200
        previewer = tree.nodes.new('TextureNodeOutput')    
        previewer.label = "Preview"
        previewer.location = 400,400
        links.new(im.outputs[0],previewer.inputs[0])
        #tex.type="IMAGE" # makes clip extend possible
        #tex.extension="CLIP"
        return set(['FINISHED'])    