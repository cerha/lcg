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

import re
import os
import commands
import string
import traceback
import codecs
import unicodedata

import imp
import util

from content import *


class Feeder(object):
    """Generic Feeder"""
    
    def __init__(self, dir, file, encoding='ascii'):
        """Initialize the Feeder.

        Arguments:

          dir -- the source directory
          file -- the source file name
          encoding -- the source file encoding

        """
        self._dir = dir
        self._file = file
        self._encoding = encoding
        assert os.path.exists(self._input_file()), \
               "File does not exest: " + self._input_file()

    def _input_file(self):
        return os.path.join(self._dir, self._file)
        
    def feed(self):
        """Return a 'Content' instance constructed by reading Feeder source."""
        pass


class PySpecFeederError(Exception):
    """Exception reised when there is a problem loading specification file."""


class PySpecFeeder(Feeder):
    """Generic 'Feeder' reading its data from Python specification files.

    This allows the most simple way of specifying content which does not need
    any conversion.  You define the content simply in a Python data structure.

    The mechanism is based on calling a function 'content()' in the
    specification file.  This function must return a 'Content' instance.

    The specification file is in fact a Python module.  The name given as
    constructor argument 'file' must not contain the '.py' extension.

    """
    
    def _input_file(self):
        return super(PySpecFeeder, self)._input_file() + '.py'

    def _get_module(self):
        module = file = None
        try:
            try:
                file, path, descr = imp.find_module(self._file, [self._dir])
                module = imp.load_module(self._file, file, path, descr)
            except ImportError, e:
                msg = "Unable to load specification file '%s':" % self._file
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
    """Vocabulary Feeder reading data from an XLS file."""
    
    _TRANSLATION_ORDER = ('en', 'de', 'cs', 'es', 'no', 'sk')
    
    _ENCODING = {'cs': 'iso-8859-2',
                 'sk': 'iso-8859-2'}
    
    def feed(self, parent):
        command = 'xls2csv -q0 -c\| %s' % self._input_file()
        status, output = commands.getstatusoutput(command)
        if status: raise Exception(output)
        encoding = self._ENCODING.get(parent.language(), 'iso-8859-1')
        translation_language = 'cs' # TODO: pass from somewhere...
        order = [l for l in self._TRANSLATION_ORDER if l != parent.language()]
        translation_index = order.index(translation_language)
        translation_encoding = self._ENCODING.get(translation_language,
                                                  'iso-8859-1')
        items = []
        diacritics_matcher = re.compile(r" WITH .*")
        danger_char_matcher = re.compile(r"[^a-zA-Z0-9-]")
        def safe_char(match):
            char = match.group(0)
            if char in ('.', ',', '?', '!', ':', ';'): return ''
            safe_name = diacritics_matcher.sub('', unicodedata.name(char))
            safe_char = unicodedata.lookup(safe_name)
            return danger_char_matcher.match(safe_char) and '-' or safe_char
        for line in output.splitlines():
            col = map(string.strip, line.split('|')[0:4])
            try:
                word = unicode(col[0], encoding=encoding)
            except UnicodeDecodeError, e:
                raise Exception("Error while reading file %s: %s: %s" %
                                (self._input_file(), e, col[0]))
            if word.startswith("#"):
                continue
            note = unicode(len(col) > 1 and col[1] or '',
                           encoding=self._encoding)
            try:
                t = col[translation_index + 2]
                trans = unicode(t, translation_encoding)
            except IndexError:
                trans = u'???'
                #print 'No translation for "%s"!' % word
            name = danger_char_matcher.sub(safe_char, word.replace(' ', '-'))
            media_file = os.path.join('vocabulary', name + '.ogg')
            items.append(VocabItem(parent, word, note, trans,
                                   parent.media(media_file, tts_input=word)))
        return VocabList(parent, items)
    
    
