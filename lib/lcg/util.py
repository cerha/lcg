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

