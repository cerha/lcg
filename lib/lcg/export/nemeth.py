# -*- coding: utf-8 -*-

# Copyright (C) 2013-2015 OUI Technology Ltd.
# Copyright (C) 2019 Tomáš Cerha <t.cerha@gmail.com>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from __future__ import absolute_import

from builtins import zip
from builtins import range
from contextlib import contextmanager
import copy
import re
import string

import lcg

from .braille import _Braille, _braille_whitespace
from . import mathml


_CONDITIONAL_NUM_PREFIX = '\ue020'
_NUM_PREFIX_REQUIRED = '\ue021'
_SINGLE_LETTER_START = '\ue022'
_SINGLE_LETTER_END = '\ue023'
_SINGLE_LETTER_KILLER_PREFIX = '\ue024'
_SINGLE_LETTER_KILLER_SUFFIX = '\ue025'
_LEFT_WHITESPACE_42 = '\ue026'  # Nemeth §42 and similar
_RIGHT_WHITESPACE_42 = '\ue027'  # Nemeth §42 and similar
_END_SUBSUP = '\ue028'
_INNER_SUBSUP = '\ue029'
_IMPLICIT_SUBSCRIPT = '\ue030'  # to prevent numeric multipurpose indicator in subscripts
_AFTER_BAR = '\ue031'
_BEFORE_BAR = '\ue032'
_MATRIX_START = '\ue033'
_MATRIX_END = '\ue034'
_MATRIX_SEPARATOR = '\ue035'

_nemeth_numbers = {'0': '⠴', '1': '⠂', '2': '⠆', '3': '⠒', '4': '⠲',
                   '5': '⠢', '6': '⠖', '7': '⠶', '8': '⠦', '9': '⠔',
                   ' ': '⠀', '.': '⠨', ',': '⠠'}
_nemeth_digits = '⠴⠂⠆⠒⠲⠢⠖⠶⠦⠔'

_nemeth_texts = {'cos': '⠉⠕⠎',  # wrong translation by liblouis
                 'log': '⠇⠕⠛',  # wrong translation by liblouis
                 'ℵ': '⠠⠠⠁',    # aleph, not supported in liblouis
                 }

_signs_of_shape = ''
_signs_of_shape_lspace = ''
_signs_of_shape_rspace = ''
_primes = "'′″"
_braille_punctuation = ('⠂',)
_braille_left_grouping = ()
_braille_right_grouping = ()
_braille_comparison = ()


def _comparison(symbol, braille):
    global _braille_comparison, _nemeth_operators
    braille = braille.strip('%s%s' % (_SINGLE_LETTER_KILLER_PREFIX, _SINGLE_LETTER_KILLER_SUFFIX,))
    braille = '⠀' + braille + '⠀'
    if braille not in _braille_comparison:
        _braille_comparison += (braille,)
    braille = _SINGLE_LETTER_KILLER_PREFIX + braille + _SINGLE_LETTER_KILLER_SUFFIX
    _nemeth_operators[symbol] = braille


def _punctuation(symbol, braille):
    global _braille_punctuation, _nemeth_operators
    if braille not in _braille_punctuation:
        _braille_punctuation += (braille,)
    _nemeth_operators[symbol] = braille


def _shape(symbol, braille, lspace=True, rspace=True):
    global _signs_of_shape, _signs_of_shape_lspace, _signs_of_shape_rspace, _nemeth_operators
    if symbol not in _signs_of_shape:
        _signs_of_shape += symbol
    if lspace and symbol not in _signs_of_shape_lspace:
        _signs_of_shape_lspace += symbol
    if rspace and symbol not in _signs_of_shape_rspace:
        _signs_of_shape_rspace += symbol
    translated = _SINGLE_LETTER_KILLER_PREFIX + braille + _SINGLE_LETTER_KILLER_SUFFIX
    _nemeth_operators[symbol] = translated


def _lgrouping(symbol, braille):
    global _braille_left_grouping, _nemeth_operators
    if braille not in _braille_left_grouping:
        _braille_left_grouping += (braille,)
    if symbol is not None:
        _nemeth_operators[symbol] = braille


def _rgrouping(symbol, braille):
    global _braille_right_grouping, _nemeth_operators
    if braille not in _braille_right_grouping:
        _braille_right_grouping += (braille,)
    if symbol is not None:
        _nemeth_operators[symbol] = braille


def _prime(symbol, braille):
    global _primes, _nemeth_operators
    if symbol not in _primes:
        _primes += symbol
    _nemeth_operators[symbol] = braille
