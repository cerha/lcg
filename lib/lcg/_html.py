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


def field(text='', name='', size=20, cls=None, readonly=False):
    f = '<input type="text" name="%s" class="%s" value="%s" size="%d"%s>'
    return f % (name, cls and 'text ' + cls or 'text', text, size,
                readonly and ' readonly' or '')

def button(label, handler, cls=None):
    cls = cls and 'button ' + cls or 'button'
    return '<input type="button" value="%s"' % label + \
           ' onClick="javascript: %s"' % handler + \
           (cls and ' class="%s">' % cls or '>')

def link(label, url, target=None, cls=None, brackets=False):
    result = '<a href="%s"%s%s>%s</a>' % \
             (url, target and ' target="%s"' % target or '',
              cls and ' class="%s"' % cls or '', label)
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

