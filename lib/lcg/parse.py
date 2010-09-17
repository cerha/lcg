# -*- coding: utf-8 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007, 2008, 2009, 2010 Brailcom, o.p.s.
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

class ProcessingError(Exception):
    """Exception for errors generated during processing of defective source data.

    The reason (error message) must be specified when the error is raised.  A
    special property of this class, however, is that other helper attributes
    such as rough text location and associated source can be filled in later
    during the exception propagation.  These other attributes should primarily
    help the content creator to locate the error in the source document.

    """
    def __init__(self, reason, info=[]):
        """Initialize the exception

        Arguments:
          reason -- text string describing the reason for the error
          
        """
        self._reason = reason
        self._info = info

    def add_info(self, caption, information):
        """Add more information to the exception.

        There are no strict rules on 'caption' and 'information' except that
        both must be strings.  See the 'info()' method.
        
        """
        assert isinstance(caption, basestring)
        self._info.append((caption, information))

    def info(self):
        """Return information about the error.

        Returns a list of tuples (caption, information) where 'caption' is an
        identification of the type of the information ('File', 'Line',
        'Exercise' etc.)  and 'information' is a string containing the
        information.

        The list is sorted in the order the information has been added (this is
        usually bottom-up).

        Example:
          [('File', '01-telephoning/exercises.py'),
           ('Unit', '01-telephoning'),
           ('Section', 'Consolidation'),
           ('Offending text', '* Bla bla')]
           
        """
        return self._info

    def reason(self):
        """Return reason for the error
        
        Example: A choice must start with a + or minus sign and a space!
        
        """
        return self._reason
    

