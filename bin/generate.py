#!/usr/bin/env python

import sys
import gettext

try:
    source_dir, destination_dir, lang = sys.argv[1:4]
    stylesheet = len(sys.argv) > 4 and sys.argv[4] or None
except ValueError:
    raise Exception("Usage: %s source_dir destination_dir lang [stylesheet]" % \
                    sys.argv[0])

t = gettext.translation('lcg', 'translations', (lang,), fallback=True)
t.install(unicode=True)

import lcg
c = lcg.course.EurochanceCourse(source_dir, language=lang,
                                input_encoding='utf-8')
#e = lcg.ims.IMSExporter(c, destination_dir)
e = lcg.export.StaticExporter(c, destination_dir, stylesheet=stylesheet)

e.export()
