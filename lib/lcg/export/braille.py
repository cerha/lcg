# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Brailcom, o.p.s.
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

"""Export to Braille notation.
"""

import copy
import string

import louis

from lcg import Presentation, UFont, USpace
from export import Exporter, FileExporter


class BrailleExporter(FileExporter, Exporter):
    """Transforming structured content objects to Braille output.    
    """
    _OUTPUT_FILE_EXT = 'brl'

    class Context(Exporter.Context):

        def __init__(self, exporter, formatter, node, lang, tables={}, hyphenation_tables={},
                     **kwargs):
            super(BrailleExporter.Context, self).__init__(exporter, formatter, node, lang, **kwargs)
            assert isinstance(tables, dict), tables
            assert isinstance(hyphenation_tables, dict), hyphenation_tables
            self._tables = tables
            self._hyphenation_tables = hyphenation_tables
            self._page_number = 1

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

    def export(self, context):
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
            device_table = {' ': ' ', '\n': '\n', '\f': '\f'}
            for i in range(10240, 10496):
                device_table[unichr(i)] = unichr(i)
        braille_tables = presentation.braille_tables
        hyphenation_tables = presentation.braille_hyphenation_tables
        context.set_tables(braille_tables, hyphenation_tables)
        # Export
        text, hyphenation = super(BrailleExporter, self).export(context)
        # Line breaking
        page_strings = text.split('\f')
        pages = [p.split('\n') for p in page_strings]
        if page_width:
            for i in range(len(pages)):
                lines = []
                for line in pages[i]:
                    while len(line) > page_width:
                        pos = page_width
                        if hyphenation[pos] != '2':
                            pos -= 1
                            while pos > 0 and hyphenation[pos] == '0':
                                pos -= 1
                        if pos == 0:
                            lines.append(line[:page_width])
                            line = line[page_width:]
                            hyphenation = hyphenation[page_width:]
                        elif hyphenation[pos] == '1':
                            lines.append(line[:pos] + self.text(context, u'-', lang=lang)[0])
                            line = line[pos:]
                            hyphenation = hyphenation[pos:]
                        elif hyphenation[pos] == '2':
                            lines.append(line[:pos])
                            line = line[pos+1:]
                            hyphenation = hyphenation[pos+1:]
                        else:
                            raise Exception("Program error")
                    lines.append(line)
                    hyphenation = hyphenation[len(line)+1:]
                pages[i] = lines
                hyphenation = hyphenation[1:]
        # Page breaking
        if page_height:
            if left_status_line or right_status_line:
                page_height -= 1
            new_pages = []
            def add_page(page):
                status_line = left_status_line if context.page_number() % 2 else right_status_line
                page = page + [''] * (page_height - len(page))
                if status_line:
                    exported_status_line, __ = status_line.export(context)
                    page.append(exported_status_line)
                new_pages.append(page)
                context.advance_page_number()
            for page in pages:
                while len(page) > page_height:
                    add_page(page[:page_height])
                    page = page[page_height:]
                add_page(page)
            pages = new_pages
        # Device character set transformation
        final_text = string.join([string.join(p, '\n') for p in pages], '\f')
        output = ''
        for c in final_text:
            output += device_table[c]
        return output
            
    # Basic utilitites

    def concat(self, *items):
        return string.join([i[0] for i in items], ''), string.join([i[1] for i in items], '')

    def text(self, context, text, lang=None, form=louis.plain_text):
        """Return 'text' converted to Unicode Braille characters.

        Arguments:

          context -- current 'Context' instance
          text -- text to convert; unicode
          form -- 'louis' typeform flags; integer
          lang -- target language as an ISO 639-1 Alpha-2 lowercase
            language code or 'None'

        """
        assert isinstance(context, self.Context), context
        assert isinstance(text, basestring), text
        assert isinstance(form, int), form
        assert lang is None or isinstance(lang, basestring), lang
        if not text:
            return '', ''
        tables = context.tables(lang)
        typeform = [form] * len(text)
        braille = louis.translateString(tables, text, typeform=copy.copy(typeform), mode=louis.dotsIO+128)
        hyphenation_table = context.hyphenation_table(lang)
        if hyphenation_table is None:
            hyphenation = ''
            for c in braille:
                hyphenation += ('2' if (c in string.whitespace or c == u'\u2800') else '0')
        else:
            hyphenation_tables = tables + [hyphenation_table]
            braille_text = louis.translateString(tables, text, typeform=copy.copy(typeform))
            start = end = 0
            length = len(braille_text)
            hyphenation = ''
            hyphenation_forbidden = False
            unbreakable_characters = string.punctuation + string.digits
            while end < length:
                if braille_text[end] in unbreakable_characters:
                    hyphenation_forbidden = True
                    end += 1
                elif braille_text[end] not in string.whitespace:
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
        assert len(braille) == len(hyphenation), (braille, hyphenation,)
        return braille, hyphenation

    def _newline(self, context, number=1):
        return '\n'*number, '0'*number

    def _list_item_prefix(self, context):
        return u'- '

    def _separator(self, context):
        return u' - '

    # Inline constructs (text styles).

    def emphasize(self, context, text):
        return self.text(context, text, form=louis.italic)

    def strong(self, context, text):
        return self.text(context, text, form=louis.bold)

    def fixed(self, context, text):
        return self.text(context, text)
     
    def underline(self, context, text):
        return self.text(context, text, form=louis.underline)
    
    def superscript(self, context, text):
        return self.text(context, text)
    
    def subscript(self, context, text):
        return self.text(context, text)
    
    def citation(self, context, text):
        return self.text(context, text)
    
    def quotation(self, context, text):
        return self.text(context, text)

    # Content element export methods (defined by _define_export_methods).
    
    def _export_new_page(self, context):
        return '\f', '0'

    def _export_horizontal_separator(self, context, element):
        return '\n', '0'

    def _export_title(self, context, element):
        title = super(BrailleExporter, self)._export_title(context, element)
        return self.text(context, title, lang=element.lang())

    def _export_page_number(self, context, element):
        return self.text(context, str(context.page_number()), lang=element.lang())

    def _page_formatter(self, context, **kwargs):
        return self.text(context, str(context.page_number()))
    
