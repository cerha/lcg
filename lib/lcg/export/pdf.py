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
import re
import string
import subprocess
import sys

import reportlab.lib.colors
import reportlab.lib.enums
import reportlab.lib.fonts
import reportlab.lib.pagesizes
import reportlab.lib.sequencer
import reportlab.lib.styles
import reportlab.lib.units
import reportlab.pdfbase.pdfmetrics
import reportlab.pdfbase.ttfonts
import reportlab.pdfgen
import reportlab.platypus
import reportlab.platypus.flowables
import reportlab.platypus.tableofcontents

import lcg
from lcg import *
from lcg.export import *

class PageTemplate(reportlab.platypus.PageTemplate):
    pass

class DocTemplate(reportlab.platypus.BaseDocTemplate):

    def __init__(self, *args, **kwargs):
        reportlab.platypus.BaseDocTemplate.__init__(self, *args, **kwargs)
        self._toc_sequencer = reportlab.lib.sequencer.Sequencer()
        self._toc_key_regexp = re.compile('<a name="([^"]+)"')
        self._new_lcg_context = None

    def handle_pageEnd(self):
        if self._new_lcg_context is None:
            next_template = 'Later'
        else:
            next_template = 'First'
            self._lcg_context = self._new_lcg_context
            self._new_lcg_context = None
        self._handle_nextPageTemplate(next_template)
        reportlab.platypus.BaseDocTemplate.handle_pageEnd(self)
        
    def afterFlowable(self, flowable):
        reportlab.platypus.BaseDocTemplate.afterFlowable(self, flowable)
        if isinstance(flowable, reportlab.platypus.Paragraph):
            style = flowable.style.name
            if style in ('Heading1', 'Heading2', 'Heading3',):
                text = flowable.getPlainText()
                level = int(style[7]) - 1
                match = self._toc_key_regexp.match(flowable.text)
                if match:
                    toc_key = match.group(1)
                else:
                    toc_key = None
                if level <= 1:
                    self.notify('TOCEntry', (level, text, self.page, toc_key,))
                if toc_key is None:
                    outline_key = 'heading-%s' % (self._toc_sequencer.next('tocheading'),)
                    # The position of the following bookmark is incorrect.  It
                    # (sometimes?) points to the next page after the element
                    # start.  As the bookmark can point only to a whole page
                    # and not to the exact element location, it's desirable to
                    # use toc_key whenever possible anyway.
                    self.canv.bookmarkPage(outline_key)
                else:
                    outline_key = toc_key
                self.canv.addOutlineEntry(text, outline_key, level=level, closed=(level>=1))

    def build(self, flowables, *args, **kwargs):
        context = self._lcg_context
        pdf_context = context.pdf_context
        pdf_context.page = 0
        first_page_header = pdf_context.first_page_header()
        page_header = pdf_context.page_header()
        page_footer = pdf_context.page_footer()
        page_background = pdf_context.page_background()
        def make_flowable(content):
            context = self._lcg_context
            pdf_context = context.pdf_context
            style = pdf_context.normal_style()
            flowable = content.export(context)
            if isinstance(flowable, Element):
                flowable = flowable.export(context)
            if isinstance(flowable, basestring):
                flowable = reportlab.platypus.Paragraph(unicode(flowable), style)
            while isinstance(flowable, (tuple, list,)):
                if len(flowable) == 1:
                    flowable = flowable[0]
                else:
                    flowable = RLTable([[f] for f in flowable])
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
            pdf_context = self._lcg_context.pdf_context
            pdf_context.page += 1
            page = pdf_context.page
            canvas.saveState()
            def add_flowable(content, position):
                flowable, width, height = make_flowable(content)
                x = (self.pagesize[0] - width) / 2
                if position == 'top':
                    y = self.height + self.bottomMargin - height
                elif position == 'bottom':
                    y = self.bottomMargin
                elif position == 'center':
                    y = self.bottomMargin + (self.height - height) / 2
                else:
                    raise Exception("Program error", position)
                flowable.drawOn(canvas, x, y)
            header = first_page_header
            if page > 1 or header is None:
                header = page_header
            if header is not None:
                add_flowable(header, 'top')
            if page_footer is not None:
                add_flowable(page_footer, 'bottom')
            if page_background is not None:
                add_flowable(page_background, 'center')
            canvas.restoreState()
        self._calc()
        Frame = reportlab.platypus.frames.Frame
        bottom_margin, height = frame_height((first_page_header or page_header), page_footer)
        first_frame = Frame(self.leftMargin, bottom_margin, self.width, height, id='first')
        bottom_margin, height = frame_height(page_header, page_footer)
        later_frame = Frame(self.leftMargin, bottom_margin, self.width, height, id='later')
        self.addPageTemplates([
            PageTemplate(id='First', frames=first_frame, onPage=on_page, pagesize=self.pagesize),
            PageTemplate(id='Later', frames=later_frame, onPage=on_page, pagesize=self.pagesize)
            ])
        reportlab.platypus.BaseDocTemplate.build(self, flowables,
                                                 canvasmaker=reportlab.pdfgen.canvas.Canvas)

    def multi_build(self, story, context=None, **kwargs):
        if context:
            self._lcg_context = context
        reportlab.platypus.BaseDocTemplate.multiBuild(self, story, **kwargs)

class RLTableOfContents(reportlab.platypus.tableofcontents.TableOfContents):
    def __init__(self, *args, **kwargs):
        if kwargs.has_key('context'):
            context = kwargs['context']
            del kwargs['context']
            presentation = context.pdf_context.current_presentation()
            font_size_coefficient = Context.default_font_size / 10.0
            presentation_name = None
            presentation_family = None
            if presentation is not None:
                font_size_coefficient *= (presentation.font_size or 1)
                presentation_name = presentation.font_name
                presentation_family = (presentation.heading_font_family or
                                       presentation.font_family or
                                       FontFamily.SERIF)
            font_name = context.pdf_context.font(presentation_name, presentation_family,
                                                 False, False)
        else:
            context = None
            font_size_coefficient = 1
            font_name = Context().font(None, FontFamily.SERIF, False, False)
        reportlab.platypus.tableofcontents.TableOfContents.__init__(self, *args, **kwargs)
        self.levelStyles = copy.copy(self.levelStyles)
        for i in range(len(self.levelStyles)):
            style = copy.copy(self.levelStyles[i])
            style.fontName = font_name
            style.fontSize *= font_size_coefficient
            if context is None:
                style.leading = style.fontSize * 1.2
            else:
                context.pdf_context.adjust_style_leading(style)
            self.levelStyles[i] = style

class RLTable(reportlab.platypus.Table):
    # The original Table class doesn't care much about determining unspecified
    # column widths.  This makes serious troubles with our horizontal
    # containers.  We avoid the most important problem by classifying at least
    # our tables as being of fixed width.
    # But beware, this can have problematic consequences in some cases.  There
    # is at least one situation where some table columns may get lost, probably
    # when using an unaligned vertical container within a table, possibly
    # accompanied by other circumstances.
    def _canGetWidth(self, thing):
        if isinstance(thing, RLTable):
            result = 1
        else:
            result = reportlab.platypus.Table._canGetWidth(self, thing)
        return result

