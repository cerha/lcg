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
import re
import sys
import codecs

from lcg import *

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
    
    def __init__(self, parent, subdir=None, language='en',
                 input_encoding='ascii'):
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

        """
        assert parent is None or isinstance(parent, ContentNode)
        assert subdir is None or isinstance(subdir, types.StringType)
        assert isinstance(language, types.StringType) and \
               len(language) == 2
        assert isinstance(input_encoding, types.StringType)
        codecs.lookup(input_encoding)
        self._parent = parent
        self._subdir = subdir
        self._language = language
        self._input_encoding = input_encoding
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
                       'input_encoding': self._input_encoding})
        return cls(self, *args, **kwargs)
    
    def _input_file(self, name, ext='txt', lang=None):
        """Return the full path to the source file."""
        if lang:
            ext = lang +'.'+ ext
        return os.path.join(self.src_dir(), name + '.' + ext)
        
    def _read_file(self, name, ext='txt', comment=None, lang=None):
        """Return all the text read from the source file."""
        filename = self._input_file(name, ext=ext, lang=lang)
        fh = codecs.open(filename, encoding=self._input_encoding)
        try:
            lines = fh.readlines()
            if comment is not None:
                # This is a dirty hack.  It should be solved elsewhere.
                matcher = re.compile(comment)
                lines = [line for line in lines if not matcher.match(line)]
            content = ''.join(lines)
        except UnicodeDecodeError, e:
            raise Exception("Error while reading file %s: %s" % (filename, e))
        fh.close()
        return content

    def _parse_wiki_file(self, name, ext='txt', lang=None):
        """Parse the file and return a sequence of content elements."""
        p = wiki.Parser(self)
        return p.parse(self._read_file(name, ext=ext, lang=lang))
    
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

    def find_section(self, anchor):
        def find(anchor, sections):
            for s in sections:
                if s.anchor() == anchor:
                    return s
                found = find(anchor, s.sections())
                if found:
                    return found
            return None
        return find(anchor, self.sections())
    
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

    def input_encoding(self):
        """Return the name of encoding expected in source files.

        The name is a string accepted by 'UnicodeType.encode()'.

        """
        return self._input_encoding
    
    
class WikiNode(ContentNode):
    """A single-purpose class serving as a wiki parser and formatter.
    
    You simply instantiate this node (giving a wiki-formatted text as a
    constructor argument) and the text is parsed and a hierarchy of 'Content'
    elements representing the document is built.  Then you can access the
    content structure or simply export the content into HTML or use an
    'Exporter' class to dump a whole page.

    """

    def __init__(self, text, title=None, **kwargs):
        """Initialize the instance.

        Arguments:
        
          text -- the wiki-formatted text as a unicode string

        """
        self._text = text
        self._title_ = title
        super(WikiNode, self).__init__(None, '.', **kwargs)

    def _create_content(self):
        p = wiki.Parser(self)
        content = SectionContainer(self, p.parse(self._text), toc_depth=0)
        if not self._title_:
            sections = content.sections()
            if len(sections):
                self._title_ = sections[0].title()
            else:
                self._title_ = "LCG generated document"
        return content
    
    def _title(self):
        return self._title_
