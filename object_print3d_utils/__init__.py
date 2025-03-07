# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

from __future__ import absolute_import
bl_info = {
    "name": "3D Print Toolbox",
    "author": "Campbell Barton",
    "blender": (2, 65, 0),
    "location": "3D View > Toolbox",
    "description": "Utilities for 3D printing",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/"
                "Scripts/Modeling/PrintToolbox",
    "support": 'OFFICIAL',
    "category": "Mesh"}


if "bpy" in locals():
    import importlib
else:
    import bpy
    from bpy.props import (
            StringProperty,
            BoolProperty,
            IntProperty,
            FloatProperty,
            FloatVectorProperty,
            EnumProperty,
            PointerProperty,
            )
    from bpy.types import (
            Operator,
            AddonPreferences,
            PropertyGroup,
            )
    from . import (
            ui,
            operators,
            )

import math

class Print3DSettings(PropertyGroup):
    export_format = EnumProperty(
            name="Format",
            description="Format type to export to",
            items=(('STL', "STL", ""),
                   ('PLY', "PLY", ""),
                   ('WRL', "VRML2", ""),
                   ('X3D', "X3D", ""),
                   ('OBJ', "OBJ", "")),
            default='STL',
            )
    use_export_texture = BoolProperty(
            name="Copy Textures",
            description="Copy textures on export to the output path",
            default=False,
            )
    use_apply_scale = BoolProperty(
            name="Apply Scale",
            description="Apply scene scale setting on export",
            default=False,
            )
    export_path = StringProperty(
            name="Export Directory",
            description="Path to directory where the files are created",
            default="//", maxlen=1024, subtype="DIR_PATH",
            )
    thickness_min = FloatProperty(
            name="Thickness",
            description="Minimum thickness",
            subtype='DISTANCE',
            default=0.001,  # 1mm
            min=0.0, max=10.0,
            )
    threshold_zero = FloatProperty(
            name="Threshold",
            description="Limit for checking zero area/length",
            default=0.0001,
            precision=5,
            min=0.0, max=0.2,
            )
    angle_distort = FloatProperty(
            name="Angle",
            description="Limit for checking distorted faces",
            subtype='ANGLE',
            default=math.radians(45.0),
            min=0.0, max=math.radians(180.0),
            )
    angle_sharp = FloatProperty(
            name="Angle",
            subtype='ANGLE',
            default=math.radians(160.0),
            min=0.0, max=math.radians(180.0),
            )
    angle_overhang = FloatProperty(
            name="Angle",
            subtype='ANGLE',
            default=math.radians(45.0),
            min=0.0, max=math.radians(90.0),
            )

classes = (
    ui.Print3DToolBarObject,
    ui.Print3DToolBarMesh,

    operators.Print3DInfoVolume,
    operators.Print3DInfoArea,

    operators.Print3DCheckDegenerate,
    operators.Print3DCheckDistorted,
    operators.Print3DCheckSolid,
    operators.Print3DCheckIntersections,
    operators.Print3DCheckThick,
    operators.Print3DCheckSharp,
    operators.Print3DCheckOverhang,
    operators.Print3DCheckAll,

    operators.Print3DCleanIsolated,
    operators.Print3DCleanDistorted,
    operators.Print3DCleanThin,
    operators.Print3DCleanNonManifold,

    operators.Print3DSelectReport,

    operators.Print3DScaleToVolume,
    operators.Print3DScaleToBounds,

    operators.Print3DExport,

    Print3DSettings,
    )


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.print_3d = PointerProperty(type=Print3DSettings)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.print_3d
