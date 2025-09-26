# -*- coding: utf-8 -*-

# Copyright (C) 2008-2017 OUI Technology Ltd.
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import
from future import standard_library
from builtins import range
from past.builtins import long
from past.utils import old_div

import copy
import decimal
import functools
import io
import inspect
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
import xml.etree.ElementTree

import reportlab.lib.colors
import reportlab.lib.enums
import reportlab.lib.fonts
import reportlab.lib.pagesizes
import reportlab.lib.sequencer
import reportlab.lib.styles
import reportlab.lib.units
import reportlab.lib.utils
import reportlab.pdfbase.pdfmetrics
import reportlab.pdfbase.ttfonts
import reportlab.pdfgen
import reportlab.platypus
import reportlab.platypus.flowables
import reportlab.platypus.tableofcontents
import reportlab.rl_config

import lcg
from lcg import FontFamily, UMm, UPoint, UPercent, UFont, USpace, UAny, HorizontalAlignment
from .export import Exporter, FileExporter

standard_library.install_aliases()
unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str

_ = lcg.TranslatableTextFactory('lcg')


MATHML_FORMATTER = 'jeuclid-cli'


class PageTemplate(reportlab.platypus.PageTemplate):
    pass


class DocTemplate(reportlab.platypus.BaseDocTemplate):

    def __init__(self, *args, **kwargs):
        reportlab.platypus.BaseDocTemplate.__init__(self, *args, **kwargs)
        self._toc_sequencer = reportlab.lib.sequencer.Sequencer()
        self._toc_key_regexp = re.compile('<a name="([^"]+)"')
        self._new_lcg_context = None
        self._context_number = 0

    def handle_pageEnd(self):
        if self._new_lcg_context is None:
            next_template = 'Later%d' % (self._context_number,)
        else:
            self._lcg_context = self._new_lcg_context
            self._new_lcg_context = None
            self._make_page_templates()
            next_template = 'First%d' % (self._context_number,)
        self._handle_nextPageTemplate(next_template)
        reportlab.platypus.BaseDocTemplate.handle_pageEnd(self)

    def afterFlowable(self, flowable):
        reportlab.platypus.BaseDocTemplate.afterFlowable(self, flowable)
        if isinstance(flowable, reportlab.platypus.Paragraph):
            style = flowable.style.name
            if style in (b'Heading1', b'Heading2', b'Heading3',):
                text = flowable.getPlainText()
                level = int(style[7]) - 1
                match = self._toc_key_regexp.match(flowable.text or '')
                if match:
                    toc_key = match.group(1)
                else:
                    toc_key = None
                if level <= 1:
                    self.notify('TOCEntry', (level, text, self.page, toc_key,))
                if toc_key is None:
                    outline_key = b'heading-%s' % (self._toc_sequencer.next('tocheading'),)
                    # The position of the following bookmark is incorrect.  It
                    # (sometimes?) points to the next page after the element
                    # start.  As the bookmark can point only to a whole page
                    # and not to the exact element location, it's desirable to
                    # use toc_key whenever possible anyway.
                    self.canv.bookmarkPage(outline_key)
                else:
                    outline_key = toc_key
                self.canv.addOutlineEntry(text, outline_key, level=level, closed=(level >= 1))

    def _make_page_templates(self):
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
                flowable = reportlab.platypus.Paragraph(unistr(flowable), style)
            while isinstance(flowable, (tuple, list)):
                if len(flowable) == 1:
                    flowable = flowable[0]
                else:
                    flowable = RLContainer(flowable, vertical=True)
            # Set max height so that header, footer and content have all chance to fit.
            max_height = old_div(self.height, 3)
            width, height = flowable.wrap(self.width, max_height)
            return flowable, width, height

        def frame_height(header, footer):
            bottom_margin = self.bottomMargin
            height = self.height
            separator_space = 0.5 * reportlab.lib.units.cm
            if header:
                _, _, header_height = make_flowable(header)
                if header_height > 0:
                    header_height = header_height + separator_space
                    height = height - header_height
            if footer:
                _, _, footer_height = make_flowable(footer)
                if footer_height > 0:
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
                x = old_div((self.pagesize[0] - width), 2)
                if isinstance(content, lcg.Container):
                    if content.halign() == lcg.HorizontalAlignment.LEFT:
                        x = self.leftMargin
                    elif content.halign() == lcg.HorizontalAlignment.RIGHT:
                        x = self.pagesize[0] - width - self.rightMargin
                if position == 'top':
                    y = self.height + self.bottomMargin - height
                elif position == 'bottom':
                    y = self.bottomMargin
                elif position == 'center':
                    y = self.bottomMargin + old_div((self.height - height), 2)
                else:
                    raise Exception("Program error", position)
                flowable.drawOn(canvas, x, y)
            if page_background is not None:
                # This must be added first, otherwise the object appears in
                # foreground rather than background.
                add_flowable(pdf_context.page_background(), 'center')
            header = pdf_context.first_page_header()
            if page > 1 or header is None:
                header = pdf_context.page_header()
            if header is not None:
                add_flowable(header, 'top')
            if page_footer is not None:
                add_flowable(pdf_context.page_footer(), 'bottom')
            canvas.restoreState()
        # Sizes of all headers and footers are assumed to be the same within
        # the same context.
        self._calc()
        Frame = reportlab.platypus.frames.Frame
        bottom_margin, height = frame_height((first_page_header or page_header), page_footer)
        n = self._context_number = self._context_number + 1
        first_frame = Frame(self.leftMargin, bottom_margin, self.width, height,
                            id=('first%d' % (n,)))
        bottom_margin, height = frame_height(page_header, page_footer)
        later_frame = Frame(self.leftMargin, bottom_margin, self.width, height,
                            id=('later%d' % (n,)))
        self.addPageTemplates([PageTemplate(id=('First%d' % (n,)), frames=first_frame,
                                            onPage=on_page, pagesize=self.pagesize),
                               PageTemplate(id=('Later%d' % (n,)), frames=later_frame,
                                            onPage=on_page, pagesize=self.pagesize)])

    def build(self, flowables, *args, **kwargs):
        self._make_page_templates()
        # It's necessary to reset the global ReportLab sequencer to prevent
        # occasional invalid item numbers in ordered lists of unrelated builds.
        reportlab.lib.sequencer.setSequencer(None)
        reportlab.platypus.BaseDocTemplate.build(self, flowables,
                                                 canvasmaker=reportlab.pdfgen.canvas.Canvas)

    def multi_build(self, story, context=None, **kwargs):
        if context:
            self._lcg_context = context
        reportlab.platypus.BaseDocTemplate.multiBuild(self, story, **kwargs)


