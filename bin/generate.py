#!/usr/bin/env python

import lcg
import sys

lang = 'en'
source_dir = sys.argv[1]
destination_dir = sys.argv[2]

lcg.course.Course(source_dir, lang).export(destination_dir)