_nemeth_operators = {
    '*': '⠈⠼' + _NUM_PREFIX_REQUIRED,
    '#': '⠨⠼' + _NUM_PREFIX_REQUIRED,
    '×': '⠈⠡',
    '∥': '⠳⠳',
    '¯': '⠱',
    '!': '⠯',
    '\u2061': '⠀' + _SINGLE_LETTER_KILLER_PREFIX,  # function application
}
_comparison('≐', '⠐⠨⠅⠣⠡⠻')
_prime("'", '⠄')
_prime('′', '⠄')
_prime('″', '⠄⠄')
_punctuation("'", '⠄')
_punctuation(':', '⠒')
_punctuation(',', '⠠⠀')
_punctuation('–', '⠤⠤')
_punctuation('—', '⠤⠤⠤⠤')
_punctuation('…', '⠄⠄⠄')
_punctuation('-', '⠤')
_punctuation('.', '⠲')
_punctuation('?', '⠦')
_punctuation('?', '⠿')          # we interpret question mark as an omission character
_punctuation('‘', '⠠⠦')
_punctuation('“', '⠦')
_punctuation('’', '⠴⠄')
_punctuation('”', '⠴')
_punctuation(';', '⠆')
_shape('∠', '⠫⠪', lspace=False)
_shape('△', '⠫⠞')
_shape('▵', '⠫⠞')
_shape('□', '⠫⠲')
_shape('◽', '⠫⠲')
_shape('◯', '⠫⠉')
_shape('→', '⠫⠕')
_lgrouping('(', '⠷')
_lgrouping(None, '⠠⠷')          # enlarged left parenthesis
_lgrouping('[', '⠈⠷')
_lgrouping(None, '⠈⠠⠷')         # enlarged left bracket
_lgrouping(None, '⠸⠈⠷')         # bold left bracket
_lgrouping('{', '⠨⠷')
_lgrouping(None, '⠨⠠⠷')         # enlarged left brace
_lgrouping('|', '⠳')
_lgrouping(None, '⠠⠳')          # enlarged vertical bar
_lgrouping('‖', '⠳⠳')
_lgrouping(None, '⠠⠳⠠⠳')        # enlarged double vertical bar
_lgrouping(None, '⠸⠳')          # bold vertical bar
_lgrouping(None, '⠸⠳⠸⠳')        # bold double vertical bar
_lgrouping('〈', '⠨⠨⠷')
_lgrouping(None, '⠨⠨⠠⠷')        # enlarged left angle bracket
_lgrouping('〚', '⠈⠸⠷')
_lgrouping(None, '⠈⠸⠠⠷')        # enlarged left barred bracket
_lgrouping('⦃', '⠨⠸⠷')
_lgrouping(None, '⠨⠸⠠⠷')        # enlarged left barred brace
_lgrouping(None, '⠈⠘⠷')         # upper left half bracket
_lgrouping(None, '⠈⠘⠠⠷')        # enlarged upper left half bracket
_lgrouping(None, '⠈⠰⠷')         # lower left half bracket
_lgrouping(None, '⠈⠰⠠⠷')        # enlarged lower left half bracket
_lgrouping(None, '⠠⠄')          # left transcriber's grouping symbol
_lgrouping(None, '⠠⠄⠷')         # enlarged left transcriber's grouping symbol
_rgrouping(')', '⠾')
_rgrouping(None, '⠠⠾')          # enlarged right parenthesis
_rgrouping(']', '⠈⠾')
_rgrouping(None, '⠈⠠⠾')         # enlarged right bracket
_rgrouping(None, '⠸⠈⠾')         # bold right bracket
_rgrouping('}', '⠨⠾')
_rgrouping(None, '⠨⠠⠾')         # enlarged right brace
_rgrouping('|', '⠳')
_rgrouping(None, '⠠⠳')          # enlarged vertical bar
_rgrouping('‖', '⠳⠳')
_rgrouping(None, '⠠⠳⠠⠳')        # enlarged double vertical bar
_rgrouping(None, '⠸⠳')          # bold vertical bar
_rgrouping(None, '⠸⠳⠸⠳')        # bold double vertical bar
_rgrouping('〉', '⠨⠨⠾')
_rgrouping(None, '⠨⠨⠠⠾')        # enlarged right angle bracket
_rgrouping('〛', '⠈⠸⠾')
_rgrouping(None, '⠈⠸⠠⠾')        # enlarged right barred bracket
_rgrouping('⦄', '⠨⠸⠾')
_rgrouping(None, '⠨⠸⠠⠾')        # enlarged right barred brace
_rgrouping(None, '⠈⠘⠾')         # upper right half bracket
_rgrouping(None, '⠈⠘⠠⠾')        # enlarged upper right half bracket
_rgrouping(None, '⠈⠰⠾')         # lower right half bracket
_rgrouping(None, '⠈⠰⠠⠾')        # enlarged lower right half bracket
_rgrouping(None, '⠠⠄')          # right transcriber's grouping symbol
_rgrouping(None, '⠠⠄⠾')         # enlarged right transcriber's grouping symbol

_math_comparison_operators = ('<=>≂≂̸≃≄≅≆≇≈≉≊≋≋̸≌≍≏≏̸≐≐̸≑≓≗≜≟≠≡≢≤≥≦≦̸≧≧̸≨≩≪≪̸≫≫̸≮≯≰≱≲≳≴≵≶≷≸'
                              '≹≺≻≼≽≾≿≿̸⊀⊁⊴⊵⋍⋖⋗⋘⋘̸⋙⋙̸⋚⋛⋞⋟⋠⋡⋦⋧⋨⋩⋪⋫⋬⋭'
                              '⦔⩭⩭̸⩯⩰⩰̸⩵⩸⩹⩺⩻⩼⩽⩽̸⩾⩾̸⩿⪀⪁⪂⪃⪄⪅⪆⪇⪈⪉⪊⪋⪌⪍⪎⪏⪐⪑⪒⪓⪔⪕⪖⪗⪘⪙⪚⪝⪞⪟⪠⪡⪡̸⪢⪢̸⪦⪨⪩⪬⪮⪯⪯̸⪰⪰'
                              '̸⪳⪴⪵⪶⪷⪸⪹⪺⪻⪼∈⋹⋵⋴⋳∈')
_signs_of_shape_and_omission = _signs_of_shape
_function_names = ('amp', 'antilog', 'arc', 'arg', 'colog', 'cos', 'cosh', 'cot', 'coth', 'covers',
                   'csc', 'csch', 'ctn', 'ctnh', 'det', 'erf', 'exp', 'exsec', 'grad', 'hav', 'im',
                   'inf', 'lim', 'ln', 'log', 'max', 'min', 'mod', 're', 'sec', 'sech', 'sin',
                   'sinh', 'sup', 'tan', 'tanh', 'vers',)
_vertical_bars = '|∥∦∤∣'

_braille_left_indicators = ('⠰', '⠸', '⠨', '⠨⠈', '⠠⠠', '⠈⠈', '⠘', '⠣', '⠩', '⠪', '⠻',
                            '⠶⠶⠶', '⠹', '⠠⠹', '⠠⠠⠹', '⠸⠹', '⠈⠻', '⠘', '⠘⠘', '⠘⠰', '⠘⠘⠘',
                            '⠘⠘⠰', '⠘⠰⠘', '⠘⠰⠰', '⠰', '⠰⠘', '⠰⠰', '⠰⠘⠘', '⠰⠘⠰', '⠰⠰⠘', '⠰⠰⠰',
                            '⠣⠣', '⠩', '⠩⠩', '⠈', '⠼', '⠨', '⠨⠨', '⠨⠨⠨', '⠫', '⠸⠫',
                            '⠠⠨', '⠠⠄⠸', '⠠⠄⠨',)
