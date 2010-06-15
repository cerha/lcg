# -*- coding: utf-8 -*-

# Copyright (C) 2008, 2010 Brailcom, o.p.s.
#
# COPYRIGHT NOTICE
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import copy
import cStringIO
import os
import string
import sys

import reportlab.lib.colors
import reportlab.lib.fonts
import reportlab.lib.pagesizes
import reportlab.lib.styles
import reportlab.lib.units
import reportlab.pdfbase.pdfmetrics
import reportlab.pdfbase.ttfonts
import reportlab.pdfgen
import reportlab.platypus

from lcg import *
from lcg.export import *

class PageTemplate(reportlab.platypus.PageTemplate):
    pass

class DocTemplate(reportlab.platypus.BaseDocTemplate):
    
    def handle_pageBegin(self):
        self._handle_pageBegin()
        self._handle_nextPageTemplate('Later')

    def build(self, flowables, context, first_page_header, page_header, page_footer):
        pdf_context = context.pdf_context
        def make_flowable(content):
            style = pdf_context.normal_style()
            flowable = content.export(context)
            if isinstance(flowable, Element):
                flowable = flowable.export(context)
            if isinstance(flowable, basestring):
                flowable = reportlab.platypus.Paragraph(flowable, style)
            while isinstance(flowable, (tuple, list,)):
                if len(flowable) == 1:
                    flowable = flowable[0]
                else:
                    flowable = reportlab.platypus.Table([flowable])
            max_height = self.height / 3  # so that header, footer and content have all chance to fit
            width, height = flowable.wrap(self.width, max_height)
            return flowable, width, height
        def frame_height(header, footer):
            bottom_margin = self.bottomMargin
            height = self.height
            separator_space = 0.5 * reportlab.lib.units.cm
            if header:
                _, _, header_height = make_flowable(header)
                header_height = header_height + separator_space
                height = height - header_height
            if footer:
                _, _, footer_height = make_flowable(footer)
                footer_height = footer_height + separator_space
                height = height - footer_height
                bottom_margin = bottom_margin + footer_height
            return bottom_margin, height
        def on_page(canvas, doc):
            page = doc.page
            pdf_context.page = page
            canvas.saveState()
            def add_flowable(content, top):
                flowable, width, height = make_flowable(content)
                x = (self.pagesize[0] - width) / 2
                if top:
                    y = self.height + self.bottomMargin
                else:
                    y = height + self.bottomMargin
                flowable.drawOn(canvas, x, y)
            header = first_page_header
            if page > 1 or header is None:
                header = page_header
            if header is not None:
                add_flowable(header, True)
            if page_footer is not None:
                add_flowable(page_footer, False)
            canvas.restoreState()
        self._calc()
        Frame = reportlab.platypus.frames.Frame
        bottom_margin, height = frame_height((first_page_header or page_header), page_footer)
        first_frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='first')
        bottom_margin, height = frame_height(page_header, page_footer)
        later_frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id='later')
        self.addPageTemplates([
            PageTemplate(id='First', frames=first_frame, onPage=on_page, pagesize=self.pagesize),
            PageTemplate(id='Later', frames=later_frame, onPage=on_page, pagesize=self.pagesize)
            ])
        reportlab.platypus.BaseDocTemplate.build(self, flowables,
                                                 canvasmaker=reportlab.pdfgen.canvas.Canvas)

