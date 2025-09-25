# -*- coding: utf-8 -*-

# Copyright (C) 2011-2016 OUI Technology Ltd.
# Copyright (C) 2019-2024 Tomáš Cerha <t.cerha@gmail.com>
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

from __future__ import unicode_literals

import sys
import copy
import lcg
import re
import string

unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


class Presentation(object):
    """Set of presentation properties.

    Using instance of this class, you can provide explicit presentation
    information to some LCG content elements.  Note that it is often not
    desirable to define presentation explicitly.  You need to define
    presentation this way when you prepare a printed document with fixed
    structure, on the other hand when preparing a general HTML page you should
    use variable external stylesheets instead.  That's why most properties are
    ignored by the HTML export backend.

    This class serves just as a storage of presentation properties, it does not
    provide any special methods.  All of the attribute values can be set to
    'None' meaning there is no presentation requirement for that attribute and
    it can be taken from another active presentation.

    Presentation properties may be passed to Presentation constructor as
    keyword arguments or manipulated on an existing instance by setting the
    relevant attributes.

    """
    font_size = None
    """Font size relative to the current font size (1.0 is the same size), float."""

    font_name = None
    """Name of the font to use, e.g. 'Free' or 'DejaVu', string."""

    font_family = None
    """Font family to be used for typesetting text, one of 'FontFamily' constants."""

    font_color = None
    """Font color, 'Color'."""

    background_color = None
    """Background color, 'Color'."""

    heading_font_family = None
    """Font family to be used for typesetting headings, one of 'FontFamily' constants."""

    noindent = None
    """If true, don't indent first lines of paragraphs."""

    bold = None
    """True when bold font face should be used, False otherwise."""

    italic = None
    """True when italic font face should be used, False otherwise."""

    baseline_shift = None
    """Shift the text baseline up/down relatively to font size, float.
    Positive number shifts the text up, negative down from the current baseline level.
    """

    boxed = None
    """'True' when the content should be surrounded by a box."""

    box_margin = None
    """Space between the box and the content, 'Unit'.
    It may be ignored in some boxed elements.
    """

    box_width = None
    """Box line width, 'Unit'."""

    box_color = None
    """Box line color, 'Color'."""

    box_radius = None
    """Radius of box corners, if the corners should be rounded, 'Unit'."""

    box_mask = None
    """Mask of visible box sides as a sequence of 4 bools (top, right, bottom, left)."""

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
    It currently works only for PDF pages and Braille if set for the top level node.
    """

    bottom_margin = None
    """Amount of space on the bottom of the object, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for PDF pages and Braille if set for the top level node.
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

    inner_margin = None
    """Amount of space on the inner side of the object, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for Braille if set for the top level node.
    """

    outer_margin = None
    """Amount of space on the outer side of the object, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for Braille if set for the top level node.
    """

    page_width = None
    """Page width, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for PDF pages or Braille output (restricted to
    UFont and USpace instances) if set for the top level node.
    """

    page_height = None
    """Page height, non-relative 'Unit'.
    If 'None', use the default value.
    It currently works only for PDF pages or Braille output (restricted to
    UFont and USpace instances) if set for the top level node.
    """

    landscape = None
    """Page orientation.
    If False then use portrait orientation, if True then use landscape orientation.
    If 'None', use the default value.
    It currently works only for PDF pages if set for the top level node.
    """

    device_output = None
    """Device output specification.
    It is currently used only for Braille output where it is a dictionary
    mapping Unicode Braille and whitespace characters to output device
    characters.
    """

    device_init = None
    """Function returning initial string to send to the Braille printer.
    The function takes two integer arguments: page width (number of characters)
    and page height (number of lines).
    """

    device_finish = None
    """Final string to send to the Braille printer."""

    braille_tables = None
    """Dictionary of Braille tables to use.
    Keys are language codes (strings), values are lists of Braille table names
    (strings) for liblouis.
    Useful only for Braille output.
    """

    braille_hyphenation_tables = None
    """Dictionary of Braille hyphenation tables to use.
    Keys are language codes (strings), values are Braille hyphenation table
    names (strings) for liblouis.
    Useful only for Braille output.
    """

    braille_math_rules = 'nemeth'
    """System to use for typesetting mathematics in Braille.
    Currently supported values are 'nemeth' and 'czech'.
    Useful only for Braille output.
    """

    printers = None
    """Dictionary of printer names (keys) and their properties (values).
    Printer properties are represented by a dictionary with property names as
    keys and their corresponding values as values.
    Only 'device_init' and 'device_finish' properties are currently
    recognized.
    Useful only for Braille output.
    """

    default_printer = None
    """Default printer, one of the 'printers' keys or 'None'.
    Useful only for Braille output.
    """

    left_page_footer = None
    """Custom left page footer, 'lcg.Content' instance or 'None'."""

    right_page_footer = None
    """Custom right page footer, 'lcg.Content' instance or 'None'."""

    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)


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


