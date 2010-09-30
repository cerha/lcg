# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007, 2008, 2009, 2010 Brailcom, o.p.s.
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
content to a 'ContentNode' instance to be able to export it.

Please note the difference between the hierarchy of content within one node and
the hierarchy of the nodes themselves.

"""

from lcg import *

_ = TranslatableTextFactory('lcg')


class Presentation(object):
    """Set of presentation properties.

    Using instance of this class, you can provide explicit presentation
    information to some LCG content elements.  Note that it is often not
    desirable to define presentation explicitly.  You need to define
    presentation this way when you prepare a printed document with fixed
    structure, on the other hand when preparing a general HTML page you should
    use variable external stylesheets instead.

    This class serves just as a storage of presentation properties, it does not
    provide any special methods.  All of the attribute values can be set to
    'None' meaning there is no presentation requirement for that attribute and
    it can be taken from another active presentation.

    """
    font_size = None
    "Font size relative to the current font size (1.0 is the same size), float."
    font_name = None
    "Name of the font to use, e.g. 'Free' or 'DejaVu', string."
    font_family = None
    "Font family to be used for typesetting text, one of 'FontFamily' constants."
    heading_font_family = None
    "Font family to be used for typesetting headings, one of 'FontFamily' constants."
    noindent = None
    "If true, don't indent first lines of paragraphs."
    bold = None
    "True when bold font face should be used, False otherwise."
    italic = None
    "True when italic font face should be used, False otherwise."
    boxed = None
    "'True' when the content should be surrounded by a box."
    separator_height = None
    """Height of lines separating objects, 'Unit'.
    It currently works only for row separators in tables.
    """
    separator_width = None
    """Width of lines separating objects, 'Unit'.
    It currently works only for column separators in tables.
    """
    separator_margin = None
    """Amount of space between objects, 'Unit'.
    It currently works only for spaces between table rows.
    """
    header_separator_height = None
    """Height of line separating headers from content, 'Unit'.
    It currently works only for tables.
    """
    header_separator_margin = None
    """Amount of space separating headers from content, 'Unit'.
    It currently works only for tables.
    """
    left_indent = None
    """Amount of space to put on left of the object, 'Unit'."""
    line_spacing = None
    """Distance between line bases, 'Unit'."""
    
    
class Content(object):
    """Generic base class for all types of content.

    One instance always makes a part of one document/node -- it cannot be split
    over multiple output nodes.  On the other hand, one node usually consists
    of multiple 'Content' instances (elements).  Each content element may be
    contained in another content element (see the 'Container' class) and thus
    they make a hierarchical structure.

    """
    _ALLOWED_CONTAINER = None
    
    def __init__(self, lang=None, **kwargs):
        """Initialize the instance.

        Arguments:

          lang -- content language as an ISO 639-1 Alpha-2
            language code (lowercase).

        """
        self._parent = None
        self._container = None
        self._lang = lang
        super(Content, self).__init__()
        
    def _container_path(self):
        path = [self]
        while path[0]._container is not None:
            path.insert(0, path[0]._container)
        return tuple(path)

    def sections(self, context):
        """Return the contained sections as a sequence of 'Section' instances.

        This method allows creation of tables of contents and introspection of
        content hierarchy.
        
        An empty sequence is returned in the base class.  The derived classes,
        however, can override this method to return the sequence of contained
        subsections.

        The argument 'context' ('lcg.Exporter.Context' instance) must be passed
        because the returned value may depend in on the current export context
        (for example 'ContentVariants' depends on current export language).

        """
        return ()
        
    def set_container(self, container):
        """Set the parent 'Container' to 'container'.

        This method is normally called automatically by the container constructor to inform the
        contained 'Content' elements about their position in content hierarchy.  You only need to
        care about calling this method if you implement your own 'Container' class and don't call
        the default constructor for all the contained elements for some reason.  Otherwise it is
        always called automatically by LCG behind the scenes.

        """
        if __debug__:
            cls = self._ALLOWED_CONTAINER or Container
            assert isinstance(container, cls), "Not a '%s' instance: %s" % (cls.__name__,container)
        self._container = container

    def set_parent(self, node):
        """Set the parent 'ContentNode' to 'node'.

        This method is called automatically by the 'ContentNode' constructor when the content is
        assigned to a node.  The parent node is normally not known (and not needed) in the time of
        content construction.  It is, however, needed in the export time, so you will need to call
        it manually before attempting to export any content which was not assigned to a
        'ContentNode' before.  Content which is contained within a container will automatically
        determine its parent node recursively so it is only needed to set the parent explicitly of
        top level elements or for unbound elements.

        """
        assert isinstance(node, ContentNode), \
               "Not a 'ContentNode' instance: %s" % node
        assert self._parent is None or self._parent is node, \
               "Reparenting not allowed: %s -> %s" % (self._parent, node)
        self._parent = node

    def parent(self):
        """Return the parent 'ContentNode' of this content element."""
        parent = self._parent or self._container and self._container.parent()
        assert parent is not None, "Parent unknown: %s" % self
        return parent

    def lang(self, inherited=True):
        """Return the content language as lowercase ISO 639-1 Alpha-2 language code.

        Arguemnts:
        
          inherited -- iff True, the language will be determined from the
            parent element in the hierarchy if this element doesn't define
            'lang' explicitly.  When False, the value of 'lang' passed to the
            constructor is returned.

        """
        lang = self._lang
        if lang is None and inherited and self._container:
            lang = self._container.lang()
        return lang

    def export(self, context):
        """Return the formatted content in an output specific form.

        The return value can later be processed by 'Exporter' methods.

        Arguments:

          context -- formatting context as a 'Exporter.Context' instance
            created and returned by 'Exporter.context' method

        """
        return context.exporter().export_element(context, self)
    #return context.exporter().escape('')

    
class HorizontalSeparator(Content):
    """Horizontal separator of document section.

    Typically it may be a page separator in paged documents or a horizontal
    separator in documents without pages.

    """
    pass


class NewPage(Content):
    """New page starts here."""
    pass


class PageNumber(Content):
    """Current page number.

    The page number is generated as an ordinal arabic number starting from one.

    This content may be used only inside page headers and footers.

    """
    def __init__(self, total=False):
        """
        Arguments:

          total -- iff true, output not only the page number, but also the
            total number of pages

        """
        self._total = total
        
    def total(self):
        """Return the value of 'total' as passed to the constructor."""
        return self._total


class HSpace(Content):
    """Horizontal space of given size.

    This should be used only in places where explicit space is needed.  In many
    cases better means such as higher level elements, alignment or style sheets
    can be used.

    """
    def __init__(self, size):
        """
        @type: L{Unit}
        @param: Size of the space.
        """
        assert isinstance(size, Unit), size
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


class TextContent(Content):
    """A simple piece of text."""

    def __init__(self, text, **kwargs):
        """Initialize the instance.

        Arguments:

          text -- the actual text content of this element as a string or
            unicode
          kwargs -- keyword arguments for parent class constructor.

        """
        assert isinstance(text, (str, unicode)), text
        super(TextContent, self).__init__(**kwargs)
        self._text = text

    def __str__(self):
        text = str(self._text).strip()
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


class HtmlContent(TextContent):
    """LCG content class for wrapping already exported HTML text.

    This class allows embedding HTML content directly into the LCG content
    hierarchy.  Its export in HTML is a noop, but it is only implemented for the
    HTML output.  Attempt to export this type of content to any other target
    format will lead to an error.

    At the same time, this class demonstrates a content element, which exports
    itself actively and doesn't rely on the exporter as the other generic
    elements defined in this module.
    
    """
    def export(self, context):
        assert isinstance(context.exporter(), HtmlExporter), \
               "Only HTML export is supported for this element."
        return self._text

    
class FormattedText(TextContent):
    """Formatted text using a simple wiki-based inline markup.

    See 'MarkupFormatter' for more information about the formatting rules.
    
    """
    pass

# Backwards compatibility alias.        
WikiText = FormattedText

    
class PreformattedText(TextContent):
    """Preformatted text."""
    pass

class Anchor(TextContent):
    """Target of a link (an anchor)."""
    
    def __init__(self, anchor, text='', **kwargs):
        """Arguments:

          anchor -- name of the link target anchor as a string.
          text -- text of the target place as a string or unicode.

        """
        assert isinstance(anchor, str)
        self._anchor = anchor
        super(Anchor, self).__init__(text, **kwargs)

    def anchor(self):
        """Return link target name given in the constructor."""
        return self._anchor


class InlineImage(Content):
    """Image embedded inside the document.

    It is unspecified whether the image is floating or to be put directly into
    the place of invocation.

    """
    
    LEFT = 'left'
    RIGHT = 'right'
    TOP = 'top'
    BOTTOM = 'bottom'
    MIDDLE = 'middle'
    
    def __init__(self, image, title=None, descr=None, name=None, align=None, size=None):
        """Arguments:

          image -- 'Image' resource instance.
          title -- image title as a string or unicode.  The
            title used for example as alternative text in HTML.
          descr -- image description a string or unicode.  Currently
            unused in HTML.
          name -- arbitrary name (string) identifying the image.  Used as CSS
            class name in HTML to allow individual image styling.
          align -- requested alignment of the image to the surrounding text;
            one of the constants 'InlineImage.LEFT', 'InlineImage.RIGHT',
            'InlineImage.TOP', 'InlineImage.BOTTOM' , 'InlineImage.MIDDLE' or
            'None'
          size -- image size in pixels as a tuple of two integers (WIDTH, HEIGHT)

        If 'title' or 'descr' is None, the title/description defined by the
        'Image' resource instance is used.

          
        """
        assert isinstance(image, Image), image
        assert title is None or isinstance(title, (str, unicode)), title
        assert descr is None or isinstance(descr, (str, unicode)), descr
        assert name is None or isinstance(name, (str, unicode)), name
        assert align in (None, self.LEFT, self.RIGHT, self.TOP, self.BOTTOM, self.MIDDLE), align
        assert size is None or isinstance(size, tuple), size
        self._image = image
        self._align = align
        self._title = title
        self._descr = descr
        self._name = name
        self._size = size
        super(InlineImage, self).__init__()

    def image(self):
        """Return the value of 'image' as passed to the constructor."""
        return self._image

    def title(self):
        """Return the value of 'title' as passed to the constructor."""
        return self._title
    
    def descr(self):
        """Return the value of 'descr' as passed to the constructor."""
        return self._descr
    
    def name(self):
        """Return the value of 'name' as passed to the constructor."""
        return self._name
    
    def align(self):
        """Return the value of 'align' as passed to the constructor."""
        return self._align
    
    def size(self):
        """Return the value of 'size' as passed to the constructor."""
        return self._size
    

class InlineAudio(Content):
    """Audio file embedded inside the document.

    For example in HTML, this might be exported as a play button using a
    Flash audio player.
    
    """
       
    def __init__(self, audio, title=None, descr=None, image=None, shared=True):
        """Arguments:

          audio -- 'Audio' resource instance.
          title -- audio file title as a string.
          descr -- audio file description as a string.
          image -- visual presentation image as an 'Image' resource instance or None.
          shared -- boolean flag indicating whether using a shared audio player is desired.

        If 'title' or 'descr' is None, the title/description defined by the
        resource instance is used.
        
        
        """
        assert isinstance(audio, Audio), audio
        assert isinstance(shared, bool)
        self._audio = audio
        self._title = title
        self._descr = descr
        self._image = image
        self._shared = shared
        super(InlineAudio, self).__init__()

    def audio(self):
        """Return the value of 'audio' as passed to the constructor."""
        return self._audio

    def title(self):
        """Return the value of 'title' as passed to the constructor."""
        return self._title
    
    def descr(self):
        """Return the value of 'descr' as passed to the constructor."""
        return self._descr
    
    def image(self):
        """Return the value of 'image' as passed to the constructor."""
        return self._image
    
    def shared(self):
        """Return the value of 'shared' as passed to the constructor."""
        return self._shared


class InlineVideo(Content):
    """Video file embedded inside the document.

    For example in HTML, this might be exported as an embedded video player.
    
    """
       
    def __init__(self, video, title=None, descr=None, image=None, size=None):
        """Arguments:

          video -- 'Video' resource instance.
          title -- video file title as a string.  
          descr -- video file description as a string.
          image -- video thumbnail image as an 'Image' resource instance or None.
          size -- video size in pixels as a tuple of two integers (WIDTH, HEIGHT)

        If 'title' or 'descr' is None, the title/description defined by the
        resource instance is used.
        
        """
        assert isinstance(video, Video), video
        self._video = video
        self._title = title
        self._descr = descr
        self._image = image
        self._size = size
        super(InlineVideo, self).__init__()

    def video(self):
        """Return the value of 'video' as passed to the constructor."""
        return self._video

    def title(self):
        """Return the value of 'title' as passed to the constructor."""
        return self._title
    
    def descr(self):
        """Return the value of 'descr' as passed to the constructor."""
        return self._descr
    
    def image(self):
        """Return the value of 'image' as passed to the constructor."""
        return self._image
    
    def size(self):
        """Return the value of 'size' as passed to the constructor."""
        return self._size


class InlineExternalVideo(Content):
    """Embedded video from external services such as YouTube or Vimeo

    For example in HTML, this might be exported as an embedded YouTube video
    player.
    
    """
    def __init__(self, service, video_id, title=None, descr=None, size=None):
        """Arguments:

          service -- string identifier of the video service.  The two currently
            supported services are 'youtube' and 'vimeo'.
          video_id -- string identifier of the video within the given service.
          size -- explicit video size in pixels as a tuple of two integers
            (WIDTH, HEIGHT) or None for the default size.
          
        """
        assert service in ('youtube', 'vimeo'), service
        assert isinstance(video_id, (str, unicode)), video_id
        assert size is None or isinstance(size, tuple), size
        self._service = service
        self._video_id = video_id
        self._title = title
        self._descr = descr
        self._size = size
        super(InlineExternalVideo, self).__init__()

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


class Container(Content):
    """Container of multiple parts, each of which is a 'Content' instance.

    Containers allow to build a hierarchy of 'Content' instances inside the
    scope of one node.  This is an addition to the hierarchy of the actual
    nodes (separate pages).

    All the contained (wrapped) content elements will be notified about the
    fact, that they are contained within this container and thus belong to the
    hierarchy.

    """
    _ALLOWED_CONTENT = Content
    _SUBSEQUENCES = False
    _SUBSEQUENCE_LENGTH = None
    
    def __init__(self, content, name=None, id=None, halign=None, valign=None, orientation=None,
                 presentation=None, **kwargs):
        """Initialize the instance.

        Arguments:
        
          content -- the actual content wrapped into this container as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.
          name -- optional string identifier which may be used as output
            presentation selector (for example as a 'class' attribute in HTML).
          id -- depracated, use 'name' instead.
          halign -- horizontal alignment of the container content; one of the
            'HorizontalAlignment' constants or 'None' (default alignment).
          valign -- vertical alignment of the container content; one of the
            'VerticalAlignment' constants or 'None' (default alignment).
          orientation -- orientation of the container content; one of the
            'Orientation' constants or 'None' (default orientation).
          presentation -- 'Presentation' instance defining various presentation
            properties; if 'None' then no explicit presentation for this container
            is defined.

        Note that 'halign', 'valign', 'orientation' and 'presentation'
        parameters may be ignored by some exporters.

        """
        super(Container, self).__init__(**kwargs)
        self._name = name or id
        assert name is None or isinstance(name, (str, unicode)), name
        assert halign is None or isinstance(halign, str), halign
        assert valign is None or isinstance(valign, str), valign
        assert orientation is None or isinstance(orientation, str), orientation
        assert presentation is None or isinstance(presentation, Presentation), presentation
        super(Container, self).__init__(**kwargs)
        if name:
            assert id == None, id
        else:
            # For backwards compatibility ('name' was formely named 'id').
            name = id
        self._name = name
        self._halign = halign
        self._valign = valign
        self._orientation = orientation
        self._presentation = presentation
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
            assert is_sequence_of(content, self._ALLOWED_CONTENT), \
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
            
    def sections(self, context):
        result = []
        for c in self._content:
            if isinstance(c, Section):
                result.append(c)
            elif isinstance(c, Container):
                result.extend(c.sections(context))
        return result
    
    def name(self):
        """Return the value of 'name' as passed to the constructor."""
        return self._name
    
    def halign(self):
        """Return the value of 'halign' as passed to the constructor."""
        return self._halign
    
    def valign(self):
        """Return the value of 'valign' as passed to the constructor."""
        return self._valign
    
    def orientation(self):
        """Return the value of 'orientation' as passed to the constructor."""
        return self._orientation
    
    def presentation(self):
        """Return the value of 'presentation' as passed to the constructor."""
        return self._presentation

SectionContainer = Container
"""Deprecated: Use 'Container' instead."""
    
class Paragraph(Container):
    """A paragraph of text, where the text can be any 'Content'."""
    pass


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
    LEFT = 'left'
    RIGHT = 'right'
    CENTER = 'center'

    def __init__(self, content, align=None, **kwargs):
        """Arguments:

          align -- requested cell content alignment, 'None' or one of the
            constants 'TableCell.LEFT', 'TableCell.RIGHT', 'TableCell.CENTER'
            or 'None' for the default alignment.

        """
        assert align in (None, self.LEFT, self.RIGHT, self.CENTER)
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

    def iterated(self):
        return self._iterated

    
class Table(Container):
    """Table is a container of 'TableRow' instances."""
    _ALLOWED_CONTENT = (TableRow, HorizontalSeparator,)

    def __init__(self, content, title=None, long=False, column_widths=None, bars=(), **kwargs):
        """Arguments:

          content -- sequence of 'TableRow' and 'HorizontalSeparator' instances
          title -- 'None' or table caption as a string or unicode
          long -- boolean indicating whether the table is long.  Long table is
            usually a table that may not fit on a single page.  Long tables may
            be handled in a different way, e.g. by splitting into several parts
            even when the table could fit on a new separate page or by using
            different column widths on each page when the column widths are
            variable.
          column_widths -- sequence of 'Unit's defining widths of columns, it
            must have the same number of elements and in the same order as
            table columns.  If any of the elements is 'None', the width of the
            corresponding column is to be determined automatically.
            Alternatively the whole 'column_widths' value may be 'None' to
            determine widths of all the columns automatically.
          bars -- sequence of vertical bars positions, integers.  The position
            before the first column is numbered 0, the next position is 1 and
            the position after the last column is numbered N where N is the
            number of columns in the table.

        """
        assert title is None or isinstance(title, (str, unicode))
        assert isinstance(long, bool), long
        assert column_widths is None or isinstance(column_widths, (tuple, list,)), column_widths
        assert isinstance(bars, (tuple, list,)), bars
        self._title = title
        self._long = long
        self._column_widths = column_widths
        self._bars = bars
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
        
    
class Section(Container):
    """Section wraps the subordinary contents into an inline section.

    Section is very similar to a 'Container', but there are a few
    differences:

      * Every section has a title, which appears in the output document as a
        heading.

      * Link targets (anchors) are attached to sections.  You may define the
        anchor name explicitly or it is assigned automatically.  The
        automatically assigned link targets are based on section order and
        hierarchy, so they will not change across several LCG invocations as
        long as the hierarchy remains unchanged.

      * Sections are numbered.  Each section knows its number within its
        container.

    """
    _ANCHOR_PREFIX = 'sec'
    
    def __init__(self, title, content, anchor=None, in_toc=True, **kwargs):
        """Arguments:

          title -- section title as a string
          content -- the actual content wrapped into this section as a
            sequence of 'Content' instances in the order in which they should
            appear in the output
          anchor -- section link target name as a string.  If 'None' (default)
            the link target name will be generated automatically.  If you want
            to refer to a section explicitly from somewhere, you will probably
            not rely on the default anchor name, so that's how you can define
            your own.  This also allows you to find a section by its anchor
            name in the hierarchy (see 'ContentNode.find_section()').
          in_toc -- a boolean flag indicating whether this section is supposed
            to be included in the Table of Contents
            
        """
        assert isinstance(title, (str, unicode)), title
        assert isinstance(anchor, (str, unicode)) or anchor is None, anchor
        assert isinstance(in_toc, bool), in_toc
        self._title = title
        self._in_toc = in_toc
        self._anchor = anchor
        self._backref = None
        super(Section, self).__init__(content, **kwargs)

    def path(self):
        """Return the sequence of parent sections in the container hierarchy.

        The returned value is a list of 'Section' instances, which are above
        this section in the hieararchy.  The document's top level section
        appears as the first and 'self' is always the last element of the list.

        """
        return [c for c in self._container_path() if isinstance(c, Section)]
    
    def section_number(self):
        """Return the number of this section within its container as int."""
        return list(self._container.sections(None)).index(self) + 1
    
    def title(self):
        """Return the section title as a string."""
        return self._title

    def in_toc(self):
        """Return true if the section is supposed to appear in TOC."""
        return self._in_toc
    
    def anchor(self):
        """Return the link target name of this section as a string.

        If 'anchor' was passed to the constructor, it is used.  Otherwise the
        anchor name is automatically generated.  The generated name is unique
        within the parent node and does not change when the section structure
        remains the same (links will work throughout multiple exports).

        """
        if self._anchor is None:
            path = self.path()
            if len(path) >= 2:
                self._anchor = path[-2].anchor() +'.'+ str(self.section_number())
            else:
                numbers = [str(x.section_number()) for x in path]
                self._anchor = self._ANCHOR_PREFIX + '.'.join(numbers)
        return self._anchor

    def create_backref(self, node):
        """Create a back reference anchor for the section and return it as a string.

        Arguments:
          node -- the parent node of the table of contents for which the back
            reference should be created.

        Back reference is a reference leading from the section heading to the
        corresponding link in the table of contents.
        
        Just one back reference target on one page is allowed.  Links on other
        pages are not back referenced.  Thus if 'node' is not section's parent
        or if a back references was already created, the method retorns 'None'.

        Back references may also be disabled in configuration.  In this case
        'None' is always returned.

        """
        if node is self.parent() and self._backref is None and config.allow_backref:
            self._backref = "backref-" + self.anchor()
            return self._backref
        else:
            return None
    
    def backref(self):
        """Return the anchor name if a back reference was previously created successfully."""
        return self._backref


class TableOfContents(Content):
    """A table of contents which lists the content subtree.

    This element works as a sort of macro, which expands to the hierarchical
    listing of content nodes and their subcontent (sections) on the output.

    The items actually present in the table of contents depend on the content
    itself (i.e. hidden sections are omitted automatically) and on the arguments
    passed to the 'TableOfContents' constructor (limiting the hierachy depth,
    selection of the root item of the hierarchy, etc).

    """
    _TOC_ITEM_TYPE = Content
    def __init__(self, item=None, title=None, depth=None, detailed=True, **kwargs):
        """Arguments:
        
          item -- the place where to start in the content hierarchy tree as a
            'Container' instance, 'ContentNode' instance or None.  When a
            'Container' is used, the table of contents will contain its sections
            (see 'Container.sections()').  'ContentNode' may be used to display
            a node hierarchy and 'None' means to start at the container of given
            'TableOfContents' instance (a local Table of Contents).  See also
            'Section' documentation for more information how section hierarchy
            representation is built.
          title -- the title of the index as a string or unicode
          depth -- hierarchy depth limit as an integer or 'None' for unlimited depth
          detailed -- boolean indicating whether the whole 'Content' hierarchy
            ('True') or only 'ContentNode' hierarchy ('False') of the leaf
            nodes of the node tree will be included in the index.  This argument
            has no effect when 'item' is a 'Container' instance.
            
          All other arguments have the same meaning as in the parent class constructor.
        
        """
        assert item is None or isinstance(item, self._TOC_ITEM_TYPE)
        assert title is None or isinstance(title, (str, unicode))
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
            assert isinstance(self._container, Container)
            item = self._container
        return item

    def _items(self, context, item, depth=None):
        if depth is not None:
            if depth <= 0:
                return ()
            depth -= 1
        items = ()
        if isinstance(item, ContentNode):
            items = [node for node in item.children() if not node.hidden()]
        if len(items) == 0 and self._detailed:
            if isinstance(item, (tuple, list)):
                items = item
            else:
                items = [s for s in item.sections(context) if s.in_toc()]
        if len(items) == 0:
            return ()
        return [(i, self._items(context, i, depth)) for i in items]

    def title(self):
        """Return the value of 'title' as passed to the constructor."""
        return self._title

    def items(self, context):
        """Return the hierarchy of items present in the table of contents.

        The returned value is a recursive structure.  It is a sequence of pairs
        (tuples) ITEM, SUBITEMS, where ITEM is always either 'Section' or
        'ContentNode' instance and SUBITEMS is a nested sequence of the same
        type if given item has subitems displayed in the table of contents.
        Otherwise SUBITEMS is an empty sequence.

        The method handles hidden items, depth limit and other conditions
        internally, so that the caller doesn't need to care which items belong
        to the table of contents.  All returned items should be displayed.

        """
        return self._items(context, self._root_item(), depth=self._depth)
    
    
class NodeIndex(TableOfContents):
    """A table of contents which lists the node subtree of the current node.

    This class is just a specific type of 'TableOfContents', which by default
    starts at the parent node of the content where it is used and which by
    default displays only nodes, not their inner conent (detailed=False).
    
    """
    _TOC_ITEM_TYPE = ContentNode

    def __init__(self, title=None, node=None, depth=None, detailed=False):
        super(NodeIndex, self).__init__(node, title=title, depth=depth, detailed=detailed)

    def _root_item(self):
        return self._item or self.parent()
        

class RootIndex(NodeIndex):
    """'NodeIndex' starting from the top level node of the whole tree."""
    
    def _root_item(self):
        return self.parent().root()

    
    

class Link(Container):
    """Link to internal or external location."""
    
    class ExternalTarget(object):
        """Representation of an external target specified by its URI."""
        def __init__(self, uri, title, descr=None):
            """Arguments:

              uri -- URI of the link target as a string
              title -- title of the target as a string or unicode
              descr -- ???
              
            """
            self._uri = uri
            self._title = title
            self._descr = descr
        def uri(self):
            return self._uri
        def title(self):
            return self._title
        def descr(self):
            return self._descr
    
    def __init__(self, target, label=None, descr=None, type=None):
        """Arguments:

          target -- target of the link, it may be either a 'Section' instance
            or a 'ContentNode' instance, a 'Link.ExternalTarget' instance or a
            'Resource' instance
          label -- link label text as a string or a 'Content' instance (such as
            'InlineImage' for image links)
          descr -- breif target description text.  If none the description is
             taken from the 'target' instance depending on its type
          type -- ???
        
        """
        assert isinstance(target, (Section, ContentNode, self.ExternalTarget, Resource)), target
        assert label is None or isinstance(label, (str, unicode, Content)), label
        assert descr is None or isinstance(descr, (str, unicode)), descr
        assert type is None or isinstance(type, (str, unicode)), type
        if label is None:
            if isinstance(target, (ContentNode, Section)):
                label = target.title()
            elif isinstance(target, Resource):
                label = target.title() or target.filename()
            elif isinstance(target, self.ExternalTarget):
                label = target.title() or target.uri()
        if isinstance(label, (str, unicode)):
            content = TextContent(label)
        elif label is not None:
            content = label
        else:
            content = ()
        self._target = target
        self._descr = descr
        self._type = type
        super(Link, self).__init__(content)

    def target(self):
        """Return the value of 'target' as passed to the constructor."""
        return self._target

    def descr(self):
        """Return the link description as a string.

        If 'descr' was passed to the constructor and is not 'None', it is used.
        Otherwise the description is taken from target description if it was
        defined.

        """
        descr = self._descr
        if descr is None:
            target = self._target
            if isinstance(target, (ContentNode, self.ExternalTarget, Resource)):
                descr = target.descr()
            elif target.parent() is not self.parent():
                descr = target.title() + ' ('+ target.parent().title() +')'
        return descr

    def type(self):
        """Return the value of 'type' as passed to the constructor."""
        return self._type


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


class NoneContent(Content):
    """Deprecated.

    Intended for places where 'Content' is required but there is nothing to put
    in.  It is, however, actually useless, since 'Content' may be used for the
    same purpose.
    
    """
    pass

class ContentVariants(Container):
    """Container of multiple language variants of the same content.

    This implements one of two LCG methods for creating multilingual documents.  The second method
    uses 'TranslatableText' within the content and is mostly useful for content, which has
    identical structure in all language variants, only the user visible texts are translated.
    'ContentVariants', on the other hand, allows you to include a completely arbitrary subcontent
    for each language within one document.  Only the relevant variant is used in export time (when
    the target language is already known).

    """
    def __init__(self, variants):
        """Arguments:
        
          variants -- a sequence of pairs '(LANG, CONTENT)', where 'LANG' is an
            ISO 639-1 Alpha-2 language code and 'CONTENT' is the actual content
            variant for this language as a 'Content' instance or a sequence of
            'Content' instances
            
        """
        self._variants = {}
        for lang, content in variants:
            if isinstance(content, (list, tuple)): 
                content = Container(content)
            self._variants[lang] = content
        super(ContentVariants, self).__init__(self._variants.values())

    def sections(self, context):
        return self._variants[context.lang()].sections(context)
        
    def variant(self, lang):
        """Return the content variant for given language.

        Arguments:
          lang -- lowercase ISO 639-1 Alpha-2 language code

        'KeyError' is raised when the content for given language is not
        defined.

        """
        return self._variants[lang]
    
    
# Convenience functions for simple content construction.

def coerce(content, formatted=False):
    """Coerce the argument into an LCG content element.

    Arguments:

      content -- can be a sequence, string or a Content instance.  A sequence is turned to a
        'Container' of the items.  Moreover each item is coerced recursively and 'None' items are
        omitted.  A string is turned into a 'TextContent' or 'FormattedText' instance according to
        the 'formatted' argument.  A 'Content' instance is returned as is.  Any other argument
        raises AssertionError.
        
      formatted -- a boolean flag indicating that strings should be treated as formatted, so
        'FormattedText' is used instead of plain 'TextContent'.  Applies recursively if a sequence
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
    elif isinstance(content, (str, unicode)):
        if formatted:
            return FormattedText(content)
        else:
            return TextContent(content)
    else:
        assert isinstance(content, Content), ('Invalid content', content,)
        return content

