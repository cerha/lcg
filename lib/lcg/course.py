# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004 Brailcom, o.p.s.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Course abstraction for Learning Content Generator.

This module includes classes used as an abstraction of a course structure based
on a tree structure with nodes capable of reading their content from input
files (either directly or using helper 'Feeder' classes) and giving some
information about themselves.  This information is then used to by the exporter
classes to write the output files in various formats (eg. as an IMS package or
static html pages).

In the second part of this module there are several derived classes which
define a concrete implementation of the language course for the Eurochance
project.  Any other course structure is possible by proper implementation of
derived classes.

"""

import os
import sys

from util import *
from content import *
from feed import *

class ContentNode(object):
    """Representation of one output document within a course material.

    This class represents a generic node of a course material.  Each node can
    have several children nodes and can depend on several 'Resource' instances.
    By instantiating a node, all the resources are read and the content is
    built and ready for export.
    
    """
    
    def __init__(self, parent, subdir, default_resource_dir='resources'):
        """Initialize the instance.

        Arguments:

          parent -- parent node; the 'ContentNode' instance directly preceeding
            this node in the content hierarchy.  Can be None for the top node.
          subdir -- a directory name relative to parent's source directory.  All
            input files are expected in this directory.
          default_resource_dir -- the LCG comes with a set of default resources
            (stylesheets, scripts and media files).  They are used if no custom
            files of the same name are present in the source directory.  This
            argument specifies the name of the directory, where LCG default
            resources are installed.


        """
        assert parent is None or isinstance(parent, ContentNode)
        assert type(subdir) == type('')
        self._parent = parent
        self._subdir = subdir
        self._default_resource_dir = default_resource_dir
        self._resources = {}
        self._counter = Counter(1)
        self._content = self._create_content()
        assert isinstance(self._content, Content)
        self._children = []
        children = self._create_children()
        for child in children:
            assert child._parent == self
            assert child in self._children
        if parent is not None:
            parent._register_child(self)
        self.stylesheet('default.css')

        
    def _register_child(self, child):
        assert isinstance(child, ContentNode)
        assert child not in self._children
        self._children.append(child)
        
    def __str__(self):
        return "<%s  id='%s' title='%s' subdir='%s'>" % \
               (self.__class__.__name__, self.id(), self.title(), self.subdir())

    def _create_content(self):
        """Create the content for this node as a 'Content' instance.

        This method should be overriden in derived classes to create the actual
        content displayed when this node is selected.

        """
        return Content(self)
    
    def _create_children(self):
        """Create any descendant nodes and return them in a sequence.

        This method should be overriden in derived classes which represent an
        inner node of the content tree.

        """
        return ()
        
    def _read_file(self, name):
        """Return all the text read from the source file."""
        filename = os.path.join(self.src_dir(), name+'.txt')
        return ''.join(open(filename).readlines())

    def _node_path(self):
        """Return the path from the root to this node as a sequence of nodes."""
        if self._parent is not None:
            return self._parent._node_path() + (self,)
        else:
            return (self,)
        
    def _id(self):
        # The not-necesarrily unique id string of this node.  This can be used
        # as a part of the unique id in connection with parent's id.
        if self._parent is not None:
            return '%02d%s' % (self._parent.index(self) + 1,
                               self.__class__.__name__.lower())
        else:
            return 'index'

    # Public methods

    def parent(self):
        """Return the parent node of this node."""
        return self._parent
    
    def root_node(self):
        """Return the top-most node of the hierarchy."""
        if self._parent is None:
            return self
        else:
            return self._parent.root_node()
        
    def children(self):
        """Return the list of all subordinate nodes as a tuple."""
        return tuple(self._children)

    def linear(self):
        """Return the linearized subtree of this node as a list."""
        return [self] + reduce(lambda l, n: l + n.linear(), self.children(), [])

    def next(self):
        """Return the node following this node in the linearized structure."""
        linear = self.root_node().linear()
        i = linear.index(self)
        if i < len(linear)-1:
            return linear[i+1]
        else:
            return None
    
    def prev(self):
        """Return the node preceeding this node in the linearized structure."""
        linear = self.root_node().linear()
        i = linear.index(self)
        if i > 0:
            return linear[i-1]
        else:
            return None

    def subdir(self):
        """Return the name of this node's subdirectory relative to root node."""
        if self._parent is None:
            return self._subdir
        else:
            return os.path.normpath(os.path.join(self._parent.subdir(),
                                                 self._subdir))

    def src_dir(self):
        return os.path.normpath(os.path.join(self.root_node().src_dir(),
                                             self.subdir()))
        
    def output_file(self):
        """Return full pathname of the output file relative to export dir."""
        return self.id() + '.html'

    def id(self):
        """Return a unique id of this node as a string."""
        if self._parent is None or self._parent is self.root_node():
            return self._id()
        else:
            return '-'.join((self._parent.id(), self._id()))
        
    def title(self):
        """Return the title of this node as a string."""
        if hasattr(self, '_title'):
            return self._title
        return self.__class__.__name__

    def full_title(self, separator=' - '):
        """Return the title of this node as a string."""
        return separator.join(map(lambda n: n.title(), self._node_path()))

    def lang(self):
        #TODO: pass from the script...
        return 'cs'

    def meta(self):
        """Return the meta data as a dictionary.

        This method returns just an empty dictionary, but it is supposed to be
        overriden in the implementing class.  Only root node's meta information
        is taken into account, however.

        """
        return {}
    
    def content(self):
        return self._content
    
    def resources(self, cls=None):
        """Return the list of all resources this node depends on.

        If cls is specifies, only instances of a specified class are returned.
        
        """
        resources = tuple(self._resources.values())
        if cls is not None:
            return filter(lambda r: isinstance(r, cls), resources)
        else:
            return resources

    def _resource(self, cls, key, *args, **kwargs):
        try:
            return self._resources[key]
        except KeyError:
            resource = apply(cls, (self,) + args, kwargs)
            self._resources[key] = resource
            return resource
        
    def media(self, file, shared=False, tts_input=None):
        """Return the 'Media' instance corresponing to given constructor args.

        The instances are cached.  They should never be constructed directly.
        They should always be acquired using this method.  The same applyes for
        the following two methods.

        """
        return self._resource(Media, (file, shared, tts_input),
                              file, shared=shared, tts_input=tts_input)

    def script(self, file):
        """Return the 'Script' resource instance."""
        return self._resource(Script, file, file)

    def stylesheet(self, file):
        """Return the 'Stylesheet' resource instance."""
        return self._resource(Stylesheet, file, file)

    
    def counter(self):
        """Return the internal counter as a 'Counter' instance.
        
        This counter can be used by content elements to count sections or
        whatever, depending on type of the content...  There is only one
        counter for each node and it is not supposed to be used by other nodes,
        it should be used only within the 'Content' elements.  For node
        counting, there is the 'index()' method below.
        
        """
        return self._counter

    def index(self, node):
        """Return the child node's index number within this node's children.

        The numbering begins at zero and corresponds to the natural order of
        child nodes.
        
        """
        return self._children.index(node)

    def default_resource_dir(self):
        """Return the name of the directory containing default LCG resources.

        This is the directory specified by the constructor argument of the same
        name.

        """
        
        return self._default_resource_dir

    
