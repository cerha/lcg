# -*- coding: iso8859-2 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
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
    _PARENT_ID_PREFIX = True
    
    def __init__(self, parent, subdir=None, language='en',
                 input_encoding='ascii'):
        """Initialize the instance.

        Arguments:

          parent -- parent node; the 'ContentNode' instance directly preceding
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
        self._counters = {}
        self._registered_children = []
        self._wiki_parser = wiki.Parser(self)
        content = self._create_content()
        if isinstance(content, Content):
            self._content = content
        else:
            assert isinstance(content, (types.TupleType, types.ListType))
            self._content = SectionContainer(self, content)
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
    
    def _input_file(self, name, ext='txt', lang=None, dir=None):
        """Return the full path to the source file."""
        if lang:
            ext = lang +'.'+ ext
        if dir is None:
            dir = self.src_dir()
        return os.path.join(dir, name + '.' + ext)
        
    def _read_file(self, name, ext='txt', comment=None, dir=None, lang=None):
        """Return all the text read from the source file."""
        filename = self._input_file(name, ext=ext, lang=lang, dir=dir)
        if not os.path.exists(filename):
            filename2 = self._input_file(name, ext=ext, dir=dir)
            print "File '%s' not found. Trying '%s' instead." % (filename,
                                                                  filename2)
            filename = filename2
        fh = codecs.open(filename, encoding=self._input_encoding)
        try:
            lines = fh.readlines()
            marker = unicodedata.lookup('ZERO WIDTH NO-BREAK SPACE')
            if lines and lines[0][0] == marker:
                # Strip the Unicode marker 
                lines[0] = lines[0][1:]
            if comment is not None:
                # This is a hack (it breaks line numbering).
                lines = [l for l in lines if not re.compile(comment).match(l)]
            content = ''.join(lines)
        except UnicodeDecodeError, e:
            raise Exception("Error while reading file %s: %s" % (filename, e))
        fh.close()
        return content

    def parse_wiki_text(self, text):
        """Parse the file and return a sequence of content elements."""
        return self._wiki_parser.parse(text)
    
    def parse_wiki_file(self, name, ext='txt', lang=None):
        """Parse the file and return a sequence of content elements."""
        return self.parse_wiki_text(self._read_file(name, ext=ext, lang=lang))
    
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
            return camel_case_to_lower(self.__class__.__name__)
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
        """Return all the top-level sections within this node's content."""
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

    def find_node(self, id):
        def find(id, node):
            if node.id() == id:
                return node
            for n in node.children():
                found = find(id, n)
                if found:
                    return found
            return None
        return find(id, self)
    
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
        """Return the node preceding this node in the linearized structure."""
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
        id = self._id()
        if self._parent is None:
            return id
        same = [n for n in self._parent.children() if n._id() == id]
        if len(same) > 1:
            id += '-%02d' % (same.index(self) + 1)
        if self._parent is self.root_node() or not self._PARENT_ID_PREFIX:
            return id
        else:
            return '-'.join((self._parent.id(), id))
        
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

        If cls is specified, only instances of given class are returned.
        
        """
        resources = self._resources.keys()
        if cls is not None:
            return tuple(filter(lambda r: isinstance(r, cls), resources))
        else:
            return tuple(resources)

    def resource(self, cls, file, **kwargs):
        """Get the resource instance.
        
        There is some additional magic so the instances should never be
        constructed directly.  Always use this method to allocate a resource.
        The arguments correspond to arguments of the 'resource()' function.

        """
        result = resource(cls, self, file, **kwargs)
        if isinstance(result, (types.ListType, types.TupleType)):
            for r in result:
                self._resources[r] = 1
        else:
            self._resources[result] = 1
        return result
        
    def counter(self, key=None):
        """Return the internal counter as a 'Counter' instance.
        
        This counter can be used by content elements to count their occurences
        within a node.  There is one counter for each distinct key, which can
        be given as first argument.  This key can be for example a class of the
        content element to allow independent counting of different elements.

        See also the 'index()' method below for node counting.
        
        """
        try:
            return self._counters[key]
        except KeyError:
            self._counters[key] = c =Counter(1)
            return c
            

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
    
    
class RootNode(ContentNode):
    """Root node of the hierarchy.

    The only difference is that 'RootNone' doesn't take the 'parent' constructor
    argument.

    """
    
    def __init__(self, dir, **kwargs):
        """Initialize the instance.

        The arguments are inherited from the parent class, except for 'parent'
        which is not needed for the root node.
          
        """
        super(RootNode, self).__init__(None, dir, **kwargs)

    
class _WikiNode(ContentNode):

    def __init__(self, *args, **kwargs):
        """Initialize the instance.

        Arguments:
        
          title -- the page title as a unicode string.  If None, the title of
            the first top-level section within the content will be used.  Thus
            it is required, that the document contains just one top-level
            section, when the title is not specified, or an exception will be
            raised.

          The other arguments are inherited from the parent class.
          
        """
        self._title_ = kwargs.get('title')
        if kwargs.has_key('title'): del kwargs['title']
        super(_WikiNode, self).__init__(*args, **kwargs)

    def _source_text(self):
        return ""
        
    def _create_content(self):
        sections = self.parse_wiki_text(self._source_text())
        if self._title_ is None:
            assert len(sections) == 1, \
                   "The wiki document must have just one top-level section!"
            s = sections[0]
            self._title_ = s.title()
            sections = s.content()
        return SectionContainer(self, sections, toc_depth=0) 
    
    def _title(self):
        return self._title_


class WikiNode(_WikiNode):
    """A single-purpose class serving as a wiki parser and formatter.
    
    You simply instantiate this node (giving a wiki-formatted text as a
    constructor argument) and the text is parsed and a hierarchy of 'Content'
    elements representing the document is built.  Then you can access the
    content structure or simply export the content into HTML or use an
    'Exporter' class to dump a whole page.

    """

    def __init__(self, text, **kwargs):
        """Initialize the instance.
        
        Arguments:
        
          text -- the wiki-formatted text as a unicode string.
          title -- the page title as a unicode string.  If None, the title of
            the first top-level section within the content will be used.

          The other arguments are inherited from the parent class.
          
        """
        self._text = text
        super(WikiNode, self).__init__(None, '.', **kwargs)
    
    def _source_text(self):
        return self._text
    
    def _title(self):
        return self._title_ or super(WikiNode, self)._title()


class DocNode(_WikiNode):

    def __init__(self, parent, dir, file, **kwargs):
        """Initialize the instance.

        Arguments:
        
          file -- the name of the wiki-formatted input file.

          The other arguments are inherited from the parent class.
          
        """
        file, ext = os.path.splitext(file)
        self._file = file
        self._ext = ext[1:]
        super(DocNode, self).__init__(parent, dir, **kwargs)

    def _id(self):
        return self._file
        
        
    def _source_text(self):
        return self._read_file(self._file, ext=self._ext)
               
        
class DocMaker(RootNode):
    """The root node for a file based wiki documentation.

    This class is also used to build the LCG documentation from wiki files.
    All files with the '.wiki' suffix in the source directory are read and
    represented as separate nodes.  The root node with a table of contents is
    generated.

    The order of the nodes can be given by the file 'index.txt', which contains
    the filenames of the source files each on one line.  Otherwise the
    alphabetical order is used.

    Any other hierarchy can be implemented by overriding the
    '_create_children()' method.

    """

    def __init__(self, dir, title=None, **kwargs):
        """Initialize the instance.

        Arguments:
        
          title -- the page title as a unicode string.  If the title is not
            given as constructor argument, the file 'title.txt' must exist in
            the source directory.  The contents of this file is then used as
            the document title.

          The other arguments are inherited from the parent class.
          
        """
        self._title_ = title
        super(DocMaker, self).__init__(dir, **kwargs)

    def _title(self):
        return self._title_ or self._read_file('title')
    
    def _create_content(self):
        return [TableOfContents(self, item=self, title=_("Table of Contents:"),
                                depth=2)]
                         
    def _create_children(self):
        d = self.src_dir()
        return [self._create_child(DocNode, '.', f) for f in list_dir(d)
                if os.path.isfile(os.path.join(d, f)) and f.endswith('.wiki')]

    