_braille_right_indicators = ('⠼', '⠠⠼', '⠠⠠⠼', '⠸⠼', '⠻', '⠸⠠⠄', '⠨⠠⠄', '⠹', '⠠⠹', '⠠⠠⠹', '⠐',
                             '⠘', '⠰', '⠣',)
_braille_symbols_42 = ()        # TODO: not yet defined


# General utilities

class _Variables(list):

    @contextmanager
    def let(self, name, value):
        if value is not None:
            self.append([name, value])
        try:
            yield None
        finally:
            if value is not None:
                self.pop()

    @contextmanager
    def xlet(self, *definitions):
        n = 0
        for k, v in definitions:
            if v is not None:
                self.append([k, v])
                n += 1
        try:
            yield None
        finally:
            for i in range(n):
                self.pop()

    def get(self, name, default=None):
        for i in range(len(self) - 1, -1, -1):
            if self[i][0] == name:
                return self[i][1]
        return default

    def set(self, name, value):
        for i in range(len(self) - 1, -1, -1):
            if self[i][0] == name:
                self[i][1] = value
                return True
        return False


@contextmanager
def _style(node, variables):
    variant = None if node is None else node.get('mathvariant')
    if variant:
        bold = variant.find('bold') >= 0
        italic = variant.find('italic') >= 0
        if bold and italic:
            style = 'bold+italic'
        elif bold:
            style = 'bold'
        elif italic:
            style = 'italic'
        else:
            style = 'normal'
    else:
        style = None
    with variables.let('style', style):
        yield None


def _child_nodes(node):
    return list(node)


def _attribute(node, name, default=None):
    return node.get(name, default)


def _node_value(node):
    value = node.text
    if value is None:
        # this may happen with unresolved entities
        value = '?'
    return value


# Common export functions

_num_prefix_regexp = re.compile('(^|[\n⠀%s%s%s])([%s%s%s]*⠤?)(%s)' %
                                (_NUM_PREFIX_REQUIRED, _RIGHT_WHITESPACE_42, _MATRIX_SEPARATOR,
                                 _SINGLE_LETTER_KILLER_PREFIX, _SINGLE_LETTER_KILLER_SUFFIX,
                                 _LEFT_WHITESPACE_42, _CONDITIONAL_NUM_PREFIX,),
                                re.M)
_prefixed_punctuation = "':.!-?‘“’”;\""
_punctuation_regexp = re.compile('([,–—]+)[%s]' % (_prefixed_punctuation,))

_braille_number_regexp = re.compile('[%s⠨]+%s?$' % (_nemeth_digits, _END_SUBSUP,))
_braille_empty_regexp = re.compile('[⠀\ue000-\ue0ff]*$')
_braille_repeated_subsup_regexp = re.compile('[⠰⠘]+(%s[⠰⠘]+)' % (_INNER_SUBSUP,))
_braille_separate_subscript_regexp = \
    re.compile('([⠰%s][%s]+|[⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵])$' % (_IMPLICIT_SUBSCRIPT,
                                                               _nemeth_digits,))