class TopLevelMatcher(ContentMatcher):
    """General matcher of the whole content.

    As a convention the matcher returns true on null content.

    """

    def matches(self, content, lang):
        """Return true iff 'content' is 'None'."""
        return content is None


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


class LCGClassMatcher(ContentMatcher):
    """Content class matching."""

    def __init__(self, content_class):
        """
        Arguments:

          content_class -- content class to match, 'lcg.Content' subclass

        """
        assert issubclass(content_class, lcg.Content), content_class
        self._content_class = content_class

    def matches(self, content, lang):
        return isinstance(content, self._content_class)


class LCGHeadingMatcher(LCGClassMatcher):
    """'lcg.Heading' matching, based on the heading level."""

    def __init__(self, level):
        """
        Arguments:

          level -- heading level to match, positive integer

        """
        assert isinstance(level, int) and level > 0, level
        super(LCGHeadingMatcher, self).__init__(lcg.Heading)
        self._level = level

    def matches(self, content, lang):
        return (super(LCGHeadingMatcher, self).matches(content, lang) and
                content.level() == self._level)


class LCGContainerMatcher(LCGClassMatcher):
    """'lcg.Container' matching, based on the container names."""

    def __init__(self, name):
        """
        Arguments:

          name -- container name to match, string

        """
        assert isinstance(name, basestring), name
        super(LCGContainerMatcher, self).__init__(lcg.Container)
        self._name = name

    def matches(self, content, lang):
        return (super(LCGContainerMatcher, self).matches(content, lang) and
                self._name in content.names())


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
        assert isinstance(presentations, (list, tuple)), presentations
        if __debug__:
            for p, m in presentations:
                assert isinstance(p, Presentation), (p, presentations,)
                assert isinstance(m, ContentMatcher), (m, presentations,)
        self._presentations = presentations
        self._merge_cache = {}

    def _matching_presentations(self, content, lang):
        return [p for p, m in self._presentations if m.matches(content, lang)]

    @classmethod
    def merge_presentations(cls, presentations, override=()):
        """Return a common presentation created from 'presentations'.

        The presentations are merged in their order; non-default parameters of
        latter presentations override parameters of former presentations.

        Arguments:

          presentation -- sequence of 'Presentation' instances
          override -- sequence of parameter names (strings); default parameters
            present here override parameters of former presentations

        """
        assert isinstance(presentations, (list, tuple)), presentations
        presentations = [p for p in presentations if p is not None]
        if __debug__:
            assert all([isinstance(p, Presentation) for p in presentations]), presentations
        if presentations:
            new_presentation = copy.copy(presentations[0])
            for p in presentations[1:]:
                for attr in dir(p):
                    if attr[0] in string.ascii_lowercase:
                        value = getattr(p, attr)
                        if value is None and attr not in override:
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
        assert isinstance(content, lcg.Content) or content is None, content
        assert lang is None or isinstance(lang, basestring), lang
        applicable_presentations = self._matching_presentations(content, lang)
        key = tuple([id(p) for p in applicable_presentations])
        presentation = self._merge_cache.get(key)
        if presentation is None:
            presentation = self._merge_cache[key] = \
                self.merge_presentations(applicable_presentations)
        return presentation


def _parse_ufont(s):
    return float(s)


def _parse_string(s):
    return s


def _parse_boolean(s):
    s = s.lower()
    if s == 'yes':
        return True
    elif s == 'no':
        return False
    else:
        raise Exception("Invalid boolean value")


def _parse_font_family(s):
    if s == 'SERIF':
        result = lcg.FontFamily.SERIF
    elif s == 'SANS_SERIF':
        result = lcg.FontFamily.SANS_SERIF
    elif s == 'FIXED_WIDTH':
        result = lcg.FontFamily.FIXED_WIDTH
    else:
        raise Exception("Invalid font family")
    return result


