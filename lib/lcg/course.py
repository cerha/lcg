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
resources (either directly from files or using helper 'Feeder' classes) and
giving some information about themselves.  This information is then used to
by the exporter classes to write the output files in various formats (eg. as an
IMS package or static html pages).

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
    have several children nodes and can depend on several 'Media' instances.
    By instantiating a node, all the resources are read and the content is
    built and ready for export.
    
    """
    
    def __init__(self, parent, subdir):
        """Initialize the instance.

        Arguments:

          parent -- parent node; the 'ContentNode' instance directly preceeding
            this node in the content hierarchy.  Can be None for the top node.
          subdir -- a directory name relative to parent's source directory.  All
            input resources are expected in this directory.

        """
        assert parent is None or isinstance(parent, ContentNode)
        assert type(subdir) == type('')
        self._parent = parent
        self._subdir = subdir
        self._media = {}
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

        
    def _register_child(self, child):
        assert isinstance(child, ContentNode)
        assert child not in self._children
        self._children.append(child)
        
    def __str__(self):
        return "<%s title='%s' id='%s' subdir='%s' output_file='%s'>" % \
               (self.__class__.__name__, self.title(), self.id(),
                self.subdir(), self.output_file())

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
        
    def _read_resource(self, name):
        """Return all the text read from the resource file."""
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

    def meta(self):
        """Return the meta data as a dictionary.

        This method returns just an empty dictionary, but it is supposed to be
        overriden in the implementing class.  Only root node's meta information
        is taken into account, however.

        """
        return {}
    
    def content(self):
        return self._content
    
    def list_media(self):
        """Return the list of all 'Media' objects within this node's content."""
        return tuple(self._media.values())

    def media(self, file, shared=False, tts_input=None):
        """Return the 'Media' instance corresponing to given constructor args.

        The instances are cached.  They should never be constructed directly.
        They should always be acquired using this method.

        The arguments correspond to arguments of 'Media' constructor.

        """
        key = (file, shared, tts_input)
        try:
            return self._media[key]
        except KeyError:
            media = Media(self, file, shared=shared, tts_input=tts_input)
            self._media[key] = media
            return media
    
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
        

class TextNode(ContentNode):
    """A section of stuctured text read from a wiki-formatted file."""

    def _create_content(self):
        name = self.__class__.__name__.lower()
        return WikiText(self, self._read_resource(name))

    
class InnerNode(ContentNode):
    """Inner node of the content tree.

    Inner node's content is an introduction of the content represented by
    subordinal nodes.
    
    """
    
    def _create_content(self):
        return WikiText(self, self._read_resource('intro'))

    def title(self):
        return self._read_resource('title')

    
class Course(InnerNode):
    """The root node of the content hierarchy.

    You still need to override the '_create_children()' method to get some
    sub-content into the course.
    
    """
    
    def __init__(self, dir):
        self._dir = dir
        super(Course, self).__init__(None, '')

    def _create_content(self):
        return TableOfContents(self)
    
    def src_dir(self):
        return self._dir

################################################################################

class Media(object):
    """Representation of a media object used within the content.

    Any 'ContentNode' (or more often a piece of 'Content' within it) can use
    media objects (typically recordings).  All the media objects are maintained
    by parent 'ContentNode' so that the node is able to keep track of all media
    objects it depends on.  That is also why 'Media' instances should not be
    constructed directly.  Use the 'ContentNode.media()' method instead.

    """
    SUBDIRECTORY = 'media'
    
    def __init__(self, parent, file, shared=False, tts_input=None):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this media object is part of.
          file -- path to the actual media file relative to its parent node's
            source/destination directory.
          shared -- a boolean flag indicating that the file is not located
            within the source/destination directory, but rather in a 'Course'
            wide media directory.
          tts_input -- if defined and the source file does not exist, the
            destination file will be generated via TTS.  The given string will be
            synthesized.

        """
        assert isinstance(parent, ContentNode), \
               "Not a 'ContentNode' instance: %s" % parent
        self._parent = parent
        self._file = file
        self._shared = shared
        self._tts_input = tts_input
        if tts_input is None:
            assert os.path.exists(self.source_file()), \
                   "Media file '%s' doesn't exist!" % self.source_file()
        
    def source_file(self):
        dir = not self._shared and self._parent.src_dir() \
              or os.path.join(self._parent.root_node().src_dir(),
                              self.SUBDIRECTORY)
        return os.path.join(dir, self._file)

    def destination_file(self, dir):
        subdir = self.SUBDIRECTORY
        if not self._shared:
            subdir = os.path.join(subdir, self._parent.subdir())
        return os.path.join(dir, subdir, self._file)

    def url(self):
        return self.destination_file('')

    def tts_input(self):
        return self._tts_input

    

################################################################################
# Concrete implemantation of Eurochance Course structure.
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

    
    
class EurochanceCourse(Course):
    """The course is a root node which comprises a set of 'Unit' instances."""

    def _create_children(self):
        return map(lambda d: Unit(self, d), list_subdirs(self.src_dir()))

    def meta(self):
        return {'author': 'Eurochance team',
                'copyright': "Copyright (c) 2004 Brailcom, o.p.s."}

