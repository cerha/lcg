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

"""Course content abstraction.

This module provides classes for representation of content elements in an
abstract container capable of HTML export.

"""

import string
import wiki
import re
import types

from util import *
from course import *

class Content(object):
    """Generic base class for all types of content.

    One instance always makes a part of one document -- it cannot be split over
    multiple output documents.  On the other hand, one document may consist of
    multiple 'Content' instances (in theory).

    Each content element may contain other content elements and thus they make
    a tree structure.  All the elements within this structure have the same
    parent 'ContentNode' instance and through it are able to gather some
    context information, such as input/output directory etc.  This is sometimes
    necessary to generete correct HTML output (e.g. URI for links etc.).

    """
    def __init__(self, parent):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.

        """
        assert isinstance(parent, ContentNode), \
               "Not a 'ContentNode' instance: %s" % parent
        self._parent = parent
        
    def export(self):
        """Return the HTML formatted content as a string."""
        return ''
 
    
class TableOfContents(Content):
    """Table Of Contents renders as a tree of links to all subsequent nodes."""

    def _export_node(self, node, indent=''):
        if len(node.children()) == 0:
            return ''
        return "\n" + indent + "<ul>\n" + \
               "\n".join(map(lambda n: '%s  <li><a href="%s">%s</a>%s</li>' % \
                             (indent, n.output_file(), n.title(),
                              self._export_node(n, indent+'    ')),
                             node.children())) + \
                             "\n" + indent + "</ul>\n" + indent[0:-2] 
    
    def export(self):
        return "<h2>Table of Contents</h2>\n" + self._export_node(self._parent)

    
class Container(Content):
    """Container of multiple parts, each of which is a 'Content' instance.

    'Container' exports all the parts concatenated in unchanged order.

    """

    def __init__(self, parent, parts):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          parts -- Sequence of 'Content' instances in the order in which they
            should appear in the output..

        """
        self._parts = parts
        super(Container, self).__init__(parent)
        
    def export(self):
        return '\n'.join(map(lambda p: p.export(), self._parts))

    
class GenericText(Content):
    """Generic parent class for content generated from a piece of text."""

    def __init__(self, parent, text):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          text -- the actual text content of this element as a string.

        """
        self._text = text
        super(GenericText, self).__init__(parent)

    def export(self):
        return self._text

        
class WikiText(GenericText):
    """Structured text in Wiki formatting language (on input)."""
    
    def export(self):
        return wiki.format(self._text)

    

    
class VocabList(Content):
    """Vocabulary listing consisting of multiple 'VocabItem' instances."""

    
    def __init__(self, parent, items):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          items -- Sequence of 'VocabItem' instances.

        """
        assert is_sequence_of(items, VocabItem)
        self._items = items
        super(VocabList, self).__init__(parent)

    def export(self):
        rows = map(lambda i:
                   '<tr><td><a href="%s">%s</a> %s</td><td>%s</td></tr>' % \
                   (i.sound_file().url(), i.word(), i.note(), i.translation()),
                   self._items)
        return '<table>\n' + '\n'.join(rows) + "\n</table>\n"

    
class VocabItem(Record):
    """One item of vocabulary listing."""
    
    def __init__(self, parent, word, note, translation, sound_file):
        """Initialize the instance.
        
        Arguments:
          word -- The actual piece of vocabulary as a string
          note -- Notes in parens as a string.  Can contain multiple notes
            in parens separated by spaces.  Typical notes are for example
            (v) for verb etc.
          translation -- the translation of the word into target language.
          sound_file -- corresponding sound file as a 'Media' instance.
        
        """
        assert type(word) == type('')
        assert type(note) == type('')
        assert type(translation) == type('')
        assert isinstance(sound_file, Media)
        self._word = word
        self._note = note
        self._translation = translation
        self._sound_file = sound_file


################################################################################
################################     Tasks     #################################
################################################################################

