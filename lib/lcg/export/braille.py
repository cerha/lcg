# -*- coding: utf-8 -*-

# Copyright (C) 2012-2015 OUI Technology Ltd.
# Copyright (C) 2019-2020 Tomáš Cerha <t.cerha@gmail.com>
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

"""Export to Braille notation."""
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from builtins import chr
from builtins import zip
from builtins import range

from contextlib import contextmanager
import copy
import ctypes
import ctypes.util
import os
import re
import string

import louis

from lcg import Presentation, UFont, USpace, ContentNode, Section, Resource, PageNumber, \
    Container, TranslatableTextFactory, Table, TableRow, TableCell, TableHeading, TextContent, \
    ItemizedList
import lcg
from . import mathml
from .export import Exporter, FileExporter
from .nemeth import mathml_nemeth

_ = TranslatableTextFactory('lcg')

unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


_braille_whitespace = ' ⠀'

_inf = 'infix'
_pre = 'prefix'
_pos = 'postfix'
_mathml_operators = {
    # operator, form, Braille code, hyphenation
    '(': (_pre, '⠦', '0',),
    ')': (_pos, '⠴', '0',),
    '[': (_pre, '⠠⠦', '00',),
    ']': (_pos, '⠠⠴', '00',),
    '{': (_pre, '⠨⠦', '00',),
    '}': (_pos, '⠨⠴', '00',),
    '⟨': (_pre, '⠈⠣', '00'),
    '⟩': (_pre, '⠈⠜', '00'),
    '|': (None, '⠸', '3',),
    '=': (_inf, '⠶', '3',),
    '≠': (_inf, '⠈⠶', '00',),
    '≐': (_inf, '⠐⠶', '00',),
    '<': (_inf, '⠁⠀⠣⠃', '0000',),
    '>': (_inf, '⠁⠀⠜⠃', '0000',),
    '≤': (_inf, '⠣⠶', '00',),
    '≥': (_inf, '⠜⠶', '00',),
    '<>': (_inf, '⠣⠜', '00',),
    '+': (None, '⠲', '3',),
    '-': (None, '⠤', '3',),
    '−': (None, '⠤', '3',),
    '±': (None, '⠲⠤', '00',),
    '.': (_inf, '⠄', '3'),
    '⋅': (_inf, '⠄', '3'),
    '×': (_inf, '⠬', '3'),
    '*': (_inf, '⠔', '3'),
    '∗': (_inf, '⠔', '3'),
    ':': (_inf, '⠒', '3'),
    '∶': (_inf, '⠒', '3'),
    '∈': (_inf, ' ⠘⠑ ', '0000',),
    '∉': (_inf, ' ⠈⠘⠑ ', '00000',),
}

_unknown_char_regexp = re.compile('⠄⡳⠭([⠴⠂⠆⠒⠲⠢⠖⠶⠦⠔]+)')  # only English version


def braille_presentation(presentation_file='presentation-braille.py'):
    """Return default braille presentation.

    Arguments:

      presentation_file -- base name of the presentation file to be used; string

    """
    presentation = Presentation()
    filename = os.path.join(os.path.dirname(__file__), 'styles', presentation_file)
    try:
        import importlib.util
    except ImportError:
        # TODO NOPY2: Remove this Python 2 compatibility workaround.
        import imp
        f = open(filename)
        confmodule = imp.load_module('_lcg_presentation', f, filename, ('.py', 'r', imp.PY_SOURCE))
        f.close()
    else:
        spec = importlib.util.spec_from_file_location('_lcg_presentation', filename)
        confmodule = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(confmodule)
    for o in dir(confmodule):
        if o[0] in string.lowercase and hasattr(presentation, o):
            setattr(presentation, o, confmodule.__dict__[o])
    return presentation


class _Braille(object):

    def __init__(self, text, hyphenation=None):
        assert isinstance(text, basestring), text
        assert hyphenation is None or isinstance(hyphenation, basestring), hyphenation
        self._text = text
        self._hyphenation = hyphenation or self._default_hyphenation(text)
        assert len(self._text) == len(self._hyphenation), (self._text, self._hyphenation,)

    def _default_hyphenation(self, text):
        return BrailleExporter.HYPH_NO * len(text)

    def text(self):
        return self._text

    def hyphenation(self):
        return self._hyphenation

    def __len__(self):
        return len(self._text)

    def __bool__(self):
        return not not self._text

    # Just for Python 2 compatibility.
    __nonzero__ = __bool__

    def __add__(self, braille):
        return _Braille(self.text() + braille.text(), self.hyphenation() + braille.hyphenation())

    def __mul__(self, n):
        return _Braille(self.text() * n, self.hyphenation() * n)

    def append(self, text, hyphenation=None):
        self._text += text
        self._hyphenation += hyphenation or self._default_hyphenation(text)
        assert len(self._text) == len(self._hyphenation), (self._text, self._hyphenation,)

    def prepend(self, text, hyphenation=None):
        self._text = text + self._text
        self._hyphenation = (hyphenation or self._default_hyphenation(text)) + self._hyphenation
        assert len(self._text) == len(self._hyphenation), (self._text, self._hyphenation,)

    def strip(self):
        text = self._text
        i = 0
        n = len(text)
        j = n
        while i < n and text[i] == '⠀':
            i += 1
        while j > 0 and text[j - 1] == '⠀':
            j -= 1
        return _Braille(text[i:j], self._hyphenation[i:j])


class BrailleError(Exception):
    """Exception raised on Braille formatting errors.

    The exception provides a human readable explanation message.

    """

    def __init__(self, message, *args):
        """
        Arguments:

          message -- message explaining the error; unicode

        """
        assert isinstance(message, basestring), message
        super(BrailleError, self).__init__(message, *args)

    def message(self):
        """Return message explaining the error; basestring.
        """
        return self.args[0]


class TableTooWideError(BrailleError):
    "Exception raised on tables that can't be fit to the page width."

    def __init__(self, info):
        super(TableTooWideError, self).__init__("Table too wide (%s)" % (info,))


_louisutdml_path = ctypes.util.find_library('louisutdml')
if _louisutdml_path is None:
    _louisutdml = None
else:
    _louisutdml = ctypes.CDLL(_louisutdml_path)

_louisutdml_initialized = False
_en6backmapping = {
    u' ': u'⠀',
    u'a': u'⠁',
    u'1': u'⠂',
    u'b': u'⠃',
    u"'": u'⠄',
    u'k': u'⠅',
    u'2': u'⠆',
    u'l': u'⠇',
    u'`': u'⠈',
    u'c': u'⠉',
    u'i': u'⠊',
    u'f': u'⠋',
    u'/': u'⠌',
    u'm': u'⠍',
    u's': u'⠎',
    u'p': u'⠏',
    u'"': u'⠐',
    u'e': u'⠑',
    u'3': u'⠒',
    u'h': u'⠓',
    u'9': u'⠔',
    u'o': u'⠕',
    u'6': u'⠖',
    u'r': u'⠗',
    u'~': u'⠘',
    u'd': u'⠙',
    u'j': u'⠚',
    u'g': u'⠛',
    u'>': u'⠜',
    u'n': u'⠝',
    u't': u'⠞',
    u'q': u'⠟',
    u',': u'⠠',
    u'*': u'⠡',
    u'5': u'⠢',
    u'<': u'⠣',
    u'-': u'⠤',
    u'u': u'⠥',
    u'8': u'⠦',
    u'v': u'⠧',
    u'.': u'⠨',
    u'%': u'⠩',
    u'{': u'⠪',
    u'$': u'⠫',
    u'+': u'⠬',
    u'x': u'⠭',
    u'!': u'⠮',
    u'&': u'⠯',
    u';': u'⠰',
    u':': u'⠱',
    u'4': u'⠲',
    u'|': u'⠳',
    u'0': u'⠴',
    u'z': u'⠵',
    u'7': u'⠶',
    u'(': u'⠷',
    u'_': u'⠸',
    u'?': u'⠹',
    u'w': u'⠺',
    u'}': u'⠻',
    u'#': u'⠼',
    u'y': u'⠽',
    u')': u'⠾',
    u'=': u'⠿',
}
_entity_regexp = re.compile('&([A-Za-z]+);')


