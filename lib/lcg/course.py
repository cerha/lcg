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

This module includes classes used as an abstraction of a language course.  Each
course consists of lessons.  Lessons have a regular structure of sections.

All these classes make a tree structure with nodes capable of reading their
content from input resources (either directly from files or using helper
'Feeder' classes), exporting themselves into HTML and giving some information
about themselves.  This information is then used to build the IMS manifest for
the generated content package.

"""

import os
import sys
import shutil

from util import *
from ims import *
from content import *
from feed import *

class ContentNode(object):
    """Representation of one output document within a course material.

    This class represents a generic node of a course material capable of IMS
    export.  The derived classes defined below define a concrete implementation
    of the language course for Eurochance project.  Any other course structure
    is possible by proper implementation of derived classes.

    """
    
    def __init__(self, parent, subdir):
        """Initialize the instance.

        Arguments:

          parent -- parent node; the 'ContentNode' instance directly preceeding
            this node in the content hierarchy.  Can be None for the top node.
          subdir -- a directory name relative to parent's source directory.  All
            input resources are expected in this directory.  The output is also
            exported to a subdirectory of this name (relative to the destination
            directory of the parent node).

        """
        self._parent = parent
        self._subdir = subdir
        self._media = {}
        self._counter = Counter(1)
        self._content = self._create_content()
        self._children = self._create_children()
        
    def __str__(self):
        return "<%s title='%s' id='%s' src_dir='%s' output_file='%s'>" % \
               (self.__class__.__name__, self.title(), self.id(),
                self.src_dir(), self.output_file())

    def _create_content(self):
        """Create the content for this node as a 'Content' instance."""
        return Content(self)
    
    def _create_children(self):
        """Create any descendant nodes and return them in a sequence."""
        return ()
        
    def _read_resource(self, name):
        """Return all the text read from the resource file."""
        filename = os.path.join(self.src_dir(), '.'.join((name, 'en', 'txt')))
        return ''.join(open(filename).readlines())

    def _export(self, dir):
        """Write the output file just for this node."""
        #print "Exporting:", self
        #base = '../' * len(self.dst_dir().split('/'))
        base = "file://" + os.path.abspath(dir) + "/"
        filename = os.path.join(dir, self.output_file())
        file = open(filename, 'w')
        file.write("\n".join(('<html>\n<head>\n' + \
                              '<title>%s</title>\n' % self.full_title() + \
                              '<base href="%s">\n' % base + \
                              '</head>\n<body bgcolor="white">',
                              self._content.export(),
                              '</body></html>')))
        file.close()

    # Public methods

    def root_node(self):
        """Return the top-most node of the hierarchy."""
        if self._parent is None:
            return self
        else:
            return self._parent.root_node()
        
    def src_dir(self):
        """Return the absolute path to this node's source directory.

        In fact this path can be relative to current directory when the
        generator is being run from the command-line.

        """
        if self._parent is None:
            return self._subdir
        else:
            return os.path.normpath(os.path.join(self._parent.src_dir(),
                                                 self._subdir))

    def dst_dir(self):
        """Return the relative path to this node's output directory.

        The path is relative to the export directory.
        
        """
        if self._parent is None:
            return self._subdir
        else:
            return os.path.normpath(os.path.join(self._parent.dst_dir(),
                                                 self._subdir))

    def output_file(self):
        """Return full pathname of the output file relative to export dir."""
        return os.path.join(self.dst_dir(),
                            self.__class__.__name__.lower()+'.html')

    def id(self):
        """Return a unique id of this node as a string."""
        return "%s-%d" % (self.__class__.__name__.lower(), id(self))

    def full_title(self):
        title = self.title()
        node = self._parent
        while (node is not None):
            title = ' - '.join((node.title(), title))
            node = node._parent
        return title

    def title(self):
        """Return the title of this node as a string."""
        if hasattr(self, '_title'):
            return self._title
        return self.__class__.__name__

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
    
    def children(self):
        """Return the list of all subordinate nodes as a tuple."""
        return tuple(self._children)

    def counter(self):
        """Return the internal counter as a 'Counter' instance.

        This counter can be used by content elements to count sections or
        whatever, depending on type of the content...  There is only one
        counter for each node and it is not supposed to be used by other nodes,
        it should be used only within the 'Content' elements.

        """
        return self._counter
        
    def export(self, dir):
        """Write the output file for this node and all subsequent nodes."""
        subdir = os.path.join(dir, self.dst_dir())
        if not os.path.isdir(subdir):
            os.makedirs(subdir)
        self._export(dir)
        for m in self._media.values():
            m.export(dir)
        for node in self._children:
            node.export(dir)


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


class NumberedNode(InnerNode):
    """Numbered node has a serial number within its parent node."""

    def __init__(self, parent, subdir, number):
        self._number = number
        super(NumberedNode, self).__init__(parent, subdir)
        
    def title(self):
        return "%s %d: %s" % (self.__class__.__name__, self._number,
                              self._read_resource('title'))

    
class Course(InnerNode):
    """The course is a root node of the actual IMS package."""
    
    def __init__(self, dir):
        self._dir = dir
        super(Course, self).__init__(None, '')

    def _create_content(self):
        return TableOfContents(self)
    
    def _export(self, dir):
        super(Course, self)._export(dir)
        manifest = Manifest(self)
        manifest.write(dir)

    def output_file(self):
        return os.path.join(self.dst_dir(), 'index.html')

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
    shared_directory = 'media'
    
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
            assert os.path.exists(self._source_file()), \
                   "Media file '%s' doesn't exist!" % self._source_file()
        
    def url(self):
        return self._destination_file('')

    def _source_file(self):
        dir = not self._shared and self._parent.src_dir() \
              or os.path.join(self._parent.root_node().src_dir(),
                              self.shared_directory)
        return os.path.join(dir, self._file)

    def _destination_file(self, dir):
        subdir = self._shared and \
                 self.shared_directory or self._parent.dst_dir()
        return os.path.join(dir, subdir, self._file)

    def export(self, dir):
        src_path = self._source_file()
        dst_path = self._destination_file(dir)
        if not os.path.exists(dst_path) or \
               os.path.exists(src_path) and \
               os.path.getmtime(dst_path) < os.path.getmtime(src_path):
            if not os.path.isdir(os.path.dirname(dst_path)):
                os.makedirs(os.path.dirname(dst_path))
            # Either create the file with tts or copy from source directory.
            if self._tts_input is not None and not os.path.exists(src_path):
                print "%s: file does not exist! Generating with TTS '%s'." % \
                      (dst_path, self._tts_input)
                os.system(('echo "%s" | festival_client --ttw 2>/dev/null | '+\
                           'oggenc -q 2 --quiet - -o %s') % \
                          (self._tts_input, dst_path))
            else:
                shutil.copy(src_path, dst_path)
                print "%s: file copied." % dst_path
    

################################################################################
# Concrete implemantation of Eurochance Course structure.
################################################################################
 

class Unit(NumberedNode):
    """Unit is a collection of sections (Vocabulary, ."""
    
    def _create_children(self):
        return map(lambda s: s(self, ''),
                   (Vocabulary, Use, Grammar, Exercises, Consolidation))

    
class Module(NumberedNode):
    """Module is a collection of 'Unit' instances."""

    def _create_children(self):
        c = Counter(1)
        return map(lambda subdir: Unit(self, subdir, c.next()),
                   list_subdirs(self.src_dir()))


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


class Consolidation(TextNode):
    """A check list of competences achieved."""
    pass


class Exercises(ContentNode):
    """A section consisting of a sequence of exercises."""

    def _create_content(self):
        try:
            return PySpecFeeder(self.src_dir(), 'exercises').feed(self)
        except PySpecFeederError, e:
            print ' '.join(e.args)
            return Content(self)
    

class EurochanceCourse(Course):
    """The course is a root node which comprises a set of 'Module' instances."""

    def _create_children(self):
        c = Counter(1)
        return map(lambda subdir: Module(self, subdir, c.next()),
                   filter(lambda d: d not in('media'),
                          list_subdirs(self.src_dir())))

