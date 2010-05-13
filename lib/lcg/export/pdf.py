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
import urlparse

try:
    import reportlab.lib.colors
    import reportlab.lib.fonts
    import reportlab.lib.styles
    import reportlab.lib.units
    import reportlab.pdfbase.pdfmetrics
    import reportlab.pdfbase.ttfonts
    import reportlab.platypus
except ImportError, err:
    # Don't throw the exception in import time to prevent LCG's dependency on reportlab when the
    # PDF export is not actually used.  If used, the exception will be re-raised in run-time.
    class FakeReportlab(object):
        def __getattr__(self, name):
            raise err
    reportlab = FakeReportlab()

from lcg import *
from lcg.export import *


class Context(object):
    """Place holder for PDF backend export state.

    An instance of this class is stored as a 'pdf_context' attribute of the LCG
    'Context' instance.

    """
    
    _font_path = '/usr/share/fonts/truetype/freefont'

    _nesting_level = 0
    _list_nesting_level = 0
    _counter = 0

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

    def list_style(self, ordered=False):
        """Return paragraph style for lists.

        Arguments:

          ordered -- iff true, consider the list ordered
          
        """
        if ordered:
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
        assert isinstance(self.content, Text), ('type error', self.content,)
    def export(self, context):
        style = context.pdf_context.code_style()
        result = reportlab.platypus.Preformatted(self.content.export(context), style)
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
        # Hack, should be handled better, preferrably in List only:
        style.bulletIndent = max(pdf_context.list_nesting_level() - 1, 0) * 1.5 * style.fontSize
        exported = ''
        for c in self.content:
            exported += c.export(context)
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
        for c in self.content:
            if isinstance(c, Text):
                c = make_element(Paragraph, content=[c])
            exported = c.export(context)
            if isinstance(exported, (list, tuple,)):
                result += exported
            else:
                result.append(exported)
        pdf_context.remove_presentation()
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
    may be used to distinguish between ordered (numbered) lists and unordered
    (bulleted) lists.

    """
    ordered = False
    def init(self):
        super(List, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        self.content = list(self.content)
    def export(self, context):
        pdf_context = context.pdf_context
        style = pdf_context.list_style(self.ordered)
        list_nesting_level = pdf_context.list_nesting_level()
        font_size = style.fontSize
        style.bulletIndent = list_nesting_level * 1.5 * font_size
        style.leftIndent = style.bulletIndent + 1.5 * font_size
        if self.ordered:
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
        return u'<a name="%s"/>%s' % (self.name, exported_text,)

class Image(Element):
    """Image taken from a file.

    'content' is a URL (string) pointing to image source data.  An additional
    argument 'text' may provide text description of the image in the form of
    base string.
    
    """
    def init(self):
        super(Image, self).init()
        assert self.text is None or isinstance(self.text, basestring)
    def export(self, context):
        url_info = urlparse.urlparse(self.content)
        if url_info[0] in ('', 'file',):
            image_url = url_info[2]
            assert isinstance(image_url, str), ('type error', image_url,)
            result = reportlab.platypus.Flowable(image_url)
        else:
            content = make_element(Text, content=self.content)
            link = make_element(Link, uri=self.content, content=content)
            result = make_element(Paragraph, content=[link]).export(context)
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
    
class Table(Element):
    """Table of rows and columns.

    'content' is a sequence of rows, each of them being a sequence of cells.
    Cells are 'TableCell' instances.

    """
    def init(self):
        super(Table, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, (list, tuple,)), ('type error', c,)
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
            if all([c.heading for c in content[0]]):
                header_row_p = True
            row = content[1]
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
            row = content[i]
            if isinstance(row, PageBreak):
                table_style_data.append(('LINEABOVE', (0, i), (-1, i), 1, black,))
                continue
            row_content = []
            for j in range(len(row)):
                column = row[j]
                if isinstance(column, (list, tuple,)):
                    row_content += [c.export(context) for c in column]
                else:
                    if isinstance(column, TableCell):
                        if column.heading:
                            table_style_data.append(('FACE', (j, i), (j, i), bold_font,))
                        if column.align is not None and column.align != alignments[j]:
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
                table_style_data.append(('TOPPADDING', (0, 0), (-1, -1), size,))
                table_style_data.append(('BOTTOMPADDING', (0, 0), (-1, -1), size,))
            if header_row_p and presentation.header_separator_margin is not None:
                size = self._unit2points(presentation.header_separator_margin, style) / 2
                table_style_data.append(('TOPPADDING', (0, 0), (-1, 0), size,))
                table_style_data.append(('BOTTOMPADDING', (0, 0), (-1, 0), size,))
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


class PDFGenerator(Generator):

    def _translate(self, object):
        # to be implemented
        return object
            
    def _concat(self, items):
        result = ''
        for i in items:
            result += self._translate(i)
        return result
    
    def escape(self, text):
        return make_element(Text, content=text)

    def pre(self, text):
        return make_element(PreformattedText, content=text)

    def _markup(self, text, tag, **attributes):
        return make_element(MarkedText, content=text, tag=tag, attributes=attributes)

    def emphasize(self, text):
        return self._markup(text, 'i')

    def strong(self, text):
        return self._markup(text, 'strong')
    
    def fixed(self, text):
        return self._markup(text, 'font', face='FreeMono')
     
    def sup(self, text):
        return self._markup(text, 'super')
    
    def sub(self, text):
        return self._markup(text, 'sub')
    
    def underline(self, text):
        return self._markup(text, 'u')
    
    def citation(self, text):
        return self.emphasize(text)
    
    def quotation(self, text):
        return self.emphasize(text)

    # Sectioning

    def heading(self, title, level, anchor=None, backref=None):
        content = self.escape(title)
        # TODO: Make backreferences optional?
        if anchor:
            content = self.anchor(content, anchor)
        if backref:
            content = self.link(content, "#"+backref)
        return make_element(Heading, content=[content], level=level)

    def p(self, content, lang=None, presentation=None):
        # LCG interpretation of "paragraph" is very wide, we have to expect
        # anything containing anything.  The only "paragraph" meaning we use
        # here is that the content should be separated from other text.
        if not isinstance(content, Text):
            return content
        return make_element(Paragraph, content=[content], presentation=presentation)

    def div(self, content, lang=None, halign=None, valign=None, orientation=None,
            presentation=None, **kwargs):
        if isinstance(content, Text):
            result_content = make_element(Paragraph, content=[content], presentation=presentation)
            if presentation is not None and presentation.boxed:
                cell = make_element(Table_Cell, content=result_content)
                result_content = make_element(Table, content=[[cell]], presentation=presentation)
        elif (isinstance(content, (tuple, list,)) and
              (orientation == 'HORIZONTAL' or halign is not None or valign is not None)):
            def cell(content):
                return make_element(TableCell, content=c, align=halign, valign=valign)
            if orientation == 'HORIZONTAL':
                table_content = [[cell(c) for c in content]]
            else:
                table_content = [[cell(c)] for c in content]
            result_content = make_element(Table, content=table_content, presentation=presentation)
        else:
            result_content = content
        return result_content
    
    def list(self, items, ordered=False, style=None, lang=None):
        return make_element(List, content=items, ordered=ordered)
    
    def br(self):
        return make_element(SimpleMarkup, content='br')

    def hr(self):
        return self.new_page()

    def new_page(self):
        return make_element(PageBreak)

    def space(self, width, height):
        return make_element(Space, width=width, height=height)
    
    # Links and images
    
    def link(self, label, uri, **kwargs):
        if isinstance(label, basestring):
            label = make_element(Text, content=label)
        elif isinstance(label, Container):
            def filter_(c):
                if isinstance(c, Text):
                    result = [c]
                elif isinstance(c, basestring):
                    result = [make_element(Text, content=c)]
                elif isinstance(c, Image):
                    link_content = make_element(Text, content=(c.text or c.content))
                    result = [make_element(Link, content=link_content, uri=c.content)]
                else:
                    result = []
                return result
            filtered_content = label.expand(filter_)
            label = make_element(TextContainer, content=filtered_content)
        return make_element(Link, content=label, uri=uri)
    
    def anchor(self, label, name, **kwargs):
        return make_element(LinkTarget, content=label, name=name)

    def img(self, src, alt=None, descr=None, align=None, width=None, height=None, **kwargs):
        return make_element(Image, content=src, text=alt)

    # Tables and definition lists

    def th(self, content, align=None, lang=None):
        return make_element(TableCell, content=content, align=align, heading=True)
        
    def td(self, content, align=None, lang=None):
        return make_element(TableCell, content=content, align=align, heading=False)
        
    def table(self, content, title=None, cls=None, lang=None, long=False, column_widths=None,
              presentation=None):
        return make_element(Table, content=content, long=long, column_widths=column_widths,
                            presentation=presentation)

    def fset(self, items, lang=None):
        def make_item(title, description):
            content = [self._markup(title, 'i'),
                       make_element(Text, content=u': '),
                       make_element(Text, content=description)]
            return make_element(Paragraph, content=content)
        result_items = [make_item(title, description) for title, description in items]
        return make_element(Container, content=result_items)

    # Special methods

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
            g = context.generator()
            method = getattr(g, markup)
            result = method(exported)
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
        g = context.generator()
        return g.br()

    def _email_formatter(self, context, email, **kwargs):
        g = context.generator()
        return g.fixed(email)
    
    def format(self, context, text):
        if not hasattr(context, 'pdf_markup_stack'):
            context.pdf_markup_stack = []
        g = context.generator()
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
            starting_text = g.escape(text[pos:match.start()])
            insert_text(starting_text)
            markup = self._markup_handler(context, match)
            insert_text(markup)
            pos = match.end()
        final_text = g.escape(text[pos:])
        insert_text(final_text)
        self._open.reverse()
        x = self._open[:]
        for type in x:
            result.append(self._formatter(context, type, {}, close=True))
        return g.concat(*result)


class PDFExporter(FileExporter, Exporter):
    
    Generator = PDFGenerator
    Formatter = PDFMarkupFormatter

    _OUTPUT_FILE_EXT = 'pdf'
    
    def _uri_section(self, context, section, local=False):
        # Force all section links to be local, since there is just one output document.
        return super(PDFExporter, self)._uri_section(context, section, local=True)
    
    def _export(self, node, context):
        result = node.content().export(context)
        if isinstance(result, basestring):
            result = context.generator().p(result)
        return result

    def _finalize(self, context):
        return None
    
    def export(self, context):
        context.pdf_context = Context()
        generator_structure = super(PDFExporter, self).export(context)
        document = generator_structure.export(context)
        # It is necessary to check for invalid anchors before doc.build gets
        # called, otherwise Reportlab throws an ugly error.
        invalid_anchors = context.pdf_context.invalid_anchor_references()
        if invalid_anchors:
            sys.stderr.write("Error: Invalid internal links:\n")
            for a in invalid_anchors:
                sys.stderr.write("  #%s\n" % (a,))
            return ''
        output = cStringIO.StringIO()
        doc = reportlab.platypus.SimpleDocTemplate(output)
        doc.build(document)
        return output.getvalue()