class RLTableOfContents(reportlab.platypus.tableofcontents.TableOfContents):

    def __init__(self, *args, **kwargs):
        if 'context' in kwargs:
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
            else:
                presentation_family = FontFamily.SERIF
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
    # There are some problems with standard ReportLab tables, so we install
    # workarounds here.

    def _canGetWidth(self, thing):
        # The original Table class doesn't care much about determining unspecified
        # column widths.  This makes serious troubles with our horizontal
        # containers.  We avoid the most important problem by classifying at least
        # our tables as being of fixed width.
        # But beware, this can have problematic consequences in some cases.  There
        # is at least one situation where some table columns may get lost, probably
        # when using an unaligned vertical container within a table, possibly
        # accompanied by other circumstances.
        if isinstance(thing, RLTable):
            result = 1
        else:
            result = reportlab.platypus.Table._canGetWidth(self, thing)
        return result

    def _hasVariWidthElements(self, upToRow=None):
        # The original implementation includes fixed width columns in the test,
        # which is wrong.
        if upToRow is None:
            upToRow = self._nrows
        col_widths = self._colWidths
        for row in range(min(self._nrows, upToRow)):
            for col in range(self._ncols):
                if col_widths[col] is not None:
                    continue
                value = self._cellvalues[row][col]
                if not self._canGetWidth(value):
                    return 1
        return 0


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

    def __init__(self, content, vertical=False, align=None, boxed=False, box_margin=0,
                 box_width=None, box_color=None, box_radius=0, box_mask=None,
                 width=None, height=None, padding=None, background_color=None):
        assert isinstance(content, (tuple, list)), content
        assert isinstance(vertical, bool), vertical
        assert box_mask is None or (isinstance(box_mask, (tuple, list)) and
                                    len(box_mask) == 4 and
                                    all(isinstance(x, bool) for x in box_mask)), box_mask
        assert width is None or isinstance(width, (float, int, long, decimal.Decimal, UPercent)), \
            width
        assert height is None or isinstance(width, (float, int, long, decimal.Decimal, UPercent)), \
            height
        assert padding is None or isinstance(padding, (tuple, list,)) and len(padding) == 4, \
            padding
        if box_mask and box_radius:
            raise Exception("Unsupported combination of 'box_mask' and 'box_radius'.")
        if __debug__:
            if vertical:
                assert align in (self.BOX_CENTER, self.BOX_LEFT, self.BOX_RIGHT, None,), align
            else:
                assert align in (self.BOX_CENTER, self.BOX_TOP, self.BOX_BOTTOM, None,), align
            for c in content:
                assert isinstance(c, reportlab.platypus.flowables.Flowable), (c, content,)
        reportlab.platypus.flowables.Flowable.__init__(self)
        self._box_original_content = content
        self._box_content = [copy.copy(c) for c in content]
        self._box_vertical = vertical
        self._box_align = align or self.BOX_CENTER
        self._box_boxed = boxed
        if not boxed:
            box_margin = 0
            box_width = 0
            box_color = None
            box_radius = 0
            box_mask = None
        self._box_box_margin = box_margin
        self._box_box_width = box_width
        self._box_box_color = box_color
        self._box_box_radius = box_radius
        self._box_box_mask = box_mask
        self._box_last_split_height = None
        self._box_last_wrap = None
        self._width = width
        self._height = height
        self._fixedWidth = 1 if width else 0
        self._fixedHeight = 1 if width else 0
        self._padding = padding
        self._background_color = background_color
        self._total_fixed_length = None
        # Another hack for pytis markup:
        if len(content) == 1:
            if getattr(content[0], 'hAlign', None):
                self.hAlign = content[0].hAlign
            else:
                self.hAlign = self._box_align

    def wrap(self, availWidth, availHeight, siblings_fixed_length=None):
        self._box_last_wrap = availWidth, availHeight
        total_box_margin_size = [2 * self._box_box_margin, 2 * self._box_box_margin]
        padding = self._padding
        if padding:
            total_box_margin_size[0] += padding[1] + padding[3]
            total_box_margin_size[1] += padding[0] + padding[2]
        availWidth -= total_box_margin_size[0]
        availHeight -= total_box_margin_size[1]
        self._box_content = [copy.copy(c) for c in self._box_original_content]
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

        def fixed_length(content, length_index_):
            # TODO: This is quite a hack.  See below (where called) for the purpose.
            # Currently we recognize only the below enumerated flowables as fixed.
            # In future we will probably need to add more.  Maybe there is some
            # general rule for recognition of fixed content or we may need to add
            # a new public method implemented by flowables themselves.  For now,
            # we just want to be safe and enumerate the known classes.
            if isinstance(content, (RLContainer, RLImage)):
                sizes = (content._width, content._height)
            elif isinstance(content, RLSpacer):
                sizes = (content.width, content.height)
                sizes = (content.width, content.height)
            else:
                sizes = (None, None)
            length = sizes[length_index_]
            return length if length and not isinstance(length, UPercent) else 0

        def wrap(content, i, width, height, store=True):
            content.canv = getattr(self, 'canv', None)
            if ((isinstance(content, RLContainer) and
                 isinstance((content._width, content._height)[length_index], UPercent))):
                # Pass the sum of fixed siblings lengths to a container with a relative
                # size.  This allows us to compute the relative sizes from the space
                # remaining after all fixed sized siblings are counted.
                if self._total_fixed_length is None:
                    self._total_fixed_length = functools.reduce(
                        lambda size, c: size + fixed_length(c, length_index),
                        self._box_content, 0
                    )
                kwargs = dict(siblings_fixed_length=(length_index, self._total_fixed_length))
            else:
                kwargs = dict()
            sizes = content.wrap(width, height, **kwargs)
            del content.canv
            if not store:
                return
            length = sizes[length_index]
            depth = sizes[depth_index]
            assert length >= 0 and depth >= 0, ("Negative size", length, depth, content,)
            self._box_total_length += length
            self._box_max_depth = max(self._box_max_depth, sizes[depth_index])
            if i is None:
                self._box_lengths.append(length)
                self._box_depths.append(depth)
            else:
                self._box_lengths[i] = length
                self._box_depths[i] = depth
            return sizes

        def unwrap(i):
            self._box_total_length -= self._box_lengths[i]
            self._box_lengths[i] = None
            self._box_content[i] = self._box_original_content[i]
            return self._box_content[i]
        i = 0
        for c in self._box_content:
            if getattr(c, fixed_attr):
                wrap(c, None, availWidth, availHeight)
            else:
                min_width = None
                if ((not vertical and
                     not isinstance(c, RLTable) and
                     (not isinstance(c, RLSpacer) or c.width is not None))):
                    # It is necessary to call `wrap' in order to set the object
                    # minimum width in some flowables, e.g. TableOfContents.
                    # We don't do it on tables and flexible spacers, because
                    # they may consume all the space as minimum width.
                    wrap(c, None, availWidth, availHeight, store=False)
                    min_width = c.minWidth()
                variable_content.append((i, c, min_width,))
                self._box_lengths.append(None)
                self._box_depths.append(None)
            i += 1
        while variable_content:
            # Handling flexible size content is tricky with ReportLab.
            # Long tables are flexible and when they are higher than available
            # height they return the minimum height higher instead of the total
            # height.  If we believe the value and it can, despite exceeding
            # the height limit slightly, fit into a higher level container,
            # ReportLab will cut the long table to fit into the given height!
            # OTOH we can't be generous with space on the general level because
            # then e.g. flexible spacers might consume more space than is
            # desirable.  So we must be careful and hope the layout (or even
            # the content!) won't get destroyed here.
            wrapped = []
            average_avail = old_div((avail_length - self._box_total_length), len(variable_content))
            if average_avail < 0:
                average_avail = 0
            if vertical:
                # We process flexible vertical spacers in the end because they
                # must stretch over average height if other elements don't use
                # their average heights.
                variable_content = ([x for x in variable_content
                                     if not isinstance(x[1], RLSpacer) or x[1].height is not None] +
                                    [x for x in variable_content
                                     if isinstance(x[1], RLSpacer) and x[1].height is None])
                spacers_started = False
            for n in range(len(variable_content)):
                i, c, width = variable_content[n]
                if ((vertical and not spacers_started and
                     isinstance(c, RLSpacer) and c.height is None)):
                    average_avail = (old_div((avail_length - self._box_total_length),
                                     (len(variable_content) - n)))
                    if average_avail < 0:
                        average_avail = 0
                    spacers_started = True
                if vertical:
                    args = [availWidth, average_avail]
                else:
                    args = [average_avail, availHeight]
                w, h = wrap(c, i, *args)
                if (((vertical and h > average_avail) or
                     (not vertical and w > average_avail) or
                     (width and width > average_avail))):
                    max_avail = avail_length
                    for j in range(len(wrapped)):
                        variable_content[j] = (variable_content[j][0],
                                               unwrap(wrapped[j]),
                                               variable_content[j][2],)
                    for j in range(i):
                        if self._box_lengths[j] is not None:
                            max_avail -= self._box_lengths[j]
                    if max_avail >= 0:
                        avail = average_avail
                        while avail < max_avail:
                            c = unwrap(i)
                            avail = min(avail + old_div(max_avail, 10), max_avail)
                            args[length_index] = avail
                            sizes = wrap(c, i, *args)
                            if sizes[length_index] <= avail:
                                break
                    del variable_content[n]
                    break
                wrapped.append(i)
            else:
                break
        if vertical:
            width_height = [self._box_max_depth, self._box_total_length]
        else:
            width_height = [self._box_total_length, self._box_max_depth]
        for i, size in enumerate((self._width, self._height)):
            if isinstance(size, UPercent):
                avail_space = self._box_last_wrap[i]
                if siblings_fixed_length and siblings_fixed_length[0] == i:
                    avail_space -= siblings_fixed_length[1]
                size = size.size() * avail_space / 100
            if size is not None:
                # The explicitly specified size of the box already includes margin and padding.
                width_height[i] = size
            else:
                # The computed size is the content size, so padding and margin must be added.
                width_height[i] += total_box_margin_size[i]
        self._width_height = tuple(width_height)
        return self._width_height

    def split(self, availWidth, availHeight):
        if not self._box_vertical or not self._box_content:
            return []
        if self._box_last_wrap is None or self._box_last_wrap != (availWidth, availHeight,):
            self.wrap(availWidth, availHeight)
        i = 0
        height = self._box_box_margin * 2
        lengths = self._box_lengths
        while i < len(self._box_lengths):
            next_height = lengths[i]
            if height + next_height >= availHeight:
                break
            height += next_height
            i += 1

        def container(content):
            return RLContainer(content, vertical=self._box_vertical,
                               align=self._box_align, boxed=self._box_boxed)
        content = self._box_content
        if i == self._box_lengths:
            result = [self]
        elif isinstance(content[i], (RLContainer, reportlab.platypus.tables.LongTable)):
            result = [container(content[:i]), content[i], container(content[i + 1:])]
        elif i > 0:
            result = [container(content[:i]), container(content[i:])]
        else:
            result = []
        return result

    def draw(self):
        canv = self.canv
        lengths = self._box_lengths
        vertical = self._box_vertical
        box_margin = self._box_box_margin
        x = box_margin
        y = box_margin
        if vertical:
            y += self._box_total_length
        padding = self._padding
        if padding:
            x += padding[3]
            y += padding[2]
        if self._box_boxed:
            width, height = self._width_height
            radius = self._box_box_radius
            stroke = not self._box_box_mask
            fill = self._background_color is not None
            self.canv.saveState()
            if self._box_box_width is not None:
                self.canv.setLineWidth(self._box_box_width)
            if self._box_box_color is not None:
                self.canv.setStrokeColorRGB(*self._box_box_color)
            if fill:
                self.canv.setFillColorRGB(*self._background_color)
            if radius != 0:
                self.canv.roundRect(0, 0, width, height, radius, fill=fill, stroke=stroke)
            else:
                self.canv.rect(0, 0, width, height, fill=fill, stroke=stroke)
            if self._box_box_mask:
                top, right, bottom, left = self._box_box_mask
                if top:
                    self.canv.line(0, height, width, height)
                if right:
                    self.canv.line(width, height, width, 0)
                if bottom:
                    self.canv.line(width, 0, 0, 0)
                if left:
                    self.canv.line(0, 0, 0, height)
            self.canv.restoreState()
        i = 0
        for c in self._box_content:
            align = self._box_align
            if vertical and getattr(c, 'hAlign', None):
                align = c.hAlign
            length = lengths[i]
            if vertical:
                y -= length
            x_shift = y_shift = 0
            if align == self.BOX_CENTER:
                shift = old_div((self._box_max_depth - self._box_depths[i]), 2)
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
                x += length
            i += 1

    def __unicode__(self):
        result = ('RLContainer(vertical=%s, align=%s, boxed=%s):\n' %
                  (self._box_vertical, self._box_align, self._box_boxed,))
        for c in self._box_content:
            u = unistr(c)
            if u and u[-1] != '\n':
                u += '\n'
            result += ('  ----\n' + '\n'.join([' ' + l if l else '' for l in u.split('\n')]))
        return result


