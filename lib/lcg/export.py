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

"""Course exporter."""

import os

from lcg import *
import _html

    
class Exporter(object):
    DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'

    def __init__(self, stylesheet=None, inlinestyles=False):
        """Initialize the exporter for a given 'ContentNode' instance."""
        self._stylesheet = stylesheet
        self._inlinestyles = inlinestyles

    def _styles(self, node):
        if self._inlinestyles:
            return ['<style type="text/css">\n%s</style>' % s.get()
                    for s in node.resources(Stylesheet)]
        else:
            return ['<link rel="stylesheet" type="text/css" href="%s">' % \
                    s.url() for s in node.resources(Stylesheet)]
            
    def head(self, node):
        if self._stylesheet is not None:
            node.resource(Stylesheet, self._stylesheet)
        tags = ['<title>%s</title>' % node.title()] + \
               ['<meta http-equiv="%s" content="%s">' % pair
                for pair in (('Content-Type', 'text/html; charset=UTF-8'),
                             ('Content-Language', node.language()))] + \
               ['<meta name="%s" content="%s">' % item
                for item in node.root().meta().items()] + \
               ['<script language="Javascript" type="text/javascript"' + \
                ' src="%s"></script>' % s.url()
                for s in node.resources(Script)]
        return '  '+'\n  '.join(tags + self._styles(node))

    def _body_parts(self, node):
        return ('<h1>%s</h1>' % node.title(),
                _html.div(node.content().export(), 'content'))
    
    def body(self, node):
        return "\n".join(self._body_parts(node))

    def page(self, node):
        lines = (self.DOCTYPE, '',
                 '<html>',
                 '<head>',
                 self.head(node),
                 '</head>',
                 '<body>',
                 self.body(node),
                 '</body>',
                 '</html>')
        return "\n".join(lines)

    
    def export(self, node, directory):
        """Export the node and its children recursively."""
        if not os.path.isdir(directory):
            os.makedirs(directory)
        filename = os.path.join(directory, node.output_file())
        file = open(filename, 'w')
        file.write(self.page(node).encode('utf-8'))
        file.close()
        for r in node.resources():
            r.export(directory)
        for n in node.children():
            self.export(n, directory)

        
class StaticExporter(Exporter):
    """Export the content as a set of static web pages."""

    _hotkey = {
        'prev': '1',
        'next': '3',
        'up': '2',
        'index': '4',
        }

    _INDEX_LABEL = None
    
    def head(self, node):
        tags = ['<link rel="%s" href="%s" title="%s">' % \
                (kind, n.url(), n.title())
                for kind, n in (('start', node.root()), 
                                ('prev', node.prev()),
                                ('next', node.next()))
                if n is not None and n is not node]
        return '\n  '.join([super(StaticExporter, self).head(node)] + tags)
             
    def _body_parts(self, node):
        return super(StaticExporter, self)._body_parts(node) + \
               ('<hr class="navigation">', self._navigation(node))

    def _link(self, node, label=None, key=None):
        if node is None: return _("None")
        if label is None: label = node.title(abbrev=True)
        return _html.link(label, node.url(), title=node.title(),
                          hotkey=not key or self._hotkey[key])
    
    def _navigation(self, node):
        nav = [_('Next') + ': ' + self._link(node.next(), key='next'),
               _('Previous') + ': ' + self._link(node.prev(), key='prev')]
        hidden = ''
        if node is not node.root():
            p = node.parent()
            if p is not node.root():
                nav.append(_("Up") + ': ' + self._link(p, key='up'))
            else:
                hidden = "\n"+self._link(p, key='up', label='')
            nav.append(self._link(node.root(), label=self._INDEX_LABEL,
                                  key='index'))
        return _html.div(' |\n'.join(nav) + hidden, 'navigation')