def xml2braille(xml):
    if _louisutdml is None:
        return None
    # Preprocess entities
    entity_table = mathml.entities

    def replace_entity(match):
        entity = match.group(1)
        replacement = entity_table.get(entity)
        if replacement is None:
            replacement = '&' + entity + ';'
        return replacement
    input_xml = _entity_regexp.sub(replace_entity, xml)
    # Allocate foreign call arguments
    inbuf = input_xml.encode('utf-8')
    maxlen = 2 ** 12 - 1
    outlen = ctypes.c_int(maxlen)
    outbuf_class = ctypes.c_int * (outlen.value + 1)
    outbuf = outbuf_class()
    global _louisutdml_initialized
    if _louisutdml_initialized:
        mode = 0
    else:
        mode = 1 << 30
        try:
            # latest liblouisutdml logs output with log level INFO - unexpected output fails tests;
            # so raise the default log level
            _louisutdml.lbu_setLogLevel(40000)  # liblouis.h: LOG_ERROR = 40000
        except AttributeError:
            pass
    # Make the foreign call and process the results
    result = _louisutdml.lbu_translateString(unistr("preferences.cfg"), inbuf, len(inbuf) + 1,
                                             outbuf, ctypes.byref(outlen), None, None, mode)
    if not result:
        raise BrailleError("XML processing failed", xml)
    _louisutdml_initialized = True
    if outlen.value == maxlen:
        raise BrailleError("Braille output too long", xml)
    # We don't know how to get dots from liblouisutdml directly, so we have to
    # translate the output here.  Additionally we remove spaces from the
    # beginning of the output which are put there by liblouisutdml for an
    # unknown reason.

    def make_dot_char(i):
        c = chr(i)
        return _en6backmapping.get(c, c)
    output = ''.join([make_dot_char(i) for i in outbuf[:outlen.value]])
    return output.strip(string.whitespace + '⠀')


