#!/usr/bin/env python
#
# Copyright (C) 2004-2007 Brailcom, o.p.s.
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

"""A simple LCG structured text formatter."""

import sys, os, getopt, codecs, lcg

def main():
    try:
        optlist, args = getopt.getopt(sys.argv[1:], '',
                                      ('encoding=', 'title=', 'stylesheet='))
        opt = dict(optlist)
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    
    try:
        filename = args[0]
        name, ext = os.path.splitext(filename)
        fh = codecs.open(filename, encoding=opt.get('--encoding', 'ascii'))
        try:
            text = ''.join(fh.readlines())
        finally:
            fh.close()
    except IndexError:
        text = ''.join(sys.stdin.readlines())
        name = 'index'
    title = opt.get('--title')
    sections = lcg.Parser().parse(text)
    if title is None:
        if len(sections) != 1 or not isinstance(sections[0], lcg.Section):
            raise Exception("The document has no top-level section:", id)
        s = sections[0]
        title = s.title()
        sections = s.content()
    rp = lcg.FileResourceProvider('.', '.',
                                  lcg.SharedResourceProvider('.'))
    node = lcg.ContentNode(name, title=title, language='en',
                           content=lcg.SectionContainer(sections),
                           resource_provider=rp)
    e = lcg.HtmlStaticExporter(stylesheet=opt.get('--stylesheet'),
                               inlinestyles=True)
    if name:
        e.dump(node, '.')
    else:
        print e.export(node).encode('utf-8')

def usage():
    import os
    help = """Wiki to HTML formatter.
    
    Usage: %s [options] file

    Options:
    
      --encoding   ... the input encoding.  
      --title      ... document title (can be also defined as a top level
                       section within the document.  
      --stylesheet ... the filename of the stylesheet to be included in the
                       resulting HTML document
                       
    If no input file is specified, STDIN is used.  The HTML document is printed
    on STDOUT.  The output encoding is always UTF-8.
    """ % os.path.split(sys.argv[0])[-1]
    sys.stderr.write(help.replace("\n    ", "\n"))

if __name__ == "__main__":
    main()
