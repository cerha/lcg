# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005 Brailcom, o.p.s.
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

This module implements an abstraction of a course structure based
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
import codecs

from util import *
from content import *
from resources import *
from feed import *

class ContentNode(object):
    """Representation of one output document within a course material.

    This class represents a generic node of a course material.  Each node has
    its 'Content', may have several children nodes and may depend on several
    'Resource' instances.

    By instantiating a node, all the resources are read and the content is
    built and ready for export.
    
    """

    _TITLE = _("Node")
    
    """The title is a string used to reference to the node from within the
    generated content (eg. in Tables Of Contents etc.).  The derived
    classes should define some more meaningful titles, such as 'Lesson',
    'Module' etc."""

    _ABBREV_TITLE = None
    
    def __init__(self, parent, subdir=None,
                 language='en', input_encoding='ascii',
                 default_resource_dir='resources'):
        """Initialize the instance.

        Arguments:

          parent -- parent node; the 'ContentNode' instance directly preceeding
            this node in the content hierarchy.  Can be None for the top node.
          subdir -- a directory name relative to parent's source directory.  All
            input files are expected in this directory.
          language -- content language as a lowercase ISO 639-1 Alpha-2
            language code.
          input_encoding -- The content read from source files is expected in
            the specified encoding (ASCII by default).  The output encoding is
            set by the used exporter class.
          default_resource_dir -- the LCG comes with a set of default resources
            (stylesheets, scripts and media files).  They are used if no custom
            files of the same name are present in the source directory.  This
            argument specifies the name of the directory, where LCG default
            resources are installed.

        """
        assert parent is None or isinstance(parent, ContentNode)
        assert subdir is None or isinstance(subdir, types.StringType)
        assert isinstance(language, types.StringType)
        assert isinstance(input_encoding, types.StringType)
        assert isinstance(default_resource_dir, types.StringType)
        codecs.lookup(input_encoding)
        self._parent = parent
        self._subdir = subdir
        self._language = language
        self._input_encoding = input_encoding
        self._default_resource_dir = default_resource_dir
        self._resources = {}
        self._counter = Counter(1)
        self._registered_children = []
        content = self._create_content()
        if isinstance(content, Content):
            self._content = content
        else:
            self._content = Container(self, content)
        self._children = self._create_children()
        for child in self._children:
            assert child._parent == self
            assert child in self._registered_children
        if parent is not None:
            parent._register_child(self)
        self.resource(Stylesheet, 'default.css')
        
    def _register_child(self, child):
        assert isinstance(child, ContentNode)
        assert child not in self._registered_children
        self._registered_children.append(child)
        
    def __str__(self):
        return "<%s  id='%s' title='%s' subdir='%s'>" % \
               (self.__class__.__name__, self.id(), self.title(), self.subdir())

    def _create_content(self):
        """Create the content for this node.

        This method should be overriden in derived classes to create the actual
        content displayed when this node is selected.

        The returned value must be a 'Content' instance or a sequence of
        'Content' instances.

        """
        return Content(self)
    
    def _create_children(self):
        """Create any descendant nodes and return them in a sequence.

        This method should be overriden in derived classes which represent an
        inner node of the content tree.

        """
        return ()

    def _create_child(self, cls, *args, **kwargs):
        """Helper method to be used within '_create_children()'."""
        kwargs.update({'language': self._language,
                       'input_encoding': self._input_encoding,
                       'default_resource_dir': self._default_resource_dir})
        return cls(self, *args, **kwargs)
    
    def _input_file(self, name, ext='txt'):
        """Return the full path to the source file."""
        return os.path.join(self.src_dir(), name + '.' + ext)
        
    def _read_file(self, name, comment=None):
        """Return all the text read from the source file."""
        filename = self._input_file(name)
        fh = codecs.open(filename, encoding=self._input_encoding)
        try:
            lines = fh.readlines()
            if comment is not None:
                matcher = re.compile(comment)
                lines = [line for line in lines if not matcher.match(line)]
            content = ''.join(lines)
        except UnicodeDecodeError, e:
            raise Exception("Error while reading file %s: %s" % (filename, e))
        fh.close()
        return content

    def _node_path(self):
        """Return the path from the root to this node as a sequence of nodes."""
        if self._parent is not None:
            return self._parent._node_path() + (self,)
        else:
            return (self,)
        
    def _id(self):
        """Return the textual identifier of this node as a string.
        
        The identifier is not necesarrily unique within all nodes, but is
        unique within its parent's children.  Thus it can be used
        as unique in combination with parent's unique id.  See the public
        method 'id()' for that.
        
        """
        if self._parent is not None:
            name = camel_case_to_lower(self.__class__.__name__)
            return '%02d-%s' % (self._parent.index(self) + 1, name)
        else:
            return 'index'

    def _title(self):
        """Return the title of this node as a string."""
        return self._TITLE

    def _abbrev_title(self):
        """Return the abbreviated title of this node as a string."""
        return self._ABBREV_TITLE
    
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

    def sections(self):
        return self._content.sections()
    
    def url(self):
        return self.output_file()
    
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
        """Return this node's subdirectory name relative to the root node."""
        if self._parent is None:
            return ''
        elif self._subdir is None:
            return self._parent.subdir()
        else:
            return os.path.join(self._parent.subdir(), self._subdir)

    def src_dir(self):
        if self._parent is None:
            return self._subdir
        else:
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
        
    def title(self, abbrev=False):
        """Return the title of this node as a string."""
        abbrev_title = self._abbrev_title()
        if abbrev_title is not None:
            if abbrev:
                return abbrev_title
            else:
                return "%s: %s" % (abbrev_title, self._title())
        else:
            return self._title()
    
    def full_title(self, separator=' - '):
        """Return the full title of this node as a string.

        Full title is made of titles of all nodes in the path.
        
        """
        return separator.join([n.title(abbrev=True) for n in self._node_path()])

    def language(self):
        """Return the content language as an ISO 639-1 Alpha-2 code."""
        return self._language

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

    def resource(self, cls, *args, **kwargs):
        """Get the resource instance.
        
        The instances are cached.  They should never be constructed directly.
        They should always be allocated using this method.  

        """
        assert issubclass(cls, Resource)
        key = (cls, args, tuple(kwargs.items()))
        try:
            return self._resources[key]
        except KeyError:
            resource = apply(cls, (self,) + args, kwargs)
            self._resources[key] = resource
            return resource
        
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

    def input_encoding(self):
        """Return the name of encoding expected in source files.

        The name is a string accepted by 'UnicodeType.encode()'.

        """
        return self._input_encoding
    
    
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
        return (WikiText(self, self._read_file('intro')),
                TableOfContents(self, title=_("Table of Contents:")))
    
    def _title(self):
        return self._read_file('title')

    
