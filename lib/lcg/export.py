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
        for m in node.list_media():
            self._export_media(m)
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
            
    def _export_media(self, media):
        src_path = media.source_file()
        dst_path = media.destination_file(self._dir)
        if not os.path.exists(dst_path) or \
               os.path.exists(src_path) and \
               os.path.getmtime(dst_path) < os.path.getmtime(src_path):
            if not os.path.isdir(os.path.dirname(dst_path)):
                os.makedirs(os.path.dirname(dst_path))
            # Either create the file with tts or copy from source directory.
            if media.tts_input() is not None and not os.path.exists(src_path):
                print "%s: file does not exist!" % dst_path
                cmd = None
                try:
                    cmd = os.environ['LCG_TTS_COMMAND']
                except KeyError:
                    pass
                if cmd:
                    cmd = cmd % {'text': media.tts_input(), 'file': dst_path}
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
    
    def _wrap_content(self, node):
        nav = self._navigation(node)
        
        return "\n".join((self.DOCTYPE, '',
                          '<html>',
                          '<head>',
                          '  <title>%s</title>' % node.full_title(),
                          self._meta(node),
                          '</head>',
                          '<body bgcolor="white">',
                          nav, '<hr>',
                          '<h1>%s</h1>' % node.title(),
                          node.content().export(),
                          self._toc(node),
                          '<hr>', nav,
                          '</body></html>'))

    def _meta(self, node):
        meta = node.root_node().meta()
        return '\n'.join(map(lambda k:
                             '  <meta name="%s" content="%s">' % (k, meta[k]),
                             meta.keys()))

    def _link(self, node, label=None, title=''):
        if node is None: return 'None' 
        label = label or node.title()
        return '<a href="%s" title="%s">%s</a>' % \
               (node.output_file(), title, label)
    
    def _navigation(self, node):
        nav = ['Next: ' + self._link(node.next()),
               'Previous: ' + self._link(node.prev())]
        if node is not node.root_node():
            p = node.parent()
            if p is not node.root_node():
                nav.append(p.__class__.__name__ + ' Index: ' + self._link(p))
            nav.append(self._link(node.root_node(), label='Course Index'))
        return ' | '.join(nav)

    def _toc(self, node):
        if isinstance(node, (RootNode, InnerNode)):
            return "<h2>Table of Contents</h2>\n" + self._make_toc(node)
        else:
            return ''
    
    def _make_toc(self, node, indent='', deep=False):
        if len(node.children()) == 0:
            return ''
        return "\n" + indent + "<ul>\n" + \
               "\n".join(map(lambda n: '%s  <li><a href="%s">%s</a>%s</li>' % \
                             (indent, n.output_file(), n.title(),
                              deep and self._make_toc(n, indent+'    ') or ''),
                             node.children())) + \
                             "\n" + indent + "</ul>\n" + indent[0:-2] 
    
