# -*- coding: utf-8 -*-
#
# Copyright (C) 2012, 2013 Brailcom, o.p.s.
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

"""Export to Braille notation.
"""

import copy
import imp
import os
import re
import string

import louis

from lcg import Presentation, UFont, USpace, ContentNode, Section, Resource, PageNumber, \
    Container, TranslatableTextFactory
import entities

_ = TranslatableTextFactory('lcg')

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

from export import Exporter, FileExporter

def braille_presentation(presentation_file='presentation-braille.py'):
    """Return default braille presentation.

    Arguments:

      presentation_file -- base name of the presentation file to be used; string
      
    """
    presentation = Presentation()
    filename = os.path.join(os.path.dirname(__file__), 'styles', presentation_file)
    f = open(filename)
    confmodule = imp.load_module('_lcg_presentation', f, filename, ('.py', 'r', imp.PY_SOURCE))
    f.close()
    for o in dir(confmodule):
        if o[0] in string.lowercase and hasattr(presentation, o):
            setattr(presentation, o, confmodule.__dict__[o])
    return presentation


class BrailleError(Exception):
    """Exception raised on Braille formatting errors.

    The exception provides a human readable explanation message.

    """
    def __init__(self, message):
        """
        Arguments:

          message -- message explaining the error; unicode
          
        """
        assert isinstance(message, basestring), message
        super(BrailleError, self).__init__(message)

    def message(self):
        """Return message explaining the error; basestring.
        """
        return self.args[0]