class RootNode(InnerNode):
    """The root node of the content hierarchy.

    The only special thing about this node is, that it doesn't have a parent.
    
    You still need to override the '_create_children()' method to get some
    content into the course.

    """
    def __init__(self, *args, **kwargs):
        super(RootNode, self).__init__(None, *args, **kwargs)


################################################################################
# A Concrete implemantation of Eurochance course structure.
################################################################################

class Unit(ContentNode):
    """Unit is a collection of sections (Vocabulary, Grammar, Exercises...)."""
    _EXERCISE_SECTION_SPLITTER = re.compile(r"\r?\n====+\s*\r?\n")

    def _id(self):
        return 'unit%02d' % self._parent.index(self)
    
    def _abbrev_title(self, abbrev=False):
        return _("Unit %d") % self._parent.index(self)

    def _title(self, abbrev=False):
        return self._read_file('title')

    def _create_content(self):
        feeder = ExcelVocabFeeder(self._input_file('vocabulary', 'xls'),
                                  input_encoding=self._input_encoding)
        vocab = feeder.feed(self)
        sections = (Section(self, _("Aims and Objectives"),
                            WikiText(self, self._read_file('aims'))),
                    Section(self, _("Vocabulary"),
                            VocabList(self, vocab)),
                    Section(self, _("Grammar"),
                            self._create_grammar(self._read_file('grammar')),
                            toc_depth=99),
                    Section(self, _("Exercises"),
                            self._create_exercises(vocab), toc_depth=1),
                    Section(self, _("Checklist"),
                            WikiText(self, self._read_file('checklist'))))
        return Container(self, sections, toc_depth=2)

    def _create_grammar(self, text):
        text, sections = wiki.parse_sections(text)
        def make_sections(sections):
            return [Section(self, s.title(),
                            [WikiText(self, s.text())] +
                            make_sections(s.sections()))
                    for s in sections]
        return [WikiText(self, text)] + make_sections(sections)
    
    def _create_exercises(self, vocab):
        filename = self._input_file('exercises')
        text = self._read_file('exercises', '^//')
        splittable = SplittableText(text, input_file=filename)
        pieces = splittable.split(self._EXERCISE_SECTION_SPLITTER)
        assert len(pieces) == 5, \
               "%s: 5 sections expected, %d found." % (filename, len(pieces))
        titles = (_("Vocabulary Practice"),
                  _("Listening Comprehension"),
                  _("General Comprehension"),
                  _("Grammar Practice"),
                  _("Consolidation"))
        enc = self._input_encoding
        return [Section(self, _("Section %d") + ': ' + title,
                        ExerciseFeeder(piece, vocabulary=vocab,
                                       input_encoding=enc).feed(self))
                for title, piece in zip(titles, pieces)]

    
class Instructions(TextNode):
    """A general set of pre-course instructions."""
    _TITLE = _("General Course Instructions")

    def _create_content(self):
        return (super(Instructions, self)._create_content(),
                TableOfContents(self))

    
    def _create_children(self):
        return [self._create_child(ExerciseInstructions, e, 'help')
                for e in Exercise.used_types()]

    def _id(self):
        return 'instructions'

    
class ExerciseInstructions(TextNode):
    """Exercise instructions."""
    def __init__(self, parent, exercise_class_, *args, **kwargs):
        assert issubclass(exercise_class_, Exercise)
        self._exercise_class_ = exercise_class_
        super(ExerciseInstructions, self).__init__(parent, *args, **kwargs)
        
    def _create_content(self):
        try:
            return WikiText(self, self._read_file(self._exercise_class_.id()))
        except IOError, e:
            print "Warning: %s" % e
            return Content(self)

    def title(self, abbrev=False):
        return _("Instructions for %s") % self._exercise_class_.name()

    def _id(self):
        return self._exercise_class_.id()

    def src_dir(self):
        return os.path.join(self.default_resource_dir(), 'help')

    
class CourseIndex(ContentNode):
    _TITLE = _("Detailed Course Index")

    def _create_content(self):
        return TableOfContents(self, item=self.parent(), depth=3)

    
class EurochanceCourse(RootNode):
    """The course is a root node which comprises a set of 'Unit' instances."""

    def _create_children(self):
        units = [self._create_child(Unit, subdir=d)
                 for d in list_subdirs(self.src_dir())
                 if d[0] in map(str, range(0, 9))]
        return [self._create_child(Instructions)] + \
               units + \
               [self._create_child(CourseIndex)]
    
    def meta(self):
        return {'author': 'Eurochance Team',
                'copyright': "Copyright (c) 2004 Eurochance Team"}

