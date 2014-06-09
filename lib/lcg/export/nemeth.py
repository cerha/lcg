# -*- coding: utf-8 -*-

# Copyright (C) 2013, 2014 Brailcom, o.p.s.
#
# COPYRIGHT NOTICE
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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

from contextlib import contextmanager
import re
import string

import lcg

from braille import _Braille, _braille_whitespace
import entities


_CONDITIONAL_NUM_PREFIX = '\ue020'
_NUM_PREFIX_REQUIRED = '\ue021'
_SINGLE_LETTER_START = '\ue022'
_SINGLE_LETTER_END = '\ue023'
_SINGLE_LETTER_KILLER_PREFIX = '\ue024'
_SINGLE_LETTER_KILLER_SUFFIX = '\ue025'
_LEFT_WHITESPACE_42 = '\ue026' # Nemeth §42
_RIGHT_WHITESPACE_42 = '\ue027' # Nemeth §42

_nemeth_numbers = {'0': '⠴', '1': '⠂', '2': '⠆', '3': '⠒', '4': '⠲',
                   '5': '⠢', '6': '⠖', '7': '⠶', '8': '⠦', '9': '⠔',
                   ' ': '⠀', '.': '⠨', ',': '⠠'}

_signs_of_shape = ''
_braille_punctuation = ('⠂',)
_braille_left_grouping = ()
_braille_right_grouping = ()
def _comparison(op):
    return _SINGLE_LETTER_KILLER_PREFIX + op + _SINGLE_LETTER_KILLER_SUFFIX
def _punctuation(symbol, braille):
    global _braille_punctuation, _nemeth_operators
    if braille not in _braille_punctuation:
        _braille_punctuation += (braille,)
    _nemeth_operators[symbol] = braille
def _shape(symbol, braille):
    global _signs_of_shape, _nemeth_operators
    if symbol not in _signs_of_shape:
        _signs_of_shape += symbol
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
_nemeth_operators = {
    '*': '⠈⠼' + _NUM_PREFIX_REQUIRED,
    '#': '⠨⠼' + _NUM_PREFIX_REQUIRED,
    '=': _comparison('⠀⠨⠅⠀'),
    '×': '⠈⠡',
    '∥': '⠳⠳',
    '\u2061': '⠀' + _SINGLE_LETTER_KILLER_PREFIX, # function application
}
_punctuation("'", '⠄')
_punctuation(':', '⠒')
_punctuation(',', '⠠⠀')
_punctuation('–', '⠤⠤')
_punctuation('—', '⠤⠤⠤⠤')
_punctuation('…', '⠄⠄⠄')
_punctuation('!', '⠖')
_punctuation('-', '⠤')
_punctuation('.', '⠲')
_punctuation('?', '⠦')
_punctuation('?', '⠿')          # we interpret question mark as an omission character
_punctuation('‘', '⠠⠦')
_punctuation('“', '⠦')
_punctuation('’', '⠴⠄')
_punctuation('”', '⠴')
_punctuation(';', '⠆')
_shape('∠', '⠫⠪')
_shape('△', '⠫⠞')
_shape('▵', '⠫⠞')
_shape('□', '⠫⠲')
_shape('◽', '⠫⠲')
_shape('◯', '⠫⠉')
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
                              '̸⪳⪴⪵⪶⪷⪸⪹⪺⪻⪼')
_signs_of_shape_and_omission = _signs_of_shape

_braille_left_indicators = ('⠰', '⠸', '⠨', '⠨⠈', '⠠⠠', '⠈⠈', '⠘', '⠣', '⠩', '⠪', '⠻', '⠠',
                            '⠶⠶⠶', '⠹', '⠠⠹', '⠠⠠⠹', '⠸⠹', '⠈⠻', '⠐', '⠘', '⠘⠘', '⠘⠰', '⠘⠘⠘',
                            '⠘⠘⠰', '⠘⠰⠘', '⠘⠰⠰', '⠰', '⠰⠘', '⠰⠰', '⠰⠘⠘', '⠰⠘⠰', '⠰⠰⠘', '⠰⠰⠰',
                            '⠣', '⠣⠣', '⠩', '⠩⠩', '⠈', '⠼', '⠣', '⠨', '⠨⠨', '⠨⠨⠨', '⠫', '⠸⠫',
                            '⠠⠨', '⠠⠄⠸', '⠠⠄⠨',)
_braille_right_indicators = ('⠼', '⠠⠼', '⠠⠠⠼', '⠸⠼', '⠻', '⠸⠠⠄', '⠨⠠⠄', '⠹', '⠠⠹', '⠠⠠⠹',)
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
    return node.getchildren()

def _attribute(node, name, default=None):
    return node.get(name, default)

def _node_value(node):
    value = node.text
    if value is None:
        # this may happen with unresolved entities
        value = '?'
    return value


# Common export functions

