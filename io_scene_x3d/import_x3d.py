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

DEBUG = False

# This should work without a blender at all
import os
import shlex
from io import open
from itertools import izip


def imageConvertCompat(path):

    if os.sep == '\\':
        return path  # assume win32 has quicktime, dont convert

    if path.lower().endswith('.gif'):
        path_to = path[:-3] + 'png'

        '''
        if exists(path_to):
            return path_to
        '''
        # print('\n'+path+'\n'+path_to+'\n')
        os.system('convert "%s" "%s"' % (path, path_to))  # for now just hope we have image magick

        if os.path.exists(path_to):
            return path_to

    return path

# notes
# transform are relative
# order dosnt matter for loc/size/rot
# right handed rotation
# angles are in radians
# rotation first defines axis then amount in radians


# =============================== VRML Spesific

def vrml_split_fields(value):
    """
    key 0.0 otherkey 1,2,3 opt1 opt1 0.0
        -> [key 0.0], [otherkey 1,2,3], [opt1 opt1 0.0]
    """
    def iskey(k):
        if k[0] != '"' and k[0].isalpha() and k.upper() not in set(['TRUE', 'FALSE']):
            return True
        return False

    field_list = []
    field_context = []

    for v in value:
        if iskey(v):
            if field_context:
                field_context_len = len(field_context)
                if (field_context_len > 2) and (field_context[-2] in set(['DEF', 'USE'])):
                    field_context.append(v)
                elif (not iskey(field_context[-1])) or ((field_context_len == 3 and field_context[1] == 'IS')):
                    # this IS a key but the previous value was not a key, ot it was a defined field.
                    field_list.append(field_context)
                    field_context = [v]
                else:
                    # The last item was not a value, multiple keys are needed in some cases.
                    field_context.append(v)
            else:
                # Is empty, just add this on
                field_context.append(v)
        else:
            # Add a value to the list
            field_context.append(v)

    if field_context:
        field_list.append(field_context)

    return field_list


def vrmlFormat(data):
    """
    Keep this as a valid vrml file, but format in a way we can predict.
    """
    # Strip all commends - # not in strings - warning multiline strings are ignored.
    def strip_comment(l):
        #l = ' '.join(l.split())
        l = l.strip()

        if l.startswith('#'):
            return ''

        i = l.find('#')

        if i == -1:
            return l

        # Most cases accounted for! if we have a comment at the end of the line do this...
        #j = l.find('url "')
        j = l.find('"')

        if j == -1:  # simple no strings
            return l[:i].strip()

        q = False
        for i, c in enumerate(l):
            if c == '"':
                q = not q  # invert

            elif c == '#':
                if q is False:
                    return l[:i - 1]

        return l

    data = '\n'.join([strip_comment(l) for l in data.split('\n')])  # remove all whitespace

    EXTRACT_STRINGS = True  # only needed when strings or filesnames containe ,[]{} chars :/

    if EXTRACT_STRINGS:

        # We need this so we can detect URL's
        data = '\n'.join([' '.join(l.split()) for l in data.split('\n')])  # remove all whitespace

        string_ls = []

        #search = 'url "'
        search = '"'

        ok = True
        last_i = 0
        while ok:
            ok = False
            i = data.find(search, last_i)
            if i != -1:

                start = i + len(search)  # first char after end of search
                end = data.find('"', start)
                if end != -1:
                    item = data[start:end]
                    string_ls.append(item)
                    data = data[:start] + data[end:]
                    ok = True  # keep looking

                    last_i = (end - len(item)) + 1
                    # print(last_i, item, '|' + data[last_i] + '|')

    # done with messy extracting strings part

    # Bad, dont take strings into account
    '''
    data = data.replace('#', '\n#')
    data = '\n'.join([ll for l in data.split('\n') for ll in (l.strip(),) if not ll.startswith('#')]) # remove all whitespace
    '''
    data = data.replace('{', '\n{\n')
    data = data.replace('}', '\n}\n')
    data = data.replace('[', '\n[\n')
    data = data.replace(']', '\n]\n')
    data = data.replace(',', ' , ')  # make sure comma's separate

    # We need to write one property (field) per line only, otherwise we fail later to detect correctly new nodes.
    # See T45195 for details.
    data = '\n'.join([' '.join(value) for l in data.split('\n') for value in vrml_split_fields(l.split())])

    if EXTRACT_STRINGS:
        # add strings back in

        search = '"'  # fill in these empty strings

        ok = True
        last_i = 0
        while ok:
            ok = False
            i = data.find(search + '"', last_i)
            # print(i)
            if i != -1:
                start = i + len(search)  # first char after end of search
                item = string_ls.pop(0)
                # print(item)
                data = data[:start] + item + data[start:]

                last_i = start + len(item) + 1

                ok = True

    # More annoying obscure cases where USE or DEF are placed on a newline
    # data = data.replace('\nDEF ', ' DEF ')
    # data = data.replace('\nUSE ', ' USE ')

    data = '\n'.join([' '.join(l.split()) for l in data.split('\n')])  # remove all whitespace

    # Better to parse the file accounting for multiline arrays
    '''
    data = data.replace(',\n', ' , ') # remove line endings with commas
    data = data.replace(']', '\n]\n') # very very annoying - but some comma's are at the end of the list, must run this again.
    '''

    return [l for l in data.split('\n') if l]

NODE_NORMAL = 1  # {}
NODE_ARRAY = 2  # []
NODE_REFERENCE = 3  # USE foobar
# NODE_PROTO = 4 #

lines = []


def getNodePreText(i, words):
    # print(lines[i])
    use_node = False
    while len(words) < 5:

        if i >= len(lines):
            break
            '''
        elif lines[i].startswith('PROTO'):
            return NODE_PROTO, i+1
            '''
        elif lines[i] == '{':
            # words.append(lines[i]) # no need
            # print("OK")
            return NODE_NORMAL, i + 1
        elif lines[i].count('"') % 2 != 0:  # odd number of quotes? - part of a string.
            # print('ISSTRING')
            break
        else:
            new_words = lines[i].split()
            if 'USE' in new_words:
                use_node = True

            words.extend(new_words)
            i += 1

        # Check for USE node - no {
        # USE #id - should always be on the same line.
        if use_node:
            # print('LINE', i, words[:words.index('USE')+2])
            words[:] = words[:words.index('USE') + 2]
            if lines[i] == '{' and lines[i + 1] == '}':
                # USE sometimes has {} after it anyway
                i += 2
            return NODE_REFERENCE, i

    # print("error value!!!", words)
    return 0, -1


def is_nodeline(i, words):

    if not lines[i][0].isalpha():
        return 0, 0

    #if lines[i].startswith('field'):
    #   return 0, 0

    # Is this a prototype??
    if lines[i].startswith('PROTO'):
        words[:] = lines[i].split()
        return NODE_NORMAL, i + 1  # TODO - assumes the next line is a '[\n', skip that
    if lines[i].startswith('EXTERNPROTO'):
        words[:] = lines[i].split()
        return NODE_ARRAY, i + 1  # TODO - assumes the next line is a '[\n', skip that

    '''
    proto_type, new_i = is_protoline(i, words, proto_field_defs)
    if new_i != -1:
        return proto_type, new_i
    '''

    # Simple "var [" type
    if lines[i + 1] == '[':
        if lines[i].count('"') % 2 == 0:
            words[:] = lines[i].split()
            return NODE_ARRAY, i + 2

    node_type, new_i = getNodePreText(i, words)

    if not node_type:
        if DEBUG:
            print "not node_type", lines[i]
        return 0, 0

    # Ok, we have a { after some values
    # Check the values are not fields
    for i, val in enumerate(words):
        if i != 0 and words[i - 1] in set(['DEF', 'USE']):
            # ignore anything after DEF, it is a ID and can contain any chars.
            pass
        elif val[0].isalpha() and val not in set(['TRUE', 'FALSE']):
            pass
        else:
            # There is a number in one of the values, therefor we are not a node.
            return 0, 0

    #if node_type==NODE_REFERENCE:
    #   print(words, "REF_!!!!!!!")
    return node_type, new_i


def is_numline(i):
    """
    Does this line start with a number?
    """

    # Works but too slow.
    '''
    l = lines[i]
    for w in l.split():
        if w==',':
            pass
        else:
            try:
                float(w)
                return True

            except:
                return False

    return False
    '''

    l = lines[i]

    line_start = 0

    if l.startswith(', '):
        line_start += 2

    line_end = len(l) - 1
    line_end_new = l.find(' ', line_start)  # comma's always have a space before them

    if line_end_new != -1:
        line_end = line_end_new

    try:
        float(l[line_start:line_end])  # works for a float or int
        return True
    except:
        return False


