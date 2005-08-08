# -*- coding: utf-8 -*-
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

import os
import types
import re

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
    _MARKUP = (('linebreak', '//'),
               ('emphasize', ('/',  '/')),
               ('strong',    ('\*', '\*')),
               ('fixed',     ('=',  '=')),
               ('underline', ('_',  '_')),
               ('citation',  ('>>', '<<')),
               ('quotation', ('``', "''")),
               ('link', (r'\[(?P<href>[^\]\|\#\s]*)(?:#(?P<anchor>[^\]\|\s]*))?'
                         r'(?:(?:\||\s+)(?P<title>[^\]]*))?\]')),
               ('uri', r'(https?|ftp)://\S+?(?=[\),.:;]?(\s|$))'),
               ('email', r'\w[\w\-\.]*@\w[\w\-\.]+'),
               ('comment', r'^#.*'),
               ('rule', r'^----+\s*$'),
               ('dash', r'(^|(?<=\s))--($|(?=\s))'),
               ('nbsp', '~'),
               ('lt', '<'),
               ('gt', '>'),
               ('amp', '&'),
               )
    _HELPER_PATTERNS = ('href', 'anchor', 'title')
    
    # The list below lists the which elements are paired on the output
    # (formatter) side, not the input (markup) side (they must be opened and
    # then closed individually).
    _PAIR = ('emphasize', 'strong', 'fixed', 'underline', 'citation',
             'quotation')
    
    _FORMAT = {'strong': ('<strong>', '</strong>'),
               'emphasize': ('<em>', '</em>'),
               'fixed': ('<tt>', '</tt>'),
               'underline': ('<u>', '</u>'),
               'quotation': (u'“<span class="quotation">', u'</span>”'),
               'citation': ('<span class="citation">', '</span>'),
               'comment': '',
               'linebreak': '<br/>',
               'rule': '<hr/>',
               'dash': '&ndash;',
               'nbsp': '&nbsp;',
               'lt':   '&lt;',
               'gt':   '&gt;',
               'amp':   '&amp;',
               }

    def __init__(self, parent):
        regexp = r"(?P<%s>\!?%s)"
        pair_regexp = '|'.join((regexp % ("%s_start", r"(?<!\w)%s(?=\S)"),
                                regexp % ("%s_end",   r"(?<=\S)%s(?!\w)")))
        regexps = [isinstance(markup, types.StringType)
                   and regexp % (type, markup)
                   or pair_regexp % (type, markup[0], type, markup[1])
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
            formatter = getattr(self, '_'+type+'_formatter')
        except AttributeError:
            f = self._FORMAT[type]
            return type in self._PAIR and f[close and 1 or 0] or f
        return formatter(groups, close=close)
        
    def _link_formatter(self, groups, close=False):
        title = groups.get('title')
        href = groups.get('href')
        anchor = groups.get('anchor')
        if href:
            node = self._parent.root_node().find_node(href)
            if node:
                href = node.url()
        else:
            node = self._parent
        if node and not title:
            if anchor:
                section = node.find_section(anchor)
                if section:
                    title = section.title()
            else:
                title = node.title()
        if anchor is not None:
            href += '#'+anchor
        if not title:
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
    corresponding 'Content' element hierarchy.

    """
    
    _SECTION_RE = re.compile(r"^(?P<level>=+) (?P<title>.*) (?P=level)" + \
                             r"(?:[\t ]+(?:\*|(?P<anchor>[\w\d_-]+)))?\s*$",
                             re.MULTILINE)

    _PRE_BLOCK_RE = re.compile(r"^(?:\{\{\{\s*$(.*?)^\}\}\}\s*$" + 
                               r"|-----+\s*$(.*?)^-----+)\s*$",
                               re.DOTALL|re.MULTILINE)

    _LIST_MARKER = r"\(?(?:\*|-|(?:[a-z]|\d+|#)(?:\)|\.))"

    _SPLITTER_RE = re.compile(r"\r?\n(?:(?:\s*\r?\n)+|(?=(?:[\t ]+" +
                              _LIST_MARKER +"[\t ]|:[^:]*\S:\s+)))")

    _MATCHERS = (('list_item',
                  r"(?P<indent>[\t ]+)(?P<type>" + _LIST_MARKER + ")[\t ]+" + \
                  r"(?P<content>.+)"),
                 ('field',
                  r":(?P<label>[^:]*\S):[\t ]*" + \
                  r"(?P<value>[^\r\n]*(?:\r?\n[\t ]+[^\r\n]+)*)"),
                 ('definition',
                  r"(?P<term>\S[^\r\n]*)\r?\n" + \
                  r"(?P<descr>([\t ]+[^\r\n]+\r?\n?)+)"),
                 ('toc',
                  r"(?:(?P<title>[^\r\n]+)[\t ]+)?\@TOC\@\s*"),
                 ('table',
                  r"((\|[^\r\n\|]*)+\|\s*)+"),
                 )
    
    _REGEXPS = [r"^(\s*\r?\n)*(?P<%s>%s)$" % (key, matcher)
                for key, matcher in _MATCHERS]

    _MATCHER = re.compile('(?:' + '|'.join(_REGEXPS) + ')', re.DOTALL)

    _HELPER_PATTERNS = ('indent', 'content', 'title', 'label', 'value', 'term',
                        'descr')
    
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
        return self._make_sections(root)

    def _make_sections(self, section):
        subsections = [Section(self._parent, s.title, self._make_sections(s),
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

    def _store_list_item(self, block, groups):
        content = WikiText(self._parent, groups['content'])
        indent = re.sub(' {0,7}\t', 8*' ', groups['indent'])
        return (self._list_item_type(groups), len(indent), content)
        
    def _finish_list_item(self, stored):
        parent = self._parent
        class _Context:
            def __init__(self, type, indent, content):
                self.type = type
                self.indent = indent
                self.content = content
                self.items = []
            def state(self):
                return (self.type, self.indent, self.content, self.items)
            def make_list(self):
                #_log("**")
                items = [len(i) > 1 and Container(parent, i) or i[0]
                         for i in self.items]
                self.content.append(ItemizedList(parent, items, type=self.type))
                self.items = []
        result = []
        stack = [] # For storing the context between level changes.
        context = _Context(stored[0][0], stored[0][1], result)
        stored.append(('xxx', 0, None))
        for type, indent, content in stored:
            #_log("====", content, indent, type, len(stack), context.state())
            if indent != context.indent:
                if indent > context.indent:
                    # Save the context and start a new level.
                    stack.append(context)
                    context = _Context(type, indent, context.items[-1])
                else:
                    # Restore the context of the higher level.
                    while indent < context.indent:
                        context.make_list()
                        if stack and stack[-1].indent >= indent:
                            context = stack.pop()
                        else:
                            # That's a bad indentation, but let's not panic.
                            context = _Context(type, indent, context.content)
                #_log("<=>", context.state())
            if context.items and context.type != type:
                context.make_list()
                context.type = type
            if content is not None:
                context.items.append([content])
        assert not stack
        return result

    def _store_field(self, block, groups):
        label = WikiText(self._parent, groups['label'])
        content = WikiText(self._parent, groups['value'])
        return (label, content)
        
    def _finish_field(self, stored):
        p = self._parent
        fields = [Field(p, label, value) for label, value in stored]
        return (FieldSet(p, fields),)
    
    def _store_definition(self, block, groups):
        term = WikiText(self._parent, groups['term'])
        content = WikiText(self._parent, groups['descr'])
        return (term, content)
        
    def _finish_definition(self, stored):
        p = self._parent
        definitions = [Definition(p, term, descr) for term, descr in stored]
        return (DefinitionList(p, definitions),)
    
    def _parse_blocks(self, text):
        def finish(type, data):
            f = getattr(self, '_finish_'+type)
            return f(data)
        content = []
        unfinished = None
        for piece in self._SPLITTER_RE.split(text):
            if len(piece.strip()) == 0: continue
            block, type, groups = self._identify_block(piece)
            #_log("============", type)
            #_log(block)
            if unfinished and unfinished[0] != type:
                content.extend(finish(*unfinished))
                unfinished = None
            if hasattr(self, '_store_'+type):
                store = getattr(self, '_store_'+type)
                data = store(block, groups)
                if unfinished:
                    unfinished[1].append(data)
                else:
                    unfinished = (type, [data])
            else:
                content.append(getattr(self, '_make_'+type)(block, groups))
        if unfinished:
            content.extend(finish(*unfinished))
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
        elif t in ('*', '-'):
            return ItemizedList.TYPE_UNORDERED
        elif t[0].isalpha():
            return ItemizedList.TYPE_ALPHA
        else:
            return ItemizedList.TYPE_NUMERIC

    def parse(self, text):
        return self._parse_sections(re.sub("(?m)^#.*$", "", text))


class MacroParser(object):
    _VARIABLE_REGEX = re.compile(r"(?!\\)\$\{?([a-zA-Z_]+)\}?")
    _INCLUDE_REGEX = re.compile(r'(?m)^\s*#include (.*)$')
    _IF_ELSE_REGEX = re.compile(r'(?m)^\s*(#(?:if .+|else|endif))\s*$')

    class _ConditionalText(object):
        def __init__(self, provider, condition, parent=None):
            self._provider = provider
            self._condition = condition
            self.parent = parent
            self._state = True
            self._content = {True: [], False: []}
            
        def switch(self):
            self._state = False
        
        def append(self, content):
            self._content[self._state].append(content)

        def __str__(self):
            value = bool(self._provider(self._condition))
            return '\n'.join([unicode(x) for x in self._content[value]])

    
    def __init__(self, eval_provider=None, include_provider=None,
                 include_dir='.'):
        self._eval_provider = eval_provider or self._python_eval_provider
        self._include_provider = include_provider
        self._include_dir = include_dir
        self._vars = {}

    def _python_eval_provider(self, expr):
        return eval("bool(%s)" % expr, self._vars)

    def _substitute_variables(self, text):
        try:
            return self._VARIABLE_REGEX.sub(lambda m: self._vars[m.group(1)],
                                            text)
        except KeyError, e:
            raise Exception("Unknown variable $%s." % e.args[0])

    def add_globals(self, **kwargs):
        self._vars.update(kwargs)
        
    def parse(self, text):
        func = lambda m: self._include_provider(m.group(1).strip())
        text = self._INCLUDE_REGEX.sub(func, text)
        tokens = self._IF_ELSE_REGEX.split(text)
        structured = current = self._ConditionalText(self._eval_provider, 1)
        for t in tokens:
            if t.startswith('#if'):
                new = self._ConditionalText(self._eval_provider, t[4:].strip(),
                                            parent=current)
                current.append(new)
                current = new
            elif t == '#else':
                current.switch()
            elif t == '#endif' and current.parent is not None:
                current = current.parent
            else:
                current.append(t)
        parsed = unicode(structured)
        return self._substitute_variables(parsed)

    
def _log(*args):
    """Just for internal debugging purposes..."""
    def _str(x):
        if isinstance(x, WikiText):
            return '"'+str(x._text.encode('ascii', 'replace'))+'"'
        elif isinstance(x, Container):
            return "<%s %s>" % (x.__class__.__name__, _str(x._content))
        elif isinstance(x, (types.ListType, types.TupleType)):
            result = ', '.join([_str(i) for i in x])
            if isinstance(x, types.ListType):
                return '[' + result + ']'
            else:
                return '(' + result + ')'
        else:
            return str(x.encode('ascii', 'replace'))
    sys.stderr.write(' '.join([_str(a) for a in args])+"\n")
   