_num_prefix_regexp = re.compile('(^|[\n⠀%s%s])([%s%s%s]*⠤?)(%s)' %
                                (_NUM_PREFIX_REQUIRED, _RIGHT_WHITESPACE_42,
                                 _SINGLE_LETTER_KILLER_PREFIX, _SINGLE_LETTER_KILLER_SUFFIX,
                                 _LEFT_WHITESPACE_42, _CONDITIONAL_NUM_PREFIX,),
                                re.M)
_prefixed_punctuation = "':.!-?‘“’”;\""
_punctuation_regexp = re.compile('([,–—]+)[%s]' % (_prefixed_punctuation,))

_braille_number_regexp = re.compile('⠼[⠴⠂⠆⠒⠲⠢⠖⠶⠦⠔⠨]+$')
_braille_empty_regexp = re.compile('[⠀\ue000-\ue0ff]*$')
def mathml_nemeth(exporter, context, element):
    # Implemented: Rule I - XII (partially)
    # Missing: Rule XIII -- Rule XXV
    class EntityHandler(element.EntityHandler):
        def __init__(self, *args, **kwargs):
            super(EntityHandler, self).__init__(*args, **kwargs)
            self._data = entities.entities
        def __getitem__(self, key):
            return self._data.get(key, '?')
    entity_handler = EntityHandler()
    top_node = element.tree_content(entity_handler, transform=True)
    pre = element.previous_element()
    post = element.next_element()
    variables = _Variables()
    braille = _child_export(top_node, exporter, context, variables).strip()
    text = braille.text()
    hyphenation = braille.hyphenation().replace(exporter.HYPH_WS, exporter.HYPH_NEMETH_WS)
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
    # Cleanup
    text_len = len(text)
    i = 0
    while i < text_len:
        if text[i] in (_CONDITIONAL_NUM_PREFIX, _NUM_PREFIX_REQUIRED,
                       _SINGLE_LETTER_KILLER_PREFIX, _SINGLE_LETTER_KILLER_SUFFIX,):
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
                children = last_children = last_element.getchildren()
                while last_element.tag not in ('mi', 'mo', 'mn',) and children:
                    last_children = children
                    children = last_element.getchildren()
                    last_element = children[-1]
                if last_element.tag == 'mo' and last_element.text in ',-–—':
                    if len(last_children) > 1:
                        last_element = last_children[-2]
                if ((last_element.tag == 'mo' or
                     (last_element.tag == 'mi' and last_element.text == '…'))):
                    op = last_element.text.strip()
                    if op in ('–—…' + _signs_of_shape + _math_comparison_operators):
                        indicate = True
                if ((not indicate and last_element.tag == 'mi' and
                     last_element.text.strip() in ('sin', 'cos', 'tg', 'cotg',))):
                    indicate = True
            if indicate:
                text += '⠸'
                hyphenation += '0'
    # Whitespace
    text_len = len(text)
    i = 0
    while i < text_len:
        space = True
        if text[i] == _LEFT_WHITESPACE_42:
            t = text[:i]
            if not post and _braille_empty_regexp.match(t):
                space = False
            elif not _braille_number_regexp.search(t): # numbers may look like punctuation
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
    # Done
    return _Braille(text, hyphenation)

_exporters = {}
def _exporter(tag):
    e = _exporters.get(tag)
    if e is None:
        e = _exporters[tag] = globals().get('_export_' + tag)
    return e

def _export(node, exporter, context, variables, **kwargs):
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
        if style and not plain and text and all(c in string.ascii_letters for c in text):
            prefix += '⠰'
        elif (not style and text and all(c in string.ascii_letters for c in text) and
              variables.get('enclosed-list') != 'yes' and
              variables.get('no-letter-prefix') != 'yes' and
              (len(text) == 1 or text in ('cd',))): # short-form combinations
            prefix = _SINGLE_LETTER_START + prefix
            suffix += _SINGLE_LETTER_END
        else:
            if text in _signs_of_shape or text in _math_comparison_operators:
                suffix += _SINGLE_LETTER_KILLER_SUFFIX
            if text in _signs_of_shape_and_omission or text in _math_comparison_operators:
                prefix = _SINGLE_LETTER_KILLER_PREFIX + prefix
        lang = 'en' if plain else 'nemeth'
        if text == 'cos':
            # It gets translated wrong in liblouis
            braille = '⠉⠕⠎'
        else:
            braille = exporter.text(context, text, lang=lang).text().strip(_braille_whitespace)
        if prefix:
            braille = prefix + braille
        if suffix:
            braille += suffix
    return _Braille(braille)
    