class RLContainer(reportlab.platypus.flowables.Flowable):
    # Using tables for container management is actually not reasonably
    # manageable.  For this reason we introduce our own container object that
    # is much simpler than ReportLab alternatives such as Table or
    # KeepTogether.  The class is rather primitive but hopefully this is enough
    # to serve its purpose.
    BOX_CENTER = 'CENTER'
    BOX_TOP = 'TOP'
    BOX_BOTTOM = 'BOTTOM'
    BOX_LEFT = 'LEFT'
    BOX_RIGHT = 'RIGHT'
    def __init__(self, content, vertical=False, align=None):
        assert isinstance(content, (tuple, list,)), content
        assert isinstance(vertical, bool), vertical
        if __debug__:
            if vertical:
                assert align in (self.BOX_CENTER, self.BOX_LEFT, self.BOX_RIGHT, None,), align
            else:
                assert align in (self.BOX_CENTER, self.BOX_TOP, self.BOX_BOTTOM, None,), align
            for c in content:
                assert isinstance(c, reportlab.platypus.flowables.Flowable), (c, content,)
        reportlab.platypus.flowables.Flowable.__init__(self)
        self._box_content = content
        self._box_vertical = vertical
        self._box_align = align or self.BOX_CENTER
        # Another hack for pytis markup:
        if len(content) == 1:
            if getattr(content[0], 'hAlign', None):
                self.hAlign = content[0].hAlign
            else:
                self.hAlign = self._box_align
    def wrap(self, availWidth, availHeight):
        vertical = self._box_vertical
        if vertical:
            length_index = 1
            avail_length = availHeight
            fixed_attr = '_fixedHeight'
        else:
            length_index = 0
            avail_length = availWidth
            fixed_attr = '_fixedWidth'
        depth_index = 1 - length_index
        self._box_total_length = 0
        self._box_max_depth = 0
        variable_content = []
        self._box_lengths = []
        self._box_depths = []
        def wrap(content, i, width, height, store=True):
            content.canv = self.canv
            sizes = content.wrap(width, height)
            del content.canv
            if not store:
                return
            length = sizes[length_index]
            depth = sizes[depth_index]
            self._box_total_length += length
            self._box_max_depth = max(self._box_max_depth, sizes[depth_index])
            if i is None:
                self._box_lengths.append(length)
                self._box_depths.append(depth)
            else:
                self._box_lengths[i] = length
                self._box_depths[i] = depth
        i = 0
        for c in self._box_content:
            if getattr(c, fixed_attr):
                wrap(c, None, availWidth, availHeight)
            else:
                min_width = None
                if not vertical:
                    # It is necessary to call `wrap' in order to set the object
                    # minimum width in some flowables, e.g. TableOfContents.
                    c.canv = self.canv
                    wrap(c, None, availWidth, availHeight, store=False)
                    min_width = c.minWidth()
                variable_content.append((i, c, min_width,))
                self._box_lengths.append(None)
                self._box_depths.append(None)
            i += 1
        if variable_content:
            stop = False
            while not stop:
                stop = True
                avail = (avail_length - self._box_total_length) / len(variable_content)
                if vertical:
                    args = (availWidth, avail,)
                else:
                    args = (avail, availHeight,)
                stop = True
                for i, c, w in variable_content:
                    if w and w > avail and self._box_lengths[i] is None:
                        wrap(c, i, *args)
                        stop = False                
            for i, c, w in variable_content:
                wrap(c, i, *args)
        if vertical:
            result = (self._box_max_depth, self._box_total_length,)
        else:
            result = (self._box_total_length, self._box_max_depth,)
        return result
    def draw(self):
        canv = self.canv
        lengths = self._box_lengths
        vertical = self._box_vertical
        x = 0
        if vertical:
            y = self._box_total_length
        else:
            y = 0
        i = 0
        for c in self._box_content:
            align = self._box_align
            if vertical and getattr(c, 'hAlign', None):
                align = c.hAlign
            l = lengths[i]
            if vertical:
                y -= l
            x_shift = y_shift = 0
            if align == self.BOX_CENTER:
                shift = (self._box_max_depth - self._box_depths[i]) / 2
                if vertical:
                    x_shift = shift
                else:
                    y_shift = shift
            elif align == self.BOX_TOP:
                y_shift = self._box_max_depth - self._box_depths[i]
            elif align == self.BOX_RIGHT:
                x_shift = self._box_max_depth - self._box_depths[i]
            c.drawOn(canv, x + x_shift, y + y_shift)
            if not vertical:
                x += l
            i += 1

class RLText(reportlab.platypus.flowables.Flowable):
    # Paragraphs have variable dimensions and they don't work well when
    # wrapping simple texts for horizontal concatenation.  Tables can handle
    # simple texts without wrapping them by paragraphs, but they have other
    # problems (see RLContainer).  For this reason we implement a simple text
    # flowable to be used inside RLContainers.  No formatting, no wrapping,
    # just a piece of plain text with a style.
    _fixedWidth = 1
    _fixedHeight = 1
    def __init__(self, text, style, halign=None):
        reportlab.platypus.flowables.Flowable.__init__(self)
        self._text = text
        self._style = style
        if text:
            self.width = reportlab.pdfbase.pdfmetrics.stringWidth(text, style.fontName, style.fontSize)
            self.height = style.leading
        else:
            self.width = self.height = 0
        self.hAlign = halign or 'LEFT'
    def draw(self):
        if not self._text:
            return
        x = 0
        y = self.height - self._style.fontSize
        if self._style.textColor:
            self.canv.setFillColor(self._style.textColor)
        tx = self.canv.beginText(x, y)
        tx.setFont(self._style.fontName,
                  self._style.fontSize,
                  self._style.leading)
        tx.textLine(self._text)
        self.canv.drawText(tx)
    
class RLSpacer(reportlab.platypus.flowables.Spacer):
    def wrap(self, availWidth, availHeight):
        if self.width is None:
            width = availWidth
        else:
            width = min(self.width, availWidth)
        if self.height is None:
            height = availHeight-1e-8
        else:
            height = min(self.height, availHeight)
        return width, height

class RLImage(reportlab.platypus.flowables.Image):
    # This class is introduced to handle images exceeding page dimensions.
    # Its instance can't be used more than once in the document.
    def __init__(self, *args, **kwargs):
        self._last_avail_height = None
        reportlab.platypus.flowables.Image.__init__(self, *args, **kwargs)
    def wrap(self, availWidth, availHeight):
        if availWidth < self.drawWidth:
            # We allow any width compression.
            self._setup(min(availWidth, self.drawWidth), self.drawHeight,
                        kind='proportional', lazy=0)
        elif (availHeight < self.drawHeight and
              self._last_avail_height is not None and
              self._last_avail_height < availHeight):
            # We must be more careful with height compressions so that images
            # are not unnecessarily reduced at the end of page.
            self._setup(availWidth, min(availHeight, self.drawHeight),
                        kind='proportional', lazy=0)
        self._last_avail_height = availHeight
        return reportlab.platypus.flowables.Image.wrap(self, availWidth, availHeight)

