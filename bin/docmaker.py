#!/usr/bin/env python
# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005 Brailcom, o.p.s.
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

"""A generator for the LCG documentation."""

import sys, getopt, codecs, lcg

def main():
    try:
        optlist, args = getopt.getopt(sys.argv[1:], '',
                                      ('encoding=', 'stylesheet='))
        opt = dict(optlist)
        source_dir, destination_dir = args
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    except ValueError:
        usage()
        sys.exit(2)
        
    #lcg.set_language('en')
    
    from lcg.eurochance import DocMaker
    doc = DocMaker(source_dir, "LCG documentation",
                   input_encoding=opt.get('--encoding', 'utf-8'))
    e = lcg.StaticExporter(stylesheet=opt.get('--stylesheet'))
    e.export(doc, destination_dir)

def usage():
    import os
    help = """Usage: %s [options] source_dir destination_dir

    Options:
    
      --encoding   ... the input encoding.
      --stylesheet ... the filename of the stylesheet to use.
                       
    The output encoding is always UTF-8.
    """ % os.path.split(sys.argv[0])[-1]
    sys.stderr.write(help.replace("\n    ", "\n"))

if __name__ == "__main__":
    main()