class vrmlNode(object):
    __slots__ = ('id',
                 'fields',
                 'proto_node',
                 'proto_field_defs',
                 'proto_fields',
                 'node_type',
                 'parent',
                 'children',
                 'parent',
                 'array_data',
                 'reference',
                 'lineno',
                 'filename',
                 'blendObject',
                 'blendData',
                 'DEF_NAMESPACE',
                 'ROUTE_IPO_NAMESPACE',
                 'PROTO_NAMESPACE',
                 'x3dNode')

    def __init__(self, parent, node_type, lineno):
        self.id = None
        self.node_type = node_type
        self.parent = parent
        self.blendObject = None
        self.blendData = None
        self.x3dNode = None  # for x3d import only
        if parent:
            parent.children.append(self)

        self.lineno = lineno

        # This is only set from the root nodes.
        # Having a filename also denotes a root node
        self.filename = None
        self.proto_node = None  # proto field definition eg: "field SFColor seatColor .6 .6 .1"

        # Store in the root node because each inline file needs its own root node and its own namespace
        self.DEF_NAMESPACE = None
        self.ROUTE_IPO_NAMESPACE = None
        '''
        self.FIELD_NAMESPACE = None
        '''

        self.PROTO_NAMESPACE = None

        self.reference = None

        if node_type == NODE_REFERENCE:
            # For references, only the parent and ID are needed
            # the reference its self is assigned on parsing
            return

        self.fields = []  # fields have no order, in some cases rool level values are not unique so dont use a dict

        self.proto_field_defs = []  # proto field definition eg: "field SFColor seatColor .6 .6 .1"
        self.proto_fields = []  # proto field usage "diffuseColor IS seatColor"
        self.children = []
        self.array_data = []  # use for arrays of data - should only be for NODE_ARRAY types

    # Only available from the root node
    '''
    def getFieldDict(self):
        if self.FIELD_NAMESPACE != None:
            return self.FIELD_NAMESPACE
        else:
            return self.parent.getFieldDict()
    '''
    def getProtoDict(self):
        if self.PROTO_NAMESPACE != None:
            return self.PROTO_NAMESPACE
        else:
            return self.parent.getProtoDict()

    def getDefDict(self):
        if self.DEF_NAMESPACE != None:
            return self.DEF_NAMESPACE
        else:
            return self.parent.getDefDict()

    def getRouteIpoDict(self):
        if self.ROUTE_IPO_NAMESPACE != None:
            return self.ROUTE_IPO_NAMESPACE
        else:
            return self.parent.getRouteIpoDict()

    def setRoot(self, filename):
        self.filename = filename
        # self.FIELD_NAMESPACE =        {}
        self.DEF_NAMESPACE = {}
        self.ROUTE_IPO_NAMESPACE = {}
        self.PROTO_NAMESPACE = {}

    def isRoot(self):
        if self.filename is None:
            return False
        else:
            return True

    def getFilename(self):
        if self.filename:
            return self.filename
        elif self.parent:
            return self.parent.getFilename()
        else:
            return None

    def getRealNode(self):
        if self.reference:
            return self.reference
        else:
            return self

    def getSpec(self):
        self_real = self.getRealNode()
        try:
            return self_real.id[-1]  # its possible this node has no spec
        except:
            return None

    def findSpecRecursive(self, spec):
        self_real = self.getRealNode()
        if spec == self_real.getSpec():
            return self

        for child in self_real.children:
            if child.findSpecRecursive(spec):
                return child

        return None

    def getPrefix(self):
        if self.id:
            return self.id[0]
        return None

    def getSpecialTypeName(self, typename):
        self_real = self.getRealNode()
        try:
            return self_real.id[list(self_real.id).index(typename) + 1]
        except:
            return None

    def getDefName(self):
        return self.getSpecialTypeName('DEF')

    def getProtoName(self):
        return self.getSpecialTypeName('PROTO')

    def getExternprotoName(self):
        return self.getSpecialTypeName('EXTERNPROTO')

    def getChildrenBySpec(self, node_spec):  # spec could be Transform, Shape, Appearance
        self_real = self.getRealNode()
        # using getSpec functions allows us to use the spec of USE children that dont have their spec in their ID
        if type(node_spec) == str:
            return [child for child in self_real.children if child.getSpec() == node_spec]
        else:
            # Check inside a list of optional types
            return [child for child in self_real.children if child.getSpec() in node_spec]

    def getChildBySpec(self, node_spec):  # spec could be Transform, Shape, Appearance
        # Use in cases where there is only ever 1 child of this type
        ls = self.getChildrenBySpec(node_spec)
        if ls:
            return ls[0]
        else:
            return None

    def getChildrenByName(self, node_name):  # type could be geometry, children, appearance
        self_real = self.getRealNode()
        return [child for child in self_real.children if child.id if child.id[0] == node_name]

    def getChildByName(self, node_name):
        self_real = self.getRealNode()
        for child in self_real.children:
            if child.id and child.id[0] == node_name:  # and child.id[-1]==node_spec:
                return child

    def getSerialized(self, results, ancestry):
        """ Return this node and all its children in a flat list """
        ancestry = ancestry[:]  # always use a copy

        # self_real = self.getRealNode()

        results.append((self, tuple(ancestry)))
        ancestry.append(self)
        for child in self.getRealNode().children:
            if child not in ancestry:
                # We dont want to load proto's, they are only references
                # We could enforce this elsewhere

                # Only add this in a very special case
                # where the parent of this object is not the real parent
                # - In this case we have added the proto as a child to a node instancing it.
                # This is a bit arbitary, but its how Proto's are done with this importer.
                if child.getProtoName() is None and child.getExternprotoName() is None:
                    child.getSerialized(results, ancestry)
                else:

                    if DEBUG:
                        print 'getSerialized() is proto:', child.getProtoName(), child.getExternprotoName(), self.getSpec()

                    self_spec = self.getSpec()

                    if child.getProtoName() == self_spec or child.getExternprotoName() == self_spec:
                        #if DEBUG:
                        #    "FoundProto!"
                        child.getSerialized(results, ancestry)

        return results

    def searchNodeTypeID(self, node_spec, results):
        self_real = self.getRealNode()
        # print(self.lineno, self.id)
        if self_real.id and self_real.id[-1] == node_spec:  # use last element, could also be only element
            results.append(self_real)
        for child in self_real.children:
            child.searchNodeTypeID(node_spec, results)
        return results

    def getFieldName(self, field, ancestry, AS_CHILD=False, SPLIT_COMMAS=False):
        self_real = self.getRealNode()  # in case we're an instance

        for f in self_real.fields:
            # print(f)
            if f and f[0] == field:
                # print('\tfound field', f)

                if len(f) >= 3 and f[1] == 'IS':  # eg: 'diffuseColor IS legColor'
                    field_id = f[2]

                    # print("\n\n\n\n\n\nFOND IS!!!")
                    f_proto_lookup = None
                    f_proto_child_lookup = None
                    i = len(ancestry)
                    while i:
                        i -= 1
                        node = ancestry[i]
                        node = node.getRealNode()

                        # proto settings are stored in "self.proto_node"
                        if node.proto_node:
                            # Get the default value from the proto, this can be overwridden by the proto instace
                            # 'field SFColor legColor .8 .4 .7'
                            if AS_CHILD:
                                for child in node.proto_node.children:
                                    #if child.id  and  len(child.id) >= 3  and child.id[2]==field_id:
                                    if child.id and ('point' in child.id or 'points' in child.id):
                                        f_proto_child_lookup = child

                            else:
                                for f_def in node.proto_node.proto_field_defs:
                                    if len(f_def) >= 4:
                                        if f_def[0] == 'field' and f_def[2] == field_id:
                                            f_proto_lookup = f_def[3:]

                        # Node instance, Will be 1 up from the proto-node in the ancestry list. but NOT its parent.
                        # This is the setting as defined by the instance, including this setting is optional,
                        # and will override the default PROTO value
                        # eg: 'legColor 1 0 0'
                        if AS_CHILD:
                            for child in node.children:
                                if child.id and child.id[0] == field_id:
                                    f_proto_child_lookup = child
                        else:
                            for f_def in node.fields:
                                if len(f_def) >= 2:
                                    if f_def[0] == field_id:
                                        if DEBUG:
                                            print "getFieldName(), found proto", f_def
                                        f_proto_lookup = f_def[1:]

                    if AS_CHILD:
                        if f_proto_child_lookup:
                            if DEBUG:
                                print "getFieldName() - AS_CHILD=True, child found"
                                print f_proto_child_lookup
                        return f_proto_child_lookup
                    else:
                        return f_proto_lookup
                else:
                    if AS_CHILD:
                        return None
                    else:
                        # Not using a proto
                        return f[1:]
        # print('\tfield not found', field)

        # See if this is a proto name
        if AS_CHILD:
            for child in self_real.children:
                if child.id and len(child.id) == 1 and child.id[0] == field:
                    return child

        return None

    def getFieldAsInt(self, field, default, ancestry):
        self_real = self.getRealNode()  # in case we're an instance

        f = self_real.getFieldName(field, ancestry)
        if f is None:
            return default
        if ',' in f:
            f = f[:f.index(',')]  # strip after the comma

        if len(f) != 1:
            print '\t"%s" wrong length for int conversion for field "%s"' % (f, field)
            return default

        try:
            return int(f[0])
        except:
            print '\tvalue "%s" could not be used as an int for field "%s"' % (f[0], field)
            return default

    def getFieldAsFloat(self, field, default, ancestry):
        self_real = self.getRealNode()  # in case we're an instance

        f = self_real.getFieldName(field, ancestry)
        if f is None:
            return default
        if ',' in f:
            f = f[:f.index(',')]  # strip after the comma

        if len(f) != 1:
            print '\t"%s" wrong length for float conversion for field "%s"' % (f, field)
            return default

        try:
            return float(f[0])
        except:
            print '\tvalue "%s" could not be used as a float for field "%s"' % (f[0], field)
            return default

    def getFieldAsFloatTuple(self, field, default, ancestry):
        self_real = self.getRealNode()  # in case we're an instance

        f = self_real.getFieldName(field, ancestry)
        if f is None:
            return default
        # if ',' in f: f = f[:f.index(',')] # strip after the comma

        if len(f) < 1:
            print '"%s" wrong length for float tuple conversion for field "%s"' % (f, field)
            return default

        ret = []
        for v in f:
            if v != ',':
                try:
                    ret.append(float(v))
                except:
                    break  # quit of first non float, perhaps its a new field name on the same line? - if so we are going to ignore it :/ TODO
        # print(ret)

        if ret:
            return ret
        if not ret:
            print '\tvalue "%s" could not be used as a float tuple for field "%s"' % (f, field)
            return default

    def getFieldAsBool(self, field, default, ancestry):
        self_real = self.getRealNode()  # in case we're an instance

        f = self_real.getFieldName(field, ancestry)
        if f is None:
            return default
        if ',' in f:
            f = f[:f.index(',')]  # strip after the comma

        if len(f) != 1:
            print '\t"%s" wrong length for bool conversion for field "%s"' % (f, field)
            return default

        if f[0].upper() == '"TRUE"' or f[0].upper() == 'TRUE':
            return True
        elif f[0].upper() == '"FALSE"' or f[0].upper() == 'FALSE':
            return False
        else:
            print '\t"%s" could not be used as a bool for field "%s"' % (f[1], field)
            return default

    def getFieldAsString(self, field, default, ancestry):
        self_real = self.getRealNode()  # in case we're an instance

        f = self_real.getFieldName(field, ancestry)
        if f is None:
            return default
        if len(f) < 1:
            print '\t"%s" wrong length for string conversion for field "%s"' % (f, field)
            return default

        if len(f) > 1:
            # String may contain spaces
            st = ' '.join(f)
        else:
            st = f[0]

        # X3D HACK
        if self.x3dNode:
            return st

        if st[0] == '"' and st[-1] == '"':
            return st[1:-1]
        else:
            print '\tvalue "%s" could not be used as a string for field "%s"' % (f[0], field)
            return default

    def getFieldAsArray(self, field, group, ancestry):
        """
        For this parser arrays are children
        """

        def array_as_number(array_string):
            array_data = []
            try:
                array_data = [int(val) for val in array_string]
            except:
                try:
                    array_data = [float(val) for val in array_string]
                except:
                    print '\tWarning, could not parse array data from field'

            return array_data

        self_real = self.getRealNode()  # in case we're an instance

        child_array = self_real.getFieldName(field, ancestry, True, SPLIT_COMMAS=True)

        #if type(child_array)==list: # happens occasionaly
        #   array_data = child_array

        if child_array is None:
            # For x3d, should work ok with vrml too
            # for x3d arrays are fields, vrml they are nodes, annoying but not tooo bad.
            data_split = self.getFieldName(field, ancestry, SPLIT_COMMAS=True)
            if not data_split:
                return []

            array_data = array_as_number(data_split)

        elif type(child_array) == list:
            # x3d creates these
            array_data = array_as_number(child_array)
        else:
            # print(child_array)
            # Normal vrml
            array_data = child_array.array_data

        # print('array_data', array_data)
        if group == -1 or len(array_data) == 0:
            return array_data

        # We want a flat list
        flat = True
        for item in array_data:
            if type(item) == list:
                flat = False
                break

        # make a flat array
        if flat:
            flat_array = array_data  # we are already flat.
        else:
            flat_array = []

            def extend_flat(ls):
                for item in ls:
                    if type(item) == list:
                        extend_flat(item)
                    else:
                        flat_array.append(item)

            extend_flat(array_data)

        # We requested a flat array
        if group == 0:
            return flat_array

        new_array = []
        sub_array = []

        for item in flat_array:
            sub_array.append(item)
            if len(sub_array) == group:
                new_array.append(sub_array)
                sub_array = []

        if sub_array:
            print '\twarning, array was not aligned to requested grouping', group, 'remaining value', sub_array

        return new_array

    def getFieldAsStringArray(self, field, ancestry):
        """
        Get a list of strings
        """
        self_real = self.getRealNode()  # in case we're an instance

        child_array = None
        for child in self_real.children:
            if child.id and len(child.id) == 1 and child.id[0] == field:
                child_array = child
                break
        if not child_array:
            return []

        # each string gets its own list, remove ""'s
        try:
            new_array = [f[0][1:-1] for f in child_array.fields]
        except:
            print '\twarning, string array could not be made'
            new_array = []

        return new_array

    def getLevel(self):
        # Ignore self_real
        level = 0
        p = self.parent
        while p:
            level += 1
            p = p.parent
            if not p:
                break

        return level

    def __repr__(self):
        level = self.getLevel()
        ind = '  ' * level
        if self.node_type == NODE_REFERENCE:
            brackets = ''
        elif self.node_type == NODE_NORMAL:
            brackets = '{}'
        else:
            brackets = '[]'

        if brackets:
            text = ind + brackets[0] + '\n'
        else:
            text = ''

        text += ind + 'ID: ' + str(self.id) + ' ' + str(level) + (' lineno %d\n' % self.lineno)

        if self.node_type == NODE_REFERENCE:
            text += ind + "(reference node)\n"
            return text

        if self.proto_node:
            text += ind + 'PROTO NODE...\n'
            text += str(self.proto_node)
            text += ind + 'PROTO NODE_DONE\n'

        text += ind + 'FIELDS:' + str(len(self.fields)) + '\n'

        for i, item in enumerate(self.fields):
            text += ind + 'FIELD:\n'
            text += ind + str(item) + '\n'

        text += ind + 'PROTO_FIELD_DEFS:' + str(len(self.proto_field_defs)) + '\n'

        for i, item in enumerate(self.proto_field_defs):
            text += ind + 'PROTO_FIELD:\n'
            text += ind + str(item) + '\n'

        text += ind + 'ARRAY: ' + str(len(self.array_data)) + ' ' + str(self.array_data) + '\n'
        #text += ind + 'ARRAY: ' + str(len(self.array_data)) + '[...] \n'

        text += ind + 'CHILDREN: ' + str(len(self.children)) + '\n'
        for i, child in enumerate(self.children):
            text += ind + ('CHILD%d:\n' % i)
            text += str(child)

        text += '\n' + ind + brackets[1]

        return text

    def parse(self, i, IS_PROTO_DATA=False):
        new_i = self.__parse(i, IS_PROTO_DATA)

        # print(self.id, self.getFilename())

        # Check if this node was an inline or externproto

        url_ls = []

        if self.node_type == NODE_NORMAL and self.getSpec() == 'Inline':
            ancestry = []  # Warning! - PROTO's using this wont work at all.
            url = self.getFieldAsString('url', None, ancestry)
            if url:
                url_ls = [(url, None)]
            del ancestry

        elif self.getExternprotoName():
            # externproto
            url_ls = []
            for f in self.fields:

                if type(f) == str:
                    f = [f]

                for ff in f:
                    for f_split in ff.split('"'):
                        # print(f_split)
                        # "someextern.vrml#SomeID"
                        if '#' in f_split:

                            f_split, f_split_id = f_split.split('#')  # there should only be 1 # anyway

                            url_ls.append((f_split, f_split_id))
                        else:
                            url_ls.append((f_split, None))

        # Was either an Inline or an EXTERNPROTO
        if url_ls:

            # print(url_ls)

            for url, extern_key in url_ls:
                print url
                urls = []
                urls.append(url)
                urls.append(bpy.path.resolve_ncase(urls[-1]))

                urls.append(os.path.join(os.path.dirname(self.getFilename()), url))
                urls.append(bpy.path.resolve_ncase(urls[-1]))

                urls.append(os.path.join(os.path.dirname(self.getFilename()), os.path.basename(url)))
                urls.append(bpy.path.resolve_ncase(urls[-1]))

                try:
                    url = [url for url in urls if os.path.exists(url)][0]
                    url_found = True
                except:
                    url_found = False

                if not url_found:
                    print '\tWarning: Inline URL could not be found:', url
                else:
                    if url == self.getFilename():
                        print '\tWarning: cant Inline yourself recursively:', url
                    else:

                        try:
                            data = gzipOpen(url)
                        except:
                            print '\tWarning: cant open the file:', url
                            data = None

                        if data:
                            # Tricky - inline another VRML
                            print '\tLoading Inline:"%s"...' % url

                            # Watch it! - backup lines
                            lines_old = lines[:]

                            lines[:] = vrmlFormat(data)

                            lines.insert(0, '{')
                            lines.insert(0, 'root_node____')
                            lines.append('}')
                            '''
                            ff = open('/tmp/test.txt', 'w')
                            ff.writelines([l+'\n' for l in lines])
                            '''

                            child = vrmlNode(self, NODE_NORMAL, -1)
                            child.setRoot(url)  # initialized dicts
                            child.parse(0)

                            # if self.getExternprotoName():
                            if self.getExternprotoName():
                                if not extern_key:  # if none is spesified - use the name
                                    extern_key = self.getSpec()

                                if extern_key:

                                    self.children.remove(child)
                                    child.parent = None

                                    extern_child = child.findSpecRecursive(extern_key)

                                    if extern_child:
                                        self.children.append(extern_child)
                                        extern_child.parent = self

                                        if DEBUG:
                                            print "\tEXTERNPROTO ID found!:", extern_key
                                    else:
                                        print "\tEXTERNPROTO ID not found!:", extern_key

                            # Watch it! - restore lines
                            lines[:] = lines_old

        return new_i

    def __parse(self, i, IS_PROTO_DATA=False):
        '''
        print('parsing at', i, end="")
        print(i, self.id, self.lineno)
        '''
        l = lines[i]

        if l == '[':
            # An anonymous list
            self.id = None
            i += 1
        else:
            words = []

            node_type, new_i = is_nodeline(i, words)
            if not node_type:  # fail for parsing new node.
                print "Failed to parse new node"
                raise ValueError

            if self.node_type == NODE_REFERENCE:
                # Only assign the reference and quit
                key = words[words.index('USE') + 1]
                self.id = (words[0],)

                self.reference = self.getDefDict()[key]
                return new_i

            self.id = tuple(words)

            # fill in DEF/USE
            key = self.getDefName()
            if key != None:
                self.getDefDict()[key] = self

            key = self.getProtoName()
            if not key:
                key = self.getExternprotoName()

            proto_dict = self.getProtoDict()
            if key != None:
                proto_dict[key] = self

                # Parse the proto nodes fields
                self.proto_node = vrmlNode(self, NODE_ARRAY, new_i)
                new_i = self.proto_node.parse(new_i)

                self.children.remove(self.proto_node)

                # print(self.proto_node)

                new_i += 1  # skip past the {

            else:  # If we're a proto instance, add the proto node as our child.
                spec = self.getSpec()
                try:
                    self.children.append(proto_dict[spec])
                    #pass
                except:
                    pass

                del spec

            del proto_dict, key

            i = new_i

        # print(self.id)
        ok = True
        while ok:
            if i >= len(lines):
                return len(lines) - 1

            l = lines[i]
            # print('\tDEBUG:', i, self.node_type, l)
            if l == '':
                i += 1
                continue

            if l == '}':
                if self.node_type != NODE_NORMAL:  # also ends proto nodes, we may want a type for these too.
                    print 'wrong node ending, expected an } ' + str(i) + ' ' + str(self.node_type)
                    if DEBUG:
                        raise ValueError
                ### print("returning", i)
                return i + 1
            if l == ']':
                if self.node_type != NODE_ARRAY:
                    print 'wrong node ending, expected a ] ' + str(i) + ' ' + str(self.node_type)
                    if DEBUG:
                        raise ValueError
                ### print("returning", i)
                return i + 1

            node_type, new_i = is_nodeline(i, [])
            if node_type:  # check text\n{
                child = vrmlNode(self, node_type, i)
                i = child.parse(i)

            elif l == '[':  # some files have these anonymous lists
                child = vrmlNode(self, NODE_ARRAY, i)
                i = child.parse(i)

            elif is_numline(i):
                l_split = l.split(',')

                values = None
                # See if each item is a float?

                for num_type in (int, float):
                    try:
                        values = [num_type(v) for v in l_split]
                        break
                    except:
                        pass

                    try:
                        values = [[num_type(v) for v in segment.split()] for segment in l_split]
                        break
                    except:
                        pass

                if values is None:  # dont parse
                    values = l_split

                # This should not extend over multiple lines however it is possible
                # print(self.array_data)
                if values:
                    self.array_data.extend(values)
                i += 1
            else:
                words = l.split()
                if len(words) > 2 and words[1] == 'USE':
                    vrmlNode(self, NODE_REFERENCE, i)
                else:

                    # print("FIELD", i, l)
                    #
                    #words = l.split()
                    ### print('\t\ttag', i)
                    # this is a tag/
                    # print(words, i, l)
                    value = l
                    # print(i)
                    # javastrips can exist as values.
                    quote_count = l.count('"')
                    if quote_count % 2:  # odd number?
                        # print('MULTILINE')
                        while 1:
                            i += 1
                            l = lines[i]
                            quote_count = l.count('"')
                            if quote_count % 2:  # odd number?
                                value += '\n' + l[:l.rfind('"')]
                                break  # assume
                            else:
                                value += '\n' + l

                    # use shlex so we get '"a b" "b v"' --> '"a b"', '"b v"'
                    value_all = shlex.split(value, posix=False)

                    for value in vrml_split_fields(value_all):
                        # Split

                        if value[0] == 'field':
                            # field SFFloat creaseAngle 4
                            self.proto_field_defs.append(value)
                        else:
                            self.fields.append(value)
                i += 1


