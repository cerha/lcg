# -*- coding: utf-8 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2012 Brailcom, o.p.s.
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
import re
import string
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


def _bool(string):
    return string.strip().lower() not in ('0', 'false', 'no',)

class Parser(object):
    """Structured text (wiki) document parser.

    This parser parses the structure of the document and builds the
    corresponding 'Content' element hierarchy.  This parser doesn't care about
    inline markup at all.  Only higher-level constructs are recognized here.
    Formatting the inline markup is done by the 'MarkupFormatter' on LCG output
    (as opposed to parsing, which is done on LCG input).

    """
    _ALIGNMENT_MATCHER = re.compile(r'@(center|centre|left|right) *\r?$', re.MULTILINE)
    _HRULE_MATCHER = re.compile(r'^----+ *\r?$', re.MULTILINE)
    _TOC_MATCHER = re.compile(r'(?:(?P<title>[^\r\n]+)[\t ]+)?\@(?P<toctype>(N?TOC|NodeIndex))(\((?P<tocdepth>\d+)\))?\@ *')
    _TABLE_MATCHER = re.compile(r'\|.*\| *\r?$', re.MULTILINE)
    _CELL_ALIGNMENT_MATCHER = re.compile(r'<([clr]?)([0-9]*)>')
    _CELL_ALIGNMENT_MAPPING = {'c': TableCell.CENTER, 'l': TableCell.LEFT, 'r': TableCell.RIGHT}
    _COMMENT_MATCHER = re.compile('^#[^\r\n]*\r?(\n|$)', re.MULTILINE)
    _SECTION_MATCHER = re.compile((r'^(?P<level>=+) (?P<title>.*) (?P=level)' +
                                   r'(?:[\t ]+(?:\*|(?P<anchor>[\w\d_-]+)))? *\r?$'),
                                  re.MULTILINE)
    _LINE_MATCHER = re.compile(r'^([\t ]*)([^\n\r]*)\r?(\n|$)', re.MULTILINE)
    _LITERAL_MATCHER = re.compile(r'^-----+[ \t]*\r?\n(.*?)^-----+ *\r?$', re.DOTALL|re.MULTILINE)
    _VARIABLE_MATCHER = re.compile(r'@define +([a-z_]+)( +.*)?\r?$', re.MULTILINE)
    _PARAMETER_MATCHER = re.compile(r'@parameter +([a-z_]+)( +.*)?\r?$', re.MULTILINE)
    _VSPACE_MATCHER = re.compile(r'@vspace +([0-9]+(\.[0-9]+)?)mm\r?$', re.MULTILINE)
    _FIELD_MATCHER = re.compile(r':(?P<label>[^:]*\S):[\t ]*' +
                                r'(?P<value>[^\r\n]*(?:\r?\n[\t ]+[^\r\n]+)*)\r?$', re.MULTILINE)
    _DEFINITION_MATCHER = re.compile(r'(?P<term>\S[^\r\n]*)\r?\n' + 
                                     r'(?P<description>([\t ]+[^\r\n]+\r?\n)*([\t ]+[^\r\n]+\r?\n?))')
    _LIST_MATCHER = re.compile(r'( *)\(?(?:\*|-|(?:[a-z]|\d+|#)(?:\)|\.)) +')
    _STYLE_MATCHER = re.compile(r'@style +([a-z_]+)[\t ]*\r?$', re.MULTILINE)
    _TAB_MATCHER = re.compile(r'^\t')
    
    _PARAMETERS = {'header': ('parameter', 'page_header', None,),
                   'first_page_header': ('parameter', 'first_page_header', None,),
                   'footer': ('parameter', 'page_footer', None,),
                   'left_footer': ('parameter', 'left_page_footer', None,),
                   'right_footer': ('parameter', 'right_page_footer', None,),
                   'background': ('parameter', 'page_background', None,),
                   'font_size': ('presentation', 'font_size', float,),
                   'font_name': ('presentation', 'font_name', None,),
                   'font_family': ('presentation', 'font_family', None,),
                   'heading_font_family': ('presentation', 'heading_font_family', None,),
                   'noindent': ('presentation', 'noindent', _bool,),
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
                            self._variable_processor,
                            self._style_processor,
                            self._space_processor,
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
                if not fields:
                    return None
                break
            groups = match.groupdict()
            fields.append((FormattedText(groups['label']), FormattedText(groups['value']),))
            position += match.end() + 1
        return FieldSet(fields), position

    def _definition_processor(self, text, position, **kwargs):
        match = self._DEFINITION_MATCHER.match(text[position:])
        if not match:
            return None
        definitions = []
        while match:
            groups = match.groupdict()
            term, description = groups['term'], groups['description']
            old_position = self._old_position
            position += match.end()
            next_position = position
            while True:
                line_match = self._LINE_MATCHER.match(text[position:])
                if (not line_match or
                    (line_match.group(2) and not line_match.group(1)) or
                    line_match.end() == 0):
                    break
                position += line_match.end()
            description += text[next_position:position]
            parsed_description = self.parse(description)
            # Handle backward compatibility with the old structured text constructs
            if (not definitions and
                len(parsed_description) == 1 and
                isinstance(parsed_description[0], ItemizedList)):
                self._old_position = old_position
                return None
            definitions.append((FormattedText(term), Container(parsed_description),))
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
            if content is not None:
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
                                                            self._paragraph_processor,
                                                            self._whitespace_processor,),
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
            if len(item_content) == 1:
                element = item_content[0]
                # Hack to prevent ugly list formatting
                if (isinstance(element, Paragraph) and
                    element.halign() is None and
                    len(element.content()) == 1):
                    element = element.content()[0]
                items.append(element)
            else:
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
        re_iterate = re.compile(' *@iterate ')
        while text[position:position+1] == '|':
            iterated = False
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
                    match_iterate = re_iterate.match(cell)
                    if match_iterate:
                        iterated = True
                        cell = cell[match_iterate.end():]
                    row_cells.append(TableCell(FormattedText(cell.strip()),
                                               align=align(i, cell.expandtabs())))
                    i += 1
            table_rows.append(TableRow(row_cells, line_above=line_above, iterated=iterated))
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
            match = re.search('^@end %s *\r?$' % (identifier,), text[position:], re.MULTILINE)
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

    def _variable_processor(self, text, position, **kwargs):
        match = self._VARIABLE_MATCHER.match(text[position:])
        if not match:
            return None
        identifier = match.group(1)
        value = match.group(2)
        position += match.end()
        while text[position:position+1] in ('\r', '\n',):
            position += 1
        if value:
            value = value.strip()
            variable_content = FormattedText(value)
        else:
            match = re.search('^@end %s *\r?$' % (identifier,), text[position:], re.MULTILINE)
            if match:
                value = text[position:position+match.start()].strip()
                position += match.end()
            else:                       # unfinished variable
                return None, position
            variable_content = Container(self.parse(value))
        content = SetVariable(str(identifier), variable_content)
        return content, position

    def _style_processor(self, text, position, **kwargs):
        match = self._STYLE_MATCHER.match(text[position:])
        if not match:
            return None
        name = match.group(1)
        text_start = position + match.end()
        while text[text_start:text_start+1] in ('\r', '\n',):
            text_start += 1
        match = re.search('^@end style *\r?$', text[text_start:], re.MULTILINE)
        if not match:
            return None, position
        text_end = text_start + match.start()
        end_position = text_start + match.end()
        cut_text = text[:text_end]
        position = text_start
        content_list = []
        position = self._find_next_block(text, position)
        while True:
            if position >= text_end:
                break
            content, position = self._parse(cut_text, position, **kwargs)
            if content is None:
                break
            content_list.append(content)
            if position >= text_end:
                break
            position = self._find_next_block(text, position)
        if not content_list:
            return None, end_position
        container = Container(content_list, name=name)
        return container, end_position

    def _space_processor(self, text, position, **kwargs):
        match = self._VSPACE_MATCHER.match(text[position:])
        if not match:
            return None
        value = float(match.group(1))
        position += match.end()
        content = VSpace(UMm(value))
        return content, position
        
    def _paragraph_processor(self, text, position, halign=None, indentation=0, extra_indentation=0,
                             compressed=False, **kwargs):
        next_position = self._skip_content(text, position, indentation=indentation,
                                           extra_indentation=extra_indentation,
                                           compressed=compressed)
        if next_position == position:
            return None
        content = Paragraph(FormattedText(text[position:next_position]), halign=halign)
        return content, next_position

    def _whitespace_processor(self, text, position, **kwargs):
        next_position = position
        while text[next_position:] and text[next_position] in string.whitespace:
            next_position += 1
        content = Paragraph(FormattedText(''))
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
        while True:
            if (self._LITERAL_MATCHER.match(text[position:]) or
                self._LIST_MATCHER.match(text[position:])):
                # some blocks don't have to be separated by blank lines
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
                start_position = position
                break
            char = text[position]
            if char not in string.whitespace:
                break
            position += 1
            if char == '\n' or char == '\r':
                start_position = position
        return start_position

    def _parse(self, text, position, processors=None, **kwargs):
        assert position > self._old_position, \
               (self._old_position, position, text[position:position+100],)
        if __debug__:
            self._old_position = position
        for processor in (processors or self._processors):
            result = processor(text, position, **kwargs)
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
          parameters -- 'None' or a dictionary where keyword parameters for
            'ContentNode' constructor are stored to

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
        position = self._find_next_block(text, position)
        while True:
            if position >= size:
                break
            content, position = self._parse(text, position, parameters=parameters,
                                            presentation=presentation)
            if content is not None:
                contents.append(content)
            position = self._find_next_block(text, position)
        if parameters is not None:
            parameters['presentation'] = presentation
        return contents


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
    _INCLUDE_REGEX = re.compile(r'(?m)^@include (.*)\r?$')

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
            except Exception as e:
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
        if isinstance(x, FormattedText):
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
   
