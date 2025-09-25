# -*- coding: utf-8 -*-

# Copyright (C) 2004-2015 OUI Technology Ltd.
# Copyright (C) 2019, 2025 Tomáš Cerha <t.cerha@gmail.com>
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

import lcg


class Reader(lcg.DocFileReader):
    """Simple LCG Reader example.

    This is a very simple reader which reads in one file and processes it.  This
    reader doesn't do anything special.  You could however override its methods
    to customize the creation of the LCG document.

    Since we want to read a structured text document, the reader is derived from
    'lcg.DocFileReader'.  If we wanted a completely custom document creation
    (reading source text from a database, constructing it on the fly from some
    other source of data), we would derive just from 'lcg.Reader', but we would
    need to implement more of its methods.

    This reader is so simple, that it would be possible to achieve the same
    functionality without even defining a reader.  LCG knows to read textual
    documents by default (since 'lcg.DocFileReader' is the default reader
    class).  Thus this example is useful only as a template for other custom
    readers.  If you really wanted to just process one (structued) text file,
    you could simply invoke 'python -m lcg file.txt'.

    """

    def __init__(self, id, *args, **kwargs):
        # Force the name of the input file to the other file in the same directory.
        super(Reader, self).__init__('src', *args, **kwargs)

    # Here you would override the DocFileReader methods