def gzipOpen(path):
    import gzip

    data = None
    try:
        data = gzip.open(path, 'r').read()
    except:
        pass

    if data is None:
        try:
            filehandle = open(path, 'rU')
            data = filehandle.read()
            filehandle.close()
        except:
            pass
    else:
        data = data.decode('utf-8', "replace")

    return data


def vrml_parse(path):
    """
    Sets up the root node and returns it so load_web3d() can deal with the blender side of things.
    Return root (vrmlNode, '') or (None, 'Error String')
    """
    data = gzipOpen(path)

    if data is None:
        return None, 'Failed to open file: ' + path

    # Stripped above
    lines[:] = vrmlFormat(data)

    lines.insert(0, '{')
    lines.insert(0, 'dymmy_node')
    lines.append('}')
    # Use for testing our parsed output, so we can check on line numbers.

    '''
    ff = open('/tmp/test.txt', 'w')
    ff.writelines([l+'\n' for l in lines])
    ff.close()
    '''

    # Now evaluate it
    node_type, new_i = is_nodeline(0, [])
    if not node_type:
        return None, 'Error: VRML file has no starting Node'

    # Trick to make sure we get all root nodes.
    lines.insert(0, '{')
    lines.insert(0, 'root_node____')  # important the name starts with an ascii char
    lines.append('}')

    root = vrmlNode(None, NODE_NORMAL, -1)
    root.setRoot(path)  # we need to set the root so we have a namespace and know the path in case of inlineing

    # Parse recursively
    root.parse(0)

    # This prints a load of text
    if DEBUG:
        print root

    return root, ''


