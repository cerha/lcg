# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005 Brailcom, o.p.s.
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

We need something very simple and quite specific, so it is not worth using
'htmlgen'.

"""

import operator
import types

from util import *

def _attr(*pairs):
    all = [v is not None and ' %s="%s"' % (a, v) or '' for a, v in pairs]
    return "".join(all)

def _tag(tag, attr, content, concat=''):
    start = '<%s%s>' % (tag, _attr(*attr))
    end = '</%s>' % tag
    if isinstance(content, (types.ListType, types.TupleType)):
        result = (start,) + tuple(content) + (end,)
    else:
        result = [start, content, end]
    return concat.join(result)

# Some basic ones...

def h(title, level=2):
    return '<h%d>%s</h%d>' % (level, title, level)
    
def b(text):
    return '<b>%s</b>' % text

def p(*content, **kwargs):
    return _tag('p', (('class', kwargs.get('cls')),), content, concat='\n')

def div(content, cls=None):
    return _tag('div', (('class', cls),), content, concat='\n')

def link(label, url, brackets=False,
         title=None, target=None, cls=None, hotkey=None):
    if hotkey:
        t = '(Alt-%s)' % hotkey
        title = title and title + ' ' + t or t
    attr = (('href', url), ('title', title), ('target', target),
            ('class', cls), ('accesskey', hotkey))
    result = _tag('a', attr, label)
    return brackets and '['+result+']' or result

def itemize(items, indent=0, ordered=False, style=None, cls=None):
    spaces = ' ' * indent
    tag = ordered and 'ol' or 'ul'
    attr = style and ' style="list-style-type: %s"' % style or ''
    items = [spaces+"  <li>%s</li>" % i for i in items]
    return "\n".join([spaces+"<"+tag+attr+">"] + items + [spaces+"</"+tag+">"])

# Form controls

def _input(type, name=None, value=None, handler=None, cls=None, size=None,
           readonly=False):
    handler = handler and "javascript: %s" % handler
    return '<input type="%s"%s%s>' % (type, _attr(('name', name),
                                                  ('value', value),
                                                  ('size', size),
                                                  ('onClick', handler),
                                                  ('class', cls)),
                                      readonly and ' readonly' or '')

def field(text='', name='', size=20, cls=None, readonly=False):
    cls = cls and 'text ' + cls or 'text'
    return _input('text', name=name, value=text, size=size, cls=cls,
                  readonly=readonly)

def button(label, handler, cls=None):
    cls = cls and 'button ' + cls or 'button'
    return _input('button', value=label, handler=handler, cls=cls)

def reset(label, handler=None, cls=None):
    return _input('reset', handler=handler, value=label, cls=cls)

def hidden(name, value):
    return _input('hidden', name=name, value=value)

def radio(name, handler=None, value=None, cls=None):
    return _input('radio', name=name, handler=handler, value=value, cls=cls)

def select(name, options, handler=None, default=""):
    opts = [_tag('option', (('value', value),), text)
            for text, value in options]
    if default is not None:
        opts.insert(0, _tag('option', (), default))
    attr = (('name', name), ('onChange', handler))
    return _tag('select', attr, opts, concat="\n")

# Special controls

def speaking_text(text, media):
    a1 = link(text, "javascript: play_audio('%s')" % media.url())
    a2 = link(text, media.url())
    return script_write(a1, a2)

# JavaScript code generation.

def script(code, noscript=None):
    noscript = noscript and '<noscript>'+ noscript +'</noscript>' or ''
    return '<script type="text/javascript" language="Javascript"><!--\n' + \
           code +' //--></script>' + noscript

def script_write(content, noscript=None):
    c = content.replace('"','\\"').replace('\n','\\n').replace("'","\\'")
    return script('document.write("'+ c +'");', noscript)

def js_value(var):
    if isinstance(var, types.StringTypes):
        return "'%s'" % var.replace("'", "\\'")
    elif isinstance(var, types.IntType):
        return str(var)
    elif isinstance(var, (types.ListType, types.TupleType)):
        return js_array(var)
    else:
        raise Exception("Invalid type for JavaScript conversion:", var)
    
def js_array(items):
    assert isinstance(items, (types.ListType, types.TupleType))
    return '[' + ", ".join([js_value(i) for i in items]) + ']'

def js_dict(items):
    assert isinstance(items, (types.ListType, types.TupleType, types.DictType))
    if isinstance(items, types.DictType):
        items = items.items()
    assert is_sequence_of(dict(items).keys(), types.StringType)
    return '{' + ", ".join([k+": "+js_value(v) for k,v in items]) + '}'