def mathml_nemeth(exporter, context, element):
    class EntityHandler(element.EntityHandler):

        def __init__(self, *args, **kwargs):
            super(EntityHandler, self).__init__(*args, **kwargs)
            self._data = mathml.entities

        def __getitem__(self, key):
            return self._data.get(key, '?')
    entity_handler = EntityHandler()
    top_node = element.tree_content(entity_handler, transform=True)
    post = element.next_element()
    variables = _Variables()
    braille = _child_export(top_node, exporter, context, variables)
    text = braille.text()
    hyphenation = braille.hyphenation().replace(exporter.HYPH_WS, exporter.HYPH_NEMETH_WS)
    # Separate vertical bars
    while True:
        pos = text.find('%s%s' % (_AFTER_BAR, _BEFORE_BAR,))
        if pos == -1:
            break
        text = text[:pos] + '⠐' + text[pos + 2:]
        hyphenation = hyphenation[:pos] + '0' + hyphenation[pos + 2:]
    # Remove repeated subsup's
    while True:
        match = _braille_repeated_subsup_regexp.search(text)
        if match is None:
            break
        start, end = match.span(1)
        text = text[:start] + text[end:]
        hyphenation = hyphenation[:start] + hyphenation[end:]
    # Handle numeric prefixes
    while True:
        match = _num_prefix_regexp.search(text)
        if match is None:
            break
        start, end = match.start(3), match.end(3)
        text = text[:start] + '⠼' + text[end:]
        hyphenation = hyphenation[:start] + '0' + hyphenation[end:]
    # Punctuation indicator -- part 1
    single_letter = text and text[-1] == _SINGLE_LETTER_END
    # Handle letter prefixes
    space_or_punctuation = '⠀⠨⠠⠰'
    while True:
        pos = text.find(_SINGLE_LETTER_START)
        if pos == -1:
            break
        pos_end = text.find(_SINGLE_LETTER_END)
        assert pos_end > pos, text
        # I don't understand Nemeth definition of "single letters" very well.
        # The definitions seem to contradict the examples, especially as for
        # parentheses.  As we use the examples in tests, we try to be
        # consistent with them.  The most important "clarification" rules we
        # add here are:
        # - Single letters may occur at the beginning or at the end of the
        #   whole math construct.
        # - Single letters may be preceeded or succeeded by parentheses, but
        #   not from both the sides -- this is explicitly prohibited by Nemeth,
        #   see §25.a.v-vi, while being explicitly applied in the examples,
        #   see §26.b.(4)-(5).
        pre_punctuation = '' if pos == 0 else text[pos - 1]
        post_punctuation = '' if pos_end >= len(text) - 1 else text[pos_end + 1]
        if ((pre_punctuation == '' or
             pre_punctuation in space_or_punctuation or pre_punctuation == '⠷') and
            (post_punctuation == '' or
             post_punctuation in space_or_punctuation or post_punctuation == '⠾')):
            prefix = '⠰'
            prefix_hyph = '0'
        else:
            prefix = prefix_hyph = ''
        text = text[:pos] + prefix + text[pos + 1:pos_end] + text[pos_end + 1:]
        hyphenation = (hyphenation[:pos] + prefix_hyph + hyphenation[pos + 1:pos_end] +
                       hyphenation[pos_end + 1:])
    # Multipurpose indicator to distinguish base line numbers from subscripts
    while True:
        pos = text.find(_CONDITIONAL_NUM_PREFIX)
        if pos == -1:
            break
        if _braille_separate_subscript_regexp.search(text[:pos]):
            text = text[:pos] + '⠐' + text[pos + 1:]
            hyphenation = hyphenation[:pos] + '0' + hyphenation[pos + 1:]
        else:
            text = text[:pos] + text[pos + 1:]
            hyphenation = hyphenation[:pos] + hyphenation[pos + 1:]
    # Cleanup
    text_len = len(text)
    i = 0
    while i < text_len:
        if text[i] in (_CONDITIONAL_NUM_PREFIX, _NUM_PREFIX_REQUIRED, _IMPLICIT_SUBSCRIPT,
                       _SINGLE_LETTER_KILLER_PREFIX, _SINGLE_LETTER_KILLER_SUFFIX, _INNER_SUBSUP,
                       _AFTER_BAR, _BEFORE_BAR,):
            text = text[:i] + text[i + 1:]
            hyphenation = hyphenation[:i] + hyphenation[i + 1:]
            text_len -= 1
        else:
            i += 1
    # Punctuation indicator -- part 2
    if isinstance(post, lcg.TextContent):
        post_text = post.text()
        punctuated = False
        if post_text:
            if post_text[0] in _prefixed_punctuation:
                punctuated = True
            else:
                m = _punctuation_regexp.match(post_text)
                if m is not None:
                    pos = m.end(1)
                    context.set_alternate_text(post, post_text[:pos] + u'_' + post_text[pos:])
        if punctuated:
            indicate = single_letter
            for indicator in _braille_right_indicators:
                if text.endswith(indicator):
                    indicate = True
                    break
            if not indicate and _braille_number_regexp.search(text):
                indicate = True
            if not indicate:
                last_element = top_node
                children = last_children = list(last_element)
                while last_element.tag not in ('mi', 'mo', 'mn',) and children:
                    last_children = children
                    last_element = children[-1]
                    children = list(last_element)
                if last_element.tag == 'mo' and (last_element.text or '') in ',-–—':
                    if len(last_children) > 1:
                        last_element = last_children[-2]
                if ((last_element.tag == 'mo' or
                     (last_element.tag == 'mi' and last_element.text == '…'))):
                    op = last_element.text.strip()
                    if op in ('–—…' + _signs_of_shape + _math_comparison_operators):
                        indicate = True
                if ((not indicate and last_element.tag == 'mi' and
                     last_element.text.strip() in _function_names)):
                    indicate = True
            if indicate:
                text += '⠸'
                hyphenation += '0'
    # Subscript/superscript base level
    while True:
        pos = text.find(_END_SUBSUP)
        if pos == -1:
            break
        indicate = True
        if pos >= len(text) - 1:
            indicate = False
        elif text[pos + 1] in '⠸⠠%s' % (_END_SUBSUP,):
            indicate = False
        else:
            p = pos + 1
            text_len = len(text)
            while p < text_len and text[p] in '\n⠀':
                p += 1
            if p > pos + 1:
                next_text = text[p:]
                for o in _braille_comparison:
                    if next_text.startswith(o.strip('⠀')):
                        indicate = False
                        break
        pos0 = pos
        while pos0 > 0 and text[pos0 - 1] in '⠰⠘':
            pos0 -= 1
        if indicate:
            text = text[:pos0] + '⠐' + text[pos + 1:]
            hyphenation = hyphenation[:pos0] + '0' + hyphenation[pos + 1:]
        else:
            text = text[:pos0] + text[pos + 1:]
            hyphenation = hyphenation[:pos0] + hyphenation[pos + 1:]
    # Whitespace
    text_len = len(text)
    i = 0
    while i < text_len:
        space = True
        if text[i] == _LEFT_WHITESPACE_42:
            t = text[:i]
            if not post and _braille_empty_regexp.match(t):
                space = False
            elif not _braille_number_regexp.search(t):  # numbers may look like punctuation
                for b in (_braille_punctuation + _braille_right_indicators +
                          _braille_left_grouping + _braille_right_grouping + _braille_symbols_42 +
                          ('⠀',)):
                    if b != '⠤' and t.endswith(b):
                        space = False
                        break
        elif text[i] == _RIGHT_WHITESPACE_42:
            t = text[i + 1:]
            if not post and _braille_empty_regexp.match(t):
                space = False
            else:
                for b in (_braille_punctuation + _braille_left_indicators +
                          _braille_left_grouping + _braille_right_grouping + _braille_symbols_42 +
                          ('⠀',)):
                    if b != '⠤' and b != '⠼' and t.startswith(b):
                        # We do insert space before numeric indicator.  It
                        # seems to contradict §42-43 but it respects the
                        # example in §9 (we prefer the examples in case of
                        # conflicts).
                        space = False
                        break
        else:
            i += 1
            continue
        if space:
            text = text[:i] + '⠀' + text[i + 1:]
            hyphenation = hyphenation[:i] + '4' + hyphenation[i + 1:]
            i += 1
        else:
            text = text[:i] + text[i + 1:]
            hyphenation = hyphenation[:i] + hyphenation[i + 1:]
            text_len -= 1
    # Adjust matrices
    while True:
        start = text.find(_MATRIX_START)
        if start == -1:
            break
        end = text.find(_MATRIX_END)
        assert end > start + 1
        rows = text[start + 1:end - 1].split('\n')
        n_columns = len(rows[0].split(_MATRIX_SEPARATOR))
        column_widths = [0] * n_columns
        for r in rows:
            column_widths = [max(w, len(c))
                             for w, c in zip(column_widths, r.split(_MATRIX_SEPARATOR))]
        matrix = ''
        for r in rows:
            cells = r.split(_MATRIX_SEPARATOR)
            for i in range(n_columns):
                c = cells[i]
                matrix += c + '⠀' * (column_widths[i] - len(c) + (1 if i < n_columns - 2 else 0))
            matrix += '\n'
        text = text[:start] + matrix + text[end + 1:]
        hyphenation = hyphenation[:start] + '0' * len(matrix) + hyphenation[end + 1:]
    # Done
    return _Braille(text, hyphenation)