class Context(object):
    """Place holder for PDF backend export state.

    An instance of this class is stored as a 'pdf_context' attribute of the LCG
    'Context' instance.

    """
    
    _font_path = '/usr/share/fonts/truetype/freefont'

    _nesting_level = 0
    _list_nesting_level = 0
    _counter = 0
    page = 0
    total_pages = None
    total_pages_requested = False

    def __init__(self, *args, **kwargs):
        super(Context, self).__init__(*args, **kwargs)
        self._init_fonts()
        self._styles = reportlab.lib.styles.getSampleStyleSheet()        
        self._normal_style = copy.copy(self._styles['Normal'])
        self._normal_style.fontName='FreeSerif'
        self._code_style = copy.copy(self._styles['Code'])
        self._code_style.fontName='FreeMono'
        self._anchors = {}
        self._presentations = []

    def _init_fonts(self):
        self._fonts = {}
        for family in 'Serif', 'Sans', 'Mono':
            font_name = 'Free' + family
            i = 0
            if family == 'Serif':
                faces = (('', False, False,), ('Italic', False, True,),
                         ('Bold', True, False,), ('BoldItalic', True, True,),)
            else:
                faces = (('', False, False,), ('Oblique', False, True,),
                         ('Bold', True, False,), ('BoldOblique', True, True,),)
            for face, bold, italic in faces:
                font_face_name = font_name + face
                f = reportlab.pdfbase.ttfonts.TTFont(font_face_name, os.path.join(self._font_path, font_face_name) + '.ttf')
                reportlab.pdfbase.pdfmetrics.registerFont(f)
                reportlab.lib.fonts.addMapping(font_name, i/2, i%2, font_face_name)
                i = i + 1
                self._fonts[(family, bold, italic)] = font_face_name

    def font(self, family, bold, italic):
        """Return full font name for given arguments.

        Arguments:

          family -- one of 'Serif', 'Sans', 'Mono' constants
          bold -- boolean
          italic -- boolean
          
        """
        return self._fonts[(family, bold, italic,)]

    def font_parameters(self, font_name):
        """Return tuple (FAMILY, BOLD, ITALIC,) corresponding to given 'font_name'.
        """
        for k, v in self._fonts.items():
            if v == font_name:
                return k
        else:
            raise KeyError(font_name)

    def nesting_level(self):
        """Return current paragraph and list nesting level.

        This is used mostly for determining proper left indentation.
        Starting level is 0.
        
        """
        return self._nesting_level

    def inc_nesting_level(self):
        """Increase current nesting level by 1.
        """
        self._nesting_level += 1

    def list_nesting_level(self):
        """Return current list nesting level.

        This is used for determining proper bullet style.
        Starting level is 0.
        
        """
        return self._list_nesting_level

    def inc_list_nesting_level(self):
        """Increase current list nesting level by 1.
        """
        self._list_nesting_level += 1

    def normal_style(self):
        """Return standard paragraph style.
        """
        return self._normal_style

    def code_style(self):
        """Return paragraph style for verbatim texts.
        """
        return self._code_style

    def heading_style(self, level):
        """Return paragraph style for headings.

        Arguments:

          level -- heading level as int starting from 1 (the highest level)

        """
        if level < 1:
            level = 1
        elif level > 3:
            level = 3
        style = copy.copy(self._styles['Heading%d' % (level,)])
        style.fontName='FreeSerif'
        return style

    def list_style(self, order=None):
        """Return paragraph style for lists.

        Arguments:

          order -- None for an unordered list (bullet list) or one of allowed strings
            describing ordering style ('numeric', 'lower-alpha', 'upper-alpha').

        """
        if order:
            style_name = 'Normal'
        else:
            style_name = 'Bullet'
        style = copy.copy(self._styles[style_name])
        style.fontName='FreeSerif'
        return style

    def style(self, style=None):
        """Return style corresponding to the given context.

        Arguments:

          style -- style to use as a template; if 'None' then use normal style
        
        """
        style = copy.copy(style or self.normal_style())
        presentation = self.current_presentation()
        if presentation is not None:
            if presentation.font_size is not None:
                style.font_size = style.font_size * presentation.font_size
            family, bold, italic = self.font_parameters(style.fontName)
            if presentation.font_family is not None:
                if presentation.font_family == 'PROPORTIONAL':
                    family = 'FreeSerif'
                elif presentation.font_family == 'SANS_SERIF':
                    family = 'FreeSans'
                elif presentation.font_family == 'FIXED_WIDTH':
                    family = 'FreeMono'
                else:
                    raise Exception('Unknown font family', presentation.font_family)
            if presentation.bold is not None:
                bold = presentation.bold
            if presentation.italic is not None:
                italic = presentation.italic
            style.font_family = self.font(family, bold, italic)
        return style

    def get_seqid(self):
        """Increase counter value by 1 and return the new value.

        This enables access to internal counter that can be used to lease
        unique numbers for any purpose.
        
        """
        self._counter += 1
        return self._counter

    def register_anchor_reference(self, name):
        """Register anchor reference into the context.

        This serves for later detection of anchor references to nonexistent
        anchors.

        Parameters:

          name -- name of the anchor, basestring
          
        """
        if not self._anchors.has_key(name):
            self._anchors[name] = False

    def clear_anchor_reference(self, name):
        """Mark anchor reference as valid.

        This means the given anchor actually exists in the document.

        Parameters:

          name -- name of the anchor, basestring
          
        """
        self._anchors[name] = True

    def invalid_anchor_references(self):
        """Return sequence of names of invalid anchor references.
        """
        return [k for k, v in self._anchors.items() if not v]

    def current_presentation(self):
        """Return current 'Presentation' instance."""
        if self._presentations:
            presentation = self._presentations[-1]
        else:
            presentation = None
        return presentation

    def add_presentation(self, presentation):
        """Add 'presentation' to presentations.

        It is merged with other presentations in the current presentation list
        and the resulting presentation is added to the list and becomes the
        current presentation.  The presentation must be removed from the
        presentation list using 'remove_presentation' method when the object it
        introduces is left.

        Arguments:

          presentation -- 'Presentation' to be applied; if 'None', current
            presentation is used instead
        
        """
        current_presentation = self.current_presentation()
        if current_presentation is None:
            new_presentation = presentation
        elif presentation is None:
            new_presentation = current_presentation
        else:
            new_presentation = Presentation()
            for attr in dir(presentation):
                if attr[0] in string.ascii_lowercase:
                    value = getattr(presentation, attr)
                    if value is None:
                        value = getattr(current_presentation, attr)
                    setattr(new_presentation, attr, value)
        self._presentations.append(new_presentation)

    def remove_presentation(self):
        """Remove the current presentation from the presentation list."""
        self._presentations.pop()


def _ok_export_result(result):
    if not isinstance(result, (tuple, list,)) or not result:
        return True
    if isinstance(result[0], basestring):
        expected = 'string'
    else:
        expected = 'nonstring'
    for r in result[1:]:
        if isinstance(r, basestring):
            if expected != 'string':
                return False
        else:
            if expected != 'nonstring':
                return False
    return True

