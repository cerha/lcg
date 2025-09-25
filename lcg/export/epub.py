# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2016 by OUI Technology Ltd.
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

from __future__ import unicode_literals
from future import standard_library
from builtins import map

import lcg

import xml.dom.minidom as xml
import zipfile
import io
import datetime
import mimetypes
import re
import unicodedata
import os
import sys

standard_library.install_aliases()
unistr = type(u'')  # Python 2/3 transition hack.


class Constants(object):
    """Things mandated by EPUB 3 spec"""
    CONTAINER_NS = 'urn:oasis:names:tc:opendocument:xmlns:container'
    EPUB_MIMETYPE = b'application/epub+zip'
    PATHSEP = '/'
    PATHENC = 'UTF-8'
    PACKAGE_DOC_MIMETYPE = 'application/oebps-package+xml'
    METADIR = 'META-INF'
    OPF_NS = 'http://www.idpf.org/2007/opf'
    DC_NS = 'http://purl.org/dc/elements/1.1/'


class EpubHtml5Exporter(lcg.Html5Exporter):

    _ALLOW_BACKREF = False

    class Generator(lcg.Html5Exporter.Generator):

        def script(self, *args, **kwargs):
            # We need to be able to find out, whether a script was used
            # within a particular node export.  Thus we assign the current context
            # to the generator in _xhtml_content_document to be able to access it here.
            self.context.scripted = True
            return super(EpubHtml5Exporter.Generator, self).script(*args, **kwargs)

    _SUPPRESSED_MATHML = re.compile(
        # Annotations are otherwise displayed in iBooks.
        r'(<annotation encoding="ASCII">.*?</annotation>|'
        r' ((fontfamily|mathcolor)=""|contenteditable="false"))'
    )
    _INVALID_RESOURCE_URI_CHARACTERS = re.compile(r'[^a-z0-9;,_+*/=\-\.\(\)]')

    def __init__(self, *args, **kwargs):
        super(EpubHtml5Exporter, self).__init__(*args, **kwargs)
        self._resource_uri_dict = {}

    def _head(self, context):
        g = context.generator()
        stylesheet = context.resource('epub.css')
        return ([g.title(self._title(context)),
                 g.link(rel="stylesheet", type="text/css", href=context.uri(stylesheet))] +
                [g.script(src=context.uri(s)) for s in self._scripts(context)])

    def _export_table_of_contents(self, context, element):
        return ''

    def _export_inline_image(self, context, element):
        g = self._generator
        image = element.image(context)
        uri = context.uri(image)
        title = element.title()
        if title is None:
            title = image.title()
        descr = element.descr()
        if descr is None:
            descr = image.descr()
        if descr:
            if title:
                alt = self.concat(title, ': ', descr)
            else:
                alt = descr
        else:
            alt = title
        width, height = element.width(), element.height()
        if width is None and height is None:
            thumbnail = image.thumbnail()
            if thumbnail and thumbnail.size():
                width, height = [lcg.UPx(x) for x in thumbnail.size()]
            elif not thumbnail and image.size():
                width, height = [lcg.UPx(x) for x in image.size()]
        cls = ['lcg-image']
        if element.align():
            cls.append(element.align() + '-aligned')
        if element.name():
            cls.append('image-' + element.name())
        return g.img(uri, alt=alt, cls=' '.join(cls), style=self._image_style(width, height))

    def _export_mathml(self, context, element):
        context.mathml = True
        result = super(EpubHtml5Exporter, self)._export_mathml(context, element)
        return self._generator.noescape(self._SUPPRESSED_MATHML.sub('', result))

    def _uri_node(self, context, node, lang=None):
        return node.id() + '.xhtml'

    def _uri_resource(self, context, resource):
        return self.resource_uri(resource)

    def _export_inline_audio(self, context, element):
        """Export emedded audio player for given audio file.

        Use the HTML 5 <audio> tag instead of the LCG's shared player.  This is
        here because the original player implementation did not work in EPUB
        because of its Flash dependency.  This might be reconsidered after
        testing the new player implementation with EPUB.

        """
        g = self._generator
        audio = element.audio(context)
        image = element.image(context)
        title = element.title() or audio.title()
        descr = element.descr() or audio.descr()
        uri = context.uri(audio)
        if image:
            label = g.img(context.uri(image), alt=title)
            descr = descr or title
        else:
            label = title or audio.filename()
        return g.audio(src=uri, title=descr or title or audio.filename(),
                       # 'content' is displayed when the audio tag is not supported by browser
                       content=g.a(label, href=uri, title=descr))

    def resource_uri(self, resource):
        uri = resource.filename()
        if resource.SUBDIR:
            uri = resource.SUBDIR + '/' + uri
        # Normalize and disambiguate the URI (several source URIs may have
        # the same normalized form or the normalized form may match an existing
        # resource URI).
        if isinstance(uri, unistr):
            uri = unicodedata.normalize('NFKD', uri).encode('ascii', 'ignore').decode('ascii')
        uri = self._INVALID_RESOURCE_URI_CHARACTERS.sub('-', uri.lower())
        n = 0
        template = '%s-%%d%s' % os.path.splitext(uri)
        while self._resource_uri_dict.get(uri, resource) is not resource:
            n += 1
            uri = template % n
        self._resource_uri_dict[uri] = resource
        return uri