class TextNode(ContentNode):
    """A section of stuctured text read from a wiki-formatted file."""

    def _create_content(self):
        name = self.__class__.__name__.lower()
        return WikiText(self, self._read_file(name))

    
class InnerNode(ContentNode):
    """Inner node of the content tree.

    Inner node's content is an introduction of the content represented by
    subordinal nodes.
    
    """
    
    def _create_content(self):
        return WikiText(self, self._read_file('intro'))

    def title(self):
        return self._read_file('title')

    
class RootNode(InnerNode):
    """The root node of the content hierarchy.

    You still need to override the '_create_children()' method to get some
    sub-content into the course.
    
    """
    
    def __init__(self, dir):
        self._dir = dir
        super(RootNode, self).__init__(None, '')

    def src_dir(self):
        return self._dir

    
################################################################################

class Resource(object):
    """Representation of an external resource, the content depends on.

    Any 'ContentNode' (or more often a piece of 'Content' within it) can depend
    on several external resources.  They are maintained by parent 'ContentNode'
    so that the node is able to keep track of all the resources it depends on.
    
    This is a base class for particular resource types, such as `Media' or
    `Script'.

    """
    SUBDIR = 'resources'
    
    def __init__(self, parent, file, shared=True, check_file=True):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this resource belongs to.
          file -- path to the actual resource file relative to its parent
            node's source/destination directory.
          shared -- a boolean flag indicating that the file may be shared by
            multiple nodes (is not located within the node-specific
            subdirectory, but rather in a course-wide resource directory).
          check_file -- if true, an exception will be risen when the source file
            can not be found.

        """
        assert isinstance(parent, ContentNode), \
               "Not a 'ContentNode' instance: %s" % parent
        self._parent = parent
        self._file = file
        self._shared = shared
        if shared:
            src_dirs = [os.path.join(d, self.SUBDIR)
                        for d in (self._parent.root_node().src_dir(),
                                  self._parent.default_resource_dir())]
            dst_subdir = self.SUBDIR
        else:
            src_dirs = (parent.src_dir(), )
            dst_subdir = os.path.join(self.SUBDIR, parent.subdir())
        self._src_path = self._find_source_file(src_dirs, file)
        self._dst_path = os.path.join(dst_subdir, file)
        if check_file:
            assert os.path.exists(self._src_path), \
                   "Resource file '%s' doesn't exist!" % self._src_path
        
    def _find_source_file(self, dirs, file):
        for d in dirs:
            path = os.path.join(d, file)
            if os.path.exists(path):
                return path
        return os.path.join(dirs[0], file)
                
    def _destination_file(self, dir):
        return os.path.join(dir, self._dst_path)

    def url(self):
        return '/'.join(self._dst_path.split(os.path.sep))

    def name(self):
        return "%s_%s" % (self.__class__.__name__.lower(), id(self))

    def export(self, dir):
        dst_path = self._destination_file(dir)
        if not os.path.exists(dst_path) or \
               os.path.exists(self._src_path) and \
               os.path.getmtime(dst_path) < os.path.getmtime(self._src_path):
            if not os.path.isdir(os.path.dirname(dst_path)):
                os.makedirs(os.path.dirname(dst_path))
            self._export(dir)
            
    def _export(self, dir):
        shutil.copy(self._src_path, self._destination_file(dir))
        print "%s: file copied." % self._destination_file(dir)

    
class Media(Resource):
    """Representation of a media object used within the content.

    'Media' instances should not be constructed directly.  Use the
    'ContentNode.media()' method instead.

    """
    SUBDIR = 'media'
    
    def __init__(self, parent, file, shared=False, tts_input=None):
        """Initialize the instance.

        Arguments:

          parent, file, shared -- See 'Resource.__init__()'.
          tts_input -- if defined and the source file does not exist, the
            destination file will be generated via TTS.  The given string will
            be synthesized.

        """
        ext = os.path.splitext(file)[1]
        assert ext in ('.ogg','.mp3','.wav'), "Unsupported media type: %s" %ext
        super(Media, self).__init__(parent, file, shared=shared,
                                    check_file=(tts_input is None))
        self._tts_input = tts_input   
        
    def _find_source_file(self, dirs, file):
        basename, extension = os.path.splitext(file)
        for ext in ('.ogg','.mp3','.wav','.tts.txt', '.txt'):
            path = super(Media, self)._find_source_file(dirs, basename + ext)
            if os.path.exists(path):
                return path
        return super(Media, self)._find_source_file(dirs, file)

    def _command(self, which, errmsg):
        var = 'LCG_%s_COMMAND' % which
        try:
            return os.environ[var]
        except KeyError:
            raise "Environment variable %s not set!\n" % var + errmsg

    def _open_stream_from_tts(self):
        text = self._tts_input or \
                    ''.join(open(self._src_path).readlines())
        cmd = self._command('TTS', "Specify a TTS command synthesizing " + \
                            "the text on STDIN to a wave on STDOUT.")
        print "  - generating with TTS: %s" % cmd
        input, output = os.popen2(cmd, 'b')
        input.write(text)
        input.close()
        return output
    
    def _open_stream_from_encoder(self, output_format, wave):
        # The tmp file is a hack.  It would be better to send the data into a
        # pipe, but popen2 gets stuck while reading it.  Why?
        tmp = os.tmpnam() + '.wav'
        self._tmp_files.append(tmp)
        f = open(tmp, 'wb')
        copy_stream(wave, f)
        f.close()
        cmd = self._command(output_format, "Specify a command encoding a " + \
                            "wave on STDIN to %s on STDOUT." % output_format)
        print "  - converting to %s: %s" % (output_format, cmd)
        output = os.popen('cat %s |' % tmp + cmd)
        #input, output = os.popen2(convert_cmd)
        #copy_stream(wave, input)
        #input.close()
        return output

    
    def _export(self, dir):
        # Either create the file with tts or copy from source directory.
        input_format = os.path.splitext(self._src_path)[1].upper()[1:]
        output_format = os.path.splitext(self._dst_path)[1].upper()[1:]
        if input_format == output_format and os.path.exists(self._src_path):
            return super(Media, self)._export(dir)
        dst_path = self._destination_file(dir)
        wave = None
        data = None
        self._tmp_files = []
        try:
            print dst_path + ':'
            # Open the input stream
            if input_format == 'WAV' and os.path.exists(self._src_path):
                wave = open(self._src_path)
            elif input_format in ('TXT', 'TTS.TXT') or \
                     self._tts_input is not None:
                wave = self._open_stream_from_tts() 
            else:
                raise "Unknown input format: %s" % input_format
            if output_format == 'WAV':
                data = wave
            else:
                data = self._open_stream_from_encoder(output_format, wave)
            # Write the output stream
            output_file = open(dst_path, 'wb')
            copy_stream(data, output_file)
            output_file.close()
        finally:
            if wave is not None:
                wave.close()                
            if data is not None:
                data.close()
            # This is just because of the hack in _open_output_stream().
            for f in self._tmp_files:
                os.remove(f)
        
        
class Script(Resource):
    """Representation of a script object used within the content.

    The 'Script' instances should not be constructed directly.  Use the
    'ContentNode.script()' method instead.

    """
    SUBDIR = 'scripts'

    
class Stylesheet(Resource):
    """Representation of a stylesheet used within the content.

    The 'Stylesheet' instances should not be constructed directly.  Use the
    'ContentNode.stylesheet()' method instead.

    """
    SUBDIR = 'css'


################################################################################
# Concrete implemantation of Eurochance course structure.
################################################################################


class Vocabulary(ContentNode):
    """A section comprising a list of vocabulary."""

    def _create_content(self):
        return ExcelVocabFeeder(self.src_dir(), 'vocabulary.xls').feed(self)
        
    
class Use(TextNode):
    """Key language use."""
    _title = "Key Language Use"
    pass


class Grammar(TextNode):
    """Key grammar explanation."""
    _title = "Key Grammar"
    pass


class Exercises(ContentNode):
    """A section consisting of a sequence of exercises."""

    def _create_content(self):
        return ExerciseFeeder(self.src_dir(), 'exercises.txt').feed(self)


class Consolidation(TextNode):
    """A check list of competences achieved."""
    pass

        
class Unit(InnerNode):
    """Unit is a collection of sections (Vocabulary, Grammar, Exercises...)."""
    
    def _create_children(self):
        subdir = { Exercises: 'exercises' }
        return map(lambda s: s(self, subdir.get(s, '')),
                   (Vocabulary, Use, Grammar, Exercises, Consolidation))

    def _id(self):
        return 'unit%02d' % (self._parent.index(self)+1)

    def title(self):
        title = super(Unit, self).title()
        return "Unit %d: %s" % (self._parent.index(self)+1, title)

    
class EurochanceCourse(RootNode):
    """The course is a root node which comprises a set of 'Unit' instances."""

    def _create_children(self):
        return map(lambda d: Unit(self,d),
                   filter(lambda d: d[0] in map(str, range(0, 9)),
                          list_subdirs(self.src_dir())))

    def meta(self):
        return {'author': 'Eurochance team',
                'copyright': "Copyright (c) 2004 Brailcom, o.p.s."}

