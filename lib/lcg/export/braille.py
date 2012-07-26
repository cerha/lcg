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

from lcg import Presentation, UFont, USpace, ContentNode, Section, Resource
from export import Exporter, FileExporter, MarkupFormatter


class BrailleFormatter(MarkupFormatter):
    
    _FORMAT = {'linebreak': (u'\n', '0',),
               'comment': (u'', '',),
               'dash': (u'⠤', '0',),
               }

    def _set_form(self, context, close, form):
        if close:
            context.unset_form(form)
        else:
            context.set_form(form)
        return '', ''
    
    def _emphasize_formatter(self, context, close=False, **kwargs):
        return self._set_form(context, close, louis.italic)

    def _strong_formatter(self, context, close=False, **kwargs):
        return self._set_form(context, close, louis.bold)

    def _underline_formatter(self, context, close=False, **kwargs):
        return self._set_form(context, close, louis.underline)

    def _citation_formatter(self, context, close=False, **kwargs):
        if close:
            context.unset_secondary_language()
        else:
            context.set_secondary_language()
        return '', ''

    def _formatter(self, context, type, groups, close=False, lang=None):
        try:
            formatter = getattr(self, '_'+type+'_formatter')
        except AttributeError:
            formatter = None
        if formatter is not None:
            result = formatter(context, close=close, lang=lang, **groups)
        else:
            result = self._FORMAT.get(type) or ('', '',)
        return result
    