class Element(object):
    """Base class of all content classes.

    Hierarchy of these classes is used to describe any content of PDF documents
    generated by LCG.  The document structure is built during the LCG export
    phase.

    Each class provides the 'content' attribute which holds its primary
    content.  Subclasses may define additional attributes as needed.

    These classes don't define argument initialization constructors not to
    waste space in this source file.  Use the 'make_element' function to create
    instances of these classes.
    
    """
    content = None
    def init(self):
        """Initialize class.

        This method is called after instance attributes are set in
        'make_element' function.
        
        """
        pass
    def export(self, context):
        """Export this element and its contents into a reportlab document.

        Arguments:

          context -- LCG 'Context' instance
          
        """
        raise Exception ('Not implemented')
    def prepend_text(self, text):
        """Prepend given 'text' to the front of the element contents.

        This method was introduced primarily to allow adding bullets to list
        paragraphs, etc.

        Arguments:

          text -- basestring to prepend

        """
        raise Exception('Not implemented')
    def _unit2points(self, size, style):
        if isinstance(size, UMm):
            points = size.size() * reportlab.lib.units.mm
        elif isinstance(size, UPoint):
            points = size.size()
        elif isinstance(size, (UFont, USpace,)):
            points = size.size() * style.fontSize
        else:
            raise Exception('Not implemented', size)
        return points

class Text(Element):
    """Basic text.

    Its content is basestring (preferably unicode) or another 'Text' instance.
    No text may be placed into the document hierarchy directly; always use
    'Text' or one of its subclasses to store text into the document.

    """
    _replacements = (('&', '&amp;',),
                     ('<', '&lt;',),
                     ('>', '&gt;',),
                     )
    def init(self):
        assert isinstance(self.content, (basestring, Text,)), ('type error', self.content,)
        if isinstance(self.content, basestring):
            for old, new in self._replacements:
                self.content = self.content.replace(old, new)
    def export(self, context):
        content = self.content
        if isinstance(content, basestring):
            result = context.translate(self.content)
        else:
            result = content.export(context)
        assert _ok_export_result(result), ('wrong export', result,)
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        if isinstance(self.content, basestring):
            new_content = [text, copy.copy(self)]
            self.content = make_element(TextContainer, content=new_content)
        else:
            self.content.prepend_text(text)

class Empty(Text):
    """An empty content.

    Useful when 'Element' is required or expected, but there is no actual
    content to provide.  'content' value is ignored.
    
    """
    def init(self):
        self.content = ''

class MarkedText(Text):
    """Text wrapped by an in-paragraph markup.

    'content' must be a 'Text' instance.  Additionaly, 'tag' name of the markup
    is required, optionally accompanied by 'attributes' dictionary providing
    tag attribute names and values.

    """
    tag = None
    attributes = {}
    def init(self):
        super(MarkedText, self).init()
        assert isinstance(self.tag, str), ('type error', self.tag,)
        assert isinstance(self.attributes, dict)
    def export(self, context):
        exported = super(MarkedText, self).export(context)
        start_mark = self.tag
        for k, v in self.attributes.items():
            start_mark += ' %s="%s"' % (k, v,)
        result = u'<%s>%s</%s>' % (start_mark, exported, self.tag,)
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        self.content.prepend_text(text)

class SimpleMarkup(Text):
    """In-paragraph markup without content.

    A typical example of such an element might be a line break.

    'content' is the tag name.  It can be optionally accompanied by
    'attributes' dictionary providing tag attribute names and values.

    """
    attributes = {}
    def init(self):
        assert isinstance(self.content, str), ('type error', self.content,)
    def export(self, context):
        mark = self.content
        for k, v in self.attributes.items():
            mark += ' %s="%s"' % (k, v,)
        result = '<%s/>' % (mark,)
        return result

class TextContainer(Text):
    """Container of any number of 'Text' elements.

    'content' is a list of 'Text' instances.

    This class serves for grouping several 'Text' elements together.
    
    """
    def init(self):
        content = self.content
        assert isinstance(content, list), ('type error', content,)
        if __debug__:
            for c in content:
                assert isinstance(c, Text), ('type error', c,)
    def export(self, context):
        result = u''
        for c in self.content:
            result += c.export(context)
        assert _ok_export_result(result), ('wrong export', result,)
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        self.content.insert(0, make_element(Text, content=text))
    
class PreformattedText(Element):
    """Text to be output verbatim.

    'content' is a unicode object to be printed.
    
    """
    def init(self):
        super(PreformattedText, self).init()
        assert isinstance(self.content, basestring), ('type error', self.content,)
    def export(self, context):
        style = context.pdf_context.code_style()
        result = reportlab.platypus.Preformatted(self.content, style)
        return result