class Context(object):
    """Place holder for PDF backend export state.

    An instance of this class is stored as a 'pdf_context' attribute of the LCG
    'Context' instance.

    """
    _registered_fonts = {}
    _registered_font_files = {}

    _nesting_level = 0
    _list_nesting_level = 0
    _counter = 0
    page = 0
    heading_level = 1
    toc_present = False
    default_font_size = 12
    left_indent = 0
    bullet_indent = 0
    last_element_category = None
    in_paragraph = False

    def __init__(self, parent_context=None, total_pages=0, first_page_header=None,
                 page_header=None, page_footer=None, page_background=None, presentation=None,
                 lang=None):
        self._lang = lang
        self._presentations = []
        self._init_fonts()
        self._init_styles()
        self._anchors = {}
        if presentation is not None:
            self._presentations.append(presentation)
        self._total_pages = total_pages
        self._total_pages_requested = False
        self._parent_context = parent_context
        self._first_page_header = first_page_header
        self._page_header = page_header
        self._page_footer = page_footer
        self._page_background = page_background
        if parent_context is not None:
            if self._first_page_header is None:
                self._first_page_header = parent_context.first_page_header()
            if self._page_header is None:
                self._page_header = parent_context.page_header()
            if self._page_footer is None:
                self._page_footer = parent_context.page_footer()
        self._relative_font_size = 1
        self._export_notes = []

    def _init_styles(self):
        self._styles = reportlab.lib.styles.getSampleStyleSheet()
        # Normal
        self._normal_style = copy.copy(self._styles['Normal'])
        self._normal_style.fontName = self.font(None, FontFamily.SERIF, False, False)
        self._normal_style.fontSize = self.default_font_size
        self._normal_style.bulletFontName = self._normal_style.fontName
        self._normal_style.bulletFontSize = self._normal_style.fontSize
        self.adjust_style_leading(self._normal_style)
        self._normal_style.firstLineIndent = self._normal_style.leading
        # Code
        self._code_style = copy.copy(self._styles['Code'])
        self._code_style.fontName = self.font(None, FontFamily.FIXED_WIDTH, False, False)
        self._code_style.fontSize = self.default_font_size
        self.adjust_style_leading(self._code_style)
        # Bullet
        self._styles['Bullet'].space_before = self.default_font_size / 2

    def _init_fonts(self):
        self._fonts = {}
        default_font = self.font(None, FontFamily.SERIF, False, False)
        try: # these objects are no longer present in newer ReportLab versions
            reportlab.platypus.tableofcontents.levelZeroParaStyle.fontName = default_font
            reportlab.platypus.tableofcontents.levelOneParaStyle.fontName = default_font
            reportlab.platypus.tableofcontents.levelTwoParaStyle.fontName = default_font
            reportlab.platypus.tableofcontents.levelThreeParaStyle.fontName = default_font
            reportlab.platypus.tableofcontents.levelFourParaStyle.fontName = default_font
        except AttributeError:
            pass

    def _find_font_file(self, name, family, bold, italic, lang):
        # It seems there fontconfig utilities are a bit buggy so we have to use
        # nonstraight ways of retrieving the font file.  It's prone to
        # fontconfig changes but we hardly can do much better unless we are
        # going to use fontconfig library directly.
        #
        # Find pattern
        if family == FontFamily.SERIF:
            family_pattern = 'serif'
        elif family == FontFamily.SANS_SERIF:
            family_pattern = 'sans-serif'
        elif family == FontFamily.FIXED_WIDTH:
            family_pattern = 'monospace'
        else:
            raise Exception('Unknown font family', presentation_family)
        if bold:
            bold_pattern = 'bold'
        else:
            bold_pattern = 'medium'
        if italic:
            italic_pattern = 'italic'
        else:
            italic_pattern = 'roman'
        if lang is None:
            language_pattern = ''
        else:
            language_pattern = ':lang=' + lang
        pattern = (':family=%s:weight=%s:slant=%s%s' %
                   (family_pattern, bold_pattern, italic_pattern, language_pattern,))
        # Retrieve preferred font.
        # Fontconfig is very weird.  For instance, in Fontconfig 2.8.0
        # `fc-match PATTERN' returns other result than the first item in
        # `fc-match --sort PATTERN'.  The former seems to give better results
        # so we first ask for the preferred font using `fc-match PATTERN' and
        # then try to use it if possible.
        # Oh, and expect fc-match output format changes among different
        # Fontconfig versions, there is nothing like stable documented output
        # format there.
        def read_from_process(process_args):
            p = subprocess.Popen(process_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 close_fds=True)
            output = ''
            while True:
                data = p.stdout.read()
                if not data:
                    break
                output += data
            p.stdout.close()
            return output
        output = read_from_process(['fc-match', '-v', pattern])
        re_file = re.compile('.*file: *"([^"]+\.ttf)"')
        for line in output.splitlines():
            match = re_file.match(line)
            if match:
                preferred_font_file = match.group(1)
                break
        else:
            preferred_font_file = None
        # Retrieve candidates
        output = read_from_process(['fc-match', '-v', '--sort', pattern])
        # Find matching font
        font_file = None
        default_font_file = None
        family_match = False
        family_string = 'family: "%s' % (name or '',)
        for line in output.splitlines():
            if line.find('family: ') >= 0:
                family_match = (line.find(family_string) >= 0)
            else:
                match = re_file.match(line)
                if match:
                    file_ = match.group(1)
                    if family_match:
                        if font_file is None or file_ == preferred_font_file:
                            font_file = file_
                            if file_ == preferred_font_file:
                                break
                    elif default_font_file is None:
                        default_font_file = file_
        # If there is no match, use a fallback font
        if font_file is None:
            font_file = default_font_file
        if font_file is None:
            if family == FontFamily.SERIF:
                family_name = 'Serif'
            elif family == FontFamily.SANS_SERIF:
                family_name = 'Sans'
            elif family == FontFamily.FIXED_WIDTH:
                family_name = 'Mono'
            if bold:
                bold_name = 'Bold'
            else:
                bold_name = ''
            if italic:
                if family == FontFamily.SERIF:
                    italic_name = 'Italic'
                else:
                    italic_name = 'Oblique'
            else:
                italic_name = ''
            font_file = ('/usr/share/fonts/truetype/freefont/Free%s%s%s.ttf' %
                         (family_name, bold_name, italic_name,))
        # That's all
        return font_file

    def _register_font(self, name, family, bold, italic, font_file):
        assert font_file
        font_name = self.font_name(name, family)
        font_face_name = '%s%s%s' % (font_name,
                                     bold and '_Bold' or '',
                                     italic and '_Italic' or '',)
        key = (font_name, bold, italic,)
        if Context._registered_fonts.has_key(key):
            assert Context._registered_fonts[key] == font_file, \
                   ("Inconsistent font definition", key, font_file,)
        else:
            if Context._registered_font_files.has_key(font_file):
                # ReportLab really doesn't like using the same font file more than once.
                font_face_name = Context._registered_font_files[font_file]
            else:
                f = reportlab.pdfbase.ttfonts.TTFont(font_face_name, font_file)
                reportlab.pdfbase.pdfmetrics.registerFont(f)
                Context._registered_font_files[font_file] = font_face_name
            reportlab.lib.fonts.addMapping(font_name, bold, italic, font_face_name)
            Context._registered_fonts[key] = font_file
        return font_face_name
        
    def font(self, name, family, bold, italic):
        """Return full font name for given arguments.

        Arguments:

          name -- name of the font (string), such as 'Free' or 'DejaVu'; it may
            also be 'None' in which case any suitable font is used
          family -- one of 'FontFamily' constants
          bold -- boolean
          italic -- boolean
          
        """
        assert family is not None
        key = (name, family, bold, italic,)
        font = self._fonts.get(key)
        if font is None:
            font_file = self._find_font_file(name, family, bold, italic, self._lang)
            font = self._fonts[key] = self._register_font(name, family, bold, italic, font_file)
        return font

    def font_parameters(self, font_name):
        """Return tuple (NAME, FAMILY, BOLD, ITALIC,) corresponding to given 'font_name'.

        Arguments:
        
          font-name -- font name as a string

        Raise 'KeyError' if the given name is not found.

        """
        for k, v in self._fonts.items():
            if v == font_name:
                return k
        else:
            raise KeyError(font_name)

    def font_name(self, name, family):
        """Return font name corresponding to given font name and family.

        Arguments:

          name -- font name as a string (such as 'Free' or 'DejaVu') or 'None'
            in which case default font is used
          family -- one of 'FontFamily' constants or 'None' (in
            which case default font name is returned)

        """
        assert family is not None
        font_name = (name or 'DEFAULT')
        name = '%s_%s' % (font_name, family,)
        return name

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
        style = copy.copy(self._normal_style)
        style.fontSize *= self.relative_font_size()
        self.adjust_style_leading(style)
        return style

    def code_style(self):
        """Return paragraph style for verbatim texts.
        """
        style = copy.copy(self._code_style)
        style.fontSize *= self.relative_font_size()
        self.adjust_style_leading(style)
        return style

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
        presentation = self.current_presentation()
        presentation_font_name = None
        presentation_font_family = None
        if presentation:
            presentation_font_name = presentation.font_name
            presentation_font_family = (presentation.heading_font_family or
                                        presentation.font_family or
                                        FontFamily.SERIF)
        style.fontName = self.font(presentation_font_name, presentation_font_family, False, False)
        style.fontSize *= (self.default_font_size / 10.0) * self.relative_font_size()
        self.adjust_style_leading(style)
        return style

    def list_style(self, order=None):
        """Return paragraph style for lists.

        Arguments:

          order -- None for an unordered list (bullet list) or one of allowed strings
            describing ordering style ('numeric', 'lower-alpha', 'upper-alpha').

        """
        style = copy.copy(self._styles['Bullet'])
        style.fontName = self.font(None, FontFamily.SERIF, False, False)
        style.fontSize = self.default_font_size
        style.bulletFontSize = style.fontSize
        self.adjust_style_leading(style)
        style.space_before = self.default_font_size / 2
        return style

    def style(self, style=None):
        """Return ReportLab style corresponding to the given context.

        Arguments:

          style -- style to use as a template; if 'None' then use normal style
        
        """
        style = copy.copy(style or self.normal_style())
        presentation = self.current_presentation()
        if presentation is not None:
            if presentation.font_size is not None:
                style.fontSize = style.fontSize * presentation.font_size
                self.adjust_style_leading(style)
            font_name, family, bold, italic = self.font_parameters(style.fontName)
            if presentation.font_name is not None:
                font_name = presentation.font_name
            if (presentation.font_family is not None and
                style.name != 'Code' and style.name[:7] != 'Heading'):
                family = presentation.font_family
            if presentation.bold is not None:
                bold = presentation.bold
            if presentation.italic is not None:
                italic = presentation.italic
            style.fontName = self.font(font_name, family, bold, italic)
        style.fontSize *= self.relative_font_size()
        self.adjust_style_leading(style)
        style.leftIndent = self.left_indent
        style.bulletFontSize = style.fontSize
        style.bulletIndent = self.bullet_indent
        if style.firstLineIndent != 0:
            style.firstLineIndent = style.leading
        return style

    def adjust_style_leading(self, style):
        """Adjust leading in 'style' according to current presentation.

        Arguments:

          style -- ReportLab style object

        """
        presentation = self.current_presentation()
        if presentation is None or presentation.line_spacing is None:
            coefficient = 1.2
        else:
            coefficient = presentation.line_spacing
        style.leading = style.fontSize * coefficient

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
        if self._parent_context:
            self._parent_context.register_anchor_reference(name)

    def clear_anchor_reference(self, name):
        """Mark anchor reference as valid.

        This means the given anchor actually exists in the document.

        Parameters:

          name -- name of the anchor, basestring
          
        """
        self._anchors[name] = True
        if self._parent_context:
            self._parent_context.clear_anchor_reference(name)            

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
                    elif attr == 'font_size':
                        last_value = getattr(current_presentation, attr)
                        if last_value is None:
                            last_value = 1
                        value = value * last_value
                    setattr(new_presentation, attr, value)
        self._presentations.append(new_presentation)

    def set_presentation(self, presentation):
        """Set 'presentation' as the current presentation.

        Unlike 'add_presentation' the presentation is set as it is and is not
        merged with current presentations.  The presentation must be removed
        from the presentation list using 'remove_presentation' method when the
        object it introduces is left.

        Arguments:

          presentation -- 'Presentation' to be applied; if 'None', current
            presentation is used instead
        
        """
        self._presentations.append(presentation)        

    def remove_presentation(self):
        """Remove the current presentation from the presentation list."""
        self._presentations.pop()

    def total_pages_requested(self):
        """Return whether it is necessary to know the total page number in this context."""
        return self._total_pages_requested

    def total_pages(self):
        """Return total number of pages of the given context.

        If the number is unknown, return 'None'.

        """
        self._total_pages_requested = True
        if self._parent_context is not None:
            self._parent_context.total_pages()
        return self._total_pages

    def first_page_header(self):
        """Return first page header markup."""
        return self._first_page_header

    def page_header(self):
        """Return page header markup."""
        return self._page_header

    def page_footer(self):
        """Return page footer markup."""
        return self._page_footer

    def page_background(self):
        """Return page background markup."""
        return self._page_background

    def relative_font_size(self):
        """Return global font size coefficient."""
        coefficient = self._relative_font_size
        if self._parent_context is not None:
            coefficient = coefficient * self._parent_context.relative_font_size()
        return coefficient

    def set_relative_font_size(self, coefficient):
        """Make default font size of this context to 'coefficient'."""
        self._relative_font_size = coefficient

    def export_notes(self):
        """Return sequence of export notes.

        Export notes are arbitrary strings put on a stack and they serve as
        information modifying the process of building pdf.py hierarchy of
        classes.  For instance, they can be used to prevent some
        transformations inside certain elements.

        """
        return tuple(self._export_notes)

    def append_export_note(self, note):
        """Add export note on the notes stack.

        Arguments:

          note -- the note, string

        """
        assert isinstance(note, str)
        self._export_notes.append(note)
        
    def pop_export_note(self):
        """Remove the last export note from the notes stack."""
        self._export_notes.pop()

