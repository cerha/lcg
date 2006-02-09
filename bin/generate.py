#!/usr/bin/env python
# -*- coding: iso8859-2 -*-
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

"""A generator for the Eurochance courses."""

import os
from lcgmake import getoptions, usage

OPTIONS = (
    ('lang=', 'en', "The language of the course  (the taught language)."),
    ('user-lang=', 'cs', "The user's (learner's) language"),
    ('stylesheet=', 'default.css', "Filename of the stylesheet to use."),
    ('ims', False, "Generate an IMS package instead of a standalone HTML."),
    ('advanced', False, "This is the advanced version of the course.")
    )

def main():
    opt, args = getoptions(OPTIONS)
    if opt is None or len(args) != 2:
        usage(OPTIONS)
    source_dir, destination_dir = args

    lang = opt['lang']
    os.environ['LCG_LANGUAGE'] = lang
    import lcg
    
    from lcg.eurochance import IntermediateCourse, AdvancedCourse, \
                               EurochanceExporter
    if opt['advanced']:
        c = AdvancedCourse(source_dir, language=lang, input_encoding='utf-8')
    else:
        c = IntermediateCourse(source_dir, course_language=lang,
                               users_language=opt['user-lang'],
                               input_encoding='utf-8')
    if opt['ims']:
        exporter = lcg.ims.IMSExporter
    else:
        exporter = EurochanceExporter
        
    e = exporter(stylesheet=opt['stylesheet'])
    e.export(c, destination_dir)

    
if __name__ == "__main__":
    main()

