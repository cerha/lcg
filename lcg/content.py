# -*- coding: utf-8 -*-

# Copyright (C) 2004-2017 OUI Technology Ltd.
# Copyright (C) 2019-2025 Tomáš Cerha <t.cerha@gmail.com>
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

"""Generic content abstraction.

The classes defined in this module were designed to represent general content
elements of a structured document, such as sections, paragraphs, lists, tables
etc.  Each content element is represented by an instance of one of the classes
defined below.  Some types of elements can contain other elements and thus the
whole document is represented by a tree of content elements.  When the
construction of the whole tree is finished, each element knows its ancestor
(the container) and all the successors (sub-content) in the tree.

The content hierarchy may be built independently, however you need to assign a
content to a 'lcg.ContentNode' instance to be able to export it.

Please note the difference between the hierarchy of content within one node and
the hierarchy of the nodes themselves.

"""

from __future__ import unicode_literals
from future import standard_library
from builtins import range

import sys
import copy
import re
import lcg


_ = lcg.TranslatableTextFactory('lcg')

standard_library.install_aliases()
unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


class Content(object):
    """Generic base class for all types of content.

    All (more specific) content element classes are derived from this class.

    Each content element instance may be contained in another content element
    instance (see the 'Container' class) and thus they make a hierarchical
    structure.

    """
    _ALLOWED_CONTAINER = None

    def __init__(self, lang=None, resources=()):
        """Initialize the instance.

        Arguments:

          lang -- content language as a lowercase ISO 639-1 Alpha-2 language code.
          resources -- sequence of resource instances associated with the
            content.  This allows passing resource instances explicitly with
            content rather than relying on their allocation through resource
            provider.

        """
        assert resources is None or isinstance(resources, (tuple, list)), resources
        self._parent = None
        self._container = None
        self._lang = lang
        self._page_number = ''
        self._resources = tuple(resources)
        super(Content, self).__init__()

    def set_container(self, container):
        """Set the parent 'Container' to 'container'.

        This method is normally called automatically by the container
        constructor to inform the contained 'Content' elements about their
        position in content hierarchy.  You only need to care about calling
        this method if you implement your own 'Container' class and don't call
        the default constructor for all the contained elements for some reason.
        Otherwise it is always called automatically by LCG behind the scenes.

        """
        if __debug__:
            cls = self._ALLOWED_CONTAINER or Container
            assert isinstance(container, cls), \
                "Not a '%s' instance: %s" % (cls.__name__, container,)
        self._container = container

    def set_parent(self, node):
        """Set the parent 'lcg.ContentNode' to 'node'.

        This method is deprecated.  The parent node (the node to which the
        content belongs) should always be obtained from the export context, not
        from the node itself.  This method is now called automatically when an
        element is exported to keep the 'parent()' method working, but both
        methods should be avoided in newly written code.

        """
        assert isinstance(node, lcg.ContentNode), \
            "Not a 'lcg.ContentNode' instance: %s" % node
        # assert self._parent is None or self._parent is node, \
        #       "Reparenting not allowed: %s -> %s" % (self._parent, node)
        self._parent = node

    def set_page_number(self, number):
        """Set page number of the content element.

        This is to be used in table of contents.

        Arguments:

          number -- the page number; basestring

        """
        assert isinstance(number, basestring), number
        self._page_number = number

    def parent(self):
        """Deprecated.  Use context.node() instead."""
        parent = self._parent or self._container and self._container.parent()
        return parent

    def lang(self, inherited=True):
        """Return the content language as lowercase ISO 639-1 Alpha-2 language code.

        Arguments:

          inherited -- iff True, the language will be determined from the
            parent element in the hierarchy if this element doesn't define
            'lang' explicitly.  When False, the value of 'lang' passed to the
            constructor is returned.

        """
        lang = self._lang
        if lang is None and inherited and self._container:
            lang = self._container.lang()
        return lang

    def resources(self):
        """Return the value of 'resources' passed to the constructor as a tuple."""
        return self._resources

    def container(self):
        """Return the direct container of this element."""
        return self._container

    def container_path(self):
        """Return a list of containers of the given element

        The list is sorted from top to bottom, the last element being
        this element itself.

        """
        path = [self]
        while path[0]._container is not None:
            path.insert(0, path[0]._container)
        return tuple(path)

    def _neighbor_element(self, direction, stop_classes):
        element = self
        container = self.container()
        while True:
            if container is None:
                return None
            content = container.content()
            index = content.index(element)
            if direction < 0:
                if index > 0:
                    neighbor = content[index - 1]
                    break
            else:
                if index < len(content) - 1:
                    neighbor = content[index + 1]
                    break
            if isinstance(container, stop_classes):
                return None
            element = container
            container = container.container()
        while isinstance(neighbor, Container):
            content = neighbor.content()
            if not content:
                return neighbor
            neighbor = content[-1]
        return neighbor

    def previous_element(self, stop_classes=()):
        """ """
        return self._neighbor_element(-1, stop_classes)

    def next_element(self, stop_classes=()):
        """ """
        return self._neighbor_element(1, stop_classes)

    def sections(self):
        """Return the contained sections as a list of 'Section' instances.

        This method allows introspection of content hierarchy (for example for
        creation of a table of contents).

        An empty list is returned in the base class.  Derived classes which
        contain sections should override this method to return the contained
        sections.

        """
        return []

    def page_number(self):
        """Return page number of the content element.

        This is to be used in table of contents.

        Arguments:

          context -- formatting context as a 'Exporter.Context' instance
            created and returned by 'Exporter.context' method

        """
        return self._page_number

    def export(self, context):
        """Return the formatted content in an output specific form.

        The return value can later be processed by 'Exporter' methods.

        Arguments:

          context -- formatting context as a 'Exporter.Context' instance
            created and returned by 'Exporter.context' method

        """
        return context.exporter().export_element(context, self)


