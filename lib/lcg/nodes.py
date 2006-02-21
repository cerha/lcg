# -*- coding: iso8859-2 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006 Brailcom, o.p.s.
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
import unicodedata

from lcg import *

class ContentNode(object):
    """Representation of one output document within the package.

    This class represents a generic node of the output document structure.
    Each node has its 'Content', may have several child nodes and manages the
    dependencies on externam resources ('Resource' instances).

    By instantiating a node, all the resources are read and the content is
    built and ready for export.
    
    """

    _TITLE = _("Node")
    
    """The title is a string used to reference to the node from within the
    generated content (eg. in Tables Of Contents etc.).  The derived
    classes should define some more meaningful titles, such as 'Lesson',
    'Module' etc."""

    _ABBREV_TITLE = None
    
    def __init__(self, parent, id, subdir=None, hidden=False, language='en',
                 input_encoding='ascii'):
        """Initialize the instance.

        Arguments:

          parent -- parent node; the 'ContentNode' instance directly preceding
            this node in the content hierarchy.  Can be None for the top node.
          id -- a textual identifier of this node.
          subdir -- a directory name relative to parent's source directory.  All
            input files are expected in this directory.
          language -- content language as a lowercase ISO 639-1 Alpha-2
            language code.
          input_encoding -- The content read from source files is expected in
            the specified encoding (ASCII by default).  The output encoding is
            set by the used exporter class.

        """
        assert parent is None or isinstance(parent, ContentNode)
        assert isinstance(id, types.StringType)
        assert subdir is None or isinstance(subdir, types.StringType)
        assert isinstance(hidden, types.BooleanType), hidden
        assert isinstance(language, types.StringType) and \
               len(language) == 2
        assert isinstance(input_encoding, types.StringType)
        codecs.lookup(input_encoding)
        self._parent = parent
        self._id = id
        self._subdir = subdir
        self._hidden = hidden
        self._language = language
        self._input_encoding = input_encoding
        self._resources = {}
        self._counters = {}
        self._registered_children = []
        self._wiki_parser = wiki.Parser(self)
        self._wiki_formatter = wiki.Formatter(self)
        
        content = self._create_content()
        if isinstance(content, Content):
            self._content = content
        else:
            assert isinstance(content, (types.TupleType, types.ListType))
            self._content = SectionContainer(self, content)
        self._children = self._create_children()
        if __debug__:
            for child in self._children:
                assert child._parent == self
                assert child in self._registered_children
        if parent is not None:
            parent._register_child(self)
        else:
            if __debug__:
                seen = {}
                for n in self.linear():
                    nid = n.id()
                    assert not seen.has_key(nid), \
                           "Duplicate node id: %s, %s" % (n, seen[nid])
                    seen[nid] = n
        
    def _register_child(self, child):
        assert isinstance(child, ContentNode)
        assert child not in self._registered_children
        self._registered_children.append(child)
        
    def __str__(self):
        return "<%s id='%s' title='%s' subdir='%s'>" % \
               (self.__class__.__name__, self.id(),
                self.title().encode('ascii', 'replace'), self.subdir())

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
    
    def _title(self):
        """Return the title of this node as a string."""
        return self._TITLE

    def _abbrev_title(self):
        """Return the abbreviated title of this node as a string."""
        return self._ABBREV_TITLE
    
    def _node_path(self, relative_to=None):
        """Return the path from root to this node as a sequence of nodes.

        When the optional argument `relative_to' is specified, the returned
        path is relative to this node, when it exists in the path.
        
        """
        if self._parent is None or self._parent is relative_to:
            return (self,)
        else:
            return self._parent._node_path(relative_to=relative_to) + (self,)

    # File-related private methods
        
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
        if lang is not None and not os.path.exists(filename):
            filename2 = self._input_file(name, ext=ext, dir=dir)
            log("File '%s' not found. Trying '%s' instead.", filename,filename2)
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

    # Public methods

    def id(self):
        """Return a unique id of this node as a string."""
        return self._id
        
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

    def hidden(self):
        return self._hidden
        
    def parent(self):
        """Return the parent node of this node."""
        return self._parent
    
    def root(self):
        """Return the top-most node of the hierarchy."""
        if self._parent is None:
            return self
        else:
            return self._parent.root()
        
    def children(self):
        """Return the list of all subordinate nodes as a tuple."""
        return tuple(self._children)

    def content(self):
        return self._content
    
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
    
    def linear(self):
        """Return the linearized subtree of this node as a list."""
        return [self] + reduce(lambda l, n: l + n.linear(), self.children(), [])

    def next(self):
        """Return the node following this node in the linearized structure."""
        linear = self.root().linear()
        i = linear.index(self)
        if i < len(linear)-1:
            return linear[i+1]
        else:
            return None
    
    def prev(self):
        """Return the node preceding this node in the linearized structure."""
        linear = self.root().linear()
        i = linear.index(self)
        if i > 0:
            return linear[i-1]
        else:
            return None

    def language(self):
        """Return the content language as an ISO 639-1 Alpha-2 code."""
        return self._language

    def input_encoding(self):
        """Return the name of encoding expected in source files.

        The name is a string accepted by 'UnicodeType.encode()'.

        """
        return self._input_encoding
    
    def meta(self):
        """Return the meta data as a dictionary.

        This method returns just an empty dictionary, but it is supposed to be
        overriden in the implementing class.  Only root node's meta information
        is taken into account, however.

        """
        return {}
    
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
        elif result is not None:
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

    # File-related methods
    
    def output_file(self):
        """Return full pathname of the output file relative to export dir."""
        return self.id() + '.html'

    def url(self):
        return self.output_file()
    
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
            return os.path.normpath(os.path.join(self.root().src_dir(),
                                                 self.subdir()))
    # Wiki-related methods

    def format_wiki_text(self, text):
        """Format text with wiki markup and return HTML."""
        if text:
            return self._wiki_formatter.format(text)
        else:
            return ''
    
    def parse_wiki_text(self, text, macro=False, globals=None):
        """Parse the text and return a sequence of content elements."""
        if macro:
            def mygettext(x):
                return _(re.sub('\s*\n', ' ', x))
            mp = wiki.MacroParser(substitution_provider=mygettext)
            if globals:
                mp.add_globals(**globals)
            text = mp.parse(text)
        return self._wiki_parser.parse(text)
    
    def parse_wiki_file(self, name, ext='txt', lang=None,
                        macro=False, globals=None):
        """Parse the file and return a sequence of content elements."""
        return self.parse_wiki_text(self._read_file(name, ext=ext, lang=lang),
                                    macro=macro, globals=globals)
    
        

    
