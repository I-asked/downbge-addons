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

# <pep8 compliant>

# Script copyright (C) 2006-2012, assimp team
# Script copyright (C) 2013 Blender Foundation

from __future__ import absolute_import
BOOL = 'C'[0]
INT16 = 'Y'[0]
INT32 = 'I'[0]
INT64 = 'L'[0]
FLOAT32 = 'F'[0]
FLOAT64 = 'D'[0]
BYTES = 'R'[0]
STRING = 'S'[0]
INT32_ARRAY = 'i'[0]
INT64_ARRAY = 'l'[0]
FLOAT32_ARRAY = 'f'[0]
FLOAT64_ARRAY = 'd'[0]
BOOL_ARRAY = 'b'[0]
BYTE_ARRAY = 'c'[0]

# array types - actual length may vary (depending on underlying C implementation)!
import array

# For now, bytes and bool are assumed always 1byte.
ARRAY_BOOL = 'b'
ARRAY_BYTE = 'B'

ARRAY_INT32 = None
ARRAY_INT64 = None
for _t in 'ilq':
    size = array.array(_t).itemsize
    if size == 4:
        ARRAY_INT32 = _t
    elif size == 8:
        ARRAY_INT64 = _t
    if ARRAY_INT32 and ARRAY_INT64:
        break
if not ARRAY_INT32:
    raise Exception("Impossible to get a 4-bytes integer type for array!")
if not ARRAY_INT64:
    raise Exception("Impossible to get an 8-bytes integer type for array!")

ARRAY_FLOAT32 = None
ARRAY_FLOAT64 = None
for _t in 'fd':
    size = array.array(_t).itemsize
    if size == 4:
        ARRAY_FLOAT32 = _t
    elif size == 8:
        ARRAY_FLOAT64 = _t
    if ARRAY_FLOAT32 and ARRAY_FLOAT64:
        break
if not ARRAY_FLOAT32:
    raise Exception("Impossible to get a 4-bytes float type for array!")
if not ARRAY_FLOAT64:
    raise Exception("Impossible to get an 8-bytes float type for array!")