class Container(Content):
    """Container of other content elements.

    Containers allow to build a hierarchy of 'Content' instances inside the
    scope of one node.  This is an addition to the hierarchy of the nodes
    themselves.

    All the contained (wrapped) content elements will be notified about the
    fact, that they are contained within this container and thus belong to the
    hierarchy.

    """
    _ALLOWED_CONTENT = Content
    _SUBSEQUENCES = False
    _SUBSEQUENCE_LENGTH = None

    def __init__(self, content, name=(), id=None, role=None, label=None,
                 halign=None, valign=None, orientation=None, width=None, height=None,
                 padding=None, presentation=None, **kwargs):
        """Initialize the instance.

        Arguments:

          content -- the actual content wrapped into this container as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.
          name -- optional string identifier or a sequence of them.  These
            identifiers may be then used as output presentation selectors (for
            example in HTML they will compose the value of the 'class'
            attribute).
          id -- unique identifier as a string.  The identifier must be unique
            within the whole content hierarchy of one 'lcg.ContentNode'.
          role -- ARIA role name for HTML output as a string or None.
          label -- container label to be used for aria-label in HTML output.
          halign -- horizontal alignment of the container content; one of the
            'lcg.HorizontalAlignment' constants or 'None' (default alignment).
          valign -- vertical alignment of the container content; one of the
            'VerticalAlignment' constants or 'None' (default alignment).
          orientation -- orientation of the container content flow (vertical
            vs.horizontalal); one of the 'Orientation' constants or 'None'
            (default orientation).
          width -- explicit output width as 'lcg.Unit' subclass instance.
            Applies to the outer dimension of the whole box including any
            padding and/or box_margin.  Currently only supported in PDF export.
          height -- explicit output width as 'lcg.Unit' subclass instance.
            Applies to the outer dimension of the whole box including any
            padding and/or box_margin.  Currently only supported in PDF export.
          padding -- space around the container content.  If not None, it can
            be either a 'Unit' instance determining equal padding for all sides
            or a sequence of four 'Unit' instances determining padding for each
            side separately in the order (top, right, bottom, left) or a
            sequence of two 'Unit' instances, where the first value determines
            top and bottom padding and the second value determines left and
            right padding.  Note, that 'presentation' may also define
            'box_margin' for a boxed group, but there are major differences
            between box_margin and padding.  Box margin only applies to boxed
            groups and is ignored for non boxed groups.  Padding applies to
            both.  Also, box_margin is (through presentation inheritance)
            inherited to any inner boxed groups which don't explicitly override
            it.  Padding only applies to the container for which it is defined.
            Currently only supported in PDF export.
          presentation -- 'Presentation' instance defining various presentation
            properties; if 'None' then no explicit presentation for this container
            is defined.

        Note that 'halign', 'valign', 'orientation', 'width', 'height' and 'presentation'
        parameters may be ignored by some exporters.

        """
        super(Container, self).__init__(**kwargs)
        assert isinstance(name, basestring) or lcg.is_sequence_of(name, basestring), name
        assert halign is None or isinstance(halign, basestring), halign
        assert valign is None or isinstance(valign, basestring), valign
        assert orientation is None or isinstance(orientation, basestring), orientation
        assert id is None or isinstance(id, basestring), id
        assert width is None or isinstance(width, lcg.Unit), width
        assert height is None or isinstance(height, lcg.Unit), height
        assert (padding is None or isinstance(padding, lcg.Unit)
                or lcg.is_sequence_of(padding, lcg.Unit) and len(padding) in (2, 4)), padding
        self._id = id
        if isinstance(name, basestring):
            names = (name,)
        else:
            names = tuple(name)
        self._names = names
        self._role = role
        self._label = label
        from lcg import Presentation
        assert presentation is None or isinstance(presentation, Presentation), presentation
        super(Container, self).__init__(**kwargs)
        self._halign = halign
        self._valign = valign
        self._orientation = orientation
        self._width = width
        self._height = height
        self._padding = padding
        self._presentation = presentation
        self._contained_resources = None
        if self._SUBSEQUENCES:
            assert isinstance(content, (list, tuple)), "Not a sequence: %s" % content
            self._content = tuple([tuple(subseq) for subseq in content])
            for subseq in content:
                assert isinstance(subseq, (list, tuple)), "Not a sequence: %s" % subseq
                if self._SUBSEQUENCE_LENGTH is not None:
                    assert len(subseq) == self._SUBSEQUENCE_LENGTH
                for c in subseq:
                    assert isinstance(c, self._ALLOWED_CONTENT), \
                        "Not a '%s' instance: %s" % (self._ALLOWED_CONTENT, c)
                    c.set_container(self)
        elif isinstance(content, (list, tuple)):
            assert lcg.is_sequence_of(content, self._ALLOWED_CONTENT), \
                "Not a '%s' instances sequence: %s" % (self._ALLOWED_CONTENT, content)
            self._content = tuple(content)
            for c in content:
                c.set_container(self)
        else:
            assert isinstance(content, self._ALLOWED_CONTENT), \
                "Not a '%s' instance: %s" % (self._ALLOWED_CONTENT, content)
            self._content = (content,)
            content.set_container(self)

    def content(self):
        """Return the sequence of contained content elements.
        """
        return self._content

    def id(self):
        """Return the unique identifier of this container as a string."""
        return self._id

    def sections(self):
        result = []
        for c in self._content:
            if isinstance(c, Section):
                result.append(c)
            elif isinstance(c, Container):
                result.extend(c.sections())
        return result

    def names(self):
        """Return the tuple of strings passed as 'name' to the constructor."""
        return self._names

    def role(self):
        """Return the 'role' passed to the constructor."""
        return self._role

    def label(self):
        """Return the 'label' passed to the constructor."""
        return self._label

    def halign(self):
        """Return the value of 'halign' as passed to the constructor."""
        return self._halign

    def valign(self):
        """Return the value of 'valign' as passed to the constructor."""
        return self._valign

    def orientation(self):
        """Return the value of 'orientation' as passed to the constructor."""
        return self._orientation

    def width(self):
        """Return the value of 'width' as passed to the constructor."""
        return self._width

    def height(self):
        """Return the value of 'height' as passed to the constructor."""
        return self._height

    def padding(self):
        """Return the value of 'padding' as passed to the constructor."""
        return self._padding

    def presentation(self):
        """Return the value of 'presentation' as passed to the constructor."""
        return self._presentation

    def resources(self):
        """Return the value of 'resources' as passed to the constructor."""
        if self._contained_resources is None:
            resources = []
            if self._SUBSEQUENCES:
                content = self._content
            else:
                content = (self._content,)
            for subseq in content:
                for c in subseq:
                    resources.extend(c.resources())
            self._contained_resources = tuple(resources)
        return self._resources + self._contained_resources


# ======================== Inline content elements ========================


class Strong(Container):
    """Text emphasized by bold font face."""
    pass


class Emphasized(Container):
    """Text emphasized by slanted font face."""
    pass


class Underlined(Container):
    """Underlined text."""
    pass


class Code(Container):
    """Text representing a piece of computer code."""
    pass


class Citation(Container):
    """Citation of a text in another language."""
    pass


class Quotation(Container):
    """Quotation of content from other source."""

    def __init__(self, content, source=None, uri=None, **kwargs):
        """Arguments:

          content -- quoted content as lcg.Content instance
          source -- reference to the source of the quotation, such as the
            original author, publication, web page etc. (basestring)
          uri -- link to the source (basestring)

        """
        assert source is None or isinstance(source, basestring), source
        assert uri is None or isinstance(uri, basestring), uri
        self._source = source
        self._uri = uri
        super(Quotation, self).__init__(content, **kwargs)

    def source(self):
        """Return the quotation source as passed to the constructor."""
        return self._source

    def uri(self):
        """Return the quotation source URI as passed to the constructor."""
        return self._uri


class Superscript(Container):
    """Text vertically aligned above the normal line level."""
    pass


class Subscript(Container):
    """Text vertically aligned below the normal line level."""
    pass


class TextContent(Content):
    """A simple piece of text."""

    def __init__(self, text, **kwargs):
        """Initialize the instance.

        Arguments:

          text -- the actual text content of this element as a string or
            unicode
          kwargs -- keyword arguments for parent class constructor.

        """
        assert isinstance(text, basestring), text
        super(TextContent, self).__init__(**kwargs)
        self._text = text

    def __unicode__(self):
        text = self._text.strip()
        sample = text and text.splitlines()[0] or ''
        if len(sample) > 20:
            sample = sample[:20]
        if len(sample) < len(text):
            sample += '...'
        cls = self.__class__.__name__
        return '<%s at 0x%x text="%s">' % (cls, id(self), sample)

    def text(self):
        """Return the value of 'text' as passed to the constructor."""
        return self._text

    def clone(self, text):
        """Return copy of the instance with text replaced by 'text'.

        Arguments:

          text -- text content of the element copy; basestring

        """
        cloned = copy.copy(self)
        cloned._text = text
        return cloned