def _ok_export_result(result):
    if not isinstance(result, (tuple, list,)) or not result:
        return True
    if isinstance(result[0], basestring):
        expected = 'string'
    else:
        expected = 'nonstring'
    for r in result[1:]:
        if isinstance(r, (tuple, list)):
            return False
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
    _CATEGORY = None
    
    content = None
    
    def init(self):
        """Initialize class.

        This method is called after instance attributes are set in
        'make_element' function.
        
        """
        pass
    def export(self, context, **kwargs):
        """Export this element and its contents into a reportlab document.

        Arguments:

          context -- LCG 'Context' instance
          kwargs -- class specific arguments
          
        """
        result = self._export(context, **kwargs)
        if self._CATEGORY is not None:
            context.pdf_context.last_element_category = self._CATEGORY
        return result
    def _export(self, context, **kwargs):
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
        elif isinstance(size, UAny):
            # TODO: This should produce flexible space, but for now we just
            # prevent it from breaking the document processing.
            points = None
        else:
            raise Exception('Not implemented', size)
        return points

class Text(Element):
    """Basic text.

    Its content is basestring (preferably unicode) or another 'Text' instance.
    No text may be placed into the document hierarchy directly; always use
    'Text' or one of its subclasses to store text into the document.

    """
    _CATEGORY = 'text'
    _replacements = (('&', '&amp;',),
                     ('<', '&lt;',),
                     ('>', '&gt;',),
                     )
    style = None
    halign = None
    def init(self):
        assert isinstance(self.content, (basestring, Text,)), ('type error', self.content,)
        if isinstance(self.content, basestring):
            for old, new in self._replacements:
                self.content = self.content.replace(old, new)
            # The following two lines of code are tricky.  In order to prevent
            # some coding issues with pytis data retrieved from the database we
            # must make sure that the result is unicode.  On the other hand we
            # shouldn't touch the original object unless needed, otherwise the
            # mysterious Context.translate method may stop produce texts from
            # symbolic labels.
            if not isinstance(self.content, unicode):
                self.content = unicode(self.content)
    def _export(self, context):
        content = self.content
        if isinstance(content, basestring):
            result = context.translate(self.content)
        else:
            result = content.export(context)
        assert _ok_export_result(result), ('wrong export', result,)
        result = unicode(result)
        if self.style is not None:
            result = RLText(result, self.style, halign=self.halign)
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        if isinstance(self.content, basestring):
            new_content = [text, copy.copy(self)]
            self.content = make_element(TextContainer, content=new_content)
        else:
            self.content.prepend_text(text)
    def plain_text(self):
        """Return true iff the text is plain text without markup."""
        if self.style is not None:
            return False
        if isinstance(self.content, Text):
            return self.content.plain_text()
        return True