class BrailleExporter(FileExporter, Exporter):
    "Transforming structured content objects to Braille output."

    _OUTPUT_FILE_EXT = 'brl'

    _PAGE_START_CHAR = '\ue010'  # recommended page break + priority
    _PAGE_END_CHAR = '\ue011'  # end of a single-page object
    _PAGE_START_REPEAT_CHAR = '\ue012'  # end of repeating lines from the first page start (headers)
    _DOUBLE_PAGE_CHAR = '\ue013'  # left and right pages composing a single page (e.g. wide table)
    _SOFT_NEWLINE_CHAR = '\ue014'  # removable newline (e.g. removable at the end of a page)
    _NEW_PAGE_CHAR = '\ue015'  # new page if not at the beginning of new page
    _NO_PAGE_BREAK_CHAR = '\ue016'  # no page break after this line
    _INDENTATION_CHAR = '\uf010'
    _NEXT_INDENTATION_CHAR = '\uf011'
    _RESTART_INDENTATION_CHAR = '\uf012'
    _CENTER_CHAR = '\uf013'

    HYPH_NO = '0'
    HYPH_YES = '1'
    HYPH_WS = '2'
    HYPH_CZECH_MATH_WS = '3'
    HYPH_NEMETH_WS = '4'
    HYPH_NEMETH_NUMBER = '5'

    class Context(Exporter.Context):

        def __init__(self, exporter, node, lang, tables={}, hyphenation_tables={},
                     **kwargs):
            super(BrailleExporter.Context, self).__init__(exporter, node, lang, **kwargs)
            assert isinstance(tables, dict), tables
            assert isinstance(hyphenation_tables, dict), hyphenation_tables
            self._tables = tables
            self._hyphenation_tables = hyphenation_tables
            self._node_presentation = None
            self._page_number = 1
            self._form = [louis.plain_text]
            self._hyphenate = True
            self._compactness = {}
            self._table_column_compactness = {}
            self._double_page = None
            self._content_to_alter = None
            self._alternate_text = None

        def tables(self, lang):
            if lang is None:
                lang = self.lang()
                if lang is None:
                    raise Exception("No language specified")
            tables = self._tables.get(lang)
            if tables is None:
                raise Exception("Unsupported language", lang)
            return tables

        def hyphenation_table(self, lang):
            return self._hyphenation_tables.get(lang or self.lang())

        def set_tables(self, tables, hyphenation_tables):
            assert isinstance(tables, dict), tables
            assert isinstance(hyphenation_tables, dict), hyphenation_tables
            self._tables = tables
            self._hyphenation_tables = hyphenation_tables

        def node_presentation(self):
            if self._node_presentation is None:
                presentation_set = self.presentation()
                node = self.node()
                lang = self.lang()
                if presentation_set is None:
                    presentation = node.presentation(lang) or Presentation()
                else:
                    presentations = (Presentation(),
                                     presentation_set.presentation(None, lang),
                                     node.presentation(lang),)
                    presentation = presentation_set.merge_presentations(presentations)
                self._node_presentation = presentation
            return self._node_presentation

        def page_number(self):
            return self._page_number

        def advance_page_number(self):
            page_number = self._page_number
            self._page_number += 1
            return page_number

        def reset_page_number(self):
            self._page_number = 1

        def form(self):
            return self._form[-1]

        @contextmanager
        def let_form(self, form):
            if form is not None:
                self._form.append(self._form[-1] | form)
            try:
                yield None
            finally:
                if form is not None:
                    self._form.pop()

        @contextmanager
        def let_hyphenate(self, hyphenate):
            old_hyphenate = self._hyphenate
            if hyphenate is not None:
                self._hyphenate = hyphenate
            try:
                yield None
            finally:
                self._hyphenate = old_hyphenate

        def compactness(self):
            return self._compactness

        def set_compactness(self, compactness):
            self._compactness = compactness

        def table_column_compactness(self):
            return self._table_column_compactness

        def set_table_column_compactness(self, compactness):
            self._table_column_compactness = compactness

        def double_page(self):
            return self._double_page

        def set_double_page(self, flag):
            self._double_page = flag

        def alternate_text(self, content):
            text = content.text()
            if content is self._content_to_alter:
                text = self._alternate_text
                self.set_alternate_text(None, None)
            return text

        def set_alternate_text(self, content, text):
            self._content_to_alter = content
            self._alternate_text = text

    def __init__(self, *args, **kwargs):
        super(BrailleExporter, self).__init__(*args, **kwargs)
        self._unbreakable_characters = (string.punctuation + string.digits +
                                        self._braille_characters())
        self._whitespace = string.whitespace + ' \u2800'

    def _braille_characters(self):
        return ''.join([chr(i) for i in range(10240, 10496)])

    def braille_unknown_char(self, code, report):
        return '⠿⠿⠿%s⠿⠿⠿' % (code,)

    def export(self, context, recursive=False):
        # Presentation
        node = context.node()
        lang = context.lang()
        presentation = context.node_presentation()
        if presentation.default_printer is not None:
            printer_properties = presentation.printers[presentation.default_printer]
        else:
            printer_properties = {}
        page_width = presentation.page_width
        if page_width:
            assert isinstance(page_width, (UFont, USpace)), page_width
            page_width = page_width.size()
        page_height = presentation.page_height
        if page_height:
            assert isinstance(page_height, (UFont, USpace)), page_height
            page_height = page_height.size()
        left_status_line = presentation.left_page_footer or node.left_page_footer(lang)
        right_status_line = presentation.right_page_footer or node.right_page_footer(lang)
        device_table = printer_properties.get('device_output', presentation.device_output)
        if device_table is None or isinstance(device_table, tuple):
            spec = device_table
            device_table = {' ': '⠀', '\n': '\r\n', '\f': '\f'}
            for c in self._braille_characters():
                device_table[c] = c
            if spec is not None:
                for c, t in spec:
                    device_table[c] = t
        braille_tables = presentation.braille_tables
        hyphenation_tables = presentation.braille_hyphenation_tables
        context.set_tables(braille_tables, hyphenation_tables)
        # Export

        def run_export(page_height=page_height):
            context.set_page_heading(_Braille(''))
            braille = super(BrailleExporter, self).export(context, recursive=recursive)
            text = braille.text()
            hyphenation = braille.hyphenation()
            # Fix marker chars not preceded by newlines
            toc_marker_regexp = re.compile('[^\n][%s%s][0-9]+' % (self._TOC_MARKER_CHAR,
                                                                  self._PAGE_START_CHAR) +
                                           self._END_MARKER_CHAR, re.MULTILINE)
            while True:
                match = toc_marker_regexp.search(text)
                if match is None:
                    break
                n = match.start() + 1
                text = text[:n] + '\n' + text[n:]
                hyphenation = hyphenation[:n] + self.HYPH_NO + hyphenation[n:]
            # Line breaking
            hfill = self._HFILL
            hfill_len = len(hfill)
            page_strings = text.split('\f')

            def split(page):
                lines = page.split('\n')
                if lines[-1] == u'':
                    lines = lines[:-1]
                return lines
            pages = [split(p) for p in page_strings]
            double_page = False
            if page_width:
                for i in range(len(pages)):
                    lines = []

                    def add_line(l, center=False, no_page_break=False):
                        while True:
                            pos = l.find(hfill)
                            if pos < 0:
                                break
                            fill_len = page_width - len(l) + hfill_len
                            l = l[:pos] + '⠀' * fill_len + l[pos + hfill_len:]
                        if center and len(l) < page_width:
                            l = l.strip(' ⠀' + self._CENTER_CHAR)
                            l = '⠀' * ((page_width - len(l)) // 2) + l
                        if no_page_break and not l.startswith(self._NO_PAGE_BREAK_CHAR):
                            l = self._NO_PAGE_BREAK_CHAR + l
                        lines.append(l)
                    for line in pages[i]:
                        no_page_break = False
                        while line.startswith(self._NO_PAGE_BREAK_CHAR):
                            no_page_break = True
                            line = line[1:]
                            hyphenation = hyphenation[1:]
                        mark = self._text_mark(line)
                        if mark:
                            marker, arg = mark
                            if marker == self._DOUBLE_PAGE_CHAR:
                                double_page = True
                            elif marker == self._PAGE_END_CHAR:
                                double_page = False
                            if marker not in (self._INDENTATION_CHAR, self._NEXT_INDENTATION_CHAR,
                                              self._RESTART_INDENTATION_CHAR,
                                              self._NO_PAGE_BREAK_CHAR,):
                                add_line(line)
                                hyphenation = hyphenation[len(line) + 1:]
                                continue
                        pos = line.rfind(self._RESTART_INDENTATION_CHAR)
                        if pos >= 0:
                            line = line[pos + 1:]
                            hyphenation = hyphenation[pos + 1:]
                        prefix_len = 0
                        while prefix_len < len(line) and line[prefix_len] == self._INDENTATION_CHAR:
                            prefix_len += 1
                        next_prefix_len = prefix_len
                        while True:
                            start = line.find(self._NEXT_INDENTATION_CHAR)
                            if start < 0:
                                break
                            end = start + 1
                            while end < len(line) and line[end] == self._NEXT_INDENTATION_CHAR:
                                end += 1
                            line = line[:start] + line[end:]
                            hyphenation = hyphenation[:start] + hyphenation[end:]
                            next_prefix_len += end - start
                        prefix = ' ' * next_prefix_len
                        prefix_limit = page_width // 2
                        if next_prefix_len > prefix_limit:
                            prefix = prefix[:prefix_limit]
                        hyphenation_prefix = self.HYPH_NO * len(prefix)
                        if prefix_len > 0:
                            line = ' ' * prefix_len + line[prefix_len:]
                        if len(line) > prefix_len and line[prefix_len] == self._CENTER_CHAR:
                            center = True
                            width = page_width - 2 * prefix_len
                            line = line[prefix_len + 1:]
                            prefix += self._CENTER_CHAR
                            hyphenation_prefix += self.HYPH_NO
                        else:
                            center = False
                            width = page_width
                        if len(line) > prefix_len and line[prefix_len] == self._NO_PAGE_BREAK_CHAR:
                            line = line[:prefix_len] + line[prefix_len + 1:]
                            hyphenation = hyphenation[:prefix_len] + hyphenation[prefix_len + 1:]
                            no_page_break = True
                        if no_page_break:
                            prefix = self._NO_PAGE_BREAK_CHAR + prefix
                            hyphenation_prefix = self.HYPH_NO + hyphenation_prefix
                        while len(line) > width and not double_page:
                            pos = width
                            if hyphenation[pos] not in (self.HYPH_WS, self.HYPH_NEMETH_WS,):
                                pos -= 1
                                while (pos > 0 and
                                       hyphenation[pos] in (self.HYPH_NO,
                                                            self.HYPH_NEMETH_NUMBER,)):
                                    pos -= 1
                            if pos == 0:
                                pos = width
                                while line[pos - 1] == hfill[0]:
                                    pos -= 1
                                add_line(line[:pos], center, no_page_break)
                                line = prefix + line[pos:]
                                hyphenation = hyphenation_prefix + hyphenation[pos:]
                            elif hyphenation[pos] == self.HYPH_YES:
                                add_line(line[:pos] + self.text(context, '-', lang=lang).text(),
                                         center, no_page_break)
                                line = prefix + line[pos:]
                                hyphenation = hyphenation_prefix + hyphenation[pos:]
                            elif hyphenation[pos] == self.HYPH_WS:
                                add_line(line[:pos], center, no_page_break)
                                line = prefix + line[pos + 1:]
                                hyphenation = hyphenation_prefix + hyphenation[pos + 1:]
                            elif hyphenation[pos] == self.HYPH_CZECH_MATH_WS:
                                add_line(line[:pos + 1], center, no_page_break)
                                line = prefix + line[pos:]
                                hyphenation = hyphenation_prefix + hyphenation[pos:]
                            elif hyphenation[pos] == self.HYPH_NEMETH_WS:
                                if line[pos] in _braille_whitespace:
                                    add_line(line[:pos], center, no_page_break)
                                    line = line[pos + 1:]
                                    hyphenation = hyphenation[pos + 1:]
                                else:
                                    pos += 1
                                    add_line(line[:pos], center, no_page_break)
                                    line = line[pos:]
                                    hyphenation = hyphenation[pos:]
                                if line:
                                    line = '⠀' * 2 + line
                                    hyphenation = self.HYPH_NO * 2 + hyphenation
                                    prefix_len += 2
                                    if prefix:
                                        line = prefix + line
                                        hyphenation = hyphenation_prefix + hyphenation
                            else:
                                raise Exception("Program error", hyphenation[pos])
                            if len(line) > prefix_len:
                                if hyphenation[prefix_len] == self.HYPH_NEMETH_NUMBER:
                                    n = prefix_len
                                    if line[n] == '⠤':
                                        n += 1
                                    if len(line) > n and line[n] != '⠼':
                                        line = line[:n] + '⠼' + line[n:]
                                        hyphenation = (hyphenation[:n] + self.HYPH_NO +
                                                       hyphenation[n:])
                        pos = line.find(hfill)
                        if pos >= 0:
                            fill_len = (page_width - len(line) + hfill_len)
                            line = (line[:pos] + '⠀' * fill_len + line[pos + hfill_len:])
                            hyphenation = (hyphenation[:pos] + self.HYPH_NO * fill_len +
                                           hyphenation[pos + hfill_len:])
                        add_line(line, center, no_page_break)
                        hyphenation = hyphenation[len(line) + 1:]
                    pages[i] = lines
                    hyphenation = hyphenation[1:]
            else:
                for i in range(len(pages)):
                    pages[i] = [line.replace(hfill, ' ') for line in pages[i]]
            # Page breaking
            if page_height:
                context.reset_page_number()
                if left_status_line or right_status_line:
                    page_height -= 1
                new_pages = []
                repeated_lines = []
                repeated_lines_activated = [False]

                def add_page(page):
                    lines = []

                    def add_line(l, line_list, check=False):
                        if __debug__ and check:
                            if self._RE_MARKER_MATCHER.search(l) is not None:
                                raise BrailleError("Marker in output", (l, page,))
                        line_list.append(l)
                    line_limit = page_height
                    while page:
                        mark = self._text_mark(page[0])
                        if ((mark is not None and
                             mark[0] in (self._SOFT_NEWLINE_CHAR, self._NEW_PAGE_CHAR))):
                            page.pop(0)
                        else:
                            break
                    page_len = len(page)
                    if page_len == 0:
                        return
                    best_priority = '9'
                    n = 0
                    i = n_repeated_lines = len(repeated_lines) if repeated_lines_activated[0] else 0
                    if context.double_page() == 'left' and context.page_number() % 2 == 0:
                        line_limit = 0
                    if i > 0:
                        if i >= page_height:
                            i = 0
                        else:
                            for l in repeated_lines:
                                if self._text_mark(l) is not None:
                                    add_line(l, lines)
                    page_start = None
                    cond_line_limit = None
                    while i < page_height and n < page_len:
                        l = page[n]
                        n += 1
                        mark = self._text_mark(l)
                        if mark is None:
                            i += 1
                            cond_line_limit = None
                        else:
                            marker, arg = mark
                            if marker == self._PAGE_START_CHAR:
                                if page_start is None:
                                    page_start = n
                                if i > n_repeated_lines:
                                    priority = arg
                                    if priority <= best_priority:
                                        line_limit = i
                                        best_priority = priority
                            elif marker == self._PAGE_END_CHAR:
                                line_limit = page_height
                                best_priority = '9'
                                repeated_lines[:] = []
                            elif marker == self._PAGE_START_REPEAT_CHAR:
                                repeated_lines[:] = page[page_start:n - 1]
                                repeated_lines_activated[0] = False
                            elif marker == self._DOUBLE_PAGE_CHAR:
                                if i > 0:
                                    line_limit = i
                                    break
                            elif marker == self._NEW_PAGE_CHAR:
                                line_limit = i
                                break
                            elif marker == self._SOFT_NEWLINE_CHAR:
                                i += 1
                            if marker == self._NO_PAGE_BREAK_CHAR:
                                if cond_line_limit is None:
                                    cond_line_limit = i
                                i += 1
                            else:
                                cond_line_limit = None
                    if cond_line_limit is not None and cond_line_limit > 0:
                        line_limit = cond_line_limit
                    page.reverse()
                    facing_lines = []
                    while page and len(lines) < line_limit:
                        l = page.pop()
                        mark = self._text_mark(l)
                        if mark is not None and mark[0] == self._NO_PAGE_BREAK_CHAR:
                            l = l[1:]
                            mark = self._text_mark(l)
                        if mark is None or mark == (self._SOFT_NEWLINE_CHAR, ''):
                            if mark is not None:
                                l = ''
                            if context.double_page() == 'left':
                                add_line(l[:page_width], lines, True)
                                add_line(l[page_width:], facing_lines, True)
                            else:
                                add_line(l, lines, True)
                        else:
                            marker, arg = mark
                            if marker == self._TOC_MARKER_CHAR:
                                page_number = unistr(context.page_number())
                                element = context.toc_element(arg)
                                element.set_page_number(page_number)
                                if isinstance(element, Section):
                                    exported = self.text(context, element.title(), reformat=True)
                                else:
                                    exported = element.export(context)
                                text = exported.text()
                                if text and text[0] == self._TOC_MARKER_CHAR:
                                    text = text.split(self._END_MARKER_CHAR)[1]
                                pos = text.find('\n')
                                if pos >= 0:
                                    text = text[:pos]
                                context.set_page_heading(_Braille(text))
                            elif marker == self._PAGE_START_REPEAT_CHAR:
                                repeated_lines_activated[0] = True
                            elif marker == self._PAGE_END_CHAR:
                                if context.double_page() == 'left':
                                    add_line(mark, facing_lines)
                                    break
                                elif context.double_page() == 'right':
                                    context.set_double_page(None)
                                    break
                            elif marker == self._DOUBLE_PAGE_CHAR:
                                context.set_double_page('left')
                    page_number = context.page_number()
                    status_line = right_status_line if page_number % 2 else left_status_line
                    lines = lines + [''] * (page_height - len(lines))
                    if status_line:
                        exported_status_line = status_line.export(context).text()
                        while True:
                            match = toc_marker_regexp.search(exported_status_line)
                            if match is None:
                                break
                            exported_status_line = (exported_status_line[:match.start() + 1] +
                                                    exported_status_line[match.end():])
                        # Hack: We have to center status line text manually here.
                        # Of course, this won't work in a generic case and we
                        # make just basic precautions.
                        if isinstance(status_line, Container):
                            c = status_line.content()
                            if c and isinstance(c[0], PageNumber):
                                pos = exported_status_line.find(u'⠀')
                                if pos > 0:
                                    title = exported_status_line[pos:].strip(u'⠀ ')
                                    text_len = len(title) + pos
                                    fill = (page_width - text_len) // 2
                                    exported_status_line = (exported_status_line[:pos] +
                                                            u'⠀' * fill + title)
                            elif c and isinstance(c[-1], PageNumber):
                                pos = exported_status_line.rfind(u'⠀')
                                if pos >= 0 and pos != len(exported_status_line) - 1:
                                    title = exported_status_line[:pos].strip(u'⠀ ')
                                    text_len = len(title) + (len(exported_status_line) - pos)
                                    fill_2 = (page_width - text_len) // 2
                                    fill_1 = page_width - text_len - fill_2
                                    exported_status_line = (u'⠀' * fill_1 + title + u'⠀' * fill_2 +
                                                            exported_status_line[pos + 1:])
                        add_line(exported_status_line, lines, True)
                    new_pages.append(lines)
                    context.advance_page_number()
                    page.reverse()
                    if facing_lines:
                        page[0:0] = facing_lines
                    if context.double_page() == 'left':
                        context.set_double_page('right')
                    elif context.double_page() == 'right':
                        context.set_double_page('left')
                for page in pages:
                    page_lengths = [len(page)]
                    while page_lengths[-1] > 0:
                        add_page(page)
                        page_lengths.append(len(page))
                        if ((len(page_lengths) >= 3 and
                             page_lengths[-1] == page_lengths[-2] == page_lengths[-3])):
                            raise Exception("Page breaking failed", page_height)
                pages = new_pages
            else:
                for i in range(len(pages)):
                    pages[i] = [line for line in pages[i] if self._text_mark(line) is None]
            return pages
        # Two-pass export in order to get page numbers in table of contents
        run_export()
        pages = run_export()
        # Device character set transformation
        final_text = '\f'.join(['\n'.join(p) for p in pages])
        if final_text and final_text[-1] != '\f':
            final_text += '\f'
        output = ''
        for c in final_text:
            try:
                output += device_table[c]
            except KeyError:
                context.log(_("Character %r can't be represented on "
                              'given output device: "%s"',
                              c, output[-50:]), kind=lcg.ERROR)
                output += '?'
        device_init = printer_properties.get('device_init', presentation.device_init)
        if device_init is not None:
            inner = presentation.inner_margin.size()
            outer = presentation.outer_margin.size()
            top = presentation.top_margin.size()
            bottom = presentation.bottom_margin.size()
            output = device_init(page_width, page_height, inner, outer, top, bottom) + output
        device_finish = printer_properties.get('device_finish', presentation.device_finish)
        if device_finish is not None:
            output += device_finish
        return output

    # Basic utilitites

    def concat(self, *items):
        return _Braille(''.join([i.text() for i in items]),
                        ''.join([i.hyphenation() for i in items]))

    _per_cent_regexp = re.compile('([ ⠀]+)⠼[⠏⠗]')

    def text(self, context, text, lang=None, reformat=False):
        """Return 'text' converted to Unicode Braille characters.

        Arguments:

          context -- current 'Context' instance
          text -- text to convert; unicode
          lang -- target language as an ISO 639-1 Alpha-2 lowercase
            language code or 'None'
          reformat -- iff true, make some 'text' sanitization

        """
        assert isinstance(context, self.Context), context
        assert isinstance(text, basestring), text
        assert lang is None or isinstance(lang, basestring), lang
        if lang is None:
            lang = context.lang()
        if reformat:
            text = self._reformat_text(context, text)
        if not text:
            return _Braille('', '')
        if self._text_mark(text) is not None:
            return _Braille(text)
        compactness = context.compactness()
        if compactness.get('lower'):
            text = text.lower()
        if compactness.get('plain'):
            form = louis.plain_text
        else:
            form = context.form()
        discarded_prefix = compactness.get('prefix')
        tables = context.tables(lang)
        if form != louis.plain_text and lang == 'cs':
            # liblouis doesn't handle this so we have to handle it ourselves.
            bold = form & louis.bold
            italic = form & louis.italic
            underline = form & louis.underline
            typeform = None
        else:
            typeform = [form] * len(text)
        # Using typeform without context information is incorrect since there
        # is no guarantee that `text' isn't directly attached to another text.
        # But hopefully this simplification here doesn't cause real use
        # problems.
        braille = louis.translateString(tables, text, typeform=copy.copy(typeform),
                                        mode=(louis.dotsIO + louis.ucBrl))
        whitespace = self._whitespace
        if typeform is None:
            if italic:
                braille = '⠔⠨' + braille + '⠨⠔'
            if underline:
                compact = (form == louis.underline)
                if compact:
                    for c in braille:
                        if c in whitespace:
                            compact = False
                            break
                if compact:
                    braille = '⠸' + braille
                else:
                    braille = '⠔⠸' + braille + '⠸⠔'
            if bold:
                braille = '⠔⠰' + braille + '⠰⠔'
        hyphenation_table = context.hyphenation_table(lang)
        if hyphenation_table is None or form != louis.plain_text:
            hyphenation = ''
            for c in braille:
                hyphenation += (self.HYPH_WS if c in whitespace else self.HYPH_NO)
        else:
            hyphenation_tables = tables + [hyphenation_table]
            braille_text = louis.translateString(tables, text, typeform=copy.copy(typeform))
            start = end = 0
            length = len(braille_text)
            hyphenation = ''
            hyphenation_forbidden = False
            unbreakable_characters = self._unbreakable_characters
            while end < length:
                if braille_text[end] in unbreakable_characters:
                    hyphenation_forbidden = True
                    end += 1
                elif braille_text[end] not in whitespace:
                    end += 1
                else:
                    if end > start:
                        if hyphenation_forbidden:
                            hyphenation += self.HYPH_NO * (end - start)
                            hyphenation_forbidden = False
                        else:
                            try:
                                hyphenation += louis.hyphenate(hyphenation_tables,
                                                               braille_text[start:end], mode=1)
                            except RuntimeError:
                                hyphenation += self.HYPH_NO * (end - start)
                    hyphenation += self.HYPH_WS
                    start = end = end + 1
            if end > start:
                if hyphenation_forbidden:
                    hyphenation += self.HYPH_NO * (end - start)
                else:
                    word = braille_text[start:end]
                    try:
                        hyphenation += louis.hyphenate(hyphenation_tables, word, mode=1)
                    except Exception as e:
                        # liblouis may crash on some patterns
                        context.log("`%s' can't be hyphenated: %s" % (word, e,), kind=lcg.WARNING)
                        hyphenation += '0' * (end - start)
        # Per cent & per mille formatting may not work properly for Czech in
        # liblouis so let's fix it here:
        if lang == 'cs':
            while True:
                match = self._per_cent_regexp.search(braille)
                if not match:
                    break
                start, end = match.span(1)
                braille = braille[:start] + braille[end:]
                hyphenation = hyphenation[:start] + hyphenation[end:]
        while True:
            match = _unknown_char_regexp.search(braille)
            if match is None:
                break
            start, end = match.start(0), match.end(0)
            unknown = self.braille_unknown_char(match.group(1), (text, lang,))
            braille = braille[:start] + unknown + braille[end:]
            hyphenation = hyphenation[:start] + '0' * len(unknown) + hyphenation[end:]
        assert len(braille) == len(hyphenation), (braille, hyphenation,)
        if discarded_prefix and braille.startswith(discarded_prefix):
            n = len(discarded_prefix)
            braille, hyphenation = braille[n:], hyphenation[n:]
        discarded_suffix = compactness.get('suffix')
        if discarded_suffix and braille.endswith(discarded_suffix):
            n = len(discarded_suffix)
            braille, hyphenation = braille[:-n], hyphenation[:-n]
        xprefix = compactness.get('xprefix')
        if xprefix:
            braille = xprefix + '⠀' + braille
            hyphenation = (len(xprefix) + 1) * self.HYPH_NO + hyphenation
        xsuffix = compactness.get('xsuffix')
        if xsuffix:
            braille = braille + '⠀' + xsuffix
            hyphenation = (len(xsuffix) + 1) * self.HYPH_NO + hyphenation
        return _Braille(braille, hyphenation)

    def _newline(self, context, number=1, soft=False, page_start=None, page_end=False):
        braille = _Braille('')
        if page_end:
            braille += self._marker(self._PAGE_END_CHAR)
        newline = self._marker(self._SOFT_NEWLINE_CHAR) if soft else _Braille('\n')
        braille += newline * number
        if page_start is not None:
            assert page_start >= 0 and page_start < 10, page_start
            braille += self._marker(self._PAGE_START_CHAR, page_start)
        return braille

    def _ensure_newlines(self, context, exported, number=1):
        real_number = 0
        text = exported.text()
        while real_number < number and len(text) > real_number and text[-real_number - 1] == '\n':
            real_number += 1
        n = number - real_number
        return _Braille(text + '\n' * n, exported.hyphenation() + self.HYPH_NO * n)

    def _indent(self, exported, indentation, init_indentation=None, center=False,
                no_page_break=False, first_indented=0, restart=False):
        if init_indentation is None:
            init_indentation = indentation
        text = exported.text()
        hyphenation = exported.hyphenation()
        new_text = ''
        new_hyphenation = ''
        if no_page_break and not text.startswith(self._NO_PAGE_BREAK_CHAR):
            new_text += self._NO_PAGE_BREAK_CHAR
            new_hyphenation += self.HYPH_NO
        if center:
            new_text += self._CENTER_CHAR
            new_hyphenation += self.HYPH_NO
        lines = text.split('\n')
        # Skip initial lines
        intro = '\n'.join(lines[:first_indented])
        n = len(intro)
        new_text += intro
        new_hyphenation += hyphenation[:n]
        # Indent the rest of the lines
        space = self._INDENTATION_CHAR * init_indentation
        if restart:
            space = self._RESTART_INDENTATION_CHAR + space
        space_hyphenation = self.HYPH_NO * len(space)
        if indentation > init_indentation:
            diff = indentation - init_indentation
            space += self._NEXT_INDENTATION_CHAR * diff
            space_hyphenation += self.HYPH_NO * diff
        first_line = first_indented == 0
        for l in lines[first_indented:]:
            if first_line:
                first_line = False
            else:
                new_text += '\n'
                n += 1
                new_hyphenation += self.HYPH_NO
            if l:
                if l != self._SOFT_NEWLINE_CHAR:
                    new_text += space
                    new_hyphenation += space_hyphenation
                new_text += l
                m = n
                n += len(l)
                new_hyphenation += hyphenation[m:n]
        # All right?
        assert n == len(hyphenation), (n, len(hyphenation),)
        assert len(new_text) == len(new_hyphenation), \
            (new_text, len(new_text), new_hyphenation, len(new_hyphenation),)
        return _Braille(new_text, new_hyphenation)

    def _list_item_prefix(self, context, lang=None):
        level = context.list_level
        if level == 1:
            prefix = _Braille('⠸⠲⠀')
        elif level == 2:
            prefix = _Braille('⠸⠔⠀')
        else:
            prefix = self.text(context, '- ', lang=lang)
        return prefix

    def _separator(self, context):
        return ' - '

    def _marker(self, marker, argument=''):
        mark = super(BrailleExporter, self)._marker(marker, argument)
        return _Braille(mark)

    # Content element export methods (defined by _define_export_methods).

    def _export_text_content(self, context, element):
        text = context.alternate_text(element)
        return self.text(context, text, lang=element.lang(), reformat=True)

    def _export_new_page(self, context, element):
        return _Braille('\f', self.HYPH_NO)

    def _export_horizontal_separator(self, context, element, width=64):
        return _Braille('\n', self.HYPH_NO)

    def _export_title(self, context, element):
        title = super(BrailleExporter, self)._export_title(context, element)
        return self.text(context, title, lang=element.lang())

    def _export_page_number(self, context, element):
        return self.text(context, unistr(context.page_number()), lang=element.lang())

    def _export_page_heading(self, context, element):
        return context.page_heading()

    def _page_formatter(self, context, **kwargs):
        return self.text(context, unistr(context.page_number()))

    def _export_section(self, context, element):
        level = len(element.section_path())
        center = False
        if level == 1:
            center = True
            indentation = 3
        elif level == 2:
            indentation = 5
        else:
            indentation = 7
        toc_marker = context.add_toc_marker(element)
        context.position_info.append(element.title())
        try:
            title = self.text(context, element.title(), element.lang(), reformat=True)
            if level > 1 or (element.content() and isinstance(element.content()[0], Section)):
                n_newlines = 1
            else:
                n_newlines = 2
            return self.concat(self._marker(self._TOC_MARKER_CHAR, toc_marker),
                               self._indent(title, indentation, center=center),
                               self._newline(context, n_newlines),
                               self._export_container(context, element))
        finally:
            context.position_info.pop()

    # Inline constructs (text styles).

    def _inline_braille_export(self, context, element, form=None, lang=None, hyphenate=None):
        with context.let_lang(lang):
            with context.let_form(form):
                with context.let_hyphenate(hyphenate):
                    exported = self._export_container(context, element)
        return exported

    def _export_emphasized(self, context, element):
        return self._inline_braille_export(context, element, louis.italic)

    def _export_strong(self, context, element):
        return self._inline_braille_export(context, element, louis.bold)

    def _export_code(self, context, element):
        return self._inline_braille_export(context, element)

    def _export_underlined(self, context, element):
        return self._inline_braille_export(context, element, louis.underline)

    def _export_superscript(self, context, element):
        lang = context.lang()
        braille = self._inline_braille_export(context, element)
        if lang == 'cs':
            braille.prepend('⠌', self.HYPH_NO)
            braille.append('⠱', self.HYPH_NO)
        return braille

    def _export_subscript(self, context, element):
        lang = context.lang()
        braille = self._inline_braille_export(context, element)
        if lang == 'cs':
            braille.prepend('⠡', self.HYPH_NO)
            braille.append('⠱', self.HYPH_NO)
        return braille

    def _export_citation(self, context, element):
        lang = element.lang(inherited=False) or context.sec_lang()
        hyphenate = (lang == context.lang())
        # We have to disable hyphenation as there is currently no easy way to
        # handle multilingual hyphenation characters in the export code.
        hyphenate = False
        return self._inline_braille_export(context, element, lang=lang, hyphenate=hyphenate)

    def _transform_link_content(self, context, element):
        return self._export_container(context, element)[0]

    def _transform_link_heading(self, context, heading):
        return heading.export(context)[0]

    def _link_content_is_url(self, context, label):
        http_prefix = self.text(context, 'http:')[0]
        return label.startswith(http_prefix)

    def _export_link(self, context, element):
        label = self._export_container(context, element)
        if not label:
            target = element.target(context)
            if isinstance(target, (ContentNode, Section)):
                label = target.heading().export(context)
            elif isinstance(target, Resource):
                label = self.text(context, target.title() or target.filename(), reformat=True)
            elif isinstance(target, element.ExternalTarget):
                label = self.text(context, target.title() or target.uri(), reformat=True)
        return label

    # Tables

    def _export_table(self, context, element, recursive=False):
        exception = None

        def export(element, explanation):
            if isinstance(element, Table):
                try:
                    exported = super(BrailleExporter, self)._export_table(context, element)
                finally:
                    context.table_column_compactness().clear()
            else:
                exported = self.export_element(context, element)
            if explanation is not None and not recursive:
                text = self.text(context, explanation, reformat=True)
                exported = self.concat(text, self._newline(context, 2), exported)
            return exported
        transformations = element.transformations()
        try:
            result = export(element, None)
        except TableTooWideError as e:
            if 'transpose' in transformations:
                try:
                    result = export(self._transposed_table(context, element),
                                    _("The table is transposed."))
                except TableTooWideError as e:
                    exception = e
            else:
                exception = e
        if exception is not None:
            if 'row-expand' in transformations:
                result = export(self._expanded_table(context, element, 'row'),
                                _("The table is expanded by rows."))
            elif 'column-expand' in transformations:
                result = export(self._expanded_table(context, element, 'column'),
                                _("The table is expanded by columns."))
            elif 'split' in transformations:
                n_cols = max([len(c.content()) for c in element.content()
                              if isinstance(c, TableRow)])
                for i in range(n_cols - 1, 1, -1):
                    table_1, table_2 = self._split_table(context, element, i)
                    try:
                        exported = export(table_1, _("The table is vertically split."))
                    except TableTooWideError:
                        continue
                    result = self.concat(exported, self._newline(context),
                                         self._export_table(context, table_2, recursive=True))
                    break
                else:
                    context.log(unistr(exception), kind=lcg.ERROR)
                    return _Braille('')
            else:
                context.log(unistr(exception), kind=lcg.ERROR)
                return _Braille('')
        return result

    def _export_table_cell(self, context, element):
        exported = super(BrailleExporter, self)._export_table_cell(context, element)
        text, hyphenation = exported.text(), exported.hyphenation()
        text = text.rstrip('\n' + self._SOFT_NEWLINE_CHAR)
        return _Braille(text, hyphenation[:len(text)])

    def _transposed_table(self, context, element):
        content = [c.content() for c in element.content() if isinstance(c, TableRow)]
        n_rows = max([len(c) for c in content])
        transposed = []
        for i in range(n_rows):
            row = []
            for c in content:
                try:
                    row.append(c[i])
                except IndexError:
                    row.append(TableCell(TextContent('')))
            transposed.append(TableRow(row))
        return Table(transposed, title=element.title(), transformations=('facing',))

    def _expanded_table(self, context, element, direction):
        content = [c.content() for c in element.content() if isinstance(c, TableRow)]
        top_label = content[0][0]
        items = []

        def cell(label, value):
            return Container((label, TextContent(': '), value,))

        def add_list(label, headings, cells):
            cells = list(cells) + [TextContent('')] * (len(headings) - len(cells))
            subitems = [cell(*lv) for lv in zip(headings, cells)]
            items.append(Container((cell(top_label, label), ItemizedList(subitems),)))
        if direction == 'row':
            headings = content[0][1:]
            for row in content[1:]:
                add_list(row[0], headings, row[1:])
        elif direction == 'column':
            headings = [c[0] for c in content[1:]]

            def get_cell(row, i):
                try:
                    return row[i]
                except IndexError:
                    return TableCell(TextContent(''))
            for i in range(1, len(content[0])):
                add_list(content[0][i], headings, [get_cell(row, i) for row in content[1:]])
        else:
            raise Exception("Program Error", direction)
        return ItemizedList(items)

    def _split_table(self, context, element, split_column):
        title = element.title()
        content = element.content()
        content_1 = []
        content_2 = []
        for row in content:
            if isinstance(row, TableRow):
                cells = row.content()
                content_1.append(TableRow(cells[:split_column]))
                content_2.append(TableRow([cells[0]] + list(cells[split_column:])))
            else:
                content_1.append(row)
                content_2.append(row)
        return (Table(content_1, title=title, transformations=()),
                Table(content_2, title=title, transformations=('split',)))

    def _vertical_cell_separator(self, context, position):
        return _Braille('', '') if position <= 0 else _Braille('  ')

    def _table_row_separator(self, context, width, cell_widths, row_number, vertical_separator,
                             last_row, heading_present):
        if row_number <= 0:
            filler = u'⠶' if row_number == 0 else u'⠛'
            separator = self.concat(_Braille(filler * width), self._newline(context))
        elif row_number == 1 and cell_widths and heading_present:
            cell_separators = [_Braille(u'⠐' + u'⠒' * (w - 1) if c else ' ' * w, self.HYPH_NO * w)
                               for w, c in zip(cell_widths, last_row)]
            elements = [cell_separators[0]]
            for c in cell_separators[1:]:
                elements.append(vertical_separator)
                elements.append(c)
            elements.append(self._newline(context))
            elements.append(self._marker(self._PAGE_START_REPEAT_CHAR))
            elements.append(self._newline(context))
            separator = self.concat(*elements)
        else:
            separator = None
        return separator

    def _set_table_column_widths(self, context, element, extra_width, widths):
        max_width = context.node_presentation().page_width.size()
        super(BrailleExporter, self)._set_table_column_widths(context, element, extra_width, widths)
        simple_total_width = sum(widths, extra_width)
        if simple_total_width <= max_width:
            return
        # Table too wide, let's try to shorten the columns
        cells = [r.content() for r in element.content() if isinstance(r, TableRow)]
        n_cells = len(widths)
        context_compactness = context.compactness()
        orig_context_compactness = copy.copy(context_compactness)
        column_compactness = {}
        total_width = simple_total_width
        export = self._export_table_cell
        table_cell_width = self._table_cell_width
        table_intro = None

        def prefix(cell, common):
            i = 0
            for i in range(min(len(cell), len(common))):
                if cell[i] != common[i]:
                    break
            return common[:i]

        def suffix(cell, common):
            i = 0
            for i in range(min(len(cell), len(common))):
                if cell[-i - 1] != common[-i - 1]:
                    break
            return common[len(common) - i:]

        def export_cells(column, compactness):
            context_compactness.clear()
            context_compactness.update(compactness)
            exported = []
            for row in cells:
                if len(row) > column:
                    exported.append(export(context, row[column]))
                else:
                    exported.append(_Braille(''))
            return exported

        def adjust_widths(max_w, total_width=total_width):
            if total_width <= max_w:
                return True
            ws = copy.copy(widths)
            len_0 = len(cells[0])
            for level in ('plain', 'lower', 'prefix', 'suffix',):
                for i in range(n_cells):
                    w = new_w = ws[i]
                    compactness = column_compactness.get(i, {})
                    c = copy.copy(compactness)
                    if level in ('plain', 'lower',):
                        c[level] = True
                        exported_column = export_cells(i, c)
                        new_w = max([table_cell_width(context, element, cell)
                                     for cell in exported_column])
                    elif level in ('prefix', 'suffix',):
                        if i < len_0 and isinstance(cells[0][i], TableHeading):
                            exported_column = export_cells(i, c)
                            braille_column = [b.text() for b in exported_column]
                            n_rows = len(braille_column)
                            if n_rows > 1:
                                heading_width = table_cell_width(context, element,
                                                                 exported_column[0])
                                heading_available = w - heading_width - 1
                                if heading_available > 0:
                                    if level == 'prefix':
                                        f = prefix
                                        common = braille_column[1][:heading_available]
                                    elif level == 'suffix':
                                        f = suffix
                                        common = braille_column[1][-heading_available:]
                                    else:
                                        raise Exception("Program error", level)
                                    for j in range(2, n_rows):
                                        common = f(braille_column[j], common)
                                        if not common:
                                            break
                                    else:
                                        c[level] = common
                                        exported_column = export_cells(i, c)
                                        new_w = max([table_cell_width(context, element, cell)
                                                     for cell in exported_column[1:]]) - len(common)
                                        new_w = max(new_w,
                                                    heading_width + len(common.strip('⠀')) + 1)
                    else:
                        raise Exception("Invalid compactness level", level)
                    if new_w < w:
                        total_width -= (w - new_w)
                        column_compactness[i] = c
                        ws[i] = new_w
                        if total_width <= max_w:
                            for i in range(len(widths)):
                                widths[i] = ws[i]
                            return True
            return False
        try:
            adjusted = adjust_widths(max_width)
            if not adjusted:
                if 'facing' not in element.transformations() or not adjust_widths(max_width * 2):
                    # Future option: Try to use double-line rows.
                    max_row = None
                    max_len = -1
                    for row in cells:
                        e = [export(context, c) for c in row]
                        e_len = sum([len(i) for i in e])
                        if e_len > max_len:
                            max_row = e
                            max_len = e_len
                    info = '⠀'.join([c.text() for c in max_row])
                    raise TableTooWideError(info)
        finally:
            context_compactness.clear()
            context_compactness.update(orig_context_compactness)
        if not adjusted:
            intro_text = context.localize(_("The table is read across facing pages."))
            table_intro = self.text(context, intro_text)
            table_intro += self._newline(context)
            table_intro += self._marker(self._DOUBLE_PAGE_CHAR)
        context.set_table_column_compactness(column_compactness)
        return table_intro

    def _export_table_row(self, context, element):
        content = element.content()
        orig_compactness = copy.copy(context.compactness())
        table_column_compactness = context.table_column_compactness()
        exported = []
        for i in range(len(content)):
            compactness = copy.copy(orig_compactness)
            compactness.update(table_column_compactness.get(i, {}))
            context.set_compactness(compactness)
            exported.append(content[i].export(context))
            context.set_compactness(orig_compactness)
        return exported

    def _export_table_heading(self, context, element):
        compactness = context.compactness()
        prefix = compactness.get('prefix')
        suffix = compactness.get('suffix')
        if prefix or suffix:
            c = copy.copy(compactness)
            if prefix:
                c['xprefix'] = prefix.strip('⠀')
            if suffix:
                c['xsuffix'] = suffix.strip('⠀')
            context.set_compactness(c)
        exported = super(BrailleExporter, self)._export_table_heading(context, element)
        if prefix or suffix:
            context.set_compactness(compactness)
        return exported

    # Mathematics

    def _export_mathml(self, context, element):
        math_rules = context.node_presentation().braille_math_rules
        if math_rules == 'nemeth':
            result = self._export_mathml_nemeth(context, element)
            return result
        elif math_rules == 'nemeth-liblouis':
            return self._export_mathml_nemeth_liblouis(context, element)
        elif math_rules == 'czech':
            return self._export_mathml_czech(context, element)
        else:
            raise Exception("Unsupported math rules", math_rules)

    def _export_mathml_nemeth_liblouis(self, context, element):
        xml = element.content()
        braille = xml2braille(xml)
        hyphenation_list = [self.HYPH_WS if c == '⠀' else self.HYPH_NO for c in braille]
        return _Braille(braille, ''.join(hyphenation_list))

    def _export_mathml_nemeth(self, context, element):
        return mathml_nemeth(self, context, element)

    def _export_mathml_czech(self, context, element):
        class EntityHandler(element.EntityHandler):

            def __init__(self, *args, **kwargs):
                super(EntityHandler, self).__init__(*args, **kwargs)
                self._data = mathml.entities

            def __getitem__(self, key):
                return self._data.get(key, '?')
        entity_handler = EntityHandler()
        top = element.tree_content(entity_handler, transform=True)
        exporters = {}
        flags = []

        def current_style():
            for i in range(len(flags) - 1, -1, -1):
                if flags[i].startswith('style:'):
                    return flags[i]
            return ''

        def set_style(node):
            variant = node.get('mathvariant')
            if variant:
                bold = variant.find('bold') >= 0
                italic = variant.find('italic') >= 0
                if bold and italic:
                    f = 'style:bold+italic'
                elif bold:
                    f = 'style:bold'
                elif italic:
                    f = 'style:italic'
                else:
                    f = 'style:normal'
            elif node.tag == 'mi':
                # <mi> content should be in italic but it would make the
                # Braille output only larger and harder to read.
                # f = 'style:italic'
                f = ''
            else:
                f = ''
            flags.append(f)

        def unset_style():
            flags.pop()

        def node_value(node):
            value = node.text
            if value is None:
                # this may happen with unresolved entities
                value = '?'
            return value

        def child_nodes(node, exported=False):
            children = list(node)
            if exported:
                children = [export(c) for c in children]
            return children

        def attribute(node, name, default=None):
            return node.attrib.get(name, default)

        def op_translation(operator, node=None):
            translation = _mathml_operators.get(operator)
            op_form = None if translation is None else translation[0]
            op_braille = text_export(operator, node=node).text()
            # We prefer using liblouis translation since it should be the
            # primary source of Braille formatting and it should work for more
            # languages than just Czech.  But it returns something like
            # character code on unknown characters, we try to identify and
            # handle such a situation here.
            if (((not op_braille or op_braille.find(u'⠈⠀⠭') >= 0) and
                 translation is not None)):
                __, op_braille, hyphenation = translation
            else:
                # We use our own hyphenation rules, just to be sure (at least
                # for Czech).
                if len(op_braille) == 1:
                    hyphenation = self.HYPH_CZECH_MATH_WS
                else:
                    hyphenation = self.HYPH_NO * len(op_braille)
            if op_braille.find(u'⠈⠀⠭') >= 0:
                # Still a Unicode character?  We should do something about it.
                op_braille = self.braille_unknown_char(op_braille, operator)
                hyphenation = self.HYPH_NO * len(op_braille)
            if translation is not None:
                t_braille = translation[1]
                if t_braille[-1] in (' ', '⠀',) and op_braille[-1] not in (' ', '⠀',):
                    # We don't handle spacing in liblouis yet.
                    op_braille += '⠀'
                    hyphenation += self.HYPH_CZECH_MATH_WS
            return op_form, _Braille(op_braille, hyphenation)

        def text_export(text, node=None):
            if node is not None:
                set_style(node)
            style = current_style()
            form = 0
            if style.find('bold') >= 0:
                form |= louis.bold
            elif style.find('italic') >= 0:
                form |= louis.italic
            with context.let_form(form):
                braille = self.text(context, text, reformat=True).text()
            if node is not None:
                unset_style()
            return _Braille(braille, self.HYPH_NO * len(braille))

        def export(node, **kwargs):
            tag = node.tag
            e = exporters.get(tag)
            if e is None:
                result = text_export('<%s>' % (tag,))
            else:
                variant = attribute(node, 'mathvariant')
                if variant:
                    bold = variant.find('bold') >= 0
                    italic = variant.find('italic') >= 0
                    if bold and italic:
                        f = 'bold+italic'
                    elif bold:
                        f = 'bold'
                    elif italic:
                        f = 'italic'
                    else:
                        f = 'normal'
                    flags.append(f)
                result = e(node, **kwargs)
                if variant:
                    flags.pop()
            return result

        def child_export(node, separators=None):
            braille = _Braille('', '')
            children = child_nodes(node)
            op_form = None
            for i in range(len(children)):
                n = children[i]
                if n.tag == 'mo':
                    if i == 0 or op_form == 'infix':
                        op_form = 'prefix'
                    elif i == len(children) - 1:
                        op_form = 'postfix'
                    else:
                        op_form = (_mathml_operators.get((n.text or '').strip(), ('infix',))[0] or
                                   'infix')
                else:
                    op_form = None
                if braille and separators:
                    separator = separators[-1] if i > len(separators) else separators[i - 1]
                    hyph_separator = self.HYPH_CZECH_MATH_WS if len(separator) == 1 else None
                    braille.append(separator, hyph_separator)
                braille = braille + export(n, op_form=op_form)
            return braille

        def export_mi(node, **kwargs):
            text = node_value(node).strip()
            return text_export(text, node=node)

        def export_mn(node, **kwargs):
            text = node_value(node).replace(' ', '')
            braille = text_export(text)
            # We don't know what follows so we put the lower case letter prefix
            # here.  It should be present here only if lower case a-h follows;
            # this will be fixed in final MathML result processing.
            braille.append(u'⠐', self.HYPH_NO)
            return braille

        def export_mo(node, op_form=None, **kwargs):
            form = attribute(node, 'form', op_form)  # prefix, infix, postfix
            separator = attribute(node, 'separator')  # true, false
            # We should probably ignore these as Braille script has its own
            # rules of math line breaking:
            # linebreak = attribute(node, 'linebreak') # auto, newline, nobreak, goodbreak, badbreak
            # linebreakstyle = attribute(node, 'linebreakstyle')
            #                  # before, after, duplicate, infixlinebreakstyle
            op = node_value(node).strip()
            op_form, op_braille = op_translation(op)
            if form is None and op_form is not None:
                form = op_form
            if separator == 'true':
                if op_braille.text()[-1] not in (' ', '⠀',):
                    op_braille.append('⠀', self.HYPH_NO)
            elif form == 'infix':
                if op_braille.text()[0] not in (' ', '⠀',):
                    op_braille.prepend(' ', self.HYPH_NO)
            return op_braille

        def export_mtext(node, **kwargs):
            text = node_value(node).strip()
            # It's necessary to replace commas in order to distinguish
            # sequences from decimal numbers (consider x_{1,2}).
            pos = 0
            while True:
                pos = text.find(',', pos)
                if pos < 0:
                    break
                if pos + 1 < len(text) and text[pos + 1] != ' ':
                    pos += 1
                    text = text[:pos] + ' ' + text[pos:]
                pos += 1
            return text_export(text, node=node)

        def export_mspace(node, **kwargs):
            return text_export(' ')

        def export_ms(node, **kwargs):
            text = '"%s"' % (node_value(node).strip(),)
            return text_export(text, node=node)

        def export_mrow(node, **kwargs):
            return child_export(node)

        def export_mfrac(node, **kwargs):
            child_1, child_2 = child_nodes(node, exported=True)
            mfrac_flag = 'mfrac'
            if len(node.getiterator(mfrac_flag)) > 1:
                line = _Braille('⠻⠻')
            else:
                line = _Braille('⠻', self.HYPH_CZECH_MATH_WS)
            return _Braille('⠆') + child_1 + line + child_2 + _Braille('⠰')

        def export_msqrt(node, **kwargs):
            return _Braille('⠩', self.HYPH_CZECH_MATH_WS) + child_export(node) + _Braille('⠱')

        def export_mroot(node, **kwargs):
            base, root = child_nodes(node, exported=True)
            return (_Braille('⠠⠌') + root + _Braille('⠩', self.HYPH_CZECH_MATH_WS) + base +
                    _Braille('⠱'))

        def export_mstyle(node, **kwargs):
            break_style = attribute(node, 'infixlinebreakstyle')
            if break_style:  # before, after, duplicate
                flags.append('infixlinebreakstyle:' + break_style)
            set_style(node)
            result = child_export(node)
            unset_style()
            if break_style:
                flags.pop()
            return result

        def export_merror(node, **kwargs):
            return child_export(node)

        def export_mpadded(node, **kwargs):
            return child_export(node)

        def export_mphantom(node, **kwargs):
            braille = child_export(node)
            n = len(braille)
            return _Braille('⠀' * n)

        def export_menclose(node, **kwargs):
            return child_export(node)

        def export_msub(node, **kwargs):
            base, sub = child_nodes(node, exported=True)
            return base + _Braille('⠡') + sub + _Braille('⠱')

        def export_msup(node, **kwargs):
            base, sup = child_nodes(node, exported=True)
            return base + _Braille('⠌') + sup + _Braille('⠱')

        def export_msubsup(node, **kwargs):
            base, sub, sup = child_nodes(node, exported=True)
            return base + _Braille('⠌') + sub + _Braille('⠱⠡') + sup + _Braille('⠱')

        def export_munder(node, **kwargs):
            base, under = child_nodes(node, exported=True)
            return base + _Braille('⠠⠡') + under + _Braille('⠱')

        def export_mover(node, **kwargs):
            base_child, over_child = child_nodes(node)
            base = export(base_child)
            if ((over_child.tag == 'mo' and over_child.text.strip() == '¯' and
                 base_child.tag == 'mn')):
                braille = base + base
                braille.append('⠤')
            else:
                over = export(over_child)
                braille = base + over
            return braille

        def export_munder_mover(node, **kwargs):
            base, under, over = child_nodes(node, exported=True)
            return base + _Braille('⠠⠡') + under + _Braille('⠱⠠⠌') + over + _Braille('⠱')

        def export_maction(node, **kwargs):
            selection = attribute(node, 'selection')
            if not selection:
                selection = 1
            return export(child_nodes(node)[selection - 1])
        # def export_mmultiscripts(node, **kwargs):
        # def export_mtable(node, **kwargs):
        # def export_mtr(node, **kwargs):
        # def export_mlabeledtr(node, **kwargs):
        # def export_mtd(node, **kwargs):
        # def export_maligngroup(node, **kwargs):
        # def export_mstack(node, **kwargs):
        # def export_msgroup(node, **kwargs):
        # def export_msrow(node, **kwargs):
        # def export_msline(node, **kwargs):
        # def export_mscarries(node, **kwargs):
        # def export_mscarry(node, **kwargs):
        # def export_mlongdiv(node, **kwargs):
        for k, v in list(locals().items()):
            if k.startswith('export_'):
                exporters[k[len('export_'):]] = v
        e = child_export(top)
        braille, hyphenation = e.text(), e.hyphenation()
        l = len(braille)
        i = 0
        while i < l:
            if braille[i] == '⠐' and (i + 1 == l or braille[i + 1] not in '⠁⠃⠉⠙⠑⠋⠛⠓'):
                braille = braille[:i] + braille[i + 1:]
                hyphenation = hyphenation[:i] + hyphenation[i + 1:]
                l -= 1
                if i + 1 < l and braille[i] == '⠼' and braille[i + 1] not in '⠏⠗':
                    # This can happen in periodic numbers (see export_mover)
                    braille = braille[:i] + braille[i + 1:]
                    hyphenation = hyphenation[:i] + hyphenation[i + 1:]
                    l -= 1
            i += 1
        return _Braille(braille, hyphenation)
