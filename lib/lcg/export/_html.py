# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005, 2006 Brailcom, o.p.s.
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

"""Simple HTML generation utility functions.

This is an attempt to separate at least the most used constructs somewhere out of
the code to allow later rewrite of the output rutines by something more
sophisticated (e.g. pluggable formatters) if necessary.

We need something very simple and quite specific, so it is not worth using
'htmlgen'.

"""

import types
from lcg import *

def _attr(*pairs):
    attributes = []
    for attr, value in pairs:
        if value is None:
            continue
        elif isinstance(value, types.BooleanType):
            if not value:
                continue
            string = attr
        else:
            if isinstance(value, int):
                value = str(value)
            string = concat(attr+'="', value, '"')
        attributes.append(concat(' ', string))
    return concat(*attributes)

def _tag(tag, attr, content, newlines=False):
    start = concat('<'+tag, _attr(*attr), '>')
    end = '</%s>' % tag
    if isinstance(content, (types.ListType, types.TupleType)):
        result = (start,) + tuple(content) + (end,)
    else:
        result = (start, content, end)
    return concat(result, separator=(newlines and "\n" or ""))

# Some basic ones...

def h(title, level=2):
    return concat('<h%d>' % level, title, '</h%d>' % level)
    
def strong(text):
    return concat('<strong>', text, '</strong>')

def pre(text, cls=None):
    return _tag('pre', (('class', cls),), text)

def span(text, cls=None, id=None, lang=None):
    attr = (('class', cls),
            ('lang', lang),
            ('id', id))
    return _tag('span', attr, text)

def p(*content, **kwargs):
    return _tag('p', (('class', kwargs.get('cls')),), content, newlines=True)

def br(cls=None):
    return concat('<br', _attr(('class', cls),), '/>')

def hr(cls=None):
    return concat('<hr', _attr(('class', cls),), '/>')

def div(content, id=None, cls=None, lang=None):
    args = (('class', cls), ('id', id), ('lang', lang))
    return _tag('div', args, content, newlines=True)

def map(content, cls=None, lang=None, name=None, title=None):
    args = (('class', cls), ('lang', lang), ('name', name), ('title', title))
    return _tag('map', args, content, newlines=True)

def link(label, uri, name=None, title=None, target=None, cls=None, hotkey=None):
    if hotkey:
        t = '(Alt-%s)' % hotkey
        title = title and title + ' ' + t or t
    if target:
        cls = (cls and cls+' ' or '') + 'external-link'
    attr = (('href', uri), ('name', name), ('title', title), ('target', target),
            ('class', cls), ('accesskey', hotkey))
    return _tag('a', attr, label)

def list(items, indent=0, ordered=False, style=None, cls=None, lang=None):
    tag = ordered and 'ol' or 'ul'
    attr = _attr(('style', style and 'list-style-type: %s' % style),
                 ('lang', lang),
                 ('class', cls))
    spaces = ' ' * indent
    items = [concat(spaces+"  <li>", i, "</li>") for i in items]
    return concat(spaces+"<"+tag, attr, ">", items, spaces+"</"+tag+">")

# Form controls

def form(content, name=None, cls=None, action="#", method=None):
    attr = (('name', name), ('action', action), ('method', method),
            ('class', cls))
    return _tag('form', attr, content, newlines=True)

def fieldset(content, legend=None, cls=None):
    if legend:
        content = (_tag('legend', (), legend),) + tuple(content)
    return _tag('fieldset', (('class', cls),), content, newlines=True)

def label(text, id, lang=None, cls=None):
    return _tag('label', (('for', id), ('lang', lang), ('class', cls)), text)

