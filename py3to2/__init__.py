'''
BEGIN GPL LICENSE BLOCK

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

END GPL LICENCE BLOCK
'''

from __future__ import absolute_import

from importlib import import_module
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

refactor = import_module('lib2to3.refactor')
pygram = import_module('lib2to3.pygram')

bl_info = {
    "name": "Python Version Converter (for downBGE)",
    "author": "JulaDDR",
    "version": (1, 0, 8),
    "blender": (2, 7, 6),
    "category": "Text Editor",
    "location": "",
    "wiki_url": "",
    "tracker_url": ""
}

if "bpy" in locals():
    import imp

import bpy


class Refactor(refactor.RefactoringTool):

    def __init__(self, fixer_pkg, exclude=frozenset(), explicit=frozenset(), is3to2=False):
        fixers = set(refactor.get_fixers_from_package(fixer_pkg)) - set(exclude)
        options = {}

        super(Refactor, self).__init__(fixers, options, set(explicit))
        if is3to2:
            self.driver.grammar = pygram.python_grammar_no_print_statement

    def refactor_string(self, data, name):
        tree = self.driver.parse_string(data)
        self.refactor_tree(tree, name)
        return tree

    def execute(self, context):
        st = context.space_data
        text = st.text

        tree = self.refactor_string(text.as_string() + '\n', text.name)
        text.from_string(str(tree)[:-1])

        return set(['FINISHED'])


class Run2to3(bpy.types.Operator):
    bl_idname = 'text.python2to3'
    bl_label = 'Convert Python 2 to 3'
    bl_options = set(['REGISTER', 'UNDO'])

    def __init__(self):
        self._refactor = Refactor("lib2to3.fixes")

    def execute(self, context):
        return self._refactor.execute(context)


class Run3to2(bpy.types.Operator):
    bl_idname = 'text.python3to2'
    bl_label = 'Convert Python 3 to 2'
    bl_options = set(['REGISTER', 'UNDO'])

    def __init__(self):
        self._refactor = Refactor("lib3to2.fixes", exclude=set(['lib3to2.fixes.fix_str']), is3to2=True)

    def execute(self, context):
        return self._refactor.execute(context)


class TEXT_MT_text_python(bpy.types.Menu):
    bl_label = "Convert Python"

    def draw(self, context):
        self.layout.operator("text.python3to2", text="3 to 2")
        self.layout.operator("text.python2to3", text="2 to 3")


def menu_func(self, context):
    st = context.space_data
    text = st.text

    if text:
        self.layout.menu("TEXT_MT_text_python")
        self.layout.separator()


def register():
    bpy.utils.register_class(Run2to3)
    bpy.utils.register_class(Run3to2)
    bpy.utils.register_class(TEXT_MT_text_python)
    bpy.types.TEXT_MT_text.prepend(menu_func)


def unregister():
    bpy.utils.unregister_class(Run2to3)
    bpy.utils.unregister_class(Run3to2)
    bpy.utils.unregister_class(TEXT_MT_text_python)
    bpy.types.VIEW3D_MT_edit_mesh_specials.remove(menu_func)
