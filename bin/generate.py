#!/usr/bin/env python
#
# Copyright (C) 2004, 2005, 2006, 2007 Brailcom, o.p.s.
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

"""Eurochance language course generator."""

import os, lcg
from lcgmake import getoptions, usage

OPTIONS = (
    ('lang=', 'en', ("The course language.  A two-letter laguage code.  "
                     "For the Intermediate Course, it consists of a pair "
                     "(course language, users language) concatenated with "
                     "a hyphen - e.g. 'en-es').")),
    ('stylesheet=', 'default.css', "Filename of the stylesheet to use."),
    ('ims', False, "Generate an IMS package instead of a standalone HTML."),
    )

def main():
    opt, args = getoptions(OPTIONS)
    if opt is None or len(args) != 2:
        usage(OPTIONS)
    source_dir, destination_dir = args

    lang = opt['lang']
    
    from lcg.eurochance import EurochanceCourse, EurochanceExporter
    c = EurochanceCourse(source_dir, language=lang, input_encoding='utf-8')
    
    if opt['ims']:
        exporter = lcg.ims.IMSExporter
    else:
        exporter = EurochanceExporter
    t = lcg.GettextTranslator('-' in lang and lang[:2] or lang)
    e = exporter(translator=t, stylesheet=opt['stylesheet'])
    e.dump(c, destination_dir)

    
if __name__ == "__main__":
    main()