def _child_export(node, exporter, context, variables, separators=None):
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
        if ((first.tag == 'mo' and first.text.strip() in ('(', '[', '{',) and
             last.tag == 'mo' and last.text.strip() in (')', ']', '}',) and
             content.tag == 'mi')):
            direct_delimiters = 'yes'
    # Export
    op_form = None
    left_node = None
    for i in range(len(children)):
        n = children[i]
        if False and n.tag == 'mo':
            if i == 0 or op_form == 'infix':
                op_form = 'prefix'
            elif i == len(children) - 1:
                op_form = 'postfix'
            else:
                op_form = (_nemeth_operators.get((n.text or '').strip(), ('infix',))[0] or
                           'infix')
        else:
            op_form = None
        with variables.xlet(('enclosed-list', enclosed_list),
                            ('direct-delimiters', direct_delimiters),
                            ('left-node', left_node)):
            braille = braille + _export(n, exporter, context, variables, op_form=op_form)
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
        if op_braille is None or op_braille.find(u'⠈⠀⠭') >= 0:
            op_braille = '⠿⠿⠿%s⠿⠿⠿' % (op_braille,)
            hyphenation = exporter.HYPH_NO * len(op_braille)
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
    return _text_export(text, exporter, context, variables, node=node)

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
        translated = prefix + string.join([_nemeth_numbers[c] for c in text], '')
    variables.set('enclosed-list', 'no')
    hyphenation = string.join([exporter.HYPH_NEMETH_WS if c == '⠀' else exporter.HYPH_NEMETH_NUMBER
                               for c in translated], '')
    return _Braille(translated, hyphenation)

def _export_mo(node, exporter, context, variables, op_form=None, **kwargs):
    op = _node_value(node).strip()
    op_braille = _op_export(op, exporter, context, variables)
    if op in '—…':
        op_braille.prepend(_LEFT_WHITESPACE_42)
        op_braille.append(_RIGHT_WHITESPACE_42)
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
        if width.endswith('em'):
            n = int(width[:-2])
        else:
            raise
    return _Braille('⠀' * n, '4' * n)

def _export_ms(node, exporter, context, variables, **kwargs):
    text = '"%s"' % (_node_value(node).strip(),)
    return _text_export(text, exporter, context, variables, node=node, plain=True)

def _export_mrow(node, exporter, context, variables, **kwargs):
    return _child_export(node, exporter, context, variables)

def _export_mstyle(node, exporter, context, variables, **kwargs):
    break_style = _attribute(node, 'infixlinebreakstyle') # before, after, duplicate
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
    return (opening + _export(numerator, exporter, context, variables, **kwargs) + line +
            _export(denominator, exporter, context, variables, **kwargs) + closing)

def _export_msqrt(node, **kwargs):
    pass
    # return _Braille('⠩', '3') + child_export(node) + _Braille('⠱', '0')

def _export_mroot(node, **kwargs):
    base, root = child_nodes(node, exported=True)
    # return _Braille('⠠⠌', '00') + root + _Braille('⠩', '3') + base + _Braille('⠱', '0')

def _export_msub(node, **kwargs):
    base, sub = child_nodes(node, exported=True)
    # return base + _Braille('⠡', '0') + sub + _Braille('⠱', '0')

def _export_msup(node, **kwargs):
    base, sup = child_nodes(node, exported=True)
    # return base + _Braille('⠌', '0') + sup + _Braille('⠱', '0')

def _export_msubsup(node, **kwargs):
    base, sub, sup = child_nodes(node, exported=True)
    # return base + _Braille('⠌', '0') + sub + _Braille('⠱⠡', '00') + sup + \
    #     _Braille('⠱', '0')

def _export_munder(node, **kwargs):
    base, under = child_nodes(node, exported=True)
    # return base + _Braille('⠠⠡', '00') + under + _Braille('⠱', '0')

def _export_mover(node, **kwargs):
    base_child, over_child = child_nodes(node)
    # base = export(base_child)
    # if ((over_child.tag == 'mo' and over_child.text.strip() == '¯' and
    #      base_child.tag == 'mn')):
    #     braille = base + base
    #     braille.append('⠤', '0')
    # else:
    #     over = export(over_child)
    #     braille = base + over
    # return braille

def _export_munder_mover(node, **kwargs):
    base, under, over = child_nodes(node, exported=True)
    # return (base + _Braille('⠠⠡', '00') + under + _Braille('⠱⠠⠌', '000') + over +
    #         _Braille('⠱', '0'))

#def _export_mmultiscripts(node, **kwargs):
#def _export_mtable(node, **kwargs):
#def _export_mtr(node, **kwargs):
#def _export_mlabeledtr(node, **kwargs):
#def _export_mtd(node, **kwargs):
#def _export_maligngroup(node, **kwargs):
#def _export_mstack(node, **kwargs):
#def _export_msgroup(node, **kwargs):
#def _export_msrow(node, **kwargs):
#def _export_msline(node, **kwargs):
#def _export_mscarries(node, **kwargs):
#def _export_mscarry(node, **kwargs):
#def _export_mlongdiv(node, **kwargs):
