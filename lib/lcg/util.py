# -*- coding: iso8859-2 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006 Brailcom, o.p.s.
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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Various utilities"""

import glob
import os
import string
import operator
import types
import re
import sys

class SplittableText:
    """A piece of text which can be split keeping track of line numbers.

    The 'text()' method can be used to retrieve the actual text as a string.
    
    The 'split()' method allows you to split the text into pieces (each
    represented by a new SplittableText instance) using any regex splitter.
    These new pieces keep track of the original input_file (if any) and line
    numbers relative to the original piece of text.

    The 'firstline()' method reports the line number of the first line of given
    piece within the original text.

    This class should work well with UNICODE, as-well as with ordinary strings.

    """
    
    def __init__(self, text, input_file=None, firstline=1):
        """Initialize the instance.

        Arguments:

          text -- the actual text which is subject to split as a String or
            Unicode string.
          input_file -- name of the input file as a string.  This argument can
            be optionally used when the text was read from a file.  This is
            mainly useful when you want to report an error in the input file
            found within the text of this instance.  You set the filename when
            creating the instance and it is passed to the pieces automatically
            when splitting the text and passing it elsewhere in the program.
          firstline -- Line number of the first line.  Normally you should not
            care about this argument.  

        """
        assert isinstance(text, types.StringTypes)
        assert isinstance(firstline, types.IntType)
        self._text = text
        self._firstline = firstline
        self._input_file = input_file

    def text(self):
        """Return the actual text as a string or unicode."""
        return self._text

    def firstline(self):
        """Return the number of the first line of this text on input."""
        return self._firstline

    def input_file(self):
        """Return the name of the input file (if specified in constructor)."""
        return self._input_file

    def piece(self, start, end):
        """Create a 'SplittableText' instance as a substring."""
        n = len(self._text[:start].splitlines()) + self._firstline
        text = self._text[start:end].rstrip()
        return SplittableText(text, input_file=self._input_file, firstline=n)
    
    def split(self, matcher, maxsplit=None):
        """Return parts of the text as a tuple of SplittableText instances.

        The 'matcher' argument is an instance of compiled regular expression.
        This regex should match the splitter used to divide the pieces of the
        input text into subsequent parts.

        If 'maxsplit; is given, at most 'maxsplit' splits are done. (thus, the
        list will have at most `maxsplit+1' elements).  If MAXSPLIT is not
        specified or is zero, then there is no limit on the number of splits
        (all possible splits are made).
        
        All beginning and trailing whitespace characters are stripped from
        the pieces of text.

        """
        pieces = []
        lastposition = len(self._text) - len(self._text.lstrip())
        for i, match in enumerate(matcher.finditer(self._text)):
            if i == maxsplit:
                break
            pieces.append(self.piece(lastposition, match.start()))
            if match.groups():
                pieces.append(match.groups())
            lastposition = match.end()
        pieces.append(self.piece(lastposition, None))
        return pieces


class Counter(object):
    """Incrementing counter."""
    def __init__(self, initial_value=0):
        self._value = initial_value
        
    def next(self):
        value = self._value
        self._value = self._value + 1
        return value
                
    
def is_sequence_of(seq, cls):
    """Return true if 'seq' is a sequence of instances of 'cls'."""
    if not operator.isSequenceType(seq):
        return False
    for item in seq:
        if not isinstance(item, cls):
            return False
    return True


_CAMEL_CASE_WORD = re.compile(r'[A-Z][a-z\d]+')
        
def camel_case_to_lower(string, separator='-'):
    """Return a lowercase string using 'separator' to concatenate words."""
    words = _CAMEL_CASE_WORD.findall(string)
    return separator.join([w.lower() for w in words])


def positive_id(obj):
    """Return id(obj) as a non-negative integer."""
    result = id(obj)
    if result < 0:
        # This is a puzzle:  there's no way to know the natural width of
        # addresses on this box (in particular, there's no necessary
        # relation to sys.maxint).  Try 32 bits first (and on a 32-bit
        # box, adding 2**32 gives a positive number with the same hex
        # representation as the original result).
        result += 1L << 32
        if result < 0:
            # Undo that, and try 64 bits.
            result -= 1L << 32
            result += 1L << 64
            assert result >= 0 # else addresses are fatter than 64 bits
    return result



def log(message, *args):
    """Log a processing information to STDERR.

    Arguments:

      message -- The text of a message.  Any object will be converted to a
        unicode string.
        
      *args -- message arguments.  When formatting the message with these
        arguments doesn't succeed, the arguemnts are simply appended to the end
        of the message.

    """
    if not isinstance(message, types.StringTypes):
        message = unicode(message)
    try:
        message %= args
    except TypeError:
        if not message.endswith(":"):
            message += ":"
        if not message.endswith(" "):
            message += " "
        message += ', '.join([unicode(a) for a in args])
    if not message.endswith("\n"):
        message += "\n"
    sys.stderr.write("  "+message.encode('iso-8859-2'))