class Link(Container):
    """Link to internal or external location."""

    class ExternalTarget(object):
        """Representation of an external target specified by its URI."""

        def __init__(self, uri, title, descr=None, lang=None):
            """Arguments:

              uri -- URI of the link target as a string
              title -- title of the target as a string or unicode
              descr -- ???
              lang -- lowercase ISO 639-1 Alpha-2 language code

            """
            self._uri = uri
            self._title = title
            self._descr = descr
            self._lang = lang

        def uri(self):
            return self._uri

        def title(self):
            return self._title

        def descr(self):
            return self._descr

        def lang(self):
            return self._lang

    def __init__(self, target, label=None, descr=None, type=None, lang=None):
        """Arguments:

          target -- target of the link, instance of 'Section', 'lcg.ContentNode',
            'lcg.Resource', 'Link.ExternalTarget' or 'basestring'.  If a string is
            used, it is a temporary reference to be resolved in export time.
            It allows creation of links which refer to objects, which can not
            be resolved at the time of Link instance creation (their instances
            may not exist yet when the source text is parsed).  The reference
            is then automatically resolved by the method 'target()' into one of
            the other allowed link targets.
          label -- link label text as a string or a 'Content' instance (such as
            'InlineImage' for image links)
          descr -- breif target description text.  If none the description is
            taken from the 'target' instance depending on its type
          type -- ???
          lang -- lowercase ISO 639-1 Alpha-2 language code

        """
        assert isinstance(target, (Section, lcg.ContentNode, lcg.Resource, self.ExternalTarget,
                                   basestring)), target
        assert label is None or isinstance(label, (basestring, Content)), label
        assert descr is None or isinstance(descr, basestring), descr
        assert type is None or isinstance(type, basestring), type
        assert lang is None or isinstance(lang, basestring), lang
        if isinstance(label, basestring):
            content = TextContent(label)
        elif label is not None:
            content = label
        else:
            content = ()
        self._target = target
        self._descr = descr
        self._type = type
        super(Link, self).__init__(content, lang=lang)

    def target(self, context):
        """Return the link target.

        If a string reference was passed to the constructor argument 'target',
        it is automatically resolved, so the returned instance is always one of
        'Section', 'lcg.ContentNode', 'lcg.Resource' or 'Link.ExternalTarget'.

        """
        target = self._target
        if isinstance(target, basestring):
            reference = target
            target = context.resource(reference, warn=False)
            if target is None and '@' not in reference:
                if '#' in reference:
                    node_id, section_id = reference.split('#', 1)
                    node = context.node()
                    if node_id:
                        node = node.root().find_node(node_id)
                    if node:
                        target = node.find_section(context.lang(), section_id)
                else:
                    target = context.node().root().find_node(reference)
            if target is None:
                target = self.ExternalTarget(reference, reference)
        return target

    def descr(self):
        """Return the link description as passed to the constructor argument 'descr'."""
        return self._descr

    def type(self):
        """Return the value of 'type' as passed to the constructor."""
        return self._type

    def node_id(self):
        "Return target node id (basestring) or 'None'."
        target = self._target
        if isinstance(target, basestring) and '#' in target:
            return target.split('#', 1)[0]
        return None


class Abbreviation(TextContent):
    """Abbreviation with description."""

    def __init__(self, text, descr, **kwargs):
        """Arguments:

          text -- the abbreviation as a string or unicode.
          descr -- the description as a string or unicode.

        """
        assert isinstance(descr, basestring), descr
        self._descr = descr
        super(Abbreviation, self).__init__(text, **kwargs)

    def descr(self):
        """Return the abbreviation description given in the constructor."""
        return self._descr


class Anchor(TextContent):
    """Target of a link (an anchor)."""

    def __init__(self, anchor, text='', **kwargs):
        """Arguments:

          anchor -- name of the link target anchor as a string.
          text -- text of the target place as a string or unicode.

        """
        assert isinstance(anchor, basestring), anchor
        self._anchor = anchor
        super(Anchor, self).__init__(text, **kwargs)

    def anchor(self):
        """Return link target name given in the constructor."""
        return self._anchor


class _InlineObject(Content):
    """Super class for embedded objects, such as images, audio and video."""

    def __init__(self, title=None, descr=None, name=None, lang=None):
        """Arguments:

          title -- object title as a string or unicode.  If not None, overrides
            'resource.title()' for this particular use.
          descr -- object description a string or unicode.  If not None, overrides
            'resource.descr()' for this particular use.
          name -- arbitrary name (string) identifying the object.  Used as CSS
            class name in HTML to allow individual styling.
          lang -- content language as an ISO 639-1 Alpha-2 language code (lowercase)

        """
        assert title is None or isinstance(title, basestring), title
        assert descr is None or isinstance(descr, basestring), descr
        assert name is None or isinstance(name, basestring), name
        self._title = title
        self._descr = descr
        self._name = name
        super(_InlineObject, self).__init__(lang=lang)

    def _resource_instance(self, context, resource, cls):
        if isinstance(resource, basestring):
            filename = resource
            if ((filename.startswith('http:') or filename.startswith('https:') or
                 filename.startswith('ftp:'))):
                resource = cls(filename, uri=filename)
            else:
                resource = context.resource(filename)
                if resource is None:
                    resource = cls(filename, uri=filename)
                else:
                    assert isinstance(resource, cls), resource
        return resource

    def title(self):
        """Return the value of 'title' as passed to the constructor."""
        return self._title

    def descr(self):
        """Return the value of 'descr' as passed to the constructor."""
        return self._descr

    def name(self):
        """Return the value of 'name' as passed to the constructor."""
        return self._name


class InlineImage(_InlineObject):
    """Image embedded inside the document.

    The image may be either a part of a textual paragraph or standalone
    (outside paragraph).  When inside paragraph, it may float left or right
    from the surrounding text or be put directly into its position within the
    text.

    """

    LEFT = 'left'
    RIGHT = 'right'
    TOP = 'top'
    BOTTOM = 'bottom'
    MIDDLE = 'middle'

    def __init__(self, image, align=None, width=None, height=None, standalone=False, **kwargs):
        """Arguments:

          image -- the displayed image as an 'lcg.Image' resource instance.
          align -- requested alignment of the image within the surrounding
            text; one of the class constants: 'InlineImage.LEFT' and
            'InlineImage.RIGHT' make the image float aside the text,
            'InlineImage.TOP', 'InlineImage.BOTTOM' , 'InlineImage.MIDDLE'
            align the image horizontally within the text line. 'None' let's the
            output backend decide the best image position.
          width -- output image width as lcg.Unit subclass instance.  If only
            one of width/height is specified (not None), the other dimension is
            computed to maintain the original image proportions.  Note that
            various output backends may only support certain units.
          height -- output image height as lcg.Unit subclass instance.  See 'width'.
          standalone -- iff true then never put the image inside a paragraph.

        All other keyword arguments are passed to the parent class constructor.

        """
        assert isinstance(image, (lcg.Image, basestring)), image
        assert align in (None, self.LEFT, self.RIGHT, self.TOP, self.BOTTOM, self.MIDDLE), align
        assert width is None or isinstance(width, lcg.Unit), width
        assert height is None or isinstance(height, lcg.Unit), height
        assert isinstance(standalone, bool), standalone
        self._image = image
        self._align = align
        self._width = width
        self._height = height
        self._standalone = standalone
        super(InlineImage, self).__init__(**kwargs)

    def image(self, context):
        """Return the value of 'image' passed to the constructor.

        If the 'image' was passed as a string reference, it is automatically
        converted into an 'lcg.Image' instance.

        """
        return self._resource_instance(context, self._image, lcg.Image)

    def align(self):
        """Return the value of 'align' as passed to the constructor."""
        return self._align

    def width(self):
        """Return the value of 'width' as passed to the constructor."""
        return self._width

    def height(self):
        """Return the value of 'height' as passed to the constructor."""
        return self._height

    def standalone(self):
        """Return the value of 'standalone' as passed to the constructor."""
        return self._standalone


