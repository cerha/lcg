# -*- coding: utf-8 -*-

# Copyright (C) 2010-2016 OUI Technology Ltd.
# Copyright (C) 2019-2021 Tomáš Cerha <t.cerha@gmail.com>
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
Dimensions, their units and miscellaneous enumeration constants for content.

Each dimension is defined by a particular class representing a dimension unit
and its value.  Dimension objects are typically used in space content.

There is a base class L{Unit} representing an abstract general dimension unit.
Particular dimension units are defined as L{Unit} subclasses.  Their instances
represent dimensions.

Additionally various enumerations are defined here, for instance:
@L{HorizontalAlignment}, L{VerticalAlignment}, L{Orientation}, L{FontFamily}.

"""
from __future__ import unicode_literals
from past.builtins import cmp

import sys
import decimal

if sys.version_info[0] > 2:
    basestring = str

class Unit(object):
    """Dimension unit representation.

    Instances of subclasses of this class can be used in places where an
    explicit dimension value is required (typically in explicitly defined
    spaces).

    This is a base class representing an abstract general unit, not to be used
    directly.  Use one of its subclasses instead.

    """

    def __init__(self, size):
        """
        @type size: integer, float or decimal.Decimal
        @param size: Dimension value.
        """
        assert isinstance(size, (float, int, decimal.Decimal)), size
        self._size = size

    def __bool__(self):
        """
        @return: True iff the size is non-zero.
        """
        return self._size != 0

    # Just for Python 2 compatibility.
    __nonzero__ = __bool__

    def __add__(self, size):
        """
        @type size: integer, float or decimal.Decimal
        @param size: Value to increase the instance size by.
        @return: New instance of the same class, with size increased by C{size}.
        """
        assert isinstance(size, (float, int, decimal.Decimal)), size
        return self.__class__(self._size + size)

    def __mul__(self, size):
        """
        @type size: integer, float or decimal.Decimal
        @param size: Value to multiple the instance size by.
        @return: New instance of the same class, with size multiplied by C{size}.
        """
        assert isinstance(size, (float, int, decimal.Decimal)), size
        return self.__class__(self._size * size)

    def __cmp__(self, other):
        if self.__class__ == other.__class__:
            result = cmp(self.__class__, other.__class__)
        else:
            result = cmp(self.size(), other.size())
        return result

    def size(self):
        """
        @return: The size given in the constructor.
        """
        return self._size


class UMm(Unit):
    """Millimeter units."""


class UPoint(Unit):
    """Point (1/72 in) units."""


class UFont(Unit):
    """Units corresponding to a current font size."""


class USpace(Unit):
    """Units corresponding to a current preferred gap between two words."""

class UPercent(Unit):
    """Units representing percentage of available space."""

class UAny(Unit):
    """Special unit representing a flexible space.
    The value is currently ignored.
    """


class UPx(Unit):
    """Pixel units (only supported by HTML output)."""


class HorizontalAlignment(object):
    """Enumeration of horizontal alignment kinds."""
    CENTER = 'CENTER'
    LEFT = 'LEFT'
    RIGHT = 'RIGHT'
    JUSTIFY = 'JUSTIFY'


class VerticalAlignment(object):
    """Enumeration of vertical alignment kinds."""
    CENTER = 'CENTER'
    TOP = 'TOP'
    BOTTOM = 'BOTTOM'


class Orientation(object):
    """Enumeration of container orientations."""
    HORIZONTAL = 'HORIZONTAL'
    VERTICAL = 'VERTICAL'


class FontFamily(object):
    PROPORTIONAL = 'SERIF'
    """Standard proportional font, alias for 'SERIF'."""
    SERIF = 'SERIF'
    """Standard proportional font with serifs (e.g. Times)."""
    SANS_SERIF = 'SANS_SERIF'
    """Standard sans serif proportional font(e.g. Helvetica)."""
    FIXED_WIDTH = 'FIXED_WIDTH'
    """Standard nonproportional font (e.g. Courier)."""


class Color(object):
    """RGB color specification.

    The constructor accepts differnt color specification options:
      - Color(255, 128 0) -- three ints specify decimal RGB values in 0-255 range
      - Color(1.0, 0.5, 0) -- three floats specify RGB values in 0.0-1.0 range
      - Color('#ff8000') -- string in HTML hex notation
      - Color('#f80') -- string in short HTML hex notation

    """
    # TODO: Add support for transparency (RGBA)

    def __init__(self, *args):
        n = len(args)
        arg = args and args[0]
        if n == 3 and all(isinstance(a, int) and a >= 0 and a <= 255 for a in args):
            rgb = args
        elif n == 3 and all(isinstance(a, (int, float)) and a >= 0 and a <= 1 for a in args):
            rgb = [int(a * 255) for a in args]
        elif n == 1 and isinstance(arg, basestring) and arg.startswith('#') and len(arg) == 7:
            rgb = [int(x, 16) for x in (arg[1:3], arg[3:5], arg[5:7])]
        elif n == 1 and isinstance(arg, basestring) and arg.startswith('#') and len(arg) == 4:
            rgb = [int(x + x, 16) for x in arg[1:]]
        else:
            raise ValueError("Invalid color specification: %r" % (args,))
        self._rgb = tuple(rgb)

    def rgb(self):
        """Return RGB color as a tuple of three integers in range 0-255."""
        return self._rgb