class Empty(Text):
    """An empty content.

    Useful when 'Text' is required or expected, but there is no actual
    content to provide.  'content' value is ignored.
    
    """
    _CATEGORY = None
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
    def _export(self, context):
        exported = super(MarkedText, self)._export(context)
        start_mark = self.tag
        presentation = context.pdf_context.current_presentation()
        for k, v in self.attributes.items():
            start_mark += ' %s="%s"' % (k, v,)
        result = u'<%s>%s</%s>' % (start_mark, exported, self.tag,)
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        self.content.prepend_text(text)
    def plain_text(self):
        return False

class SimpleMarkup(Text):
    """In-paragraph markup without content.

    A typical example of such an element might be a line break.

    'content' is the tag name.  It can be optionally accompanied by
    'attributes' dictionary providing tag attribute names and values.

    """
    attributes = {}
    def init(self):
        assert isinstance(self.content, str), ('type error', self.content,)
    def _export(self, context):
        mark = self.content
        for k, v in self.attributes.items():
            mark += ' %s="%s"' % (k, v,)
        result = '<%s/>' % (mark,)
        return result
    def plain_text(self):
        return False

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
    def _expand_content(self):
        content = []
        for c in self.content:
            if isinstance(c, TextContainer):
                content += c._expand_content()
            else:
                content.append(c)
        return content
    def _export(self, context):
        pdf_context = context.pdf_context
        content = self._expand_content()
        result = u''
        for c in content:
            if isinstance(c, TextContainer):
                result += c.export(context)
            else:
                result += c.export(context)                
        if (not pdf_context.in_paragraph and
            not all([c.plain_text() for c in content])):
            style = pdf_context.style()
            style.firstLineIndent = 0
            result = reportlab.platypus.Paragraph(result, style)
        assert _ok_export_result(result), ('wrong export', result,)
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        self.content.insert(0, make_element(Text, content=text))
    def plain_text(self):
        result = True
        for c in self.content:
            if not c.plain_text():
                result = False
                break
        return result
    
class PreformattedText(Element):
    """Text to be output verbatim.

    'content' is a unicode object to be printed.
    
    """
    _CATEGORY = 'paragraph'
    def init(self):
        super(PreformattedText, self).init()
        assert isinstance(self.content, basestring), ('type error', self.content,)
    def _export(self, context):
        pdf_context = context.pdf_context
        style = pdf_context.style(pdf_context.code_style())
        space = reportlab.platypus.Spacer(0, self._unit2points(UFont(0.5), style))
        result = [space, reportlab.platypus.Preformatted(self.content, style), space]
        return result

class Paragraph(Element):
    """Paragraph of text.

    'content' is a sequence of 'Text' elements.

    \"Paragraph\" is used here in a wider sense, it's just a separated piece of
    text, possibly characterized by some style.  However mutual nesting the
    paragraphs is not allowed, paragraphs may only contain text elements.

    """
    _CATEGORY = 'paragraph'
    _style = None
    noindent = False
    presentation = None
    halign = None
    def init(self):
        super(Paragraph, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, Text), ('type error', c,)
        self.content = list(self.content)
    def _export(self, context, style=None):
        pdf_context = context.pdf_context
        assert not pdf_context.in_paragraph
        pdf_context.in_paragraph = True
        halign = self.halign
        presentation = self.presentation
        pdf_context.add_presentation(presentation)
        current_presentation = pdf_context.current_presentation()
        template_style = style or self._style or pdf_context.normal_style()
        style = pdf_context.style(style=template_style)
        if (self.noindent or
            (current_presentation and current_presentation.noindent) or
            halign or
            pdf_context.last_element_category != 'paragraph'):
            style.firstLineIndent = 0
        if (current_presentation and current_presentation.noindent and style.name[:7] != 'Heading'):
            style.spaceBefore = style.fontSize * 1.2
        if current_presentation and current_presentation.left_indent:
            style.leftIndent += self._unit2points(current_presentation.left_indent, style)
        if halign == HorizontalAlignment.LEFT:
            style.alignment = reportlab.lib.enums.TA_LEFT
        elif halign == HorizontalAlignment.RIGHT:
            style.alignment = reportlab.lib.enums.TA_RIGHT
        elif halign == HorizontalAlignment.CENTER:
            style.alignment = reportlab.lib.enums.TA_CENTER
        exported = ''
        for c in self.content:
            exported += c.export(context)
        assert _ok_export_result(exported), ('wrong export', exported,)
        result = reportlab.platypus.Paragraph(exported, style)
        pdf_context.remove_presentation()
        pdf_context.in_paragraph = False
        return result
    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        self.content.insert(0, make_element(Text, content=text))
        
class Heading(Paragraph):
    """Heading of a section, etc.

    'content' is the same as in 'Paragraph'.  Additionally heading 'level'
    property must be specified, as an int starting from 1 (the topmost level).
    
    """
    _CATEGORY = 'heading'
    level = None
    def init(self):
        super(Heading, self).init()
        assert isinstance(self.level, int), ('type error', self.level,)
    def _export(self, context):
        style = context.pdf_context.heading_style(self.level)
        maybe_break = reportlab.platypus.CondPageBreak(self._unit2points(UFont(5), style))
        heading = super(Heading, self)._export(context, style=style)
        return [maybe_break, heading]

class PageBreak(Element):
    """Unconditional page break.

    Its 'content' is ignored.

    """
    _CATEGORY = 'break'
    def _export(self, context):
        return reportlab.platypus.PageBreak()