class InlineAudio(_InlineObject):
    """Audio file embedded inside the document.

    When possible, this element should be represented by an interactive control
    which invokes playback of the embedded audio.

    """

    def __init__(self, audio, image=None, **kwargs):
        """Arguments:

          audio -- the target audio file as 'lcg.Audio' resource instance.
          image -- visual presentation image as an 'lcg.Image' resource instance or None.

        All other arguments are passed to the parent class constructor.

        """
        assert isinstance(audio, (lcg.Audio, basestring)), audio
        assert image is None or isinstance(image, (lcg.Image, basestring)), image
        self._audio = audio
        self._image = image
        super(InlineAudio, self).__init__(**kwargs)

    def audio(self, context):
        """Return the value of 'audio' as passed to the constructor.

        If the 'audio' was passed as a string reference, it is automatically
        converted into an 'lcg.Audio' instance.

        """
        return self._resource_instance(context, self._audio, lcg.Audio)

    def image(self, context):
        """Return the value of 'image' as passed to the constructor.

        If the 'image' was passed as a string reference, it is automatically
        converted into an 'lcg.Image' instance.

        """
        return self._resource_instance(context, self._image, lcg.Image)


class InlineVideo(_InlineObject):
    """Video file embedded inside the document.

    When possible, this element should be represented as an embedded video
    player preloaded with given video and playing it on invocation.

    """

    def __init__(self, video, image=None, size=None, **kwargs):
        """Arguments:

          video -- 'lcg.Video' resource instance.
          image -- video thumbnail image as an 'lcg.Image' resource instance or None.
          size -- size in pixels as a tuple of two integers (WIDTH, HEIGHT)

        All other keyword arguments are passed to the parent class constructor.

        """
        assert isinstance(video, (lcg.Video, basestring)), video
        assert image is None or isinstance(image, (lcg.Image, basestring)), image
        assert size is None or isinstance(size, tuple), size
        self._video = video
        self._image = image
        self._size = size
        super(InlineVideo, self).__init__(**kwargs)

    def video(self, context):
        """Return the value of 'video' as passed to the constructor.

        If the 'video' was passed as a string reference, it is automatically
        converted into an 'lcg.Video' instance.

        """
        return self._resource_instance(context, self._video, lcg.Video)

    def image(self, context):
        """Return the value of 'image' as passed to the constructor.

        If the 'image' was passed as a string reference, it is automatically
        converted into an 'lcg.Image' instance.

        """
        return self._resource_instance(context, self._image, lcg.Image)

    def size(self):
        """Return the value of 'size' as passed to the constructor."""
        return self._size


class InlineExternalVideo(Content):
    """Embedded video from external services such as YouTube or Vimeo

    When possible, this element should be represented as an embedded video
    player preloaded with given video and playing it on invocation.

    """

    def __init__(self, service, video_id, title=None, descr=None, size=None, lang=None):
        """Arguments:

          service -- string identifier of the video service.  The two currently
            supported services are 'youtube' and 'vimeo'.
          video_id -- string identifier of the video within the given service.
          title -- video title as a string or None.
          size -- explicit video size in pixels as a tuple of two integers
            (WIDTH, HEIGHT) or None for the default size.
          lang -- content language as an ISO 639-1 Alpha-2 language code (lowercase)

        """
        assert service in ('youtube', 'vimeo'), service
        assert isinstance(video_id, basestring), video_id
        assert size is None or isinstance(size, tuple), size
        self._service = service
        self._video_id = video_id
        self._title = title
        self._descr = descr
        self._size = size
        super(InlineExternalVideo, self).__init__(lang=lang)

    def service(self):
        """Return the string identifier of the video service."""
        return self._service

    def video_id(self):
        """Return the string identifier of the video within the service."""
        return self._video_id

    def title(self):
        """Return the value of 'title' as passed to the constructor."""
        return self._title

    def descr(self):
        """Return the value of 'descr' as passed to the constructor."""
        return self._descr

    def size(self):
        """Return the video size in pixels as a pair of integers or None."""
        return self._size


class Title(Content):
    """Inline element, which is substituted by the title of the requested item in export time.

    It may not be possible to find out what is the title of the current node or some other element
    in the time of content construction.  So this symbolic element may be used to refer to the item
    an it will be simply replaced by the title text in export time.

    The constructor argument 'id' may be used to refer to the required item.  It may be a section
    id in the current page or an identifier of another node.  The default value (None) refers to
    the title of the current node.  If the item refered by id can not be found, the id itself is
    used for substitution.

    """

    def __init__(self, id=None):
        """Arguments:

          id -- reference to the item providing the required title; it may be a
            section id (??? what is it ???) in the current page or an
            identifier of another node (??? what is it ???).  'None' refers to
            the title of the current node.  If the item refered by 'id' cannot
            be found, the id itself is used for substitution.

        """
        super(Title, self).__init__()
        self._id = id

    def id(self):
        """Return the value of 'id' as passed to the constructor."""
        return self._id


class HorizontalSeparator(Content):
    """Horizontal separator.

    Typically rendered as a horizontal line separating visually the content
    above and below it.

    """

    def __init__(self, thickness=None, color=None, **kwargs):
        """Arguments:
        thickness -- Thickness of the line as 'lcg.Unit' or None for the (media
          dependent) default thickness.  Currently only supported by the PDF backend.
        color -- line color as 'lcg.Color' or None for the (media dependent)
          default color.  Currently only supported by the PDF backend.
        """
        assert thickness is None or isinstance(thickness, lcg.Unit), thickness
        assert color is None or isinstance(color, lcg.Color), color
        self._thickness = thickness
        self._color = color
        super(HorizontalSeparator, self).__init__(**kwargs)

    def thickness(self):
        return self._thickness

    def color(self):
        return self._color


class NewPage(Content):
    """New page starts here."""
    pass


class NewLine(Content):
    """Explicit line break."""
    pass


class PageNumber(Content):
    """Current page number.

    The page number is generated as an ordinal arabic number starting from one.

    This content may be used only inside page headers and footers.

    """

    def __init__(self, total=False, separator=None, lang=None):
        """
        Arguments:

          total -- iff true, output not only the page number, but also the
            total number of pages; if 'separator' is 'None', output only the
            total number of pages
          separator -- basestring or 'None'; if it is a basestring and 'total'
            is true, insert it betwenn the page numebr and the total number of
            pages
          lang -- content language as an ISO 639-1 Alpha-2 language code (lowercase)

        """
        super(PageNumber, self).__init__(lang=lang)
        self._total = total
        self._separator = separator

    def total(self):
        """Return the value of 'total' as passed to the constructor."""
        return self._total

    def separator(self):
        """Return the value of 'separator' as passed to the constructor."""
        return self._separator


class PageHeading(Content):
    """Current page heading.

    This content may be used only inside page headers and footers.

    """
    pass


class HSpace(Content):
    """Horizontal space of given size.

    This should be used only in places where explicit space is needed.  In many
    cases better means such as higher level elements, alignment or style sheets
    can be used.

    """

    def __init__(self, size, lang=None):
        """
        @type: L{lcg.Unit}
        @param: Size of the space.
        @type: string
        @param: Content language as an ISO 639-1 Alpha-2 language code (lowercase).
        """
        super(HSpace, self).__init__(lang=lang)
        assert isinstance(size, lcg.Unit), size
        self._size = size

    def size(self, context):
        """Return the value of 'size' as passed to the constructor."""
        return self._size


class VSpace(HSpace):
    """Vertical space of given size.

    This should be used only in places where explicit space is needed.  In many
    cases better means such as higher level elements, alignment or style sheets
    can be used.

    """


