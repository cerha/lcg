# -*- coding: utf-8 -*-

# Copyright (C) 2010 Brailcom, o.p.s.
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
Dimensions, their units and miscellaneous enumeration constants for content.

Each dimension is defined by a particular class representing a dimension unit
and its value.  Dimension objects are typically used in space content.

There is a base class L{Unit} representing an abstract general dimension unit.
Particular dimension units are defined as L{Unit} subclasses.  Their instances
represent dimensions.

Additionally various enumerations are defined here, for instance:
@L{HorizontalAlignment}, L{VerticalAlignment}, L{Orientation}, L{FontFamily}.

"""

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
        @type size: float or integer
        @param size: Dimension value.
        """
        assert isinstance(size, (float, int, long,)), size
        self._size = size

    def __nonzero__(self):
        """
        @return: True iff the size is non-zero.
        """
        return self._size != 0
    
    def __add__(self, size):
        """
        @type size: float or integer
        @param size: Value to increase the instance size by.
        @return: New instance of the same class, with size increased by C{size}.
        """
        assert isinstance(size, (float, int, long,)), size
        return self.__class__(self._size + size)

    def __mul__(self, size):
        """
        @type size: float or integer
        @param size: Value to multiple the instance size by.
        @return: New instance of the same class, with size multiplied by C{size}.
        """
        assert isinstance(size, (float, int, long,)), size
        return self.__class__(self._size * size)        

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

class UAny(Unit):
    """Special unit representing a flexible space.
    The value is currently ignored.
    """


class HorizontalAlignment(object):
    """Enumeration of horizontal alignment kinds."""
    CENTER = 'CENTER'
    LEFT = 'LEFT'
    RIGHT = 'RIGHT'

class VerticalAlignment(object):
    """Enumeration of vertical alignment kinds."""
    CENTER = 'CENTER'

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
