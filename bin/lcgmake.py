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

"""Simple and `quite' generic LCG generator."""

import os
import sys, getopt, os

OPTIONS = (
    ('language=', 'en', "The language to use."),
    ('encoding=', 'utf-8', "Input encoding (output encoding is always utf-8)"),
    ('stylesheet=', None, "Filename of the stylesheet to use."),
    ('ext=', 'txt', "Extension of the source files."),
    ('root=', 'index', "Filename of the root document."),
    ('hhp', False, "generate a MS HTML Help Workshop package."),
    )

def main():
    opt, args = getoptions(OPTIONS)
    if opt is None or len(args) != 2:
        usage(OPTIONS)
    source_dir, destination_dir = args

    os.environ['LCG_LANGUAGE'] = opt['language']
    import lcg
    
    doc = lcg.DocRoot(source_dir, id=opt['root'], ext=opt['ext'],
                      language=opt['language'], input_encoding=opt['encoding'])
    
    if opt['hhp']:
        from lcg import hhp
        e = hhp.HhpExporter(stylesheet=opt['stylesheet'])
    else:
        e = lcg.StaticExporter(stylesheet=opt['stylesheet'])
    e.export(doc, destination_dir)


def getoptions(optspec):
    import getopt
    try:
        optlist, args = getopt.getopt(sys.argv[1:], '', [x[0] for x in optspec])
    except getopt.GetoptError:
        return None, None
    opt = dict(optlist)
    options = {}
    for option, default, descr in optspec:
        if option.endswith('='):
            option = option[:-1]
            options[option] = opt.get('--'+option, default)
        else:
            options[option] = opt.has_key('--'+option)
    return options, args


def dumpoptions(optspec, width=80, indent=3):
    from textwrap import wrap
    options = []
    maxlen = 0
    for option, default, descr in optspec:
        if option.endswith('='):
            option += '<value>'
        descr += "  Default is %r." % default
        maxlen = max(maxlen, len(option))
        options.append((option, descr))
    spacer = ' '*(maxlen+7+indent)
    return "\n".join(["%s--%s ... " % (indent*' ', o.ljust(maxlen)) + \
                      ("\n"+spacer).join(wrap(d, width-len(spacer)))
                      for o, d in options])


def usage(optspec):
    help = "Usage: %s [options] source_dir destination_dir\n\nOptions:\n%s\n" %\
           (os.path.split(sys.argv[0])[-1],
            dumpoptions(optspec, width=80, indent=2))
    sys.stderr.write(help)
    sys.exit(2)

    
if __name__ == "__main__":
    main()
