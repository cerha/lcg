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

"""Simple and `quite' generic LCG generator."""

import os
import sys, getopt, os, lcg

OPTIONS = (
    ('encoding=', 'utf-8', "Input encoding (output encoding is always utf-8)"),
    ('stylesheet=', 'default.css', "Filename of the stylesheet to use."),
    ('inline-styles', False, "Embed styles into the HTML pages."),
    ('ext=', 'txt', "Extension of the source files."),
    ('root=', 'index', "Filename of the root document."),
    ('translations=', None, "Colon separated list of translation directories."),
    ('sec-lang=', None, "Secondary content language (citations)."),
    ('html', False, "generate static HTML files (default)."),
    ('hhp', False, "generate a MS HTML Help Workshop package."),
    ('ims', False, "generate an IMS package."),
    )

def main():
    opt, args = getoptions(OPTIONS)
    if opt is None or len(args) != 2:
        usage(OPTIONS)
    source_dir, destination_dir = args

    formats = [k for k in ('html', 'ims', 'hhp') if opt[k]]
    if not formats:
        output_format = 'html'
    elif len(formats) > 1:
        lcg.log("Select just one output format!")
        sys.exit()
    else:
        output_format = formats[0]
    
    reader = lcg.reader(source_dir, opt['root'], ext=opt['ext'], encoding=opt['encoding'])
    doc = reader.build()
    
    translations = (lcg.config.translation_dir,)
    if opt['translations']:
        translations += tuple([os.path.abspath(d) for d in opt['translations'].split(':')])

    if output_format == 'hhp':
        from lcg import hhp
        exporter = hhp.HhpExporter
    elif output_format == 'ims':
        from lcg import ims
        exporter = ims.IMSExporter
    else:
        exporter = lcg.HtmlStaticExporter
    e = exporter(stylesheet=opt['stylesheet'], inlinestyles=opt['inline-styles'],
                 translations=translations)
        
    e.dump(doc, destination_dir, sec_lang=opt['sec-lang'])


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
    try:
        main()
    except KeyboardInterrupt:
        raise
    except SystemExit:
        raise
    except:
        einfo = sys.exc_info()
        try:
            import cgitb
            sys.stderr.write(cgitb.text(einfo))
        except Exception, e:
            sys.stderr.write("Unable to generate detailed traceback: "+ str(e) +"\n")
            import traceback
            traceback.print_exception(*einfo)