_exporters = {}


def _exporter(tag):
    e = _exporters.get(tag)
    if e is None:
        e = _exporters[tag] = globals().get('_export_' + tag)
    return e


def _export(node, exporter, context, variables, **kwargs):
    braille = getattr(node, 'braille', None)
    if braille is not None:
        return braille
    tag = node.tag
    e = _exporter(tag)
    if e is None:
        result = _text_export('<%s>' % (tag,), exporter, context, variables)
    else:
        with _style(node, variables):
            result = e(node, exporter, context, variables, **kwargs)
    return result


def _text_export(text, exporter, context, variables, node=None, plain=False):
    with _style(node, variables):
        # liblouis doesn't handle typeforms and letter prefixes (correctly) in
        # Nemeth so we can't relay that to it
        prefix = suffix = ''
        style = variables.get('style', '')
        if style.find('bold') >= 0:
            prefix += '⠸'
        if style.find('italic') >= 0:
            prefix += '⠨'
        if ((style and style != 'normal' and not plain and
             text and all(c in string.ascii_letters for c in text))):
            prefix += '⠰'
        elif (not style and text and all(c in string.ascii_letters for c in text) and
              variables.get('enclosed-list') != 'yes' and
              variables.get('direct-delimiters') != 'yes' and
              variables.get('no-letter-prefix') != 'yes' and
              (len(text) == 1 or text in ('cd',))):  # short-form combinations
            prefix = _SINGLE_LETTER_START + prefix
            suffix += _SINGLE_LETTER_END
        else:
            if text in _signs_of_shape or text in _math_comparison_operators:
                suffix += _SINGLE_LETTER_KILLER_SUFFIX
            if text in _signs_of_shape_and_omission or text in _math_comparison_operators:
                prefix = _SINGLE_LETTER_KILLER_PREFIX + prefix
        lang = 'en' if plain else 'nemeth'
        braille = _nemeth_texts.get(text)
        if braille is None:
            braille = exporter.text(context, text, lang=lang).text().strip(_braille_whitespace)
        if prefix:
            braille = prefix + braille
        if suffix:
            braille += suffix
    return _Braille(braille)


def _child_export(node, exporter, context, variables, separators=None, **kwargs):
    braille = _Braille('', '')
    children = _child_nodes(node)
    # Check for Enclosed List (simplified)
    enclosed_list = None
    if len(children) >= 5:
        first = children[0]
        last = children[-1]
        if ((first.tag == 'mo' and first.text.strip() in ('(', '[', '{',) and
             last.tag == 'mo' and last.text.strip() in (')', ']', '}',) and
             all([c.text.strip() not in ('', ';', '.')
                  for c in children if c.tag == 'mo']) and
             all([c.tag != 'mspace' for c in children]) and
             node.find('mtext') is None and
             all([c.text.strip() not in _math_comparison_operators
                  for c in node.findall('.//mo')]))):
            enclosed_list = 'yes'
    # Check for direct contact with opening and closing group signs
    direct_delimiters = None
    if len(children) == 3:
        first = children[0]
        last = children[-1]
        content = children[1]
        while content.tag == 'mrow' and len(_child_nodes(content)) == 1:
            content = _child_nodes(content)[0]
        if ((first.tag == 'mo' and first.text.strip() in ('(', '[', '{',) and
             last.tag == 'mo' and last.text.strip() in (')', ']', '}',) and
             content.tag == 'mi')):
            direct_delimiters = 'yes'
    # Export
    left_node = None
    for i in range(len(children)):
        n = children[i]
        with variables.xlet(('enclosed-list', enclosed_list),
                            ('direct-delimiters', direct_delimiters),
                            ('left-node', left_node)):
            braille = braille + _export(n, exporter, context, variables)
        left_node = n
    return braille


def _op_export(operator, exporter, context, variables, node=None):
    op_braille = _nemeth_operators.get(operator)
    hyphenation = None
    if op_braille is None:
        op_braille = _text_export(operator, exporter, context, variables, node=node).text()
        # If liblouis translation returns something like character code
        # on unknown characters, we try to identify and handle such a
        # situation here.
        if op_braille is None or '⠈⠀⠭' in op_braille or '⡳' in op_braille:
            op_braille = ''.join([c for c in op_braille if c != '⡳'])
            op_braille = exporter.braille_unknown_char(op_braille, operator)
            hyphenation = exporter.HYPH_NO * len(op_braille)
        elif operator in _math_comparison_operators:
            _comparison(operator, op_braille)
            op_braille = _nemeth_operators[operator]
            hyphenation = None
    if hyphenation is None:
        hyphenation = exporter.HYPH_NO * len(op_braille)
    if op_braille[0] == '⠀' and hyphenation[0] == exporter.HYPH_NO:
        hyphenation = exporter.HYPH_NEMETH_WS + hyphenation[1:]
    if op_braille[-1] == '⠀' and hyphenation[-1] == exporter.HYPH_NO:
        hyphenation = hyphenation[:-1] + exporter.HYPH_NEMETH_WS
    return _Braille(op_braille, hyphenation)


# Element exports

def _export_mi(node, exporter, context, variables, **kwargs):
    text = _node_value(node).strip()
    if text == '…':
        return _export_mo(node, exporter, context, variables, **kwargs)
    exported = _text_export(text, exporter, context, variables, node=node)
    if _attribute(node, 'mathvariant') == 'normal':
        exported.prepend(_LEFT_WHITESPACE_42)
        exported.append(_RIGHT_WHITESPACE_42)
    return exported


def _export_mn(node, exporter, context, variables, **kwargs):
    text = _node_value(node).strip()
    prefix = ''
    style_applied = False
    with _style(node, variables):
        style = variables.get('style', '')
        if style.find('bold') >= 0:
            prefix += '⠸'
            style_applied = True
        if style.find('italic') >= 0:
            prefix += '⠨'
            style_applied = True
        if text and text[0] == '-':
            prefix += '⠤'
            text = text[1:]
        if style_applied:
            prefix += '⠼'
        if variables.get('enclosed-list') != 'yes':
            prefix += _CONDITIONAL_NUM_PREFIX
        if context.lang() == 'cs':
            text = text.replace(',', '.')
        translated = prefix + ''.join([_nemeth_numbers[c] for c in text])
    variables.set('enclosed-list', 'no')
    hyphenation = ''.join([exporter.HYPH_NEMETH_WS if c == '⠀' else exporter.HYPH_NEMETH_NUMBER
                           for c in translated])
    return _Braille(translated, hyphenation)