# ====================== END VRML

# ====================== X3d Support

# Sane as vrml but replace the parser
class x3dNode(vrmlNode):
    def __init__(self, parent, node_type, x3dNode):
        vrmlNode.__init__(self, parent, node_type, -1)
        self.x3dNode = x3dNode

    def parse(self, IS_PROTO_DATA=False):
        # print(self.x3dNode.tagName)

        define = self.x3dNode.getAttributeNode('DEF')
        if define:
            self.getDefDict()[define.value] = self
        else:
            use = self.x3dNode.getAttributeNode('USE')
            if use:
                try:
                    self.reference = self.getDefDict()[use.value]
                    self.node_type = NODE_REFERENCE
                except:
                    print '\tWarning: reference', use.value, 'not found'
                    self.parent.children.remove(self)

                return

        for x3dChildNode in self.x3dNode.childNodes:
            if x3dChildNode.nodeType in set([x3dChildNode.TEXT_NODE, x3dChildNode.COMMENT_NODE, x3dChildNode.CDATA_SECTION_NODE]):
                continue

            node_type = NODE_NORMAL
            # print(x3dChildNode, dir(x3dChildNode))
            if x3dChildNode.getAttributeNode('USE'):
                node_type = NODE_REFERENCE

            child = x3dNode(self, node_type, x3dChildNode)
            child.parse()

        # TODO - x3d Inline

    def getSpec(self):
        return self.x3dNode.tagName  # should match vrml spec

    def getDefName(self):
        data = self.x3dNode.getAttributeNode('DEF')
        if data:
            data.value  # XXX, return??
        return None

    # Other funcs operate from vrml, but this means we can wrap XML fields, still use nice utility funcs
    # getFieldAsArray getFieldAsBool etc
    def getFieldName(self, field, ancestry, AS_CHILD=False, SPLIT_COMMAS=False):
        # ancestry and AS_CHILD are ignored, only used for VRML now

        self_real = self.getRealNode()  # in case we're an instance
        field_xml = self.x3dNode.getAttributeNode(field)
        if field_xml:
            value = field_xml.value

            # We may want to edit. for x3d specific stuff
            # Sucks a bit to return the field name in the list but vrml excepts this :/
            if SPLIT_COMMAS:
                value = value.replace(",", " ")
            return value.split()
        else:
            return None


def x3d_parse(path):
    """
    Sets up the root node and returns it so load_web3d() can deal with the blender side of things.
    Return root (x3dNode, '') or (None, 'Error String')
    """

    try:
        import xml.dom.minidom
    except:
        return None, 'Error, import XML parsing module (xml.dom.minidom) failed, install python'

    '''
    try:    doc = xml.dom.minidom.parse(path)
    except: return None, 'Could not parse this X3D file, XML error'
    '''

    # Could add a try/except here, but a console error is more useful.
    data = gzipOpen(path)

    if data is None:
        return None, 'Failed to open file: ' + path

    doc = xml.dom.minidom.parseString(data)

    try:
        x3dnode = doc.getElementsByTagName('X3D')[0]
    except:
        return None, 'Not a valid x3d document, cannot import'

    bpy.ops.object.select_all(action='DESELECT')

    root = x3dNode(None, NODE_NORMAL, x3dnode)
    root.setRoot(path)  # so images and Inline's we load have a relative path
    root.parse()

    return root, ''

## f = open('/_Cylinder.wrl', 'r')
# f = open('/fe/wrl/Vrml/EGS/TOUCHSN.WRL', 'r')
# vrml_parse('/fe/wrl/Vrml/EGS/TOUCHSN.WRL')
#vrml_parse('/fe/wrl/Vrml/EGS/SCRIPT.WRL')
'''
import os
files = os.popen('find /fe/wrl -iname "*.wrl"').readlines()
files.sort()
tot = len(files)
for i, f in enumerate(files):
    #if i < 801:
    #   continue

    f = f.strip()
    print(f, i, tot)
    vrml_parse(f)
'''

# NO BLENDER CODE ABOVE THIS LINE.
# -----------------------------------------------------------------------------------
from __future__ import division
from __future__ import absolute_import
import bpy
from bpy_extras import image_utils
from mathutils import Vector, Matrix

GLOBALS = {'CIRCLE_DETAIL': 16}


def translateRotation(rot):
    """ axis, angle """
    return Matrix.Rotation(rot[3], 4, Vector(rot[:3]))


def translateScale(sca):
    mat = Matrix()  # 4x4 default
    mat[0][0] = sca[0]
    mat[1][1] = sca[1]
    mat[2][2] = sca[2]
    return mat


def translateTransform(node, ancestry):
    cent = node.getFieldAsFloatTuple('center', None, ancestry)  # (0.0, 0.0, 0.0)
    rot = node.getFieldAsFloatTuple('rotation', None, ancestry)  # (0.0, 0.0, 1.0, 0.0)
    sca = node.getFieldAsFloatTuple('scale', None, ancestry)  # (1.0, 1.0, 1.0)
    scaori = node.getFieldAsFloatTuple('scaleOrientation', None, ancestry)  # (0.0, 0.0, 1.0, 0.0)
    tx = node.getFieldAsFloatTuple('translation', None, ancestry)  # (0.0, 0.0, 0.0)

    if cent:
        cent_mat = Matrix.Translation(cent)
        cent_imat = cent_mat.inverted()
    else:
        cent_mat = cent_imat = None

    if rot:
        rot_mat = translateRotation(rot)
    else:
        rot_mat = None

    if sca:
        sca_mat = translateScale(sca)
    else:
        sca_mat = None

    if scaori:
        scaori_mat = translateRotation(scaori)
        scaori_imat = scaori_mat.inverted()
    else:
        scaori_mat = scaori_imat = None

    if tx:
        tx_mat = Matrix.Translation(tx)
    else:
        tx_mat = None

    new_mat = Matrix()

    mats = [tx_mat, cent_mat, rot_mat, scaori_mat, sca_mat, scaori_imat, cent_imat]
    for mtx in mats:
        if mtx:
            new_mat = new_mat * mtx

    return new_mat


def translateTexTransform(node, ancestry):
    cent = node.getFieldAsFloatTuple('center', None, ancestry)  # (0.0, 0.0)
    rot = node.getFieldAsFloat('rotation', None, ancestry)  # 0.0
    sca = node.getFieldAsFloatTuple('scale', None, ancestry)  # (1.0, 1.0)
    tx = node.getFieldAsFloatTuple('translation', None, ancestry)  # (0.0, 0.0)

    if cent:
        # cent is at a corner by default
        cent_mat = Matrix.Translation(Vector(cent).to_3d())
        cent_imat = cent_mat.inverted()
    else:
        cent_mat = cent_imat = None

    if rot:
        rot_mat = Matrix.Rotation(rot, 4, 'Z')  # translateRotation(rot)
    else:
        rot_mat = None

    if sca:
        sca_mat = translateScale((sca[0], sca[1], 0.0))
    else:
        sca_mat = None

    if tx:
        tx_mat = Matrix.Translation(Vector(tx).to_3d())
    else:
        tx_mat = None

    new_mat = Matrix()

    # as specified in VRML97 docs
    mats = [cent_imat, sca_mat, rot_mat, cent_mat, tx_mat]

    for mtx in mats:
        if mtx:
            new_mat = new_mat * mtx

    return new_mat


# 90d X rotation
import math
MATRIX_Z_TO_Y = Matrix.Rotation(math.pi / 2.0, 4, 'X')


