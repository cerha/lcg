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

from __future__ import unicode_literals

"""Export to Braille notation.
"""

import copy
import string

import louis

from lcg import Presentation, UFont, USpace, ContentNode, Section, Resource
from export import Exporter, FileExporter, MarkupFormatter
import entities

class BrailleFormatter(MarkupFormatter):
    
    _FORMAT = {'linebreak': ('\n', '0',),
               'comment': ('', '',),
               'dash': ('⠤', '0',),
               }

    def _set_form(self, context, close, form):
        if close:
            context.unset_form()
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
    _INDENTATION_CHAR = '\ue010'
    _NEXT_INDENTATION_CHAR = '\ue011'

    class Context(Exporter.Context):

        def __init__(self, exporter, formatter, node, lang, tables={}, hyphenation_tables={},
                     **kwargs):
            super(BrailleExporter.Context, self).__init__(exporter, formatter, node, lang, **kwargs)
            assert isinstance(tables, dict), tables
            assert isinstance(hyphenation_tables, dict), hyphenation_tables
            self._tables = tables
            self._hyphenation_tables = hyphenation_tables
            self._page_number = 1
            self._form = [louis.plain_text]

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

    def __init__(self, *args, **kwargs):
        super(BrailleExporter, self).__init__(*args, **kwargs)
        self._unbreakable_characters = string.punctuation + string.digits + self._braille_characters()
        self._whitespace = string.whitespace + ' \u2800'

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
            device_table = {' ': '⠀', '\n': '\n', '\f': '\f'}
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
                                line = prefix + line[pos+1:]
                                hyphenation = hyphenation_prefix + hyphenation[pos+1:]
                            elif hyphenation[pos] == '3':
                                lines.append(line[:pos+1])
                                line = prefix + line[pos:]
                                hyphenation = hyphenation_prefix + hyphenation[pos:]
                            else:
                                raise Exception("Program error", hyphenation[pos])
                        pos = line.find(hfill)
                        if pos >= 0:
                            fill_len = (page_width - len(line) + len(hfill))
                            line = (line[:pos] + ' '*fill_len + line[pos+len(hfill):])
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
    
    def _export_new_page(self, context):
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
            text = '⠌' + text + '⠱'
            hyphenation = '0' + hyphenation + '0'
        return text, hyphenation
    
    def _export_subscript(self, context, element):
        lang = context.lang()
        text, hyphenation = self.text(context, self._export_container(context, element))
        if lang == 'cs':
            text = '⠡' + text + '⠱'
            hyphenation = '0' + hyphenation + '0'
        return text, hyphenation
    
    def _export_citation(self, context, element):
        lang = (element.lang(inherited=False) or context.sec_lang())
        text = self._export_container(context, element)
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

    def _export_mathml(self, context, element):
        # Only Czech MathML processing is available
        class EntityHandler(element.EntityHandler):
            def __init__(self, *args, **kwargs):
                super(EntityHandler, self).__init__(*args, **kwargs)
                self._data = entities.entities
            def __getitem__(self, key):
                return self._data.get(key, '?')
        entity_handler = EntityHandler()
        top = element.tree_content(entity_handler)
        exporters = {}
        flags = []
        op_translation = {'(': ('⠦', '0'), ')': ('⠴', '0'), '[': ('⠠⠦', '00'), ']': ('⠠⠴', '00'),
                          '{': ('⠨⠦', '00'), '}': ('⠨⠴', '00'), '|': ('⠸', '3'),
                          '=': ('⠶', '3'), '<': ('⠁⠀⠣⠃', '0000'), '>': ('⠁⠀⠜⠃', '0000'),
                          '+': ('⠲', '3'), '-': ('⠤', '3'), '±': ('⠲⠤', '00')}
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
                variant = node.get('mathvariant')
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
        def child_export(node, separator=None):
            exported = ''
            hyphenation = ''
            if separator:
                hyph_separator = '3' if len(separator == 1) else '0' * len(separator)
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
                        op_form = 'infix'
                else:
                    op_form = None
                if exported and separator:
                    exported += separator
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
            form = node.get('form', op_form) # prefix, infix, postfix
            separator = node.get('separator') # true, false
            # We should probably ignore these as Braille script has its own
            # rules of math line breaking:
            # linebreak = node.getAttribute('linebreak') # auto, newline, nobreak, goodbreak, badbreak
            # linebreakstyle = node.getAttribute('linebreakstyle') # before, after, duplicate, infixlinebreakstyle
            op = node_value(node).strip()
            translation = op_translation.get(op)
            if translation is None:
                op_braille, hyphenation = text_export(op, node=node)
            else:
                op_braille, hyphenation = translation
            if separator == 'true':
                op_braille = op_braille + ' '
                hyphenation = hyphenation + '0'
            elif form == 'infix':
                op_braille = ' ' + op_braille
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
                if pos + 1 < len(text) and text[pos+1] != ' ':
                    pos += 1
                    text = text[:pos] + ' ' + text[pos:]
                pos += 1
            return text_export(text, node=node)
        def export_mspace(node, **kwargs):
            return text_export(' ')
        def export_ms (node, **kwargs):
            text = '"%s"' % (node_value(node).strip(),)
            return text_export(text, node=node)
        def export_mrow(node, **kwargs):
            return child_export(node)
        def export_mfrac(node, **kwargs):
            child_1, child_2 = child_nodes(node, exported=True)
            mfrac_flag = 'mfrac'
            if len(node.getiterator('mfrac')) > 1:
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
            break_style = node.get('infixlinebreakstyle')
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
        def export_mfenced(node, **kwargs):
            open_string = node.get('open', '(')
            close_string = node.get('close', ')')
            separator = node.get('separator')
            if separator:
                if separator == ',':
                    # It's not clear what we should do with spaces in separators.
                    # But it's clear that at least comma should be transformed
                    # to a spaced version to distinguish it from decimal point.
                    separator = ', '
                separator = text_export(separator, node=node)[0]
            exported, e_hyphenation = child_export(node, separator=separator)
            open_braille, o_hyphenation = text_export(open_string, node=node)
            close_braille, c_hyphenation = text_export(close_string, node=node)
            braille = open_braille + exported + close_braille
            hyphenation = o_hyphenation + e_hyphenation + c_hyphenation
            return braille, hyphenation
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
            base, over = child_nodes(node, exported=True)
            braille = '%s⠠⠌%s⠱' % (base[0], over[0],)
            hyphenation = '%s00%s0' % (base[1], over[1],)
            return braille, hyphenation
        def export_munder_mover(node, **kwargs):
            base, under, over = child_nodes(node, exported=True)
            braille = '%s⠠⠡%s⠱⠠⠌%s⠱' % (base[0], under[0], over[0],)
            hyphenation = '%s00%s000%s0' % (base[1], under[1], over[1],)
            return braille, hyphenation
        def export_maction(node, **kwargs):
            selection = node.get('selection')
            if not selection:
                selection = 1
            return export(child_nodes(node)[selection-1])
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
            if braille[i] == '⠐' and (i + 1 == l or braille[i+1] not in '⠁⠃⠉⠙⠑⠋⠛⠓'):
                braille = braille[:i] + braille[i+1:]
                hyphenation = hyphenation[:i] + hyphenation[i+1:]
                l -= 1
            i += 1
        result = braille, hyphenation
        assert len(result[0]) == len(result[1])
        return result