class BrailleExporter(FileExporter, Exporter):
    "Transforming structured content objects to Braille output."
    
    _OUTPUT_FILE_EXT = 'brl'
    _INDENTATION_CHAR = '\ue010'
    _NEXT_INDENTATION_CHAR = '\ue011'

    class Context(Exporter.Context):

        def __init__(self, exporter, node, lang, tables={}, hyphenation_tables={},
                     **kwargs):
            super(BrailleExporter.Context, self).__init__(exporter, node, lang, **kwargs)
            assert isinstance(tables, dict), tables
            assert isinstance(hyphenation_tables, dict), hyphenation_tables
            self._tables = tables
            self._hyphenation_tables = hyphenation_tables
            self._page_number = 1
            self._form = [louis.plain_text]
            self._hyphenate = True
            self._removable_newlines = 0

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

        def set_form(self, form):
            self._form.append(self._form[-1] | form)

        def unset_form(self):
            self._form.pop()

        def set_hyphenate(self, hyphenate):
            old_hyphenate = self._hyphenate
            self._hyphenate = hyphenate
            return old_hyphenate

        def removable_newlines(self):
            return self._removable_newlines

        def set_removable_newlines(self, value):
            self._removable_newlines = value

    def __init__(self, *args, **kwargs):
        super(BrailleExporter, self).__init__(*args, **kwargs)
        self._unbreakable_characters = (string.punctuation + string.digits +
                                        self._braille_characters())
        self._whitespace = string.whitespace + ' \u2800'

    def _braille_characters(self):
        return string.join([unichr(i) for i in range(10240, 10496)], '')

    def export(self, context, recursive=False):
        # Presentation
        presentation_set = context.presentation()
        node = context.node()
        lang = context.lang()
        if presentation_set is None:
            presentation = node.presentation(lang) or Presentation()
        else:
            presentations = (Presentation(),
                             presentation_set.presentation(None, lang),
                             node.presentation(lang),)
            presentation = presentation_set.merge_presentations(presentations)
        page_width = presentation.page_width
        if page_width:
            assert isinstance(page_width, (UFont, USpace,)), page_width
            page_width = page_width.size()
        page_height = presentation.page_height
        if page_height:
            assert isinstance(page_height, (UFont, USpace,)), page_height
            page_height = page_height.size()
        left_status_line = presentation.left_page_footer or node.left_page_footer(lang)
        right_status_line = presentation.right_page_footer or node.right_page_footer(lang)
        device_table = presentation.device_output
        if device_table is None:
            device_table = {' ': '⠀', '\n': '\n', '\f': '\f'}
            for c in self._braille_characters():
                device_table[c] = c
        braille_tables = presentation.braille_tables
        hyphenation_tables = presentation.braille_hyphenation_tables
        context.set_tables(braille_tables, hyphenation_tables)
        # Export
        def run_export(page_height=page_height):
            text, hyphenation = super(BrailleExporter, self).export(context, recursive=recursive)
            assert len(text) == len(hyphenation)
            # Fix marker chars not preceded by newlines
            toc_marker_regexp = re.compile('[^\n]' + self._TOC_MARKER_CHAR, re.MULTILINE)
            while True:
                match = toc_marker_regexp.search(text)
                if match is None:
                    break
                n = match.start() + 1
                text = text[:n] + '\n' + text[n:]
                hyphenation = hyphenation[:n] + '0' + hyphenation[n:]
            # Line breaking
            hfill = self._HFILL
            page_strings = text.split('\f')
            pages = [p.split('\n') for p in page_strings]
            if page_width:
                for i in range(len(pages)):
                    lines = []
                    for line in pages[i]:
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
                        prefix_limit = page_width / 2
                        if next_prefix_len > prefix_limit:
                            prefix = prefix[:prefix_limit]
                        hyphenation_prefix = '0' * len(prefix)
                        if prefix_len > 0:
                            line = ' ' * prefix_len + line[prefix_len:]
                        while len(line) > page_width:
                            pos = page_width
                            if hyphenation[pos] != '2':
                                pos -= 1
                                while pos > 0 and hyphenation[pos] == '0':
                                    pos -= 1
                            if pos == 0:
                                lines.append(line[:page_width])
                                line = prefix + line[page_width:]
                                hyphenation = hyphenation_prefix + hyphenation[page_width:]
                            elif hyphenation[pos] == '1':
                                lines.append(line[:pos] + self.text(context, '-', lang=lang)[0])
                                line = prefix + line[pos:]
                                hyphenation = hyphenation_prefix + hyphenation[pos:]
                            elif hyphenation[pos] == '2':
                                lines.append(line[:pos])
                                line = prefix + line[pos + 1:]
                                hyphenation = hyphenation_prefix + hyphenation[pos + 1:]
                            elif hyphenation[pos] == '3':
                                lines.append(line[:pos + 1])
                                line = prefix + line[pos:]
                                hyphenation = hyphenation_prefix + hyphenation[pos:]
                            else:
                                raise Exception("Program error", hyphenation[pos])
                        pos = line.find(hfill)
                        if pos >= 0:
                            fill_len = (page_width - len(line) + len(hfill))
                            line = (line[:pos] + ' ' * fill_len + line[pos + len(hfill):])
                            hyphenation = (hyphenation[:pos] + '0' * fill_len +
                                           hyphenation[pos + len(hfill):])
                        lines.append(line)
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
                def add_page(page):
                    page.reverse()
                    lines = []
                    while page and len(lines) < page_height:
                        l = page.pop()
                        if l and l[0] == self._TOC_MARKER_CHAR:
                            marker = l[1:]
                            page_number = unicode(context.page_number())
                            context.toc_element(marker).set_page_number(context, page_number)
                        else:
                            lines.append(l)
                    page_number = context.page_number()
                    status_line = right_status_line if page_number % 2 else left_status_line
                    lines = lines + [''] * (page_height - len(lines))
                    if status_line:
                        exported_status_line, __ = status_line.export(context)
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
                                    fill = (page_width - text_len) / 2
                                    exported_status_line = (exported_status_line[:pos] +
                                                            u'⠀' * fill + title)
                            elif c and isinstance(c[-1], PageNumber):
                                pos = exported_status_line.rfind(u'⠀')
                                if pos >= 0 and pos != len(exported_status_line) - 1:
                                    title = exported_status_line[:pos].strip(u'⠀ ')
                                    text_len = len(title) + (len(exported_status_line) - pos)
                                    fill_2 = (page_width - text_len) / 2
                                    fill_1 = page_width - text_len - fill_2
                                    exported_status_line = (u'⠀' * fill_1 + title + u'⠀' * fill_2 +
                                                            exported_status_line[pos + 1:])
                        lines.append(exported_status_line)
                    new_pages.append(lines)
                    context.advance_page_number()
                    page.reverse()
                for page in pages:
                    while len(page) > page_height:
                        add_page(page)
                    # Final page (maybe it's empty)
                    removable_newlines = context.removable_newlines()
                    while page and removable_newlines > 0 and not page[-1]:
                        page = page[:-1]
                        removable_newlines -= 1
                    if page:
                        add_page(page)
                pages = new_pages
            else:
                for i in range(len(pages)):
                    pages[i] = [line for line in pages[i]
                                if not line or line[0] != self._TOC_MARKER_CHAR]
            return pages
        # Two-pass export in order to get page numbers in table of contents
        run_export()
        pages = run_export()
        # Device character set transformation
        final_text = string.join([string.join(p, '\n') for p in pages], '\f')
        if final_text and final_text[-1] != '\f':
            final_text += '\f'
        output = ''
        for c in final_text:
            try:
                output += device_table[c]
            except KeyError:
                raise BrailleError(_("Text can't be represented on given output device."))
        if presentation.default_printer is not None:
            printer_properties = presentation.printers[presentation.default_printer]
        else:
            printer_properties = {}
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
        return string.join([i[0] for i in items], ''), string.join([i[1] for i in items], '')

    _per_cent_regexp = re.compile('([ ⠀]+)⠼[⠏⠗]')
    
    def text(self, context, text, lang=None):
        """Return 'text' converted to Unicode Braille characters.

        Arguments:

          context -- current 'Context' instance
          text -- text to convert; unicode
          lang -- target language as an ISO 639-1 Alpha-2 lowercase
            language code or 'None'

        """
        assert isinstance(context, self.Context), context
        assert isinstance(text, basestring), text
        form = context.form()
        assert lang is None or isinstance(lang, basestring), lang
        if lang is None:
            lang = context.lang()
        if not text:
            return '', ''
        if self._private_char(text[0]):
            if text[0] == self._TOC_MARKER_CHAR:
                return text + '\n', '0' * (len(text) + 1)
            else:
                return text, '0' * len(text)
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
                                       mode=(louis.dotsIO + 128))
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
                hyphenation += ('2' if c in whitespace else '0')
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
                            hyphenation += '0' * (end - start)
                            hyphenation_forbidden = False
                        else:
                            hyphenation += louis.hyphenate(hyphenation_tables,
                                                           braille_text[start:end], mode=1)
                    hyphenation += '2'
                    start = end = end + 1
            if end > start:
                if hyphenation_forbidden:
                    hyphenation += '0' * (end - start)
                else:
                    hyphenation += louis.hyphenate(hyphenation_tables,
                                                   braille_text[start:end], mode=1)
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
        assert len(braille) == len(hyphenation), (braille, hyphenation,)
        return braille, hyphenation

    def _newline(self, context, number=1, inline=False):
        context.set_removable_newlines(number if inline else 0)
        return '\n' * number, '0' * number
    
    def _ensure_newlines(self, context, exported, number=1):
        real_number = 0
        text = exported[0]
        while real_number < number and len(text) > real_number and text[-real_number - 1] == '\n':
            real_number += 1
        n = number - real_number
        return text + '\n' * n, exported[1] + '0' * n

    def _indent(self, exported, indentation, init_indentation=None):
        if init_indentation is None:
            init_indentation = indentation
        text, hyphenation = exported
        n = 0
        new_text = ''
        new_hyphenation = ''
        lines = text.split('\n')
        if lines:
            new_text += self._INDENTATION_CHAR * init_indentation
            if indentation > init_indentation:
                diff = indentation - init_indentation
                new_text += self._NEXT_INDENTATION_CHAR * diff
            new_text += lines[0]
            n += len(lines[0])
            new_hyphenation += '0' * max(init_indentation, indentation) + hyphenation[:n]
            space = self._INDENTATION_CHAR * indentation
            space_hyphenation = '0' * indentation
            for l in lines[1:]:
                new_text += '\n'
                n += 1
                new_hyphenation += '0'
                if l:
                    new_text += space + l
                    m = n
                    n += len(l)
                    new_hyphenation += space_hyphenation + hyphenation[m:n]
        assert n == len(hyphenation), (n, len(hyphenation),)
        assert len(new_text) == len(new_hyphenation), \
            (new_text, len(new_text), new_hyphenation, len(new_hyphenation),)
        return new_text, new_hyphenation

    def _list_item_prefix(self, context):
        return '- '

    def _separator(self, context):
        return ' - '

    # Content element export methods (defined by _define_export_methods).
    
    def _export_new_page(self, context, element):
        return '\f', '0'

    def _export_horizontal_separator(self, context, element, width=64, in_table=False):
        if in_table:
            return None
        return '\n', '0'

    def _vertical_cell_separator(self, context):
        return (' ', '1',), 1
    
    def _export_title(self, context, element):
        title = super(BrailleExporter, self)._export_title(context, element)
        return self.text(context, title, lang=element.lang())

    def _export_page_number(self, context, element):
        return self.text(context, str(context.page_number()), lang=element.lang())

    def _export_page_heading(self, context, element):
        return context.page_heading()

    def _page_formatter(self, context, **kwargs):
        return self.text(context, str(context.page_number()))
    
    # Inline constructs (text styles).

    def _inline_braille_export(self, context, element, form=None, lang=None, hyphenate=None):
        if lang is not None:
            orig_lang = context.set_lang(lang)
        if form is not None:
            context.set_form(form)
        if hyphenate is not None:
            orig_hyphenate = context.set_hyphenate(hyphenate)
        exported = self._export_container(context, element)
        if hyphenate is not None:
            context.set_hyphenate(orig_hyphenate)
        if form is not None:
            context.unset_form()
        if lang is not None:
            context.set_lang(orig_lang)
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
        text, hyphenation = self._inline_braille_export(context, element)
        if lang == 'cs':
            text = '⠌' + text + '⠱'
            hyphenation = '0' + hyphenation + '0'
        return text, hyphenation
    
    def _export_subscript(self, context, element):
        lang = context.lang()
        text, hyphenation = self._inline_braille_export(context, element)
        if lang == 'cs':
            text = '⠡' + text + '⠱'
            hyphenation = '0' + hyphenation + '0'
        return text, hyphenation
    
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
        if not label[0]:
            target = element.target(context)
            if isinstance(target, (ContentNode, Section)):
                label = target.heading().export(context)
            elif isinstance(target, Resource):
                label = self.text(context, target.title() or target.filename())
            elif isinstance(target, element.ExternalTarget):
                label = self.text(context, target.title() or target.uri())
        return label

    def _export_mathml(self, context, element):
        # Only Czech MathML processing is available
        class EntityHandler(element.EntityHandler):
            def __init__(self, *args, **kwargs):
                super(EntityHandler, self).__init__(*args, **kwargs)
                self._data = entities.entities
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
                #f = 'style:italic'
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
            children = node.getchildren()
            if exported:
                children = [export(c) for c in children]
            return children
        def attribute(node, name, default=None):
            return node.attrib.get(name, default)
        def op_translation(operator, node=None):
            translation = _mathml_operators.get(operator)
            op_form = None if translation is None else translation[0]
            op_braille, hyphenation = text_export(operator, node=node)
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
                    hyphenation = '3'
                else:
                    hyphenation = '0' * len(op_braille)
            if op_braille.find(u'⠈⠀⠭') >= 0:
                # Still a Unicode character?  We should do something about it.
                op_braille = '⠿⠿⠿%s⠿⠿⠿' % (op_braille,)
                hyphenation = '0' * len(op_braille)
            if translation is not None:
                t_braille = translation[1]
                if t_braille[-1] in (' ', '⠀',) and op_braille[-1] not in (' ', '⠀',):
                    # We don't handle spacing in liblouis yet.
                    op_braille += '⠀'
                    hyphenation += '3'
            return op_form, op_braille, hyphenation
        def text_export(text, node=None):
            if node is not None:
                set_style(node)
            style = current_style()
            form = 0
            if style.find('bold') >= 0:
                form |= louis.bold
            elif style.find('italic') >= 0:
                form |= louis.italic
            context.set_form(form)
            braille = self.text(context, text)[0]
            context.unset_form()
            if node is not None:
                unset_style()
            return braille, '0' * len(braille)
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
            exported = ''
            hyphenation = ''
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
                if exported and separators:
                    separator = separators[-1] if i > len(separators) else separators[i - 1]
                    exported += separator
                    hyph_separator = '3' if len(separator) == 1 else '0' * len(separator)
                    hyphenation += hyph_separator
                e, h = export(n, op_form=op_form)
                exported += e
                hyphenation += h
            return exported, hyphenation
        def export_mi(node, **kwargs):
            text = node_value(node).strip()
            return text_export(text, node=node)
        def export_mn(node, **kwargs):
            text = node_value(node).replace(' ', '')
            braille, hyphenation = text_export(text)
            # We don't know what follows so we put the small letter prefix
            # here.  It should be present here only if small a-h follows; this
            # will be fixed in final MathML result processing.
            braille += u'⠐'
            hyphenation += '0'
            return braille, hyphenation
        def export_mo(node, op_form=None, **kwargs):
            form = attribute(node, 'form', op_form) # prefix, infix, postfix
            separator = attribute(node, 'separator') # true, false
            # We should probably ignore these as Braille script has its own
            # rules of math line breaking:
            # linebreak = attribute(node, 'linebreak') # auto, newline, nobreak, goodbreak, badbreak
            # linebreakstyle = attribute(node, 'linebreakstyle')
            #                  # before, after, duplicate, infixlinebreakstyle
            op = node_value(node).strip()
            op_form, op_braille, hyphenation = op_translation(op)
            if form is None and op_form is not None:
                form = op_form
            if separator == 'true':
                if op_braille[-1] not in (' ', '⠀',):
                    op_braille = op_braille + '⠀'
                    hyphenation = hyphenation + '0'
            elif form == 'infix':
                if op_braille[0] not in (' ', '⠀',):
                    op_braille = '⠀' + op_braille
                    hyphenation = '0' + hyphenation
            return op_braille, hyphenation
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
                line = '⠻⠻'
                l_hyphenation = '00'
            else:
                line = '⠻'
                l_hyphenation = '3'
            braille = '⠆%s%s%s⠰' % (child_1[0], line, child_2[0],)
            hyphenation = '0%s%s%s0' % (child_1[1], l_hyphenation, child_2[1],)
            return braille, hyphenation
        def export_msqrt(node, **kwargs):
            exported, hyphenation = child_export(node)
            return '⠩' + exported + '⠱', '3' + hyphenation + '0'
        def export_mroot(node, **kwargs):
            base, root = child_nodes(node, exported=True)
            braille = '⠠⠌%s⠩%s⠱' % (root[0], base[0],)
            hyphenation = '00%s3%s0' % (root[1], base[1],)
            return braille, hyphenation
        def export_mstyle(node, **kwargs):
            break_style = attribute(node, 'infixlinebreakstyle')
            if break_style: # before, after, duplicate
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
            exported, hyphenation = child_export(node)
            n = len(exported)
            return '⠀' * n, '0' * n
        def export_menclose(node, **kwargs):
            return child_export(node)
        def export_msub(node, **kwargs):
            base, sub = child_nodes(node, exported=True)
            braille = '%s⠡%s⠱' % (base[0], sub[0],)
            hyphenation = '%s0%s0' % (base[1], sub[1],)
            return braille, hyphenation
        def export_msup(node, **kwargs):
            base, sup = child_nodes(node, exported=True)
            braille = '%s⠌%s⠱' % (base[0], sup[0],)
            hyphenation = '%s0%s0' % (base[1], sup[1],)
            return braille, hyphenation
        def export_msubsup(node, **kwargs):
            base, sub, sup = child_nodes(node, exported=True)
            braille = '%s⠌%s⠱⠡%s⠱' % (base[0], sub[0], sup[0],)
            hyphenation = '%s0%s00%s0' % (base[1], sub[1], sup[1],)
            return braille, hyphenation
        def export_munder(node, **kwargs):
            base, under = child_nodes(node, exported=True)
            braille = '%s⠠⠡%s⠱' % (base[0], under[0],)
            hyphenation = '%s00%s0' % (base[1], under[1],)
            return braille, hyphenation
        def export_mover(node, **kwargs):
            base_child, over_child = child_nodes(node)
            base = export(base_child)
            if ((over_child.tag == 'mo' and over_child.text.strip() == '¯' and
                 base_child.tag == 'mn')):
                braille = base[0] + base[0] + '⠤'
                hyphenation = base[1] + base[1] + '0'
            else:
                over = export(over_child)
                braille = '%s⠠⠌%s⠱' % (base[0], over[0],)
                hyphenation = '%s00%s0' % (base[1], over[1],)
            return braille, hyphenation
        def export_munder_mover(node, **kwargs):
            base, under, over = child_nodes(node, exported=True)
            braille = '%s⠠⠡%s⠱⠠⠌%s⠱' % (base[0], under[0], over[0],)
            hyphenation = '%s00%s000%s0' % (base[1], under[1], over[1],)
            return braille, hyphenation
        def export_maction(node, **kwargs):
            selection = attribute(node, 'selection')
            if not selection:
                selection = 1
            return export(child_nodes(node)[selection - 1])
        #def export_mmultiscripts(node, **kwargs):
        #def export_mtable(node, **kwargs):
        #def export_mtr(node, **kwargs):
        #def export_mlabeledtr(node, **kwargs):
        #def export_mtd(node, **kwargs):
        #def export_maligngroup(node, **kwargs):
        #def export_mstack(node, **kwargs):
        #def export_msgroup(node, **kwargs):
        #def export_msrow(node, **kwargs):
        #def export_msline(node, **kwargs):
        #def export_mscarries(node, **kwargs):
        #def export_mscarry(node, **kwargs):
        #def export_mlongdiv(node, **kwargs):
        for k, v in locals().items():
            if k.startswith('export_'):
                exporters[k[len('export_'):]] = v
        braille, hyphenation = child_export(top)
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
        result = braille, hyphenation
        assert len(result[0]) == len(result[1])
        return result