def getFinalMatrix(node, mtx, ancestry, global_matrix):

    transform_nodes = [node_tx for node_tx in ancestry if node_tx.getSpec() == 'Transform']
    if node.getSpec() == 'Transform':
        transform_nodes.append(node)
    transform_nodes.reverse()

    if mtx is None:
        mtx = Matrix()

    for node_tx in transform_nodes:
        mat = translateTransform(node_tx, ancestry)
        mtx = mat * mtx

    # worldspace matrix
    mtx = global_matrix * mtx

    return mtx


def importMesh_IndexedFaceSet(geom, bpyima, ancestry):
    # print(geom.lineno, geom.id, vrmlNode.DEF_NAMESPACE.keys())

    ccw = geom.getFieldAsBool('ccw', True, ancestry)
    ifs_colorPerVertex = geom.getFieldAsBool('colorPerVertex', True, ancestry)  # per vertex or per face
    ifs_normalPerVertex = geom.getFieldAsBool('normalPerVertex', True, ancestry)

    # This is odd how point is inside Coordinate

    # VRML not x3d
    #coord = geom.getChildByName('coord') # 'Coordinate'

    coord = geom.getChildBySpec('Coordinate')  # works for x3d and vrml

    if coord:
        ifs_points = coord.getFieldAsArray('point', 3, ancestry)
    else:
        coord = []

    if not coord:
        print '\tWarnint: IndexedFaceSet has no points'
        return None, ccw

    ifs_faces = geom.getFieldAsArray('coordIndex', 0, ancestry)

    coords_tex = None
    if ifs_faces:  # In rare cases this causes problems - no faces but UVs???

        # WORKS - VRML ONLY
        # coords_tex = geom.getChildByName('texCoord')
        coords_tex = geom.getChildBySpec('TextureCoordinate')

        if coords_tex:
            ifs_texpoints = [(0, 0)] # EEKADOODLE - vertex start at 1
            ifs_texpoints.extend(coords_tex.getFieldAsArray('point', 2, ancestry))
            ifs_texfaces = geom.getFieldAsArray('texCoordIndex', 0, ancestry)

            if not ifs_texpoints:
                # IF we have no coords, then dont bother
                coords_tex = None

    # WORKS - VRML ONLY
    # vcolor = geom.getChildByName('color')
    vcolor = geom.getChildBySpec('Color')
    vcolor_spot = None  # spot color when we dont have an array of colors
    if vcolor:
        # float to char
        ifs_vcol = [(0, 0, 0)]  # EEKADOODLE - vertex start at 1
        ifs_vcol.extend([col for col in vcolor.getFieldAsArray('color', 3, ancestry)])
        ifs_color_index = geom.getFieldAsArray('colorIndex', 0, ancestry)

        if not ifs_vcol:
            vcolor_spot = vcolor.getFieldAsFloatTuple('color', [], ancestry)

    # Convert faces into somthing blender can use
    edges = []

    # All lists are aligned!
    faces = []
    faces_uv = []  # if ifs_texfaces is empty then the faces_uv will match faces exactly.
    faces_orig_index = []  # for ngons, we need to know our original index

    if coords_tex and ifs_texfaces:
        do_uvmap = True
    else:
        do_uvmap = False

    # current_face = [0] # pointer anyone

    def add_face(face, fuvs, orig_index):
        l = len(face)
        if l == 3 or l == 4:
            faces.append(face)
            # faces_orig_index.append(current_face[0])
            if do_uvmap:
                faces_uv.append(fuvs)

            faces_orig_index.append(orig_index)
        elif l == 2:
            edges.append(face)
        elif l > 4:
            for i in xrange(2, len(face)):
                faces.append([face[0], face[i - 1], face[i]])
                if do_uvmap:
                    faces_uv.append([fuvs[0], fuvs[i - 1], fuvs[i]])
                faces_orig_index.append(orig_index)
        else:
            # faces with 1 verts? pfft!
            # still will affect index ordering
            pass

    face = []
    fuvs = []
    orig_index = 0
    for i, fi in enumerate(ifs_faces):
        # ifs_texfaces and ifs_faces should be aligned
        if fi != -1:
            # face.append(int(fi)) # in rare cases this is a float
            # EEKADOODLE!!!
            # Annoyance where faces that have a zero index vert get rotated. This will then mess up UVs and VColors
            face.append(int(fi) + 1)  # in rare cases this is a float, +1 because of stupid EEKADOODLE :/

            if do_uvmap:
                if i >= len(ifs_texfaces):
                    print '\tWarning: UV Texface index out of range'
                    fuvs.append(ifs_texfaces[0])
                else:
                    fuvs.append(ifs_texfaces[i])
        else:
            add_face(face, fuvs, orig_index)
            face = []
            if do_uvmap:
                fuvs = []
            orig_index += 1

    add_face(face, fuvs, orig_index)
    del add_face  # dont need this func anymore

    bpymesh = bpy.data.meshes.new(name="XXX")

    # EEKADOODLE
    bpymesh.vertices.add(1 + (len(ifs_points)))
    bpymesh.vertices.foreach_set("co", [0, 0, 0] + [a for v in ifs_points for a in v])  # XXX25 speed

    # print(len(ifs_points), faces, edges, ngons)

    try:
        bpymesh.tessfaces.add(len(faces))
        bpymesh.tessfaces.foreach_set("vertices_raw", [a for f in faces for a in (f + [0] if len(f) == 3 else f)])  # XXX25 speed
    except KeyError:
        print "one or more vert indices out of range. corrupt file?"
        #for f in faces:
        #   bpymesh.tessfaces.extend(faces, smooth=True)

    bpymesh.validate()
    # bpymesh.update()  # cant call now, because it would convert tessface

    if len(bpymesh.tessfaces) != len(faces):
        print '\tWarning: adding faces did not work! file is invalid, not adding UVs or vcolors'
        bpymesh.update()
        return bpymesh, ccw

    # Apply UVs if we have them
    if not do_uvmap:
        faces_uv = faces  # fallback, we didnt need a uvmap in the first place, fallback to the face/vert mapping.
    if coords_tex:
        #print(ifs_texpoints)
        # print(geom)
        uvlay = bpymesh.tessface_uv_textures.new()

        for i, f in enumerate(uvlay.data):
            f.image = bpyima
            fuv = faces_uv[i]  # uv indices
            for j, uv in enumerate(f.uv):
                # print(fuv, j, len(ifs_texpoints))
                try:
                    f.uv[j] = ifs_texpoints[fuv[j] + 1]  # XXX25, speedup
                except:
                    print '\tWarning: UV Index out of range'
                    f.uv[j] = ifs_texpoints[0]  # XXX25, speedup

    elif bpyima and len(bpymesh.tessfaces):
        # Oh Bugger! - we cant really use blenders ORCO for for texture space since texspace dosnt rotate.
        # we have to create VRML's coords as UVs instead.

        # VRML docs
        """
        If the texCoord field is NULL, a default texture coordinate mapping is calculated using the local
        coordinate system bounding box of the shape. The longest dimension of the bounding box defines the S coordinates,
        and the next longest defines the T coordinates. If two or all three dimensions of the bounding box are equal,
        ties shall be broken by choosing the X, Y, or Z dimension in that order of preference.
        The value of the S coordinate ranges from 0 to 1, from one end of the bounding box to the other.
        The T coordinate ranges between 0 and the ratio of the second greatest dimension of the bounding box to the greatest dimension.
        """

        # Note, S,T == U,V
        # U gets longest, V gets second longest
        xmin, ymin, zmin = ifs_points[0]
        xmax, ymax, zmax = ifs_points[0]
        for co in ifs_points:
            x, y, z = co
            if x < xmin:
                xmin = x
            if y < ymin:
                ymin = y
            if z < zmin:
                zmin = z

            if x > xmax:
                xmax = x
            if y > ymax:
                ymax = y
            if z > zmax:
                zmax = z

        xlen = xmax - xmin
        ylen = ymax - ymin
        zlen = zmax - zmin

        depth_min = xmin, ymin, zmin
        depth_list = [xlen, ylen, zlen]
        depth_sort = depth_list[:]
        depth_sort.sort()

        depth_idx = [depth_list.index(val) for val in depth_sort]

        axis_u = depth_idx[-1]
        axis_v = depth_idx[-2]  # second longest

        # Hack, swap these !!! TODO - Why swap??? - it seems to work correctly but should not.
        # axis_u,axis_v = axis_v,axis_u

        min_u = depth_min[axis_u]
        min_v = depth_min[axis_v]
        depth_u = depth_list[axis_u]
        depth_v = depth_list[axis_v]

        depth_list[axis_u]

        if axis_u == axis_v:
            # This should be safe because when 2 axies have the same length, the lower index will be used.
            axis_v += 1

        uvlay = bpymesh.tessface_uv_textures.new()

        # HACK !!! - seems to be compatible with Cosmo though.
        depth_v = depth_u = max(depth_v, depth_u)

        bpymesh_vertices = bpymesh.vertices[:]
        bpymesh_faces = bpymesh.tessfaces[:]

        for j, f in enumerate(uvlay.data):
            f.image = bpyima
            fuv = f.uv
            f_v = bpymesh_faces[j].vertices[:]  # XXX25 speed

            for i, v in enumerate(f_v):
                co = bpymesh_vertices[v].co
                fuv[i] = (co[axis_u] - min_u) / depth_u, (co[axis_v] - min_v) / depth_v

    # Add vcote
    if vcolor:
        # print(ifs_vcol)
        collay = bpymesh.tessface_vertex_colors.new()

        for f_idx, f in enumerate(collay.data):
            fv = bpymesh.tessfaces[f_idx].vertices[:]
            if len(fv) == 3:  # XXX speed
                fcol = f.color1, f.color2, f.color3
            else:
                fcol = f.color1, f.color2, f.color3, f.color4
            if ifs_colorPerVertex:
                for i, c in enumerate(fcol):
                    color_index = fv[i]  # color index is vert index
                    if ifs_color_index:
                        try:
                            color_index = ifs_color_index[color_index]
                        except:
                            print '\tWarning: per vertex color index out of range'
                            continue

                    if color_index < len(ifs_vcol):
                        c.r, c.g, c.b = ifs_vcol[color_index]
                    else:
                        #print('\tWarning: per face color index out of range')
                        pass
            else:
                if vcolor_spot:  # use 1 color, when ifs_vcol is []
                    for c in fcol:
                        c.r, c.g, c.b = vcolor_spot
                else:
                    color_index = faces_orig_index[f_idx]  # color index is face index
                    #print(color_index, ifs_color_index)
                    if ifs_color_index:
                        if color_index >= len(ifs_color_index):
                            print '\tWarning: per face color index out of range'
                            color_index = 0
                        else:
                            color_index = ifs_color_index[color_index]
                    # skip eedadoodle vert
                    color_index += 1
                    try:
                        col = ifs_vcol[color_index]
                    except IndexError:
                        # TODO, look
                        col = (1.0, 1.0, 1.0)
                    for i, c in enumerate(fcol):
                        c.r, c.g, c.b = col

    # XXX25
    # bpymesh.vertices.delete([0, ])  # EEKADOODLE

    bpymesh.update()
    bpymesh.validate()

    return bpymesh, ccw


