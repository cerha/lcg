#!/usr/bin/env python

import lcg
import sys

source_dir = sys.argv[1]
destination_dir = sys.argv[2]

lcg.course.EurochanceCourse(source_dir).export(destination_dir)