class Parser(object):
    """Structured text (wiki) document parser.

    This parser parses the structure of the document and builds the
    corresponding 'Content' element hierarchy.  This parser doesn't care about
    inline markup at all.  Only higher-level constructs are recognized here.
    Formatting the inline markup is done by the 'MarkupFormatter' on LCG output
    (as oposed to parsing, which is done on LCG input).

    """
    
    _SECTION_RE = re.compile(r"^(?P<level>=+) (?P<title>.*) (?P=level)" + \
                             r"(?:[\t ]+(?:\*|(?P<anchor>[\w\d_-]+)))?\s*$",
                             re.MULTILINE)

    _PRE_BLOCK_RE = re.compile(r"^-----+[ \t]*\r?\n(.*?)^-----+\s*$", re.DOTALL|re.MULTILINE)

    _LIST_MARKER = r"\(?(?:\*|-|(?:[a-z]|\d+|#)(?:\)|\.))"

    _SPLITTER_RE = re.compile(r"\r?\n(?:(?:\s*\r?\n)+|(?=(?:[\t ]+" +
                              _LIST_MARKER +"[\t ]|:[^:]*\S:\s+)))")

    _COMMENT_MATCHER = re.compile("^#[^\n]*(\n|$)", re.MULTILINE)

    _MATCHERS = (('list_item',
                  r"(?P<indent>[\t ]+)(?P<type>" + _LIST_MARKER + ")[\t ]+" + \
                  r"(?P<content>.+)"),
                 ('field',
                  r":(?P<label>[^:]*\S):[\t ]*" + \
                  r"(?P<value>[^\r\n]*(?:\r?\n[\t ]+[^\r\n]+)*)"),
                 ('definition',
                  r"(?P<term>\S[^\r\n]*)\r?\n" + \
                  r"(?P<descr>([\t ]+[^\r\n]+\r?\n)*([\t ]+[^\r\n]+\r?\n?))"),
                 ('toc',
                  r"(?:(?P<title>[^\r\n]+)[\t ]+)?\@(?P<toctype>(N?TOC|NodeIndex))(\((?P<tocdepth>\d+)\))?\@\s*"),
                 ('table',
                  r"((\|[^\r\n\|]*)+\|\s*)+"),
                 ('rule',
                  r'^----+\s*$'),
                 )
    
    _REGEXPS = [r"^(\s*\r?\n)*(?P<%s>%s)$" % (key, matcher)
                for key, matcher in _MATCHERS]

    _MATCHER = re.compile('(?:' + '|'.join(_REGEXPS) + ')', re.DOTALL)

    _HELPER_PATTERNS = ('indent', 'content', 'title', 'label', 'value', 'term',
                        'descr', 'toctype', 'tocdepth')

    _PARAMETERS = (('parameter', 'page_header', 'HEADER', None,),
                   ('parameter', 'first_page_header', 'FIRST_PAGE_HEADER', None,),
                   ('parameter', 'page_footer', 'FOOTER', None,),
                   ('presentation', 'font_size', 'FONT_SIZE', float),
                   ('presentation', 'font_family', 'FONT_FAMILY', None),
                   ('presentation', 'noindent', 'NOINDENT', bool),
                   )

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
            
        
    def __init__(self):
        self._parameters = {}

    def _parse_sections(self, text, presentation=None):
        root = last = self._Section('__ROOT_SECTION__', None, 0)
        while (1):
            m = self._SECTION_RE.search(text)
            if not m:
                last.content = self._parse_section_content(text)
                break
            last.content = self._parse_section_content(text[:m.start()])
            text = text[m.end():]
            this = self._Section(m.group('title'), m.group('anchor'), len(m.group('level')))
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
        return self._make_sections(root, presentation)

    def _make_sections(self, section, presentation=None):
        subsections = [Section(s.title, self._make_sections(s), anchor=s.anchor,
                               presentation=presentation)
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
            content.append(PreformattedText(m.group(1)))
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
        content = WikiText(groups['content'])
        indent = re.sub(' {0,7}\t', 8*' ', groups['indent'])
        return (self._list_item_order(groups), len(indent), content)
        
    def _finish_list_item(self, stored):
        class _Context:
            def __init__(self, order, indent, content):
                self.order = order
                self.indent = indent
                self.content = content
                self.items = []
            def state(self):
                return (self.order, self.indent, self.content, self.items)
            def make_list(self):
                #_log("**")
                items = [len(i) > 1 and Container(i) or i[0]
                         for i in self.items]
                self.content.append(ItemizedList(items, order=self.order))
                self.items = []
        result = []
        stack = [] # For storing the context between level changes.
        context = _Context(stored[0][0], stored[0][1], result)
        stored.append(('xxx', 0, None))
        for order, indent, content in stored:
            #_log("====", content, indent, order, len(stack), context.state())
            if indent != context.indent:
                if indent > context.indent:
                    # Save the context and start a new level.
                    stack.append(context)
                    context = _Context(order, indent, context.items[-1])
                else:
                    # Restore the context of the higher level.
                    while indent < context.indent:
                        context.make_list()
                        if stack and stack[-1].indent >= indent:
                            context = stack.pop()
                        else:
                            # That's a bad indentation, but let's not panic.
                            context = _Context(order, indent, context.content)
                #_log("<=>", context.state())
            if context.items and context.order != order:
                context.make_list()
                context.order = order
            if content is not None:
                context.items.append([content])
        assert not stack
        return result

    def _store_field(self, block, groups):
        return (WikiText(groups['label']), WikiText(groups['value']))
        
    def _finish_field(self, stored):
        return (FieldSet(stored),)
    
    def _store_definition(self, block, groups):
        return (WikiText(groups['term']), WikiText(groups['descr']))
        
    def _finish_definition(self, stored):
        return (DefinitionList(stored),)
    
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
                element = getattr(self, '_make_'+type)(block, groups)
                if element is not None:
                    content.append(element)
        if unfinished:
            content.extend(finish(*unfinished))
        return content

    def _make_paragraph(self, block, groups):
        text = self._COMMENT_MATCHER.sub("", block).strip()
        if text:
            return Paragraph(WikiText(text))
        else:
            return None
    
    def _make_table(self, block, groups):
        def align(cell):
            length = len(cell)
            if length - len(cell.lstrip()) > length - len(cell.rstrip()):
                return TableCell.RIGHT
            else:
                return None
        lines = block.strip().splitlines()
        # When all cells of the first row are bold or empty, they are considered headings.
        headings = [cell.strip() for cell in lines[0].split('|')[1:-1]]
        if False not in [not h or h.startswith("*") and h.endswith("*") for h in headings]:
            del lines[0]
            rows = [TableRow([TableHeading(FormattedText(h and h[1:-1])) for h in headings])]
        else:
            rows = []
        rows += [TableRow([TableCell(FormattedText(cell.strip()), align=align(cell.expandtabs())) 
                           for cell in line.split('|')[1:-1]])
                 for line in lines]
        return Table(rows)

    def _make_toc(self, block, groups):
        title = groups['title']
        cls = groups['toctype'] in ('NodeIndex', 'NTOC') and NodeIndex or TableOfContents
        d = groups['tocdepth'] and int(groups['tocdepth']) or None
        return cls(title=title, depth=d)

    def _make_rule(self, block, groups):
        return HorizontalSeparator()
    
    def _list_item_order(self, groups):
        t = groups.get('type')
        if not t:
            return None
        elif t in ('*', '-'):
            return None
        elif t[0].isalpha():
            if t.lower() == t:
                return ItemizedList.LOWER_ALPHA
            else:
                return ItemizedList.UPPER_ALPHA
        else:
            return ItemizedList.NUMERIC

    def _parse_parameters(self, text):
        parameters = {}
        presentation = Presentation()
        def add_parameter(kind, name, value, function):
            if function is not None:
                value = function(value)
            if kind == 'parameter':
                parameters[name] = Container(self._parse_sections(value))
            elif kind == 'presentation':
                setattr(presentation, name, value)
            else:
                raise Exception("Program error", kind)
        def cut_off(text, start, end):
            return text[:start] + text[end:]
        for kind, name, identifier, function in self._PARAMETERS:
            # Only single occurrence supported for now
            match = re.search('^#\+%s: ([^\n]*)(\n|$)' % (identifier,), text, re.MULTILINE)
            if match:
                add_parameter(kind, name, match.group(1), function)
                text = cut_off(text, match.start(), match.end())
            else:
                start_match = re.search('^#\+BEGIN_%s *(\n|$)' % (identifier,), text, re.MULTILINE)
                if start_match:
                    end_match = re.search('^#\+END_%s *(\n|$)' % (identifier,), text, re.MULTILINE)
                    if end_match and end_match.start() >= start_match.end():
                        add_parameter(kind, name, text[start_match.end():end_match.start()], function)
                        text = cut_off(text, start_match.start(), end_match.end())
        return parameters, presentation, text

    def parameters(self):
        """Return dictionary of document parameters.

        The dictionary consists from some keyword arguments of
        'ContentNode' constructor.

        The parameters are instantiated only after 'parse()' method gets called.

        """
        return self._parameters
        
    def parse(self, text):
        assert isinstance(text, (str, unicode)), text
        self._parameters, presentation, content_text = self._parse_parameters(text)
        sections = self._parse_sections(content_text, presentation=presentation)
        return sections


class MacroParser(object):
    """Simple text macro parser.

    Macro parser is designed to be applied on structured text source before
    structured text parsing (using 'Parser'), but it can be used on any
    reasonable text format which doesn't interfer with the macro syntax.

    The method 'parse()' takes text on input, expands any macros within this
    text and returns the resulting text on output.

    Two macros are currently supported:

      * Conditional text
      * Inclusion

    Conditional text syntax:

    @if condition
    Text for condition evaluated as true.
    @else
    Optional text for false condition.
    @endif

    The condition is by default a python expression using 'globals' passed to
    parser constructor, but you may also use the 'evaluate' parser constructor
    to supply any condition evaluation method you wish.

    Inclusion syntax:

    @include foo

    The default inclusion method is to replace the macro with the value of
    given variable from 'globals' passed to parser constructor.  identifier
    ('foo' in this case)

    The @ sign marking the macro must always start the line.

    """
    _CONDITION_REGEX = re.compile(r'(?m)^(@(?:if .+|else|endif))\s*?$\r?\n?')
    _INCLUDE_REGEX = re.compile(r'(?m)^@include (.*)$')

    class _ConditionalText(object):
        def __init__(self, evaluate, condition, parent=None):
            self._evaluate = evaluate
            self._condition = condition
            self.parent = parent
            self._state = True
            self._content = {True: [], False: []}

        def switch(self):
            self._state = False

        def append(self, content):
            self._content[self._state].append(content)

        def __str__(self):
            try:
                result = self._evaluate(self._condition)
            except Exception, e:
                return e.__class__.__name__+': '+unicode(e)
            else:
                return ''.join([unicode(x) for x in self._content[bool(result)]])

    def __init__(self, globals=None, evaluate=None, include=None):
        """Arguments:
        
          globals -- dictionary of variables used by default inclusion and
            evaluation methods.
          evaluate -- None for the default evaluation method or a function of
            one argument (the conditionalal expression as a string) returning a
            boolean result of custom expression evaluation.
          include -- None for the default inclusion method or a function of one
            argument (the @include macro argument as a string) returning a
            string value to replace given inclusion macro.

        """
        self._globals = globals or {}
        self._evaluate = evaluate or self._default_evaluate
        self._include = include or self._default_include

    def _default_evaluate(self, expr):
        safe_builtins = ('False', 'None', 'True', 'abs', 'all', 'any', 'bool', 'chr', 'cmp',
                         'complex', 'dict', 'divmod', 'float', 'hash', 'hex', 'id',
                         'isinstance', 'int', 'len', 'list', 'long', 'max', 'min', 'oct', 'ord',
                         'pow', 'range', 'repr', 'reversed', 'round', 'set', 'slice', 'sorted',
                         'str', 'sum', 'tuple', 'unichr', 'unicode', 'zip')
        globals = dict(self._globals, __builtins__=None)
        for builtin in safe_builtins:
            globals[builtin] = __builtins__[builtin]
        return eval("bool(%s)" % expr, globals, {})

    def _default_include(self, name):
        try:
            return unicode(self._globals[name])
        except KeyError:
            return ''

    def parse(self, text):
        """Return the text with all macros processed."""
        text = self._INCLUDE_REGEX.sub(lambda m: self._include(m.group(1).strip()), text)
        tokens = self._CONDITION_REGEX.split(text)
        result = current = self._ConditionalText(self._evaluate, True)
        for t in tokens:
            if t.startswith('@if'):
                new = self._ConditionalText(self._evaluate, t[4:].strip(), parent=current)
                current.append(new)
                current = new
            elif t == '@else':
                current.switch()
            elif t == '@endif' and current.parent is not None:
                current = current.parent
            else:
                current.append(t)
        return unicode(result)


def add_processing_info(exception, caption, information):
    """Add processing info to a given exception.

    This function is used to add more informatioin to an exception during its
    propagation.
    
    If the exception is a 'ProcessingError' instance, the proper mechanism is
    followed.  Raising 'ProcessingError' in the place, where the error is
    detected should be always prefered.  A special attribute
    '_lcg_processing_details' is added to other exception types.  This hack
    allows us to to add processing information to any exception, which is
    mostly useful for exeptions raised in old code, which did not use
    'ProcessingError'.

    See 'ProcesingError' for more information and for the meaning of the
    arguments.

    """
    if isinstance(exception, ProcessingError):
        exception.add_info(caption, information)
    else:
        if not hasattr(exception, '_lcg_processing_details'):
            exception._lcg_processing_details = []
        exception._lcg_processing_details.append((caption, information))
    
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
   
