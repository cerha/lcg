#!/usr/bin/env python

import os
import sys
import gettext

try:
    source_dir, destination_dir, lcg_dir, lang = sys.argv[1:5]
    stylesheet = len(sys.argv) > 5 and sys.argv[5] or None
except ValueError:
    msg = "Usage: %s source_dir destination_dir lcg_dir lang [stylesheet]"
    raise Exception(msg % sys.argv[0])

resource_dir = os.path.join(lcg_dir, 'resources')
translation_dir = os.path.join(lcg_dir, 'translations')

t = gettext.translation('lcg', translation_dir, (lang,), fallback=True)
t.install(unicode=True)

import lcg
c = lcg.EurochanceCourse(source_dir, language=lang, input_encoding='utf-8',
                         default_resource_dir=resource_dir)
#e = lcg.ims.IMSExporter(c, destination_dir)
e = lcg.StaticExporter(c, destination_dir, stylesheet=stylesheet)
e.export()