class Task(Content):
    """This class an abstract base class for various concrete tasks.

    A set of concrete tasks is a part of each 'Exercise'.

    """
    pass


class MultipleChoiceQuestion(Task):
    """Answer a question by selecting from a list of predefined choices."""
    
    def __init__(self, parent, question, choices):
        """Initialize the instance.

        Arguments:
        
          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          question --  exercise within the containing section.
          choices -- sequence of 'Choice' instances related to this Task.
          
        """
        assert type(question) == type('')
        assert is_sequence_of(choices, Choice)
        self._question = question
        self._choices = choices
        self._response = {
            True: parent.media('correct-response.ogg', shared=True,
                               tts_input='correct'),
            False: parent.media('incorrect-response.ogg', shared=True,
                                tts_input='you are wrong!') }
        super(MultipleChoiceQuestion, self).__init__(parent)

    def _export_choices(self, choices):
        return '<ol style="list-style-type: lower-latin;">\n' + \
               "\n".join(map(lambda a: "  <li>%s</li>" % a, choices)) +"\n"+ \
               "</ol>\n"
        
    def export(self):
        choices = map(lambda a: '<a href="%s">%s</a>' % \
                      (self._response[a.correct()].url(), a.answer()),
                      self._choices)
        return "<p>%s\n%s</p>\n"%(self._question, self._export_choices(choices))

    
class Choice(Record):
    """Answer text with an information whether it is correct or not.

    One of the choices for 'MultipleChoiceQuestion'.

    """
    def __init__(self, answer, correct=False):
        assert type(answer) == type('')
        assert type(correct) == type(True)
        self._answer = answer
        self._correct = correct

        
class TrueFalseStatement(MultipleChoiceQuestion):
    """The goal is to indicate whether the statement is true or false."""
    
    def __init__(self, parent, statement, correct=True):
        """Initialize the instance.

        Arguments:
        
          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          statement --  exercise within the containing section.
          correct -- boolean flag indicating whether the statement is correct
            or not (true when it is correct).
          
        """
        assert type(correct) == type(True)
        choices = (Choice('TRUE', correct), Choice('FALSE', not correct))
        super(TrueFalseStatement, self).__init__(parent, statement, choices)
        
    def _export_choices(self, choices):
        return "\n".join(map(lambda a: "[%s]" % a, choices)) + "\n"


class GapFillStatement(MultipleChoiceQuestion):
    """The goal is to select the correct word to complete the sentence."""


class Cloze(Task):

    def __init__(self, parent, text):
        assert type(text) == type('')
        self._text = text
        super(Cloze, self).__init__(parent)

    def _make_field(self, match):
        word = match.group(1)
        return '<input style="border: solid gray 1px; padding: 1px;' + \
               ' margin: 1px; background: #e8e8e8" '+\
               'type="text" size="%d">' % (len(word) + 1)
        
    def export(self):
        text = re.sub("\((\w+)\)", self._make_field, self._text)
        return "<p>" + text + "</p>"
        

