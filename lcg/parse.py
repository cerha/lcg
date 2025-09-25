# -*- coding: utf-8 -*-

# Copyright (C) 2004-2017 OUI Technology Ltd.
# Copyright (C) 2019-2021 Tomáš Cerha <t.cerha@gmail.com>
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

from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from future import standard_library
from builtins import chr
from builtins import map
from builtins import range

import copy
import html.parser
import html.entities
import re
import string
import sys
import xml.etree.ElementTree

import lcg

standard_library.install_aliases()
unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


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
    corresponding 'Content' element hierarchy.  Complete documents (including
    block level constructs, such as paraghaphs, sections, itemized lists, etc
    are processed by the method 'parse()'.  Inline markup (text emphasizing,
    links, substitutions) are processed by a separate method
    'parse_inline_markup().

    """
    _ALIGNMENT_MATCHER = re.compile(r'@(center|centre|left|right) *\r?$', re.MULTILINE)
    _HRULE_MATCHER = re.compile(r'^----+ *\r?$', re.MULTILINE)
    _TOC_MATCHER = re.compile(r'(?:(?P<title>[^\r\n]+)[\t ]+)?\@(?P<toctype>(N?TOC|NodeIndex))'
                              r'(\((?P<tocdepth>\d+)\))?\@ *')
    _TABLE_MATCHER = re.compile(r'\|.*\| *\r?$', re.MULTILINE)
    _CELL_ALIGNMENT_MATCHER = re.compile(r'<([clr]?)([0-9]*)>')
    _CELL_ALIGNMENT_MAPPING = {'c': lcg.TableCell.CENTER, 'l': lcg.TableCell.LEFT,
                               'r': lcg.TableCell.RIGHT}
    _COMMENT_MATCHER = re.compile('^#[^\r\n]*\r?(\n|$)', re.MULTILINE)
    _SECTION_MATCHER = re.compile((r'^(?P<level>=+) (?P<collapsible>>\+? +)?'
                                   r'(?P<title>.*) (?P=level)'
                                   r'(?:[\t ]+(?:\*|(?P<not_in_toc>\!)?'
                                   r'(?P<section_id>[\w\d_-]+)))?'
                                   r'(?P<section_classes>(?:[\t ]+\.[\w\d_-]+)*) *\r?$'),
                                  re.MULTILINE)
    _CONTAINER_MATCHER = re.compile((r'^(?P<collapsible>\[(?P<title>[^\]]+)\]\+? +)?'
                                     r'\>(?P<level>\>+)'
                                     r'(?P<id>[ \t]+([ \t]*[#\.=]?[\w\d_-]+)*)?'
                                     r'([ \t]+"(?P<label>[^"]*)")?'
                                     r'[\t ]*\r?$'), re.MULTILINE)
    _CONTAINER_END_MATCHER = [re.compile(r'^\<%s *\r?$' % (r'\<' * i), re.MULTILINE)
                              for i in range(10)]
    _LINE_MATCHER = re.compile(r'^([\t ]*)([^\n\r]*)\r?(\n|$)', re.MULTILINE)
    _LITERAL_MATCHER = re.compile(r'^-----+[ \t]*\r?\n(.*?)^-----+ *\r?$', re.DOTALL | re.MULTILINE)
    _DOCTEST_MATCHER = re.compile(r'(^>>> .+\r?\n)(^(>>>|\.\.\.)[ \t].+\r?\n)*(^[ \t]*\S.*\r?\n)*',
                                  re.MULTILINE)
    _EXERCISE_MATCHER = re.compile(r'^<exercise type=["\']([a-zA-Z]+)["\']>\s*\r?\n'
                                   r'(.*?)^</exercise>\s*\r?$',
                                   re.DOTALL | re.MULTILINE)
    _VARIABLE_MATCHER = re.compile(r'@define +([a-z_]+)( +.*)?\r?$', re.MULTILINE)
    _PARAMETER_MATCHER = re.compile(r'@parameter +([a-z_]+)( +.*)?\r?$', re.MULTILINE)
    _VSPACE_MATCHER = re.compile(r'@vspace +([0-9]+(\.[0-9]+)?)mm\r?$', re.MULTILINE)
    _FIELD_MATCHER = re.compile(r':(?P<label>[^:]*\S):[\t ]*' +
                                r'(?P<value>[^\r\n]*(?:\r?\n[\t ]+[^\r\n]+)*)\r?$', re.MULTILINE)
    _DEFINITION_MATCHER = re.compile(r'(?P<term>\S[^\r\n]*)\r?\n' +
                                     r'(?P<description>([\t ]+\S+\r?\n)*([\t ]+\S+\r?\n?))')
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

    _INLINE_MARKUP = (
        ('newline', '//'),
        ('emphasized', ('/', '/')),
        ('strong', (r'\*', r'\*')),
        ('code', ('=', '=')),
        ('underlined', ('_', '_')),
        ('citation', ('>>', '<<')),
        # Link to an internal or external (http) target via [ ].
        ('link', (r'\['
                  r'(?P<align>[<>])?'  # Left/right Image aligment e.g. [<imagefile], [>imagefile]
                  r'(?P<href>(?!(java|vb)script:)[^\[\]\|\s]*?)'  # The link target e.g. [src]
                  r'(?::(?P<size>\d+x\d+))?'  # Optional explicit image (or video) size
                                              # e.g. [image.jpg:30x40])
                  r'(?:(?:\s*\|\s*|\s+)'  # Separator (pipe is enabled for backwards compatibility,
                                          # but space is the official separator)
                  r'(?P<label>[^\[\]\|]*))?'  # Label text
                  r'(?:(?:\s*\|\s*)(?P<descr>[^\[\]]*))?'  # Description after |
                                                           # [src Label | Description]
                  r'\]')),
        # Link directly in the text starting with http(s)/ftp://
        ('uri', (r'(?:https?|ftp)://\S+?(?=[\),.:;]*(\s|$))')),  # ?!? SOS!
        ('email', r'\w[\w\-\.]*@\w[\w\-\.]*\w'),
        ('substitution', (r"(?!\\)\$(?P<subst>[a-zA-Z][a-zA-Z_]*(\.[a-zA-Z][a-zA-Z_]*)?" +
                          r"|\{[^\}]+\})")),
        ('comment', r'^#.*'),
        ('dash', r'(^|(?<=\s))--($|(?=\s))'),
        ('nbsp', '~'),
        ('page_number', '@PAGE@'),
        ('total_pages', '@PAGES@'),
        ('escape', r'\\\\(?P<char>[-*@])'),
    )

    _INLINE_MARKUP_PARAMETERS = ('align', 'href', 'label', 'descr', 'subst', 'size', 'char')

    _VIMEO_VIDEO_MATCHER = re.compile(r"https?://(www.)?vimeo.com/(?P<video_id>[0-9]*)")
    _YOUTUBE_VIDEO_MATCHER = re.compile(
        r"https?://(www.)?youtube.com/watch\?v=(?P<video_id>[a-zA-z0-9_-]*)")
    _BLANK_MATCHER = re.compile(r'\s+', re.MULTILINE)

    class _StackEntry(object):

        def __init__(self, name):
            self.name = name
            self.content = []

    def __init__(self):
        self._processors = (self._alignment_processor,
                            self._field_processor,
                            self._section_processor,
                            self._container_processor,
                            self._literal_processor,
                            self._doctest_processor,
                            self._exercise_processor,
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
        regexp = r"(?P<%s>\\*%s)"
        pair_regexp = '|'.join((regexp % ("%s_end", r"(?<=\S)%s(?!\w)"),
                                regexp % ("%s_start", r"(?<!\w)%s(?=\S)")))
        regexps = [pair_regexp % (name, markup[1], name, markup[0])
                   if isinstance(markup, tuple) else regexp % (name, markup)
                   for name, markup in self._INLINE_MARKUP]
        self._inline_markup = re.compile('(?:' + '|'.join(regexps) + ')',
                                         re.MULTILINE | re.UNICODE | re.IGNORECASE)

    def _prune_kwargs(self, kwargs, prune):
        kwargs = copy.copy(kwargs)
        for k in prune:
            try:
                del kwargs[k]
            except KeyError:
                pass
        return kwargs

    def _alignment_processor(self, text, position, **kwargs):
        match = self._ALIGNMENT_MATCHER.match(text[position:])
        if not match:
            return None
        identifier = match.group(1)
        if identifier in ('center', 'centre',):
            halign = lcg.HorizontalAlignment.CENTER
        elif identifier == 'left':
            halign = lcg.HorizontalAlignment.LEFT
        elif identifier == 'right':
            halign = lcg.HorizontalAlignment.RIGHT
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
            fields.append((self.parse_inline_markup(groups['label']),
                           self.parse_inline_markup(groups['value']),))
            position += match.end() + 1
        return lcg.FieldSet(fields), position

    def _definition_processor(self, text, position, **kwargs):
        match = self._DEFINITION_MATCHER.match(text[position:])
        if not match:
            return None
        definitions = []
        while match:
            groups = match.groupdict()
            term, description = groups['term'], groups['description']
            if __debug__:
                old_position = self._old_position
            position += match.end()
            next_position = position
            while True:
                line_match = self._LINE_MATCHER.match(text[position:])
                if ((not line_match or
                     (line_match.group(2) and not line_match.group(1)) or
                     line_match.end() == 0)):
                    break
                position += line_match.end()
            description += text[next_position:position]
            parsed_description = self.parse(description)
            # Handle backward compatibility with the old structured text constructs
            if ((not definitions and
                 len(parsed_description) == 1 and
                 isinstance(parsed_description[0], lcg.ItemizedList))):
                if __debug__:
                    self._old_position = old_position
                return None
            definitions.append((self.parse_inline_markup(term),
                                lcg.Container(parsed_description),))
            match = self._DEFINITION_MATCHER.match(text[position:])
        return lcg.DefinitionList(definitions), position

    def _hrule_processor(self, text, position, **kwargs):
        match = self._HRULE_MATCHER.match(text[position:])
        if not match:
            return None
        return lcg.HorizontalSeparator(), position + match.end()

    def _section_processor(self, text, position, section_level=0, **kwargs):
        # section_level is ignored now, but it may become useful if we want to
        # restrict section levels by some rules.
        match = self._SECTION_MATCHER.match(text[position:])
        if not match:
            return None
        title = match.group('title')
        section_id = match.group('section_id')
        section_classes = [x.lstrip('.') for x in match.group('section_classes').strip().split()]
        in_toc = not match.group('not_in_toc')
        level = len(match.group('level'))
        section_content = []
        size = len(text)
        position += match.end()
        kwargs = self._prune_kwargs(kwargs, ('section_level',))
        element_kwargs = {}
        if match.group('collapsible'):
            element = lcg.CollapsibleSection
            if match.group('collapsible').strip().endswith('+'):
                element_kwargs['collapsed'] = False
        else:
            element = lcg.Section
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
        return element(title=title, heading=self.parse_inline_markup(title),
                       content=lcg.Container(section_content),
                       id=section_id, name=tuple(section_classes) or ('default-section',),
                       in_toc=in_toc, **element_kwargs), position

    def _container_processor(self, text, position, section_level=0, **kwargs):
        start = self._CONTAINER_MATCHER.match(text[position:])
        if not start:
            return None
        position += start.end()
        level = len(start.group('level'))
        end = self._CONTAINER_END_MATCHER[level].search(text[position:])
        if not end:
            return None
        content = self.parse(text[position:position + end.start()])
        position += end.end()
        id_, role, classes = None, None, []
        if start.group('id'):
            for x in start.group('id').strip().split():
                if x.startswith('.'):
                    classes.append(x.lstrip('.'))
                elif x.startswith('='):
                    role = x.lstrip('=')
                elif x.startswith('#'):
                    id_ = x.lstrip('#')
                else:
                    id_ = x
        container_kwargs = {}
        if start.group('collapsible'):
            container = lcg.CollapsiblePane
            if start.group('collapsible').strip().endswith('+'):
                container_kwargs['collapsed'] = False
            container_kwargs['title'] = start.group('title')
        else:
            container = lcg.Container
            if not classes:
                classes = 'lcg-generic-container'
            container_kwargs['label'] = start.group('label')
        container = container(content=content, id=id_, name=classes, role=role, **container_kwargs)
        return container, position

    def _literal_processor(self, text, position, **kwargs):
        match = self._LITERAL_MATCHER.match(text[position:])
        if not match:
            return None
        content = lcg.PreformattedText(match.group(1))
        return content, position + match.end()

    def _doctest_processor(self, text, position, **kwargs):
        match = self._DOCTEST_MATCHER.match(text[position:])
        if not match:
            return None
        content = lcg.PreformattedText(match.group(0), mime_type='text/x-python-doctest')
        return content, position + match.end()

    def _exercise_processor(self, text, position, **kwargs):
        match = self._EXERCISE_MATCHER.match(text[position:])
        if not match:
            return None
        from . import exercises
        parser = exercises.ExerciseParser()
        exercise_type = getattr(exercises, match.group(1), None)
        if not exercise_type:
            return None
        content = parser.parse(exercise_type, match.group(2))
        return content, position + match.end()

    def _toc_processor(self, text, position, **kwargs):
        match = self._TOC_MATCHER.match(text[position:])
        if not match:
            return None
        groups = match.groupdict()
        title = groups['title']
        if groups['toctype'] in ('NodeIndex', 'NTOC'):
            class_ = lcg.NodeIndex
        else:
            class_ = lcg.TableOfContents
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
                return lcg.ItemizedList.NUMERIC
            elif char == char.lower():
                return lcg.ItemizedList.LOWER_ALPHA
            else:
                return lcg.ItemizedList.UPPER_ALPHA
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
                    if text[position + current_indentation] == ' ':
                        current_indentation += 1
                    else:
                        break
                if current_indentation < inner_indentation:  # no inner content anymore
                    break
            # Hack to prevent single paragraphs in list item contents.
            item0 = item_content[0]
            if (((len(item_content) == 1
                  or len(item_content) > 1 and isinstance(item_content[1], lcg.ItemizedList))
                 and isinstance(item0, lcg.Paragraph)
                 and item0.halign() is None
                 and len(item0.content()) == 1)):
                item_content[0] = item0.content()[0]
            if len(item_content) == 1:
                items.append(item_content[0])
            else:
                items.append(lcg.Container(item_content))
            if position >= size or current_indentation != list_indentation:  # no next item
                break
            match = self._LIST_MATCHER.match(text[position:])
            if not match:               # this is not a (next) list item
                break
            if list_kind(text, position + match.end(1)) != kind:
                # list kind switch => start new list
                break
        return lcg.ItemizedList(items, order=kind), position

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
                return lcg.TableCell.RIGHT
            else:
                return None
        table_rows = []
        line_above = 0
        re_iterate = re.compile(' *@iterate ')
        while text[position:position + 1] == '|':
            iterated = False
            # Get the line
            start_position = position = position + 1
            eol = text[start_position:].find('\n')
            if eol >= 0:
                position += eol + 1
                if text[position - 2] != '\r' and text[position:position + 1] == '\r':  # Mac
                    position += 1
            else:
                position = len(text)
            # Rule?
            if text[start_position:start_position + 1] == '-':
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
                        maybe_bars.append(i + 1)
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
                                width = lcg.UFont(float(width))
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
                     for cell in stripped_cells])):  # noqa: F812
                row_cells = [lcg.TableHeading(self.parse_inline_markup(cell and cell[1:-1]))
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
                    row_cells.append(lcg.TableCell(self.parse_inline_markup(cell.strip()),
                                                   align=align(i, cell.expandtabs())))
                    i += 1
            table_rows.append(lcg.TableRow(row_cells, line_above=line_above, iterated=iterated))
            line_above = 0
        if line_above > 0 and table_rows:
            table_rows[-1].set_line_below(line_above)
        # Make and return the content object
        if bars is None:
            bars = ()
        if global_widths is None or all([w is None for w in global_widths.values()]):
            column_widths = None
        else:
            column_widths = [global_widths.get(i)
                             for i in range(max(global_widths) + 1)]  # noqa: F812
        content = lcg.Table(table_rows, bars=bars, column_widths=column_widths, halign=halign)
        return content, position

    def _parameters_processor(self, text, position, parameters=None, presentation=None,
                              **kwargs):
        match = self._PARAMETER_MATCHER.match(text[position:])
        if not match:
            return None
        identifier = match.group(1)
        value = match.group(2)
        position += match.end()
        while text[position:position + 1] in ('\r', '\n',):
            position += 1
        if value:
            value = value.strip()
        if not value:
            match = re.search('^@end %s *\r?$' % (identifier,), text[position:], re.MULTILINE)
            if match:
                value = text[position:position + match.start()].strip()
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
                    parameters[name] = lcg.Container(Parser().parse(value))
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
        while text[position:position + 1] in ('\r', '\n',):
            position += 1
        if value:
            value = value.strip()
            variable_content = self.parse_inline_markup(value)
        else:
            match = re.search('^@end %s *\r?$' % (identifier,), text[position:], re.MULTILINE)
            if match:
                value = text[position:position + match.start()].strip()
                position += match.end()
            else:                       # unfinished variable
                return None, position
            variable_content = lcg.Container(self.parse(value))
        content = lcg.SetVariable(unistr(identifier), variable_content)
        return content, position

    def _style_processor(self, text, position, **kwargs):
        match = self._STYLE_MATCHER.match(text[position:])
        if not match:
            return None
        name = match.group(1)
        text_start = position + match.end()
        while text[text_start:text_start + 1] in ('\r', '\n',):
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
        container = lcg.Container(content_list, name=name)
        return container, end_position

    def _space_processor(self, text, position, **kwargs):
        match = self._VSPACE_MATCHER.match(text[position:])
        if not match:
            return None
        value = float(match.group(1))
        position += match.end()
        content = lcg.VSpace(lcg.UMm(value))
        return content, position

    def _paragraph_processor(self, text, position, halign=None, indentation=0, extra_indentation=0,
                             compressed=False, **kwargs):
        next_position = self._skip_content(text, position, indentation=indentation,
                                           extra_indentation=extra_indentation,
                                           compressed=compressed)
        if next_position == position:
            return None
        paragraph_text = text[position:next_position].strip()
        content = lcg.Paragraph(self.parse_inline_markup(paragraph_text), halign=halign)
        return content, next_position

    def _whitespace_processor(self, text, position, **kwargs):
        next_position = position
        while text[next_position:] and text[next_position] in string.whitespace:
            next_position += 1
        content = lcg.Paragraph(self.parse_inline_markup(''))
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
            text = text[:match.start()] + ' ' * 8 + text[match.end():]
        return text

    def _skip_content(self, text, position, indentation=0, extra_indentation=0, compressed=False):
        while True:
            if ((self._LITERAL_MATCHER.match(text[position:]) or
                 self._LIST_MATCHER.match(text[position:]))):
                # some blocks don't have to be separated by blank lines
                break
            match = self._LINE_MATCHER.match(text[position:])
            if not match:               # end of text?
                break
            if not match.group(2):      # blank line?
                break
            if match.end(1) - match.start(1) + extra_indentation < indentation:
                # reduced indentation?
                break
            if compressed and self._LIST_MATCHER.match(text[position:]):  # inner list
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
            (self._old_position, position, text[position:position + 100],)
        if __debug__:
            self._old_position = position
        for processor in (processors or self._processors):
            result = processor(text, position, **kwargs)
            if result is not None:
                if __debug__:
                    position = result[1]
                    assert position >= min(self._old_position + 1, len(text)), \
                        (self._old_position, position, text[position:position + 100], processor,)
                return result
        else:
            raise Exception('Unhandled text', text[position:])

    def _substitution_markup_handler(self, markup, subst):
        # get the substitution value for _SUBSTITUTION_REGEX match
        if subst.startswith('{') and subst.endswith('}'):
            subst = subst[1:-1]
        if subst:
            return lcg.Substitution(subst, markup=markup)
        else:
            return lcg.TextContent(markup)

    def _link_markup_handler(self, link, href=None, size=None, label=None, descr=None, align=None):
        def _basename(filename):
            if filename:
                if '/' in filename:
                    filename = filename.split('/')[-1]
                if '.' in filename:
                    filename = filename.rsplit('.', 1)[0]
            return filename or None
        if label:
            label = label.strip() or None
        label_image = None
        if label:
            label_parts = self._BLANK_MATCHER.split(label, 1)
            if len(label_parts) == 1 and lcg.Resource.subclass(label) is lcg.Image:
                label_image = label
                label = None
            elif len(label_parts) == 2 and lcg.Resource.subclass(label_parts[0]) is lcg.Image:
                label_image = label_parts[0]
                label = label_parts[1].strip()
        if size:
            pxsize = tuple(map(int, size.split('x')))
            width, height = map(lcg.UPx, pxsize)
        else:
            pxsize = None
            width, height = None, None
        if align:
            align = {'>': lcg.InlineImage.RIGHT, '<': lcg.InlineImage.LEFT}.get(align)
        resource_cls = None
        match = self._YOUTUBE_VIDEO_MATCHER.match(href)
        if match:
            video_service = 'youtube'
            video_id = match.group("video_id")
        else:
            match = self._VIMEO_VIDEO_MATCHER.match(href)
            if match:
                video_service = 'vimeo'
                video_id = match.group("video_id")
            else:
                video_service = None
                resource_cls = lcg.Resource.subclass(href)
        if video_service:
            result = lcg.InlineExternalVideo(video_service, video_id, size=pxsize, title=label)
        elif resource_cls is lcg.Image and not label_image:
            result = lcg.InlineImage(href, title=label, descr=descr, name=_basename(href),
                                     align=align, width=width, height=height)
        elif resource_cls is lcg.Audio:
            result = lcg.InlineAudio(href, title=label, descr=descr, name=_basename(href),
                                     image=label_image)
        elif resource_cls is lcg.Video:
            result = lcg.InlineVideo(href, title=label, descr=descr, name=_basename(href),
                                     image=label_image, size=pxsize)
        else:
            if label_image:
                label = lcg.InlineImage(label_image, title=label, name=_basename(label_image),
                                        align=align)
            if ((href.startswith('http://') or href.startswith('https://') or
                 href.startswith('ftp://'))):
                target = lcg.Link.ExternalTarget(href, label)
            else:
                target = href
            result = lcg.Link(target, label=label, descr=descr)
        return result

    def _uri_markup_handler(self, uri):
        return self._link_markup_handler(uri, href=uri)

    def _page_number_markup_handler(self, markup):
        return lcg.PageNumber()

    def _total_pages_markup_handler(self, markup):
        return lcg.TotalPages()

    def _escape_markup_handler(self, markup):
        return lcg.TextContent(markup)

    def _email_markup_handler(self, email):
        return lcg.Link(lcg.Link.ExternalTarget('mailto:' + email, email))

    def _newline_markup_handler(self, markup):
        return lcg.NewLine()

    def _comment_markup_handler(self, text):
        return lcg.Content()

    def _dash_markup_handler(self, markup):
        return lcg.TextContent(u'—')

    def _nbsp_markup_handler(self, markup):
        return lcg.TextContent(u' ')

    # The following handlers receive the already parsed lcg.Content instance as
    # argument (as they have paired markup on input).

    def _emphasized_markup_handler(self, content):
        return lcg.Emphasized(content)

    def _strong_markup_handler(self, content):
        return lcg.Strong(content)

    def _code_markup_handler(self, content):
        return lcg.Code(content)

    def _underlined_markup_handler(self, content):
        return lcg.Underlined(content)

    def _citation_markup_handler(self, content):
        return lcg.Citation(content)

    def _markup_handler(self, stack, match, append):
        name, markup, kwargs = None, None, {}
        for key, value in match.groupdict().items():
            if value is not None:
                if key in self._INLINE_MARKUP_PARAMETERS:
                    kwargs[key] = value
                else:
                    name = key
                    markup = value
        number_of_backslashes = markup.count('\\')
        markup = markup[number_of_backslashes:]
        initial_backslashes = (number_of_backslashes // 2) * '\\'
        if number_of_backslashes % 2:
            # If the number of backslashes is odd, the markup is escaped (printed as is).
            return [lcg.TextContent(initial_backslashes + markup)]
        if initial_backslashes:
            append(lcg.TextContent(initial_backslashes))
        result = []
        # We need two variables (start and end), because both can be False for
        # unpaired markup.
        start = False
        end = False
        if name.endswith('_start'):
            name = name[:-6]
            start = True
        elif name.endswith('_end'):
            name = name[:-4]
            end = True
        if start and name not in [entry.name for entry in stack]:
            # Opening markup.
            stack.append(self._StackEntry(name))
        elif end and stack and name == stack[-1].name:
            # Closing an open markup.
            entry = stack.pop()
            handler = getattr(self, '_' + name + '_markup_handler')
            x = handler(entry.content, **kwargs)
            result.append(x)
        elif not start and not end:
            # Unpaired markup.
            handler = getattr(self, '_' + name + '_markup_handler')
            result.append(handler(markup, **kwargs))
        elif markup:
            # Markup in an invalid context is just printed as is.
            # This can be end markup, which was not opened or start markup,
            # which was already opened.
            result.append(lcg.TextContent(markup))
        return result

    def parse_inline_markup(self, text):
        """Parse inline constructs within given source text and return a 'Container' instance.

        As opposed to 'parse()', which parses block level constructs, this
        method only parses inline constructs within the blocks processed by
        'parse()'.  The inline constructs are links, text emphasizing etc.

        """
        stack = []
        result = []
        pos = 0

        def append(*content):
            if stack:
                stack[-1].content.extend(content)
            else:
                result.extend(content)
        for match in self._inline_markup.finditer(text):
            preceding_text = text[pos:match.start()]
            if preceding_text:
                append(lcg.TextContent(preceding_text))
            append(*self._markup_handler(stack, match, append))
            pos = match.end()
        final_text = text[pos:]
        if final_text:
            append(lcg.TextContent(final_text))
        while stack:
            entry = stack.pop()
            handler = getattr(self, '_' + entry.name + '_markup_handler')
            append(handler(entry.content))
        return lcg.Container(result)

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
        presentation = lcg.Presentation()
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
                return e.__class__.__name__ + ': ' + unistr(e)
            else:
                return ''.join([unistr(x) for x in self._content[bool(result)]])

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
        safe_builtins = ('False', 'None', 'True', 'abs', 'all', 'any', 'bool', 'bytes',
                         'chr', 'complex', 'dict', 'divmod', 'float', 'hash', 'hex',
                         'id', 'isinstance', 'int', 'len', 'list', 'max', 'min', 'oct',
                         'ord', 'pow', 'range', 'repr', 'reversed', 'round', 'set',
                         'slice', 'sorted', 'str', 'sum', 'tuple', 'zip')
        globals = dict(self._globals, __builtins__=None)
        for builtin in safe_builtins:
            globals[builtin] = __builtins__[builtin]
        return eval("bool(%s)" % expr, globals, {})

    def _default_include(self, name):
        try:
            return unistr(self._globals[name])
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
        return unistr(result)


class HTMLProcessor(object):
    """Convertor from LCG HTML to LCG Content.

    LCG HTML is an HTML text in the form defined here.  The following rules
    apply (this is just a starting set for now, to be expanded in future):

    - 'h*' elements introduce new sections.  The element content makes a
      section title while all following elements until the next 'h*' element of
      the same or higher level (or the end of the HTML text) make the section
      content.

    The conversion process consists of two basic parts: HTML parsing and
    transforming the parsed content to LCG Content structures.  HTML parsing
    creates an etree structure corresponding to the input HTML.  Tag elements
    are represented by etree Elements; text elements are represented by etree
    Elements with special tag '_text'.  'math' element is handled in a special
    way.  The parsing process is performed by '_HTMLParser' inner class and
    here is probably nothing you would need to customize there.

    The more interesting part is transformation of the resulting etree to LCG
    structures.  It is performed by '_Transformer' inner class.  By changing or
    subclassing it you can influence the transformation process.

    The most important customization method is '_Transformer._matchers' which
    defines the transformation rules.  The method returns sequence of pairs
    (MATCHER, HANDLER).  MATCHER is a tuple of the form (TAG-REGEXP,
    (ATTRIBUTE-NAME, ATTRIBUTE-REGEXP), ...).  TAG-REGEXP is a regular
    expression matching the whole tag name; ATTRIBUTE-REGEXP is a regular
    expression matching the whole value of attribute ATTRIBUTE-NAME, undefined
    attributes are handled as empty strings.  Alternatively MATCHER can be also
    a function of single argument, the element, returning True iff the element
    matches.  The first matching pair is used for transformation of each of the
    elements.  It is an error if an element doesn't match any of the matchers
    -- such elements couldn't be transformed.

    HANDLER is a pair of the form (FUNCTION, KWARGS).  Function is a function
    of two non-optional arguments: The handled element and a sequence of the
    following elements (siblings) on the same level (this argument is useful
    when the content of the corresponding LCG element consists not only of the
    handled element but also from some elements following it, e.g. in case of
    sections).  Dictionary of additional KWARGS to be passed to the called
    function may be provided.  The handler function is responsible for
    processing element's subelements, typically '_Transformer.transform' method
    is applied on them and the returned 'Content' instances are inserted into
    the transformed element.  Several typical handling functions (methods) are
    predefined in '_Transformer' class.

    """

    class _HTMLParser(html.parser.HTMLParser):

        def reset(self):
            html.parser.HTMLParser.reset(self)
            self._hp_tree = xml.etree.ElementTree.Element('html')
            self._hp_elements = [self._hp_tree]
            self._hp_open_tags = []
            self._hp_current_text = ''
            self._hp_raw = False

        def _hp_finish_text(self):
            if self._hp_current_text:
                element = xml.etree.ElementTree.SubElement(self._hp_elements[-1], '_text')
                element.text = self._hp_current_text
                self._hp_current_text = ''

        def handle_starttag(self, tag, attrs):
            if self._hp_raw:
                self._hp_current_text += self.get_starttag_text()
                return
            self._hp_finish_text()
            if tag == 'math':
                if not self._hp_raw and self._hp_current_text:
                    element = xml.etree.ElementTree.SubElement(self._hp_elements[-1], '_text')
                    element.text = self._hp_current_text
                self._hp_raw = True
            if self._hp_raw:
                self._hp_current_text = self.get_starttag_text()
            element = xml.etree.ElementTree.SubElement(self._hp_elements[-1], tag, dict(attrs))
            self._hp_elements.append(element)
            self._hp_open_tags.append(tag)

        def handle_endtag(self, tag):
            if self._hp_raw:
                self._hp_current_text += '</%s>' % (tag,)
                if tag != self._hp_open_tags[-1]:
                    return
            while self._hp_open_tags[-1] != tag:
                self.handle_endtag(self._hp_open_tags[-1])
            if self._hp_raw:
                self._hp_elements[-1].text = self._hp_current_text
                self._hp_current_text = ''
            else:
                self._hp_finish_text()
            self._hp_elements.pop()
            self._hp_open_tags.pop()
            self._hp_raw = False

        def handle_data(self, data):
            self._hp_current_text += data

        def handle_charref(self, name):
            num = name.lstrip('&#').rstrip(';')
            expanded = chr(int(num))
            self.handle_data(expanded)

        def handle_entityref(self, name):
            if self._hp_raw:
                self.handle_data('&' + name + ';')
            else:
                expanded = html.entities.entitydefs[name]
                if expanded[0] == b'&' and expanded[-1] == b';':
                    self.handle_charref(expanded)
                else:
                    self.handle_data(unistr(expanded, 'iso-8859-1'))

        def close(self):
            while self._open_tags:
                self.handle_endtag(self._open_tags[-1])
            html.parser.HTMLParser.close()

        def tree(self):
            return self._hp_tree

    class _Transformer(object):

        def __init__(self):
            object.__init__(self)
            self._make_matchers()
            self._in_table_heading = False

        def _matchers(self):
            return (
                (('div', ('style', '.*page-break-after: always;.*')),
                 (self._single, dict(class_=lcg.NewPage))),
                ('br', (self._single, dict(class_=lcg.NewLine))),
                (('pre', ('class', 'lcg-exercise'), ('data-type', '.*')), self._exercise),
                ('(html|div|span|strike|li|dt|dd)', self._container),
                ('p', (self._container, dict(class_=lcg.Paragraph))),
                ('blockquote', self._blockquote),
                ('figure', self._figure),
                ('strong', (self._container, dict(class_=lcg.Strong))),
                ('em', (self._container, dict(class_=lcg.Emphasized))),
                ('u', (self._container, dict(class_=lcg.Underlined))),
                ('sub', (self._container, dict(class_=lcg.Subscript))),
                ('sup', (self._container, dict(class_=lcg.Superscript))),
                ('h[0-9]', self._section),
                ('pre', (self._text, dict(class_=lcg.PreformattedText))),
                ('ul', (self._list, dict(order=None))),
                (('ol', ('style', '.* lower-alpha;.*')),
                 (self._list, dict(order=lcg.ItemizedList.LOWER_ALPHA))),
                (('ol', ('style', '.* upper-alpha;.*')),
                 (self._list, dict(order=lcg.ItemizedList.UPPER_ALPHA))),
                ('ol', (self._list, dict(order=lcg.ItemizedList.NUMERIC))),
                ('dl', self._definition_list),
                (('a', ('name', '.+')), self._anchor),
                (('a', ('class', 'lcg-audio')), (self._media, dict(class_=lcg.InlineAudio))),
                (('a', ('class', 'lcg-video')), (self._media, dict(class_=lcg.InlineVideo))),
                (('a', ('href', '.+')), self._link),
                ('a', self._container),
                ('table', self._table),
                ('tr', (self._container, dict(class_=lcg.TableRow))),
                ('t[dh]', self._table_cell),
                ('hr', (self._single, dict(class_=lcg.HorizontalSeparator))),
                ('math', (self._plain, dict(class_=lcg.MathML))),
                ('img', self._image),
                ('_text', self._text),
            )

        def _first_text(self, element):
            text = element.text
            if text:
                return text
            for child in element:
                text = self._first_text(child)
                if text:
                    return text
            return ''

        def _plain_text(self, element):
            text = element.text or ''
            for child in element:
                text += self._plain_text(child)
            return text

        def _transform_sub(self, obj, nowhitespace=True):
            obj = list(obj)
            content = []
            while obj:
                content.append(self.transform(obj.pop(0), obj))
            if nowhitespace:
                new_content = []
                for c in content:
                    if ((isinstance(c, lcg.TextContent) and
                         not isinstance(c, lcg.Anchor) and
                         not c.text().strip())):
                        continue
                    if ((isinstance(c, lcg.NewLine) and
                         new_content and isinstance(new_content[-1], lcg.TextContent))):
                        t = new_content[-1]
                        new_content[-1] = t.clone(t.text().rstrip())
                    if ((isinstance(c, lcg.TextContent) and
                         new_content and isinstance(new_content[-1], lcg.NewLine))):
                        c = c.clone(c.text().lstrip())
                    new_content.append(c)
                content = new_content
            return content

        def _container(self, element, followers, class_=lcg.Container, **kwargs):
            if element.tag == 'p' and 'style' in element.attrib:
                styles = dict([[xx.strip() for xx in x.split(':', 2)]
                               for x in element.attrib['style'].strip('\t ;').split(';')])
                align = styles.get('text-align')
                if align:
                    kwargs['halign'] = {'right': lcg.HorizontalAlignment.RIGHT,
                                        'center': lcg.HorizontalAlignment.CENTER,
                                        'justify': lcg.HorizontalAlignment.JUSTIFY}.get(align)
                margin = styles.get('margin-left')
                if margin:
                    margin = margin.strip('px')
                    if margin.isdigit():
                        kwargs['presentation'] = presentation = lcg.Presentation()
                        presentation.indent_left = lcg.UFont(int(margin) // 12)
            content = self._transform_sub(element)
            if class_ == lcg.Paragraph and self._find_element(content, (lcg.Section,
                                                                        lcg.Paragraph,
                                                                        lcg.Table,
                                                                        lcg.Figure)):
                # Suppress nested paragraphs or sections, figures or tables nested in paragraphs.
                class_ = lcg.Container
            return class_(content, lang=element.attrib.get('lang'), **kwargs)

        def _find_element(self, content, cls):
            if isinstance(content, cls):
                return True
            elif isinstance(content, lcg.Container):
                return self._find_element(content.content(), cls)
            elif isinstance(content, (list, tuple)):
                for item in content:
                    if self._find_element(item, cls):
                        return True
            return False

        def _blockquote(self, element, followers):
            kwargs = {}
            footer = element.find('footer')
            if footer is not None:
                # Convert the <footer> content inside <blockquote> into Quotation 'kwargs'.
                element.remove(footer)
                text = self._plain_text(footer).strip()
                if text.startswith(u'— '):
                    text = text[2:]
                kwargs['source'] = text
                link = footer.find('a')
                if link is not None:
                    kwargs['uri'] = link.attrib.get('href')
            content = self._transform_sub(element)
            return lcg.Quotation(content, **kwargs)

        def _exercise(self, element, followers):
            from . import exercises
            parser = exercises.ExerciseParser()
            exercise_type = getattr(exercises, element.attrib.get('data-type'))
            src = self._first_text(element)
            return parser.parse(exercise_type, src.strip())

        def _figure(self, element, followers):
            kwargs = {}
            body = []
            for child in element:
                if child.tag == 'figcaption':
                    kwargs['caption'] = lcg.Container(self._transform_sub(child))
                else:
                    body.append(child)
            content = self._transform_sub(body)
            kwargs['align'] = element.attrib.get('data-lcg-align')
            return lcg.Figure(content, **kwargs)

        def _section(self, element, followers):
            level = element.tag[1]
            section_children = []
            while followers:
                c = followers[0]
                if c.tag[0] == 'h' and c.tag[1] <= level:
                    break
                section_children.append(c)
                followers.pop(0)
            title_text = self._plain_text(element).strip()
            title_content = self._transform_sub(element)
            if not title_content:
                title_content = (lcg.TextContent(title_text),)
            elif len(title_content) == 1 and isinstance(title_content[0], lcg.TextContent):
                title_content = lcg.TextContent(title_content[0].text().strip())
            title_content = lcg.Container(title_content, lang=element.attrib.get('lang'))
            content = self._transform_sub(section_children)
            return lcg.Section(title_text, content, heading=title_content)

        def _list(self, element, followers, order=None):
            items = self._transform_sub(element)
            return lcg.ItemizedList(items, order=order)

        def _definition_list(self, element, followers):
            items = self._transform_sub(element)
            paired_items = []
            while items:
                paired_items.append((items.pop(0), items.pop(0),))
            return lcg.DefinitionList(paired_items)

        def _text(self, element, followers, class_=lcg.TextContent):
            return class_(self._first_text(element))

        def _plain(self, element, followers, class_=lcg.Content):
            return class_(element.text)

        def _single(self, element, followers, class_=lcg.Content):
            return class_()

        def _anchor(self, element, followers):
            name = element.attrib['name']
            text = self._first_text(element)
            return lcg.Anchor(anchor=name, text=text)

        def _link(self, element, followers):
            label = lcg.Container(self._transform_sub(element))
            if 'enlarge' in element.attrib.get('data-lcg-link-type', ''):
                # Temporary hack to ignore link around images enlarged on click.
                return label
            else:
                resource = element.attrib.get('data-lcg-resource')
                if resource:
                    target = resource
                else:
                    target = element.attrib['href']
                return lcg.Link(target=target, label=label)

        def _media(self, element, followers, class_=None, uri=None, **kwargs):
            resource = element.attrib.get('data-lcg-resource')
            if resource:
                target = resource
            else:
                target = uri or element.attrib['href']
            basename = target.split('/')[-1].rsplit('.', 1)[0]
            return class_(target, name=basename, title=self._plain_text(element), **kwargs)

        def _image(self, element, followers):
            align = {'left': lcg.InlineImage.LEFT,
                     'right': lcg.InlineImage.RIGHT}.get(element.attrib.get('align'))
            return self._media(element, followers, class_=lcg.InlineImage,
                               uri=element.attrib['src'], align=align)

        def _table(self, element, followers):
            content = []
            title = None
            transformations = element.attrib.get('data-lcg-transformations')
            if transformations is not None:
                kwargs = {'transformations': tuple(transformations.split())}
            else:
                # Don't pass the argument to use the default transformations.
                kwargs = {}
            for child in element:
                tag = child.tag
                if tag == 'caption':
                    title = self._first_text(child).strip()
                elif tag == 'thead':
                    self._in_table_heading = True
                    content += self._transform_sub(child)
                    self._in_table_heading = False
                elif tag == 'tbody':
                    content += self._transform_sub(child)
            return lcg.Table(content, title=title, **kwargs)

        def _table_cell(self, element, followers):
            content = lcg.Container(self._transform_sub(element))
            style = element.attrib.get('style', '')
            align = None
            if style.find('text-align: left;') >= 0:
                align = lcg.TableCell.LEFT
            elif style.find('text-align: right;') >= 0:
                align = lcg.TableCell.RIGHT
            elif style.find('text-align: center;') >= 0:
                align = lcg.TableCell.CENTER
            class_ = lcg.TableHeading if self._in_table_heading else lcg.TableCell
            return class_(content, align=align)

        def _make_matchers(self):
            matchers = self._matchers()
            compiled_matchers = []
            for test, handler in matchers:
                if isinstance(test, basestring):
                    test = (test,)
                if isinstance(test, (tuple, list)):
                    tag_regexp = re.compile(test[0] + '$')
                    attr_tests = [(a, re.compile(r),) for a, r in test[1:]]

                    def test_function(element, tag_regexp=tag_regexp, attr_tests=attr_tests):
                        if not tag_regexp.match(element.tag):
                            return False
                        for attr, regexp in attr_tests:
                            try:
                                value = element.attrib[attr]
                            except KeyError:
                                return False
                            if not regexp.match(value + '$'):
                                return False
                        return True
                elif callable(test):
                    test_function = test
                else:
                    raise Exception("Invalid matcher test specification", test)
                if not isinstance(handler, (tuple, list)):
                    handler = (handler, {})
                compiled_matchers.append((test_function, handler))
            self._compiled_matchers = compiled_matchers

        def transform(self, element, _followers=None):
            if _followers is None:
                _followers = []
            for test, handler in self._compiled_matchers:
                if test(element):
                    function, kwargs = handler
                    return function(element, _followers, **kwargs)
            raise Exception("No transformation available for element", element)

    _TEXT_REPLACEMENTS = (
        (re.compile('</(?P<tag>em|strong)>( *)<(?P=tag)>'), '\\2',),
        (re.compile('<(?P<tag>em|strong|p)>(( |&nbsp;)*)</(?P=tag)>'), '\\2',),
        # Filter out all special characters (simply use the valid XML character ranges).
        (re.compile(u'[^\u0020-\uD7FF\x09\x0A\x0D\uE000-\uFFFD\u10000-\u10FFFF]', re.U), u'')
    )

    def _text_process(self, html):
        for regexp, replacement in self._TEXT_REPLACEMENTS:
            html = regexp.sub(replacement, html)
        return html

    def _tree_content(self, html):
        html = self._text_process(html)
        parser = self._HTMLParser()
        parser.feed(html)
        return parser.tree()

    def _lcg_content(self, tree):
        transformer = self._Transformer()
        return transformer.transform(tree)

    def html2lcg(self, html):
        """Return LCG Content corresponding to given LCG 'html'.

        Arguments:

          html -- unicode containing input LCG HTML

        """
        assert isinstance(html, basestring), html
        tree = self._tree_content(html)
        lcg = self._lcg_content(tree)
        return lcg


def html2lcg(html):
    """Convenience function to convert LCG HTML to LCG Content.

    Arguments:

      html -- unicode containing input LCG HTML

    Return corresponding 'Content' instance.

    See 'HTMLProcessor' for more information and information about LCG HTML.

    """
    processor = HTMLProcessor()
    return processor.html2lcg(html)


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