class RootNode(ContentNode):
    """Root node of the hierarchy.

    The only difference is that 'RootNone' doesn't take the 'parent' constructor
    argument.

    """
    
    def __init__(self, dir, id='index', **kwargs):
        """Initialize the instance.

        The arguments are inherited from the parent class, except for 'parent'
        which is not needed for the root node.
          
        """
        super(RootNode, self).__init__(None, id, dir, **kwargs)

    
class _WikiNode(ContentNode):
    """Node read from a LCG Structured Text (wiki) document.

    The node's content is read from a Structured Text document.  The title of
    the top-level section within the document will be used as node's title when
    the `title' constructor argument is not passed.  Thus it is required, that
    the document contains just one top-level section, when no title is passed.
    If not, an exception will be raised.
    
    """
    def __init__(self, parent, id, title=None, **kwargs):
        """Initialize the instance.


        The other arguments are inherited from the parent class.
          
        """
        self._document_title = title
        super(_WikiNode, self).__init__(parent, id, **kwargs)

    def _source_text(self):
        return ""
        
    def _create_content(self):
        sections = self.parse_wiki_text(self._source_text())
        if self._document_title is None:
            if len(sections) != 1 or not isinstance(sections[0], Section):
                raise Exception("The document has no top-level section:",
                                self._id)
            s = sections[0]
            self._document_title = s.title()
            sections = s.content()
        return SectionContainer(self, sections, toc_depth=0) 
    
    def _title(self):
        return self._document_title