class HtmlContent(Content):
    """Special element for dirtect HTML embedding in LCG content hierarchy.

    This class only supports HTML export and an attempt to export an element of
    this class to any other target format will lead to an error.

    The HTML content may be passed directly as a Python string or as a Python
    function which will be called to generate the content dynamically in export
    time.  The function will be called with at least two arguments (context,
    element), where 'element' is the 'HtmlContent' instance itself and
    'context' is a 'wiking.Exporter.Context' instance.  Any positional
    arguments passed to the constructor are also passed to the export function.

    Use with caution.  Defining specific content classes for more generic
    content elements is encouraged over using this class.  This class should
    only be used for simple cases where defining a class makes too much
    unnecessary noise...

    This class demonstrates a content element, which exports itself actively
    and doesn't rely on the exporter as the other generic elements defined in
    this module.

    """

    def __init__(self, content, *args, **kwargs):
        """Initialize the instance.

        Arguments:

          content -- the actual HTML content of this element as a basestring
            or an export function (see class docstring for details).
          *args -- additional positional arguments passed to the export
            function (given in 'content').  No arguments are allowed when
            'content' is a basestring.
          kwargs -- keyword arguments for parent class constructor.

        """
        assert isinstance(content, basestring) or callable(content), content
        self._content = content
        self._export_args = args
        super(HtmlContent, self).__init__(**kwargs)

    def export(self, context):
        assert isinstance(context.exporter(), lcg.HtmlExporter), \
            "Only HTML export is supported for this element."
        if isinstance(self._content, basestring):
            g = context.generator()
            return g.noescape(self._content)
        else:
            return self._content(context, self, *self._export_args)


class Heading(Container):
    """Heading, e.g. heading of a section.

    Purpose of this element is twofold: to provide information about level of
    the heading and to distinguish the element from other parts of a document
    for the purpose of applying specific styles to its content.

    """

    def __init__(self, content, level, **kwargs):
        """
        Arguments:

          cotnent -- the actual content of this element as lcg.Content element
            or their sequence
          level -- level of the heading, positive integer, starting from 1
          kwargs -- keyword arguments for parent class constructor

        """
        assert isinstance(level, int) and level > 0, level
        super(Heading, self).__init__(content, **kwargs)
        self._level = level

    def level(self):
        "Return level of the heading, positive integer, starting from 1."
        return self._level


class PreformattedText(TextContent):
    """Preformatted text."""

    def __init__(self, text, mime_type=None, **kwargs):
        """Arguments:

          text -- the text itself as a basestring.
          mime_type -- MIME type of the text as a basestring.  Used for
            syntax highlighting in HTML export.

        """
        super(PreformattedText, self).__init__(text, **kwargs)
        self._mime_type = mime_type

    def mime_type(self):
        """Return MIME type of the text if it was passed to the constructor or None."""
        return self._mime_type


# ======================== Block level elements ========================


SectionContainer = Container
"""Deprecated: Use 'Container' instead."""


class Paragraph(Container):
    """A paragraph of text, where the text can be any 'Content'."""

    def __init__(self, content, noindent=False, **kwargs):
        """Arguments:

          content -- sequence of list items as 'Content' instances.
          noindent -- True if first line indentation should be suppressed.
            Note, that only PDF export currently supports first paragraph line
            indentation.

        """
        assert isinstance(noindent, bool)
        self._noindent = noindent
        super(Paragraph, self).__init__(content, **kwargs)

    def noindent(self):
        """Return 'noindent' as it was given in the constructor."""
        return self._noindent


class ItemizedList(Container):
    """An itemized list."""

    NUMERIC = 'numeric'
    LOWER_ALPHA = 'lower-alpha'
    UPPER_ALPHA = 'upper-alpha'

    def __init__(self, content, order=None, **kwargs):
        """Arguments:

          content -- sequence of list items as 'Content' instances.
          order -- one of class constants determining the list item ordering style or
            None for an unordered list (bullet list).

        """
        assert order in (None, self.LOWER_ALPHA, self.UPPER_ALPHA, self.NUMERIC)
        self._order = order
        super(ItemizedList, self).__init__(content, **kwargs)

    def order(self):
        """Return the value of 'order' as passed to the constructor."""
        return self._order


class DefinitionList(Container):
    """A list of definitions.

    The constructor accepts a sequence of definitions, where each definition is a pair '(TERM,
    DESCRIPTION)', where both items are 'Content' instances.

    """
    _SUBSEQUENCES = True
    _SUBSEQUENCE_LENGTH = 2


class FieldSet(Container):
    """A list of label and value pairs.

    The constructor accepts a sequence of '(LABEL, VALUE)' pairs, where both
    items are 'Content' instances.  Logically similar to 'DefinitionList', but
    more suitable for an enumeration of shorter fields presented side by side
    (while definition description usually follows on another line below the
    term).

    """
    _SUBSEQUENCES = True
    _SUBSEQUENCE_LENGTH = 2


class TableCell(Container):
    """Table cell is a container of cell content and may appear within 'TableRow'."""
    LEFT = lcg.HorizontalAlignment.LEFT
    RIGHT = lcg.HorizontalAlignment.RIGHT
    CENTER = lcg.HorizontalAlignment.CENTER

    def __init__(self, content, align=None, **kwargs):
        """Arguments:

          align -- requested cell content alignment, 'None' or one of the
            constants 'TableCell.LEFT', 'TableCell.RIGHT', 'TableCell.CENTER'
            or 'None' for the default alignment.

        """
        assert align in (None, self.LEFT, self.RIGHT, self.CENTER), align
        self._align = align
        super(TableCell, self).__init__(content, **kwargs)

    def align(self):
        """Return the value of 'align' as passed to the constructor."""
        return self._align


class TableHeading(TableCell):
    """Table heading is a container of heading content and may appear within 'TableRow'."""
    pass


class TableRow(Container):
    """Table row is a container of cells or headings and may appear within 'Table'."""
    _ALLOWED_CONTENT = (TableCell, TableHeading)

    def __init__(self, content, line_above=None, line_below=None, iterated=False, **kwargs):
        """Arguments:

          line_above -- iff true, request line above the row
          line_below -- iff true, request line below the row
          iterated -- iff true, this row expands into any number of rows
            according to the iterator variable used within one or more of its
            cells

        """
        self._line_above = line_above
        self._line_below = line_below
        self._iterated = iterated
        super(TableRow, self).__init__(content, **kwargs)

    def line_above(self):
        return self._line_above

    def line_below(self):
        return self._line_below

    def set_line_below(self, n):
        self._line_below = n

    def iterated(self):
        return self._iterated


class Table(Container):
    """Table is a container of 'TableRow' instances."""
    _ALLOWED_CONTENT = (TableRow, HorizontalSeparator,)

    def __init__(self, content, title=None, long=False, column_widths=None, bars=(),
                 compact=False, transformations=('facing', 'transpose',), **kwargs):
        """Arguments:

          content -- sequence of 'TableRow' and 'HorizontalSeparator' instances
          title -- 'None' or table caption as a string or unicode
          long -- boolean indicating whether the table is long.  Long table is
            usually a table that may not fit on a single page.  Long tables may
            be handled in a different way, e.g. by splitting into several parts
            even when the table could fit on a new separate page or by using
            different column widths on each page when the column widths are
            variable.
          column_widths -- sequence of 'lcg.Unit's defining widths of columns, it
            must have the same number of elements and in the same order as
            table columns.  If any of the elements is 'None', the width of the
            corresponding column is to be determined automatically.
            Alternatively the whole 'column_widths' value may be 'None' to
            determine widths of all the columns automatically.
          bars -- sequence of vertical bars positions, integers.  The position
            before the first column is numbered 0, the next position is 1 and
            the position after the last column is numbered N where N is the
            number of columns in the table.
          compact -- If True, suppress default padding in all table cells
            (including headings).  Use containers to add custom padding.  Only
            implemented in PDF output.
          transformations -- permitted table transformations; currently used
            only in Braille backend.  It's a sequence containing any of the
            following strings: 'facing' (table may be spread across facing
            pages), 'transpose' (table may be transposed), 'row-expand' (table
            may be expanded by rows), 'column-expand' (table may be expanded by
            columns), 'split' (table may be vertically split into several
            narrower tables).

        """
        assert title is None or isinstance(title, basestring)
        assert isinstance(long, bool), long
        assert column_widths is None or isinstance(column_widths, (tuple, list)), column_widths
        assert isinstance(bars, (tuple, list)), bars
        assert isinstance(compact, bool), compact
        self._title = title
        self._long = long
        self._column_widths = column_widths
        self._bars = bars
        self._compact = compact
        self._transformations = transformations
        super(Table, self).__init__(content, **kwargs)

    def title(self):
        """Return the value of 'title' as passed to the constructor."""
        return self._title

    def long(self):
        """Return the value of 'long' as passed to the constructor."""
        return self._long

    def column_widths(self):
        """Return the value of 'column_widths' as passed to the constructor."""
        return self._column_widths

    def bars(self):
        """Return positions of vertical bars.

        See '__init__()' documentation for information about the positions.

        """
        return self._bars

    def compact(self):
        """Return the value of 'compact' passed to the constructor."""
        return self._compact

    def transformations(self):
        """Return the value of 'transformations' as passed to the constructor."""
        return self._transformations


