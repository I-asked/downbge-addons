#!/usr/bin/env python3
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

"""
Usage
=====

   fbx2json [FILES]...

This script will write a JSON file for each FBX argument given.


Output
======

The JSON data is formatted into a list of nested lists of 4 items:

   ``[id, [data, ...], "data_types", [subtree, ...]]``

Where each list may be empty, and the items in
the subtree are formatted the same way.

data_types is a string, aligned with data that spesifies a type
for each property.

The types are as follows:

* 'Y': - INT16
* 'C': - BOOL
* 'I': - INT32
* 'F': - FLOAT32
* 'D': - FLOAT64
* 'L': - INT64
* 'R': - BYTES
* 'S': - STRING
* 'f': - FLOAT32_ARRAY
* 'i': - INT32_ARRAY
* 'd': - FLOAT64_ARRAY
* 'l': - INT64_ARRAY
* 'b': - BOOL ARRAY
* 'c': - BYTE ARRAY

Note that key:value pairs aren't used since the id's are not
ensured to be unique.
"""


# ----------------------------------------------------------------------------
# FBX Binary Parser

from __future__ import with_statement
from __future__ import absolute_import
from struct import unpack
import array
import zlib
from io import open
from itertools import izip
import sys

# at the end of each nested block, there is a NUL record to indicate
# that the sub-scope exists (i.e. to distinguish between P: and P : {})
# this NUL record is 13 bytes long.
_BLOCK_SENTINEL_LENGTH = 13
_BLOCK_SENTINEL_DATA = ('\0' * _BLOCK_SENTINEL_LENGTH)
_IS_BIG_ENDIAN = (__import__("sys").byteorder != 'little')
_HEAD_MAGIC = 'Kaydara FBX Binary\x20\x20\x00\x1a\x00'
from collections import namedtuple
FBXElem = namedtuple("FBXElem", ("id", "props", "props_type", "elems"))
del namedtuple


def read_uint(read):
    return unpack('<I', read(4))[0]


def read_ubyte(read):
    return unpack('B', read(1))[0]


def read_string_ubyte(read):
    size = read_ubyte(read)
    data = read(size)
    return data


def unpack_array(read, array_type, array_stride, array_byteswap):
    length = read_uint(read)
    encoding = read_uint(read)
    comp_len = read_uint(read)

    data = read(comp_len)

    if encoding == 0:
        pass
    elif encoding == 1:
        data = zlib.decompress(data)

    assert(length * array_stride == len(data))

    data_array = array.array(array_type, data)
    if array_byteswap and _IS_BIG_ENDIAN:
        data_array.byteswap()
    return data_array


read_data_dict = {
    'Y'[0]: lambda read: unpack('<h', read(2))[0],  # 16 bit int
    'C'[0]: lambda read: unpack('?', read(1))[0],   # 1 bit bool (yes/no)
    'I'[0]: lambda read: unpack('<i', read(4))[0],  # 32 bit int
    'F'[0]: lambda read: unpack('<f', read(4))[0],  # 32 bit float
    'D'[0]: lambda read: unpack('<d', read(8))[0],  # 64 bit float
    'L'[0]: lambda read: unpack('<q', read(8))[0],  # 64 bit int
    'R'[0]: lambda read: read(read_uint(read)),      # binary data
    'S'[0]: lambda read: read(read_uint(read)),      # string data
    'f'[0]: lambda read: unpack_array(read, 'f', 4, False),  # array (float)
    'i'[0]: lambda read: unpack_array(read, 'i', 4, True),   # array (int)
    'd'[0]: lambda read: unpack_array(read, 'd', 8, False),  # array (double)
    'l'[0]: lambda read: unpack_array(read, 'q', 8, True),   # array (long)
    'b'[0]: lambda read: unpack_array(read, 'b', 1, False),  # array (bool)
    'c'[0]: lambda read: unpack_array(read, 'B', 1, False),  # array (ubyte)
    }


def read_elem(read, tell, use_namedtuple):
    # [0] the offset at which this block ends
    # [1] the number of properties in the scope
    # [2] the length of the property list
    end_offset = read_uint(read)
    if end_offset == 0:
        return None

    prop_count = read_uint(read)
    prop_length = read_uint(read)

    elem_id = read_string_ubyte(read)        # elem name of the scope/key
    elem_props_type = bytearray(prop_count)  # elem property types
    elem_props_data = [None] * prop_count    # elem properties (if any)
    elem_subtree = []                        # elem children (if any)

    for i in xrange(prop_count):
        data_type = read(1)[0]
        elem_props_data[i] = read_data_dict[data_type](read)
        elem_props_type[i] = data_type

    if tell() < end_offset:
        while tell() < (end_offset - _BLOCK_SENTINEL_LENGTH):
            elem_subtree.append(read_elem(read, tell, use_namedtuple))

        if read(_BLOCK_SENTINEL_LENGTH) != _BLOCK_SENTINEL_DATA:
            raise IOError("failed to read nested block sentinel, "
                          "expected all bytes to be 0")

    if tell() != end_offset:
        raise IOError("scope length not reached, something is wrong")

    args = (elem_id, elem_props_data, elem_props_type, elem_subtree)
    return FBXElem(*args) if use_namedtuple else args


