# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004 Brailcom, o.p.s.
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
        file.write(self._wrap_content(node))
        file.close()
        for m in node.resources():
            self._export_resource(m)
        for n in node.children():
            self._export_node(n)

    def _wrap_content(self, node):
        return "\n".join(('<html>',
                          '  <head>',
                          '    <title>%s</title>' % node.full_title(),
                          '  </head>',
                          '  <body bgcolor="white">',
                          node.content().export(),
                          '  </body>',
                          '</html>'))
            
    def _export_resource(self, r):
        src_path = r.source_file()
        dst_path = r.destination_file(self._dir)
        if not os.path.exists(dst_path) or \
               os.path.exists(src_path) and \
               os.path.getmtime(dst_path) < os.path.getmtime(src_path):
            if not os.path.isdir(os.path.dirname(dst_path)):
                os.makedirs(os.path.dirname(dst_path))
            # Either create the file with tts or copy from source directory.
            if isinstance(r, Media) and r.tts_input() is not None \
                   and not os.path.exists(src_path):
                print "%s: file does not exist!" % dst_path
                cmd = None
                try:
                    cmd = os.environ['LCG_TTS_COMMAND']
                except KeyError:
                    pass
                if cmd:
                    cmd = cmd % {'text': r.tts_input(), 'file': dst_path}
                    print "  - generating with TTS: %s" % cmd
                    os.system(cmd)
            else:
                shutil.copy(src_path, dst_path)
                print "%s: file copied." % dst_path
            
    def export(self):
        self._export_node(self._course)


class StaticExporter(Exporter):
    """Export the content as a set of static web pages."""
    DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'

    _hotkey = {
        'next': 'n',
        'prev': 'p',
        'content-beginning': 'b',
        'global-index': 'h',
        'local-index': 'i',
        }
    
    def __init__(self, course, dir, stylesheet=None):
        """Initialize the exporter for a given 'Course'."""
        super(StaticExporter, self).__init__(course, dir)
        self._stylesheet = stylesheet

    def _wrap_content(self, node):
        def tags(template, items):
            return '\n'.join(map(lambda x: "  " + template % x, items))
        node.stylesheet(self._stylesheet)
        nav = self._navigation(node)
        meta = node.root_node().meta()
        c = (self.DOCTYPE, '',
             '<html>',
             '<head>',
             '  <title>%s</title>' % node.full_title(),
             tags('<meta name="%s" content="%s">', meta.items()),
             tags('<link rel="%s" href="%s" title="%s">',
                  map(lambda a: (a[0], a[1].output_file(), a[1].title()),
                      filter(lambda a: a[1] is not None,
                             (('prev', node.prev()), ('next', node.next()))))),
             tags('<link rel="stylesheet" type="text/css" href="%s">',
                  map(lambda s: s.url(), node.resources(Stylesheet))),
             tags('<script language="Javascript" type="text/javacript"' + \
                  ' src="%s">', map(lambda s: s.url(), node.resources(Script))),
             '</head>',
             '<body>',
             nav, '<hr class="navigation">',
             '<a name="content" accesskey="%s"></a>' % 
             self._hotkey['content-beginning'],
             '<h1>%s</h1>' % node.title(),
             self._div('content', node.content().export()),
             self._toc(node),
             '<hr class="navigation">', nav,
             '</body></html>')
        return "\n".join(c)

    def _div(self, cls, *contents):
        return '\n'.join(('<div class="%s">' % cls,) + contents + ('</div>\n',))

    def _link(self, node, label=None, title='', key=None):
        if node is None: return 'None' 
        label = label or node.title()
        hotkey = not key or self._hotkey[key]
        return '<a href="%s" title="%s" accesskey="%s">%s</a>' % \
               (node.output_file(), title, hotkey, label)
    
    def _navigation(self, node):
        nav = ['Next: ' + self._link(node.next(), key='next'),
               'Previous: ' + self._link(node.prev(), key='prev')]
        if node is not node.root_node():
            p = node.parent()
            if p is not node.root_node():
                nav.append(p.__class__.__name__ + ' Index: ' + \
                           self._link(p, key='local-index'))
            nav.append(self._link(node.root_node(), label='Course Index',
                                  key='global-index'))
        return self._div('navigation', ' | '.join(nav))

    def _toc(self, node):
        if not isinstance(node, (RootNode, InnerNode)): return ''
        return self._div("table-of-contents",
                         '<h2>Table of Contents</h2>',
                         self._make_toc(node))
    
    def _make_toc(self, node, indent='', deep=False):
        if len(node.children()) == 0:
            return ''
        return "\n" + indent + "<ul>\n" + \
               "\n".join(map(lambda n: '%s  <li><a href="%s">%s</a>%s</li>' % \
                             (indent, n.output_file(), n.title(),
                              deep and self._make_toc(n, indent+'    ') or ''),
                             node.children())) + \
                             "\n" + indent + "</ul>\n" + indent[0:-2] 
    
            