class NewDocument(PageBreak):
    """Element with no real content marking end of a new document in series.

    This mark serves for transfering contexts to ReportLab formatting.  The
    content is LCG 'Content' instance to be transferred to the given place.
    
    """
    def init(self):
        super(NewDocument, self).init()
        assert isinstance(self.content, Exporter.Context), ('type error', self.content,)
    def _export(self, context):
        context = self.content
        def set_context(flowable, aW, aH, context=context):
            flowable.canv._doctemplate._new_lcg_context = context
        exported = [reportlab.platypus.flowables.CallerMacro(wrapCallable=set_context),
                    reportlab.platypus.PageBreak()]
        return exported

class HorizontalRule(Element):
    """Horizontal rule, similar to HTML <hr>.

    Its 'content' is ignored.

    """
    _CATEGORY = 'break'
    def _export(self, context):
        return reportlab.platypus.flowables.HRFlowable(width='100%')

class TableOfContents(Element):
    """Table of contents.

    This table of contents is complete and usually shouldn't be present in the
    document more than once.
    
    """
    _CATEGORY = 'paragraph'
    def _export(self, context):
        return RLTableOfContents(context=context)

class PageNumber(Text):
    """Page number.

    'total' parameter determines whether total number of pages should be output
    instead of the current page number.

    """
    # This implementation is an ugly hack to make the class a subclass of Text
    # easily, for the reasons of type checking and appropriate handling at
    # several places.
    total = False
    def init(self):
        pass
    def _export(self, context):
        pdf_context = context.pdf_context
        if self.total:
            total = pdf_context.total_pages()
            if total:
                text = str(total)
            else:
                text = '?'
        else:
            text = str(pdf_context.page)
        self.content = text
        Text.init(self)
        return Text._export(self, context)

class Space(Element):
    """Hard space.

    There is no content, instead there are two size parameters:

      width -- width of the space, 'Unit'
      height -- height of the space, 'Unit'

    """
    _CATEGORY = 'break'
    width = UMm(0)
    height = UMm(0)
    def _export(self, context):
        style = context.pdf_context.style()
        width = self._unit2points(self.width, style)
        height = self._unit2points(self.height, style)
        return RLSpacer(width, height)
        