def parse_version(fn):
    """
    Return the FBX version,
    if the file isn't a binary FBX return zero.
    """
    with open(fn, 'rb') as f:
        read = f.read

        if read(len(_HEAD_MAGIC)) != _HEAD_MAGIC:
            return 0

        return read_uint(read)


def parse(fn, use_namedtuple=True):
    root_elems = []

    with open(fn, 'rb') as f:
        read = f.read
        tell = f.tell

        if read(len(_HEAD_MAGIC)) != _HEAD_MAGIC:
            raise IOError("Invalid header")

        fbx_version = read_uint(read)

        while True:
            elem = read_elem(read, tell, use_namedtuple)
            if elem is None:
                break
            root_elems.append(elem)

    args = ('', [], bytearray(0), root_elems)
    return FBXElem(*args) if use_namedtuple else args, fbx_version


# ----------------------------------------------------------------------------
# Inline Modules

# pyfbx.data_types
data_types = type(array)("data_types")
data_types.__dict__.update(
dict(
INT16 = 'Y'[0],
BOOL = 'C'[0],
INT32 = 'I'[0],
FLOAT32 = 'F'[0],
FLOAT64 = 'D'[0],
INT64 = 'L'[0],
BYTES = 'R'[0],
STRING = 'S'[0],
FLOAT32_ARRAY = 'f'[0],
INT32_ARRAY = 'i'[0],
FLOAT64_ARRAY = 'd'[0],
INT64_ARRAY = 'l'[0],
BOOL_ARRAY = 'b'[0],
BYTE_ARRAY = 'c'[0],
))

# pyfbx.parse_bin
parse_bin = type(array)("parse_bin")
parse_bin.__dict__.update(
dict(
parse = parse
))


# ----------------------------------------------------------------------------
# JSON Converter
# from pyfbx import parse_bin, data_types
import json
import array


def fbx2json_property_as_string(prop, prop_type):
    if prop_type == data_types.STRING:
        prop_str = prop.decode('utf-8')
        prop_str = prop_str.replace('\x00\x01', '::')
        return json.dumps(prop_str)
    else:
        prop_py_type = type(prop)
        if prop_py_type == str:
            return json.dumps(repr(prop)[2:-1])
        elif prop_py_type == bool:
            return json.dumps(prop)
        elif prop_py_type == array.array:
            return repr(list(prop))

    return repr(prop)


def fbx2json_properties_as_string(fbx_elem):
    return ", ".join(fbx2json_property_as_string(*prop_item)
                     for prop_item in izip(fbx_elem.props,
                                          fbx_elem.props_type))


def fbx2json_recurse(fw, fbx_elem, ident, is_last):
    fbx_elem_id = fbx_elem.id.decode('utf-8')
    fw('%s["%s", ' % (ident, fbx_elem_id))
    fw('[%s], ' % fbx2json_properties_as_string(fbx_elem))
    fw('"%s", ' % (fbx_elem.props_type.decode('ascii')))

    fw('[')
    if fbx_elem.elems:
        fw('\n')
        ident_sub = ident + "    "
        for fbx_elem_sub in fbx_elem.elems:
            fbx2json_recurse(fw, fbx_elem_sub, ident_sub,
                             fbx_elem_sub is fbx_elem.elems[-1])
    fw(']')

    fw(']%s' % ('' if is_last else ',\n'))


def fbx2json(fn):
    import os

    fn_json = "%s.json" % os.path.splitext(fn)[0]
    print "Writing: %r " % fn_json,; sys.stdout.write("")
    fbx_root_elem, fbx_version = parse(fn, use_namedtuple=True)
    print "(Version %d) ..." % fbx_version

    with open(fn_json, 'w', encoding="ascii", errors='xmlcharrefreplace') as f:
        fw = f.write
        fw('[\n')
        ident_sub = "    "
        for fbx_elem_sub in fbx_root_elem.elems:
            fbx2json_recurse(f.write, fbx_elem_sub, ident_sub,
                             fbx_elem_sub is fbx_root_elem.elems[-1])
        fw(']\n')


# ----------------------------------------------------------------------------
# Command Line

def main():
    import sys

    if "--help" in sys.argv:
        print __doc__
        return

    for arg in sys.argv[1:]:
        try:
            fbx2json(arg)
        except:
            print "Failed to convert %r, error:" % arg

            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