class ExerciseFeeder(Feeder):
    """Exercise Feeder reading data from a plain text file."""

    _SPLITTER_MATCHER = re.compile(r"\r?\n----+\s*\r?\n")
    _BLANK_LINE_MATCHER = re.compile(r"\r?\n\s*\r?\n")
    _HEADER_MATCHER = re.compile(r"^(?P<key>[a-z0-9_]+): (?P<value>.*)$")
        
    def feed(self, parent):
        fh = codecs.open(self._input_file(), encoding=self._encoding)
        try:
            content = ''.join(fh.readlines())
        except UnicodeDecodeError, e:
            raise Exception("Error while reading file %s: %s" % \
                            (self._input_file(), e))
        fh.close()
        text = SplittableText(content)
        exercises = [self._exercise(parent, piece)
                     for piece in text.split(self._SPLITTER_MATCHER)]
        return Container(parent, exercises)

    def _exercise(self, parent, text):
        """Convert textual exercise specification into an Exercise instance."""
        try:
            pieces = text.split(self._BLANK_LINE_MATCHER)
            assert len(pieces) >= 2, \
                   "Exercise must comprise a header and at least one task."
            type, kwargs = self._read_header(pieces[0].text())
            tasks = [self._read_task(type.task_type(), p.text())
                     for p in pieces[1:]]
            kwargs['tasks'] = tuple(tasks)
            return type(parent, **kwargs)
        except SystemExit:
            sys.exit()
        except:
            m = "Exception caught while processing exercise specification:\n" +\
                '  File "%s", line %d\n' %(self._input_file(), text.firstline())
            sys.stderr.write(m)
            apply(traceback.print_exception, sys.exc_info())
            sys.exit()
    
    def _read_header(self, text):
        """Read excercise header and return the tuple (type, info).
        
        Here the 'type' is a class of the exercise got by name read as the
        corresponding header field and 'info' is a dictionary of all other
        header fields.  This dictionary is supposed to be used as 

        """
        info = {}
        for line in text.splitlines():
            match = self._HEADER_MATCHER.match(line)
            assert match, "Invalid exercise header syntax."
            info[str(match.group('key'))] = match.group('value')
        try:
            type = getattr(content, str(info['type']))
            assert issubclass(type, Exercise), \
                   "Invalid exercise class %s:" % type
            del(info['type'])
            return (type, info)
        except KeyError:
            raise Exception("Required exercise header item 'type' missing!")
        except AttributeError:
            raise Exception("Invalid exercise type: %s" % info['type'])
    
    def _read_task(self, type, text):
        # Read a task specification using a method according to given task type.
        method = {
            ClozeTask:              self._read_cloze,
            TransformationTask:     self._read_transformation,
            Selection:              self._read_selection,
            MultipleChoiceQuestion: self._read_multiple_choice_question,
            GapFillStatement:       self._read_gap_fill_statement,
            TrueFalseStatement:     self._read_true_false_statement,
            }[type]
        try:
            return method(unicode(text))
        except:
            m = "Exception caught while processing task specification:\n" +\
                '  File "%s", line %d\n' %(self._input_file(), text.firstline())
            sys.stderr.write(m)
            apply(traceback.print_exception, sys.exc_info())
            sys.exit()

    def _process_choices(self, lines):
        # split the list of choices
        def choice(text):
            assert text.startswith('+ ') or text.startswith('- '), \
                   "A choice must start with a + or minus sign and a space!"
            correct = text.startswith('+ ')
            return Choice(text[2:].strip(), correct=correct)
        choices = map(choice, lines)
        correct = filter(lambda ch: ch.correct(), choices)
        assert len(correct) == 1, \
               "Number of correct choices must be exactly one! " + \
               "%d out of %d found." % (len(correct), len(choices))
        return choices
    
    def _read_selection(self, text):
        return Selection(self._process_choices(text.splitlines()))

    def _read_multiple_choice_question(self, text):
        lines = text.splitlines()
        return MultipleChoiceQuestion(lines[0],self._process_choices(lines[1:]))
    
    def _read_gap_fill_statement(self, text):
        lines = text.splitlines()
        assert lines[0].find('___') != -1, \
               "Gap-fill statement must include a gap marked by at least " + \
               "three underscores."
        return GapFillStatement(lines[0],
                                self._process_choices(lines[1:]))
    
    def _read_cloze(self, text):
        return ClozeTask(text)

    def _read_transformation(self, text):
        lines = text.splitlines()
        assert len(lines) == 2, \
               "Transformation task specification must consist of just two " + \
               "lines (%d given)." % len(lines)
        orig, transformation = lines
        if transformation.find('[') == -1:
            transformation = '['+transformation+']'
        return TransformationTask(orig, transformation)

    def _read_true_false_statement(self, text):
        text = text.strip()
        assert text.endswith('[T]') or text.endswith('[F]'), \
               "A true/false statement must end with '[T]' or '[F]'!"
        correct = text.endswith('[T]')
        text = ' '.join(map(string.strip, text.splitlines()))[:-3].strip()
        return TrueFalseStatement(text, correct=correct)
    