def link(target, label=None, type=None, descr=None):
    """Return a 'Link' instance.

    Arguments:

      target -- link target.  It can be a direct URI as a string or unicode
        instance or any referable content element, such as 'Section',
        'ContentNode', 'Resource' or 'Link.ExternalTarget'.
      label -- link label is mandatory when the target is a direct URI (string
        or unicode) and optional for LCG content element targets.  In this case
        it just overrides the default title of the refered object.
      type -- mime type specification of the refered object.
      descr -- additional description of the link target.  Only applicable when
        the link target is a direct URI.

    """
    if isinstance(target, (str, unicode)):
        assert label is not None
        target = Link.ExternalTarget(target, None, descr=descr)
    else:
        assert isinstance(target, (ContentNode, Section, Link.ExternalTarget, Resource)), target
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

def fieldset(pairs, title=None, formatted=False):
    """Create a 'FieldSet' out of given sequence of (LABEL, VALUE) pairs.

    Both label and value are coerced, but only value is treated as formatted.
    
    """
    fields = [(coerce(label), coerce(value, formatted=formatted)) for label, value in pairs]
    return FieldSet(fields, title=title)

def p(*items, **kwargs):
    """Create a 'Paragraph' by coercing all arguments."""
    return Paragraph([coerce(item, **kwargs) for item in items])

def join(items, separator=' '):
    """Coerce all items and put the coerced separator in between them."""
    sep = coerce(separator)
    result = []
    for item in items:
        if result:
            result.append(sep)
        result.append(coerce(item))
    return coerce(result)