################################################################################
################################   Exercises   #################################
################################################################################

    
class Exercise(Content):
    """Exercise consists of an assignment and a set of tasks."""

    _task_type = Task
    _name = None
    
    def __init__(self, parent, tasks):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          tasks -- sequence of 'Task' instances related to this exercise.
          
        """
        assert is_sequence_of(tasks, self._task_type), \
               "Tasks must be a sequence of '%s' instances!" % \
               self._task_type.__class__.__name__
        self._number = parent.counter().next()
        self._tasks = tasks
        super(Exercise, self).__init__(parent)
        
    def export(self):
        name = self._name and " &ndash; " + self._name or ''
        return "<h3>Exercise %d" % self._number + name + "</h3>\n\n" + \
               self._export_instructions() + "\n\n" + \
               "\n".join(map(lambda t: t.export(), self._tasks))
    
    def _instructions(self):
        return ""
    
    def _export_instructions(self):
        """Return the HTML formatted instructions for this type of exercise."""
        return "<p>" + self._instructions() + "</p>"
    
    
class TrueFalseExercise(Exercise):
    """Exercise Comprising of a list of statements.

    This class overrides the constructor to provide a more comfortable way to
    specify this concrete type of exercise and to allow more detailed checking
    of this specification.
    
    """

    _task_type = TrueFalseStatement
    _name = "True/False Statements"
    
    def __init__(self, parent, tasks):
        """Initialize the instance.

        Arguments:
        
          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          tasks -- a tuple of (statement, flag) pairs.  Statement is the
            actual string and flag is a boolean value indicating whether the
            statement is true or not.

        """
        assert isinstance(tasks, types.TupleType), \
               "The 'tasks' argument must be a tuple: %s" % tasks
        for item in tasks:
            assert isinstance(item, types.TupleType) and len(item) == 2, \
                   "Each item of 'tasks' must be a pair (statement, flag)."
            statement, flag = item
            assert type(statement) == type(''), \
                   "First item of each (statement, flag) pair must be a string."
            assert type(flag) == type(True), \
                   "Second item of each (statement, flag) pair must be a " + \
                   "boolean value."
        tasks = map(lambda s: TrueFalseStatement(parent, s[0], correct=s[1]),
                   tasks)
        super(TrueFalseExercise, self).__init__(parent, tasks)
        
    def _instructions(self):
        return """A list of %d statements follows.  After each sentence,
        there are two links.  Select [TRUE] if you think the sentence is true,
        or select [FALSE] if you think it is false.""" % len(self._tasks)


class MultipleChoiceExercise(Exercise):
    """An Exercise with MultipleChoiceQuestion tasks."""
    
    _task_type = MultipleChoiceQuestion
    _name = "Multiple Choice Questions"
    
    def _instructions(self):
        return """Below is a list of %d questions.  For each question, choose
        from the list of possible answers, and choose the best one by pressing
        enter on it.""" % len(self._tasks)
    
    
class GapFillingExercise(Exercise):
    """An exercise composed of GapFillStatement tasks."""

    _task_type = GapFillStatement
    _name = "Gap Filling"

    def _instructions(self):
        return """Fill in the gaps in the following %d sentences using a word
        from the list.""" % len(self._tasks)

    
class ComprehensionExercise(Exercise):
    """This exercise is based on listenning to a recording."""

    _name = "Listening Comprehension"

    def __init__(self, parent, sound_file, transcript, tasks):
        """Initialize the instance.

        Arguments:
          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          sound_file -- name of the file with the actual recording (as string).
          transcript -- textual transcript of the recording.
          tasks -- sequence of 'Task' instances related to this exercise.
          
        """
        assert type(sound_file) == type('')
        assert type(transcript) == type('')
        self._sound_file = parent.media(sound_file)
        self._transcript = transcript
        super(ComprehensionExercise, self).__init__(parent, tasks)

    def _instructions(self):
        return "You will hear a short recording. " + \
               super(ComprehensionExercise, self)._instructions()
        
    def _export_instructions(self):
        return "<p>" + self._instructions() + "</p>\n\n<p>Recording: " + \
               '<a href="%s">[press to listen]</a>' % self._sound_file.url()



class MulitpleChoiceComprehensionExercise(ComprehensionExercise,
                                          MultipleChoiceExercise):
    """Comprehension exercise with multiple choice questions."""


class TrueFalseComprehensionExercise(ComprehensionExercise,
                                     TrueFalseExercise):
    """Comprehension exercise with true/false questions."""

class ClozeTest(Exercise):
    """Filling in gaps in text by typing the correct word."""

    _name = "Cloze Test"

    def __init__(self, parent, text):
        tasks = (Cloze(parent, text), )
        super(ClozeTest, self).__init__(parent, tasks)
        