def _input(type, name=None, value=None, title=None, id=None,
           onclick=None, size=None, cls=None, readonly=False, checked=False,
           disabled=False):
    assert isinstance(checked, types.BooleanType)
    assert isinstance(readonly, types.BooleanType)
    assert isinstance(disabled, types.BooleanType)
    assert not checked or type in ('radio', 'checkbox')
    attr = _attr(('name', name),
                 ('value', value),
                 ('title', title),
                 ('id', id),
                 ('size', size),
                 ('onclick', onclick),
                 ('class', cls),
                 ('checked', checked),
                 ('readonly', readonly),
                 ('disabled', disabled))
    return concat('<input type="%s"' % type, attr, ' />')

def field(value='', name='', size=20, **kwargs):
    kwargs['cls'] = kwargs.has_key('cls') and 'text '+kwargs['cls'] or 'text'
    return _input('text', name=name, value=value, size=size, **kwargs)

def radio(name, **kwargs):
    return _input('radio', name=name, **kwargs)

def hidden(name, value):
    return _input('hidden', name=name, value=value)

def button(label, handler, cls=None, title=None):
    cls = cls and 'button ' + cls or 'button'
    return _input('button', value=label, onclick=handler, cls=cls, title=title)

def reset(label, onclick=None, cls=None):
    return _input('reset', onclick=onclick, value=label, cls=cls)

def submit(label, onclick=None, cls=None):
    return _input('submit', onclick=onclick, value=label, cls=cls)

def select(name, options, onchange=None, selected=None, id=None):
    assert selected is None or selected in [value for text, value in options],\
           (selected, options)
    opts = [_tag('option',
                 (('value', value),
                  ('selected', (value == selected))),
                 text)
            for text, value in options]
    attr = (('name', name), ('id', id), ('onchange', onchange))
    return _tag('select', attr, opts, newlines=True)

def checkbox(name, id=None, checked=False, disabled=False, cls=None):
    return _input('checkbox', id=id, checked=checked, disabled=disabled,
                  cls=cls)

def textarea(name, value='', id=None, cls=None, rows=None, cols=None):
    attr = (('name', name),
            ('id', id),
            ('rows', rows),
            ('cols', cols),
            ('class', cls))
    return _tag('textarea', attr, value)
    
# Special controls

def speaking_text(text, media):
    id_ = 'text_%s' % id(media)
    a1 = button(text, "play_audio('%s');" % media.uri(),
                cls='speaking-text')
    a2 = link(text, media.uri(), cls='speaking-text')
    return script_write(a1, a2)

# JavaScript code generation.

def script(code, noscript=None):
    noscript = noscript and \
               concat('<noscript>', noscript, '</noscript>') or ''
    if code:
        code = concat('<!--\n', code, ' //-->\n')
    return concat('<script type="text/javascript" language="Javascript">',
                        code, '</script>', noscript)

def script_write(content, noscript=None, condition=None):
    #return content
    #return noscript
    if content:
        c = content.replace('"','\\"').replace("'","\\'")
        c = c.replace('</', '<\\/').replace('\n','\\n')
        content = concat('document.write("', c, '");')
        if condition:
            content = concat('if (', condition, ') ', content)
    return script(content, noscript)

def js_value(var):
    if isinstance(var, types.StringTypes):
        return "'" + var.replace("'", "\\'") + "'"
    elif isinstance(var, (TranslatableText, Concatenation)):
        return concat("'", var.replace("'", "\\'"), "'")
    elif isinstance(var, types.IntType):
        return str(var)
    elif isinstance(var, (types.ListType, types.TupleType)):
        return js_array(var)
    else:
        raise Exception("Invalid type for JavaScript conversion:", var)
    
def js_array(items):
    assert isinstance(items, (types.ListType, types.TupleType))
    values = [js_value(i) for i in items]
    return concat('[', concat(values, separator=", "), ']')

def js_dict(items):
    assert isinstance(items, (types.ListType, types.TupleType, types.DictType))
    if isinstance(items, types.DictType):
        items = items.items()
    assert is_sequence_of(dict(items).keys(), types.StringType)
    pairs = [concat("'%s': " % k, js_value(v)) for k,v in items]
    return concat('{', concat(pairs, separator=", "), '}')

