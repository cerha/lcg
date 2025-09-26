# -*- coding: utf-8 -*-

# Copyright (C) 2004-2015 OUI Technology Ltd.
# Copyright (C) 2019-2025 Tomáš Cerha <t.cerha@gmail.com>
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

"""Tools for building the LCG 'ContentNode' hierarchy."""

from __future__ import unicode_literals
import codecs
import glob
import os
import re
import sys
import unicodedata

import lcg

unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


class Reader(object):
    """LCG content hierarchy reader.

    Readers provide a generic interface for building the LCG content hierarchy.  Derived classes
    may implement reading the data from different sources, such as files and directories, databases
    or python source files.

    Reader instances are created hierarchically, matching the content node hierarchy, but the major
    difference is that the nodes are constructed from bottom up (the leave nodes must be
    instantiated first), while readers from the top (reader of the root node first).

    The 'build()' method of the reader invokes the recursive process of building the complete
    hierarchy and the corresponding 'ContentNode' instances.

    Except for the arguments 'id' and 'hidden', which are passed to 'Reader' constructor, all the
    remaining 'ContentNode' constructor arguments are read by the reader from the data source.
    Just override the corresponding method, such as '_title()' for the 'title' argument, etc.

    """

    def __init__(self, id, parent=None, hidden=False, resource_provider=None):
        """Initialize the instance.

        Arguments:

          id -- node identifier
          parent -- parent 'Reader' instance in the hierarchy
          hidden -- boolean flag passed to the created 'ContentNode' constructor
          resource_provider -- 'ResourceProvider' instance or None.  An instance may only be passed
            to the root reader, child readers will automatically use the root's resource provider.

        """
        super(Reader, self).__init__()
        self._id = id
        self._parent = parent
        self._hidden = hidden
        if parent is None:
            root = self
            if resource_provider is None:
                resource_provider = self._resource_provider()
        else:
            root = parent
            while root.parent() is not None:
                root = root.parent()
            assert resource_provider is None, (self._id, resource_provider)
            resource_provider = root._resource_provider_
        self._root = root
        self._resource_provider_ = resource_provider

    def _title(self):
        return None

    def _brief_title(self):
        return None

    def _descr(self):
        return None

    def _children(self):
        return ()

    def _variants(self):
        return ()

    def _content(self, lang):
        return dict()

    def _resource_dirs(self):
        return ()

    def _resource_provider(self):
        return lcg.ResourceProvider(dirs=self._resource_dirs())

    def _globals(self):
        return {}

    def parent(self):
        return self._parent

    def resource(self, filename, **kwargs):
        return self._resource_provider_.resource(filename, node=self._id, **kwargs)

    def build(self):
        """Build hierarchy of 'ContentNode' instances and return the root node."""
        try:
            variants = self._variants()
            if variants:
                # There is one or more known source language (files have the lang extension).
                kwargs = dict(variants=[lcg.Variant(lang, **self._content(lang))
                                        for lang in variants])
            else:
                # There is one unknown source language.
                kwargs = self._content(None)
            return lcg.ContentNode(id=self._id,
                                   title=self._title(),
                                   brief_title=self._brief_title(),
                                   descr=self._descr(),
                                   children=[child.build() for child in self._children()],
                                   resource_provider=self._resource_provider_,
                                   globals=self._globals(),
                                   hidden=self._hidden,
                                   **kwargs)

        except Exception as e:
            if hasattr(self, '_source_filename'):
                # TODO: This is a quick hack.  The attribute `_source_filename' is prefilled in
                # 'FileReader._read_file', so it would be at least more appropriate to move this
                # hack into the 'FileReader' class.  Even then, there is no guarantee, that the
                # exception was actually raised during processing this file.
                e = lcg.add_processing_info(e, 'File', self._source_filename)
            raise


