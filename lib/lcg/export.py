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

"""Course exporter."""

import os
import shutil

from course import *
from resources import *

class Exporter(object):

    def __init__(self, course, dir):
        """Initialize the exporter for a given 'Course'."""
        self._course = course
        self._dir = dir

    def _export_node(self, node):
        """Write the output file for given node and all subsequent nodes."""
        #print "Exporting:", node
        if not os.path.isdir(self._dir):
            os.makedirs(self._dir)
        filename = os.path.join(self._dir, node.output_file())
        file = open(filename, 'w')
        data = self._wrap_content(node, node.content().export())
        file.write(data.encode('utf-8'))
        file.close()
        for r in node.resources():
            r.export(self._dir)
        for n in node.children():
            self._export_node(n)

    def _wrap_content(self, node, content):
        return "\n".join(('<html>',
                          '  <head>',
                          '    <title>%s</title>' % node.full_title(),
                          '  </head>',
                          '  <body bgcolor="white">',
                          content,
                          '  </body>',
                          '</html>'))
            
    def export(self):
        self._export_node(self._course)


class StaticExporter(Exporter):
    """Export the content as a set of static web pages."""
    DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'

    _hotkey = {
        'next': '3',
        'prev': '1',
        'content-beginning': '0',
        'global-index': '5',
        'local-index': '4',
        }
    
    def __init__(self, course, dir, stylesheet=None):
        """Initialize the exporter for a given 'Course'."""
        super(StaticExporter, self).__init__(course, dir)
        self._stylesheet = stylesheet

    def _wrap_content(self, node, content):
        def tags(template, items):
            return '\n'.join(map(lambda x: "  " + template % x, items))
        if self._stylesheet is not None:
            node.resource(Stylesheet, self._stylesheet)
        nav = self._navigation(node)
        meta = node.root_node().meta()
        http_equiv = {'Content-Type': 'text/html; charset=UTF-8'}
        c = (self.DOCTYPE, '',
             '<html>',
             '<head>',
             '  <title>%s</title>' % node.full_title(),
             tags('<meta http-equiv="%s" content="%s">', http_equiv.items()),
             tags('<meta name="%s" content="%s">', meta.items()),
             tags('<link rel="%s" href="%s" title="%s">',
                  [(kind, n.url(), n.title())
                   for kind, n in (('prev', node.prev()), ('next', node.next()))
                   if n is not None]),
             tags('<link rel="stylesheet" type="text/css" href="%s">',
                  map(lambda s: s.url(), node.resources(Stylesheet))),
             tags('<script language="Javascript" type="text/javascript"' + \
                  ' src="%s"></script>',
                  map(lambda s: s.url(), node.resources(Script))),
             '</head>',
             '<body>',
             nav, '<hr class="navigation">',
             '<a name="content" accesskey="%s"></a>' % 
             self._hotkey['content-beginning'],
             '<h1>%s</h1>' % node.title(),
             div(content, 'content'),
             '<hr class="navigation">', nav,
             '</body></html>')
        return "\n".join(c)

    def _link(self, node, label=None, key=None):
        if node is None: return 'None' 
        label = label or node.title(abbrev=True)
        return link(label, node.url(), title=node.title(),
                    hotkey=not key or self._hotkey[key])
    
    def _navigation(self, node):
        nav = [_('Next') + ': ' + self._link(node.next(), key='next'),
               _('Previous') + ': ' + self._link(node.prev(), key='prev')]
        if node is not node.root_node():
            p = node.parent()
            if p is not node.root_node():
                nav.append(_("Up") + ': ' + self._link(p, key='local-index'))
            nav.append(self._link(node.root_node(), label=_('Course Index'),
                                  key='global-index'))
        return div(' | '.join(nav), 'navigation')