class BrailleExporter(FileExporter, Exporter):
    """Transforming structured content objects to Braille output.    
    """
    Formatter = BrailleFormatter
    
    _OUTPUT_FILE_EXT = 'brl'
    _INDENTATION_CHAR = u'\ue010'
    _NEXT_INDENTATION_CHAR = u'\ue011'

    class Context(Exporter.Context):

        def __init__(self, exporter, formatter, node, lang, tables={}, hyphenation_tables={},
                     **kwargs):
            super(BrailleExporter.Context, self).__init__(exporter, formatter, node, lang, **kwargs)
            assert isinstance(tables, dict), tables
            assert isinstance(hyphenation_tables, dict), hyphenation_tables
            self._tables = tables
            self._hyphenation_tables = hyphenation_tables
            self._page_number = 1
            self._form = louis.plain_text

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
            return self._form

        def set_form(self, form):
            self._form = self._form | form

        def unset_form(self, form):
            self._form = self._form & ~form

    def __init__(self, *args, **kwargs):
        super(BrailleExporter, self).__init__(*args, **kwargs)
        self._unbreakable_characters = string.punctuation + string.digits + self._braille_characters()
        self._whitespace = string.whitespace + u' \u2800'

    def _braille_characters(self):
        return string.join([unichr(i) for i in range(10240, 10496)], '')

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
            device_table = {' ': u'⠀', '\n': '\n', '\f': '\f'}
            for c in self._braille_characters():
                device_table[c] = c
        braille_tables = presentation.braille_tables
        hyphenation_tables = presentation.braille_hyphenation_tables
        context.set_tables(braille_tables, hyphenation_tables)
        # Export
        def run_export(page_height=page_height):
            text, hyphenation = super(BrailleExporter, self).export(context)
            assert len(text) == len(hyphenation)
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
                        prefix = u' ' * next_prefix_len
                        prefix_limit = page_width / 2
                        if next_prefix_len > prefix_limit:
                            prefix = prefix[:prefix_limit]
                        hyphenation_prefix = '0' * len(prefix)
                        if prefix_len > 0:
                            line = u' ' * prefix_len + line[prefix_len:]
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
                                lines.append(line[:pos] + self.text(context, u'-', lang=lang)[0])
                                line = prefix + line[pos:]
                                hyphenation = hyphenation_prefix + hyphenation[pos:]
                            elif hyphenation[pos] == '2':
                                lines.append(line[:pos])
                                line = prefix + line[pos+1:]
                                hyphenation = hyphenation_prefix + hyphenation[pos+1:]
                            else:
                                raise Exception("Program error", hyphenation[pos])
                        pos = line.find(hfill)
                        if pos >= 0:
                            fill_len = (page_width - len(line) + len(hfill))
                            line = (line[:pos] + u' '*fill_len + line[pos+len(hfill):])
                            hyphenation = (hyphenation[:pos] + '0'*fill_len + hyphenation[pos+len(hfill):])
                        lines.append(line)
                        hyphenation = hyphenation[len(line)+1:]
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
                    status_line = left_status_line if context.page_number() % 2 else right_status_line
                    lines = lines + [''] * (page_height - len(lines))
                    if status_line:
                        exported_status_line, __ = status_line.export(context)
                        lines.append(exported_status_line)
                    new_pages.append(lines)
                    context.advance_page_number()
                    page.reverse()
                for page in pages:
                    while len(page) > page_height:
                        add_page(page)
                    add_page(page)
                pages = new_pages
            else:
                for i in range(len(pages)):
                    pages[i] = [line for line in pages[i] if not line or line[0] != self._TOC_MARKER_CHAR]
            return pages
        # Two-pass export in order to get page numbers in table of contents
        run_export()
        pages = run_export()
        # Device character set transformation
        final_text = string.join([string.join(p, '\n') for p in pages], '\f')
        output = ''
        for c in final_text:
            output += device_table[c]
        return output
            
    # Basic utilitites

    def concat(self, *items):
        return string.join([i[0] for i in items], ''), string.join([i[1] for i in items], '')

    def text(self, context, text, lang=None):
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
                                       mode=louis.dotsIO+128)
        whitespace = self._whitespace
        if typeform is None:
            if italic:
                braille = u'⠔⠨' + braille + u'⠨⠔'
            if underline:
                compact = (form == louis.underline)
                if compact:
                    for c in braille:
                        if c in whitespace:
                            compact = False
                            break
                if compact:
                    braille = u'⠸' + braille
                else:
                    braille = u'⠔⠸' + braille + u'⠸⠔'
            if bold:
                braille = u'⠔⠰' + braille + u'⠰⠔'
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
        assert len(braille) == len(hyphenation), (braille, hyphenation,)
        return braille, hyphenation

    def _newline(self, context, number=1):
        return '\n'*number, '0'*number
    
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
            new_hyphenation += u'0' * max(init_indentation, indentation) + hyphenation[:n]
            space = self._INDENTATION_CHAR * indentation
            space_hyphenation = u'0' * indentation
            for l in lines[1:]:
                new_text += '\n'
                n += 1
                new_hyphenation += u'0'
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
        return u'- '

    def _separator(self, context):
        return u' - '

    # Content element export methods (defined by _define_export_methods).
    
    def _export_new_page(self, context):
        return '\f', '0'

    def _export_horizontal_separator(self, context, element, width=64, in_table=False):
        if in_table:
            return None
        return '\n', '0'

    def _vertical_cell_separator(self, context):
        return (u' ', '1',), 1
    
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

    def _export_emphasize(self, context, element):
        text = self._export_container(context, element)
        return self.text(context, text, form=louis.italic)

    def _export_strong(self, context, element):
        text = self._export_container(context, element)
        return self.text(context, text, form=louis.bold)

    def _export_code(self, context, element):
        text = self._export_container(context, element)
        return self.text(context, text)
     
    def _export_underline(self, context, element):
        text = self._export_container(context, element)
        return self.text(context, text, form=louis.underline)
    
    def _export_superscript(self, context, element):
        lang = context.lang()
        text, hyphenation = self.text(context, self._export_container(context, element))
        if lang == 'cs':
            text = u'⠌' + text + u'⠱'
            hyphenation = '0' + hyphenation + '0'
        return text, hyphenation
    
    def _export_subscript(self, context, element):
        lang = context.lang()
        text, hyphenation = self.text(context, self._export_container(context, element))
        if lang == 'cs':
            text = u'⠡' + text + u'⠱'
            hyphenation = '0' + hyphenation + '0'
        return text, hyphenation
    
    def _export_citation(self, context, element):
        lang = (element.lang(inherited=False) or context.sec_lang())
        return self.text(context, text, lang=lang)

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
