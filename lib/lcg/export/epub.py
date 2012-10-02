# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 by BRAILCOM,o.p.s.
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

from lcg.export import *

import xml.dom.minidom as xml
import zipfile

class Constants(object):
    """Things mandated by EPUB 3 spec"""
    CONTAINER_NS = 'urn:oasis:names:tc:opendocument:xmlns:container'
    EPUB_MIMETYPE = 'application/epub+zip'
    PATHSEP = '/'
    PATHENC = 'UTF-8'
    PACKAGE_DOC_MIMETYPE = 'application/oebps-package+xml'
    METADIR = 'META-INF'
    OPF_NS = 'http://www.idpf.org/2007/opf'
    DC_NS = 'http://purl.org/dc/elements/1.1/'
    

class EpubExporter(Exporter):
    class Config(object):
        """Specifies implementation-defined EPUB parameters"""
        RESOURCEDIR = 'rsrc'
        PACKAGE_DOC_FILENAME = 'pkg.opf'
        NAV_DOC_FILENAME = 'nav.xhtml'
        UID_ID = 'uid'
        
    def __init__(self, *args, **kwargs):
        kwargs.pop('force_lang_ext', None)
        super(EpubExporter, self).__init__(*args, **kwargs)

    def dump(self, node, directory, filename=None, variant=None, **kwargs):
        variants = variant and (variant,) or node.variants() or (None,)
        for lang in variants:
            context = self.context(node, lang, **kwargs)
            lang_ = lang and '.'+lang or ''
            epub = zipfile.ZipFile(filename + lang_, 'w', zipfile.ZIP_DEFLATED)
            try:
                mimeinfo = zipfile.ZipInfo('mimetype')
                mimeinfo.compress_type = zipfile.ZIP_STORED
                epub.writestr(mimeinfo, Constants.EPUB_MIMETYPE)
                epub.writestr(self._meta_path('container.xml'), self._ocf_container(node, lang))
                epub.writestr(self._publication_resource_path(self.Config.NAV_DOC_FILENAME), self._navigation_document(context))
                for n in node.linear():
                    epub.writestr(self._node_path(n), self._xhtml_content_document(n, lang))
                epub.writestr(self._publication_resource_path(self.Config.PACKAGE_DOC_FILENAME), self._package_document(node, lang))
                for resource in node.resource_provider().resources():
                    epub.writestr(self._resource_path(resource), resource.get())
            except:
                epub.close()
                raise

    def _container_path(self, *components):
        #TODO replace forbidden characters as per spec
        def ensure_pathenc(component):
            if isinstance(component, unicode):
                return component.encode(Constants.PATHENC)
            return component
        components = map(ensure_pathenc, components)
        path = Constants.PATHSEP.join(components)
        return path

    def _meta_path(self, *components):
        return self._container_path(Constants.METADIR, *components)

    def _publication_resource_path(self, *components):
        return self._container_path(self.Config.RESOURCEDIR, *components)

    def _resource_path(self, resource):
        components = [resource.filename()]
        if resource.SUBDIR:
            components.insert(0, resource.SUBDIR)
        return self._publication_resource_path(*components)

    def _node_path(self, node):
        filename = node.id()
        filename += '.xhtml'
        return self._publication_resource_path(filename)

    def _ocf_container(self, node, lang):
        doc = xml.Document()
        container = doc.appendChild(doc.createElement('container'))
        container.setAttribute('xmlns', Constants.CONTAINER_NS)
        container.setAttribute('version', '1.0')
        rootfiles = container.appendChild(doc.createElement('rootfiles'))
        rootfile = rootfiles.appendChild(doc.createElement('rootfile'))
        packagedoc_path = self._publication_resource_path(self.Config.PACKAGE_DOC_FILENAME)
        rootfile.setAttribute('full-path', packagedoc_path)
        rootfile.setAttribute('media-type', Constants.PACKAGE_DOC_MIMETYPE)
        return doc.toprettyxml(indent=4*'', newl='', encoding='UTF-8')

    def _package_document(self, node, lang):
        doc = xml.Document()
        package = doc.appendChild(doc.createElement('package'))
        package.setAttribute('xmlns', Constants.OPF_NS)
        package.setAttribute('version', '3.0')
        package.setAttribute('unique-identifier', self.Config.UID_ID)
        package.setAttribute('xml:lang', lang)
        # metadata
        metadata = package.appendChild(doc.createElement('metadata'))
        metadata.setAttribute('xmlns:dc', Constants.DC_NS)
        dc_identifier = metadata.appendChild(doc.createElement('dc:identifier'))
        dc_identifier.setAttribute('id', self.Config.UID_ID)
        dc_identifier.appendChild(doc.createTextNode(self._document_unique_identifier(node, lang)))
        metadata.appendChild(doc.createElement('dc:title')).appendChild(doc.createTextNode(node.title()))
        metadata.appendChild(doc.createElement('dc:language')).appendChild(doc.createTextNode(lang))
        curtime = 'TODO'
        meta_modified = metadata.appendChild(doc.createElement('meta'))
        meta_modified.appendChild(doc.createTextNode(curtime))
        meta_modified.setAttribute('property', 'dcterms:modified')
        # manifest and spine
        manifest = package.appendChild(doc.createElement('manifest'))
        spine = package.appendChild(doc.createElement('spine'))
        def add_itemref(idref):
            spine.appendChild(doc.createElement('itemref')).setAttribute('idref', idref)
        def add_item(id, href, mediatype, properties=()):
            item = manifest.appendChild(doc.createElement('item'))
            item.setAttribute('id', id)
            item.setAttribute('href', href)
            item.setAttribute('media-type', mediatype)
            properties = ' '.join(properties)
            if properties:
                item.setAttribute('properties', properties)
        add_item('nav', self.Config.NAV_DOC_FILENAME, 'application/xhtml+xml', properties=('nav',))
        for n in node.linear():
            href = '/'.join(self._node_path(n).split('/')[1:]) #TODO hack to make path relative
            add_item(n.id(), href, mediatype='application/xhtml+xml')
            add_itemref(n.id())
        for resource in node.resource_provider().resources():
            add_item('TODO', resource.filename(), mediatype=self._guess_media_type(resource))
        # export
        return doc.toprettyxml(indent=4*'', newl='', encoding='UTF-8')

    def _guess_media_type(self, resource):
        #TODO
        return 'image/jpeg'

    def _uri_node(self, context, node, lang=None):
        return node.id() + '.xhtml'

    def _navigation_document(self, context):
        node = context.node()
        lang = context.lang()
        doc = xml.Document()
        html = doc.appendChild(doc.createElement('html'))
        html.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml')
        html.setAttribute('xmlns:epub', 'http://www.idpf.org/2007/ops')
        html.setAttribute('xml:lang', lang)
        head = html.appendChild(doc.createElement('head'))
        head.appendChild(doc.createElement('meta')).setAttribute('charset', 'UTF-8')
        body = html.appendChild(doc.createElement('body'))
        nav = body.appendChild(doc.createElement('nav'))
        nav.setAttribute('epub:type', 'toc')
        def export(items, root):
            ol = root.appendChild(doc.createElement('ol'))
            for item, subitems in items:
                title = item.title()
                descr = item.descr() #TODO unused
                uri = context.uri(item) #TODO fix relativeness, add #fragments for Sections
                li = ol.appendChild(doc.createElement('li'))
                a = li.appendChild(doc.createElement('a'))
                a.setAttribute('href', uri)
                a.appendChild(doc.createTextNode(title))
                if subitems:
                    export(subitems, li)
        items = NodeIndex(node=node, detailed=True).items(context)
        export(items, nav)
        return doc.toprettyxml(indent='', newl='', encoding='UTF-8')

    def _xhtml_content_document(self, node, lang):
        exporter = Html5Exporter()
        context = exporter.context(node, lang)
        data = context.localize(exporter.export(context))
        return data.encode('UTF-8')

    def _document_unique_identifier(self, node, lang):
        #TODO
        return 'urn:uuid:%s' % ('073a5060-6629-11e1-b86c-0800200c9a66',)
