# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004 Brailcom, o.p.s.
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

class SplittableText:
    """A piece of text which can be split keeping track of line numbers.

    The string representation of this class is the actual text.  The 'split()'
    method allows you to split the text into pieces (each represented by a new
    SplittableText instance) using any regex splitter.  The 'firstline()'
    method then reports the line number where the text of each part begins in
    the original text.  It keeps working when you split the pieces recursively.

    """
    
    def __init__(self, text, firstline=1):
        assert isinstance(text, types.StringTypes)
        assert isinstance(firstline, types.IntType)
        self._text = text
        self._firstline = firstline

    def text(self):
        """Return the actual text as a string or unicode."""
        return self._text

    def firstline(self):
        """Return the number of the first line of this text on input."""
        return self._firstline

    def _create_piece(self, start, end):
        # Create a piece as a substring of the text of this piece.
        n = len(self._text[:start].splitlines()) + self._firstline
        text = self._text[start:end].rstrip()
        return SplittableText(text, n)
    
    def split(self, matcher):
        """Return parts of the text as a tuple of SplittableText instances.

        The 'matcher' argument is an instance of compiled regular expression.
        This regex should match the splitter used to devide the pieces of the
        input text into subsequent parts.

        All beginning and trailing whitespace characters are stripped from
        the pieces of text.

        """
        pieces = []
        lastposition = len(self._text) - len(self._text.lstrip())
        for match in matcher.finditer(self._text):
            pieces.append(self._create_piece(lastposition, match.start()))
            lastposition = match.end()
        pieces.append(self._create_piece(lastposition, None))
        return pieces


class Counter(object):
    """Incrementing counter."""
    def __init__(self, initial_value=0):
        self._value = initial_value
        
    def next(self):
        value = self._value
        self._value = self._value + 1
        return value


class Record(object):
    """A generic class to store data.

    Each private attributte (beginning with a single underscore), that is
    created in the constructor can be accessed (read-only) via a public method
    of the same name (without the leading underscore).

    A derived class is responsible to initialize the attributes in its
    constructor.  It only deesn't have to define all the accessor methods.

    """
        
    def __getattr__(self, attr):
        if hasattr(self, '_'+attr):
            return lambda : getattr(self, '_'+attr)
        else:
            raise AttributeError("%s has no property '%s'" % \
                                 (self.__class__.__name__, attr))
                
    
def list_subdirs(dir):
    """Return the list of subdirectories found in dir.

    If the directory contains the file 'index.txt' the list is read from there.
    Otherwise all subdirectories in the directory are returned in alphabetical
    order.

    Directory names beginning with an underscore and 'CVS' directories are
    ignored.
    
    """
    try:
        index = open(os.path.join(dir, 'index.txt')).readlines()
        items = filter(len, map(string.strip, index))
    except:
        items = filter(lambda d: os.path.isdir(os.path.join(dir, d)) and \
                       d[0] != '_' and d != 'CVS', os.listdir(dir))
        items.sort()
    return items

def is_sequence_of(seq, cls):
    """Return true if 'seq' is a sequence of instances of 'cls'."""
    if not operator.isSequenceType(seq):
        return False
    for item in seq:
        if not isinstance(item, cls):
            return False
    return True

def copy_stream(input, output):
    """Kopíruj data ze streamu 'input' do streamu 'output'."""
    while True:
        data = input.read(4096)
        if not data:
            break
        output.write(data)
              
