#!/usr/bin/env python

import lcg
import sys

source_dir = sys.argv[1]
destination_dir = sys.argv[2]
stylesheet = len(sys.argv) > 3 and sys.argv[3] or None

c = lcg.course.EurochanceCourse(source_dir)

#e = lcg.ims.IMSExporter(c, destination_dir)
e = lcg.export.StaticExporter(c, destination_dir, stylesheet=stylesheet)

e.export()
