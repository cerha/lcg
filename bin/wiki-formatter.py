#!/usr/bin/env python

import sys, getopt, codecs, lcg

def main():
    try:
        optlist, args = getopt.getopt(sys.argv[1:], '',
                                      ('encoding=', 'stylesheet='))
        opt = dict(optlist)
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    
    try:
        filename = args[0]
        fh = codecs.open(filename, encoding=opt.get('--encoding', 'ascii'))
        try:
            text = ''.join(fh.readlines())
        finally:
            fh.close()
    except IndexError:
        text = ''.join(sys.stdin.readlines())

    n = lcg.WikiNode(text, language='en')
    e = lcg.Exporter(stylesheet=opt.get('--stylesheet'), inlinestyles=True)
    print e.page(n).encode('utf-8')

def usage():
    import os
    help = """Wiki to HTML formatter.
    
    Usage: %s [options] file

    Options:
    
      --encoding ...   the input encoding.  
      --stylesheet ... the filename of the stylesheet to be included in the
                       resulting HTML document
                       
    If no input file is specified, STDIN is used.  The HTML document is printed
    on STDOUT.  The output encoding is always UTF-8.
    """ % os.path.split(sys.argv[0])[-1]
    sys.stderr.write(help.replace("\n    ", "\n"))

if __name__ == "__main__":
    main()
