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

def _attr(*pairs):
    return "".join([v is not None and ' %s="%s"' % (a, v) or ''
                    for a, v in pairs])

def div(content, cls):
    if operator.isSequenceType(content) \
           and not isinstance(content, types.StringTypes):
        content = '\n'.join(content)
    return '\n'.join(('<div class="%s">' % cls, content, '</div>\n'))

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

def radio(name, handler, value=None, cls=None):
    return _input('radio', name=name, handler=handler, value=value, cls=cls)

def link(label, url, brackets=False,
         title=None, target=None, cls=None, hotkey=None):
    if hotkey:
        t = '(Alt-%s)' % hotkey
        title = title and title + ' ' + t or t
    attr = _attr(('title', title),
                 ('target', target),
                 ('class', cls),
                 ('accesskey', hotkey))
    result = '<a href="%s"%s>%s</a>' % (url, attr, label)
    return brackets and '['+result+']' or result

def speaking_text(text, media):
    a1 = link(text, "javascript: play_audio('%s')" % media.url())
    a2 = link(text, media.url())
    return script_write(a1, a2)

def script(code, noscript=None):
    noscript = noscript and '<noscript>'+ noscript +'</noscript>' or ''
    return '<script type="text/javascript" language="Javascript"><!--\n' + \
           code +' //--></script>' + noscript

def script_write(content, noscript=None):
    c = content.replace('"','\\"').replace('\n','\\n').replace("'","\\'")
    return script('document.write("'+ c +'");', noscript)

def ul(items, indent=0):
    spaces = ' ' * indent
    items = [spaces+"  <li>%s</li>" % i for i in items]
    return "\n".join([spaces+"<ul>"] + items + [spaces+"</ul>"])

def h(title, level=2):
    return '<h%d>%s</h%d>' % (level, title, level)
    
def b(text):
    return '<b>%s</b>' % text