class EpubExporter(lcg.Exporter):

    class Config(object):
        """Specifies implementation-defined EPUB parameters"""
        RESOURCEDIR = 'rsrc'
        PACKAGE_DOC_FILENAME = 'pkg.opf'
        NAV_DOC_FILENAME = 'nav.xhtml'
        MAX_IMAGE_RESOLUTION = 3200000
        # iBooks has image size limitation.  The iOS version will not display larger
        # images at all.  The OSX version doesn't seem to care.  However it stil seems an
        # acceptable general limit to keep the total EPUB size reasonable.

    class Context(lcg.Exporter.Context):

        def _init_kwargs(self, allow_interactivity=True, **kwargs):
            self._allow_interactivity = allow_interactivity
            super(EpubExporter.Context, self)._init_kwargs(**kwargs)

        def allow_interactivity(self):
            return self._allow_interactivity

    def __init__(self, *args, **kwargs):
        kwargs.pop('force_lang_ext', None)
        super(EpubExporter, self).__init__(*args, **kwargs)
        self._html_exporter = EpubHtml5Exporter(translations=self._translation_path)

    def dump(self, node, directory, filename=None, variant=None, **kwargs):
        variants = (variant,) if variant else node.variants() or (None,)
        for lang in variants:
            context = self.context(node, lang, **kwargs)
            ext = lang and '.' + lang or ''
            f = open(filename + ext, 'w')
            f.write(self.export(context))

    def export(self, context):
        """Return the exported E-pub archive as a binary string."""
        fileobject = io.BytesIO()
        epub = zipfile.ZipFile(fileobject, 'w', zipfile.ZIP_DEFLATED)
        node = context.node()
        lang = context.lang()
        resources = []
        node_properties = {}
        try:
            mimeinfo = zipfile.ZipInfo('mimetype')
            mimeinfo.compress_type = zipfile.ZIP_STORED
            epub.writestr(mimeinfo, Constants.EPUB_MIMETYPE)
            epub.writestr(self._meta_path('container.xml'),
                          self._ocf_container(node, lang))
            epub.writestr(self._publication_resource_path(self.Config.NAV_DOC_FILENAME),
                          self._navigation_document(context))
            for n in node.linear():
                exported_content, properties = self._xhtml_content_document(n, context)
                epub.writestr(self._node_path(n), exported_content)
                for resource in n.resources():
                    if resource not in resources:
                        resources.append(resource)
                node_properties[n] = properties
            cover_image = node.cover_image()
            if cover_image and cover_image not in resources:
                resources.append(cover_image)
            for resource in resources:
                data = self._get_resource_data(context, resource)
                if isinstance(resource, lcg.Image):
                    import PIL.Image
                    image = PIL.Image.open(io.BytesIO(data))
                    width, height = image.size
                    max_resolution = self.Config.MAX_IMAGE_RESOLUTION
                    if width * height > max_resolution:
                        import math
                        scale = math.sqrt(float(max_resolution - 1) / (width * height))
                        size = (int(width * scale), int(height * scale))
                        image.thumbnail(size, PIL.Image.ANTIALIAS)
                        stream = io.BytesIO()
                        image.save(stream, image.format)
                        data = stream.getvalue()
                epub.writestr(self._resource_path(resource), data)

            epub.writestr(self._publication_resource_path(self.Config.PACKAGE_DOC_FILENAME),
                          self._package_document(node, lang, resources, node_properties))
        finally:
            try:
                epub.close()
            except Exception:
                # Closing may fail after a prior exception.
                # This prevents the later exception to take over.
                pass
        return fileobject.getvalue()

    def _get_resource_data(self, context, resource):
        """Return the resource file data as a (binary) string.

        The base class implementation only handles resources with src_file.
        Retrieving the file data for other resources is usually application
        specific.  Thus this method may be implemented to support such
        application specific resource retrieval.

        """
        return resource.get()

    def _container_path(self, *components):
        # TODO: replace forbidden characters as per spec
        if sys.version_info[0] == 2:
            def ensure_pathenc(component):
                if isinstance(component, unistr):
                    return component.encode(Constants.PATHENC)
                return component
            components = map(ensure_pathenc, components)
        return Constants.PATHSEP.join(components)

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
        return doc.toprettyxml(indent=4 * '', newl='', encoding='UTF-8')

    def _package_document(self, node, lang, resources, node_properties):
        doc = xml.Document()
        package = doc.appendChild(doc.createElement('package'))
        uid_id = 'uid'
        for name, value in (
                ('xmlns', Constants.OPF_NS),
                ('version', '3.0'),
                ('unique-identifier', uid_id),
                ('xml:lang', lang)):
            package.setAttribute(name, value)
        # metadata
        metadata = node.metadata() or lcg.Metadata()
        metadata_element = package.appendChild(doc.createElement('metadata'))
        metadata_element.setAttribute('xmlns:dc', Constants.DC_NS)

        def add_meta(name, value, **kwargs):
            if value:
                element = metadata_element.appendChild(doc.createElement(name))
                for k, v in kwargs.items():
                    element.setAttribute(k, v)
                element.appendChild(doc.createTextNode(value))
        if metadata.isbn:
            identifier = 'urn:isbn:' + metadata.isbn
        elif metadata.uuid:
            identifier = 'urn:uuid:%s' % metadata.uuid
        else:
            import uuid
            identifier = 'urn:uuid:%s' % uuid.uuid1()
        add_meta('dc:identifier', identifier, id=uid_id)
        add_meta('dc:source', metadata.original_isbn and 'urn:isbn:' + metadata.original_isbn)
        add_meta('dc:title', node.title())
        add_meta('dc:publisher', metadata.publisher)
        add_meta('dc:date', metadata.published)
        add_meta('dc:language', lang)
        for name in metadata.authors:
            add_meta('dc:creator', name)
        for name in metadata.contributors:
            add_meta('dc:contributor', name)
        add_meta('meta', datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                 property='dcterms:modified')
        # manifest and spine
        manifest = package.appendChild(doc.createElement('manifest'))
        spine = package.appendChild(doc.createElement('spine'))

        def add_item(item_id, href, mediatype, properties=()):
            item = manifest.appendChild(doc.createElement('item'))
            item.setAttribute('id', item_id)
            item.setAttribute('href', href)
            item.setAttribute('media-type', mediatype)
            if properties:
                item.setAttribute('properties', ' '.join(properties))
        add_item('nav', self.Config.NAV_DOC_FILENAME, 'application/xhtml+xml', properties=('nav',))
        for n in node.linear():
            item_id = 'node-' + n.id()  # Prefix to avoid ids beginning with a number (invalid HTML)
            href = '/'.join(self._node_path(n).split('/')[1:])  # TODO hack to make path relative
            add_item(item_id, href, mediatype='application/xhtml+xml',
                     properties=node_properties.get(n, ()))
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
        return doc.toprettyxml(indent=4 * '', newl='', encoding='UTF-8')

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
                # descr = item.descr() TODO: unused
                uri = context.uri(item)  # TODO fix relativeness, add #fragments for Sections
                li = ol.appendChild(doc.createElement('li'))
                a = li.appendChild(doc.createElement('a'))
                a.setAttribute('href', uri)
                a.appendChild(doc.createTextNode(title))
                if subitems:
                    export(subitems, li)
        # Add the top level node as the first navigation item.
        items = [(node, ())] + lcg.NodeIndex(node=node).items(lang)
        export(items, nav)
        return doc.toprettyxml(indent='', newl='', encoding='UTF-8')

    def _xhtml_content_document(self, node, root_context):
        exporter = self._html_exporter
        context = exporter.context(node, root_context.lang(), log=root_context.log,
                                   allow_interactivity=root_context.allow_interactivity())
        context.generator().context = context
        context.scripted = False
        context.mathml = False
        data = context.localize(exporter.export(context))
        properties = []
        if context.scripted:
            properties.append('scripted')
        if context.mathml:
            properties.append('mathml')
        return (data.encode('UTF-8'), properties)

    def uri(self, context, target, **kwargs):
        return self._html_exporter.uri(context, target, **kwargs)
