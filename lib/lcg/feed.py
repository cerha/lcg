# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005 Brailcom, o.p.s.
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
derived class) or a sequence of elements.

"""

import re
import os
import commands
import string
import traceback
import codecs
import imp

from lcg import *


class Feeder(object):
    """Generic Feeder"""
    
    def __init__(self, input_encoding='ascii'):
        """Initialize the Feeder.

        Arguments:

          encoding -- the source data encoding

        """
        self._input_encoding = input_encoding

    def feed(self, parent):
        """Return a 'Content' instance constructed by reading Feeder source."""
        pass

    def _current_input_position(self, object):
        """Return the current position within the source data as a string."""
        return None

    def _panic(self, message, einfo, object=None):
        position = self._current_input_position(object)
        if position is not None:
            message += ":\n  " + position
        sys.stderr.write(message + "\n")
        apply(traceback.print_exception, einfo)
        sys.exit()

    def _warn(self, message, object=None):
        position = self._current_input_position(object)
        if position is not None:
            message += ": " + position
        sys.stderr.write('Warning: %s\n' % message)
    
class FileFeeder(Feeder):
    """Generic Feeder reading its data from an input file."""
    
    def __init__(self, filename, **kwargs):
        """Initialize the Feeder.

        Arguments:

          file -- the source file name

          All the remaining arguments are inherited from parent class.

        """
        super(FileFeeder, self).__init__(**kwargs)
        assert os.path.exists(filename), "File does not exest: " + filename
        self._filename = filename

    def _current_input_position(self, line):
        pos = 'File "%s"' % self._filename
        if line is not None:
            assert isinstance(line, types.IntType)
            pos += ", line %d" % line
        return pos

    
class PySpecFeederError(Exception):
    """Exception reised when there is a problem loading specification file."""


class PySpecFeeder(FileFeeder):
    """A 'Feeder' reading its data from Python specification files.

    This allows the most simple and generic way of specifying content which
    does not need any conversion.  You define the content simply in a Python
    data structure.

    The mechanism is based on calling a function 'content()' in the
    specification file.  This function must return a 'Content' instance.

    """

    def _get_module(self):
        module = file = None
        dirname, filename = os.path.split(self._filename)
        modulename, ext = os.path.splitext(filename)
        assert ext.lower() == '.py'
        try:
            try:
                file, path, descr = imp.find_module(modulename, [dirname])
                module = imp.load_module(modulename, file, path, descr)
            except ImportError, e:
                msg = "Unable to load specification file '%s':" % self._filename
                raise PySpecFeederError(msg, dirname, str(e))
        finally:
            if file is not None:
                file.close()
        return module

    def feed(self, parent):
        module = self._get_module()
        spec = getattr(module, 'content')
        return spec(parent)
    

class SplittableTextFeeder(Feeder):
    """Generic Feeder reading its data from a piece of textan input file."""
    
    def __init__(self, text, **kwargs):
        """Initialize the Feeder.
    
        Arguments:

          text -- the source text as a SplittableText instance or a sequence of
            SplittableText instances.
          
          All the remaining arguments are inherited from parent class.
          
        """
        super(SplittableTextFeeder, self).__init__(**kwargs)
        assert isinstance(text, SplittableText)
        self._text = text

    def _current_input_position(self, text):
        if text is not None:
            assert isinstance(text, SplittableText)
        else:
            text = self._text
        return 'File "%s", line %d' % (text.input_file(),
                                       text.firstline())

    def _process_pieces(self, text, splitter, func, *args):
        def f(piece):
            try:
                return func(piece, *args)
            except SystemExit:
                sys.exit()
            except:
                self._panic(self.__class__.__name__ + " failed",
                            sys.exc_info(), piece)
        return [x for x in [f(piece) for piece in text.split(splitter)
                            if piece.text()] if x is not None]
    
    
class VocabFeeder(SplittableTextFeeder):
    """Vocabulary Feeder"""
    
    _LINE_SPLITTER = re.compile(r"\r?\n")
    _ITEM_SPLITTER = re.compile(r"\s*::\s*")
    
    def __init__(self, text, translation_language, **kwargs):
        assert isinstance(translation_language, types.StringType) and \
               len(translation_language) == 2
        self._translation_language = translation_language
        self._phrases = False
        super(VocabFeeder, self).__init__(text, **kwargs)
    
    def feed(self, parent):
        return self._process_pieces(self._text, self._LINE_SPLITTER,
                                    self._item, parent)

    def _item(self, line, parent):
        if line.text().startswith("#"):
            if line.text().startswith("# phrases"):
                self._phrases = True
            return None
        word, translation = [x.text() for x in line.split(self._ITEM_SPLITTER)]
        if word.endswith(")"):
            p = word.find("(")
            note = word[p:]
            word = word[:p].strip()
        else:
            note = None
        return VocabItem(parent, word, note, translation or u"???",
                         translation_language=self._translation_language,
                         is_phrase=self._phrases)
    
    
class ExerciseFeeder(SplittableTextFeeder):
    """Exercise Feeder reading data from a plain text file."""

    _EXERCISE_SPLITTER = re.compile(r"\r?\n----+\s*\r?\n")
    _BLANK_LINE_SPLITTER = re.compile(r"\r?\n\s*\r?\n")
    _HEADER_MATCHER = re.compile(r"^(?P<key>[a-z0-9_]+): (?P<value>.*)$")
    
    def __init__(self, text, vocabulary=(), **kwargs):
        """Initialize the Feeder.
    
        Arguments:

          vocabulary -- the sequence of VocabItem instances.  This vocabulary
            is used for the VocabExercise, if this exercise is found in the
            specification.
          
          All the remaining arguments are inherited from parent class.
          
        """
        super(ExerciseFeeder, self).__init__(text, **kwargs)
        assert is_sequence_of(vocabulary, VocabItem)
        self._vocabulary = vocabulary
        
    def feed(self, parent):
        return self._process_pieces(self._text, self._EXERCISE_SPLITTER,
                                    self._exercise, parent)
    
    def _exercise(self, text, parent):
        """Convert textual exercise specification into an Exercise instance."""
        pieces = text.split(self._BLANK_LINE_SPLITTER)
        assert len(pieces) >= 1, \
               "Exercise specification must contain a header."
        type, kwargs = self._read_header(pieces[0].text())
        task_specs = pieces[1:]            
        if type == SentenceCompletion:
            if len(task_specs) > 0:
                self._warn("SentenceCompletion should not have any tasks",
                           text)
            tasks = ()
        elif type == VocabExercise and len(task_specs) == 0:
            tasks = [ClozeTask("%s [%s]" % (i.translation(), i.word()))
                     for i in self._vocabulary]
        else:
            assert len(task_specs) >= 1, "No tasks found."
            if type == TrueFalseStatements and len(task_specs) == 1:
                self._warn("TrueFalseStatements have only onetask!", text)
            tasks = [self._read_task(type.task_type(), p)
                     for p in task_specs]
        kwargs['tasks'] = tuple(tasks)
        return type(parent, **kwargs)
    
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
            DictationTask:          self._read_dictation,
            TransformationTask:     self._read_transformation,
            Selection:              self._read_selection,
            MultipleChoiceQuestion: self._read_multiple_choice_question,
            GapFillStatement:       self._read_gap_fill_statement,
            TrueFalseStatement:     self._read_true_false_statement,
            }[type]
        try:
            return method(text.text())
        except:
            m = "Exception caught while processing task specification"
            self._panic(m, sys.exc_info(), text)

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
        return GapFillStatement(lines[0], self._process_choices(lines[1:]))
    
    def _read_cloze(self, text):
        return ClozeTask(text)

    def _read_dictation(self, text):
        return DictationTask(text)

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
    
