# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007 Brailcom, o.p.s.
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

"""Tools for building the 'ContentNode' hierarchy.

This module provides classes which implement reading LCG document hierarchies from different
sources, such as files and directories.

"""

import os
import codecs
import unicodedata

from lcg import *


class Reader(object):
    _INHERIT = ('language', 'secondary_language', 'language_variants')
    _DEFAULTS = {}
    
    def __init__(self, id, parent=None, **kwargs):
        """

        """
        super(Reader, self).__init__()
        self._id = id
        self._parent = parent
        kwargs.update(self._DEFAULTS)
        if parent is not None:
            pkwargs = parent._kwargs
            for arg in self._INHERIT:
                if not kwargs.has_key(arg) and pkwargs.has_key(arg):
                    kwargs[arg] = pkwargs[arg]
            root = parent
            while root.parent() is not None:
                root = root.parent()
        else:
            root = self
        self._root = root
        self._language = kwargs.get('language')
        kwargs['id'] = id
        kwargs['resource_provider'] = self._resource_provider()
        self._kwargs = kwargs
        
    def _create_content(self):
        return None
        
    def _create_children(self):
        return ()

    def _resource_provider(self):
        if self is self._root:
            return SharedResourceProvider()
        else:
            return self._root.resource_provider()

    def id(self):
        return self._id
    
    def parent(self):
        return self._parent
    
    def language(self):
        return self._language

    def resource_provider(self):
        return self._kwargs['resource_provider']
    
    def build(self):
        content = self._create_content()
        children = [child.build() for child in self._create_children()]
        return ContentNode(content=content, children=children, **self._kwargs)
    
        
class FileReader(Reader):
    
    def __init__(self, id='index', dir='.', encoding=None, **kwargs):
        assert isinstance(dir, str)
        assert encoding is None or isinstance(encoding, str) \
               and codecs.lookup(encoding)
        self._dir = os.path.normpath(dir)
        super(FileReader, self).__init__(id, **kwargs)
        if not encoding and self._parent and isinstance(self._parent, FileReader):
            encoding = self._parent.encoding()
        self._encoding = encoding or 'ascii'

    def _resource_provider(self):
        if self is self._root:
            p = self._shared_resource_provider = SharedResourceProvider(self._dir)
        elif isinstance(self._root, FileReader):
            p = self._root._shared_resource_provider
        else:
            p = self._root.resource_provider()
        return FileResourceProvider(self._dir, self._root.dir(), shared_resource_provider=p)

    def _input_file(self, name, ext='txt', lang=None, dir=None):
        """Return the full path to the source file."""
        if lang:
            ext = lang +'.'+ ext
        if dir is None:
            dir = self._dir
        return os.path.join(dir, name + '.' + ext)
        
    def _read_file(self, name, ext='txt', comment=None, dir=None, lang=None):
        """Return all the text read from the source file."""
        filename = self._input_file(name, ext=ext, lang=lang, dir=dir)
        if lang is not None and not os.path.exists(filename):
            filename2 = self._input_file(name, ext=ext, dir=dir)
            log("File '%s' not found. Trying '%s' instead.", filename,filename2)
            filename = filename2
        fh = codecs.open(filename, encoding=self._encoding)
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
        
    def encoding(self):
        """Return the name of encoding expected in source files.

        The name is a string accepted by 'UnicodeType.encode()'.

        """
        return self._encoding
        
    def dir(self):
        """Return the name of the source directory."""
        return self._dir
        

class StructuredTextReader(FileReader):
    """Reader class for nodes read from an LCG Structured Text document.

    Created document content by parsing the source text and building a hierarchy of 'Content'
    elements representing it.

    """

    def __init__(self, *args, **kwargs):
        self._parser = Parser()
        super(StructuredTextReader, self).__init__(*args, **kwargs)

    def _source_text(self):
        return None
        
    def _parse_source_text(self, text, macro=False, globals=None, subst=None):
        """Parse the text and return a sequence of content elements."""
        if macro:
            mp = MacroParser(substitution_provider=subst)
            if globals:
                mp.add_globals(**globals)
            text = mp.parse(text)
        return self._parser.parse(text)
    
    def _create_content(self):
        sections = self._parse_source_text(self._source_text())
        if self._kwargs.get('title') is None:
            if len(sections) != 1 or not isinstance(sections[0], Section):
                raise Exception("The document has no top-level section:", self._id)
            s = sections[0]
            self._kwargs['title'] = s.title()
            sections = s.content()
        return SectionContainer(sections, toc_depth=0)
    
    
class DocFileReader(StructuredTextReader):
    """Node of a Structured Text read from a source file."""

    def __init__(self, id, ext='txt', **kwargs):
        """Initialize the instance.

        Arguments:
        
          ext -- the extension of the input file ('txt' by default).  The
            complete filename is the node's id, an optional language extension
            and this extension.

          The other arguments are inherited from the parent class.
          
        """
        self._ext = ext
        super(DocFileReader, self).__init__(id, **kwargs)
        if not self._kwargs.get('language_variants'):
            variants = [os.path.splitext(os.path.splitext(f)[0])[1][1:]
                        for f in glob.glob(self._input_file(self._id, lang='*', ext=self._ext))]
            self._kwargs['language_variants'] = variants
    
    def _source_text(self):
        return self._read_file(self._id, lang=self._language, ext=self._ext)
        
    
class DocDirReader(DocFileReader):
    """Node of a Structured Text read from a source file.

    This reader automatically reads child nodes from the files and subdirectories found in the
    source directory.  See the documentation of 'DocRoot' for more information.

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
        for name, hidden in self._list_dir(self._dir):
            if name not in (self._id, 'resources'):
                dir = self._dir
                if os.path.isfile(self._input_file(name, ext='py')):
                    import imp
                    file, path, descr = imp.find_module(name, [dir])
                    m = imp.load_module(name, file, path, descr)
                    if hasattr(m, 'IndexNode'):
                        # Just for backwards compatibility
                        reader = m.IndexNode
                    else:
                        reader = m.Reader
                else:
                    subdir = os.path.join(dir, name)
                    if os.path.isdir(subdir):
                        dir = subdir
                        reader = DocDirReader
                    else:
                        reader = DocFileReader
                kwargs = dict(id=name, parent=self, hidden=hidden)
                if issubclass(reader, FileReader):
                    kwargs = dict(dir=dir, encoding=self._encoding, **kwargs)
                children.append(reader(**kwargs))
        return children

    
