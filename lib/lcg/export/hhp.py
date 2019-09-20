# -*- coding: utf-8 -*-

# Copyright (C) 2006-2015 OUI Technology Ltd.
# Copyright (C) 2019 Tomáš Cerha <t.cerha@gmail.com>
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

from __future__ import unicode_literals

import lcg
import os


class _MetaFile(object):
    _EXT = None

    def __init__(self, context, charset='utf-8'):
        self._context = context
        self._charset = charset

    def _lines(self):
        return ()

    def filename(self):
        return self._context.node().id() + self._EXT

    def write(self, directory):
        file = open(os.path.join(directory, self.filename()), 'w')
        file.write("\n".join(self._lines()).encode(self._charset))
        file.close()


class _Contents(_MetaFile):
    _EXT = '.hhc'

    def _item(self, node, indent=''):
        uri = self._context.exporter().uri(self._context, node)
        lines = ('<li>',
                 '  <object type="text/sitemap">',
                 '    <param name="Name" value="%s">' % node.title(),
                 '    <param name="Local" value="%s">' % uri,
                 '  </object>')
        return tuple([indent + '  ' + line for line in lines])

    def _lines(self, node=None, indent=''):
        node = node or self._context.node()
        lines = ()
        children = node.children()
        if children:
            lines += (indent + "<ul>",)
            for n in children:
                lines += self._item(n, indent=indent)
                lines += self._lines(node=n, indent=indent + '    ')
            lines += (indent + "</ul>",)
        return lines


class _Index(_Contents):
    _EXT = '.hhk'

    def _lines(self):
        lines = ("<ul>",)
        for n in self._context.node().linear():
            lines += self._item(n)
        lines += ("</ul>", )
        return lines


class _Header(_MetaFile):
    _EXT = '.hhp'

    def __init__(self, context, contents, index, **kwargs):
        super(_Header, self).__init__(context, **kwargs)
        self._contents = contents
        self._index = index

    def _lines(self):
        return ("Contents file=%s" % self._contents.filename(),
                "Index file=%s" % self._index.filename(),
                "Title=%s" % self._context.node().title(),
                "Default topic=%s" % self._context.exporter().uri(self._context,
                                                                  self._context.node()),
                "Charset=%s" % self._charset)


class HhpExporter(lcg.HtmlFileExporter):

    _ALLOW_BACKREF = False

    class Generator(lcg.HtmlGenerator):

        def hr(self, **kwargs):
            return '<hr>'  # We don't want XHTML tag syntax (<hr/>).

        def table(self, content, cls=None, **kwargs):
            if cls == 'lcg-table':
                kwargs = dict(kwargs, cellspacing=3, cellpadding=0)
            return super(HhpExporter.Generator, self).table(content, cls=cls, **kwargs)

        def div(self, content, cls=None, **kwargs):
            if cls == 'table-of-contents':
                content = '<br>' + content
            return super(HhpExporter.Generator, self).div(content, cls=cls, **kwargs)

    def dump(self, node, directory, **kwargs):
        super(HhpExporter, self).dump(node, directory, **kwargs)
        if node == node.root():
            context = self.context(node, None)
            contents = _Contents(context)
            index = _Index(context)
            header = _Header(context, contents, index)
            for metafile in (header, contents, index):
                metafile.write(directory)