class FileReader(Reader):

    # Byte Order Mark (see http://en.wikipedia.org/wiki/Byte-order_mark).
    _BOM = unicodedata.lookup('ZERO WIDTH NO-BREAK SPACE').encode('utf-8')

    _ENCODING_HEADER_MATCHER = re.compile(br'^#\s*-\*-.*coding:\s*([^\s;]+).*-\*-\s*$')
    _EMACS_CODING_EXTENSION_MATCHER = re.compile(br'(^mule-|-(dos|unix|mac)$)')

    def __init__(self, id='index', dir='.', encoding=None, **kwargs):
        assert isinstance(dir, basestring), dir
        assert encoding is None or isinstance(encoding, basestring) and codecs.lookup(encoding), \
            encoding
        self._dir = os.path.normpath(dir)
        super(FileReader, self).__init__(id, **kwargs)
        if not encoding and self._parent and isinstance(self._parent, FileReader):
            encoding = self._parent.encoding()
        self._encoding = encoding or 'ascii'

    def _resource_dirs(self):
        return (self._dir,)

    def _input_file(self, name, ext='txt', lang=None, dir=None):
        """Return the full path to the source file."""
        filename = '.'.join([part for part in (name, lang, ext) if part])
        if dir is None:
            dir = self._dir
        return os.path.join(dir, filename)

    def _read_file(self, name, ext='txt', comment=None, dir=None, lang=None, fallback_lang=None):
        """Return the text read from the source file."""
        filename = self._input_file(name, ext=ext, lang=lang, dir=dir)
        if lang is not None and not os.path.exists(filename):
            filename2 = self._input_file(name, ext=ext, lang=fallback_lang, dir=dir)
            if os.path.exists(filename2):
                lcg.log("File '%s' not found. Using '%s' instead.", filename, filename2)
                filename = filename2
        self._source_filename = filename
        fh = open(filename, 'rb')
        try:
            lines = fh.readlines()
        finally:
            fh.close()
        encoding = self._encoding
        if lines:
            if lines[0].startswith(self._BOM):
                # Strip the Unicode marker (BOM)
                lines[0] = lines[0][len(self._BOM):]
            match = self._ENCODING_HEADER_MATCHER.match(lines[0])
            if match:
                enc = self._EMACS_CODING_EXTENSION_MATCHER.sub('', match.group(1))
                if sys.version_info[0] > 2:
                    enc = str(enc, 'ascii')
                try:
                    codecs.lookup(str(enc))
                except LookupError:
                    lcg.log("File %s: Unknown encoding '%s' in file header, using default '%s'.",
                            filename, enc, encoding)
                else:
                    encoding = enc
                del lines[0]
            if comment is not None:
                # This is a hack (it breaks line numbering).
                comment_matcher = re.compile(comment)
                lines = [l for l in lines if not comment_matcher.match(l)]
        content = b''.join(lines)
        try:
            return unistr(content, encoding=encoding)
        except UnicodeDecodeError as e:
            raise Exception("File %s: %s" % (filename, e))

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
        self._parser = lcg.Parser()
        self._titles = {}
        super(StructuredTextReader, self).__init__(*args, **kwargs)

    def _source_text(self, lang):
        return None

    def _parse_text(self, text):
        parser = self._parser
        parameters = {}
        result = parser.parse(text, parameters)
        return result, parameters

    def _document(self, text):
        sections, parameters = self._parse_text(text)
        if len(sections) != 1 or not isinstance(sections[0], lcg.Section):
            raise Exception("The document has no top-level section:", (self._id, sections,))
        s = sections[0]
        title = s.title()
        sections = s.content()
        return title, lcg.Container(sections), parameters

    def _title(self):
        # This method is called after _content(), is called for each
        # language, so the dictionary of titles is already built.
        if len(self._titles.keys()) == 1:
            title = list(self._titles.values())[0]
        else:
            title = lcg.SelfTranslatableText(self._id, translations=self._titles)
        return title

    def _content(self, lang):
        title, content, parameters = self._document(self._source_text(lang))
        self._titles[lang] = title
        return dict(content=content, **parameters)


class DocFileReader(StructuredTextReader):
    """Node of a Structured Text read from a source file."""

    def __init__(self, id, ext='txt', **kwargs):
        """Initialize the instance.

        Arguments:

          ext -- the extension of the input file ('txt' by default).  The complete filename is the
            node's id, an optional language extension and this extension.

          The other arguments are inherited from the parent class.

        """
        self._ext = ext
        self._cached_variants = None
        super(DocFileReader, self).__init__(id, **kwargs)

    def _variants(self):
        # Cache the result to avoid repetitive file system access...
        if self._cached_variants is not None:
            variants = self._cached_variants
        else:
            if self._parent is not None:
                variants = self._parent._variants()
            else:
                matcher = self._input_file(self._id, lang='*', ext=self._ext)
                variants = tuple([os.path.splitext(os.path.splitext(f)[0])[1][1:]
                                  for f in glob.glob(matcher)])
            self._cached_variants = variants
        return variants

    def _source_text(self, lang):
        return self._read_file(self._id, lang=lang, ext=self._ext)


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
                if ((item and item not in items and item not in exclude and
                     item != 'CVS' and
                     not item.startswith('_') and
                     not item.startswith('.'))):
                    items.append(item)
            items.sort()
            return items
        try:
            index = open(os.path.join(dir, indexfile))
        except IOError:
            return [(item, False) for item in listdir(dir)]
        else:
            items = [item for item in [line.strip() for line in index.readlines()]
                     if item != '' and not item.startswith('#')]
            hidden = listdir(dir, exclude=items)
            return [(x, False) for x in items] + [(x, True) for x in hidden]

    def _children(self):
        children = []
        for name, hidden in self._list_dir(self._dir):
            if name not in (self._id, 'resources'):
                children.append(reader(self._dir, name, encoding=self._encoding,
                                       hidden=hidden, parent=self))
        return children


def reader(dir, name, root=True, encoding=None, ext='txt', parent=None, recourse=True, cls=None,
           **kwargs):
    """Create an instance of sensible reader class for given source directory and document name.

    All the keyword arguments are passed to the reader, if they make sense to it.

    """
    if cls is None:
        try:
            import importlib.util
        except ImportError as e:
            # TODO NOPY2: Remove this Python 2 compatibility workaround.
            import imp
            try:
                f, filename, descr = imp.find_module(name, [dir])
            except ImportError:
                module = None
            else:
                module = imp.load_module(name, f, filename, descr)
        else:
            filename = os.path.join(dir, name + '.py')
            if os.path.exists(filename):
                spec = importlib.util.spec_from_file_location(name, filename)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            else:
                module = None
        if module:
            if hasattr(module, 'IndexNode'):
                cls = module.IndexNode  # Just for backwards compatibility
            elif hasattr(module, 'Reader'):
                cls = module.Reader
            else:
                raise lcg.ProcessingError("{} does not define a 'Reader' class.".format(filename))
        elif parent is None and recourse:
            cls = DocDirReader
        else:
            subdir = os.path.join(dir, name)
            if os.path.isdir(subdir):
                dir = subdir
                cls = DocDirReader
            else:
                cls = DocFileReader

    if issubclass(cls, FileReader):
        kwargs = dict(kwargs, dir=dir, encoding=encoding)
        if issubclass(cls, DocFileReader):
            kwargs['ext'] = ext
    return cls(name, parent=parent, **kwargs)