class Paragraph(Element):
    """Paragraph of text.

    'content' is a sequence of 'Text' elements.

    \"Paragraph\" is used here in a wider sense, it's just a separated piece of
    text, possibly characterized by some style.  However mutual nesting the
    paragraphs is not allowed, paragraphs may only contain text elements.

    """
    _style = None
    presentation = None
    def init(self):
        super(Paragraph, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, Text), ('type error', c,)
        self.content = list(self.content)
    def export(self, context, style=None):
        pdf_context = context.pdf_context
        pdf_context.add_presentation(self.presentation)
        template_style = style or self._style or pdf_context.normal_style()
        style = pdf_context.style(style=template_style)
        style.leftIndent = pdf_context.nesting_level() * 1.5 * style.fontSize
        if self.presentation and self.presentation.left_indent:
            style.leftIndent += self._unit2points(self.presentation.left_indent, style)
        # Hack, should be handled better, preferrably in List only:
        style.bulletIndent = max(pdf_context.list_nesting_level() - 1, 0) * 1.5 * style.fontSize
        exported = ''
        for c in self.content:
            exported += c.export(context)
        assert _ok_export_result(exported), ('wrong export', exported,)
        result = reportlab.platypus.Paragraph(exported, style)
        pdf_context.remove_presentation()
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        self.content.insert(0, make_element(Text, content=text))
        
class Heading(Paragraph):
    """Heading of a section, etc.

    'content' is the same as in 'Paragraph'.  Additionally heading 'level'
    property must be specified, as an int starting from 1 (the topmost level).
    
    """
    level = None
    def init(self):
        super(Heading, self).init()
        assert isinstance(self.level, int), ('type error', self.level,)
    def export(self, context):
        style = context.pdf_context.heading_style(self.level)
        result = super(Heading, self).export(context, style=style)
        return result

class PageBreak(Element):
    """Unconditional page break.

    Its 'content' is ignored.

    """
    def export(self, context):
        return reportlab.platypus.PageBreak()

class PageNumber(Text):
    """Page number.

    'total' parameter determines whether total number of pages should be added.

    """
    # This implementation is an ugly hack to make the class a subclass of Text
    # easily, for the reasons of type checking and appropriate handling at
    # several places.
    def init(self):
        pass
    def export(self, context):
        pdf_context = context.pdf_context
        text = str(pdf_context.page)
        if self.total:
            total = pdf_context.total_pages
            if total is None:
                pdf_context.total_pages_requested = True
            else:
                text = '%s/%s' % (text, total,)
        self.content = text
        Text.init(self)
        return Text.export(self, context)

class Space(Element):
    """Hard space.

    There is no content, instead there are two size parameters:

      width -- width of the space, 'Unit'
      height -- height of the space, 'Unit'

    """
    def export(self, context):
        # Note: According to Reportlab documentation, only vertical spaces work.
        style = context.pdf_context.style()
        width = self._unit2points(self.width, style)
        height = self._unit2points(self.height, style)
        return reportlab.platypus.Spacer(width, height)

class Container(Element):
    """Sequence of (almost) any objects.

    'content' is a sequence of 'Element' instances.

    This class serves for general grouping of elements.  Not all combinations
    may work.  Allowed content is unspecified in LCG now, it may get more
    restricted in future (not counting current implementation restrictions).

    """
    presentation = None
    def init(self):
        if __debug__:
            for c in self.content:
                assert isinstance(c, Element), ('type error', c,)
    def export(self, context):
        pdf_context = context.pdf_context
        pdf_context.add_presentation(self.presentation)
        result = []
        all_text = all([isinstance(c, (basestring, Text,)) for c in self.content])
        for c in self.content:
            if isinstance(c, basestring):
                c = make_element(Text, content=c)
            if isinstance(c, Text) and not all_text:
                c = make_element(Paragraph, content=[c])
            exported = c.export(context)
            if isinstance(exported, (list, tuple,)):
                result += exported
            else:
                result.append(exported)
        pdf_context.remove_presentation()
        assert _ok_export_result(result), ('wrong export', result,)
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        if self.content:
            self.content[0].prepend_text(text)
        else:
            text_element = make_element(Text, content=text)
            paragraph = make_element(Paragraph, content=[text_element])
            self.content = [paragraph]
    def expand(self, filter_):
        """Convert the container into a plain sequence of 'Element's and return it.

        The primary purpose of this method is to cope with the mess caused by
        LCG mixing everything together under the assumptions that all the
        exported objects are HTML strings and that there are no strict
        restrictions on the content (e.g. paragraph may contain other
        paragraphs or even itself).

        The container is inspected recursively and its objects are put to a
        single non-nested sequence.  'filter_' is applied on non-'Container'
        instances.

        Arguments:

          filter_ -- function of a single argument, the content instance,
            returning a list of 'Element' instances.  Through the filtering
            function the container content may be changed or filtered out (by
            returning empty lists).
          
        """
        expanded = []
        for c in self.content:
            if isinstance(c, Container):
                # We should prevent infinite recursion here, but hopefully LCG
                # actually doesn't use Containers containing themselves.
                expanded += c.expand(filter_)
            else:
                expanded += filter_(c)
        return expanded