def importMesh_IndexedLineSet(geom, ancestry):
    # VRML not x3d
    #coord = geom.getChildByName('coord') # 'Coordinate'
    coord = geom.getChildBySpec('Coordinate')  # works for x3d and vrml
    if coord:
        points = coord.getFieldAsArray('point', 3, ancestry)
    else:
        points = []

    if not points:
        print '\tWarning: IndexedLineSet had no points'
        return None

    ils_lines = geom.getFieldAsArray('coordIndex', 0, ancestry)

    lines = []
    line = []

    for il in ils_lines:
        if il == -1:
            lines.append(line)
            line = []
        else:
            line.append(int(il))
    lines.append(line)

    # vcolor = geom.getChildByName('color') # blender dosnt have per vertex color

    bpycurve = bpy.data.curves.new('IndexedCurve', 'CURVE')
    bpycurve.dimensions = '3D'

    for line in lines:
        if not line:
            continue
        # co = points[line[0]]  # UNUSED
        nu = bpycurve.splines.new('POLY')
        nu.points.add(len(line) - 1)  # the new nu has 1 point to begin with
        for il, pt in izip(line, nu.points):
            pt.co[0:3] = points[il]

    return bpycurve


def importMesh_PointSet(geom, ancestry):
    # VRML not x3d
    #coord = geom.getChildByName('coord') # 'Coordinate'
    coord = geom.getChildBySpec('Coordinate')  # works for x3d and vrml
    if coord:
        points = coord.getFieldAsArray('point', 3, ancestry)
    else:
        points = []

    # vcolor = geom.getChildByName('color') # blender dosnt have per vertex color

    bpymesh = bpy.data.meshes.new("XXX")
    bpymesh.vertices.add(len(points))
    bpymesh.vertices.foreach_set("co", [a for v in points for a in v])

    # No need to validate
    bpymesh.update()
    return bpymesh

GLOBALS['CIRCLE_DETAIL'] = 12


def bpy_ops_add_object_hack():  # XXX25, evil
    scene = bpy.context.scene
    obj = scene.objects[0]
    scene.objects.unlink(obj)
    bpymesh = obj.data
    bpy.data.objects.remove(obj)
    return bpymesh


def importMesh_Sphere(geom, ancestry):
    diameter = geom.getFieldAsFloat('radius', 0.5, ancestry)
    # bpymesh = Mesh.Primitives.UVsphere(GLOBALS['CIRCLE_DETAIL'], GLOBALS['CIRCLE_DETAIL'], diameter)

    bpy.ops.mesh.primitive_uv_sphere_add(segments=GLOBALS['CIRCLE_DETAIL'],
                                         ring_count=GLOBALS['CIRCLE_DETAIL'],
                                         size=diameter,
                                         view_align=False,
                                         enter_editmode=False,
                                         )

    bpymesh = bpy_ops_add_object_hack()

    bpymesh.transform(MATRIX_Z_TO_Y)
    return bpymesh


def importMesh_Cylinder(geom, ancestry):
    # bpymesh = bpy.data.meshes.new()
    diameter = geom.getFieldAsFloat('radius', 1.0, ancestry)
    height = geom.getFieldAsFloat('height', 2, ancestry)

    # bpymesh = Mesh.Primitives.Cylinder(GLOBALS['CIRCLE_DETAIL'], diameter, height)

    bpy.ops.mesh.primitive_cylinder_add(vertices=GLOBALS['CIRCLE_DETAIL'],
                                        radius=diameter,
                                        depth=height,
                                        end_fill_type='NGON',
                                        view_align=False,
                                        enter_editmode=False,
                                        )

    bpymesh = bpy_ops_add_object_hack()

    bpymesh.transform(MATRIX_Z_TO_Y)

    # Warning - Rely in the order Blender adds verts
    # not nice design but wont change soon.

    bottom = geom.getFieldAsBool('bottom', True, ancestry)
    side = geom.getFieldAsBool('side', True, ancestry)
    top = geom.getFieldAsBool('top', True, ancestry)

    if not top:  # last vert is top center of tri fan.
        # bpymesh.vertices.delete([(GLOBALS['CIRCLE_DETAIL'] + GLOBALS['CIRCLE_DETAIL']) + 1])  # XXX25
        pass

    if not bottom:  # second last vert is bottom of triangle fan
        # XXX25
        # bpymesh.vertices.delete([GLOBALS['CIRCLE_DETAIL'] + GLOBALS['CIRCLE_DETAIL']])
        pass

    if not side:
        # remove all quads
        # XXX25
        # bpymesh.tessfaces.delete(1, [f for f in bpymesh.tessfaces if len(f) == 4])
        pass

    return bpymesh


def importMesh_Cone(geom, ancestry):
    # bpymesh = bpy.data.meshes.new()
    diameter = geom.getFieldAsFloat('bottomRadius', 1.0, ancestry)
    height = geom.getFieldAsFloat('height', 2, ancestry)

    # bpymesh = Mesh.Primitives.Cone(GLOBALS['CIRCLE_DETAIL'], diameter, height)

    bpy.ops.mesh.primitive_cone_add(vertices=GLOBALS['CIRCLE_DETAIL'],
                                    radius1=diameter,
                                    radius2=0,
                                    depth=height,
                                    end_fill_type='NGON',
                                    view_align=False,
                                    enter_editmode=False,
                                    )

    bpymesh = bpy_ops_add_object_hack()

    bpymesh.transform(MATRIX_Z_TO_Y)

    # Warning - Rely in the order Blender adds verts
    # not nice design but wont change soon.

    bottom = geom.getFieldAsBool('bottom', True, ancestry)
    side = geom.getFieldAsBool('side', True, ancestry)

    if not bottom:  # last vert is on the bottom
        # bpymesh.vertices.delete([GLOBALS['CIRCLE_DETAIL'] + 1]) # XXX25
        pass
    if not side:  # second last vert is on the pointy bit of the cone
        # bpymesh.vertices.delete([GLOBALS['CIRCLE_DETAIL']]) # XXX25
        pass

    return bpymesh


def importMesh_Box(geom, ancestry):
    # bpymesh = bpy.data.meshes.new()

    size = geom.getFieldAsFloatTuple('size', (2.0, 2.0, 2.0), ancestry)

    # bpymesh = Mesh.Primitives.Cube(1.0)
    bpy.ops.mesh.primitive_cube_add(view_align=False,
                                    enter_editmode=False,
                                    )

    bpymesh = bpy_ops_add_object_hack()

    # Scale the box to the size set
    scale_mat = Matrix(((size[0], 0, 0), (0, size[1], 0), (0, 0, size[2]))) * 0.5
    bpymesh.transform(scale_mat.to_4x4())

    return bpymesh