class StyleFile(object):
    """Style file support.

    External style file can be used to define output style properties.  Its
    syntax is, not very formally, as follows:

      STYLES := STYLE STYLES | $
      STYLE := identifier '(' INHERITS ')' ':' newline PROPERTIES
      INHERITS := identifier ',' INHERITS | $
      PROPERTIES := PROPERTY newline PROPERTIES | $
      PROPERTY := identifier = VALUE newline
      VALUE := 'yes' | 'no' | number | text

    Supported style identifiers are defined in '_MATCHERS' attribute, supported
    property identifiers in '_PROPERTY_MAPPING' attribute.  The user can define
    his own styles with his own names (all lower case identifiers are
    recommended) and inherit them in the supported styles or his other styles.

    """
    _MATCHERS = (
        ('Common', TopLevelMatcher(),),
        ('Heading_1', LCGHeadingMatcher(1),),
        ('Heading_2', LCGHeadingMatcher(2),),
        ('Heading_3', LCGHeadingMatcher(3),),
        ('Table_Of_Contents', LCGClassMatcher(lcg.TableOfContents),),
        ('Preformatted_Text', LCGClassMatcher(lcg.PreformattedText),),
    )

    _PROPERTY_MAPPING = (
        ('font_size', 'font_size', _parse_ufont,),
        ('font_name', 'font_name', _parse_string,),
        ('font_family', 'font_family', _parse_font_family,),
        ('bold', 'bold', _parse_boolean,),
        ('italic', 'italic', _parse_boolean,),
    )

    class _Style(object):
        name = None
        inherits = ()
        presentation = Presentation()

    class ParseError(Exception):
        pass

    def __init__(self):
        self._styles = []
        self._names_styles = {}

    def read(self, file):
        """Read styles from file.

        Arguments:

          file -- file object open for reading

        """
        def syntax_error(number, line):
            raise self.ParseError("Syntax error in style file on line %s: %s" % (number, line,))
        styles = []
        names_styles = {}
        style_line_matcher = re.compile('(.*)[(](.*)[)]')
        property_line_matcher = re.compile('(.*)=(.*)')
        current_presentation = None
        line_number = 0
        while True:
            raw_line = file.readline()
            if not raw_line:
                break
            line_number += 1
            line = raw_line.strip()
            if not line or line[0] == '#':
                continue
            if line[-1] == ':':
                # Style declaration
                line = line[:-1].strip()
                match = style_line_matcher.match(line)
                if not match:
                    syntax_error(line_number, raw_line)
                name = match.group(1).strip()
                inherits = [s.strip() for s in match.group(2).split(',')]
                if inherits == ['']:
                    inherits = []
                for s in inherits:
                    if s not in names_styles:
                        raise self.ParseError("Unknown style `%s' in style file on line %s" %
                                              (s, line_number,))
                style = names_styles[name] = self._Style()
                styles.append(style)
                style.name = name
                style.inherits = inherits
                style.presentation = current_presentation = Presentation()
            else:
                # Style property
                if current_presentation is None:
                    syntax_error(line_number, raw_line)
                match = property_line_matcher.match(line)
                if not match:
                    syntax_error(line_number, raw_line)
                name = match.group(1).strip()
                text_value = match.group(2).strip()
                for identifier, property, parser in self._PROPERTY_MAPPING:
                    if name == identifier:
                        try:
                            value = parser(text_value)
                        except Exception:
                            raise self.ParseError("Invalid property value on line %s: %s" %
                                                  (line_number, raw_line,))
                        break
                else:
                    raise self.ParseError("Unknown property name `%s' in style file on line %s" %
                                          (name, line_number,))
                setattr(current_presentation, property, value)
        self._styles = styles
        self._names_styles = names_styles

    def write(self, file):
        """Write styles to file.

        Arguments:

          file -- file object open for writing

        """
        for style in self._styles:
            file.write(style.name)
            file.write(' (%s) :\n' % (', '.join(style.inherits),))
            presentation = style.presentation
            for identifier, property, parser in self._PROPERTY_MAPPING:
                value = getattr(presentation, property)
                if value is None:
                    continue
                if isinstance(value, bool):
                    if value:
                        str_value = 'yes'
                    else:
                        str_value = 'no'
                elif isinstance(value, basestring):
                    str_value = value
                elif isinstance(value, float):
                    str_value = str(value)
                elif isinstance(value, bytes):
                    str_value = value.decode()
                else:
                    raise Exception("Unsupported value type", value)
                file.write('%s = %s\n' % (identifier, str_value,))

    def presentations(self):
        """Return presentations corresponding to the style.

        The return value is in the form of 'presentation' argument of
        'PresentationSet' constructor.

        """
        presentations = []
        for s in self._styles:
            for name, matcher in self._MATCHERS:
                if name == s.name:
                    break
            else:
                matcher = LCGContainerMatcher(name=s.name)
            presentation_list = [self._names_styles[name].presentation for name in s.inherits]
            presentation_list.reverse()
            presentation_list.append(s.presentation)
            merged = PresentationSet.merge_presentations(presentation_list)
            presentations.append((merged, matcher,))
        return presentations
