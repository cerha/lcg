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

This is an attempt to separate at least the most used constructs somewhere out of
the code to allow later rewrite of the output rutines by something more
sophisticated (e.g. pluggable formatters) if necessary.

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
        result = (start, content, end)
    return concat.join(result)

# Some basic ones...

def h(title, level=2):
    return '<h%d>%s</h%d>' % (level, title, level)
    
def b(text):
    return '<b>%s</b>' % text

def span(text, cls=None, id=None, lang=None):
    attr = (('class', cls),
            ('lang', lang),
            ('id', id))
    return _tag('span', attr, text)

def p(*content, **kwargs):
    return _tag('p', (('class', kwargs.get('cls')),), content, concat='\n')

def div(content, cls=None, lang=None):
    return _tag('div', (('class', cls), ('lang', lang)), content, concat='\n')

def link(label, url, name=None, title=None, target=None, cls=None, hotkey=None):
    if hotkey:
        t = '(Alt-%s)' % hotkey
        title = title and title + ' ' + t or t
    if target:
        cls = (cls and cls+' ' or '') + 'external-link'
    attr = (('href', url), ('name', name), ('title', title), ('target', target),
            ('class', cls), ('accesskey', hotkey))
    return _tag('a', attr, label)

def itemize(items, indent=0, ordered=False, style=None, cls=None, lang=None):
    spaces = ' ' * indent
    tag = ordered and 'ol' or 'ul'
    attr = _attr(('style', style and 'list-style-type: %s' % style),
                 ('lang', lang))
    items = [spaces+"  <li>%s</li>" % i for i in items]
    return "\n".join([spaces+"<"+tag+attr+">"] + items + [spaces+"</"+tag+">"])

# Form controls

def label(text, id, lang=None):
    return _tag('label', (('for', id), ('lang', lang)), text)

def _input(type, name=None, value=None,
           onclick=None, onkeydown=None, onfocus=None,
           size=None, readonly=False, cls=None, id=None):
    #handler = handler and "javascript: %s" % handler
    return '<input type="%s"%s%s>' % (type, _attr(('name', name),
                                                  ('value', value),
                                                  ('size', size),
                                                  ('onclick', onclick),
                                                  ('onfocus', onfocus),
                                                  ('onkeydown', onkeydown),
                                                  ('class', cls),
                                                  ('id', id)),
                                      readonly and ' readonly' or '')

def field(text='', name='', size=20, **kwargs):
    kwargs['cls'] = kwargs.has_key('cls') and 'text '+kwargs['cls'] or 'text'
    return _input('text', name=name, value=text, size=size, **kwargs)

def radio(name, **kwargs):
    return _input('radio', name=name, **kwargs)

def hidden(name, value):
    return _input('hidden', name=name, value=value)

def button(label, handler, cls=None):
    cls = cls and 'button ' + cls or 'button'
    return _input('button', value=label, onclick=handler, cls=cls)

def reset(label, onclick=None, cls=None):
    return _input('reset', onclick=onclick, value=label, cls=cls)

def select(name, options, onchange=None, default="", id=None):
    opts = [_tag('option', (('value', value),), text)
            for text, value in options]
    if default is not None:
        opts.insert(0, _tag('option', (), default))
    attr = (('name', name), ('id', id), ('onchange', onchange))
    return _tag('select', attr, opts, concat="\n")

# Special controls

def speaking_text(text, media):
    id_ = 'text_%s' % id(media)
    a1 = button(text, "javascript: play_audio('%s');" % media.url(),
                cls='speaking-text')
    a2 = link(text, media.url(), cls='speaking-text')
    return script_write(a1, a2)

# JavaScript code generation.

def script(code, noscript=None):
    noscript = noscript and '<noscript>'+ noscript +'</noscript>' or ''
    if code:
        code = '//<!--\n'+ code +' //-->\n'
    return '<script type="text/javascript" language="Javascript">' + \
           code +'</script>'+ noscript

def script_write(content, noscript=None, condition=None):
    #return content
    if content:
        c = content.replace('"','\\"').replace('\n','\\n').replace("'","\\'")
        content = 'document.write("'+ c +'");'
        if condition:
            content = 'if ('+condition+') ' + content
    return script(content, noscript)

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
    return '{'+ ", ".join(["'%s': %s" % (k, js_value(v)) for k,v in items]) +'}'

