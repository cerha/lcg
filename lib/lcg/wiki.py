# -*- coding: iso8859-2 -*-
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
#
# Author: Jonas Borgström <jonas@edgewall.com>
# This code was shamelessly stolen from the Trac Wiki formatter.
# We might need some specific features in future, however this is sufficient
# for the beginning...

import re
import time
import types
import os
import StringIO
import string
from xml.sax import saxutils
from types import *

class CommonFormatter:
    """This class contains the patterns common to both Formatter and
    OneLinerFormatter"""
    
    _rules = [r"""(?P<bold>\*)""",
              r"""(?P<italic>/)""",
              r"""(?P<underline>_)""",
              r"""(?P<begintt>\{\{\{)""",
              r"""(?P<endtt>\}\}\})"""]

    def replace(self, fullmatch):
        for type, match in fullmatch.groupdict().items():
            if match and not type in Formatter._helper_patterns:
                return getattr(self, '_' + type + '_formatter')(match, fullmatch)
    
    def tag_open_p(self, tag):
        """Do we currently have any open tag with @tag as end-tag"""
        return tag in self._open_tags

    def close_tag(self, tag):
        tmp = s = ''
        while self._open_tags != [] and tag != tmp:
            tmp = self._open_tags.pop()
            s += tmp
        return s

    def open_tag(self, tag):
        self._open_tags.append(tag)
        
    def simple_tag_handler(self, open_tag, close_tag):
        """Generic handler for simple binary style tags"""
        if self.tag_open_p(close_tag):
            return self.close_tag(close_tag)
        else:
            self.open_tag(close_tag)
            return open_tag
        
    def _bold_formatter(self, match, fullmatch):
        return self.simple_tag_handler('<strong>', '</strong>')
    
    def _italic_formatter(self, match, fullmatch):
        return self.simple_tag_handler('<i>', '</i>')

    def _underline_formatter(self, match, fullmatch):
        return self.simple_tag_handler('<span class="underline">', '</span>')

    def _begintt_formatter(self, match, fullmatch):
        return '<tt>'

    def _endtt_formatter(self, match, fullmatch):
        return '</tt>'


class OneLinerFormatter(CommonFormatter):
    """
    A special version of the wiki formatter that only implement a
    subset of the wiki formatting functions. This version is useful
    for rendering short wiki-formatted messages on a single line
    """
    _rules = CommonFormatter._rules
    _compiled_rules = re.compile('(?:' + string.join(_rules, '|') + ')')

    def format(self, text, out):
        if not text:
            return ''
        self.out = out
        self._open_tags = []
        
        rules = self._compiled_rules

        result = re.sub(rules, self.replace, escape(text.strip()))
        # Close all open 'one line'-tags
        result += self.close_tag(None)
        out.write(result)


