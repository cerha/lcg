# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2006 Brailcom, o.p.s.
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

"""Exporter class which generates HTML Help Workshop compatible output.

This format is used by MS Windows help system, but also by wx Widgets help
browser (see http://www/wxwidgets.org for more information about wx Widgets).

"""

import os
import lcg

class _MetaFile(object):
    _EXT = None
    
    def __init__(self, root, charset='utf-8'):
        self._root = root
        self._charset = charset

    def _lines(self):
        return ()

    def filename(self):
        return self._root.id() + self._EXT
    
    def write(self, directory):
        file = open(os.path.join(directory, self.filename()), 'w')
        file.write("\n".join(self._lines()).encode(self._charset))
        file.close()

        
class _Contents(_MetaFile):
    _EXT = '.hhc'
    
    def _item(self, node, indent=''):
        lines = ('<li>',
                 '  <object type="text/sitemap">',
                 '    <param name="Name" value="%s">' % node.title(),
                 '    <param name="Local" value="%s">' % node.url(),
                 '  </object>')
        return tuple([indent+'  '+line for line in lines])
    
    def _lines(self, node=None, indent=''):
        node = node or self._root
        lines = ()
        children = node.children()
        if children:
            lines += (indent + "<ul>",)
            for n in children:
                lines += self._item(n, indent=indent)
                lines += self._lines(node=n, indent=indent+'    ')
            lines += (indent + "</ul>",)
        return lines

    
class _Index(_Contents):
    _EXT = '.hhk'

    def _lines(self):
        lines = ("<ul>",)
        for n in self._root.linear():
            lines += self._item(n)
        lines += ("</ul>", )
        return lines


class _Header(_MetaFile):
    _EXT = '.hhp'

    def __init__(self, root, contents, index, **kwargs):
        super(_Header, self).__init__(root, **kwargs)
        self._contents = contents
        self._index = index
            
    def _lines(self):
        return ("Contents file=%s" % self._contents.filename(),
                "Index file=%s" % self._index.filename(),
                "Title=%s" % self._root.title(),
                "Default topic=%s" % self._root.url(),
                "Charset=%s" % self._charset)

        
class HhpExporter(lcg.Exporter):
    
    def __init__(self, *args, **kwargs):
        super(HhpExporter, self).__init__(*args, **kwargs)
        # We just want to make the following NASTY HACKS here, to influence the
        # export of some Conent elements.
        # We want to make a linebreak before any Table of Contents.
        x = lcg.TableOfContents._export_title
        lcg.TableOfContents._export_title = lambda self_: '<br>' + x(self_)
        # We want to prevent beckreferencing in section titles. 
        lcg.Section.backref = lambda s, n: None
        # We also want Tables with old HTML attributes.
        lcg.Table._ATTR = 'cellspacing="3" cellpadding="0"'
        # We don't want XHTML tag syntax (<hr/>).
        lcg.HorizontalSeparator.export = lambda self_: '<hr>'
        # We want old HTML 'visial' tags.
        lcg.wiki.Formatter._FORMAT['underline'] = ('<u>', '</u>')
        

    def export(self, node, directory):
        super(HhpExporter, self).export(node, directory)
        if node == node.root():
            contents = _Contents(node)
            index = _Index(node)
            header = _Header(node, contents, index)
            for metafile in (header, contents, index):
                metafile.write(directory)