class WikiNode(_WikiNode):
    """A single-purpose class serving as a wiki parser and formatter.
    
    You simply instantiate this node (giving a string of Structured Text as a
    constructor argument) and the text is parsed and a hierarchy of 'Content'
    elements representing the document is built.  Then you can access the
    content structure or simply export the content into HTML or use an
    'Exporter' class to dump a whole page.

    """

    def __init__(self, id, text, **kwargs):
        """Initialize the instance.
        
        Arguments:
        
          text -- the wiki-formatted text as a unicode string.

          The other arguments are inherited from the parent class.
          
        """
        self._text = text
        super(WikiNode, self).__init__(None, id, **kwargs)
    
    def _source_text(self):
        return self._text


class DocNode(_WikiNode):
    """Node of a Structured Text read from a source file."""
    
    def __init__(self, parent, id, ext='txt', **kwargs):
        """Initialize the instance.

        Arguments:
        
          ext -- the extension of the input file ('txt' by default).  The
            complete filename is the node's id, an optional language extension
            and this extension.

          The other arguments are inherited from the parent class.
          
        """
        self._ext = ext
        super(DocNode, self).__init__(parent, id, **kwargs)
        
    def _source_text(self):
        return self._read_file(self._id, lang=self._language, ext=self._ext)

    
class DocChapter(DocNode):
    """A Structured Text node with children read from the source directory.
    
    Child nodes are created automatically using the files and subdirectories
    found in the source directory.  See the documentation of 'DocRoot' for more
    information.

    """

    def _list_dir(self, dir, indexfile='_index.txt'):
        def listdir(dir, exclude=()):
            items = []
            for item in os.listdir(dir):
                if os.path.isfile(os.path.join(dir, item)):
                    if item.endswith('~'):
                        continue
                    item = os.path.splitext(os.path.splitext(item)[0])[0]
                if item and item not in items and item not in exclude \
                       and item != 'CVS' \
                       and not item.startswith('_') \
                       and not item.startswith('.'):
                    items.append(item)
            items.sort()
            return items
        try:
            index = open(os.path.join(dir, indexfile))
        except IOError:
            return [(item, False) for item in listdir(dir)]
        else:
            items = [item for item in [line.strip()
                                       for line in index.readlines()]
                     if item != '' and not item.startswith('#')]
            hidden = listdir(dir, exclude=items)
            return [(x, False) for x in items] + [(x, True) for x in hidden]

    
    def _create_children(self):
        children = []
        for name, hidden in self._list_dir(self.src_dir()):
            if name != self.id():
                kwargs = dict(hidden=hidden)
                if os.path.isfile(self._input_file(name, ext='py')):
                    import imp
                    file, path, descr = imp.find_module(name, [self.src_dir()])
                    m = imp.load_module(name, file, path, descr)
                    cls = m.IndexNode
                elif os.path.isdir(os.path.join(self.src_dir(), name)):
                    cls = DocChapter
                    kwargs['subdir'] = name
                else:
                    cls = DocNode
                children.append(self._create_child(cls, name, **kwargs))
        return children

    
class DocRoot(DocChapter):
    """The root node for a documentation based on LCG Structured Text.

    This class may be used to build a document structure from textual files
    organized in directories.  All files in the source directory with given
    suffix ('txt' by default) are read and represented as separate nodes.
    Further more all directories are read recursively.  Inside each directory,
    a file with the same filename as the name of the directory (plus the
    suffix) must exist and this file represents the directory.  All other files
    (and directories) are child nodes of this node.

    The nodes are ordered alphabetically by default.  Names beginning with an a
    dot, an underscore, ending with a tilde and 'CVS' directories are ignored.

    The order can be also defined explicitly using an index file (named
    '_index.txt' by default), which contains child node identifiers one per
    line.  Valid source files and directories (as described above) not included
    in the index file will be still used, but they will not appear in the table
    of contents.

    Files within the whole directory structure must have unique names, since
    they are used node identifiers.  This also means that it is possible to
    refer to any node using it's name, without caring which subdirectory it is
    located in.

    This class is also used to build the LCG documentation itself.

    """
    
    def __init__(self, dir, id='index', **kwargs):
        super(DocRoot, self).__init__(None, id, subdir=dir, **kwargs)