class Section(Container):
    """Section wraps the subordinary contents into an inline section.

    Section is very similar to a 'Container', but there are a few
    differences:

      * Every section has a title, which appears in the output document as a
        heading.

      * Sections can be used as link targets.  You can define section id
        explicitly or it is assigned automatically.  The automatically assigned
        ids are based on section order and hierarchy, so they will not change
        across several LCG invocations as long as the hierarchy remains
        unchanged.

      * Sections are numbered.  Each section knows its number within its
        container.

    """
    _ID_PREFIX = 'sec'

    def __init__(self, title, content, heading=None, id=None, anchor=None,
                 descr=None, in_toc=True, **kwargs):
        """Arguments:

          title -- plain text section title; basestring
          content -- the actual content wrapped into this section as a
            sequence of 'Content' instances in the order in which they should
            appear in the output
          heading -- content to be used as section heading.  By default (when
            None), the content is created automatically as TextContent(title),
            but you may pass any lcg.Content instance when some more fancy
            content is desired.
          anchor -- deprecated - use 'id' instead.
          in_toc -- a boolean flag indicating whether this section is supposed
            to be included in the Table of Contents

          Other keyword arguments are defined by parent classes.

        """
        if anchor:
            assert id is None
            id = anchor
        assert isinstance(title, basestring), title
        assert heading is None or isinstance(heading, Content), heading
        assert isinstance(in_toc, bool), in_toc
        self._title = title
        self._in_toc = in_toc
        self._descr = descr
        self._heading = heading or TextContent(title)
        super(Section, self).__init__(content, id=id, **kwargs)

    def section_path(self):
        """Return the sequence of parent sections in the container hierarchy.

        The returned value is a list of 'Section' instances, which are above
        this section in the hieararchy.  The document's top level section
        appears as the first and 'self' is always the last element of the list.

        """
        return [c for c in self.container_path() if isinstance(c, Section)]

    def title(self):
        """Return the section title as a basestring."""
        return self._title

    def descr(self):
        """Return a breif (but more verbose than title) description as a basestring or None."""
        return self._descr

    def heading(self):
        """Return section heading as a 'Heading' instance.

        Return the content passed as 'heading' argument wrapped in the
        'Heading' element (denoting the actual section heading level depending
        on section position in the document).

        """
        return Heading(self._heading, level=len(self.section_path()) + 1)

    def in_toc(self):
        """Return true if the section is supposed to appear in TOC."""
        return self._in_toc

    def id(self):
        """Return unique section identifier as a string.

        If 'id' was passed to the constructor, it is used.  Otherwise the
        identifier is automatically generated.  The generated id is unique
        within the parent node and does not change if the section structure
        remains unchanged (external references should work throughout multiple
        exports in this case).

        """
        def section_number(x):
            container = x.container()
            while container and not isinstance(container, Section) and container.container():
                container = container.container()
            if container:
                return list(container.sections()).index(x) + 1
            else:
                return 1
        if self._id is None:
            path = self.section_path()
            if len(path) >= 2:
                self._id = path[-2].id() + '.' + unistr(section_number(self))
            else:
                numbers = [unistr(section_number(x)) for x in path]
                self._id = self._ID_PREFIX + '.'.join(numbers)
        return self._id

    # Temporary backwards compatibility.
    anchor = id


class TableOfContents(Content):
    """A table of contents which lists the content subtree.

    This element works as a sort of macro, which expands to the hierarchical
    listing of content nodes and their subcontent (sections) on the output.

    The items actually present in the table of contents depend on the content
    itself (i.e. hidden sections are omitted automatically) and on the arguments
    passed to the 'TableOfContents' constructor (limiting the hierachy depth,
    selection of the root item of the hierarchy, etc).

    See also the 'NodeIndex' class if you need to display a hierarchy of nodes.

    """
    _TOC_ITEM_TYPE = Content

    def __init__(self, item=None, title=None, depth=None, detailed=True, **kwargs):
        """Arguments:
          item -- the place where to start in the content hierarchy tree as a
            'Container' instance instance or None.  If not None, the table of
            contents will start from that point -- the contained sections (see
            'Container.sections()') will become top level items in the table.
            If None, the container of given 'TableOfContents' element itself is
            used so the result is a local Table of Contents at given place.
            See also 'Section' documentation for more information how section
            hierarchy representation is built.
          title -- the title of the index as a string or unicode
          depth -- hierarchy depth limit as an integer or 'None' for unlimited depth
          detailed -- boolean indicating whether the whole 'Content' hierarchy
            ('True') or only 'lcg.ContentNode' hierarchy ('False') of the leaf
            nodes of the node tree will be included in the index.  This argument
            has no effect when 'item' is a 'Container' instance.

          All other arguments have the same meaning as in the parent class constructor.

        """
        assert item is None or isinstance(item, self._TOC_ITEM_TYPE)
        assert title is None or isinstance(title, basestring)
        assert depth is None or isinstance(depth, int)
        assert isinstance(detailed, bool)
        self._item = item
        self._title = title
        self._depth = depth
        self._detailed = detailed
        super(TableOfContents, self).__init__(**kwargs)

    def _root_item(self):
        """Return the position in the hierarchy where to start the table of contents."""
        item = self._item
        if not item:
            # Create a local table of contens automatically (taking this elements container as a
            # start point).
            assert isinstance(self._container, Container), self._container
            item = self._container
        return item

    def title(self):
        """Return the value of 'title' as passed to the constructor."""
        return self._title

    def items(self, lang):
        """Return the hierarchy of items present in the table of contents.

        The returned value is a recursive structure.  It is a list of pairs
        (tuples) ITEM, SUBITEMS, where ITEM is always either 'Section' or
        'lcg.ContentNode' instance and SUBITEMS is a nested list of the same
        type if given item has subitems displayed in the table of contents.
        Otherwise SUBITEMS is an empty list.

        The method handles hidden items, depth limit and other conditions
        internally, so that the caller doesn't need to care which items belong
        to the table of contents.  All returned items should be displayed.

        """
        def subitems(item, depth=None):
            if depth is not None:
                if depth <= 0:
                    return []
                depth -= 1
            if isinstance(item, lcg.ContentNode):
                items = [node for node in item.children() if not node.hidden()]
            else:
                items = []
            if len(items) == 0 and self._detailed:
                if isinstance(item, (tuple, list)):
                    items = item
                else:
                    if isinstance(item, lcg.ContentNode):
                        sections = item.content(lang).sections()
                    else:
                        sections = item.sections()
                    items = [s for s in sections if s.in_toc()]
            return [(subitem, subitems(subitem, depth)) for subitem in items]
        return subitems(self._root_item(), depth=self._depth)