def importShape(node, ancestry, global_matrix):
    def apply_texmtx(blendata, texmtx):
        for luv in bpydata.uv_layers.active.data:
            luv.uv = texmtx * luv.uv

    bpyob = node.getRealNode().blendObject

    if bpyob is not None:
        bpyob = node.blendData = node.blendObject = bpyob.copy()
        bpy.context.scene.objects.link(bpyob).select = True
    else:
        vrmlname = node.getDefName()
        if not vrmlname:
            vrmlname = 'Shape'

        # works 100% in vrml, but not x3d
        #appr = node.getChildByName('appearance') # , 'Appearance'
        #geom = node.getChildByName('geometry') # , 'IndexedFaceSet'

        # Works in vrml and x3d
        appr = node.getChildBySpec('Appearance')
        geom = node.getChildBySpec(['IndexedFaceSet', 'IndexedLineSet', 'PointSet', 'Sphere', 'Box', 'Cylinder', 'Cone'])

        # For now only import IndexedFaceSet's
        if geom:
            bpymat = None
            bpyima = None
            texmtx = None

            image_depth = 0  # so we can set alpha face flag later
            is_vcol = (geom.getChildBySpec('Color') is not None)

            if appr:
                #mat = appr.getChildByName('material') # 'Material'
                #ima = appr.getChildByName('texture') # , 'ImageTexture'
                #if ima and ima.getSpec() != 'ImageTexture':
                #   print('\tWarning: texture type "%s" is not supported' % ima.getSpec())
                #   ima = None
                # textx = appr.getChildByName('textureTransform')

                mat = appr.getChildBySpec('Material')
                ima = appr.getChildBySpec('ImageTexture')

                textx = appr.getChildBySpec('TextureTransform')

                if textx:
                    texmtx = translateTexTransform(textx, ancestry)

                bpymat = appr.getRealNode().blendData

                if bpymat is None:
                    # print(mat, ima)
                    if mat or ima:
                        if not mat:
                            mat = ima  # This is a bit dumb, but just means we use default values for all

                        # all values between 0.0 and 1.0, defaults from VRML docs
                        bpymat = bpy.data.materials.new(vrmlname)
                        bpymat.ambient = mat.getFieldAsFloat('ambientIntensity', 0.2, ancestry)
                        bpymat.diffuse_color = mat.getFieldAsFloatTuple('diffuseColor', [0.8, 0.8, 0.8], ancestry)

                        # NOTE - blender dosnt support emmisive color
                        # Store in mirror color and approximate with emit.
                        emit = mat.getFieldAsFloatTuple('emissiveColor', [0.0, 0.0, 0.0], ancestry)
                        bpymat.mirror_color = emit
                        bpymat.emit = (emit[0] + emit[1] + emit[2]) / 3.0

                        bpymat.specular_hardness = int(1 + (510 * mat.getFieldAsFloat('shininess', 0.2, ancestry)))  # 0-1 -> 1-511
                        bpymat.specular_color = mat.getFieldAsFloatTuple('specularColor', [0.0, 0.0, 0.0], ancestry)
                        bpymat.alpha = 1.0 - mat.getFieldAsFloat('transparency', 0.0, ancestry)
                        if bpymat.alpha < 0.999:
                            bpymat.use_transparency = True
                        if is_vcol:
                            bpymat.use_vertex_color_paint = True

                    if ima:
                        bpyima = ima.getRealNode().blendData

                        if bpyima is None:
                            ima_urls = ima.getFieldAsString('url', None, ancestry)

                            if ima_urls is None:
                                try:
                                    ima_urls = ima.getFieldAsStringArray('url', ancestry)  # in some cases we get a list of images.
                                except:
                                    ima_urls = None
                            else:
                                if '" "' in ima_urls:
                                    # '"foo" "bar"' --> ['foo', 'bar']
                                    ima_urls = [w.strip('"') for w in ima_urls.split('" "')]
                                else:
                                    ima_urls = [ima_urls]
                            # ima_urls is a list or None

                            if ima_urls is None:
                                print "\twarning, image with no URL, this is odd"
                            else:
                                for f in ima_urls:
                                    bpyima = image_utils.load_image(f, os.path.dirname(node.getFilename()), place_holder=False,
                                                                    recursive=False, convert_callback=imageConvertCompat)
                                    if bpyima:
                                        break

                                if bpyima:
                                    texture = bpy.data.textures.new(bpyima.name, 'IMAGE')
                                    texture.image = bpyima

                                    # Adds textures for materials (rendering)
                                    try:
                                        image_depth = bpyima.depth
                                    except:
                                        image_depth = -1

                                    mtex = bpymat.texture_slots.add()
                                    mtex.texture = texture

                                    mtex.texture_coords = 'UV'
                                    mtex.use_map_diffuse = True

                                    if image_depth in set([32, 128]):
                                        bpymat.use_transparency = True
                                        mtex.use_map_alpha = True
                                        mtex.alpha_factor = 0.0

                                    ima_repS = ima.getFieldAsBool('repeatS', True, ancestry)
                                    ima_repT = ima.getFieldAsBool('repeatT', True, ancestry)

                                    # To make this work properly we'd need to scale the UV's too, better to ignore th
                                    # texture.repeat =  max(1, ima_repS * 512), max(1, ima_repT * 512)

                                    if not ima_repS:
                                        bpyima.use_clamp_x = True
                                    if not ima_repT:
                                        bpyima.use_clamp_y = True
                elif ima:
                    bpyima = ima.getRealNode().blendData

                appr.blendData = bpymat
                if ima:
                    ima.blendData = bpyima

            bpydata = geom.getRealNode().blendData
            if bpydata is None:
                geom_spec = geom.getSpec()
                ccw = True
                if geom_spec == 'IndexedFaceSet':
                    bpydata, ccw = importMesh_IndexedFaceSet(geom, bpyima, ancestry)
                elif geom_spec == 'IndexedLineSet':
                    bpydata = importMesh_IndexedLineSet(geom, ancestry)
                elif geom_spec == 'PointSet':
                    bpydata = importMesh_PointSet(geom, ancestry)
                elif geom_spec == 'Sphere':
                    bpydata = importMesh_Sphere(geom, ancestry)
                elif geom_spec == 'Box':
                    bpydata = importMesh_Box(geom, ancestry)
                elif geom_spec == 'Cylinder':
                    bpydata = importMesh_Cylinder(geom, ancestry)
                elif geom_spec == 'Cone':
                    bpydata = importMesh_Cone(geom, ancestry)
                else:
                    print '\tWarning: unsupported type "%s"' % geom_spec
                    return

                if bpydata:
                    vrmlname = vrmlname + geom_spec
                    bpydata.name = vrmlname

                    if type(bpydata) == bpy.types.Mesh:
                        is_solid = geom.getFieldAsBool('solid', True, ancestry)
                        creaseAngle = geom.getFieldAsFloat('creaseAngle', None, ancestry)

                        if creaseAngle is not None:
                            bpydata.auto_smooth_angle = creaseAngle
                            bpydata.use_auto_smooth = True

                        # Only ever 1 material per shape
                        if bpymat:
                            bpydata.materials.append(bpymat)

                        if bpydata.uv_layers:
                            if texmtx:
                                # Apply texture transform?
                                apply_texmtx(blendata, texmtx)
                        # Done transforming the texture

                        # Must be here and not in IndexedFaceSet because it needs an object for the flip func. Messy :/
                        if not ccw:
                            # bpydata.flipNormals()
                            # XXX25
                            pass

                    # else could be a curve for example

            # if texmtx is defined, we need specific UVMap, hence a copy of the mesh...
            elif texmtx and blendata.uv_layers:
                bpydata = bpydata.copy()
                apply_texmtx(blendata, texmtx)

            geom.blendData = bpydata

            if bpydata:
                bpyob = node.blendData = node.blendObject = bpy.data.objects.new(vrmlname, bpydata)
                bpy.context.scene.objects.link(bpyob).select = True

    if bpyob:
        # Could transform data, but better the object so we can instance the data
        bpyob.matrix_world = getFinalMatrix(node, None, ancestry, global_matrix)


def importLamp_PointLight(node, ancestry):
    vrmlname = node.getDefName()
    if not vrmlname:
        vrmlname = 'PointLight'

    # ambientIntensity = node.getFieldAsFloat('ambientIntensity', 0.0, ancestry) # TODO
    # attenuation = node.getFieldAsFloatTuple('attenuation', (1.0, 0.0, 0.0), ancestry) # TODO
    color = node.getFieldAsFloatTuple('color', (1.0, 1.0, 1.0), ancestry)
    intensity = node.getFieldAsFloat('intensity', 1.0, ancestry)  # max is documented to be 1.0 but some files have higher.
    location = node.getFieldAsFloatTuple('location', (0.0, 0.0, 0.0), ancestry)
    # is_on = node.getFieldAsBool('on', True, ancestry) # TODO
    radius = node.getFieldAsFloat('radius', 100.0, ancestry)

    bpylamp = bpy.data.lamps.new("ToDo", 'POINT')
    bpylamp.energy = intensity
    bpylamp.distance = radius
    bpylamp.color = color

    mtx = Matrix.Translation(Vector(location))

    return bpylamp, mtx


def importLamp_DirectionalLight(node, ancestry):
    vrmlname = node.getDefName()
    if not vrmlname:
        vrmlname = 'DirectLight'

    # ambientIntensity = node.getFieldAsFloat('ambientIntensity', 0.0) # TODO
    color = node.getFieldAsFloatTuple('color', (1.0, 1.0, 1.0), ancestry)
    direction = node.getFieldAsFloatTuple('direction', (0.0, 0.0, -1.0), ancestry)
    intensity = node.getFieldAsFloat('intensity', 1.0, ancestry)  # max is documented to be 1.0 but some files have higher.
    # is_on = node.getFieldAsBool('on', True, ancestry) # TODO

    bpylamp = bpy.data.lamps.new(vrmlname, 'SUN')
    bpylamp.energy = intensity
    bpylamp.color = color

    # lamps have their direction as -z, yup
    mtx = Vector(direction).to_track_quat('-Z', 'Y').to_matrix().to_4x4()

    return bpylamp, mtx

# looks like default values for beamWidth and cutOffAngle were swapped in VRML docs.


def importLamp_SpotLight(node, ancestry):
    vrmlname = node.getDefName()
    if not vrmlname:
        vrmlname = 'SpotLight'

    # ambientIntensity = geom.getFieldAsFloat('ambientIntensity', 0.0, ancestry) # TODO
    # attenuation = geom.getFieldAsFloatTuple('attenuation', (1.0, 0.0, 0.0), ancestry) # TODO
    beamWidth = node.getFieldAsFloat('beamWidth', 1.570796, ancestry)  # max is documented to be 1.0 but some files have higher.
    color = node.getFieldAsFloatTuple('color', (1.0, 1.0, 1.0), ancestry)
    cutOffAngle = node.getFieldAsFloat('cutOffAngle', 0.785398, ancestry) * 2.0  # max is documented to be 1.0 but some files have higher.
    direction = node.getFieldAsFloatTuple('direction', (0.0, 0.0, -1.0), ancestry)
    intensity = node.getFieldAsFloat('intensity', 1.0, ancestry)  # max is documented to be 1.0 but some files have higher.
    location = node.getFieldAsFloatTuple('location', (0.0, 0.0, 0.0), ancestry)
    # is_on = node.getFieldAsBool('on', True, ancestry) # TODO
    radius = node.getFieldAsFloat('radius', 100.0, ancestry)

    bpylamp = bpy.data.lamps.new(vrmlname, 'SPOT')
    bpylamp.energy = intensity
    bpylamp.distance = radius
    bpylamp.color = color
    bpylamp.spot_size = cutOffAngle
    if beamWidth > cutOffAngle:
        bpylamp.spot_blend = 0.0
    else:
        if cutOffAngle == 0.0:  # this should never happen!
            bpylamp.spot_blend = 0.5
        else:
            bpylamp.spot_blend = beamWidth / cutOffAngle

    # Convert

    # lamps have their direction as -z, y==up
    mtx = Matrix.Translation(location) * Vector(direction).to_track_quat('-Z', 'Y').to_matrix().to_4x4()

    return bpylamp, mtx


def importLamp(node, spec, ancestry, global_matrix):
    if spec == 'PointLight':
        bpylamp, mtx = importLamp_PointLight(node, ancestry)
    elif spec == 'DirectionalLight':
        bpylamp, mtx = importLamp_DirectionalLight(node, ancestry)
    elif spec == 'SpotLight':
        bpylamp, mtx = importLamp_SpotLight(node, ancestry)
    else:
        print "Error, not a lamp"
        raise ValueError

    bpyob = node.blendData = node.blendObject = bpy.data.objects.new("TODO", bpylamp)
    bpy.context.scene.objects.link(bpyob).select = True

    bpyob.matrix_world = getFinalMatrix(node, mtx, ancestry, global_matrix)


def importViewpoint(node, ancestry, global_matrix):
    name = node.getDefName()
    if not name:
        name = 'Viewpoint'

    fieldOfView = node.getFieldAsFloat('fieldOfView', 0.785398, ancestry)  # max is documented to be 1.0 but some files have higher.
    # jump = node.getFieldAsBool('jump', True, ancestry)
    orientation = node.getFieldAsFloatTuple('orientation', (0.0, 0.0, 1.0, 0.0), ancestry)
    position = node.getFieldAsFloatTuple('position', (0.0, 0.0, 0.0), ancestry)
    description = node.getFieldAsString('description', '', ancestry)

    bpycam = bpy.data.cameras.new(name)

    bpycam.angle = fieldOfView

    mtx = Matrix.Translation(Vector(position)) * translateRotation(orientation)

    bpyob = node.blendData = node.blendObject = bpy.data.objects.new(name, bpycam)
    bpy.context.scene.objects.link(bpyob).select = True
    bpyob.matrix_world = getFinalMatrix(node, mtx, ancestry, global_matrix)