def _export_mo(node, exporter, context, variables, op_form=None, **kwargs):
    op = _node_value(node).strip()
    op_braille = _op_export(op, exporter, context, variables)

    def space(left):
        s = _attribute(node, ('lspace' if left else 'rspace'), None)
        if s is None:
            return op in '—…' or op in(_signs_of_shape_lspace if left else _signs_of_shape_rspace)
        else:
            return not s.startswith('0')
    if space(True):
        op_braille.prepend(_LEFT_WHITESPACE_42)
    if space(False):
        op_braille.append(_RIGHT_WHITESPACE_42)
    if op in _vertical_bars:
        op_braille.prepend(_BEFORE_BAR)
        op_braille.append(_AFTER_BAR)
    if op == '°' and not variables.get('subsup'):
        op_braille.append(_END_SUBSUP)
    if op_braille.text()[0] in _nemeth_digits:
        op_braille.prepend('⠸')
        op_braille.append(_NUM_PREFIX_REQUIRED)
    return op_braille


def _export_mtext(node, exporter, context, variables, **kwargs):
    text = _node_value(node).strip()
    return _text_export(text, exporter, context, variables, node=node, plain=True)


def _export_mspace(node, exporter, context, variables, **kwargs):
    # Just basic support
    width = _attribute(node, 'width', default='0')
    try:
        n = int(width)
    except ValueError:
        if width.endswith('em') or width.endswith('ex'):
            n = int(width[:-2])
        else:
            raise
    return _Braille('⠀' * n, '4' * n)


def _export_ms(node, exporter, context, variables, **kwargs):
    text = '"%s"' % (_node_value(node).strip(),)
    return _text_export(text, exporter, context, variables, node=node, plain=True)


def _export_mrow(node, exporter, context, variables, **kwargs):
    children = _child_nodes(node)
    if ((len(children) == 3 and children[1].tag == 'mtable' and
         children[0].tag == 'mo' and children[2].tag == 'mo')):
        big_prefix = '⠠'
        matrix_start = _export(children[0], exporter, context, variables, **kwargs)
        matrix_start.prepend(big_prefix)
        matrix_end = _export(children[2], exporter, context, variables, **kwargs)
        matrix_end.prepend(big_prefix)
        with variables.xlet(('matrix-start', matrix_start),
                            ('matrix-end', matrix_end)):
            return _export(children[1], exporter, context, variables, **kwargs)
    return _child_export(node, exporter, context, variables)


def _export_mstyle(node, exporter, context, variables, **kwargs):
    break_style = _attribute(node, 'infixlinebreakstyle')  # before, after, duplicate
    with variables.let('infixlinebreakstyle', break_style):
        with _style(node, variables):
            return _child_export(node, exporter, context, variables)


def _export_merror(node, exporter, context, variables, **kwargs):
    return _child_export(node, exporter, context, variables)


def _export_mpadded(node, exporter, context, variables, **kwargs):
    return _child_export(node, exporter, context, variables)


def _export_mphantom(node, exporter, context, variables, **kwargs):
    braille = _child_export(node, exporter, context, variables)
    n = len(braille)
    return _Braille('⠀' * n)


def _export_menclose(node, exporter, context, variables, **kwargs):
    return _child_export(node, exporter, context, variables)


def _export_maction(node, exporter, context, variables, **kwargs):
    selection = _attribute(node, 'selection')
    if not selection:
        selection = 1
    return _export(_child_nodes(node)[selection - 1], exporter, context, variables)


def _export_mfenced(node, exporter, context, variables, **kwargs):
    raise Exception('debug')


def _export_mfrac(node, exporter, context, variables, **kwargs):
    numerator, denominator = _child_nodes(node)
    exported_numerator = _export(numerator, exporter, context, variables, **kwargs)
    exported_denominator = _export(denominator, exporter, context, variables, **kwargs)
    if _attribute(node, 'linethickness') == '0':
        # something like binomical coefficient
        return exported_numerator + _Braille('⠩') + exported_denominator
    left_node = variables.get('left-node')
    if left_node is not None and left_node.tag == 'mn':
        opening = _Braille('⠸⠹')
        closing = _Braille('⠸⠼')
        line = _Braille('⠌')
    else:
        def fraction_level(node):
            level = 0
            for c in _child_nodes(node):
                if c.tag not in ('msub', 'msup'):
                    level = max(level, fraction_level(c))
            if node.tag == 'mfrac':
                level += 1
            return level
        level = fraction_level(node) - 1
        if level > 2:
            raise Exception("Overcomplex fraction")
        opening = _Braille('⠠' * level + '⠹')
        closing = _Braille('⠠' * level + '⠼')
        line = _Braille('⠠' * level + '⠌')
    return opening + exported_numerator + line + exported_denominator + closing


def _mroot(base, index, exporter, context, variables, **kwargs):
    level = variables.get('root-level', 0)
    repeater = _Braille('⠨' * level)
    prefix = _Braille('⠜')
    if index is not None:
        prefix = _Braille('⠣') + _export(index, exporter, context, variables, **kwargs) + prefix
    prefix = repeater + prefix
    suffix = repeater + _Braille('⠻')
    with variables.let('root-level', level + 1):
        if index is None:
            exported_base = _child_export(base, exporter, context, variables, **kwargs)
        else:
            exported_base = _export(base, exporter, context, variables, **kwargs)
    return prefix + exported_base + suffix


def _export_msqrt(node, exporter, context, variables, **kwargs):
    return _mroot(node, None, exporter, context, variables, **kwargs)


def _export_mroot(node, exporter, context, variables, **kwargs):
    base, index = _child_nodes(node)
    return _mroot(base, index, exporter, context, variables, **kwargs)


