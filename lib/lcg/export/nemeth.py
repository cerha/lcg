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

from braille import _Braille, _braille_whitespace
import entities


_CONDITIONAL_NUM_PREFIX = '\ue020'
_NUM_PREFIX_REQUIRED = '\ue021'

_num_prefix_regexp = re.compile('(^|[\n⠀%s])(⠤?)(%s)' %
                                (_NUM_PREFIX_REQUIRED, _CONDITIONAL_NUM_PREFIX,),
                                re.M)

_nemeth_numbers = {'0': '⠴', '1': '⠂', '2': '⠆', '3': '⠒', '4': '⠲',
                   '5': '⠢', '6': '⠖', '7': '⠶', '8': '⠦', '9': '⠔',
                   ' ': '⠀', '.': '⠨', ',': '⠠'}
_nemeth_operators = {
    '*': '⠈⠼' + _NUM_PREFIX_REQUIRED,
    '#': '⠨⠼' + _NUM_PREFIX_REQUIRED,
    '=': '⠀⠨⠅⠀',
    ',': '⠠⠀',
    '…': '⠀⠄⠄⠄⠀',
    '×': '⠈⠡',
    '\u2061': '⠀',              # function application
}
_math_comparison_operators = ('<=>≂≂̸≃≄≅≆≇≈≉≊≋≋̸≌≍≏≏̸≐≐̸≑≓≗≜≟≠≡≢≤≥≦≦̸≧≧̸≨≩≪≪̸≫≫̸≮≯≰≱≲≳≴≵≶≷≸'
                              '≹≺≻≼≽≾≿≿̸⊀⊁⊴⊵⋍⋖⋗⋘⋘̸⋙⋙̸⋚⋛⋞⋟⋠⋡⋦⋧⋨⋩⋪⋫⋬⋭'
                              '⦔⩭⩭̸⩯⩰⩰̸⩵⩸⩹⩺⩻⩼⩽⩽̸⩾⩾̸⩿⪀⪁⪂⪃⪄⪅⪆⪇⪈⪉⪊⪋⪌⪍⪎⪏⪐⪑⪒⪓⪔⪕⪖⪗⪘⪙⪚⪝⪞⪟⪠⪡⪡̸⪢⪢̸⪦⪨⪩⪬⪮⪯⪯̸⪰⪰'
                              '̸⪳⪴⪵⪶⪷⪸⪹⪺⪻⪼')


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

def _child_nodes(node, exported=False):
    children = node.getchildren()
    if exported:
        children = [_export(c) for c in children]
    return children

def _attribute(node, name, default=None):
    return node.get(name, default)

def _node_value(node):
    value = node.text
    if value is None:
        # this may happen with unresolved entities
        value = '?'
    return value


# Common export functions

def mathml_nemeth(exporter, context, element):
    # Implemented: Rule I - III (partially)
    # Missing: Rule IV -- Rule XXV
    class EntityHandler(element.EntityHandler):
        def __init__(self, *args, **kwargs):
            super(EntityHandler, self).__init__(*args, **kwargs)
            self._data = entities.entities
        def __getitem__(self, key):
            return self._data.get(key, '?')
    entity_handler = EntityHandler()
    top_node = element.tree_content(entity_handler, transform=True)
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
    for c in (_CONDITIONAL_NUM_PREFIX, _NUM_PREFIX_REQUIRED,):
        while True:
            pos = text.find(c)
            if pos == -1:
                break
            text = text[:pos] + text[pos + 1:]
            hyphenation = hyphenation[:pos] + hyphenation[pos + 1:]
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
        prefix = ''
        style = variables.get('style', '')
        if style.find('bold') >= 0:
            prefix += '⠸'
        if style.find('italic') >= 0:
            prefix += '⠨'
        if style and not plain and text and text[0] in string.ascii_letters:
            prefix += '⠰'
        lang = 'en' if plain else 'nemeth'
        braille = exporter.text(context, text, lang=lang).text().strip(_braille_whitespace)
        if prefix:
            braille = prefix + braille
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
                  for c in node.findall('mi')]))):
            enclosed_list = 'yes'
    # Export
    op_form = None
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
        # if braille and separators:
        #     separator = separators[-1] if i > len(separators) else separators[i - 1]
        #     hyph_separator = self._HYPH_NEMETH_WS if len(separator) == 1 else None
        #     braille.append(separator, hyph_separator)
        with variables.let('enclosed-list', enclosed_list):
            braille = braille + _export(n, exporter, context, variables, op_form=op_form)
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
    # form = _attribute(node, 'form', op_form) # prefix, infix, postfix
    separator = _attribute(node, 'separator') # true, false
    # We should probably ignore these as Braille script has its own
    # rules of math line breaking:
    # linebreak = attribute(node, 'linebreak') # auto, newline, nobreak, goodbreak, badbreak
    # linebreakstyle = attribute(node, 'linebreakstyle')
    #                  # before, after, duplicate, infixlinebreakstyle
    op = _node_value(node).strip()
    op_braille = _op_export(op, exporter, context, variables)
    if separator == 'true':
        if op_braille.text()[-1] not in (' ', '⠀',):
            op_braille.append('⠀')
    return op_braille

def _export_mtext(node, exporter, context, variables, **kwargs):
    text = _node_value(node).strip()
    return _text_export(text, exporter, context, variables, node=node, plain=True)

def _export_mspace(node, exporter, context, variables, **kwargs):
    return _text_export(' ', exporter, context, variables, plain=True)

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

def _export_mfrac(node, **kwargs):
    child_1, child_2 = child_nodes(node, exported=True)
    # mfrac_flag = 'mfrac'
    # if len(node.getiterator(mfrac_flag)) > 1:
    #     line = _Braille('⠻⠻', '00')
    # else:
    #     line = _Braille('⠻', '3')
    # return _Braille('⠆', '0') + child_1 + line + child_2 + _Braille('⠰', '0')

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