class NodeIndex(TableOfContents):
    """A table of contents which lists the node subtree of the current node.

    This class is just a specific type of 'TableOfContents', which by default
    starts at the parent node of the content where it is used and which by
    default displays only nodes, not their inner conent (detailed=False).

    """
    _TOC_ITEM_TYPE = lcg.ContentNode

    def __init__(self, title=None, node=None, depth=None, detailed=False):
        super(NodeIndex, self).__init__(node, title=title, depth=depth, detailed=detailed)

    def _root_item(self):
        return self._item or self.parent()


class RootIndex(NodeIndex):
    """'NodeIndex' starting from the top level node of the whole tree."""

    def _root_item(self):
        return self.parent().root()


class NoneContent(Content):
    """Deprecated.

    Intended for places where 'Content' is required but there is nothing to put
    in.  It is, however, actually useless, since 'Content' may be used for the
    same purpose.

    """
    pass


class SetVariable(Content):
    """Pseudo-content serving for setting node global variables.

    This content doesn't produce any output, it just sets a node global
    variable value.  It is used by structured text parser to set global
    variables at proper places.

    """

    def __init__(self, name, value, **kwargs):
        """
        Arguments:

          name -- name of the variable, string
          value -- value of the variable, 'Content' instance

        """
        assert isinstance(name, basestring), name
        assert isinstance(value, Content), value
        self._name = name
        self._value = value
        super(SetVariable, self).__init__(**kwargs)

    def name(self):
        """Return name of the variable."""
        return self._name

    def value(self):
        """Return value of the variable as a 'Content' instance."""
        return self._value


class Substitution(Content):
    """Variable to be substituted by the actual value on export."""

    def __init__(self, name, markup=None, **kwargs):
        """
        Arguments:

          name -- name of the variable, string, without $, may contain dots for
            nested variable lookup, eg. 'x.y'.
          markup -- original source markup (to be substituted if the value
            doesn't exist), eg. '$x.y' or '${x.y}'.  If None, '$'+name is
            supposed.

        """
        assert isinstance(name, basestring), name
        assert markup is None or isinstance(markup, basestring), markup
        self._name = name
        self._markup = markup or '$' + name
        super(Substitution, self).__init__(**kwargs)

    def name(self):
        """Return name of the variable."""
        return self._name

    def markup(self):
        """Return source text representation of the variable."""
        return self._markup


class Figure(Container):
    """A container that can have a caption, typicaly for images"""

    LEFT = 'left'
    RIGHT = 'right'

    def __init__(self, content, caption=None, align=None, **kwargs):
        """Arguments:

        caption - caption text as lcg.Content or a series of lcg.Content objects

        align - alignment and text wrapping around this container,
                possible values are 'left', 'right' or None
        """
        super(Figure, self).__init__(content, **kwargs)
        self._caption = caption
        self._align = align

    def caption(self):
        return self._caption

    def align(self):
        return self._align


class MathML(Content):
    """Representation of MathML content for inclusion in LCG documents.

    It works by making an instance containing a unicode representation of the
    MathML object.  You can access the MathML content either by using
    'content()' method which returns the unicode or by using 'dom_content()'
    which returns a parsed DOM structure to work with.

    It is expected that the MathML content is a presentation form of MathML 3.

    """
    class EntityHandler(object):
        """Entity dictionary to be used in 'tree_content()' method.

        This class provides just trivial implementation which always returns
        the entity name itself.  Subclasses (or different) classes may provide
        other mechanisms, e.g. mapping the entities to the corresponding
        Unicode characters.

        """

        def __getitem__(self, key):
            return key

        def get(self, key, default=None):
            try:
                return self[key]
            except KeyError:
                return default

    def __init__(self, content):
        """
        Arguments:

          content -- the MathML content represented as a MathML XML unicode

        """
        super(MathML, self).__init__()
        assert isinstance(content, basestring), content
        self._content = content

    def content(self):
        """Return the XML unicode content given in the constructor."""
        return self._content

    def _str_content(self):
        content = self._content
        # Unfortunately even the etree parser doesn't work very well with
        # "custom" entities -- it discards them in attributes.  So we have to
        # expand the entities manualy.
        regexp = re.compile('&([a-zA-Z]+);')
        i = 0
        while True:
            match = regexp.search(content[i:], re.M)
            if not match:
                break
            entity = match.group(1)
            start, end = match.span()
            if entity in ('amp', 'lt', 'gt', 'quot', 'apos', 'bsol', 'newline',):
                i += end
            else:
                from lcg.export.mathml import entities
                expansion = entities.get(entity)
                if expansion is None:
                    i += end
                else:
                    content = content[:i + start] + expansion + content[i + end:]
                    i += start + len(expansion)
        content = content.encode('utf-8')
        return content

    def _dom_content(self, element):
        from xml.etree import ElementTree
        top_elements = element.getElementsByTagName('math')
        assert len(top_elements) == 1
        top = top_elements[0]
        tree = ElementTree.Element(top.tagName)

        def export(parent_tree, node):
            node_type = node.nodeType
            if node_type == node.ELEMENT_NODE:
                tree = ElementTree.SubElement(parent_tree, node.tagName)
                attributes = node.attributes
                for i in range(attributes.length):
                    a = attributes.item(i)
                    tree.set(a.name, a.value)
                for n in node.childNodes:
                    export(tree, n)
            elif node_type == node.TEXT_NODE or node_type == node.ENTITY_NODE:
                value = node.nodeValue.strip()
                if value:
                    assert not parent_tree.text, node
                    parent_tree.text = node.nodeValue
            elif node_type == node.COMMENT_NODE:
                pass
            else:
                raise Exception('Unhandled node type', node, node.nodeType)
        for n in top.childNodes:
            export(tree, n)
        return tree

    def _dom_tree_content(self):
        # This can't handle entity references (e.g. &PlusMinus;).
        from xml.dom.minidom import parseString
        return self._dom_content(parseString(self._str_content()))

    def _tree_content(self, entity_dictionary):
        from xml.etree import ElementTree
        import io
        parser = ElementTree.XMLParser()
        if sys.version_info[0] == 2:
            # TODO: This doesn't work in Python 3.  The only way of getting it to work
            # seems to be defining all entities in a DOCTYPE  as suggested in:
            # https://stackoverflow.com/questions/35591478/ +
            # how-to-parse-html-with-entities-such-as-nbsp-using-builtin-library-elementtree
            # But is this really needed?  Valid MathML entities are already defined.
            # Do we need to allow invalid entities for some reasons?
            parser.parser.UseForeignDTD(True)
            if entity_dictionary is None:
                entity_dictionary = self.EntityHandler()
            parser.entity = entity_dictionary
        etree = ElementTree.ElementTree()
        content = self._str_content()
        try:
            tree = etree.parse(io.BytesIO(content), parser=parser)
        except ElementTree.ParseError as e:
            raise lcg.ParseError("Error when parsing MathML element", e, content)
        regexp = re.compile('{.*}')
        for e in tree.iter():
            match = regexp.match(e.tag)
            if match:
                e.tag = e.tag[match.end():]
        return tree

    def _transform_content(self, math):
        from xml.etree import ElementTree
        math = copy.copy(math)
        for node in math.getiterator():
            children = list(node)
            for i in range(len(children)):
                c = children[i]
                if c.tag == 'semantics':
                    c_children = list(c)
                    if c_children:
                        node.insert(i, c_children[0])
                        node.remove(c)
                    else:
                        # Not valid, but let's handle it some way
                        c.clear()
                        c.tag = 'mrow'
        for node in math.getiterator('mfenced'):
            opening = node.attrib.get('open', '(')
            closing = node.attrib.get('close', ')')
            separators = node.attrib.get('separators', ',').split()
            children = list(node)
            node.clear()
            node.tag = 'mrow'
            if opening:
                ElementTree.SubElement(node, 'mo', dict(fence='true')).text = opening
            i = 0
            for c in children:
                if separators and i > 0:
                    s = separators[-1] if i > len(separators) else separators[i - 1]
                    ElementTree.SubElement(node, 'mo', dict(separator='true')).text = s
                node.append(c)
                i += 1
            if closing:
                ElementTree.SubElement(node, 'mo', dict(fence='true')).text = closing
        return math

    def tree_content(self, entity_dictionary=None, transform=False, top_only=False):
        """Return a parsed 'xml.etree.Element' instance of the math content.

        Arguments:

          entity_dictionary -- an object providing common dictionary access
            methods, 'get()' and '__getitem__()', mapping entity names to
            values.  There are no requirements on the returned values, they are
            completely implementation dependent.  Typical values may be
            unchanged entity names or unicodes corresponding to the given
            entities.  If not given, 'MathML.EntityHandler' instance is used.
          transform -- iff true then expand elements which can be expressed
            using other elements (e.g. mfenced)
          top_only -- if true then check that the top element is 'math'
            element, otherwise look for 'math' element in the tree content

        """
        tree = self._tree_content(entity_dictionary)
        if top_only:
            if tree.tag != 'math':
                raise Exception("Invalid MathML top element", tree)
        else:
            try:
                tree = tree.getiterator('math').pop()
            except IndexError:
                raise Exception("No math element found", tree)
        if transform:
            tree = self._transform_content(tree)
        return tree


