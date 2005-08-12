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
    

        
class SplittableTextFeeder(Feeder):
    """Generic Feeder reading its data from a piece of text."""
    
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
        if word.endswith("(phr.)"):
            word = word[:-6].strip()
            is_phrase = True
        else:
            is_phrase = self._phrases
        if word.endswith(")"):
            p = word.find("(")
            note = word[p:]
            word = word[:p].strip()
        else:
            note = None
        return VocabItem(parent, word, note, translation,
                         translation_language=self._translation_language,
                         is_phrase=is_phrase)
    
    
class ExerciseFeeder(SplittableTextFeeder):
    """Turns a textual exercise spec. into a seq. of 'Exercise' instances."""

    _EXERCISE_SPLITTER = re.compile(r"\r?\n----+\s*\r?\n")
    _BLANK_LINE_SPLITTER = re.compile(r"\r?\n\s*\r?\n")
    _HEADER_MATCHER = re.compile(r"^(?P<key>[a-z0-9_]+): (?P<value>.*)$")
    _MULITLINE_ARG_MATCHER = \
            re.compile(r"^<(?P<key>[a-z_]+)>\s*$(?P<value>.*)^</(?P=key)>\s*$",
                       re.MULTILINE|re.DOTALL)
    _BODY_TASK_MATCHER = re.compile(r"^<task>\s*\r?\n(.*?)^</task>",
                                        re.MULTILINE|re.DOTALL)
    
    def feed(self, parent):
        return self._process_pieces(self._text, self._EXERCISE_SPLITTER,
                                    self._exercise, parent)
    
    def _exercise(self, text, parent):
        """Convert textual exercise specification into an Exercise instance."""
        type, kwargs, body = self._parse_exercise_spec(text)
        tasks = []
        if issubclass(type, Cloze):
            cstart = body.text().find("\n.. ") + 1
            if cstart != 0:
                s = self._BLANK_LINE_SPLITTER
                comments = [c.text()[3:]
                            for c in body.piece(cstart,None).split(s)]
                body = body.piece(0, cstart)
            else:
                comments = []
            tasks = (type.task_type()(body.text(), comments=comments), )
        elif body:
            pieces = body.split(self._BLANK_LINE_SPLITTER)
            i = 0
            while i < len(pieces):
                t = pieces[i]
                if i+1<len(pieces) and pieces[i+1].text().startswith('.. '):
                    comment = pieces[i+1].text()[3:]
                    i += 2
                else:
                    comment = None
                    i += 1
                tasks.append(self._read_task(type.task_type(), t, comment))
            if type == TrueFalseStatements and len(tasks) == 1:
                self._warn("TrueFalseStatements have only one task!", text)
            if type == Dictation  and len(tasks) != 1:
                self._warn("Dictation should have just one task!", text)
        elif kwargs.has_key('body'):
            body = kwargs['body'].replace('%', '%%')
            def maketask(match):
                t = SplittableText(match.group(1), input_file=text.input_file(),
                                   firstline=text.firstline())
                tasks.append(self._read_task(type.task_type(), t, None))
                return "%s"
            kwargs['body'] = self._BODY_TASK_MATCHER.sub(maketask, body)
        kwargs['tasks'] = tuple(tasks)
        return type(parent, **kwargs)
    
    def _parse_exercise_spec(self, text):
        parts = text.split(self._BLANK_LINE_SPLITTER, maxsplit=1)
        type, kwargs = self._read_header(parts[0].text())
        if len(parts) == 2:
            args, body = self._read_multiline_args(parts[1])
            kwargs.update(args)
        else:
            body = None
        return type, kwargs, body

    def _read_multiline_args(self, text):
        args = {}
        pointer = 0
        for match in self._MULITLINE_ARG_MATCHER.finditer(text.text()):
            if text.piece(pointer, match.start()).text().strip():
                break
            args[str(match.group('key'))] = match.group('value')
            pointer = match.end()
        body = text.piece(pointer, None)
        if not body.text().strip():
            body = None
        return args, body
        
    
    def _read_header(self, text):
        """Read exercise header and return the tuple (type, info).
        
        Here 'type' is the exercise class (read from the corresponding header
        field) and 'info' is a dictionary of all the remaining header fields.

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
    
    def _read_task(self, type, text, comment):
        # Read a task specification using a method according to given task type.
        try:
            method = {
                Selection:              self._read_choices,
                MultipleChoiceQuestion: self._read_prompt_and_choices,
                GapFillStatement:       self._read_gap_fill,
                FillInTask:             self._read_pair_of_statements,
                TransformationTask:     self._read_pair_of_statements,
                TrueFalseStatement:     self._read_true_false_statement,
                DictationTask:          self._read_generic_task,
                ClozeTask:              self._read_generic_task,
                }[type]
        except KeyError:
            raise Exception("Unknown type:", type)
        try:
            return method(type, text.text(), comment)
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
    
    def _read_generic_task(self, type, text, comment):
        return type(text, comment=comment)

    def _read_choices(self, type, text, comment):
        return type(self._process_choices(text.splitlines()), comment=comment)

    def _read_prompt_and_choices(self, type, text, comment):
        lines = text.splitlines()
        return type(lines[0], self._process_choices(lines[1:]), comment=comment)
    
    def _read_gap_fill(self, type, text, comment):
        lines = text.splitlines()
        if lines[0].find('___') != -1:
            choices = self._process_choices(lines[1:])
            return type(lines[0], choices, comment=comment)
        else:
            return type(text, (), comment=comment)
    
    def _read_pair_of_statements(self, type, text, comment):
        lines = text.splitlines()
        assert len(lines) == 2, \
               "Task specification must consist of just 2 lines (%d given)." % \
               len(lines)
        prompt, answer = [l.strip() for l in lines]
        if answer.startswith('[') and answer.endswith(']'):
            answer = answer[1:-1]
        return type(prompt.strip(), answer, comment=comment)

    def _read_true_false_statement(self, type, text, comment):
        text = text.strip()
        assert text.endswith('[T]') or text.endswith('[F]'), \
               "A true/false statement must end with '[T]' or '[F]'!"
        correct = text.endswith('[T]')
        text = ' '.join(map(string.strip, text.splitlines()))[:-3].strip()
        return type(text, correct=correct, comment=comment)
    
