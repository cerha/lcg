# -*- coding: utf-8 -*-
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


class Formatter(object):
    """Simple Wiki markup formatter.

    This simple Wiki formatter can only format the markup within one block (ie.
    a single paragraph or other non-structured piece of text).

    All the document structure (headings, paragraphs, bullet lists etc.) should
    be recognized by the 'Parser' class below.  Then only the contents of the
    recognized structured elements can be formatter using this formatter (where
    appropriate).

    """
    _MARKUP = (('bold', '\*'),
               ('italic', '/'),
               ('fixed', '='),
               ('underline', '_'),
               ('citation', ('>>', '<<')),
               ('quotation', ('``', "''")),
               ('link', '\[(?P<href>[^\]\|]+)(?:\|(?P<title>[^\]]+))?\]'),
               ('uri', '(https?|ftp)://\S+?(?=[\),.:;]?(\s|$))'),
               ('email', '\w[\w\-\.]*@\w[\w\-\.]+'),
               ('comment', '^#.*'),
               ('linebreak', '//'),
               ('rule', '^----\s*$'),
               ('nbsp', '~'),
               )
    _HELPER_PATTERNS = ('href', 'title')
    
    # The list below lists the which elements are paired on the output
    # (formatter) side, not the input (markup) side (they must be opened and
    # then closed individually).
    _PAIR = ('bold', 'italic', 'fixed', 'underline', 'citation', 'quotation')
    
    _FORMAT = {'bold': ('<strong>', '</strong>'),
               'italic': ('<i>', '</i>'),
               'fixed': ('<tt>', '</tt>'),
               'underline': ('<span class="underline">', '</span>'),
               'quotation': (u'“<span class="quotation">', u'</span>”'),
               'citation': ('<span class="citation">', '</span>'),
               'comment': '',
               'linebreak': '<br/>',
               'rule': '<hr/>',
               'nbsp': '&nbsp;',
               }

    def __init__(self, parent):
        regexp = "(?P<%s>\!?%s)"
        regexps = [isinstance(markup, types.StringType)
                   and regexp % (type, markup)
                   or '|'.join((regexp, regexp)) % (type+'_start', markup[0],
                                                    type+'_end', markup[1])
                   for type, markup in self._MARKUP]
        self._rules = re.compile('(?:' +'|'.join(regexps)+ ')', re.MULTILINE)
        self._parent = parent

    def _markup_handler(self, match):
        type = [key for key, m in match.groupdict().items()
                if m and not key in self._HELPER_PATTERNS][0]
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
            return ''.join([self._formatter(t, match.groupdict(), close=True)
                            for t in to_close])
        elif not end:
            if type in self._PAIR:
                self._open.append(type)
            return self._formatter(type, match.groupdict())

    def _formatter(self, type, groups, close=False):
        try:
            return getattr(self, '_'+type+'_formatter')(groups, close=close)
        except AttributeError:
            f = self._FORMAT[type]
            return type in self._PAIR and f[close and 1 or 0] or f
        
    def _link_formatter(self, groups, close=False):
        title = groups['title']
        href = groups['href']
        if not title:
            if href.startswith('#'):
                section = self._parent.find_section(href[1:])
                title = section and section.title() or href[1:]
            else:
                title = href
        return '<a href="%s">%s</a>' % (href, title)

    def _uri_formatter(self, groups, close=False):
        return self._link_formatter({'href': groups['uri'], 'title': None})

    def _email_formatter(self, groups, close=False):
        addr = groups['email']
        return self._link_formatter({'href': 'mailto:'+addr, 'title': addr})

    def format(self, text):
        self._open = []
        result = re.sub(self._rules, self._markup_handler, text)
        self._open.reverse()
        x = self._open[:]
        for type in x:
            result += self._formatter(type, {}, close=True)
        return result
        
    