class Container(Element):
    """Sequence of (almost) any objects.

    'content' is a sequence of 'Element' instances.

    This class serves for general grouping of elements.  Not all combinations
    may work.  Allowed content is unspecified in LCG now, it may get more
    restricted in future (not counting current implementation restrictions).

    """
    _CATEGORY = None
    presentation = None
    vertical = True
    halign = None
    valign = None
    def init(self):
        if __debug__:
            for c in self.content:
                assert isinstance(c, Element), ('type error', c,)
    def _export(self, context):
        pdf_context = context.pdf_context
        pdf_context.add_presentation(self.presentation)
        style = pdf_context.style()
        halign = self.halign
        # Let's first transform simple text elements into real exportable elements.
        def transform_content(c):
            if isinstance(c, basestring):
                c = make_element(Text, content=unicode(c), style=style, halign=halign)
            elif isinstance(c, Text):
                if c.style is None:
                    c.style = style
                    c.halign = halign
            return c
        content = [transform_content(c) for c in self.content]
        # If there is only a single element, unwrap it from the container.
        if len(self.content) == 1:
            content_element = self.content[0]
            if self.halign is not None and content_element.halign is None:
                content_element.halign = self.halign
            result = content_element.export(context)
            if not isinstance(result, (list, tuple,)):
                result = [result]
        # Otherwise perform standard export.
        else:
            # Export content elements and check the result.
            result = []
            for c in self.content:
                exported = c.export(context)
                if isinstance(exported, (list, tuple,)):
                    if __debug__:
                        for e in exported:
                            assert not isinstance(e, (tuple, list)), e
                    result += exported
                else:
                    result.append(exported)                    
            assert _ok_export_result(result), ('wrong export', result,)
            # If wrapping by a container is needed, create a ReportLab container.
            wrap = False
            for c in self.content:
                if (isinstance(c, Container) and
                    (c.vertical != self.vertical or
                     c.halign != self.halign or
                     c.valign != self.valign)):
                    wrap = True
                    break
            if wrap:
                if self.vertical:
                    align = self.halign
                else:
                    align = self.valign
                result = [RLContainer(content=result, vertical=self.vertical, align=align)]                
        # Export completed.
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
    'order' may be used to distinguish between several ordering styles (None
    for unordered (bulleted) lists or one of ('numeric', 'lower-alpha',
    'upper-alpha') for ordered lists.

    """
    _CATEGORY = 'block'
    order = False
    def init(self):
        super(List, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        self.content = list(self.content)
    def _export(self, context):
        pdf_context = context.pdf_context
        style = pdf_context.style(pdf_context.list_style(self.order))
        list_nesting_level = pdf_context.list_nesting_level()
        font_size = style.fontSize
        style.bulletIndent = (list_nesting_level + 1) * 1.5 * font_size
        if self.order:
            after_bullet = 1.5
        else:
            after_bullet = 1
        style.leftIndent = style.bulletIndent + after_bullet * font_size
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
        next_pdf_context.left_indent = style.leftIndent
        next_pdf_context.bullet_indent = style.bulletIndent
        next_context = copy.copy(context)
        next_context.pdf_context = next_pdf_context
        def make_item(item):
            # Prevent paragpraph indenting of text after bullet:
            next_pdf_context.last_element_category = 'list-item-start'
            item.prepend_text(bullet)
            if isinstance(item, Text):
                assert not next_pdf_context.in_paragraph
                next_pdf_context.in_paragraph = True
            exported = item.export(next_context)
            if isinstance(item, Text):
                next_pdf_context.in_paragraph = False
            if isinstance(item, Text):
                result = [reportlab.platypus.Paragraph(exported, style)]
            elif isinstance(item, Paragraph):
                result = [exported]
            elif isinstance(item, Container):
                result = exported
            else:
                raise Exception ('type error', item,)
            return result
        space = reportlab.platypus.Spacer(0, self._unit2points(UFont(0.5), style))
        result = [space]
        for item in self.content:
            result += make_item(item)
        result.append(space)
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
    def _export(self, context):
        exported_content = super(Link, self)._export(context)
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
    def _export(self, context):
        exported_text = super(LinkTarget, self)._export(context)
        context.pdf_context.clear_anchor_reference(self.name)
        result = u'<a name="%s"/>%s' % (self.name, exported_text,)
        return result

class Image(Element):
    """Image taken from an Image resource instance.

    'image' is an Image instance.  An additional argument 'text' may provide text description of
    the image in the form of base string.
    
    """
    _CATEGORY = 'block'
    def init(self):
        super(Image, self).init()
        assert isinstance(self.image, resources.Image), ('type error', self.image,)
        assert self.text is None or isinstance(self.text, basestring), ('type error', self.image,)
    def _export(self, context):
        filename = self.image.filename()
        if filename:
            result = RLImage(filename)
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
    'line_above' and 'line_below' indicate whether to put a horizontal line
    above or below the row, respectively.
    
    """
    line_above = None
    line_below = None
    def init(self):
        super(TableRow, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, TableCell), ('type error', c,)

class Table(Element):
    """Table of rows and columns.

    'content' is a sequence of 'TableRow's and 'HorizontalRule's.
    Cells are 'TableCell' instances.

    """
    _CATEGORY = 'block'
    presentation = None
    long = False
    column_widths = None
    compact = True
    halign = None
    valign = None
    bars = ()
    
    def init(self):
        super(Table, self).init()
        assert isinstance(self.content, (list, tuple,)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, (TableRow, HorizontalRule,)), ('type error', c,)
    def _export(self, context):
        pdf_context = context.pdf_context
        last_element_category = pdf_context.last_element_category
        pdf_context.add_presentation(self.presentation)
        content = self.content
        exported_content = []
        # Find out information about the table
        table_style_data = [('VALIGN', (0, 0), (-1, -1), 'TOP',)]
        number_of_rows = len(content)
        header_row_p = False
        alignments = []
        if number_of_rows > 1:
            if all([c.heading for c in content[0].content]):
                header_row_p = True
            row = content[1].content
            if row is not None:         # i.e. not a HorizontalSeparator
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
        # (In case of table style overlappings, last definition takes precedence.)
        black = reportlab.lib.colors.black
        style = pdf_context.style()
        font_name, family, bold, italic = pdf_context.font_parameters(style.fontName)
        bold_font = pdf_context.font(font_name, family, True, italic)
        table_style_data.append(('FONT', (0, 0), (-1, -1), style.fontName, style.fontSize))
        i = 0
        for row in content:
            if isinstance(row, HorizontalRule):
                table_style_data.append(('LINEABOVE', (0, i), (-1, i), 1, black,))
                continue
            if row.line_above:
                table_style_data.append(('LINEABOVE', (0, i), (-1, i), 1, black,))
            if row.line_below:
                table_style_data.append(('LINEBELOW', (0, i), (-1, i), 1, black,))
            row_content = []
            for j in range(len(row.content)):
                column = row.content[j]
                if isinstance(column, (list, tuple,)):
                    row_content += [c.export(context) for c in column]
                else:
                    kwargs = {}
                    p = None
                    if isinstance(column, TableCell):
                        p = Presentation()
                        if column.heading:
                            p.bold = True
                        if (column.align is not None and
                            (not alignments or column.align != alignments[j])):
                            table_style_data.append(('ALIGN', (j, i), (j, i), column.align.upper(),))
                        # If it is a layout table we need to work around
                        # misalignment caused by expansion of the table over
                        # the whole page width.
                        elif self.halign is not None and len(row.content) == 1:
                            table_style_data.append(('ALIGN', (j, i), (j, i), self.halign,))
                    # ReportLab can't take anything as a cell content, let's prepare for it
                    def simplify(exported_column):
                        if isinstance(exported_column, str):
                            result = unicode(exported_column)
                        elif isinstance(exported_column, (tuple, list,)):
                            exported_column = [simplify(x) for x in exported_column]
                            if len(exported_column) == 1:
                                result = exported_column[0]
                            elif all([isinstance(x, unicode) for x in exported_column]):
                                result = string.join(exported_column, ' ')
                            else:
                                result = []
                                for x in exported_column:
                                    if isinstance(x, unicode):
                                        para = make_element(Paragraph, content=[Text(content=x)])
                                        x = para.export(context)
                                    result.append(x)
                        else:
                            result = exported_column
                        return result
                    exported_column = simplify(column.export(context, **kwargs))
                    row_content.append(exported_column)
                    if (p is not None and
                        (p.bold is not None or p.italic is not None or
                         p.font_name is not None or p.font_family is not None or
                         p.font_size is not None)):
                        pdf_context.set_presentation(p)
                        s = pdf_context.style()
                        table_style_data.append(('FONT', (j, i), (j, i), s.fontName, s.fontSize))
                        pdf_context.remove_presentation()
            exported_content.append(row_content)
            i += 1
        # Add remaining presentation
        presentation = pdf_context.current_presentation()
        if presentation is not None:
            if presentation.separator_height:
                size = self._unit2points(presentation.separator_height, style)
                table_style_data.append(('LINEBELOW', (0, 0), (-1, -1), size, black,))
            if header_row_p and presentation.header_separator_height is not None:
                size = self._unit2points(presentation.header_separator_height, style)
                table_style_data.append(('LINEBELOW', (0, 0), (-1, 0), size, black,))
            elif presentation.separator_height:
                size = self._unit2points(presentation.separator_height, style)
                table_style_data.append(('LINEABOVE', (0, 0), (-1, 0), size, black,))
            if presentation.separator_width:
                size = self._unit2points(presentation.separator_width, style)
                table_style_data.append(('LINEAFTER', (0, 0), (-1, -1), size, black,))
                table_style_data.append(('LINEBEFORE', (0, 0), (-1, 0), size, black,))
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
        elif self.compact:
            table_style_data.append(('TOPPADDING', (0, 0), (-1, -1), 0,))
            table_style_data.append(('BOTTOMPADDING', (0, 0), (-1, -1), 0,))
        if self.compact:
            table_style_data.append(('LEFTPADDING', (0, 0), (-1, -1), 0,))
            table_style_data.append(('RIGHTPADDING', (0, 0), (-1, -1), 0,))
        if presentation is not None and presentation.boxed:
            table_style_data.append(('BOX', (0, 0), (-1, -1), 1, black,))
        for bar in self.bars:
            if bar == 0:
                table_style_data.append(('LINEBEFORE', (0, 0), (0, -1), 1, black,))
            else:
                table_style_data.append(('LINEAFTER', (bar-1, 0), (bar-1, -1), 1, black,))
        # Create the table instance
        repeat_rows = 0
        if self.long:
            # It may or needn't be a good idea to always use LongTable
            # unconditionally here.
            class_ = reportlab.platypus.LongTable
            if header_row_p:
                repeat_rows = 1
        else:
            class_ = RLTable
        if self.column_widths is None:
            column_widths = None
        else:
            column_widths = []
            for w in self.column_widths:
                if w is None:
                    column_widths.append(None)
                else:
                    column_widths.append(self._unit2points(w, style))
        table_style = reportlab.platypus.TableStyle(table_style_data)
        table = class_(exported_content, colWidths=column_widths, style=table_style,
                       repeatRows=repeat_rows, hAlign=(self.halign or 'CENTER'), vAlign=self.valign)
        if last_element_category == 'paragraph':
            space = make_element(Space, height=UFont(1))
            exported_space = space.export(context)
            table = [exported_space, table, exported_space]
            pdf_context.last_element_category = self._CATEGORY
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

    def _page_formatter(self, context, **kwargs):
        return make_element(PageNumber)
    
    def _total_pages_formatter(self, context, **kwargs):
        return make_element(PageNumber, total=True)
    
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

    def _content_export(self, context, element, collapse=True, presentation=None):
        content = element.content()
        if isinstance(content, (tuple, list,)):
            exported_content = [c.export(context) for c in content]
        else:
            exported_content = content.export(context)
        if collapse and isinstance(exported_content, (tuple, list,)):
            result_content = self.concat(*exported_content)
        else:
            result_content = exported_content
        if presentation is not None and collapse:
            if isinstance(result_content, basestring):
                result_content = make_element(Container,
                                              content=[make_element(Text, result_content)],
                                              presentation=presentation)
            else:
                result_content = make_element(Container, content=[result_content],
                                              presentation=presentation)
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
                        if isinstance(item, basestring):
                            item = make_element(Text, content=[item])
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
        face = context.pdf_context.font(None, FontFamily.FIXED_WIDTH, None, None)
        return self._markup(text, 'font', face=face)
     
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
        
    def export(self, context, old_contexts=None, presentation=None):
        first_pass = (old_contexts is None)
        if old_contexts is None:
            old_contexts = {}
        old = old_contexts.get(None)
        total_pages = 0
        if old is not None:
            total_pages = old.page
        node = context.node()
        lang = context.lang()
        context.pdf_context = old_contexts[None] = pdf_context = \
                              Context(total_pages=total_pages,
                                      first_page_header=node.first_page_header(lang),
                                      page_header=node.page_header(lang),
                                      page_footer=node.page_footer(lang),
                                      page_background=node.page_background(lang),
                                      presentation=node.presentation(lang),
                                      lang=lang)
        pdf_context.add_presentation(context.presentation())
        presentation = pdf_context.current_presentation()
	exported_structure = []
        first_subcontext = None
        for node in context.node().linear():
            node_id = node.id()
            if node_id[:7] == '__dummy':
                continue
            subcontext = self.context(node, lang)
            old = old_contexts.get(node_id)
            total_pages = 0
            if old is not None:
                total_pages = old.page
            subcontext.pdf_context = old_contexts[node_id] = pdf_subcontext = \
                                     Context(parent_context=pdf_context, total_pages=total_pages,
                                             first_page_header=node.first_page_header(lang),
                                             page_header=node.page_header(lang),
                                             page_footer=node.page_footer(lang),
                                             page_background=node.page_background(lang),
                                             presentation=presentation,
                                             lang=lang)
            # The subcontext serves twice: 1. when exporting node content;
            # 2. when exporting to ReportLab.  The question is how to transfer
            # the subcontext to the proper place in ReportLab formatting.  This
            # is not very easy and there may be some limitations.  We use a
            # special element that starts a new subdocument.
            if first_subcontext is None:
                first_subcontext = subcontext
            else:
                new_document = make_element(NewDocument, content=subcontext)
                exported_structure.append(new_document)
            title = node.title()
            if title.strip():
                exported_title = make_element(Heading, content=[make_element(Text, content=title)],
                                              level=0)
                exported_structure.append(exported_title)
            exported = node.content().export(subcontext)
            if isinstance(exported, (tuple, list,)):
                exported = self.concat(*exported)
            exported_structure.append(exported)
        if not exported_structure:
            return ''
        exported_content = self.concat(*exported_structure)
        document = exported_content.export(first_subcontext)
        if len(document) == 1 and isinstance(document[0], basestring):
            document = [reportlab.platypus.Paragraph(document[0], pdf_context.style())]
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
        while True:
            try:
                doc.multi_build(document, context=first_subcontext)
            except reportlab.platypus.doctemplate.LayoutError, e:
                if str(e).find('too large') >= 0:
                    pdf_context.set_relative_font_size(pdf_context.relative_font_size() / 1.2)
                    if pdf_context.relative_font_size() < 0.1:
                        log("Page content extremely large, giving up")
                        raise Exception("Content too large", e)
                    log("Page content too large, reducing it by %s" %
                        (pdf_context.relative_font_size(),))
                else:
                    raise
            else:
                break
        if first_pass and pdf_context.total_pages_requested():
            return self.export(context, old_contexts=old_contexts)
        return output.getvalue()
    
    def export_element(self, context, element):
        result = super(PDFExporter, self).export_element(context, element)
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
        return make_element(HorizontalRule)

    def _export_page_number(self, context, element):
        if element.total():
            result = make_element(PageNumber, total=True)
        else:
            result = make_element(PageNumber)
        return result

    def _export_hspace(self, context, element):
        return make_element(Space, width=element.size(context), height=UMm(0))

    def _export_vspace(self, context, element):
        return make_element(Space, height=element.size(context), width=UMm(0))

    # Container elements
    
    def _export_container(self, context, element):
        exported_content = self._content_export(context, element, collapse=False)
        return make_element(Container, content=exported_content,
                            vertical=(element.orientation() != 'HORIZONTAL'),
                            halign=element.halign(), valign=element.valign(),
                            presentation=element.presentation())

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
        pdf_context = context.pdf_context
        content = self.escape(element.title())
        anchor = element.anchor()
        if anchor:
            content = make_element(LinkTarget, content=content, name=anchor)
        backref = element.backref()
        if backref:
            content = self.link(content, "#"+backref)
        level = pdf_context.heading_level
        heading = make_element(Heading, content=[content], level=level)
        pdf_context.heading_level += 1
        inner_content = self._export_container(context, element)
        pdf_context.heading_level = level
        intro_space = make_element(Space, height=UFont(1))
        content = [intro_space, heading, inner_content]
        return make_element(Container, content=content)

    def _export_itemized_list(self, context, element):
        pdf_context = context.pdf_context
        pdf_context.append_export_note('list')
        content = self._content_export(context, element, collapse=False)
        pdf_context.pop_export_note()
        return make_element(List, content=content, order=element.order())

    def _export_definition_list(self, context, element):
        def make_item(title, description):
            if isinstance(title, Text):
                presentation = Presentation()
                presentation.bold = True
                title = make_element(Paragraph, content=[title], presentation=presentation)
            if isinstance(description, Text):
                presentation = Presentation()
                presentation.left_indent = UFont(2*1.2)
                description = make_element(Paragraph, content=[description],
                                           presentation=presentation, noindent=True)
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
        return make_element(Table, content=rows, compact=False)
            
    def _export_paragraph(self, context, element):
        # LCG interpretation of "paragraph" is very wide, we have to expect
        # anything containing anything.  The only "paragraph" meaning we use
        # here is that the content should be separated from other text.
        content = self._content_export(context, element)
        halign = element.halign()
        if isinstance(content, Text):
            paragraph = make_element(Paragraph, content=[content],
                                     presentation=element.presentation(),
                                     halign=halign)
        else:
            paragraph = make_element(Container, content=[content], halign=halign)
        return paragraph

    def _export_table_of_contents(self, context, element):
        pdf_context = context.pdf_context
        if pdf_context.toc_present:
            result = make_element(Space)
        else:
            result = make_element(TableOfContents)
            title = element.title()
            if title:
                heading = make_element(Paragraph, content=[self.strong(context, title)],
                                       noindent=True)
                result = self.concat(heading, result)
            result = self.concat(make_element(Space, height=UFont(1)), result)
            pdf_context.toc_present = True
        return result

    # Tables

    def _export_table(self, context, element):
        content = []
        for c in element.content():
            exported = c.export(context)
            if isinstance(exported, HorizontalRule):
                content.append(exported)
            else:
                content += exported.content
        return make_element(Table, content=content,
                            long=element.long(), compact=False,
                            column_widths=element.column_widths(),
                            bars=element.bars(),
                            halign=element.halign(),
                            presentation=element.presentation())

    def _export_table_row(self, context, element):
        def make_row():
            return make_element(TableRow, content=[c.export(context) for c in element.content()],
                                line_above=element.line_above(), line_below=element.line_below())
        if element.iterated():
            iterator = None
            try:
                make_row()
            except SubstitutionIterator.NotStartedError, e:
                iterator = e.iterator()
            if iterator is None:
                raise Exception("No table row iterator found")
            rows = []
            while iterator.next():
                rows.append(make_row())
            iterator.reset()
        else:
            rows = [make_row()]
        return make_element(Container, content=rows)

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