class InlineSVG(Content):
    """Generic SVG content for inclusion in LCG documents.

    SVG may be included in HTML and PDF backends.  Requires svglib when PDF
    output is used.

    """
    def __init__(self, content, *args, **kwargs):
        """Initialize the instance.

        Arguments:

          content -- the actual SVG content of this element as a string, bytes
            or a function of one argument (exporter context) returning the SVG
            as string or bytes.
          *args -- additional positional arguments passed to the export
            function (given in 'content').  No arguments are allowed when
            'content' is string or bytes.
          **kwargs -- keyword arguments for parent class constructor.

        """
        assert isinstance(content, (str, bytes)) or callable(content), content
        self._content = content
        self._export_args = args
        super(InlineSVG, self).__init__(**kwargs)

    def svg(self, context):
        """Return the SVG as bytes."""
        content = self._content
        if callable(content):
            content = content(context, *self._export_args)
        if not isinstance(content, bytes):
            content = content.encode('utf-8')
        return content

# Convenience functions for simple content construction.

def coerce(content, formatted=False):
    """Coerce the argument into an LCG content element.

    Arguments:

      content -- can be a sequence, string or a Content instance.  A sequence
        is turned to a 'Container' of the items.  Moreover each item is coerced
        recursively and 'None' items are omitted.  A string is parsed for
        inline markup or simply turned into 'TextContent' instance depending on
        the 'formatted' argument.  A 'Content' instance is returned as is.  Any
        other argument raises AssertionError.

      formatted -- a boolean flag indicating how strings should treated.  If
        False (the default) strings are simply turned into 'TextContent'
        instances.  If True, strings are parsed for inline markup using
        'lcg.Parser.parse_inline_markup()'.  Applies recursively if a sequence
        is passed as the 'content' argument.

    """
    assert isinstance(formatted, bool)
    if isinstance(content, (list, tuple)):
        container = Container
        items = []
        for item in content:
            if item is not None:
                if not isinstance(item, Content):
                    item = coerce(item, formatted=formatted)
                items.append(item)
        return container(items)
    elif isinstance(content, basestring):
        if formatted:
            from lcg import Parser
            return Parser().parse_inline_markup(content)
        else:
            return TextContent(content)
    else:
        assert isinstance(content, Content), ('Invalid content', content,)
        return content


def join(items, separator=' '):
    """Coerce all items and put the coerced separator in between them."""
    sep = coerce(separator)
    result = []
    for item in items:
        if result:
            result.append(sep)
        result.append(coerce(item))
    return coerce(result)


def link(target, label=None, type=None, descr=None):
    """Return a 'Link' instance.

    Arguments:

      target -- link target.  It can be a direct URI as a string or unicode
        instance or any referable content element, such as 'Section',
        'lcg.ContentNode', 'lcg.Resource' or 'Link.ExternalTarget'.
      label -- link label is mandatory when the target is a direct URI (string
        or unicode) and optional for LCG content element targets.  In this case
        it just overrides the default title of the refered object.
      type -- mime type specification of the refered object.
      descr -- additional description of the link target.  Only applicable when
        the link target is a direct URI.

    """
    if isinstance(target, basestring):
        assert label is not None
        target = Link.ExternalTarget(target, None, descr=descr)
    else:
        assert isinstance(target, (lcg.ContentNode, Section, Link.ExternalTarget, lcg.Resource)), \
            target
        assert descr is None
    return Link(target, label=label, type=type)


def dl(items, formatted=False):
    """Create a 'DefinitionList' from a sequence of (TERM, DESCRIPTION) pairs.

    Each term and description in the sequence is automatically coerced into a content instance, but
    only the description is treated as formatted.

    """
    return DefinitionList([(coerce(term), coerce(descr, formatted=formatted))
                           for term, descr in items])


def ul(items, formatted=False):
    """Create an 'ItemizedList' by coercing given sequence of items."""
    return ItemizedList([coerce(item, formatted=formatted) for item in items])


def ol(items, formatted=False, alpha=False):
    """Create an 'ItemizedList' by coercing given sequence of items."""
    return ItemizedList([coerce(item, formatted=formatted) for item in items],
                        order=(alpha and ItemizedList.LOWER_ALPHA or ItemizedList.NUMERIC))


def fieldset(pairs, formatted=False):
    """Create a 'FieldSet' out of given sequence of (LABEL, VALUE) pairs.

    Both label and value are coerced, but only value is treated as formatted.

    """
    fields = [(coerce(label), coerce(value, formatted=formatted)) for label, value in pairs]
    return FieldSet(fields)


def sec(title, content, heading=None, name='default-section', **kwargs):
    """Create a 'Section' by coercing all content."""
    formatted = kwargs.pop('formatted', False)
    return Section(title=title, heading=coerce(heading, formatted=formatted) if heading else None,
                   content=[coerce(item, formatted=formatted) for item in content],
                   name=name, **kwargs)


def _container(container, items, formatted=False, **kwargs):
    return container([coerce(item, formatted=formatted) for item in items], **kwargs)


def p(*items, **kwargs):
    """Create a 'Paragraph' by coercing all arguments."""
    return _container(Paragraph, items, **kwargs)


def strong(*items, **kwargs):
    """Create a 'Strong' instance by coercing all arguments."""
    return _container(Strong, items, **kwargs)


def em(*items, **kwargs):
    """Create an 'Emphasized' instance by coercing all arguments."""
    return _container(Emphasized, items, **kwargs)


def u(*items, **kwargs):
    """Create an 'Underlined' instance by coercing all arguments."""
    return _container(Underlined, items, **kwargs)


def code(*items, **kwargs):
    """Create an 'Code' instance by coercing all arguments."""
    return _container(Code, items, **kwargs)


def cite(*items, **kwargs):
    """Create an 'Citation' instance by coercing all arguments."""
    return _container(Citation, items, **kwargs)


def container(*items, **kwargs):
    return _container(Container, items, **kwargs)


def br():
    return NewLine()


def hr():
    return HorizontalSeparator()


def pre(text, **kwargs):
    """Create an 'PreformattedText' instance by coercing all arguments."""
    return PreformattedText(text, **kwargs)


def abbr(text, descr, **kwargs):
    """Create an 'Abbreviation' instance."""
    return Abbreviation(text, descr, **kwargs)