class List(Element):
    """List of items.

    'content' is a list of the list items; in theory they can be of any type,
    but 'Text' or 'Paragraph' instances are recommended.  An optional attribute
    'order' may be used to distinguish between several ordering styles (None
    for unordered (bulleted) lists or one of ('numeric', 'lower-alpha',
    'upper-alpha') for ordered lists.

    """
    order = False
    def init(self):
        super(List, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        self.content = list(self.content)
    def export(self, context):
        pdf_context = context.pdf_context
        style = pdf_context.list_style(self.order)
        list_nesting_level = pdf_context.list_nesting_level()
        font_size = style.fontSize
        style.bulletIndent = list_nesting_level * 1.5 * font_size
        style.leftIndent = style.bulletIndent + 1.5 * font_size
        if self.order:
            seqid = pdf_context.get_seqid()
            seq_string = make_element(SimpleMarkup, content='seq', attributes=dict(id='list%d'%(seqid,)))
            dot_string = make_element(Text, content=u'.')
            bullet_string = make_element(TextContainer, content=[seq_string, dot_string])
        else:
            if list_nesting_level == 0:
                bullet_string = u'•'
            else:
                bullet_string = u'-'
        bullet = make_element(MarkedText, content=bullet_string, tag='bullet')
        next_pdf_context = copy.copy(pdf_context)
        next_pdf_context.inc_nesting_level()
        next_pdf_context.inc_list_nesting_level()
        next_context = copy.copy(context)
        next_context.pdf_context = next_pdf_context
        def make_item(item):
            item.prepend_text(bullet)
            exported = item.export(next_context)
            if isinstance(item, Text):
                result = [reportlab.platypus.Paragraph(exported, style)]
            elif isinstance(item, Paragraph):
                result = [exported]
            elif isinstance(item, Container):
                result = exported
            else:
                raise Exception ('type error', item,)
            return result
        result = []
        for item in self.content:
            result += make_item(item)
        assert _ok_export_result(result), ('wrong export', result,)
        return result

class Link(Text):
    """Link to some location, either internal or external.

    'content' is the content of the link as a 'Text' instance.  There is an
    additional required parameter 'uri', a string defining the target location.
    There are two kinds of URIs supported: 'http:' prefixed URIs pointing to
    external targets and '#' prefixed URIs pointing to internal targets.

    """
    uri = None
    def init(self):
        super(Link, self).init()
        assert isinstance(self.uri, basestring), ('type error', self.uri,)
        assert self.uri, ('empty URI', self.uri,)
    def export(self, context):
        exported_content = super(Link, self).export(context)
        if self.uri[:5] == 'http:' or self.uri[0] == '#':
            result = u'<link href="%s">%s</link>' % (self.uri, exported_content,)
            if self.uri[0] == '#':
                context.pdf_context.register_anchor_reference(self.uri[1:])
        else:
            result = u'<i>%s</i>' % (exported_content,)
        return result
        
class LinkTarget(Text):
    """Target of an internal link.

    'content' is ignored.  An additional required argument 'name' defines the
    location name (without the leading '#' character).

    """
    content = ''
    name = None
    def init(self):
        super(LinkTarget, self).init()
        assert isinstance(self.name, basestring), ('type error', self.name,)
        assert self.name, ('empty target name', self.name,)
    def export(self, context):
        exported_text = super(LinkTarget, self).export(context)
        context.pdf_context.clear_anchor_reference(self.name)
        result = u'<a name="%s"/>%s' % (self.name, exported_text,)
        return result

class Image(Element):
    """Image taken from an Image resource instance.

    'image' is an Image instance.  An additional argument 'text' may provide text description of
    the image in the form of base string.
    
    """
    def init(self):
        super(Image, self).init()
        assert isinstance(self.image, resources.Image), ('type error', self.image,)
        assert self.text is None or isinstance(self.text, basestring), ('type error', self.image,)
    def export(self, context):
        filename = self.image.src_file()
        if filename:
            result = reportlab.platypus.Flowable(filename)
        else:
            content = make_element(Text, content=(self.image.title() or '[image]'))
            result = make_element(Paragraph, content=[content]).export(context)
        return result

class TableCell(Container):
    """Table cell.

    'content' is unspecified.
    There are additional styling attributes 'align', 'valign', and 'heading'.
    They are not used directly here, they are used by 'Table'.

    """
    align = None
    valign = None
    heading = False

class TableRow(Element):
    """Table row.

    'content' is a sequence of 'TableCell's.
    
    """
    def init(self):
        super(TableRow, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, TableCell), ('type error', c,)

class Table(Element):
    """Table of rows and columns.

    'content' is a sequence of 'TableRow's.
    Cells are 'TableCell' instances.

    """
    presentation = None
    long = False
    column_widths = None
    
    def init(self):
        super(Table, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, TableRow), ('type error', c,)
    def export(self, context):
        pdf_context = context.pdf_context
        pdf_context.add_presentation(self.presentation)
        content = self.content
        exported_content = []
        # Find out information about the table
        table_style_data = []
        number_of_rows = len(content)
        header_row_p = False
        alignments = []
        if number_of_rows > 1:
            if all([c.heading for c in content[0].content]):
                header_row_p = True
            row = content[1].content
            for j in range(len(row)):
                column = row[j]
                if isinstance(column, TableCell) and column.align is not None:
                    alignments.append(column.align)
                    table_style_data.append(('ALIGN', (j, 0), (j, -1), column.align.upper(),))
                else:
                    alignments.append(None)
                if isinstance(column, TableCell) and column.valign is not None:
                    table_style_data.append(('VALIGN', (j, 0), (j, -1), column.valign.upper(),))
        # Export content
        black = reportlab.lib.colors.black
        style = pdf_context.style()
        family, bold, italic = pdf_context.font_parameters(style.fontName)
        bold_font = pdf_context.font(family, True, italic)
        i = 0
        for row in content:
            if isinstance(row, PageBreak):
                table_style_data.append(('LINEABOVE', (0, i), (-1, i), 1, black,))
                continue
            row_content = []
            for j in range(len(row.content)):
                column = row.content[j]
                if isinstance(column, (list, tuple,)):
                    row_content += [c.export(context) for c in column]
                else:
                    if isinstance(column, TableCell):
                        if column.heading:
                            table_style_data.append(('FACE', (j, i), (j, i), bold_font,))
                        if (column.align is not None and
                            (not alignments or column.align != alignments[j])):
                            table_style_data.append(('ALIGN', (j, i), (j, i), column.align.upper(),))
                    row_content += column.export(context)
            exported_content.append(row_content)
            i += 1
        # Add remaining presentation
        presentation = pdf_context.current_presentation()
        if presentation is not None:
            if presentation.separator_height:
                size = self._unit2points(presentation.separator_height, style)
                table_style_data.append(('GRID', (0, 0), (-1, -1), size, black,))
            if header_row_p and presentation.header_separator_height is not None:
                size = self._unit2points(presentation.header_separator_height, style)
                table_style_data.append(('LINEBELOW', (0, 0), (-1, 0), size, black,))
            if presentation.separator_margin:
                size = self._unit2points(presentation.separator_margin, style) / 2
            else:
                size = 0
            table_style_data.append(('TOPPADDING', (0, 0), (-1, -1), size,))
            table_style_data.append(('BOTTOMPADDING', (0, 0), (-1, -1), size,))
            if header_row_p and presentation.header_separator_margin is not None:
                size = self._unit2points(presentation.header_separator_margin, style) / 2
                table_style_data.append(('TOPPADDING', (0, 0), (-1, 0), size,))
                table_style_data.append(('BOTTOMPADDING', (0, 0), (-1, 0), size,))
        else:
            table_style_data.append(('TOPPADDING', (0, 0), (-1, -1), 0,))
            table_style_data.append(('BOTTOMPADDING', (0, 0), (-1, -1), 0,))
        table_style_data.append(('LEFTPADDING', (0, 0), (-1, -1), 0,))
        table_style_data.append(('RIGHTPADDING', (0, 0), (-1, -1), 0,))        
        # Create the table instance
        repeat_cols = 0
        if self.long:
            # It may or needn't be a good idea to always use LongTable
            # unconditionally here.
            class_ = reportlab.platypus.LongTable
            if header_row_p:
                repeat_cols = 1
        else:
            class_ = reportlab.platypus.Table
        if self.column_widths is None:
            column_widths = None
        else:
            column_widths = [self._unit2points(w, style) for w in self.column_widths]
        table_style = reportlab.platypus.TableStyle(table_style_data)
        table = class_(exported_content, colWidths=column_widths, style=table_style,
                       repeatCols=repeat_cols)
        pdf_context.remove_presentation()
        return table

def make_element(cls, **kwargs):
    """Create instance of 'cls' class and initialize its attributes.

    This method was introduced to simplify creation of 'Element' instances,
    without needing to define all the trivial constructors.

    Arguments:

      kwargs -- dictionary of attribute names as keys and their values to be
        set

    """
    element = cls()
    for k, v in kwargs.items():
        setattr(element, k, v)
    element.init()
    return element


class PDFMarkupFormatter(MarkupFormatter):

    _FORMAT = {'comment': make_element(Empty),
               'dash': make_element(Text, content=u'—'),
               'nbsp': make_element(Text, content=u' ')}
               
    class _StackEntry(object):
        def __init__(self, markup):
            self.markup = markup
            self.content = []

    def _handle_open_close_markup(self, markup, context, close=False, **kwargs):
        if close:
            entry = context.pdf_markup_stack.pop()
            assert entry.markup == markup, ('markup mismatch', entry.markup, markup,)
            exported = make_element(TextContainer, content=entry.content)
            e = context.exporter()
            method = getattr(e, markup)
            result = method(context, exported)
        else:
            context.pdf_markup_stack.append(self._StackEntry(markup))
            result = make_element(Empty)
        return result
        
    def _emphasize_formatter(self, *args, **kwargs):
        return self._handle_open_close_markup('emphasize', *args,  **kwargs)

    def _strong_formatter(self, *args, **kwargs):
        return self._handle_open_close_markup('strong', *args,  **kwargs)

    def _fixed_formatter(self, *args, **kwargs):
        return self._handle_open_close_markup('fixed', *args, **kwargs)

    def _underline_formatter(self, *args, **kwargs):
        return self._handle_open_close_markup('underline', *args, **kwargs)

    def _citation_formatter(self, *args, **kwargs):
        return self._handle_open_close_markup('citation', *args, **kwargs)

    def _quotation_formatter(self, *args, **kwargs):
        return self._handle_open_close_markup('quotation', *args, **kwargs)

    def _linebreak_formatter(self, context, **kwargs):
        return make_element(SimpleMarkup, content='br')

    def _email_formatter(self, context, email, **kwargs):
        e = context.exporter()
        return e.fixed(context, email)
    
    def format(self, context, text):
        if not hasattr(context, 'pdf_markup_stack'):
            context.pdf_markup_stack = []
        e = context.exporter()
        self._open = []
        result = []
        pos = 0
        def insert_text(exported):
            if isinstance(exported, Empty):
                return
            if context.pdf_markup_stack:
                context.pdf_markup_stack[-1].content.append(exported)
            else:
                result.append(exported)
        for match in self._rules.finditer(text):
            starting_text = e.escape(text[pos:match.start()])
            insert_text(starting_text)
            markup = self._markup_handler(context, match)
            insert_text(markup)
            pos = match.end()
        final_text = e.escape(text[pos:])
        insert_text(final_text)
        self._open.reverse()
        x = self._open[:]
        for type in x:
            result.append(self._formatter(context, type, {}, close=True))
        return e.concat(*result)


class PDFExporter(FileExporter, Exporter):
    
    Formatter = PDFMarkupFormatter

    _OUTPUT_FILE_EXT = 'pdf'
    
    def _uri_section(self, context, section, local=False):
        # Force all section links to be local, since there is just one output document.
        return super(PDFExporter, self)._uri_section(context, section, local=True)

    def _content_export(self, context, element, collapse=True):
        content = element.content()
        if isinstance(content, (tuple, list,)):
            exported_content = [c.export(context) for c in content]
        else:
            exported_content = content.export(context)
        if collapse and isinstance(exported_content, (tuple, list,)):
            result_content = self.concat(*exported_content)
        else:
            result_content = exported_content
        return result_content

    def _markup(self, text, tag, **attributes):
        return make_element(MarkedText, content=text, tag=tag, attributes=attributes)

    def concat(self, *exported):
        # This method should be considered a temporary hack.
        # Its semantics is undefined.
        # Proper data types and method calls with strict rules should be used
        # instead of the inelegant and unreliable guesswork.
        if exported:
            for e in exported:
                if not isinstance(e, Text):
                    def transform(item):
                        if isinstance(item, Text):
                            result = make_element(Paragraph, content=[item])
                        else:
                            result = item
                        return result
                    result = make_element(Container, content=[transform(item) for item in exported])
                    break
            else:
                # everything is Text
                result = make_element(TextContainer, content=list(exported))
        else:
            result = make_element(Container, content=())
        return result
    
    def escape(self, text):
        return make_element(Text, content=text)

    def emphasize(self, context, text):
        return self._markup(text, 'i')

    def strong(self, context, text):
        return self._markup(text, 'strong')
    
    def fixed(self, context, text):
        return self._markup(text, 'font', face='FreeMono')
     
    def underline(self, context, text):
        return self._markup(text, 'u')
    
    def superscript(self, context, text):
        return self._markup(text, 'super')
    
    def subscript(self, context, text):
        return self._markup(text, 'sub')
    
    def citation(self, context, text):
        return self.emphasize(text)
    
    def quotation(self, context, text):
        return self.emphasize(text)

    # Classic exports
        
    def export(self, context, total_pages=None):
        context.pdf_context = pdf_context = Context()
        pdf_context.total_pages = total_pages
	exported_structure = []
        lang = context.lang()
        for node in context.node().linear():
            subcontext = self.context(node, lang)
            subcontext.pdf_context = pdf_context
            title = node.title()
            if title:
                exported_title = make_element(Heading, content=[make_element(Text, content=title)],
                                              level=0)
                exported_structure.append(exported_title)
            exported = node.content().export(subcontext)
            if isinstance(exported, (tuple, list,)):
                exported = self.concat(*exported)
            exported_structure.append(exported)
        exported_content = self.concat(*exported_structure)
        document = exported_content.export(context)
        # It is necessary to check for invalid anchors before doc.build gets
        # called, otherwise Reportlab throws an ugly error.
        invalid_anchors = context.pdf_context.invalid_anchor_references()
        if invalid_anchors:
            sys.stderr.write("Error: Invalid internal links:\n")
            for a in invalid_anchors:
                sys.stderr.write("  #%s\n" % (a,))
            return ''
        output = cStringIO.StringIO()
        margin = 10 * reportlab.lib.units.mm
        page_size = reportlab.lib.pagesizes.A4
        if True:
            page_size = reportlab.lib.pagesizes.portrait(page_size)
        else:
            page_size = reportlab.lib.pagesizes.landscape(page_size)
        doc = DocTemplate(output, pagesize=page_size,
                          leftMargin=margin, rightMargin=margin,
                          topMargin=margin, bottomMargin=margin)
        doc.build(document, context=context,
                  first_page_header=node.first_page_header(),
                  page_header=node.page_header(),
                  page_footer=node.page_footer())
        if total_pages is None and pdf_context.total_pages_requested:
            return self.export(context, total_pages=pdf_context.page)
        return output.getvalue()
    
    def export_element(self, context, element_type, element):
        result = super(PDFExporter, self).export_element(context, element_type, element)
        assert isinstance(result, Element), ('Invalid export result', element, result,)
        return result
    
    def _export_content(self, context, element):
        return make_element(Empty)

    def _export_horizontal_separator(self, context, element):
        return self.new_page(context)

    def _export_preformatted_text(self, context, element):
        return make_element(PreformattedText, content=element.text())
        
    def _export_anchor(self, context, element):
        return make_element(LinkTarget, content=element.text(), name=element.anchor())
    
    def _export_new_page(self, context, element):
        return make_element(PageBreak)

    def _export_horizontal_separator(self, context, element):
        return make_element(PageBreak)

    def _export_page_number(self, context, element):
        return make_element(PageNumber, total=element.total())

    def _export_hspace(self, context, element):
        return make_element(Space, width=element.size(), height=UMm(0))

    def _export_vspace(self, context, element):
        return make_element(Space, height=element.size(), width=UMm(0))

    # Container elements
    
    def _export_container(self, context, element):
        content = element.content()
        orientation = element.orientation()
        if (orientation == 'HORIZONTAL' or
            element.halign() is not None or element.valign() is not None):
            def cell(content):
                exported_content = [content.export(context)]
                return make_element(TableCell, content=exported_content,
                                    align=element.halign(), valign=element.valign())
            if orientation == 'HORIZONTAL':
                table_content = [make_element(TableRow, content=[cell(c) for c in content])]
            else:
                table_content = [make_element(TableRow, content=[cell(c)]) for c in content]
            result_content = make_element(Table, content=table_content,
                                          presentation=element.presentation())
        else:
            result_content = self._content_export(context, element)
        return result_content

    def _export_link(self, context, element):
        target = element.target()
        content = self._content_export(context, element)
        uri = context.uri(target)
        if isinstance(content, Container):
            def filter_(c):
                if isinstance(c, Text):
                    result = [c]
                elif isinstance(c, basestring):
                    result = [make_element(Text, content=c)]
                elif isinstance(c, Image):
                    link_content = make_element(Text, content=(c.text or c.content or 'image'))
                    uri = c.image.uri()
                    if uri is None:
                        result = []
                    else:
                        result = [make_element(Link, content=link_content, uri=uri)]
                else:
                    result = []
                return result
            filtered_content = content.expand(filter_)
            content = make_element(TextContainer, content=filtered_content)
        return make_element(Link, content=content, uri=uri)

    def _export_section(self, context, element):
        content = self.escape(element.title())
        anchor = element.anchor()
        if anchor:
            content = make_element(LinkTarget, content=content, name=anchor)
        backref = element.backref()
        if backref:
            content = self.link(content, "#"+backref)
        heading = make_element(Heading, content=[content], level=1)
        inner_content = self._export_container(context, element)
        return make_element(Container, content=[heading, inner_content])

    def _export_itemized_list(self, context, element):
        content = self._content_export(context, element, collapse=False)
        return make_element(List, content=content, order=element.order())

    def _export_definition_list(self, context, element):
        def make_item(title, description):
            if isinstance(title, Text):
                title = make_element(Paragraph, content=[title])
            if isinstance(description, Text):
                presentation = Presentation()
                presentation.left_indent = UMm(10)
                description = make_element(Paragraph, content=[description],
                                           presentation=presentation)
            return make_element(Container, content=[title, description])
        result_items = [make_item(dt.export(context), dd.export(context))
                        for dt, dd in element.content()]
        return make_element(Container, content=result_items)
    
    def _export_field_set(self, context, element):
        def make_item(label, value):
            content = [make_element(TableCell, content=[label.export(context)]),
                       make_element(TableCell, content=[value.export(context)])]
            return make_element(TableRow, content=content)
        rows = [make_item(*c) for c in element.content()]
        return make_element(Table, content=rows)
            
    def _export_paragraph(self, context, element):
        # LCG interpretation of "paragraph" is very wide, we have to expect
        # anything containing anything.  The only "paragraph" meaning we use
        # here is that the content should be separated from other text.
        content = self._content_export(context, element)
        if isinstance(content, Text):
            result = make_element(Paragraph, content=[content], presentation=element.presentation())
        else:
            result = make_element(Container, content=[content])
        return result

    def _export_table_of_contents(self, context, element):
        def make_toc(items):
            if len(items) == 0:
                return self.escape('')
            toc_items = []
            for item, subitems in items:
                label = make_element(Text, content=item.title())
                subtoc = make_toc(subitems)
                toc_items.append(self.concat(label, subtoc))
            return make_element(List, content=toc_items)
        result = make_toc(element.items(context))
        title = element.title()
        if title is not None:
            result = self.concat(self._markup(title, 'strong'), result)
        return result

    # Tables

    def _export_table(self, context, element):
        return make_element(Table, content=[c.export(context) for c in element.content()],
                            long=element.long(),
                            column_widths=element.column_widths(),
                            presentation=element.presentation())

    def _export_table_row(self, context, element):
        return make_element(TableRow, content=[c.export(context) for c in element.content()])

    def _simple_export_table_cell(self, context, element, heading):
        return make_element(TableCell,
                            content=[self._content_export(context, element)],
                            align=element.align(),
                            heading=heading)
        
    def _export_table_cell(self, context, element):
        return self._simple_export_table_cell(context, element, heading=False)

    def _export_table_heading(self, context, element):
        return self._simple_export_table_cell(context, element, heading=True)

    # Media (represented by resources wrapped in inline content elements)

    def _export_inline_image(self, context, element):
        return make_element(Image, image=element.image(), text=element.title())