def __export_subsup(indicator, node, exporter, context, variables, **kwargs):
    base, index = _child_nodes(node)
    base_node = _child_nodes(base)[0] if base.tag == 'msup' else base
    base_tag = base_node.tag
    base_text = (base_node.text or '').strip()
    subsup = variables.get('subsup', _Braille(''))
    new_subsup = subsup
    indicate = True
    if indicator == '⠰' and not subsup.text() and index.tag == 'mn':
        index_text = index.text.strip()
        if index_text and index_text[0] != '-':
            if ((base_node.tag == 'mi' and
                 (len(base_text) == 1 or base_text in _function_names + ('Na',)))):
                indicate = False
            elif base_node.tag == 'mo' and base_text in '∑∏':
                indicate = False
    if indicate:
        new_subsup += _Braille(indicator)
    for n in _child_nodes(index):
        if n.tag == 'mo' and n.text.strip() == ',':
            n.braille = _Braille('⠪')
    if (((not new_subsup) or
         (base_tag == 'mo' and base_text in _signs_of_shape) or
         (base_tag == 'mi' and base_text in _function_names))):
        terminator = _Braille('')
    elif subsup:
        terminator = subsup
    else:
        terminator = _Braille(_END_SUBSUP)
    with variables.let('no-letter-prefix', 'yes'):  # probably not *completely* correct
        exported_base = _export(base, exporter, context, variables, **kwargs)
        if exported_base.text().endswith(_END_SUBSUP):
            exported_base = _Braille(exported_base.text()[:-1], exported_base.hyphenation()[:-1])
        with variables.let('subsup', new_subsup):
            exported_index = _export(index, exporter, context, variables, **kwargs)
        if not indicate:
            exported_index = _Braille(_IMPLICIT_SUBSCRIPT) + exported_index
        return exported_base + new_subsup + exported_index + terminator


def _export_msup(node, exporter, context, variables, **kwargs):
    base, index = _child_nodes(node)
    if index.tag == 'mo' and index.text.strip() in _primes:
        return (_export(base, exporter, context, variables, **kwargs) +
                _Braille(_nemeth_operators[index.text.strip()]))
    if index.tag == 'mrow':
        index_children = _child_nodes(index)
        if ((index_children and index_children[0].tag == 'mo' and
             index_children[0].text.strip() in _primes)):
            base.braille = (_export(base, exporter, context, variables, **kwargs) +
                            _Braille(_nemeth_operators[index_children[0].text.strip()]))
            if len(index_children) > 1:
                index.remove(index_children[0])
            else:
                return base.braille
    return __export_subsup('⠘', node, exporter, context, variables, **kwargs)


def _export_msub(node, exporter, context, variables, **kwargs):
    return __export_subsup('⠰', node, exporter, context, variables, **kwargs)


def _export_msubsup(node, exporter, context, variables, **kwargs):
    base, sub, sup = _child_nodes(node)
    prime = None
    sub_only = False
    if sup.tag == 'mo' and sup.text.strip() in _primes:
        prime = _nemeth_operators[sup.text.strip()]
        sub_only = True
    elif sup.tag == 'mrow':
        sup_children = _child_nodes(sup)
        if ((sup_children and sup_children[0].tag == 'mo' and
             sup_children[0].text.strip() in _primes)):
            prime = _nemeth_operators[sup_children[0].text.strip()]
            if len(sup_children) > 1:
                sup.remove(sup_children[0])
            else:
                sub_only = True
    if prime is not None:
        base.braille = _export(base, exporter, context, variables, **kwargs) + _Braille(prime)
    from xml.etree import ElementTree
    node.clear()
    if sub_only:
        node.tag = 'msub'
        node.append(base)
        node.append(sub)
        return _export_msub(node, exporter, context, variables, **kwargs)
    else:
        node.tag = 'msup'
        ElementTree.SubElement(node, 'msub')
        node.append(sup)
        c = list(node)[0]
        c.append(base)
        c.append(sub)
        return _export_msup(node, exporter, context, variables, **kwargs)


def _modifier(variables):
    modifier = _Braille('⠐')
    subsup = variables.get('subsup')
    if subsup:
        modifier = _Braille(_INNER_SUBSUP) + subsup + modifier
    return modifier


def _export_munder(node, exporter, context, variables, **kwargs):
    base, under = _child_nodes(node)
    result = (_export(base, exporter, context, variables, **kwargs) + _Braille('⠩') +
              _export(under, exporter, context, variables, **kwargs))
    if not variables.get('no-under-boundaries'):
        result = _modifier(variables) + result + _Braille('⠻')
    return result


def _export_mover(node, exporter, context, variables, **kwargs):
    base, over = _child_nodes(node)
    exported_base = _export(base, exporter, context, variables, **kwargs)
    if ((over.tag == 'mo' and over.text.strip() == '¯' and
         base.tag in ('mi', 'mn',) and len(base.text.strip()) == 1)):
        return exported_base + _Braille('⠱')
    return (_modifier(variables) + exported_base + _Braille('⠣') +
            _export(over, exporter, context, variables, **kwargs) + _Braille('⠻'))


def _export_munderover(node, exporter, context, variables, **kwargs):
    base, under, over = _child_nodes(node)
    from xml.etree import ElementTree
    node.clear()
    node.tag = 'mover'
    ElementTree.SubElement(node, 'munder')
    node.append(over)
    c = list(node)[0]
    c.append(base)
    c.append(under)
    with variables.let('no-under-boundaries', True):
        return _export_mover(node, exporter, context, variables, **kwargs)


def _export_mtable(node, exporter, context, variables, **kwargs):
    matrix = _Braille(_MATRIX_START)
    start = variables.get('matrix-start', _Braille(''))
    end = variables.get('matrix-end', _Braille(''))
    rows = _child_nodes(node)
    n_columns = 0
    for r in rows:
        n_columns = max(n_columns, len(_child_nodes(r)))
    with variables.let('matrix-n-columns', n_columns):
        for r in rows:
            matrix += start
            matrix += _export(r, exporter, context, variables, **kwargs)
            matrix += end
            matrix.append('\n')
    matrix.append(_MATRIX_END)
    return matrix