class RLText(reportlab.platypus.flowables.Flowable):
    # Paragraphs have variable dimensions and they don't work well when
    # wrapping simple texts for horizontal concatenation.  Tables can handle
    # simple texts without wrapping them by paragraphs, but they have other
    # problems (see RLContainer).  For this reason we implement a simple text
    # flowable to be used inside RLContainers.  No formatting, no wrapping,
    # just a piece of plain text with a style.
    _fixedWidth = 1
    _fixedHeight = 1

    def __init__(self, text, style, halign=None, baseline_shift=None, max_width=None):
        reportlab.platypus.flowables.Flowable.__init__(self)
        self._text = text.split('\n')
        self._style = style
        self._baseline_shift = baseline_shift or 0
        self.width = 0
        for i in range(len(self._text)):
            while True:
                width = reportlab.pdfbase.pdfmetrics.stringWidth(self._text[i], style.fontName,
                                                                 style.fontSize)
                if max_width is None or width <= max_width:
                    break
                text_length = len(self._text[i])
                cut_length = min(int(old_div(text_length * width, max_width)), text_length - 1)
                self._text[i] = self._text[i][:cut_length]
            self.width = max(self.width, width)
        self.height = style.leading * len(self._text)
        self.hAlign = halign or 'LEFT'

    def draw(self):
        x = 0
        y = self.height - self._style.fontSize
        if self._style.textColor:
            self.canv.setFillColor(self._style.textColor)
        for line in self._text:
            tx = self.canv.beginText(x, y + self._baseline_shift * self._style.fontSize)
            tx.setFont(self._style.fontName,
                       self._style.fontSize,
                       self._style.leading)
            tx.textLine(line)
            self.canv.drawText(tx)
            y -= self._style.leading

    def __unicode__(self):
        return 'RLText(%s)' % ('\n'.join(self._text),)


class RLSpacer(reportlab.platypus.flowables.Spacer):

    def __init__(self, *args, **kwargs):
        reportlab.platypus.flowables.Spacer.__init__(self, *args, **kwargs)
        if self.width is None:
            self._fixedWidth = 0
        if self.height is None:
            self._fixedHeight = 0

    def wrap(self, availWidth, availHeight):
        if self.width is None:
            width = availWidth
        else:
            width = min(self.width, availWidth)
        if self.height is None:
            height = availHeight - 1e-8
            if height < 0:
                height = 0
        else:
            height = min(self.height, availHeight)
        return width, height


class RLImage(reportlab.platypus.flowables.Image):
    # This class is introduced to handle images exceeding page dimensions and
    # to respect image resolution at least for some image formats.

    def __init__(self, *args, **kwargs):
        self._last_avail_height = None
        if 'uri' in kwargs:
            self._uri = kwargs['uri']
            kwargs = copy.copy(kwargs)
            del kwargs['uri']
        else:
            self._uri = None
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

    def _setup_inner(self):
        if self._width is None or self._height is None:
            # Let's try to set actual image size, based on the image parameters.
            try:
                import PIL
                img = PIL.Image.open(self.filename)
                img.load()
                w, h = img.size
                xdpi, ydpi = img.info.get('dpi', (None, None,))
                if self._width is None and xdpi:
                    self._width = old_div(w * reportlab.lib.units.inch, xdpi)
                if self._height is None and ydpi:
                    self._height = old_div(h * reportlab.lib.units.inch, ydpi)
            except Exception:
                pass
        reportlab.platypus.flowables.Image._setup_inner(self)

    def draw(self):
        reportlab.platypus.flowables.Image.draw(self)
        uri = self._uri
        if uri is not None:
            link_rect = (getattr(self, '_offs_x', 0),
                         getattr(self, '_offs_y', 0),
                         self.drawWidth,
                         self.drawHeight,)
            self.canv.linkURL(uri, link_rect, relative=1)


class Context(object):
    """Place holder for PDF backend export state.

    An instance of this class is stored as a 'pdf_context' attribute of the LCG
    'Context' instance.

    """

    def __init__(self, parent_context=None, total_pages=0, first_page_header=None,
                 page_header=None, page_footer=None, page_background=None, presentation=None,
                 presentation_set=None, page_size=None, left_margin=None, right_margin=None,
                 top_margin=None, bottom_margin=None, lang=None):
        reportlab.rl_config.invariant = 1
        self._lang = lang
        self._presentations = []
        self._tempdir = None
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
        self._page_size = page_size
        self._left_margin = left_margin
        self._right_margin = right_margin
        self._top_margin = top_margin
        self._bottom_margin = bottom_margin
        self._presentation_set = presentation_set
        self._styled_presentations = []
        if parent_context is not None:
            if self._first_page_header is None:
                self._first_page_header = parent_context.first_page_header()
            if self._page_header is None:
                self._page_header = parent_context.page_header()
            if self._page_footer is None:
                self._page_footer = parent_context.page_footer()
        self._relative_font_size = 1
        self._export_notes = []

    def __del__(self):
        if self._tempdir is not None:
            shutil.rmtree(self._tempdir, ignore_errors=True)

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
        self._normal_style.autoLeading = 'max'
        # Code
        self._code_style = copy.copy(self._styles['Code'])
        self._code_style.fontName = self.font(None, FontFamily.FIXED_WIDTH, False, False)
        self._code_style.fontSize = self.default_font_size
        self.adjust_style_leading(self._code_style)
        # Bullet
        self._styles['Bullet'].space_before = old_div(self.default_font_size, 2)
        # Label
        self._label_style = copy.copy(self._styles['Normal'])
        self._label_style.name = 'Label'
        self._label_style.fontName = self.font(None, FontFamily.SERIF, True, False)
        self._label_style.fontSize = self.default_font_size
        self.adjust_style_leading(self._label_style)

    def _init_fonts(self):
        self._fonts = {}
        default_font = self.font(None, FontFamily.SERIF, False, False)
        try:  # these objects are no longer present in newer ReportLab versions
            reportlab.platypus.tableofcontents.levelZeroParaStyle.fontName = default_font
            reportlab.platypus.tableofcontents.levelOneParaStyle.fontName = default_font
            reportlab.platypus.tableofcontents.levelTwoParaStyle.fontName = default_font
            reportlab.platypus.tableofcontents.levelThreeParaStyle.fontName = default_font
            reportlab.platypus.tableofcontents.levelFourParaStyle.fontName = default_font
        except AttributeError:
            pass

    @classmethod
    def reset(class_):
        """Initialize 'Context' class.

        This method must be run before every new use of 'Context' class.

        """
        # Global variables
        # Note: We can't initialize them simply on the class level, because
        # apparently they can under some unknown circumstances survive between
        # Wiking requests while corresponding ReportLab structures don't.  So
        # it may happen that the cached objects are no longer valid.
        Context._registered_fonts = {}
        Context._registered_font_files = {}
        # Single export variables
        Context._nesting_level = 0
        Context._list_nesting_level = 0
        Context._counter = 0
        Context.page = 0
        Context.heading_level = 1
        Context.toc_present = False
        Context.default_font_size = 12
        Context.left_indent = 0
        Context.bullet_indent = 0
        Context.last_element_category = None
        Context.in_paragraph = None
        Context.in_figure = False
        Context.anchor_prefix = ''

    def _find_font_file(self, name, family, bold, italic, lang):
        if name is None:
            name = 'Free'
        if name not in ('Free', 'DejaVu',):
            raise Exception("Unsupported font", name)
        if family == FontFamily.SERIF:
            family_name = 'Serif'
        elif family == FontFamily.SANS_SERIF:
            family_name = 'Sans'
        elif family == FontFamily.FIXED_WIDTH:
            family_name = 'SansMono' if name == 'DejaVu' else 'Mono'
        else:
            raise Exception("Unknown font family", family)
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
        if name == 'DejaVu':
            if bold:
                bold_name = '-' + bold_name
            elif italic:
                italic_name = '-' + italic_name
        for directory in ('/usr/share/fonts/truetype/dejavu',
                          '/usr/share/fonts/truetype/ttf-dejavu',
                          '/usr/share/fonts/truetype/freefont',
                          '/Library/Fonts',
                          '~/Library/Fonts'):
            font_file = os.path.join(os.path.expanduser(directory),
                                     '%s%s%s%s.ttf' % (name, family_name, bold_name, italic_name,))
            if os.access(font_file, os.R_OK):
                break
        else:
            raise Exception("No matching font found", (name, family_name, bold_name, italic_name,))
        return font_file

    def _register_font(self, name, family, bold, italic, font_file):
        assert font_file
        font_name = self.font_name(name, family)
        font_face_name = '%s%s%s' % (font_name,
                                     bold and '_Bold' or '',
                                     italic and '_Italic' or '',)
        key = (font_name, bold, italic,)
        if key in Context._registered_fonts:
            assert Context._registered_fonts[key] == font_file, \
                ("Inconsistent font definition", key, font_file, Context._registered_fonts[key],)
            font_face_name = Context._registered_font_files[font_file]
        else:
            f = reportlab.pdfbase.ttfonts.TTFont(font_face_name, font_file)
            # ReportLab really doesn't like using the same font file more than once.
            # But beware: Already registered fonts may probably disappear from ReportLab
            # in Wiking processes.
            if ((font_file in Context._registered_font_files and
                 f.fontName in reportlab.pdfbase.pdfmetrics.getRegisteredFontNames())):
                font_face_name = Context._registered_font_files[font_file]
            else:
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
            # It is necessary to register all bold/italic versions, to not
            # burden other code with further registrations, e.g. when making
            # in-paragraph marks.
            for b in False, True:
                for i in False, True:
                    k = (name, family, b, i,)
                    font_file = self._find_font_file(name, family, b, i, self._lang)
                    self._fonts[k] = self._register_font(name, family, b, i, font_file)
            font = self._fonts[key]
        return font

    def font_parameters(self, font_name):
        """Return tuple (NAME, FAMILY, BOLD, ITALIC,) corresponding to given 'font_name'.

        Arguments:

          font-name -- font name as a string

        Raise 'KeyError' if the given name is not found.

        """
        for k, v in list(self._fonts.items()):
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
        else:
            presentation_font_family = FontFamily.SERIF
        style.fontName = self.font(presentation_font_name, presentation_font_family, False, False)
        style.fontSize *= (self.default_font_size / 10.0) * self.relative_font_size()
        self.adjust_style_leading(style)
        return style

    def label_style(self):
        """Return paragraph style for labels, e.g. in definition lists.
        """
        style = copy.copy(self._label_style)
        style.fontSize *= self.relative_font_size()
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
        style.space_before = old_div(self.default_font_size, 2)
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
            if presentation.font_family is not None:
                family = presentation.font_family
            if presentation.bold is not None:
                bold = presentation.bold
            if presentation.italic is not None:
                italic = presentation.italic
            if family is None:
                family = FontFamily.SERIF
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
        if name not in self._anchors:
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
        return [k for k, v in list(self._anchors.items()) if not v]

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
            new_presentation = lcg.PresentationSet.merge_presentations((current_presentation,
                                                                        presentation,),
                                                                       override=('boxed',))
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

    def presentation_set(self):
        """Return 'lcg.PresentationSet' set in this context or 'None'."""
        return self._presentation_set

    def set_styled_presentation(self, element):
        """Set \"styled\" presentation based on the given 'element'.

        The presentation is determined using the presentation set of this
        context instance.

        Arguments:

          element -- element to use to find the appropriate presentation,
            'lcg.Content' instance

        """
        if self._presentation_set is None:
            presentation = None
        else:
            presentation = self._presentation_set.presentation(element, None)
        if self._styled_presentations and self._styled_presentations[-1] is presentation:
            result = None
        else:
            result = presentation
        self._styled_presentations.append(presentation)
        return result

    def unset_styled_presentation(self):
        """Remove previously set styled presentation."""
        self._styled_presentations.pop()

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

    def page_size(self):
        "Return page width and height in points."
        return self._page_size

    def left_margin(self):
        "Return left page margin width in points."
        return self._left_margin

    def right_margin(self):
        "Return right page margin width in points."
        return self._right_margin

    def top_margin(self):
        "Return top page margin width in points."
        return self._top_margin

    def bottom_margin(self):
        "Return bottom page margin width in points."
        return self._bottom_margin

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
        assert isinstance(note, basestring)
        self._export_notes.append(note)

    def pop_export_note(self):
        """Remove the last export note from the notes stack."""
        self._export_notes.pop()

    def tempdir(self):
        "Return directory to use for storing temporary data."
        if self._tempdir is None:
            self._tempdir = tempfile.mkdtemp()
        return self._tempdir


