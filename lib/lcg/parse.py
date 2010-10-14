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

import copy
import os
import re
import types

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
    

class OldParser(object):
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

    _MATCHER = re.compile(('(?:@(?P<halign>center|centre|left|right)\r?\n)?(?:' +
                           '|'.join(_REGEXPS) + ')'),
                          re.DOTALL)
    _HALIGN_MATCHER = re.compile('@(center|centre|left|right)\r?\n', re.MULTILINE)

    _HELPER_PATTERNS = ('indent', 'content', 'title', 'label', 'value', 'term',
                        'descr', 'toctype', 'tocdepth')

    _PARAMETERS = (('parameter', 'page_header', 'HEADER', None,),
                   ('parameter', 'first_page_header', 'FIRST_PAGE_HEADER', None,),
                   ('parameter', 'page_footer', 'FOOTER', None,),
                   ('presentation', 'font_size', 'FONT_SIZE', float,),
                   ('presentation', 'font_name', 'FONT_NAME', None,),
                   ('presentation', 'font_family', 'FONT_FAMILY', None,),
                   ('presentation', 'heading_font_family', 'HEADING_FONT_FAMILY', None,),
                   ('presentation', 'noindent', 'NOINDENT', bool,),
                   ('presentation', 'line_spacing', 'LINE_SPACING', float,),
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
        pass

    def _parse_sections(self, text):
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
        return self._make_sections(root)

    def _make_sections(self, section):
        subsections = [Section(s.title, self._make_sections(s), anchor=s.anchor)
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
        match = self._HALIGN_MATCHER.match(text)
        if match:
            identifier = match.group(1)
            if identifier in ('center', 'centre',):
                halign = HorizontalAlignment.CENTER
            elif identifier == 'left':
                halign = HorizontalAlignment.LEFT
            elif identifier == 'right':
                halign = HorizontalAlignment.RIGHT                
            text = text[match.end():]
        else:
            halign = None
        match = self._MATCHER.match(text)
        if match:
            found = [(key, match.groupdict())
                     for key, m in match.groupdict().items()
                     if m and not key in self._HELPER_PATTERNS]
            result = (text, found[0][0], dict(found[0][1]))
        else:
            result = (text, 'paragraph', {})
        result[2]['halign'] = halign
        return result

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
            if len(piece.strip()) == 0:
                continue
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
            paragraph = Paragraph(WikiText(text), halign=groups.get('halign'))
        else:
            paragraph = None
        return paragraph
    
    def _make_table(self, block, groups):
        global_alignments = {}
        def align(column_number, cell):
            alignment = global_alignments.get(column_number)
            if alignment is not None:
                return alignment
            length = len(cell)
            if length - len(cell.lstrip()) > length - len(cell.rstrip()):
                return TableCell.RIGHT
            else:
                return None
        def horizontal_rule(line):
            return line and line[0][:1] == '-'
        table_rows = []
        lines = [line.split('|')[1:-1] for line in block.strip().splitlines()]
        # Check for specification column in the table
        data_column_start = 0
        nonempty_seen = False
        spec_lines = []
        for line in lines:
            if not line or horizontal_rule(line):
                continue
            cell = line[0].strip()
            if cell not in ('', '/', '#',):
                break
            if cell:
                nonempty_seen = True
                if cell == '/':
                    spec_lines.append([cell.strip() for cell in line[1:]])
        else:
            if nonempty_seen:
                data_column_start = 1
        # Vertical bars, global alignments, widths
        bars = []
        global_widths = {}
        alignment_mapping = {'c': TableCell.CENTER, 'l': TableCell.LEFT, 'r': TableCell.RIGHT}
        matcher = re.compile('<([clr]?)([0-9]*)>')
        if data_column_start:
            for line in spec_lines:
                line_alignments = []
                line_widths = []
                for i in range(len(line)):
                    width = None
                    cell = line[i]
                    if not cell:
                        continue
                    if cell in ('<', '<>',):
                        bars.append(i)
                    if cell in ('>', '<>',):
                        bars.append(i+1)
                    match = matcher.match(cell)
                    if match:
                        alignment_char = match.group(1)
                        alignment = alignment_mapping.get(alignment_char)
                        if alignment is not None:
                            global_alignments[i] = alignment
                        width = match.group(2) or None
                        if width is not None:
                            try:
                                width = UFont(float(width))
                            except ValueError:
                                width = None
                        global_widths[i] = width
        if all([w is None for w in global_widths.values()]):
            column_widths = None
        else:
            column_widths = [global_widths[i] for i in range(len(global_widths))]
        # Prepare parameters
        previous_line = None
        last_line = None
        line_above = 0
        last_line_below = 0
        n = len(lines) - 1
        while n >= 0 and horizontal_rule(lines[n]):
            last_line_below += 1
            n -= 1
        if n >= 0:
            last_line = lines[n]
        # Process table lines
        for line in lines:
            if horizontal_rule(line):
                line_above += 1
            elif data_column_start and line and line[0].strip() == '/':
                continue
            else:
                row_cells = []
                i = 0
                for cell in line[data_column_start:]:
                    row_cells.append(TableCell(FormattedText(cell.strip()),
                                               align=align(i, cell.expandtabs())))
                    i += 1
                if previous_line is None:
                    # When all cells of the first row are bold or empty, they are considered headings.
                    headings = [cell.strip() for cell in line[data_column_start:]]
                    if all([not h or h.startswith("*") and h.endswith("*") for h in headings]):
                        row_cells = [TableHeading(FormattedText(h and h[1:-1])) for h in headings]
                if line is last_line:
                    line_below = last_line_below
                else:
                    line_below = 0
                iterated = data_column_start and line[0].strip() == '#'
                table_rows.append(TableRow(row_cells, line_above=line_above, line_below=line_below,
                                           iterated=iterated))
                line_above = 0
                previous_line = line
        return Table(table_rows, bars=bars, column_widths=column_widths,
                     halign=groups.get('halign'))

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

    def _parse_parameters(self, text, parameters=None):
        presentation = Presentation()
        def add_parameter(kind, name, value, function):
            if function is not None:
                value = function(value)
            if kind == 'parameter':
                if parameters is not None:
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
        if parameters is not None:
            parameters['presentation'] = presentation
        return text
        
    def parse(self, text, parameters=None):
        assert isinstance(text, (str, unicode)), text
        content_text = self._parse_parameters(text, parameters)
        sections = self._parse_sections(content_text)
        return sections


class NewParser(object):
    """Structured text (wiki) document parser.

    This parser parses the structure of the document and builds the
    corresponding 'Content' element hierarchy.  This parser doesn't care about
    inline markup at all.  Only higher-level constructs are recognized here.
    Formatting the inline markup is done by the 'MarkupFormatter' on LCG output
    (as opposed to parsing, which is done on LCG input).

    """
    _ALIGNMENT_MATCHER = re.compile(r'@(center|centre|left|right) *$', re.MULTILINE)
    _HRULE_MATCHER = re.compile(r'^----+ *$', re.MULTILINE)
    _TOC_MATCHER = re.compile(r'(?:(?P<title>[^\r\n]+)[\t ]+)?\@(?P<toctype>(N?TOC|NodeIndex))(\((?P<tocdepth>\d+)\))?\@ *')
    _TABLE_MATCHER = re.compile(r'\|.*\| *$', re.MULTILINE)
    _CELL_ALIGNMENT_MATCHER = re.compile(r'<([clr]?)([0-9]*)>')
    _CELL_ALIGNMENT_MAPPING = {'c': TableCell.CENTER, 'l': TableCell.LEFT, 'r': TableCell.RIGHT}
    _COMMENT_MATCHER = re.compile('^#[^\n]*(\n|$)', re.MULTILINE)
    _SECTION_MATCHER = re.compile((r'^(?P<level>=+) (?P<title>.*) (?P=level)' +
                                   r'(?:[\t ]+(?:\*|(?P<anchor>[\w\d_-]+)))? *$'),
                                  re.MULTILINE)
    _LINE_MATCHER = re.compile(r'^( *)([^\n\r]*)(\r?\n\r?|$)', re.MULTILINE)
    _LITERAL_MATCHER = re.compile(r'^-----+[ \t]*\r?\n(.*?)^-----+ *$', re.DOTALL|re.MULTILINE)
    _PARAMETER_MATCHER = re.compile(r'@parameter +([a-z_]+)( +.*)?$', re.MULTILINE)
    _FIELD_MATCHER = re.compile(r':(?P<label>[^:]*\S):[\t ]*' +
                                r'(?P<value>[^\r\n]*(?:\r?\n[\t ]+[^\r\n]+)*)\r?\n')
    _DEFINITION_MATCHER = re.compile(r'(?P<term>\S[^\r\n]*)\r?\n' + 
                                     r'(?P<descr>([\t ]+[^\r\n]+\r?\n)*([\t ]+[^\r\n]+\r?\n?))')
    _LIST_MATCHER = re.compile(r'( *)\(?(?:\*|-|(?:[a-z]|\d+|#)(?:\)|\.)) +')
    _TAB_MATCHER = re.compile(r'^\t')
    
    _PARAMETERS = {'header': ('parameter', 'page_header', None,),
                   'first_page_header': ('parameter', 'first_page_header', None,),
                   'footer': ('parameter', 'page_footer', None,),
                   'font_size': ('presentation', 'font_size', float,),
                   'font_name': ('presentation', 'font_name', None,),
                   'font_family': ('presentation', 'font_family', None,),
                   'heading_font_family': ('presentation', 'heading_font_family', None,),
                   'noindent': ('presentation', 'noindent', bool,),
                   'line_spacing': ('presentation', 'line_spacing', float,),
                   }
    
    def __init__(self):
        self._processors = (self._alignment_processor,
                            self._field_processor,
                            self._section_processor,
                            self._literal_processor,
                            self._hrule_processor,
                            self._toc_processor,
                            self._table_processor,
                            self._list_processor,
                            self._definition_processor,
                            self._parameters_processor,
                            self._paragraph_processor,
                            )

    def _prune_kwargs(self, kwargs, prune):
        kwargs = copy.copy(kwargs)
        for k in prune:
            try:
                del kwargs[k]
            except:
                pass
        return kwargs

    def _alignment_processor(self, text, position, **kwargs):
        match = self._ALIGNMENT_MATCHER.match(text[position:])
        if not match:
            return None
        identifier = match.group(1)
        if identifier in ('center', 'centre',):
            halign = HorizontalAlignment.CENTER
        elif identifier == 'left':
            halign = HorizontalAlignment.LEFT
        elif identifier == 'right':
            halign = HorizontalAlignment.RIGHT                
        position = self._find_next_block(text, position + match.end())
        kwargs = self._prune_kwargs(kwargs, ('halign',))
        return self._parse(text, position, halign=halign, **kwargs)

    def _field_processor(self, text, position, **kwargs):
        if text[position] != ':':
            return None
        fields = []
        while True:
            match = self._FIELD_MATCHER.match(text[position:])
            if not match:
                break
            groups = match.groupdict()
            fields.append((WikiText(groups['label']), WikiText(groups['value']),))
            position += match.end()
        return FieldSet(fields), position

    def _definition_processor(self, text, position, **kwargs):
        match = self._DEFINITION_MATCHER.match(text[position:])
        if not match:
            return None
        definitions = []
        while match:
            groups = match.groupdict()
            definitions.append((WikiText(groups['term']), WikiText(groups['descr']),))
            position += match.end()
            match = self._DEFINITION_MATCHER.match(text[position:])
        return DefinitionList(definitions), position
        
    def _hrule_processor(self, text, position, **kwargs):
        match = self._HRULE_MATCHER.match(text[position:])
        if not match:
            return None
        return HorizontalSeparator(), position + match.end()

    def _section_processor(self, text, position, section_level=0, **kwargs):
        # section_level is ignored now, but it may become useful if we want to
        # restrict section levels by some rules.
        match = self._SECTION_MATCHER.match(text[position:])
        if not match:
            return None
        title = match.group('title')
        anchor = match.group('anchor')
        level = len(match.group('level'))
        section_content = []
        size = len(text)
        position += match.end()
        kwargs = self._prune_kwargs(kwargs, ('section_level',))
        while True:
            position = self._find_next_block(text, position)
            if position >= size:
                break
            match = self._SECTION_MATCHER.match(text[position:])
            if match and len(match.group('level')) <= level:
                break
            content, position = self._parse(text, position, section_level=level, **kwargs)
            section_content.append(content)
        container = Container(section_content)
        return Section(title=title, content=container, anchor=anchor), position

    def _literal_processor(self, text, position, **kwargs):
        match = self._LITERAL_MATCHER.match(text[position:])
        if not match:
            return None
        content = PreformattedText(match.group(1))
        return content, position + match.end()

    def _toc_processor(self, text, position, **kwargs):
        match = self._TOC_MATCHER.match(text[position:])
        if not match:
            return None
        groups = match.groupdict()
        title = groups['title']
        if groups['toctype'] in ('NodeIndex', 'NTOC'):
            class_ = NodeIndex
        else:
            class_ = TableOfContents
        depth = None
        if groups['tocdepth']:
            depth = int(groups['tocdepth'])
        return class_(title=title, depth=depth), position + match.end()

    def _list_processor(self, text, position, indentation=0, extra_indentation=0, **kwargs):
        size = len(text)
        match = self._LIST_MATCHER.match(text[position:])
        if not match:
            return None
        def list_kind(text, position):
            char = text[position]
            if char in ('*', '-',):
                return None
            elif char in string.digits:
                return ItemizedList.NUMERIC
            elif char == char.lower():
                return ItemizedList.LOWER_ALPHA
            else:
                return ItemizedList.UPPER_ALPHA
        items = []
        kind = list_kind(text, position + match.end(1))
        list_indentation = extra_indentation + match.end(1)
        inner_indentation = extra_indentation + match.end()
        kwargs = self._prune_kwargs(kwargs, ('processors', 'compressed',))
        while True:                     # consume list items
            position += match.end()
            inner_extra_indentation = inner_indentation
            item_content = []
            while True:                 # consume content of a single list item
                content, position = self._parse(text, position, indentation=inner_indentation,
                                                extra_indentation=inner_extra_indentation,
                                                processors=(self._list_processor,
                                                            self._paragraph_processor,),
                                                compressed=True,
                                                **kwargs)
                inner_extra_indentation = 0
                item_content.append(content)
                if position >= size:
                    break
                position = self._find_next_block(text, position)
                current_indentation = 0
                while current_indentation < inner_indentation and position < size:
                    if text[position+current_indentation] == ' ':
                        current_indentation += 1
                    else:
                        break
                if current_indentation < inner_indentation: # no inner content anymore
                    break
            items.append(Container(item_content))
            if position >= size or current_indentation != list_indentation: # no next item
                break
            match = self._LIST_MATCHER.match(text[position:])
            if not match:               # this is not a (next) list item
                break
            if list_kind(text, position + match.end(1)) != kind: # list kind switch => start new list
                break
        return ItemizedList(items, order=kind), position

    def _table_processor(self, text, position, halign=None, **kwargs):
        if not self._TABLE_MATCHER.match(text[position:]):
            return None
        bars = None
        global_widths = None
        global_alignments = {}
        def align(column_number, cell):
            alignment = global_alignments.get(column_number)
            if alignment is not None:
                return alignment
            length = len(cell)
            if length - len(cell.lstrip()) > length - len(cell.rstrip()):
                return TableCell.RIGHT
            else:
                return None
        table_rows = []
        line_above = 0
        while text[position:position+1] == '|':
            # Get the line
            start_position = position = position + 1
            eol = text[start_position:].find('\n')
            if eol >= 0:
                position += eol + 1
                if text[position-2] != '\r' and text[position:position+1] == '\r': # Mac
                    position += 1
            else:
                position = len(text)
            # Rule?
            if text[start_position:start_position+1] == '-':
                line_above += 1
                continue
            # Examine the cells
            text_cells = text[start_position:position].split('|')[:-1]
            stripped_cells = [cell.strip() for cell in text_cells]
            # Is it a bar specification?
            if bars is None:
                maybe_bars = []
                for i in range(len(stripped_cells)):
                    cell = stripped_cells[i]
                    if not cell:
                        continue
                    if cell not in ('<', '<>', '>',):
                        break
                    if cell in ('<', '<>',):
                        maybe_bars.append(i)
                    if cell in ('>', '<>',):
                        maybe_bars.append(i+1)
                else:
                    bars = maybe_bars
                    continue
            # Is it an alignment specification?
            if global_widths is None:
                maybe_global_alignments = {}
                maybe_global_widths = {}
                for i in range(len(stripped_cells)):
                    cell = stripped_cells[i]
                    if not cell:
                        continue
                    match = self._CELL_ALIGNMENT_MATCHER.match(cell)
                    if match:
                        alignment_char = match.group(1)
                        alignment = self._CELL_ALIGNMENT_MAPPING.get(alignment_char)
                        if alignment is not None:
                            maybe_global_alignments[i] = alignment
                        width = match.group(2) or None
                        if width is not None:
                            try:
                                width = UFont(float(width))
                            except ValueError:
                                width = None
                        maybe_global_widths[i] = width
                    else:
                        break
                else:
                    global_alignments = maybe_global_alignments
                    global_widths = maybe_global_widths
                    continue
            # Is it a heading?
            if (not table_rows and
                all([not cell or cell.startswith("*") and cell.endswith("*")
                     for cell in stripped_cells])):
                row_cells = [TableHeading(FormattedText(cell and cell[1:-1]))
                             for cell in stripped_cells]
            else:
                # Well, it's just a standard line
                row_cells = []
                i = 0
                for cell in text_cells:
                    row_cells.append(TableCell(FormattedText(cell.strip()),
                                               align=align(i, cell.expandtabs())))
                    i += 1
            table_rows.append(TableRow(row_cells, line_above=line_above))
            line_above = 0
        if line_above > 0 and table_rows:
            table_rows[-1].set_line_below(line_above)
        # Make and return the content object
        if bars is None:
            bars = ()
        if global_widths is None or all([w is None for w in global_widths.values()]):
            column_widths = None
        else:
            column_widths = [global_widths[i] for i in range(len(global_widths))]
        content = Table(table_rows, bars=bars, column_widths=column_widths, halign=halign)
        return content, position

    def _parameters_processor(self, text, position, parameters=None, presentation=None,
                              **kwargs):
        match = self._PARAMETER_MATCHER.match(text[position:])
        if not match:
            return None
        identifier = match.group(1)
        value = match.group(2)
        position += match.end()
        while text[position:position+1] in ('\r', '\n',):
            position += 1
        if value:
            value = value.strip()
        if not value:
            match = re.search('^@end %s *$' % (identifier,), text[position:], re.MULTILINE)
            if match:
                value = text[position:position+match.start()].strip()
                position += match.end()
            else:                       # unfinished parameter
                return None, position
        info = self._PARAMETERS.get(identifier)
        if info is not None:
            kind, name, function = info
            if function is not None:
                value = function(value)
            if kind == 'parameter':
                if parameters is not None:
                    parameters[name] = Container(Parser().parse(value))
            elif kind == 'presentation':
                setattr(presentation, name, value)
            else:
                raise Exception("Program error", kind)
        return None, position

    def _paragraph_processor(self, text, position, halign=None, indentation=0, extra_indentation=0,
                             compressed=False, **kwargs):
        next_position = self._skip_content(text, position, indentation=indentation,
                                           extra_indentation=extra_indentation,
                                           compressed=compressed)
        if next_position == position:
            return None
        content = Paragraph(WikiText(text[position:next_position]), halign=halign)
        return content, next_position

    def _strip_comments(self, text):
        stripped_text = ''
        while True:
            match = self._COMMENT_MATCHER.search(text)
            if not match:
                break
            stripped_text += text[:match.start()]
            text = text[match.end():]
        stripped_text += text
        return stripped_text

    def _expand_tabs(self, text):
        # Well, non-linear time complexity here
        while True:
            match = self._TAB_MATCHER.search(text)
            if not match:
                break
            text = text[:match.start()] + ' '*8 + text[match.end():]
        return text

    def _skip_content(self, text, position, indentation=0, extra_indentation=0, compressed=False):
        first_line = True
        while True:
            if self._LITERAL_MATCHER.match(text[position:]): # they don't have to be separated by blank lines
                break
            match = self._LINE_MATCHER.match(text[position:])
            if not match:               # end of text?
                break
            if not match.group(2):      # blank line?
                break
            if match.end(1) - match.start(1) + extra_indentation < indentation: # reduced indentation?
                break
            if compressed and self._LIST_MATCHER.match(text[position:]): # inner list
                break
            position += match.end()
            extra_indentation = 0
        return position
        
    def _find_next_block(self, text, position):
        start_position = position
        size = len(text)
        while True:
            if position >= size:
                break
            char = text[position]
            if char not in string.whitespace:
                break
            position += 1
            if char == '\n' or char == '\r':
                start_position = position
        return start_position

    def _parse(self, text, position, parameters, presentation, processors=None, **kwargs):
        assert position > self._old_position, \
               (self._old_position, position, text[position:position+100],)
        if __debug__:
            self._old_position = position
        kwargs = self._prune_kwargs(kwargs, ('parameters', 'presentation',))
        for processor in (processors or self._processors):
            result = processor(text, position, parameters=parameters, presentation=presentation,
                               **kwargs)
            if result is not None:
                if __debug__:
                    position = result[1]
                    assert position >= min(self._old_position + 1, len(text)), \
                           (self._old_position, position, text[position:position+100], processor,)
                return result
        else:
            raise Exception('Unhandled text', text[position:])

    def parse(self, text, parameters=None):
        """Parse given 'text' and return corresponding content.

        The return value is a sequence of 'Content' instances.

        Arguments:

          text -- input structured text, string or unicode
          parameters -- 'None' or dictionary where keyword parameters for
            'ContentNode' constructor can be stored

        """
        assert isinstance(text, basestring), text
        if __debug__:
            self._old_position = -1
        presentation = Presentation()
        text = self._strip_comments(text)
        text = self._expand_tabs(text)
        contents = []
        position = 0
        size = len(text)
        while True:
            position = self._find_next_block(text, position)
            if position >= size:
                break
            content, position = self._parse(text, position, parameters, presentation)
            if content is not None:
                contents.append(content)
            position = self._find_next_block(text, position)
        if parameters is not None:
            parameters['presentation'] = presentation
        return contents


Parser = OldParser


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
   