def importTransform(node, ancestry, global_matrix):
    name = node.getDefName()
    if not name:
        name = 'Transform'

    bpyob = node.blendData = node.blendObject = bpy.data.objects.new(name, None)
    bpy.context.scene.objects.link(bpyob).select = True

    bpyob.matrix_world = getFinalMatrix(node, None, ancestry, global_matrix)

    # so they are not too annoying
    bpyob.empty_draw_type = 'PLAIN_AXES'
    bpyob.empty_draw_size = 0.2


#def importTimeSensor(node):
def action_fcurve_ensure(action, data_path, array_index):
    for fcu in action.fcurves:
        if fcu.data_path == data_path and fcu.array_index == array_index:
            return fcu

    return action.fcurves.new(data_path=data_path, index=array_index)


def translatePositionInterpolator(node, action, ancestry):
    key = node.getFieldAsArray('key', 0, ancestry)
    keyValue = node.getFieldAsArray('keyValue', 3, ancestry)

    loc_x = action_fcurve_ensure(action, "location", 0)
    loc_y = action_fcurve_ensure(action, "location", 1)
    loc_z = action_fcurve_ensure(action, "location", 2)

    for i, time in enumerate(key):
        try:
            x, y, z = keyValue[i]
        except:
            continue

        loc_x.keyframe_points.insert(time, x)
        loc_y.keyframe_points.insert(time, y)
        loc_z.keyframe_points.insert(time, z)

    for fcu in (loc_x, loc_y, loc_z):
        for kf in fcu.keyframe_points:
            kf.interpolation = 'LINEAR'


def translateOrientationInterpolator(node, action, ancestry):
    key = node.getFieldAsArray('key', 0, ancestry)
    keyValue = node.getFieldAsArray('keyValue', 4, ancestry)

    rot_x = action_fcurve_ensure(action, "rotation_euler", 0)
    rot_y = action_fcurve_ensure(action, "rotation_euler", 1)
    rot_z = action_fcurve_ensure(action, "rotation_euler", 2)

    for i, time in enumerate(key):
        try:
            x, y, z, w = keyValue[i]
        except:
            continue

        mtx = translateRotation((x, y, z, w))
        eul = mtx.to_euler()
        rot_x.keyframe_points.insert(time, eul.x)
        rot_y.keyframe_points.insert(time, eul.y)
        rot_z.keyframe_points.insert(time, eul.z)

    for fcu in (rot_x, rot_y, rot_z):
        for kf in fcu.keyframe_points:
            kf.interpolation = 'LINEAR'


# Untested!
def translateScalarInterpolator(node, action, ancestry):
    key = node.getFieldAsArray('key', 0, ancestry)
    keyValue = node.getFieldAsArray('keyValue', 4, ancestry)

    sca_x = action_fcurve_ensure(action, "scale", 0)
    sca_y = action_fcurve_ensure(action, "scale", 1)
    sca_z = action_fcurve_ensure(action, "scale", 2)

    for i, time in enumerate(key):
        try:
            x, y, z = keyValue[i]
        except:
            continue

        sca_x.keyframe_points.new(time, x)
        sca_y.keyframe_points.new(time, y)
        sca_z.keyframe_points.new(time, z)


def translateTimeSensor(node, action, ancestry):
    """
    Apply a time sensor to an action, VRML has many combinations of loop/start/stop/cycle times
    to give different results, for now just do the basics
    """

    # XXX25 TODO
    if 1:
        return

    time_cu = action.addCurve('Time')
    time_cu.interpolation = Blender.IpoCurve.InterpTypes.LINEAR

    cycleInterval = node.getFieldAsFloat('cycleInterval', None, ancestry)

    startTime = node.getFieldAsFloat('startTime', 0.0, ancestry)
    stopTime = node.getFieldAsFloat('stopTime', 250.0, ancestry)

    if cycleInterval != None:
        stopTime = startTime + cycleInterval

    loop = node.getFieldAsBool('loop', False, ancestry)

    time_cu.append((1 + startTime, 0.0))
    time_cu.append((1 + stopTime, 1.0 / 10.0))  # anoying, the UI uses /10

    if loop:
        time_cu.extend = Blender.IpoCurve.ExtendTypes.CYCLIC  # or - EXTRAP, CYCLIC_EXTRAP, CONST,


def importRoute(node, ancestry):
    """
    Animation route only at the moment
    """

    if not hasattr(node, 'fields'):
        return

    routeIpoDict = node.getRouteIpoDict()

    def getIpo(act_id):
        try:
            action = routeIpoDict[act_id]
        except:
            action = routeIpoDict[act_id] = bpy.data.actions.new('web3d_ipo')
        return action

    # for getting definitions
    defDict = node.getDefDict()
    """
    Handles routing nodes to eachother

ROUTE vpPI.value_changed TO champFly001.set_position
ROUTE vpOI.value_changed TO champFly001.set_orientation
ROUTE vpTs.fraction_changed TO vpPI.set_fraction
ROUTE vpTs.fraction_changed TO vpOI.set_fraction
ROUTE champFly001.bindTime TO vpTs.set_startTime
    """

    #from_id, from_type = node.id[1].split('.')
    #to_id, to_type = node.id[3].split('.')

    #value_changed
    set_position_node = None
    set_orientation_node = None
    time_node = None

    for field in node.fields:
        if field and field[0] == 'ROUTE':
            try:
                from_id, from_type = field[1].split('.')
                to_id, to_type = field[3].split('.')
            except:
                print "Warning, invalid ROUTE", field
                continue

            if from_type == 'value_changed':
                if to_type == 'set_position':
                    action = getIpo(to_id)
                    set_data_from_node = defDict[from_id]
                    translatePositionInterpolator(set_data_from_node, action, ancestry)

                if to_type in set(['set_orientation', 'rotation']):
                    action = getIpo(to_id)
                    set_data_from_node = defDict[from_id]
                    translateOrientationInterpolator(set_data_from_node, action, ancestry)

                if to_type == 'set_scale':
                    action = getIpo(to_id)
                    set_data_from_node = defDict[from_id]
                    translateScalarInterpolator(set_data_from_node, action, ancestry)

            elif from_type == 'bindTime':
                action = getIpo(from_id)
                time_node = defDict[to_id]
                translateTimeSensor(time_node, action, ancestry)


def load_web3d(path,
               PREF_FLAT=False,
               PREF_CIRCLE_DIV=16,
               global_matrix=None,
               HELPER_FUNC=None,
               ):

    # Used when adding blender primitives
    GLOBALS['CIRCLE_DETAIL'] = PREF_CIRCLE_DIV

    #root_node = vrml_parse('/_Cylinder.wrl')
    if path.lower().endswith('.x3d'):
        root_node, msg = x3d_parse(path)
    else:
        root_node, msg = vrml_parse(path)

    if not root_node:
        print msg
        return

    if global_matrix is None:
        global_matrix = Matrix()

    # fill with tuples - (node, [parents-parent, parent])
    all_nodes = root_node.getSerialized([], [])

    for node, ancestry in all_nodes:
        #if 'castle.wrl' not in node.getFilename():
        #   continue

        spec = node.getSpec()
        '''
        prefix = node.getPrefix()
        if prefix=='PROTO':
            pass
        else
        '''
        if HELPER_FUNC and HELPER_FUNC(node, ancestry):
            # Note, include this function so the VRML/X3D importer can be extended
            # by an external script. - gets first pick
            pass
        if spec == 'Shape':
            importShape(node, ancestry, global_matrix)
        elif spec in set(['PointLight', 'DirectionalLight', 'SpotLight']):
            importLamp(node, spec, ancestry, global_matrix)
        elif spec == 'Viewpoint':
            importViewpoint(node, ancestry, global_matrix)
        elif spec == 'Transform':
            # Only use transform nodes when we are not importing a flat object hierarchy
            if PREF_FLAT == False:
                importTransform(node, ancestry, global_matrix)
            '''
        # These are delt with later within importRoute
        elif spec=='PositionInterpolator':
            action = bpy.data.ipos.new('web3d_ipo', 'Object')
            translatePositionInterpolator(node, action)
            '''

    # After we import all nodes, route events - anim paths
    for node, ancestry in all_nodes:
        importRoute(node, ancestry)

    for node, ancestry in all_nodes:
        if node.isRoot():
            # we know that all nodes referenced from will be in
            # routeIpoDict so no need to run node.getDefDict() for every node.
            routeIpoDict = node.getRouteIpoDict()
            defDict = node.getDefDict()

            for key, action in routeIpoDict.items():

                # Assign anim curves
                node = defDict[key]
                if node.blendData is None:  # Add an object if we need one for animation
                    node.blendData = node.blendObject = bpy.data.objects.new('AnimOb', None)  # , name)
                    bpy.context.scene.objects.link(node.blendObject).select = True

                if node.blendData.animation_data is None:
                    node.blendData.animation_data_create()

                node.blendData.animation_data.action = action

    # Add in hierarchy
    if PREF_FLAT is False:
        child_dict = {}
        for node, ancestry in all_nodes:
            if node.blendObject:
                blendObject = None

                # Get the last parent
                i = len(ancestry)
                while i:
                    i -= 1
                    blendObject = ancestry[i].blendObject
                    if blendObject:
                        break

                if blendObject:
                    # Parent Slow, - 1 liner but works
                    # blendObject.makeParent([node.blendObject], 0, 1)

                    # Parent FAST
                    try:
                        child_dict[blendObject].append(node.blendObject)
                    except:
                        child_dict[blendObject] = [node.blendObject]

        # Parent
        for parent, children in child_dict.items():
            for c in children:
                c.parent = parent

        # update deps
        bpy.context.scene.update()
        del child_dict


def load(operator, context, filepath="", global_matrix=None):

    load_web3d(filepath,
               PREF_FLAT=True,
               PREF_CIRCLE_DIV=16,
               global_matrix=global_matrix,
               )

    return set(['FINISHED'])
