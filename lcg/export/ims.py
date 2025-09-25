# -*- coding: utf-8 -*-

# Copyright (C) 2004-2015, 2017 OUI Technology Ltd.
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

"""Exporter class which generates an IMS compliant package."""

from __future__ import unicode_literals

import lcg
import xml.dom.domreg
import os
import codecs


class _Manifest(object):
    """IMS manifest is a collection of information about all files in a package.

    It defines the structure and dependencies of the content.

    """

    def __init__(self, context):
        """Initialize the manifest for given root node export context."""
        self._context = context
        uri = "http://www.imsglobal.org/xsd/imscp_v1p1"
        minidom = xml.dom.domreg.getDOMImplementation('minidom')
        self._document = document = minidom.createDocument(uri, 'manifest', '')
        self._manifest = manifest = document.firstChild
        # Namespace
        self._set_xml_attr(manifest, 'xmlns', 'http://www.imsglobal.org/xsd/imscp_v1p1')
        # Metadata
        metadata = self._append_xml_element(manifest, 'metadata')
        self._append_xml_text(metadata, 'schema', 'IMS Content')
        self._append_xml_text(metadata, 'schemaversion', '1.1.3')
        # Organisations
        organisations = self._append_xml_element(manifest, 'organizations')
        self._set_xml_attr(organisations, 'default', 'TOC1')
        o = self._append_xml_element(organisations, 'organization')
        self._set_xml_attr(o, 'identifier', 'TOC1')
        self._set_xml_attr(o, 'structure', 'hierachical')
        # Title
        self._append_xml_text(o, 'title', context.node().title())
        # Resources
        resources = self._append_xml_element(manifest, 'resources')
        # Hierarchy
        for node in context.node().children():
            self._create_item(o, resources, node)

    def _create_item(self, o, resources, node):
        item = self._append_xml_element(o, 'item')
        context = self._context
        self._set_xml_attr(item, 'identifier', 'toc-' + node.id())
        self._set_xml_attr(item, 'identifierref', node.id())
        self._append_xml_text(item, 'title', node.title())

        resource = self._append_xml_element(resources, 'resource')
        self._set_xml_attr(resource, 'identifier', node.id())
        self._set_xml_attr(resource, 'type', 'webcontent')
        self._set_xml_attr(resource, 'href', context.uri(node))

        files = sorted([context.uri(r) for r in node.resources()])
        for filename in (context.uri(node),) + tuple(files):
            file = self._append_xml_element(resource, 'file')
            self._set_xml_attr(file, 'href', filename)

        for node in node.children():
            self._create_item(item, resources, node)

    # XML helper methods.

    def _set_xml_attr(self, node, key, value):
        attr = self._document.createAttribute(key)
        node.setAttributeNode(attr)
        node.setAttribute(key, value)
        return attr

    def _append_xml_element(self, parent, key):
        node = self._document.createElement(key)
        parent.appendChild(node)
        return node

    def _append_xml_text(self, parent, key, text):
        node = self._append_xml_element(parent, key)
        node.appendChild(self._document.createTextNode(text))
        return node

    # Public methods

    def xml(self):
        """Return the IMS Manifest into a file."""
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + self._manifest.toxml()


class IMSExporter(lcg.StyledHtmlExporter, lcg.HtmlFileExporter):
    """Export the content as an IMS package."""

    _PAGE_STRUCTURE = (
        lcg.HtmlExporter.Part('content'),
    )

    def manifest(self, node):
        return _Manifest(self.context(node, None))

    def dump(self, node, directory, **kwargs):
        super(IMSExporter, self).dump(node, directory, **kwargs)
        if node == node.root():
            manifest = self.manifest(node).xml()
            with file(os.path.join(directory, 'imsmanifest.xml'), 'w') as f:
                f.write(manifest.encode('utf-8'))