def _export_mtr(node, exporter, context, variables, **kwargs):
    n_columns = variables.get('matrix-n-columns')
    cells = _child_nodes(node)
    from xml.etree import ElementTree
    while len(cells) < n_columns:
        ElementTree.SubElement(node, 'mtd')
    cells = _child_nodes(node)
    row = _Braille('')
    for c in cells:
        row += _export(c, exporter, context, variables, **kwargs)
        row.append(_MATRIX_SEPARATOR)
    if row.text()[0] == _CONDITIONAL_NUM_PREFIX:
        row = _Braille('⠼' + row.text()[1:])
    elif row.text()[:2] == '⠤' + _CONDITIONAL_NUM_PREFIX:
        row = _Braille('⠤⠼' + row.text()[2:])
    return row


def _export_mtd(node, exporter, context, variables, **kwargs):
    return _child_export(node, exporter, context, variables)


def _export_mstack(node, exporter, context, variables, **kwargs):
    rows = []
    for n in _child_nodes(node):
        if n.tag == 'msgroup':
            group_rows = _child_nodes(n)
            shift = int(_attribute(n, 'shift', default='0'))
            if shift > 0:
                rows.append((0, shift,))
            elif shift < 0:
                rows.append((((len(group_rows) - 1) * shift), shift,))
            rows += group_rows
            if shift:
                rows.append('end-shift')
        else:
            rows.append(n)
    widths_1 = [0]
    widths_2 = None
    pattern = ''
    extra_width_1 = [0]
    extra_width_2 = [0]
    widths = widths_1
    extra_width = extra_width_1
    addition_or_subtraction = False
    shift = None
    shift_inc = 0
    with variables.let('msline-present', False):
        for r in rows:
            if isinstance(r, tuple):
                shift, shift_inc = r
                continue
            if r == 'end-shift':
                shift = None
                continue
            exported = _export(r, exporter, context, variables, **kwargs).text()
            if exported and exported[0] in '⠬⠤':
                exported = exported[1:]
                extra_width[0] = 1
                addition_or_subtraction = True
            if exported and exported[0] == _CONDITIONAL_NUM_PREFIX:
                exported = exported[1:]
            for op in ('⠈⠡', '⠨'):
                if exported.startswith(op + _CONDITIONAL_NUM_PREFIX):
                    n = len(op)
                    exported = exported[:n] + exported[n + 1:]
            # Just very simplified row handling: We ignore all the MathML
            # attributes and we assume that: 1. no row has got any special
            # separator pattern suffix not present in other rows; 2. no two
            # rows have distinct non-empty separator pattern prefixes.
            parts = []
            p = ''
            i = j = 0
            for op in ('⠈⠡',):
                if exported.startswith(op):
                    i = len(op)
            if shift:
                exported += '⠀' * shift
                shift += shift_inc
            l = len(exported)
            while True:
                while i < l and exported[i] in '⠴⠂⠆⠒⠲⠢⠖⠶⠦⠔':
                    i += 1
                parts.append(exported[j:i])
                if i == l:
                    break
                p += exported[i]
                i += 1
                j = i
            if pattern is not None and not pattern.endswith(p):
                if p.endswith(pattern):
                    widths[0:0] = [0] * (len(p) - len(pattern))
                    pattern = p
                else:
                    pattern = None
            for i in range(-1, -len(p) - 2, -1):
                widths[i] = max(widths[i], len(parts[i]))
            if widths_2 is None and variables.get('msline-present'):
                widths = widths_2 = copy.copy(widths_1)
                extra_width = extra_width_2
        if pattern is None:
            if addition_or_subtraction:
                raise Exception("Non-matching mstack rows")
            pattern = ''
        max_width = (max(sum(widths_1) + extra_width_1[0], sum(widths_2) + extra_width_2[0]) +
                     len(pattern))
        msline_present = variables.get('msline-present')
        if msline_present:
            max_width += 2
    widths_1 = [0] * (len(widths_2) - len(widths_1)) + widths_1
    widths = widths_1
    shift = None
    result = ''
    with variables.xlet(('ms-widths', widths),
                        ('ms-pattern', pattern),
                        ('ms-max-width', max_width),
                        ('msline-present', False),):
        for r in rows:
            if isinstance(r, tuple):
                shift, shift_inc = r
                continue
            if r == 'end-shift':
                shift = None
                continue
            exported = _export(r, exporter, context, variables, **kwargs).text()
            if exported and exported[0] == _CONDITIONAL_NUM_PREFIX:
                exported = exported[1:]
            if shift is not None:
                exported += '⠀' * shift
                shift += shift_inc
            if len(exported) < max_width:
                if exported and exported[0] in '⠬⠤':
                    prefix = exported[0]
                    exported = exported[1:]
                    if exported and exported[0] == _CONDITIONAL_NUM_PREFIX:
                        exported = exported[1:]
                else:
                    prefix = ''
                if msline_present:
                    prefix = '⠀' + prefix
                formatted = ''
                for i in range(len(pattern) - 1, -1, -1):
                    pos = exported.rfind(pattern[i])
                    part = exported[pos + 1:]
                    exported = exported[:max(pos, 0)]
                    part = '⠀' * (widths[i + 1] - len(part)) + part
                    formatted = pattern[i] + part + formatted
                formatted = (prefix + '⠀' * (widths[0] - len(exported)) + exported + formatted)
                if msline_present:
                    formatted = '⠀' * max(max_width - 1 - len(formatted), 0) + formatted
            else:
                formatted = exported
            result = result + formatted.rstrip('⠀') + '\n'
            if variables.get('msline-present'):
                widths = widths_2
    result = _Braille(result)
    return result


def _export_msgroup(node, exporter, context, variables, **kwargs):
    return _child_export(node, exporter, context, variables)


def _export_msrow(node, exporter, context, variables, **kwargs):
    return _child_export(node, exporter, context, variables)


def _export_msline(node, exporter, context, variables, **kwargs):
    variables.set('msline-present', True)
    width = variables.get('ms-max-width')
    if width is None:
        text = ''
    else:
        text = '⠒' * (width)
    return _Braille(text)

# def _export_mmultiscripts(node, **kwargs):
# def _export_mlabeledtr(node, **kwargs):
# def _export_maligngroup(node, **kwargs):
# def _export_mscarries(node, **kwargs):
# def _export_mscarry(node, **kwargs):
# def _export_mlongdiv(node, **kwargs):
