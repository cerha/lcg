#!/usr/bin/env python

import lcg
import sys

source_dir = sys.argv[1]
destination_dir = sys.argv[2]

course = lcg.course.EurochanceCourse(source_dir)

#lcg.ims.IMSExporter(course, destination_dir).export()
lcg.export.StaticExporter(course, destination_dir).export()
