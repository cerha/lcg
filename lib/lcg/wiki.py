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
# Author: Jonas Borgstr�m <jonas@edgewall.com>
# This code was shamelessly stolen from the Trac Wiki formatter.
# We might need some specific features in future, however this is sufficient
# for the beginning...

import re
import time
import os
import StringIO
import string
from xml.sax import saxutils
from types import *

class CommonFormatter:
    """This class contains the patterns common to both Formatter and
    OneLinerFormatter"""
    
    _rules = [r"""(?P<bold>''')""",
              r"""(?P<italic>'')""",
              r"""(?P<underline>__)""",
              r"""(?P<begintt>\{\{\{)""",
              r"""(?P<endtt>\}\}\})""",
              r"""(?P<htmlescapeentity>&#[0-9]+;)""",
              r"""(?P<wikilink>(^|(?<=[^A-Za-z]))[A-Z][a-z/]*(?:[A-Z][a-z/]+)+)""",
              r"""(?P<fancylink>\[(?P<fancyurl>([a-z]+:[^ ]+)) (?P<linkname>.*?)\])"""]

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

    def _htmlescapeentity_formatter(self, match, fullmatch):
        #dummy function that match html escape entities in the format:
        # &#[0-9]+;
        # This function is used to avoid these being matched by
        # the tickethref regexp
        return match
    
    def _wikilink_formatter(self, match, fullmatch):
        #global page_dict
        #if page_dict and not page_dict.has_key(match):
        #    return '<a class="wiki-missing-page" href="%s">%s?</a>' % \
        #           (href.wiki(match), match)
        #else:
        return '<a href="%s">%s</a>' % (match, match)

    def _url_formatter(self, match, fullmatch):
        return '<a href="%s">%s</a>' % (match, match)

    def _fancylink_formatter(self, match, fullmatch):
        link = fullmatch.group('fancyurl')
        name = fullmatch.group('linkname')
        if link[0:5] == 'wiki:':
            link = href.wiki(link[5:])
        elif link[0:4] == 'svn:':
            m = re.search('^svn:(([^#]+)(#([0-9]+))?)', link)
            if m.group(4):
                link = href.browser(m.group(2), int(m.group(4)))
            else:
                link = href.browser(m.group(1))

        return '<a href="%s">%s</a>' % (link, name)


class OneLinerFormatter(CommonFormatter):
    """
    A special version of the wiki formatter that only implement a
    subset of the wiki formatting functions. This version is useful
    for rendering short wiki-formatted messages on a single line
    """
    
    _rules = CommonFormatter._rules + \
             [r"""(?P<url>([a-z]+://[^ ]+[^\., ]))"""]
    
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
    """
    A simple Wiki formatter
    """
    _rules = [r"""(?P<svnimg>svn:([^ ]+)(\.png|\.jpg|\.jpeg|\.gif))"""] + \
             CommonFormatter._rules + \
             [r"""(?P<macro>\[\[(?P<macroname>[a-zA-Z]+)(\((?P<macroargs>[^\)]*)\))?\]\])""",
              r"""(?P<heading>^\s*(?P<hdepth>=+)\s.*\s(?P=hdepth)$)""",
              r"""(?P<list>^(?P<ldepth>\s+)(?:\*|[0-9]+\.) )""",
              r"""(?P<indent>^(?P<idepth>\s+)(?=[^\s]))""",
              r"""(?P<imgurl>([a-z]+://[^ ]+)(\.png|\.jpg|\.jpeg|\.gif))""",
              r"""(?P<url>([a-z]+://[^ ]+[^\., ]))"""]
    
    _compiled_rules = re.compile('(?:' + string.join(_rules, '|') + ')')

    # RE patterns used by other patterna
    _helper_patterns = ('idepth', 'ldepth', 'hdepth', 'fancyurl',
                        'linkname', 'macroname', 'macroargs')

    def __init__(self, hdf = None):
        self.hdf = hdf
        
    def _macro_formatter(self, match, fullmatch):
        name = fullmatch.group('macroname')
        if name in ['br', 'BR']:
            return '<br />'
        args = fullmatch.group('macroargs')
        try:
            macros = __import__('wikimacros.' + name,
                                globals(),  locals(), [])
            module = getattr(macros, name)
            func = getattr(module, 'execute')
            return func(self.hdf, args)
        except Exception, e:
            return 'Macro %s(%s) failed: %s' % (name, args, e)

    def _heading_formatter(self, match, fullmatch):
        depth = min(len(fullmatch.group('hdepth')), 5)
        self.close_paragraph()
        self.close_indentation()
        self.close_list()
        self.out.write('<h%d>%s</h%d><a name="%s"></a>' % \
                       (depth, match[depth + 1:len(match) - depth - 1],
                        depth, str(id(self))+'-'+'0'))
        return ''

    def _svnimg_formatter(self, match, fullmatch):
        return '<img src="%s" alt="%s" />' % (href.file(match[4:]), match[4:])

    def _imgurl_formatter(self, match, fullmatch):
        return '<img src="%s" alt="%s" />' % (match, match)

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