class Formatter(CommonFormatter):
    """A simple Wiki formatter"""

    _rules = CommonFormatter._rules + \
             [r"""(?P<heading>^\s*(?P<hdepth>=+)\s.*\s(?P=hdepth)$)""",
              r"""(?P<list>^(?P<ldepth>\s+)(?:\*|[0-9]+\.) )""",
              r"""(?P<indent>^(?P<idepth>\s+)(?=[^\s]))"""]
    
    _compiled_rules = re.compile('(?:' + string.join(_rules, '|') + ')')

    # RE patterns used by other patterna
    _helper_patterns = ('idepth', 'ldepth', 'hdepth', 'linkname')

    def __init__(self, hdf = None):
        self.hdf = hdf
        
    def _heading_formatter(self, match, fullmatch):
        depth = min(len(fullmatch.group('hdepth')), 5)
        self.close_paragraph()
        self.close_indentation()
        self.close_list()
        self.out.write('<h%d>%s</h%d><a name="%s"></a>' % \
                       (depth, match[depth + 1:len(match) - depth - 1],
                        depth, str(id(self))+'-'+'0'))
        return ''

    def _indent_formatter(self, match, fullmatch):
        depth = int((len(fullmatch.group('idepth')) + 1) / 2)
        self.open_indentation(depth)
        return ''

    def close_indentation(self):
        self.out.write('</blockquote>\n' * self.indent_level)
        self.indent_level = 0
        
    def open_indentation(self, depth):
        diff = depth - self.indent_level
        if diff != 0:
            self.close_paragraph()
            self.close_indentation()
            self.close_list()
            self.indent_level = depth
            for i in range(depth):
                self.out.write('<blockquote>\n')

    def _list_formatter(self, match, fullmatch):
        ldepth = len(fullmatch.group('ldepth'))
        depth = int((len(fullmatch.group('ldepth')) + 1) / 2)
        self.in_list_item = depth > 0
        type_ = ['ol', 'ul'][match[ldepth] == '*']
        self._set_list_depth(depth, type_)
        return ''
    
    def _set_list_depth(self, depth, type_):
        current_depth = len(self._list_stack)
        diff = depth - current_depth
        self.close_paragraph()
        self.close_indentation()
        if diff > 0:
            for i in range(diff):
                self._list_stack.append(type_)
                self.out.write('<%s><li>' % type_)
        elif diff < 0:
            for i in range(-diff):
                tmp = self._list_stack.pop()
                self.out.write('</li></%s>' % tmp)
            if self._list_stack != [] and type_ != self._list_stack[-1]:
                tmp = self._list_stack.pop()
                self._list_stack.append(type_)
                self.out.write('</li></%s><%s><li>' % (tmp, type_))
            if depth > 0:
                self.out.write('</li><li>')
        # diff == 0
        elif self._list_stack != [] and type_ != self._list_stack[-1]:
            tmp = self._list_stack.pop()
            self._list_stack.append(type_)
            self.out.write('</li></%s><%s><li>' % (tmp, type_))
        elif depth > 0:
            self.out.write('</li><li>')

    def close_list(self):
        if self._list_stack != []:
            self._set_list_depth(0, None)
    
    def open_paragraph(self):
        if not self.paragraph_open:
            self.out.write('<p>\n')
            self.paragraph_open = 1
            
    def close_paragraph(self):
        if self.paragraph_open:
            self.out.write('</p>\n')
            self.paragraph_open = 0

    def format(self, text, out):
        self.out = out
        self._open_tags = []
        self._list_stack = []
        
        self.in_pre = 0
        self.indent_level = 0
        self.paragraph_open = 0

        rules = self._compiled_rules
        
        for line in escape(text).splitlines():
            # Handle PRE-blocks
            if not self.in_pre and line == '{{{':
                self.in_pre = 1
                self.close_paragraph()
                self.out.write('<pre>\n')
                continue
            elif self.in_pre:
                if line == '}}}':
                    out.write('</pre>\n')
                    self.in_pre = 0
                else:
                    self.out.write(line + '\n')
                continue
            # Handle Horizontal ruler
            elif line[0:4] == '----':
                self.close_paragraph()
                self.close_indentation()
                self.close_list()
                self.out.write('<hr />\n')
                continue
            # Handle new paragraph
            elif line == '':
                self.close_paragraph()
                self.close_indentation()
                self.close_list()
                continue

            self.in_list_item = 0
            
            # Throw a bunch of regexps on the problem
            result = re.sub(rules, self.replace, line)
            # Close all open 'one line'-tags
            result += self.close_tag(None)

            if not self.in_list_item:
                self.close_list()
            
            if len(result) and not self.in_list_item:
                self.open_paragraph()
            out.write(result + '\n')
            
        self.close_paragraph()
        self.close_indentation()
        self.close_list()

      
class _Node(object):
    
    def __init__(self, title, level):
        assert isinstance(title, types.StringTypes)
        assert isinstance(level, types.IntType) and level >= 0
        self.title = title
        self.level = level
        self.parent = None
        self.content = None
        self.children = []

    def tree(self, indent=0):
        children = [n.tree(indent+1) for n in self._children]
        return "%s* %s\n%s" % ("  "*indent, self.title(), "".join(children))

    def sections(self):
        return [Section(n.title, n.content, n.sections())
                for n in self.children]
        
    def add_child(self, node):
        assert isinstance(node, _Node)
        node.parent = self
        self.children.append(node)
                

class Section(object):

    def __init__(self, title, text, sections):
        self._title = title
        self._text = text
        self._sections = sections
        
    def title(self):
        return self._title

    def text(self):
        return self._text

    def sections(self):
        return self._sections

    
def parse_sections(text):
    matcher = re.compile(r"^(?P<level>=+) (?P<title>.*) (?P=level)\s*$",
                         re.MULTILINE)
    last = root = _Node('__ROOT_NODE__', 0)
    while (1):
        m = matcher.search(text)
        if not m:
            last.content = text
            break
        last.content = text[:m.start()]
        text = text[m.end():]
        this = _Node(m.group('title'), len(m.group('level')))
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
    return (root.content, root.sections())

    
def format(wikitext):
    out = StringIO.StringIO()
    Formatter().format(wikitext, out)
    return out.getvalue()

def wiki_to_oneliner(wikitext):
    out = StringIO.StringIO()
    OneLinerFormatter().format(wikitext, out)
    return out.getvalue()

def escape(text, param={'"':'&#34;'}):
    """Escapes &, <, > and \""""
    if not text:
        return ''
    elif type(text) is StringType:
        return saxutils.escape(text, param)
    else:
        return text
