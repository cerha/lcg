# -*- coding: utf-8 -*-

# Copyright (C) 2008 Brailcom, o.p.s.
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
import urlparse

try:
    import reportlab.lib.fonts
    import reportlab.lib.styles
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

    def _init_fonts(self):
        self._fonts = {}
        for font in 'Serif', 'Sans', 'Mono':
            font_name = 'Free' + font
            i = 0
            if font == 'Serif':
                faces = ('', 'Italic', 'Bold', 'BoldItalic',)
            else:
                faces = ('', 'Oblique', 'Bold', 'BoldOblique',)
            for face in faces:
                font_face_name = font_name + face
                f = reportlab.pdfbase.ttfonts.TTFont(font_face_name, os.path.join(self._font_path, font_face_name) + '.ttf')
                reportlab.pdfbase.pdfmetrics.registerFont(f)
                reportlab.lib.fonts.addMapping(font_name, i/2, i%2, font_face_name)
                i = i + 1

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

    def get_seqid(self):
        """Increase counter value by 1 and return the new value.

        This enables access to internal counter that can be used to lease
        unique numbers for any purpose.
        
        """
        self._counter += 1
        return self._counter


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
        assert isinstance(self.content, unicode), ('type error', self.content,)
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
    def init(self):
        super(Paragraph, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, Text), ('type error', c,)
        self.content = list(self.content)
    def export(self, context, style=None):
        pdf_context = context.pdf_context
        style = copy.copy(style or self._style)
        if style is None:
            style = copy.copy(pdf_context.normal_style())
        style.leftIndent = pdf_context.nesting_level() * 1.5 * style.fontSize
        # Hack, should be handled better, preferrably in List only:
        style.bulletIndent = max(pdf_context.list_nesting_level() - 1, 0) * 1.5 * style.fontSize
        exported = ''
        for c in self.content:
            exported += c.export(context)        
        result = reportlab.platypus.Paragraph(exported, style)
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

class Container(Element):
    """Sequence of (almost) any objects.

    'content' is a sequence of 'Element' instances.

    This class serves for general grouping of elements.  Not all combinations
    may work.  Allowed content is unspecified in LCG now, it may get more
    restricted in future (not counting current implementation restrictions).

    """
    def init(self):
        if __debug__:
            for c in self.content:
                assert isinstance(c, Element), ('type error', c,)
    def export(self, context):
        result = []
        for c in self.content:
            if isinstance(c, Text):
                c = make_element(Paragraph, content=[c])
            exported = c.export(context)
            if isinstance(exported, (list, tuple,)):
                result += exported
            else:
                result.append(exported)
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        if self.content:
            self.content[0].prepend_text(text)
        else:
            text_element = make_element(Text, content=text)
            paragraph = make_element(Paragraph, content=[text_element])
            self.content = [paragraph]

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
        return u'<a name="%s"/>%s' % (self.name, exported_text,)

class Image(Element):
    """Image taken from a file.

    'content' is a URL (string) pointing to image source data.
    
    """
    def export(self, context):
        url_info = urlparse.urlparse(self.content)
        if url_info[0] in ('', 'file',):
            image_url = url_info[2]
            assert isinstance(image_url, str), ('type error', image_url,)
            result = reportlab.platypus.Flowable(image_url)
        else:
            result = make_element(Link, uri=self.content).export(context)
        return result

class Table(Element):
    """Table of rows and columns.

    'content' is a sequence of rows, each of them being a sequence of cells.
    Content of the cells is unspecified.

    """
    def init(self):
        super(Table, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, (list, tuple,)), ('type error', c,)
    def export(self, context):
        exported_content = [[column.export(context) for column in row] for row in self.content]
        return reportlab.platypus.Table(exported_content)

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
        if backref:
            content = self.link(content, "#"+backref)
        if anchor:
            content = self.anchor(content, anchor)
        return make_element(Heading, content=[content], level=level)

    def p(self, content, lang=None):
        if isinstance(content, Paragraph):
            return content
        return make_element(Paragraph, content=[content])

    def div(self, content, lang=None, **kwargs):
        if isinstance(content, Text):
            result = make_element(Paragraph, content=[content])
        else:
            result = content
        return content
    
    def list(self, items, ordered=False, style=None, lang=None):
        return make_element(List, content=items, ordered=ordered)
    
    def br(self):
        return make_element(SimpleMarkup, content='br')

    def hr(self):
        return make_element(PageBreak)

    # Links and images
    
    def link(self, label, uri, **kwargs):
        return make_element(Link, content=label, uri=uri)
    
    def anchor(self, label, name, **kwargs):
        return make_element(LinkTarget, content=label, name=name)

    def img(src, alt=None, descr=None, align=None, width=None, height=None, **kwargs):
        return make_element(Image, content=src)

    # Tables and definition lists

    def gtable(self, rows, title=None, lang=None):
        return make_element(Table, content=rows)

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
        output = cStringIO.StringIO()
        doc = reportlab.platypus.SimpleDocTemplate(output)
        doc.build(document)
        return output.getvalue()