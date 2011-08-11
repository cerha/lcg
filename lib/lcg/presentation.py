# -*- coding: utf-8 -*-

# Copyright (C) 2011 Brailcom, o.p.s.
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
    box_margin = None
    """Space between the box and the content, 'Unit'.
    It may be ignored in some boxed elements.
    """
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
    top_margin = None
    """Amount of space on the top of the object, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for PDF pages if set for the top level node.
    """
    bottom_margin = None
    """Amount of space on the bottom of the object, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for PDF pages if set for the top level node.
    """
    left_margin = None
    """Amount of space on the left of the object, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for PDF pages if set for the top level node.
    """
    right_margin = None
    """Amount of space on the right of the object, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for PDF pages if set for the top level node.
    """
    page_width = None
    """Page width, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for PDF pages if set for the top level node.
    """
    page_height = None
    """Page height, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for PDF pages if set for the top level node.
    """
    landscape = None
    """Page orientation.
    If False then use portrait orientation, if True then use landscape orientation.
    If 'None', use the default value.
    It currently works only for PDF pages if set for the top level node.
    """
    

