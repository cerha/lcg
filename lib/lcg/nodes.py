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

"""

import os
import re
import sys
import codecs
import unicodedata

from lcg import *

class ContentNode(object):
    """Representation of one output document within the package.

    This class represents a generic node of the document structure.  Each node
    has its 'Content' and may have several child nodes.

    By instantiating a node, the content is ready for export (see 'Content' for
    more details).
    
    """

    _INHERITED_ARGS = ('language', 'secondary_language', 'language_variants')

    def __init__(self, parent, id, title=None, brief_title=None, descr=None,
                 content=None, language=None, secondary_language=None,
                 language_variants=(), hidden=False):
        
        """Initialize the instance.

        Arguments:

          parent -- parent node; the 'ContentNode' instance directly preceding
            this node in the node hierarchy.  Can be None for the top node.
            
          id -- a unique textual identifier of this node (as a string).

          title -- the title of this node (as a unicode string).

          brief_title -- the brief (shorter) form of title of this node (as a
            unicode string).  If given, this title will be used to refer to
            this node from places, where brevity matters.  If None, the 'title'
            will be used instead.

          descr -- a short textual description of this node (as a uni code
            string).  Additional information, which may determine the content
            of the node in addition to the title.
          
          hidden -- a boolean flag indicating, that this node should not appear
            in the Table of Contents.  Such a node will usually be referenced
            explicitely from somewhere else.

          content -- a content element hierarchy.  This is the actual content
            of this node.  The value can be a `Content' instance or a sequence
            of `Content' instances.
            
          language -- content language as a lowercase ISO 639-1 Alpha-2
            language code.
            
          secondary_language -- secondary content language (used in citations)
            as a lowercase ISO 639-1 Alpha-2 language code.
            
          language_variants -- a sequence of all available language variants of
            this node.  The sequence contains language codes as strings.  The
            current language variant is added automatically to the list if it
            is not already there.
            
        """
        assert parent is None or isinstance(parent, ContentNode), parent
        assert isinstance(id, str), repr(id)
        assert isinstance(hidden, bool), hidden
        assert language is None or isinstance(language, str) and \
               len(language) == 2, repr(language)
        assert secondary_language is None or \
               isinstance(secondary_language, str) and \
               len(secondary_language) == 2, repr(secondary_language)
        assert isinstance(language_variants, (list, tuple))
        self._parent = parent
        self._id = id
        self._title = title or brief_title or id
        self._brief_title = brief_title or title
        self._descr = descr
        self._hidden = hidden
        self._language = language
        self._secondary_language = secondary_language
        current_language = self.current_language_variant()
        if current_language and current_language not in language_variants:
            language_variants += (current_language,)
        self._language_variants = tuple(language_variants)
        self._registered_children = []
        if not isinstance(content, Content):
            assert isinstance(content, (types.TupleType, types.ListType))
            content = SectionContainer(content)
        content.set_parent(self)
        self._content = content
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
        return "<%s id='%s'>" % (self.__class__.__name__, self.id())

    def _create_children(self):
        """Create any descendant nodes and return them in a sequence.

        This method should be overriden in derived classes which represent an
        inner node of the content tree.

        """
        return ()

    def _create_child(self, cls, *args, **kwargs):
        """Helper method to be used within '_create_children()'."""
        for k in self._INHERITED_ARGS:
            if not kwargs.has_key(k):
                kwargs[k] = getattr(self, '_'+k)
        return cls(self, *args, **kwargs)
    
    def _node_path(self, relative_to=None):
        """Return the path from root to this node as a sequence of nodes.

        When the optional argument `relative_to' is specified, the returned
        path is relative to this node, when it exists in the path.
        
        """
        if self._parent is None or self._parent is relative_to:
            return (self,)
        else:
            return self._parent._node_path(relative_to=relative_to) + (self,)

    # Public methods

    def parent(self):
        """Return the parent node of this node."""
        return self._parent
    
    def id(self):
        """Return a unique id of this node as a string."""
        return self._id
        
    def title(self, brief=False):
        """Return the title of this node as a string.

        If a true value is passed to the optional argument 'brief', a shorter
        version of the title will be returned, when available.
        
        """
        return brief and self._brief_title or self._title

    def descr(self):
        """Return a short description of this node as a string or None."""
        return self._descr

    def hidden(self):
        """Return True if this is a hidden node (should not appear in TOC)."""
        return self._hidden
        
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
    
    def root(self):
        """Return the top-most node of the hierarchy."""
        if self._parent is None:
            return self
        else:
            return self._parent.root()
        
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

    def secondary_language(self):
        """Return the secondary language as an ISO 639-1 Alpha-2 code."""
        return self._secondary_language

    def language_variants(self):
        """Return the tuple of available language variants of this node.

        The returned tuple consists of language codes including the language of
        the current node.
        
        """
        return self._language_variants
        
    def current_language_variant(self):
        # This is in fact only here to allow a strange language setup in
        # eurochance courses.  In other cases, 'self.language()' should
        # directly determine the current language variant.
        return self.language()

    def meta(self):
        """Return the meta data as a tuple of pairs (name, value)."""
        return ()
    
    def resources(self, cls=None):
        """Return the list of all resources this node depends on.

        This is just a convenience wrapper for the `resources()' function.  The
        arguments are the same.
        
        """
        return resources(self, cls=cls)

    def resource(self, cls, file, **kwargs):
        """Get the resource instance.
        
        This is just a convenience wrapper for the `resource()' function.  The
        arguments are the same.

        """
        return resource(self, cls, file, **kwargs)
        
    def index(self, node):
        """Return the child node's index number within this node's children.

        The numbering begins at zero and corresponds to the natural order of
        child nodes.
        
        """
        return self._children.index(node)

  
class WikiNodeMixin(object):
    """Mix-in class for nodes read from a wiki text document."""

    def __init__(self):
        self._parser = Parser()

    def parse_wiki_text(self, text, macro=False, globals=None, subst=None):
        """Parse the text and return a sequence of content elements.

        This method is deprecated and should not be used.

        """
        if macro:
            mp = MacroParser(substitution_provider=subst)
            if globals:
                mp.add_globals(**globals)
            text = mp.parse(text)
        return self._parser.parse(text)
        

class FileNodeMixin(WikiNodeMixin):
    """Mix-in class for nodes read from input files."""

    def __init__(self, parent, subdir=None, input_encoding='ascii'):
        """Initialize the instance.
        
          subdir -- a directory name relative to parent's source directory.
            All input files are expected in this directory.

          input_encoding -- The content read from source files is expected in
            the specified encoding (ASCII by default).  The output encoding is
            set by the used exporter class.

        """
        assert subdir is None or isinstance(subdir, str)
        assert isinstance(input_encoding, str)
        self._parent = parent
        codecs.lookup(input_encoding)
        self._input_encoding = input_encoding
        self._subdir = subdir
        super(FileNodeMixin, self).__init__()

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
        
    def input_encoding(self):
        """Return the name of encoding expected in source files.

        The name is a string accepted by 'UnicodeType.encode()'.

        """
        return self._input_encoding
        
    def parse_wiki_file(self, name, ext='txt', lang=None, macro=False,
                        globals=None, subst=None):
        """Parse the file and return a sequence of content elements.

        This method is deprecated and should not be used.

        """
        return self.parse_wiki_text(self._read_file(name, ext=ext, lang=lang),
                                    macro=macro, globals=globals, subst=subst)
        
    def subdir(self):
        """Return this node's subdirectory name relative to the root node.

        This method is deprecated and should not be used.
        
        """
        if self._parent is None:
            return ''
        elif self._subdir is None:
            return self._parent.subdir()
        else:
            return os.path.join(self._parent.subdir(), self._subdir)
        
    def src_dir(self):
        """This method is deprecated and should not be used."""
        try:
            dir = self._src_dir
        except AttributeError:
            if self._parent is None:
                dir = self._subdir
            else:
                dir = os.path.normpath(os.path.join(self.root().src_dir(),
                                                    self.subdir()))
            self._src_dir = dir
        return dir


class WikiNode(ContentNode, WikiNodeMixin):
    """Node read from a LCG Structured Text (wiki) document.

    The node's content is read from a Structured Text document.  The title of
    the top-level section within the document will be used as node's title when
    the `title' constructor argument is not passed.  Thus it is required, that
    the document contains just one top-level section, when no title is passed.
    If not, an exception will be raised.
    
    You simply instantiate this node (passing a string of Structured Text as a
    constructor argument) and the text is parsed and a hierarchy of 'Content'
    elements representing the document is built.  Then you can access the
    content structure or simply export the content into HTML or use an
    'Exporter' class to dump a whole page.
    
    """
    _INHERITED_ARGS = ('language', 'secondary_language', 'input_encoding')
    
    
    def __init__(self, parent, id, text, title=None, **kwargs):
        """Initialize the instance.
        
        Arguments:
        
          text -- the wiki-formatted text as a unicode string.

          title -- 

          The other arguments are inherited from the parent class.
          
        """
        WikiNodeMixin.__init__(self)
        sections = self.parse_wiki_text(text)
        if title is None:
            if len(sections) != 1 or not isinstance(sections[0], Section):
                raise Exception("The document has no top-level section:", id)
            s = sections[0]
            title = s.title()
            sections = s.content()
        content = SectionContainer(sections, toc_depth=0)
        super(WikiNode, self).__init__(parent, id, title=title,
                                       content=content, **kwargs)
    
class DocNode(WikiNode, FileNodeMixin):
    """Node of a Structured Text read from a source file."""
    
    def __init__(self, parent, id, subdir=None, ext='txt',
                 input_encoding='ascii', language=None, **kwargs):
        """Initialize the instance.

        Arguments:
        
          ext -- the extension of the input file ('txt' by default).  The
            complete filename is the node's id, an optional language extension
            and this extension.

          The other arguments are inherited from the parent class.
          
        """
        FileNodeMixin.__init__(self, parent, subdir, input_encoding=input_encoding)
        self._ext = ext
        variants = [os.path.splitext(os.path.splitext(f)[0])[1][1:]
                    for f in glob.glob(self._input_file(id, lang='*'))]
        text = self._read_file(id, lang=language, ext=ext)
        super(DocNode, self).__init__(parent, id, text, language=language,
                                      language_variants=variants,
                                      **kwargs)

        
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
            if name not in (self.id(), 'resources'):
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


        
