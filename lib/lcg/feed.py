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
import code

from content import *


class Feeder(object):
    """Generic Feeder"""
    
    def __init__(self, dir, file):
        """Initialize the Feeder.

        Arguments:

          dir -- the sourse directory
          file -- the source file name

        """
        self._dir = dir
        self._file = file
        assert os.path.exists(self._input_file()), \
               "File does not exest: " + self._input_file()

    def _input_file(self):
        return os.path.join(self._dir, self._file)
        
    def feed(self):
        """Return a 'Content' instance constructed by reading Feeder source."""
        pass


class PySpecFeederError(Exception):
    """Exception reised when there is a problem loading specification file."""
    pass


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
    """Vocabulary Feeder reading data from XLS file."""

    def feed(self, parent):
        command = 'xls2csv -q0 -c\| '+self._input_file() #+'| konwert iso2-utf8'
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
    

class ExerciseFeeder(Feeder):
    """Exercise Feeder reading data from a plain text file."""

    _splitter_matcher = re.compile(r"\r?\n----+\s*\r?\n")
    _blank_line_matcher = re.compile(r"\r?\n\s*\r?\n")
    _header_matcher = re.compile(r"^(?P<key>[a-z0-9_]+): (?P<value>.*)$")
        

    class _PieceOfText:
        """A piece of text which can be split keeping track of line numbers."""
        
        def __init__(self, text, firstline=1):
            assert type(text) == type('')
            assert type(firstline) == type(0)
            self._text = text
            self._firstline = firstline

        def __str__(self):
            return self._text

        def firstline(self):
            """Return the number of the first line of this text on input."""
            return self._firstline

        def _create_piece(self, start, end):
            # Create a piece as a substring of the text of this piece.
            n = len(self._text[:start].splitlines()) + self._firstline
            text = self._text[start:end].rstrip()
            return ExerciseFeeder._PieceOfText(text, n)
        
        def split(self, matcher):
            """Return parts of the text as a tuple of _PieceOfText instances.

            All beginning and trailing whitespace characters are stripped from
            the pieces of text.

            """
            pieces = []
            lastposition = len(self._text) - len(self._text.lstrip())
            for match in matcher.finditer(self._text):
                pieces.append(self._create_piece(lastposition, match.start()))
                lastposition = match.end()
            pieces.append(self._create_piece(lastposition, None))
            return pieces

        
    def feed(self, parent):
        text = self._PieceOfText(''.join(open(self._input_file()).readlines()))
        return Container(parent,
                         map(lambda piece: self._exercise(parent, piece),
                             text.split(self._splitter_matcher)))

    def _exercise(self, parent, text):
        """Convert textual exercise specification into an Exercise instance."""
        try:
            pieces = text.split(self._blank_line_matcher)
            assert len(pieces) >= 2, \
                   "Exercise must comprise a header and at least one task."
            type, kwargs = self._read_header(pieces[0])
            tasks = map(lambda p: self._read_task(parent, type.task_type(), p),
                        pieces[1:])
            kwargs['tasks'] = tuple(tasks)
            return type(parent, **kwargs)
        except SystemExit:
            sys.exit()
        except:
            m = "Exception caught while processing exercise specification:\n" +\
                '  File "%s", line %d\n' %(self._input_file(), text.firstline())
            sys.stderr.write(m)
            code.InteractiveInterpreter().showtraceback()
            sys.exit()
    
    def _read_header(self, text):
        info = {}
        for line in str(text).splitlines():
            match = self._header_matcher.match(line)
            assert match, "Invalid exercise header syntax: '%s'" % \
                   (self._input_file(), line)
            info[match.group('key')] = match.group('value')
        try:
            type = getattr(content, info['type'])
            #assert isinstance(type, Exercise), \
            #       "Invalid exercise class %s" % info['type']
            del(info['type'])
            return (type, info)
        except KeyError:
            raise Exception("Required exercise header item 'type' missing!")
        except AttributeError:
            raise Exception("Invalid exercise type: %s" % info['type'])
    
    def _read_task(self, parent, type, text):
        # Read a task specification using a method according to given task type.
        method = {
            Cloze:                  self._read_cloze,
            MultipleChoiceQuestion: self._read_multiple_choice_question,
            GapFillStatement:       self._read_gap_fill_statement,
            TrueFalseStatement:     self._read_true_false_statement,
            }[type]
        try:
            return method(parent, str(text))
        except:
            m = "Exception caught while processing task specification:\n" +\
                '  File "%s", line %d\n' %(self._input_file(), text.firstline())
            sys.stderr.write(m)
            code.InteractiveInterpreter().showtraceback()
            sys.exit()

    def _process_choices(self, text):
        # split the MultipleChoiceQuestion and its list of choices
        def choice(text):
            assert text.startswith('+ ') or text.startswith('- '), \
                   "A choice must start with a + or minus sign and a space!"
            correct = text.startswith('+ ')
            return Choice(text[2:].strip(), correct=correct)
        lines = text.splitlines()
        choices = map(choice, lines[1:])
        correct = filter(lambda ch: ch.correct(), choices)
        assert len(correct) == 1, \
               "Number of correct choices must be exactly one! " + \
               "%d of %d found." % (len(correct), len(choices))
        return (lines[0], choices)
    
    def _read_multiple_choice_question(self, parent, text):
        question, choices = self._process_choices(text)
        return MultipleChoiceQuestion(parent, question, choices)
    
    def _read_gap_fill_statement(self, parent, text):
        statement, choices = self._process_choices(text)
        assert statement.find('___') != -1, \
               "Gap-fill statement must include a gap marked by at least " + \
               "three underscores."
        return GapFillStatement(parent, statement, choices)
    
    def _read_cloze(self, parent, text):
        return Cloze(parent, text)

    def _read_true_false_statement(self, parent, text):
        text = text.strip()
        assert text.endswith('[T]') or text.endswith('[F]'), \
               "A true/false statement must end with '[T]' or '[F]'!"
        correct = text.endswith('[T]')
        text = ' '.join(map(string.strip, text.splitlines()))[:-3].strip()
        return TrueFalseStatement(parent, text, correct=correct)
    