class Parser(object):
    """Structured Wiki document parser.

    This parser parses the structure of the document and builds the
    corresponding 'Conetent' element hierarchy.

    """
    _LIST_MARKER = "(?:\*|(?:[a-z]|\d+)(?:\)|\.))"
    
    _SECTION_RE = re.compile(r"^(?P<level>=+) (?P<title>.*) (?P=level)" + \
                             r"(?:\s+(?:\*|(?P<anchor>[\w\d_-]+)))?\s*$",
                             re.MULTILINE)

    _PRE_BLOCK_RE = re.compile(r"^(?:\{\{\{\s*$(.*?)^\}\}\}\s*$" + 
                               r"|-----+\s*$(.*?)^-----+)\s*$",
                               re.DOTALL|re.MULTILINE)

    _SPLITTER_RE = re.compile(r"\r?\n(?:(?:\s*\r?\n)+|(?=\s+" +
                              _LIST_MARKER +" ))")

    _MATCHERS = (('list_item',
                  "(?P<depth> +)(?P<type>"+ _LIST_MARKER +") (?P<content>.*)"),
                 ('table',
                  "\s*((\|[^\r\n\|]*)+\|\s*)+"),
                 ('toc',
                  "\s*(?:(?P<title>.+)\s+)?\@TOC\@\s*"),
                 )
    _REGEXPS = [r"^(?P<%s>%s)$" % (key, matcher) for key, matcher in _MATCHERS]
    _MATCHER = re.compile('(?:' + '|'.join(_REGEXPS) + ')', re.DOTALL)
    _HELPER_PATTERNS = ('depth', 'content', 'title')
    
    class _Section(object):
        def __init__(self, title, anchor, level):
            assert isinstance(title, types.StringTypes)
            assert isinstance(anchor, types.StringTypes) or anchor is None
            assert isinstance(level, types.IntType) and level >= 0
            self.title = title
            self.anchor = anchor
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
        root = last = self._Section('__ROOT_SECTION__', None, 0)
        while (1):
            m = self._SECTION_RE.search(text)
            if not m:
                last.content = self._parse_section_content(text)
                break
            last.content = self._parse_section_content(text[:m.start()])
            text = text[m.end():]
            this = self._Section(m.group('title'), m.group('anchor'),
                                 len(m.group('level')))
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
        subsections = [Section(self._parent, s.title, self._build_sections(s),
                               anchor=s.anchor)
                       for s in section.children]
        if section.content is None:
            return subsections
        else:
            return section.content + subsections
        
    def _parse_section_content(self, text):
        content = []
        while (1):
            m = self._PRE_BLOCK_RE.search(text)
            if not m:
                content += self._parse_blocks(text)
                break
            content += self._parse_blocks(text[:m.start()])
            pre = m.group(1) or m.group(2)
            content.append(PreformattedText(self._parent, pre))
            text = text[m.end():]
        return content

    def _identify_block(self, text):
        match = self._MATCHER.match(text)
        if match:
            found = [(key, match.groupdict())
                     for key, m in match.groupdict().items()
                     if m and not key in self._HELPER_PATTERNS]
            return (text, found[0][0], found[0][1])
        else:
            return (text, 'paragraph', {})

    def _parse_blocks(self, text):
        blocks = [self._identify_block(p)
                  for p in self._SPLITTER_RE.split(text) if len(p.strip()) > 0]
        content = []
        items = []
        list_type = None
        for block, type, groups in blocks:
            t = self._list_item_type(groups)
            if items and (type != 'list_item' or list_type != t) :
                l = ItemizedList(self._parent, items, type=list_type)
                content.append(l)
                items = []
            if type == 'list_item':
                items.append(WikiText(self._parent, groups['content']))
                list_type = t
            else:
                content.append(getattr(self, '_make_'+type)(block, groups))
        if items:
            content.append(ItemizedList(self._parent, items, type=list_type))
        return content

    def _make_paragraph(self, block, groups):
        return Paragraph(self._parent, WikiText(self._parent, block))
    
    def _make_table(self, block, groups):
        p = self._parent
        return Table(p, [TableRow(p, [TableCell(p, WikiText(p, x.strip()))
                                      for x in row.split('|')[1:-1]])
                         for row in block.strip().splitlines()])

    def _make_toc(self, block, groups):
        return TableOfContents(self._parent, title=groups['title'], depth=99)
    
    def _list_item_type(self, groups):
        t = groups.get('type')
        if not t:
            return None
        elif t == '*':
            return ItemizedList.TYPE_UNORDERED
        elif t[0].isalpha():
            return ItemizedList.TYPE_ALPHA
        else:
            return ItemizedList.TYPE_NUMERIC

    def parse(self, text):
        return self._parse_sections(text)
    

def escape(text, param={'"':'&#34;'}):
    """Escapes &, <, > and \""""
    if not text:
        return ''
    elif type(text) is types.StringType:
        return saxutils.escape(text, param)
    else:
        return text