def _ok_export_result(result):
    if not isinstance(result, (tuple, list)) or not result:
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


_replacements = (('&', '&amp;',),
                 ('<', '&lt;',),
                 ('>', '&gt;',),
                 )


def _escape(text):
    for old, new in _replacements:
        text = text.replace(old, new)
    return text


def _unescape(text):
    for old, new in _replacements:
        text = text.replace(new, old)
    return text


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
    presentation = None

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
        pdf_context = context.pdf_context
        pdf_context.add_presentation(self.presentation)
        result = self._export(context, **kwargs)
        pdf_context.remove_presentation()
        if self._CATEGORY is not None:
            context.pdf_context.last_element_category = self._CATEGORY
        return result

    def _export(self, context, **kwargs):
        raise Exception('Not implemented')

    def prepend_text(self, text):
        """Prepend given 'text' to the front of the element contents.

        This method was introduced primarily to allow adding bullets to list
        paragraphs, etc.

        Arguments:

          text -- basestring to prepend

        """
        raise Exception('Not implemented')

    def _unit2points(self, size, style):
        if size is None:
            points = None
        elif isinstance(size, UMm):
            points = size.size() * reportlab.lib.units.mm
        elif isinstance(size, UPoint):
            points = size.size()
        elif isinstance(size, (UFont, USpace)):
            points = size.size() * style.fontSize
        elif isinstance(size, UAny):
            # TODO: This should produce flexible space, but for now we just
            # prevent it from breaking the document processing.
            points = None
        else:
            raise Exception('Not implemented', size)
        return points

    def _color2rgb(self, color):
        if color is None:
            rgb = None
        else:
            rgb = [float(x) / 255 for x in color.rgb()]
        return rgb

    def _wrapped_image(self, content):
        if isinstance(content, Container) and len(content.content) == 1:
            element = content.content[0]
            if isinstance(element, Image):
                return make_element(InlineImage, image=element.image, align=element.align)
            elif isinstance(element, Container):
                return self._wrapped_image(element)
            else:
                return None
        return None


class Text(Element):
    """Basic text.

    Its content is basestring (preferably unicode) or another 'Text' instance.
    No text may be placed into the document hierarchy directly; always use
    'Text' or one of its subclasses to store text into the document.

    """
    _CATEGORY = 'text'
    style = None
    halign = None
    baseline_shift = None

    def init(self):
        assert isinstance(self.content, (basestring, Text)), ('type error', self.content,)
        if isinstance(self.content, basestring):
            self.content = _escape(self.content)
            # The following two lines of code are tricky.  In order to prevent
            # some coding issues with pytis data retrieved from the database we
            # must make sure that the result is unicode.  On the other hand we
            # shouldn't touch the original object unless needed, otherwise the
            # mysterious Context.localize method may stop produce texts from
            # symbolic labels.
            if not isinstance(self.content, basestring):
                self.content = unistr(self.content)

    def _export(self, context):
        content = self.content
        if isinstance(content, basestring):
            result = context.localize(self.content)
        else:
            result = content.export(context)
        assert _ok_export_result(result), ('wrong export', result,)
        result = unistr(result)
        if self.style is not None or self.baseline_shift is not None:
            result = _unescape(result)
            result = RLText(result, self.style, halign=self.halign,
                            baseline_shift=self.baseline_shift)
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


class SimpleMarkup(Text):
    """In-paragraph markup without content.

    A typical example of such an element might be a line break.

    'content' is the tag name.  It can be optionally accompanied by
    'attributes' dictionary providing tag attribute names and values.

    """
    attributes = {}

    def init(self):
        assert isinstance(self.content, basestring), ('type error', self.content,)

    def _export(self, context):
        mark = self.content
        for k, v in list(self.attributes.items()):
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
        content = self.content = copy.copy(self.content)
        assert isinstance(content, list), ('type error', content,)
        for i in range(len(content)):
            c = content[i]
            image = self._wrapped_image(c)
            if image is None:
                assert isinstance(c, Text), ('type error', c,)
            else:
                content[i] = image

    def _expand_content(self):
        content = []
        for c in self.content:
            if isinstance(c, TextContainer) and not isinstance(c, MarkedText):
                content += c._expand_content()
            else:
                content.append(c)
        return content

    def _export(self, context):
        pdf_context = context.pdf_context
        content = self._expand_content()
        result = u''
        for c in content:
            result += c.export(context)
        if ((pdf_context.in_paragraph is None and
             not all([c.plain_text() for c in content]))):
            style = pdf_context.style()
            style.firstLineIndent = 0
            result = reportlab.platypus.Paragraph(result, style)
        elif isinstance(result, basestring) and self.style:
            result = RLText(_unescape(result), style=self.style, halign=self.halign)
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


class MarkedText(TextContainer):
    """Text wrapped by an in-paragraph markup.

    'content' must be a sequence of 'Text' instances.  Additionaly, 'tag' name
    of the markup is required, optionally accompanied by 'attributes'
    dictionary providing tag attribute names and values.

    """
    tag = None
    attributes = {}

    def init(self):
        super(MarkedText, self).init()
        assert isinstance(self.tag, basestring), ('type error', self.tag,)
        assert isinstance(self.attributes, dict)

    def export(self, context):
        return super(MarkedText, self).export(context)

    def _export(self, context):
        pdf_context = context.pdf_context
        in_paragraph = pdf_context.in_paragraph
        if in_paragraph is None:
            pdf_context.in_paragraph = []
        exported = super(MarkedText, self)._export(context)
        if in_paragraph is None:
            pdf_context.in_paragraph = in_paragraph
        start_mark = self.tag
        for k, v in list(self.attributes.items()):
            start_mark += ' %s="%s"' % (k, v,)
        result = u'<%s>%s</%s>' % (start_mark, exported, self.tag,)
        return result

    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        self.content.prepend_text(text)

    def plain_text(self):
        return False


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
    halign = None

    def init(self):
        super(Paragraph, self).init()
        assert isinstance(self.content, (list, tuple)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, Text), ('type error', c,)
        self.content = list(self.content)

    def _export(self, context, style=None):
        pdf_context = context.pdf_context
        assert pdf_context.in_paragraph is None
        pdf_context.in_paragraph = []
        halign = self.halign
        current_presentation = pdf_context.current_presentation()
        template_style = style or self._style or pdf_context.normal_style()
        style = pdf_context.style(style=template_style)
        if ((self.noindent or
             (current_presentation and current_presentation.noindent) or
             halign or
             pdf_context.last_element_category != 'paragraph')):
            style.firstLineIndent = 0
        if ((current_presentation and current_presentation.noindent and
             style.name[:7] != 'Heading' and style.name != 'Label')):
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
        if pdf_context.in_paragraph:
            image = pdf_context.in_paragraph.pop(0)
            assert isinstance(image, RLImage), image
            result = reportlab.platypus.ParagraphAndImage(result, image, side=image.rl_side)
            if pdf_context.in_paragraph:
                result = RLContainer(content=([result] + pdf_context.in_paragraph),
                                     vertical=True, align=pdf_context.in_paragraph[0].rl_side)
        pdf_context.in_paragraph = None
        return result

    def prepend_text(self, text):
        assert isinstance(text, Text), ('type error', text,)
        self.content.insert(0, make_element(Text, content=text))


