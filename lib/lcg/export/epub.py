# -*- coding: utf-8 -*-
#
# Copyright (C) 2012, 2013 by BRAILCOM,o.p.s.
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

import lcg
from lcg.export import Exporter, Html5Exporter

import xml.dom.minidom as xml
import zipfile
import cStringIO as StringIO
import datetime
import mimetypes

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
    

class EpubHtml5Exporter(Html5Exporter):
    
    class Generator(Html5Exporter.Generator):
        # We need to be able to find out, whether a script was used
        # within a particular node export.  Thus we use this variable,
        # which is reset before each node export and checked after it.
        scripted = False

        def script(self, *args, **kwargs):
            self.scripted = True
            return super(EpubHtml5Exporter.Generator, self).script(*args, **kwargs)
                
    def _head(self, context):
        g = context.generator()
        return ([g.title(self._title(context))] + 
                [g.script(src=context.uri(s)) for s in self._scripts(context)])


    def _export_table_of_contents(self, context, element):
        return ''
        
    def _export_inline_image(self, context, element):
        g = self._generator
        image = element.image(context)
        title = element.title()
        descr = element.descr()
        size = element.size()
        uri = context.uri(image)
        if size is None:
            thumbnail = image.thumbnail()
            if thumbnail:
                size = thumbnail.size()
            else:
                size = image.size()
        if title is None:
            title = image.title()
        if descr is None:
            descr = image.descr()
        if size is not None:
            width, height = size
        else:
            width, height = None, None
        if descr:
            if title:
                alt = self.concat(title, ': ', descr)
            else:
                alt = descr
        else:
            alt = title
        cls = ['lcg-image']
        if element.align():
            cls.append(element.align() + '-aligned')
        if element.name():
            cls.append('image-'+element.name())
        return g.img(uri, alt=alt, align=element.align(), cls=' '.join(cls),
                     width=width, height=height)

    def _uri_node(self, context, node, lang=None):
        return node.id() + '.xhtml'

    def _uri_resource(self, context, resource):
        return self.resource_uri(resource)

    def _uri_section(self, context, section, local=False):
        result = "#section-" + section.anchor()
        if not local:
            result = self._uri_node(context, section.parent()) + result
        return result

    def _allow_flash_audio_player(self, context, audio):
        return False
        
    def _media_player(self, context):
        return None

    def resource_uri(self, resource):
        uri = resource.filename()
        if resource.SUBDIR:
            uri = resource.SUBDIR + '/' + uri
        return uri


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
        self._html_exporter = EpubHtml5Exporter(translations=self._translation_path)

    def dump(self, node, directory, filename=None, variant=None, **kwargs):
        variants = variant and (variant,) or node.variants() or (None,)
        for lang in variants:
            context = self.context(node, lang, **kwargs)
            ext = lang and '.'+lang or ''
            f = open(filename+ext, 'w')
            f.write(self.export(context))

    def export(self, context):
        """Return the exported E-pub archive as a binary string."""
        lcg.config.allow_backref = False
        fileobject = StringIO.StringIO()
        epub = zipfile.ZipFile(fileobject, 'w', zipfile.ZIP_DEFLATED)
        node = context.node()
        lang = context.lang()
        resources = []
        scripted_nodes = []
        try:
            mimeinfo = zipfile.ZipInfo('mimetype')
            mimeinfo.compress_type = zipfile.ZIP_STORED
            epub.writestr(mimeinfo, Constants.EPUB_MIMETYPE)
            epub.writestr(self._meta_path('container.xml'), 
                          self._ocf_container(node, lang))
            epub.writestr(self._publication_resource_path(self.Config.NAV_DOC_FILENAME), 
                          self._navigation_document(context))
            for n in node.linear():
                exported_content, scripted = self._xhtml_content_document(n, lang)
                epub.writestr(self._node_path(n), exported_content)
                if scripted:
                    scripted_nodes.append(n)
                for resource in n.resources():
                    if resource not in resources:
                        epub.writestr(self._resource_path(resource),
                                      self._get_resource_data(context, n, resource))
                        resources.append(resource)
            cover_image = node.cover_image()
            if cover_image and cover_image not in resources:
                resources.append(cover_image)
            epub.writestr(self._publication_resource_path(self.Config.PACKAGE_DOC_FILENAME),
                          self._package_document(node, lang, resources, scripted_nodes))
        finally:
            epub.close()
        return fileobject.getvalue()

    def _get_resource_data(self, context, node, resource):
        """Return the resource file data as a (binary) string.

        The base class implementation only handles resources with src_file.
        Retrieving the file data for other resources is usually application
        specific.  Thus this method may be implemented to support such
        application specific resource retrieval.
        
        """
        return resource.get()
    
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
        return self._publication_resource_path(self._html_exporter.resource_uri(resource))

    def _node_path(self, node):
        return self._publication_resource_path(node.id() + '.xhtml')

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

    def _package_document(self, node, lang, resources, scripted_nodes):
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
        curtime = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        meta_modified = metadata.appendChild(doc.createElement('meta'))
        meta_modified.appendChild(doc.createTextNode(curtime))
        meta_modified.setAttribute('property', 'dcterms:modified')
        # manifest and spine
        manifest = package.appendChild(doc.createElement('manifest'))
        spine = package.appendChild(doc.createElement('spine'))
        def add_item(item_id, href, mediatype, properties=()):
            item = manifest.appendChild(doc.createElement('item'))
            item.setAttribute('id', item_id)
            item.setAttribute('href', href)
            item.setAttribute('media-type', mediatype)
            properties = ' '.join(properties)
            if properties:
                item.setAttribute('properties', properties)
        add_item('nav', self.Config.NAV_DOC_FILENAME, 'application/xhtml+xml', properties=('nav',))
        for n in node.linear():
            item_id = 'node-'+n.id() # Prefix to avoid ids beginning with a number (invalid HTML)
            href = '/'.join(self._node_path(n).split('/')[1:]) #TODO hack to make path relative
            properties = []
            if n in scripted_nodes:
                properties.append('scripted')
            add_item(item_id, href, mediatype='application/xhtml+xml', properties=properties)
            spine.appendChild(doc.createElement('itemref')).setAttribute('idref', item_id)
        for resource in resources:
            resource_id = 'resource-%x' % id(resource)
            mime_type, encoding = mimetypes.guess_type(resource.filename())
            properties = []
            if resource is node.cover_image():
                properties.append('cover-image')
            add_item(resource_id, self._html_exporter.resource_uri(resource),
                     mediatype=mime_type or 'application/octet-stream', properties=properties)
        # export
        return doc.toprettyxml(indent=4*'', newl='', encoding='UTF-8')

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
        items = lcg.NodeIndex(node=node, detailed=True).items(context)
        export(items, nav)
        return doc.toprettyxml(indent='  ', newl='\n', encoding='UTF-8')

    def _xhtml_content_document(self, node, lang):
        exporter = self._html_exporter
        context = exporter.context(node, lang)
        context.generator().scripted = False
        data = context.localize(exporter.export(context))
        scripted = context.generator().scripted
        return (data.encode('UTF-8'), scripted)

    def _document_unique_identifier(self, node, lang):
        #TODO
        return 'urn:uuid:%s' % ('073a5060-6629-11e1-b86c-0800200c9a66',)

    def uri(self, context, target, **kwargs):
        return self._html_exporter.uri(context, target, **kwargs)
