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

import os
import types
import re
from xml.sax import saxutils

from lcg import *


class InlineFormatter(object):
    """Simple Wiki markup formatter.

    This simple Wiki formatter can only format the markup within one block (ie.
    a single paragraph or other non-structured piecece of text).

    All the document structure (headings, paragraphs, bullet lists etc.) should
    be recognized by the 'Parser' class below.  Then only the contents of the
    recognized structured elements can be formatter using this formatter (where
    appropriate).

    """
    _MARKUP = (('bold', '\*'),
               ('italic', '/'),
               ('fixed', '='),
               ('underline', '_'),
               ('example_start', '>>'),
               ('example_end', '<<'))

    _FORMAT = {'bold': ('<strong>', '</strong>'),
               'italic': ('<i>', '</i>'),
               'fixed': ('<tt>', '</tt>'),
               'underline': ('<span class="underline">', '</span>'),
               }

    _REGEXPS = [r"(?P<%s>\!?%s)" % (tag, markup) for tag, markup in _MARKUP]
    _RULES = re.compile('(?:' + '|'.join(_REGEXPS) + ')')

    def __init__(self, parent):
        self._parent = parent

    def _markup_handler(self, match):
        type = [key for key, m in match.groupdict().items() if m][0]
        if match.group(type).startswith('!'):
            return match.group(type)[1:]
        start = False
        end = False
        if type.endswith('_start'):
            type = type[:-6]
            start = True
        elif type.endswith('_end'):
            type = type[:-4]
            end = True
        if not start and type in self._open:
            i = self._open.index(type)
            to_close = self._open[i:]
            del self._open[i:]
            to_close.reverse()
            # We have to close the nested open tags as-well.
            return ''.join([self._formatter(t, close=True) for t in to_close])
        elif not end:
            self._open.append(type)
            return self._formatter(type)

    def _formatter(self, type, close=False):
        try:
            return self._FORMAT[type][close and 1 or 0]
        except:
            return getattr(self, '_'+type+'_formatter')(close=close)
        
    def _example_formatter(self, close=False):
        if not close:
            return '<span class="example" lang="%s">' % self._parent.language()
        else:
            return '</span>'
        
    def format(self, text):
        self._open = []
        result = re.sub(self._RULES, self._markup_handler, text)
        self._open.reverse()
        x = self._open[:]
        for type in x:
            result += self._formatter(type, close=True)
        return result
        
    
class Parser(object):
    """Structured Wiki document parser.

    This parser parses the structure of the document and builds the
    corresponding 'Conetent' element hierarchy.

    """
    
    _SECTION_RE = re.compile(r"^(?P<level>=+) (?P<title>.*) (?P=level)\s*$",
                             re.MULTILINE)
    _SPLITTER_RE = re.compile(r"\r?\n(?:(?:\s*\r?\n)+|(?=\s+\* ))")

    _MATCHERS = (('list_item', "(?P<depth>\s+)\* (?P<content>.*)"),
                 )
    _REGEXPS = [r"^(?P<%s>%s)$" % (key, matcher) for key, matcher in _MATCHERS]
    _MATCHER = re.compile('(?:' + '|'.join(_REGEXPS) + ')')
    _HELPER_PATTERNS = ('depth', 'content')
    
    class _Section(object):
        def __init__(self, title, level):
            assert isinstance(title, types.StringTypes)
            assert isinstance(level, types.IntType) and level >= 0
            self.title = title
            self.level = level
            self.parent = None
            self.content = None
            self.children = []
        def add_child(self, section):
            assert isinstance(section, Parser._Section)
            section.parent = self
            self.children.append(section)
        #def tree(self, indent=0):
        #    children = [n.tree(indent+1) for n in self._children]
        #    return "%s* %s\n%s" % ("  "*indent, self.title(), "".join(children))

    def __init__(self, parent):
        self._parent = parent

    def _parse_sections(self, text):
        root = last = self._Section('__ROOT_SECTION__', 0)
        while (1):
            m = self._SECTION_RE.search(text)
            if not m:
                last.content = self._parse_section_content(text)
                break
            last.content = self._parse_section_content(text[:m.start()])
            text = text[m.end():]
            this = self._Section(m.group('title'), len(m.group('level')))
            if last.level < this.level:
                parent = last
            elif last.level == this.level:
                parent = last.parent
            else:
                parent = last.parent
                while (parent.level >= this.level):
                    parent = parent.parent
            parent.add_child(this)
            last = this
        return self._build_sections(root)

    def _build_sections(self, section):
        subsections = [Section(self._parent, s.title, self._build_sections(s))
                       for s in section.children]
        if section.content is None:
            return subsections
        else:
            return section.content + subsections
        
    def _make_itemized_list(self, items):
        pass
    
    def _identify_block(self, text):
        match = self._MATCHER.match(text)
        if match:
            found = [(key, match.groupdict())
                     for key, m in match.groupdict().items()
                     if m and not key in self._HELPER_PATTERNS]
            return (text, found[0][0], found[0][1])
        else:
            return (text, None, None)

    def _parse_section_content(self, text):
        blocks = [self._identify_block(p)
                  for p in self._SPLITTER_RE.split(text) if len(p.strip()) > 0]
        items = []
        content = []
        for block, type, groups in blocks:
            if items and type != 'list_item':
                content.append(ItemizedList(self._parent, items))
                items = []
            if type == 'list_item':
                wt = WikiText(self._parent, groups['content'])
                items.append(ListItem(self._parent, wt))
            else:
                p = Paragraph(self._parent, WikiText(self._parent, block))
                content.append(p)
        if items:
            content.append(ItemizedList(self._parent, items))
        return content

    def parse(self, text):
        return self._parse_section_content(text)
    

def escape(text, param={'"':'&#34;'}):
    """Escapes &, <, > and \""""
    if not text:
        return ''
    elif type(text) is types.StringType:
        return saxutils.escape(text, param)
    else:
        return text