class Label(Paragraph):
    """Label, e.g. in a definition list.

    'content' is the same as in 'Paragraph'.

    """
    _CATEGORY = 'label'

    def _style(self, context):
        return context.pdf_context.label_style()

    def _export(self, context):
        style = self._style(context)
        maybe_break = reportlab.platypus.CondPageBreak(self._unit2points(UFont(5), style))
        label = super(Label, self)._export(context, style=style)
        return [maybe_break, label]


class Heading(Label):
    """Heading of a section, etc.

    'content' is the same as in 'Paragraph'.  Additionally heading 'level'
    property must be specified, as an int starting from 1 (the topmost level).

    """
    _CATEGORY = 'heading'
    level = None

    def init(self):
        content = self.content = copy.copy(self.content)
        for i in range(len(content)):
            image = self._wrapped_image(content[i])
            if image is not None:
                content[i] = image
        super(Heading, self).init()
        assert isinstance(self.level, int), ('type error', self.level,)

    def _style(self, context):
        return context.pdf_context.heading_style(self.level)


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
    thickness = None
    color = None

    def _export(self, context):
        kwargs = {}
        if self.thickness:
            kwargs['thickness'] = self._unit2points(self.thickness, context.pdf_context.style())
        if self.color:
            kwargs['color'] = self._color2rgb(self.color)
        return reportlab.platypus.flowables.HRFlowable(width='100%', **kwargs)


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
    instead of the current page number.  If 'separator' parameter is given and
    'total' is true, output both numbers, separated by 'separator'
    (basestring).

    """
    # This implementation is an ugly hack to make the class a subclass of Text
    # easily, for the reasons of type checking and appropriate handling at
    # several places.
    total = False
    separator = None

    def init(self):
        pass

    def _export(self, context):
        pdf_context = context.pdf_context
        if self.total:
            total = pdf_context.total_pages()
            if total:
                text = unistr(total)
            else:
                text = '?'
            if self.separator is not None:
                text = unistr(pdf_context.page) + self.separator + text
        else:
            text = unistr(pdf_context.page)
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
    vertical = True
    halign = None
    valign = None
    width = None
    height = None
    padding = None

    def init(self):
        if __debug__:
            for c in self.content:
                assert isinstance(c, Element), ('type error', c,)

    def _export(self, context, parent_container=None):
        pdf_context = context.pdf_context
        style = pdf_context.style()
        halign = self.halign
        presentation = pdf_context.current_presentation()
        if presentation.font_color:
            style.textColor = self._color2rgb(presentation.font_color)
        # Let's first transform simple text elements into real exportable elements.

        def transform_content(c):
            if isinstance(c, basestring):
                c = make_element(Text, content=unistr(c), style=style, halign=halign,
                                 baseline_shift=presentation.baseline_shift)
            elif isinstance(c, Text):
                if c.style is None:
                    c.style = style
                    c.baseline_shift = presentation.baseline_shift
                    c.halign = halign
            return c
        for c in self.content:
            transform_content(c)
        # If there is only a single element, unwrap it from the container.
        boxed = presentation and presentation.boxed
        padding, width, height = self.padding, self.width, self.height
        if len(self.content) == 1 and not boxed and not padding and not width and not height:
            content_element = self.content[0]
            if self.halign is not None and getattr(content_element, 'halign', None) is None:
                content_element.halign = self.halign
            if isinstance(content_element, Container):
                kwargs = dict(parent_container=self)
            else:
                kwargs = {}
            result = content_element.export(context, **kwargs)
            if not isinstance(result, (list, tuple)):
                result = [result]
        # Otherwise perform standard export.
        else:
            # Export content elements and check the result.
            result = []
            for c in self.content:
                if isinstance(c, Container):
                    kwargs = dict(parent_container=self)
                else:
                    kwargs = {}
                exported = c.export(context, **kwargs)
                if isinstance(exported, (list, tuple)):
                    if __debug__:
                        for e in exported:
                            assert not isinstance(e, (tuple, list)), e
                    result += exported
                else:
                    result.append(exported)
            assert _ok_export_result(result), ('wrong export', result,)
            # If wrapping by a container is needed, create a ReportLab container.
            if len(result) > 1 or boxed or padding or width or height:
                if boxed or padding or width or height:
                    wrap = True
                elif parent_container is None:
                    wrap = (not self.vertical)
                elif (parent_container.vertical != self.vertical or
                      (parent_container.vertical and
                          self.halign is not None and
                       parent_container.halign != self.halign)):
                    wrap = True
                else:
                    wrap = False
                if wrap:
                    if self.vertical:
                        align = self.halign
                    else:
                        align = self.valign
                    if presentation and boxed:
                        box_color = self._color2rgb(presentation.box_color)
                        box_width = self._unit2points(presentation.box_width, style)
                        box_radius = self._unit2points(presentation.box_radius, style) or 0
                        box_margin = self._unit2points(presentation.box_margin, style) or 0
                    else:
                        box_color = None
                        box_width = None
                        box_radius = 0
                        box_margin = 0
                    result = [RLContainer(
                        content=result, vertical=self.vertical, align=align,
                        width=(width if isinstance(width, UPercent)
                               else self._unit2points(width, style)),
                        height=(height if isinstance(height, UPercent)
                                else self._unit2points(height, style)),
                        padding=padding and [self._unit2points(x, style) for x in padding],
                        boxed=boxed,
                        box_color=box_color,
                        box_width=box_width,
                        box_radius=box_radius,
                        box_margin=box_margin,
                        box_mask=boxed and presentation and presentation.box_mask,
                        background_color=self._color2rgb(presentation.background_color),
                    )]
        # Enforce upper alignment
        if halign and len(result) == 1 and hasattr(result[0], 'hAlign'):
            result[0].hAlign = halign
        # Export completed.
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
        assert isinstance(self.content, (list, tuple)), ('type error', self.content,)
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
        if self.order == 'numeric':
            seqid = pdf_context.get_seqid()
            bullet_element = make_element(TextContainer, content=[
                make_element(SimpleMarkup, content='seq', attributes=dict(id='list%d' % (seqid,))),
                make_element(Text, content=u'.'),
            ])
        elif self.order is None:
            if list_nesting_level == 0:
                bullet_string = u'•'
            else:
                bullet_string = u'-'
            bullet_element = make_element(Text, content=bullet_string)
        else:
            bullet_element = None
        next_pdf_context = copy.copy(pdf_context)
        next_pdf_context.inc_nesting_level()
        next_pdf_context.inc_list_nesting_level()
        next_pdf_context.left_indent = style.leftIndent
        next_pdf_context.bullet_indent = style.bulletIndent
        next_context = copy.copy(context)
        next_context.pdf_context = next_pdf_context

        def make_item(i, item):
            # Prevent paragpraph indenting of text after bullet:
            next_pdf_context.last_element_category = 'list-item-start'
            if self.order in ('lower-alpha', 'upper-alpha'):
                letters = (string.ascii_lowercase if self.order == 'lower-alpha' else
                           string.ascii_uppercase)
                bullet = make_element(Text, content=letters[i] + u')')
            else:
                bullet = bullet_element
            item.prepend_text(make_element(MarkedText, content=[bullet], tag='bullet'))
            if isinstance(item, Text):
                assert next_pdf_context.in_paragraph is None
                next_pdf_context.in_paragraph = True
            exported = item.export(next_context)
            if isinstance(item, Text):
                next_pdf_context.in_paragraph = None
            if isinstance(item, Text):
                result = [reportlab.platypus.Paragraph(exported, style)]
            elif isinstance(item, Paragraph):
                result = [exported]
            elif isinstance(item, Container):
                result = exported
            else:
                raise Exception('type error', item,)
            return result
        space = reportlab.platypus.Spacer(0, self._unit2points(UFont(0.5), style))
        result = [space]
        for i, item in enumerate(self.content):
            result += make_item(i, item)
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


class ImageBase(Element):
    filename = None
    width = None
    height = None
    align = None

    def init(self):
        super(ImageBase, self).init()
        assert isinstance(self.image, lcg.resources.Image), ('type error', self.image,)
        assert self.filename is None or isinstance(self.filename, basestring), \
            ('type error', self.filename,)
        assert self.width is None or isinstance(self.width, lcg.Unit), self.width
        assert self.height is None or isinstance(self.height, lcg.Unit), self.height
        assert self.align is None or isinstance(self.align, basestring), self.align

    def _size(self, context, filename):
        style = context.pdf_context.style()
        if self.width is not None and self.height is not None:
            width, height = (self._unit2points(x, style) for x in (self.width, self.height))
        else:
            img = reportlab.lib.utils.ImageReader(filename)
            img_width, img_height = img.getSize()
            if self.width is not None:
                width = self._unit2points(self.width, style)
                height = old_div(width * img_height, img_width)
            elif self.height is not None:
                height = self._unit2points(self.height, style)
                width = old_div(height * img_width, img_height)
            else:
                width, height = img_width, img_height
        return width, height


class InlineImage(ImageBase, Text):
    """Image inside a paragraph.

    'image' is an Image instance.

    """
    resize = None

    def init(self):
        self.content = ''
        super(InlineImage, self).init()
        assert self.resize is None or isinstance(self.resize, float), self.resize

    def plain_text(self):
        return False

    def _export(self, context):
        image = self.image
        if image is None:
            context.log(_("Missing image: %s", self.uri), kind=lcg.ERROR)
            return ''
        filename = image.src_file()
        if not filename:
            content = image.get()
            if content:
                filename = io.BytesIO(content)
        if not filename:
            filename = self.filename
        if filename:
            align = self.align
            pdf_context = context.pdf_context
            if align in (None, lcg.InlineImage.LEFT, lcg.InlineImage.RIGHT,):
                alignment = ' valign="text-top"'
            elif isinstance(align, (int, float)):
                alignment = ' valign="%s"' % (align,)
            else:
                mapping = {
                    lcg.InlineImage.TOP: 'valign="top"',
                    lcg.InlineImage.BOTTOM: 'valign="bottom"',
                    lcg.InlineImage.MIDDLE: 'valign="center"',
                }
                alignment = ' ' + mapping[align]
            width, height = self._size(context, filename)
            if self.width is None and self.height is None:
                resize = self.resize
                if resize is not None:
                    width, height = width * resize, height * resize
                else:
                    page_width, page_height = context.pdf_context.page_size()
                    max_width, max_height = page_width * 0.5, page_height * 0.5
                    if width > max_width:
                        height *= (old_div(max_width, width))
                        width = max_width
                    if height > max_height:
                        width *= (old_div(max_height, height))
                        height = max_height
            if ((isinstance(pdf_context.in_paragraph, list) and
                 align in (lcg.InlineImage.LEFT, lcg.InlineImage.RIGHT,))):
                rl_image = RLImage(filename, width=width, height=height)
                rl_image.rl_side = align
                pdf_context.in_paragraph.append(rl_image)
                result = ''
            else:
                result = (u'<img src="%s"%s width="%s" height="%s"/>' %
                          (filename, alignment, width, height))
        else:
            result = image.title() or image.filename()
        return result


class Image(ImageBase):
    """Image taken from an Image resource instance.

    'image' is an Image instance.  An additional argument 'text' may provide text description of
    the image in the form of base string.

    """
    _CATEGORY = 'block'
    uri = None

    def init(self):
        super(Image, self).init()
        assert self.uri is None or isinstance(self.uri, basestring), ('type error', self.uri,)

    def _export(self, context):
        image = self.image
        if image is None:
            context.log(_("Missing image: %s", self.uri), kind=lcg.ERROR)
            dummy_comment = [make_element(Text, content='[image]')]
            return make_element(Paragraph, content=dummy_comment).export(context)
        filename = image.src_file()
        if not filename:
            content = image.get()
            if content:
                filename = io.BytesIO(content)
        if not filename:
            filename = self.filename
        if filename:
            width, height = self._size(context, filename)
            result = RLImage(filename, uri=self.uri, width=width, height=height)
        else:
            content = make_element(Text, content=(image.title() or image.filename()))
            result = make_element(Paragraph, content=[content]).export(context)
        return result


class SVGDrawing(Element):

    def _export(self, context):
        from svglib.svglib import svg2rlg
        svg = self.svg
        if b'Created with matplotlib' in svg[:200]:
            factor = 1 / context.exporter().MATPLOTLIB_RESCALE_FACTOR
        else:
            factor = 1
        drawing = svg2rlg(io.BytesIO(svg))
        page_width = context.pdf_context.page_size()[0]
        if drawing.width * factor > page_width:
            factor *= page_width / (drawing.width * factor)
        drawing.scale(factor, factor)
        drawing.width *= factor
        drawing.height *= factor
        # If the SVG is wider than page width, we scale it down to fit
        # the page width, but it may still exceed to page margins.  The
        # initial position aligns with the left margin so we need to
        # shift it to the left in order to overlap equally on both
        # sides.
        width = page_width - context.pdf_context.left_margin() - context.pdf_context.right_margin()
        overlap = drawing.width - width
        if overlap > 0:
            drawing.shift(-1 * overlap / 2.0, 0)
        return drawing


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
        assert isinstance(self.content, (list, tuple)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, TableCell), ('type error', c,)


class Table(Element):
    """Table of rows and columns.

    'content' is a sequence of 'TableRow's and 'HorizontalRule's.
    Cells are 'TableCell' instances.

    """
    _CATEGORY = 'block'
    long = False
    column_widths = None
    compact = True
    halign = None
    valign = None
    bars = ()

    def init(self):
        super(Table, self).init()
        assert isinstance(self.content, (list, tuple)), ('type error', self.content,)
        if __debug__:
            for c in self.content:
                assert isinstance(c, (TableRow, HorizontalRule)), ('type error', c,)

    def _export(self, context):
        pdf_context = context.pdf_context
        last_element_category = pdf_context.last_element_category
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
        if header_row_p:
            p = lcg.Presentation()
            p.bold = True
            pdf_context.add_presentation(p)
            header_style = pdf_context.style()
            pdf_context.remove_presentation()
        font_name, family, bold, italic = pdf_context.font_parameters(style.fontName)
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
                if isinstance(column, (list, tuple)):
                    row_content += [c.export(context) for c in column]
                else:
                    kwargs = {}
                    p = None
                    if isinstance(column, TableCell):
                        p = lcg.Presentation()
                        if column.heading:
                            p.bold = True
                        if ((column.align is not None and
                             (not alignments or column.align != alignments[j]))):
                            table_style_data.append(('ALIGN', (j, i), (j, i),
                                                     column.align.upper(),))
                        # If it is a layout table we need to work around
                        # misalignment caused by expansion of the table over
                        # the whole page width.
                        elif self.halign is not None and len(row.content) == 1:
                            table_style_data.append(('ALIGN', (j, i), (j, i), self.halign,))
                    # ReportLab can't take anything as a cell content, let's prepare for it

                    def simplify(exported_column):
                        if isinstance(exported_column, basestring):
                            result = unistr(exported_column)
                        elif isinstance(exported_column, (tuple, list)):
                            exported_column = [simplify(x) for x in exported_column]
                            if len(exported_column) == 1:
                                result = exported_column[0]
                            elif all(isinstance(x, basestring) for x in exported_column):
                                result = ' '.join(exported_column)
                            else:
                                result = []
                                for x in exported_column:
                                    if isinstance(x, basestring):
                                        para = make_element(Paragraph, content=[Text(content=x)])
                                        x = para.export(context)
                                    result.append(x)
                        else:
                            result = exported_column
                        return result
                    exported_column = simplify(column.export(context, **kwargs))
                    if isinstance(exported_column, basestring):
                        exported_column = _unescape(exported_column)
                    row_content.append(exported_column)
                    if (p is not None and
                        (p.bold is not None or p.italic is not None or
                         p.font_name is not None or p.font_family is not None or
                         p.font_size is not None)):
                        pdf_context.add_presentation(p)
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
            if header_row_p and presentation.header_separator_height:
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
                size = old_div(self._unit2points(presentation.separator_margin, style), 2)
            else:
                size = 0
            table_style_data.append(('TOPPADDING', (0, 0), (-1, -1), size,))
            table_style_data.append(('BOTTOMPADDING', (0, 0), (-1, -1), size,))
            if header_row_p and presentation.header_separator_margin is not None:
                size = old_div(self._unit2points(presentation.header_separator_margin, style), 2)
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
                table_style_data.append(('LINEAFTER', (bar - 1, 0), (bar - 1, -1), 1, black,))
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
            for i in range(len(self.column_widths)):
                w = self.column_widths[i]
                if w is None:
                    column_widths.append(None)
                else:
                    w_points = self._unit2points(w, style)
                    column_widths.append(w_points)
                    for row in exported_content:
                        try:
                            cell = row[i]
                        except IndexError:
                            continue
                        if isinstance(cell, basestring):
                            if row is exported_content[0] and header_row_p:
                                s = header_style
                            else:
                                s = style
                            row[i] = RLText(_unescape(row[i]), s, max_width=w_points)
        table_style = reportlab.platypus.TableStyle(table_style_data)
        table = class_(exported_content, colWidths=column_widths, style=table_style,
                       repeatRows=repeat_rows, hAlign=(self.halign or 'CENTER'), vAlign=self.valign)
        if last_element_category == 'paragraph':
            space = make_element(Space, height=UFont(1))
            exported_space = space.export(context)
            table = [exported_space, table, exported_space]
            pdf_context.last_element_category = self._CATEGORY
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
    for k, v in list(kwargs.items()):
        setattr(element, k, v)
    element.init()
    return element


def make_marked_text(text, **kwargs):
    """Returned MarkedText instance containing just 'text'.

    Arguments:

      text -- text content of the MarkedText instance; basestring
      kwargs -- kwargs to pass to MarkedText constructor

    """
    assert isinstance(text, basestring), text
    text_element = make_element(Text, content=text)
    return make_element(MarkedText, content=[text_element], **kwargs)


class PDFExporter(FileExporter, Exporter):

    _OUTPUT_FILE_EXT = 'pdf'

    MATPLOTLIB_RESCALE_FACTOR = 1.5
    """This trick helps to improve matplotlib plots in PDF output.

    Matplotlib automatically determines the level of detail present in the plot
    based on plot dimensions.  While this usually works fine in HTML output,
    the result is not perfect in PDF output.  The printed plots seem to have
    less detail than they deserve for given output size.  The fonts are too
    big, the lines too thick, axes have too few labeled values etc.

    This constant defines the scaling factor which tricks matplotlib to include
    more details.  We enlarge the requested plot size passed to matplotlib by
    given factor, matplotlib creates a plot of bigger dimmensions and then we
    scale down the result by the same factor before embedding it into the final
    PDF.  Thus the final plot size matches the requested size but the plot
    includes more details.  It is a hack but it solves the problem.

    """

    def _uri_section(self, context, section, local=False):
        # Force all section links to be local, since there is just one output document.
        return super(PDFExporter, self)._uri_section(context, section, local=True)

    def _content_export(self, context, element, collapse=True, presentation=None):
        content = element.content()
        if isinstance(content, (tuple, list)):
            exported_content = [c.export(context) for c in content]
        else:
            exported_content = content.export(context)
        if collapse and isinstance(exported_content, (tuple, list)):
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
                            item = make_element(Text, content=item)
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

    def _reformat_text(self, context, text):
        return text

    def _ensure_newlines(self, context, exported, number=1):
        if isinstance(exported, Text):
            exported = make_element(Paragraph, content=[exported])
        return exported

    def text(self, context, text, lang=None, reformat=False):
        assert isinstance(text, basestring), text
        if text:
            # We should get reasonable input from the parsers but this is
            # currently not the case.
            if text[0] == '\n':
                text = ' ' + text[1:]
            if text[-1] == '\n':
                text = text[:-1] + ' '
            result = make_element(Text, content=text)
        else:
            result = make_element(Empty)
        return result

    def escape(self, text):
        return make_element(Text, content=text)

    def _get_resource_path(self, context, resource):
        return None

    # Classic exports

    def export(self, context, old_contexts=None, global_presentation=None, recursive=False):
        Context.reset()
        first_pass = (old_contexts is None)
        if old_contexts is None:
            old_contexts = {}
        old = old_contexts.get(None)
        if old is not None:
            total_pages = old.page
            page_size = old.page_size()
        else:
            total_pages = 0
            page_size = reportlab.lib.pagesizes.A4
        node = context.node()
        lang = context.lang()
        page_header = node.page_header(lang)
        presentation_set = context.presentation()
        if presentation_set is None:
            node_presentation = node.presentation(lang) or lcg.Presentation()
        else:
            presentations = (lcg.Presentation(),
                             presentation_set.presentation(None, lang),
                             node.presentation(lang),)
            node_presentation = presentation_set.merge_presentations(presentations)
        if global_presentation is not None:
            node_presentation = copy.copy(node_presentation)
            for p in ('font_name', 'font_family',):
                setattr(node_presentation, p,
                        (getattr(node_presentation, p) or getattr(global_presentation, p)))
            if global_presentation.landscape:
                page_size = reportlab.lib.pagesizes.landscape(page_size)
            else:
                page_size = reportlab.lib.pagesizes.portrait(page_size)

        def presentation_size(attr, default=(10 * reportlab.lib.units.mm)):
            try:
                size = getattr(global_presentation, attr)
                if isinstance(size, UMm):
                    points = size.size() * reportlab.lib.units.mm
                elif isinstance(size, UPoint):
                    points = size.size()
                else:
                    points = default
            except Exception:
                points = default
            return points
        page_size = (presentation_size('page_width', default=page_size[0]),
                     presentation_size('page_height', default=page_size[1]),)
        left_margin = presentation_size('left_margin')
        right_margin = presentation_size('right_margin')
        top_margin = presentation_size('top_margin')
        bottom_margin = presentation_size('bottom_margin')
        context.pdf_context = old_contexts[None] = pdf_context = \
            Context(total_pages=total_pages,
                    first_page_header=(node.first_page_header(lang) or page_header),
                    page_header=page_header,
                    page_footer=node.page_footer(lang),
                    page_background=node.page_background(lang),
                    page_size=page_size,
                    left_margin=left_margin,
                    right_margin=right_margin,
                    top_margin=top_margin,
                    bottom_margin=bottom_margin,
                    presentation=node_presentation,
                    presentation_set=presentation_set,
                    lang=lang)
        presentation = pdf_context.current_presentation()
        exported_structure = []
        first_subcontext = None
        subnodes = node.linear()
        if len([n for n in subnodes if n.id() != '__dummy']) > 1:
            init_heading_level = 1
            context_heading_level = 2
        else:
            init_heading_level = 0
            context_heading_level = 1
        for n in subnodes:
            node_id = n.id()
            if node_id[:7] == '__dummy':
                continue
            subcontext = self.context(n, lang)
            old = old_contexts.get(node_id)
            total_pages = 0
            if old is not None:
                total_pages = old.page
            page_header = n.page_header(lang)
            subcontext.pdf_context = old_contexts[node_id] = \
                Context(parent_context=pdf_context, total_pages=total_pages,
                        first_page_header=(n.first_page_header(lang) or page_header),
                        page_header=page_header,
                        page_footer=n.page_footer(lang),
                        page_background=n.page_background(lang),
                        presentation=presentation,
                        presentation_set=context.presentation(),
                        page_size=page_size,
                        left_margin=left_margin,
                        right_margin=right_margin,
                        top_margin=top_margin,
                        bottom_margin=bottom_margin,
                        lang=lang)
            subcontext.pdf_context.add_presentation(n.presentation(lang))
            subcontext.pdf_context.heading_level = context_heading_level
            subcontext.pdf_context.anchor_prefix = node_id + '-'
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
            if n.title().strip():
                title = subcontext.exporter().export_element(subcontext, n.heading())
                exported_heading = make_element(Heading, content=[title], level=init_heading_level)
                exported_structure.append(exported_heading)
            exported = n.content(lang).export(subcontext)
            if isinstance(exported, (tuple, list)):
                exported = self.concat(*exported)
            exported_structure.append(exported)
        if not exported_structure:
            return b''
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
            return b''
        output = io.BytesIO()
        doc = DocTemplate(output, pagesize=page_size,
                          leftMargin=left_margin,
                          rightMargin=right_margin,
                          topMargin=top_margin,
                          bottomMargin=bottom_margin)
        while True:
            try:
                doc.multi_build(document, context=first_subcontext)
            except reportlab.platypus.doctemplate.LayoutError as e:
                if unistr(e).find('too large') >= 0:
                    pdf_context.set_relative_font_size(pdf_context.relative_font_size() / 1.2)
                    if pdf_context.relative_font_size() < 0.1:
                        tb = sys.exc_info()[2]
                        frame_locals = inspect.getinnerframes(tb)[-1][0].f_locals
                        for v in ('flowable', 'f',):
                            if v in frame_locals:
                                obj = frame_locals[v]
                                break
                        else:
                            obj = None
                        if obj is not None:
                            e = (e, unistr(obj),)
                        context.log(_("Page content extremely large, giving up"), kind=lcg.ERROR)
                    context.log(_("Page content too large, reducing it by %s",
                                  (pdf_context.relative_font_size())))
                else:
                    raise
            else:
                break
        if first_pass and pdf_context.total_pages_requested():
            return self.export(context, old_contexts=old_contexts)
        return output.getvalue()

    def export_element(self, context, element):
        pdf_context = context.pdf_context
        presentation = pdf_context.set_styled_presentation(element)
        result = super(PDFExporter, self).export_element(context, element)
        assert isinstance(result, Element), ('Invalid export result', element, result,)
        if presentation is not None:
            if result.presentation is not None:
                presentation = lcg.PresentationSet.merge_presentations((result.presentation,
                                                                        presentation,),
                                                                       override=('boxed',))
            result.presentation = presentation
        pdf_context.unset_styled_presentation()
        return result

    def _export_content(self, context, element):
        return make_element(Empty)

    def _export_preformatted_text(self, context, element):
        return make_element(PreformattedText, content=element.text())

    def _export_anchor(self, context, element):
        anchor = element.anchor()
        if anchor:
            anchor = context.pdf_context.anchor_prefix + anchor
        return make_element(LinkTarget, content=element.text(), name=anchor)

    def _export_new_page(self, context, element):
        return make_element(PageBreak)

    def _export_new_line(self, context, element):
        return make_element(SimpleMarkup, content='br')

    def _export_horizontal_separator(self, context, element):
        return make_element(HorizontalRule, thickness=element.thickness(), color=element.color())

    def _export_page_number(self, context, element):
        return make_element(PageNumber, total=element.total(), separator=element.separator())

    def _export_hspace(self, context, element):
        return make_element(Space, width=element.size(context), height=UMm(0))

    def _export_vspace(self, context, element):
        return make_element(Space, height=element.size(context), width=UMm(0))

    # Container elements

    def _export_container(self, context, element):
        exported_content = self._content_export(context, element, collapse=False)
        assert isinstance(exported_content, (list, tuple,)), exported_content
        texts = [isinstance(c, (Text, basestring,)) for c in exported_content]
        # This is going to be a really wild guesswork.  There can be two very
        # distinct kinds of containers: 1. alignment containers; 2. paragraphs
        # (Containers inside Paragraphs).  And of course there are many common
        # (often useless) containers with no special purpose in typical LCG
        # content.
        plain_container = (element.presentation() is None and element.orientation() is None and
                           element.halign() is None and element.valign() is None)
        assert isinstance(exported_content, (list, tuple)), exported_content
        texts = [isinstance(c, (Text, basestring)) for c in exported_content]
        if plain_container:
            # Just a container without any special purpose.  Maybe we can avoid
            # it.
            if all(texts):
                # Nothing but texts, this is good.  We can simply collapse them.
                return self.concat(*exported_content)
            else:
                # There are other elements present, we can't make single
                # Paragraph from this.
                if any(texts):
                    mixed_content = exported_content
                    exported_content = []
                    while mixed_content:
                        text_p = isinstance(mixed_content[0], Text)
                        i = 1
                        while (i < len(mixed_content) and
                               text_p == isinstance(mixed_content[i], Text)):
                            i += 1
                        # TODO: This doesn't check for Paragraphs inside Paragraph
                        exported_content.append(make_element(Paragraph if text_p else Container,
                                                             content=mixed_content[:i]))
                        mixed_content = mixed_content[i:]
        else:
            # We can't make anything else than common Container.  But in some
            # places it isn't expected to contain texts, so we must replace
            # them.
            def wrap(c):
                if isinstance(c, Text) and not isinstance(c, TextContainer):
                    c = make_element(TextContainer, content=[c])
                return c
            exported_content = [wrap(c) for c in exported_content]
        padding = element.padding()
        if padding is not None:
            if not isinstance(padding, (tuple, list)):
                padding = (padding, padding, padding, padding)
            elif len(padding) == 2:
                padding = (padding[0], padding[1], padding[0], padding[1])
        return make_element(Container, content=exported_content,
                            vertical=(element.orientation() != 'HORIZONTAL'),
                            halign=element.halign(), valign=element.valign(),
                            width=element.width(), height=element.height(),
                            padding=padding,
                            presentation=element.presentation())

    def _markup_container(self, context, element, tag, **attributes):
        exported_content = self._content_export(context, element, collapse=False)
        return make_element(MarkedText, content=exported_content, tag=tag, attributes=attributes)

    def _export_emphasized(self, context, element):
        return self._markup_container(context, element, 'i')

    def _export_strong(self, context, element):
        return self._markup_container(context, element, 'strong')

    def _export_code(self, context, element):
        face = context.pdf_context.font(None, FontFamily.FIXED_WIDTH, False, False)
        return self._markup_container(context, element, 'font', face=face)

    def _export_underlined(self, context, element):
        return self._markup_container(context, element, 'u')

    def _export_shifted(self, context, element, font_size, baseline_shift):
        # Work around: Subscript/superscript was originally implemented using
        # _markup_container(), but it uses a 'reportlab.platypus.Paragraph'
        # which spans to the available width.  Thus it produces an unwanted
        # (potentially huge) space between the sub/super script and the
        # adjacent text.  This is unusable so this is why 'baseline_shift' was
        # introduced to help implement subscript and superscript.  If the
        # spacing after 'reportlab.platypus.Paragraph' can be avoided, we can
        # revert back to using _markup_container().  This problem probably also
        # applies to other elements using _markup_container(), but these are
        # not widely used (Containers with custom Presentation are used instead
        # in Pytis print for example).
        presentation = element.presentation() or lcg.Presentation()
        presentation.font_size = font_size
        presentation.baseline_shift = baseline_shift
        exported_content = self._content_export(context, element, collapse=False)
        return make_element(Container, content=exported_content,
                            presentation=presentation)

    def _export_superscript(self, context, element):
        return self._export_shifted(context, element, 0.8, 0.1)

    def _export_subscript(self, context, element):
        return self._export_shifted(context, element, 0.8, -0.5)

    def _export_citation(self, context, element):
        return self._export_emphasized(context, element)

    def _export_quotation(self, context, element):
        exported = self._export_paragraph(context, element)
        source = element.source()
        uri = element.uri()
        if source or uri:
            lang = element.lang()
            extra = [self.text(context, '--', lang=lang)]
            if source:
                extra.append(self.text(context, u' ' + source, lang=lang, reformat=True))
            if uri:
                format_ = u' (%s)' if source else u' %s'
                extra.append(self.text(context, format_ % (uri,), lang=lang, reformat=True))
            text = self.concat(*extra)
            exported = make_element(Paragraph, content=[text], halign=HorizontalAlignment.RIGHT)
        return exported

    def _export_link(self, context, element):
        target = element.target(context)
        node_id = element.node_id()
        if node_id and node_id != context.pdf_context.anchor_prefix:
            return make_element(Empty)
        if element.content():
            content = self._content_export(context, element)
        else:
            if isinstance(target, (lcg.ContentNode, lcg.Section)):
                content = target.heading().export(context)
            elif isinstance(target, lcg.Resource):
                content = make_element(Text, content=(target.title() or target.filename()))
            elif isinstance(target, element.ExternalTarget):
                content = make_element(Text, content=target.title() or target.uri())
        # TODO: Show link (or target) 'descr()' as a tooltip or something similar (see html export).
        uri = context.uri(target)
        if uri and uri[0] == '#':
            uri = '#' + context.pdf_context.anchor_prefix + uri[1:]
        if isinstance(content, Container):
            def filter_(c):
                if isinstance(c, Text):
                    result = [c]
                elif isinstance(c, basestring):
                    result = [make_element(Text, content=c)]
                elif isinstance(c, Image):
                    link_content = make_element(Text, content=(c.text or c.content or 'image'))
                    if c.image.src_file() is None:
                        result = [make_element(Link, content=link_content, uri=uri)]
                    else:
                        result = [make_element(Link, content=link_content, uri=uri)]
                else:
                    result = []
                return result
            container_content = content.content
            if len(container_content) == 1 and isinstance(container_content[0], Image):
                image = container_content[0]
                image.uri = uri
                return image
            filtered_content = content.expand(filter_)
            content = make_element(TextContainer, content=filtered_content)
        return make_element(Link, content=content, uri=uri)

    def _export_section(self, context, element):
        pdf_context = context.pdf_context
        content = context.exporter().export_element(context, element.heading())

        def update_text(content, function):
            if isinstance(content, TextContainer):
                c = content.content
                for i in range(len(c)):
                    if isinstance(c[i], TextContainer):
                        if update_text(c[i], function):
                            return True
                    elif isinstance(c[i], Text) and c[i].content.strip():
                        c[i] = function(c[i])
                        return True
            elif isinstance(content, Container):
                for c in content.content:
                    if update_text(c, function):
                        return True
            return False
        anchor = element.id()
        if anchor:
            anchor = context.pdf_context.anchor_prefix + anchor

            def make_link_target(content):
                return make_element(LinkTarget, name=anchor, content=content.content,
                                    style=content.style, halign=content.halign)
            update_text(content, make_link_target)
        level = pdf_context.heading_level
        heading = make_element(Heading, content=content.content, level=level)
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
            while isinstance(title, Container) and len(title.content) == 1:
                title = title.content[0]
            if isinstance(title, Text):
                title = make_element(Label, content=[title])
            presentation = lcg.Presentation()
            presentation.left_indent = UFont(2 * 1.2)
            if isinstance(description, Text):
                description = make_element(Paragraph, content=[description],
                                           presentation=presentation, noindent=True)
            else:
                description = make_element(Container, content=[description],
                                           presentation=presentation)
            return make_element(Container, content=[title, description])
        result_items = [make_item(dt.export(context), dd.export(context))
                        for dt, dd in element.content()]
        return make_element(Container, content=result_items)

    def _export_field_set(self, context, element):
        def has_markup(element):
            if isinstance(element, (MarkedText, Link)):
                return True
            if not isinstance(element, Element):
                return False
            content = element.content
            if not isinstance(content, (list, tuple)):
                content = (content,)
            for c in content:
                if has_markup(c):
                    return True
            return False

        def make_cell(element):
            exported = element.export(context)
            if has_markup(exported):
                exported = make_element(Paragraph, content=[exported])
            return make_element(TableCell, content=[exported])

        def make_item(label, value):
            content = [make_cell(label), make_cell(value)]
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
                                     halign=halign, noindent=element.noindent())
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
                heading = make_element(Paragraph,
                                       content=[make_marked_text(title, tag='strong')],
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
                            long=element.long(), compact=element.compact(),
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
            except lcg.SubstitutionIterator.NotStartedError as e:
                iterator = e.iterator()
            if iterator is None:
                raise lcg.SubstitutionIterator.IteratorError("No table row iterator found")
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
        image = element.image(context)
        filename = self._get_resource_path(context, image)
        if element.standalone() or context.pdf_context.in_figure:
            class_ = Image
            kwargs = {}
        else:
            class_ = InlineImage
            kwargs = dict(text=element.title())
        return make_element(class_, image=image, filename=filename,
                            width=element.width(), height=element.height(),
                            align=element.align(), **kwargs)

    def _export_figure(self, context, element):
        pdf_context = context.pdf_context
        in_figure = pdf_context.in_figure
        pdf_context.in_figure = True
        result = super(PDFExporter, self)._export_figure(context, element)
        pdf_context.in_figure = in_figure
        return result

    # Special constructs

    _simple_annotation_regexp = re.compile('^[- 0-9.,a-zA-Z+=()]+$')

    def _export_mathml(self, context, element):
        # For simple cases, use just annotation (it's faster and may look better)
        xml_tree = element.tree_content()
        annotation = xml_tree.findtext('*/annotation')
        if annotation is not None:
            annotation = annotation.strip()
            if self._simple_annotation_regexp.match(annotation):
                i = 0
                length = len(annotation)
                content = []
                while i < length:
                    j = i
                    while j < length and annotation[j] in string.ascii_letters:
                        j += 1
                    if j > i:
                        content.append(make_marked_text(annotation[i:j], tag='i'))
                        i = j
                    while j < length and annotation[j] not in string.ascii_letters:
                        j += 1
                    if j > i:
                        content.append(make_element(Text, content=annotation[i:j]))
                        i = j
                return make_element(TextContainer, content=content)
        # We have to fix mstyle attribute problem of the CMS editor first,
        # otherwise some parts or the whole element may not be rendered.
        root = element.tree_content()
        for node in root.iter('mstyle'):
            for n, v in list(node.items()):
                if v == '':
                    del node.attrib[n]
        tree = xml.etree.ElementTree.ElementTree(root)
        # Let's try MathML rendering
        tempdir = tempfile.mkdtemp(dir=context.pdf_context.tempdir())
        tempfile_mml = os.path.join(tempdir, 'math.mml')
        tempfile_png = os.path.join(tempdir, 'math.png')
        tree.write(tempfile_mml, encoding='utf-8')
        style = context.pdf_context.normal_style()
        font_size = style.fontSize
        scale = 2.0
        args = [tempfile_mml, tempfile_png, '-fontSize', unistr(font_size * scale)]
        font_name = style.fontName
        if font_name is not None and font_name.startswith('DejaVu'):
            args.extend(['-fontsMonospaced', 'DejaVuSansMono',
                         '-fontsSansSerif', 'DejaVuSans',
                         '-fontsSerif', 'DejaVuSerif'])
        else:
            args.extend(['-fontsMonospaced', 'FreeMono',
                         '-fontsSansSerif', 'FreeSans',
                         '-fontsSerif', 'FreeSerif'])
        result = subprocess.call([MATHML_FORMATTER] + args)
        if result == 0:
            image = lcg.Image(tempfile_png, src_file=tempfile_png)
            import PIL.Image
            pil_image = PIL.Image.open(tempfile_png)
            height = old_div(pil_image.size[1], scale)
            # There is some magic in the vertical positioning, we try some wild guess here
            shift = min(0, font_size - height - 2.5)
            result = make_element(InlineImage, image=image, resize=(1.0 / scale), align=shift)
        else:
            # If rendering doesn't work then use the fallback mechanism
            text = annotation or element.content()
            result = make_element(TextContainer, content=[make_element(Text, content=text)])
        return result

    def _export_inline_svg(self, context, element):
        return make_element(SVGDrawing, svg=element.svg(context))
