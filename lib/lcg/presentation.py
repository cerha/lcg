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

"""
This file defines presentation infrastructure, so called \"PDF stylesheets\"
(but not necessarily limited to the PDF backend).  The primary motivation is to
allow PDF output customization, somewhat similar to CSS for HTML.

Presentation properties are stored in 'Presentation' instance.  'Presentation'
instances are grouped into 'PresentationSet' instances that can be passed to
document formatting.  Every 'Presentation' inside 'PresentationSet' is
accompanied by 'ContentMatcher' instance that determines whether the
presentation is applicable at the given place in the document, based on
currently processed 'Content' instance and current language.

"""

import copy
import lcg
import string

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


class ContentMatcher(object):
    """Matcher for presentations.

    This is a base class to be subclassed by classes implementing different
    matching algorithms.  Matching is performed using 'matches()' method.  

    """
    def matches(self, content, lang):
        """Return true iff the matcher matches the given content and language.

        In this class the method always returns true.

        Arguments:

          content -- 'Content' instance
          lang -- lowercase ISO 639-1 Alpha-2 language code; string
        
        """
        return True


class LanguageMatcher(ContentMatcher):
    """Langugage based matching, ignoring content.

    The matcher takes a language specifications and matches it with equal or
    unspecified languages.
    
    """
    def __init__(self, lang):
        """
        Arguments:

          lang -- lowercase ISO 639-1 Alpha-2 language code; string or 'None'
          
        """
        super(LanguageMatcher, self).__init__()
        assert lang is None or isinstance(lang, basestring), lang
        self._lang = None
        
    def matches(self, content, lang):
        """Return true iff 'lang' matches the matcher's language.

        If any of the languages is 'None', return true.

        'content' is ignored.
        
        """
        assert lang is None or isinstance(lang, basestring), lang
        return self._lang is None or lang is None or lang == self._lang

    
class PresentationSet(object):
    """Group of 'Presentation' objects, together with their matchers.

    The class can create a common 'Presentation' object from filtered
    presentations, see 'presentation()' method.
    
    """
    def __init__(self, presentations):
        """
        Arguments:

          presentations -- sequence of pairs (PRESENTATION, MATCHER) where
           PRESENTATION is 'Presentation' instance and MATCHER is
           'ContentMatcher' instance determining applicability of the
           presentation.

        """
        assert isinstance(presentations, (list, tuple,)), presentations
        if __debug__:
            for p, m in presentations:
                assert isinstance(p, Presentation), (p, presentations,)
                assert isinstance(m, ContentMatcher), (m, presentations,)
        self._presentations = presentations
        self._merge_cache = {}

    def _matching_presentations(self, content, lang):
        return [p for p, m in self._presentations if m.matches(content, lang)]

    @classmethod
    def merge_presentations(class_, presentations):
        """Return a common presentation created from 'presentations'.

        The presentations are merged in their order; non-default parameters of
        latter presentations override parameters of former presentations.

        Arguments:

          presentation -- sequence of 'Presentation' instances          

        """
        assert isinstance(presentations, (list, tuple,)), presentations
        if __debug__:
            assert all([isinstance(p, Presentation) for p in presentations]), presentations
        if presentations:
            new_presentation = copy.copy(presentations[0])
            for p in presentations[1:]:
                for attr in dir(p):
                    if attr[0] in string.ascii_lowercase:
                        value = getattr(p, attr)
                        if value is None:
                            value = getattr(new_presentation, attr)
                        elif attr == 'font_size':
                            last_value = getattr(new_presentation, attr)
                            if last_value is None:
                                last_value = 1
                            value = value * last_value
                        setattr(new_presentation, attr, value)
        else:
            new_presentation = Presentation()
        return new_presentation

    def presentation(self, content, lang):
        """Return a merged 'Presentation' instance.

        The resulting presentation is created by merging all applicable
        presentations of the set.  Applicable instance are those with matchers
        returning true for the given method arguments.  The applicable
        presentations are processed in their order given in the constructor;
        non-default parameters of latter presentations override parameters of
        former presentations.

        Arguments:

          content -- 'Content' instance
          lang -- lowercase ISO 639-1 Alpha-2 language code; string or 'None'

        """
        assert isinstance(content, lcg.Content), content
        assert lang is None or isinstance(lang, basestring), lang
        applicable_presentations = self._matching_presentations(content, lang)
        key = tuple([id(p) for p in applicable_presentations])
        presentation = self._merge_cache.get(key)
        if presentation is None:
            presentation = self._merge_cache[key] = \
                           self.merge_presentations(applicable_presentations)
        return presentation
