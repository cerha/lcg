# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004 Brailcom, o.p.s.
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

"""Feed the Learning Content Generator by data read from the resource.

The classes defined here allow to separate the low-level details of reading
data from various sources.  The output is always a 'Content' element (usually a
derived class).

"""

import imp
import re
import os
import commands
import string

from content import *


class Feeder(object):
    """Generic Feeder"""
    
    def feed(self):
        """Return a 'Content' instance constructed by reading Feeder source."""
        pass

class PySpecFeederError(Exception):
    """Exception reised when there is a problem loading specification file."""
    pass
    
class PySpecFeeder(Feeder):
    """Generic 'Feeder' reading its data from Python specification files."""

    
    def __init__(self, dir, name):
        self._dir = dir
        self._name = name

    def _get_module(self):
        module = file = None
        try:
            try:
                file, path, descr = imp.find_module(self._name, [self._dir])
                module = imp.load_module(self._name, file, path, descr)
            except ImportError, e:
                msg = "Unable to load specification file '%s':" % self._name
                raise PySpecFeederError(msg, self._dir, str(e))
        finally:
            if file is not None:
                file.close()
        return module

    def feed(self, parent):
        module = self._get_module()
        spec = getattr(module, 'content')
        return spec(parent)
    

class ExcelVocabFeeder(Feeder):
    """Vocabulary Feeder reading data from XLS file."""

    def __init__(self, dir, file):
        self._dir = dir
        self._file = file

    def feed(self, parent):
        filename = os.path.join(self._dir, self._file)
        command = 'xls2csv -q0 -c\| ' + filename # + ' | konwert iso2-utf8'
        status, output = commands.getstatusoutput(command)
        if status: raise Exception(output)
        items = []
        for line in output.splitlines():
            word, note, cz, sk = map(string.strip, line.split('|')[0:4])
            name = re.sub('[^a-zA-Z0-9-]', '', word.replace(' ', '-'))
            media_file = os.path.join('vocabulary', name + '.ogg')
            from content import VocabItem, VocabList
            items.append(VocabItem(parent, word, note, word,
                                   parent.media(media_file, tts_input=word)))
        return VocabList(parent, items)


# class InfoNode:
#     """Dictionary-like class which decodes a string to read (key, value) pairs.

#     The input string consists of lines of text, each o which starts with a key
#     separated by a colon from it's value.

#     Exapmle:

#     key1: value1
#     key2: value2

#     All initial and final blank characters are stripped from keys and values.
#     Newlines can be CR+LF or LF.
    
#     """
#     _info_matcher = re.compile(r"^(?P<key>[a-z-0-9]+): (?P<value>.*)$")

# class InfoNodeGroup:
#     """Reads a sequence of 'InfoNode' instances from a string.

    

    
#     """
#     _blank_line_matcher = re.compile(r"\r?\n\s*\r?\n")


# class InfoGroupSequence:
#     """Reads a sequence of 'InfoNodeGroup' instances from a string."""
#     _splitter_matcher = re.compile(r"\r?\n----+\s*\r?\n")


    
# class TextFileFeeder(Feeder):
#     """Read data from a text file"""
#     def __init__(file):
#         pass
        
    
# class TextFileExerciseFeeder(TextFileFeeder):
#     """Read exercises from a text file"""


#     def __init__(self, file):
#         self._file = file

#     def feed(self):
#         file = self._file
#         c = Counter(1)
#         if not os.path.exists(file):
#             return Content()
#         text = ''.join(open(file).readlines())
#         exercises = []

#         correct_response = os.path.join('media', 'correct-response.ogg')
#         incorrect_response = os.path.join('media', 'incorrect-response.ogg')
#         self._media.append(correct_response)
#         self._media.append(incorrect_response)
#         def response(correct):
#             return correct and correct_response or incorrect_response
        
#         for part in self._splitter_matcher.split(text):
#             spec = []
#             for section in self._blank_line_matcher.split(part.strip()):
#                 spec.append({})
#                 for line in section.splitlines():
#                     info = self._info_matcher.match(line)
#                     assert info, "%s: Invalid syntax: %s" %(file, line)
#                     spec[-1][info.group('key')] = info.group('value')

#             info = spec.pop(0)
#             f = os.path.join('exercises', info['file'])
#             self._media.append(f+'.ogg')

#             tasks = []
#             for task in spec:
#                 a_keys = filter(lambda k: k.startswith('choice-'), task.keys())
#                 a_keys.sort()
#                 assert task['correct'] in a_keys, \
#                        "%s: Invalid key %s specified as 'correct' for '%s'" % \
#                        (file, task['correct'], task['question'])
#                 a = map(lambda k: MultipleChoiceAnswer(task[k],
#                                                        response(task['correct']\
#                                                                 == k)),
#                         a_keys)
#                 tasks.append(Task(task['question'], a))
                
#             e = ComprehensionExercise(c.next(), tasks,
#                                       self._output_file_path(file+'.ogg'),
#                                       self._read_file(f))
#             exercises.append(e)
#         return Container(exercises)


