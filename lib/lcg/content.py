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
        super(Container, self).__init__(parent)
        self._parts = parts
        
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
        super(GenericText, self).__init__(parent)
        self._text = text

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
        super(VocabList, self).__init__(parent)
        assert is_sequence_of(items, VocabItem)
        self._items = items

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
        assert isinstance(translation, types.StringTypes)
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


class Choice(Record):
    """Answer text with an information whether it is correct or not.

    One of the choices for 'MultipleChoiceQuestion'.

    """
    
    def __init__(self, answer, correct=False):
        assert type(answer) == type('')
        assert type(correct) == type(True)
        self._answer = answer
        self._correct = correct

        
class Selection(Task):
    """Select the correct statement out of a list of predefined choices."""
    
    def __init__(self, parent, choices):
        """Initialize the instance.

        Arguments:
        
          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          choices -- sequence of 'Choice' instances related to this Task.
          
        """
        super(Selection, self).__init__(parent)
        assert is_sequence_of(choices, Choice)
        self._choices = choices
        self._response = {
            True: parent.media('correct-response.ogg', shared=True,
                               tts_input='correct'),
            False: parent.media('incorrect-response.ogg', shared=True,
                                tts_input='you are wrong!') }
        
    def _choice_controls(self):
        return map(lambda a: '<a href="%s">%s</a>' % \
                   (self._response[a.correct()].url(), a.answer()),
                   self._choices)

    def _export_choices(self):
        items = map(lambda a: "  <li>%s</li>" % a, self._choice_controls())
        return "\n".join(('<ol style="list-style-type: lower-latin;">',
                          "\n".join(items), "</ol>"))
        
    def export(self):
        return self._export_choices()


class MultipleChoiceQuestion(Selection):
    """Answer a question by selecting from a list of predefined choices."""
    
    def __init__(self, parent, question, choices):
        """Initialize the instance.

        Arguments:
        
          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          question --  exercise within the containing section.
          choices -- sequence of 'Choice' instances related to this Task.
          
        """
        super(MultipleChoiceQuestion, self).__init__(parent, choices)
        assert type(question) == type('')
        self._question = question

    def export(self):
        return "<p>%s</p>\n%s" % (self._question, self._export_choices())

        
        
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
        
    def _export_choices(self):
        return "\n".join(map(lambda a: "[%s]" % a, self._choice_controls()))

    def export(self):
        return "<p>%s\n%s</p>\n" % (self._question, self._export_choices())
    

class GapFillStatement(MultipleChoiceQuestion):
    """The goal is to select the correct word to complete the sentence."""


class ClozeTask(Task):

    _REGEXP = re.compile(r"\[([^\]]+)\]")
    
    def __init__(self, parent, text):
        super(ClozeTask, self).__init__(parent)
        assert type(text) == type('')
        self._text = text

    def answers(self):
        return self._REGEXP.findall(self._text)
    
    def _make_field(self, match):
        return '<input class="cloze" type="text" size="%d">' % \
               (len(match.group(1))+1)
    
    def _export_text(self):
        return self._REGEXP.sub(self._make_field, self._text)

    def export(self):
        return "\n".join(('<p>', self._export_text(), '</p>'))
               
class TransformationTask(ClozeTask):

    def __init__(self, parent, orig, transformed):
        super(TransformationTask, self).__init__(parent, transformed)
        assert type(orig) == type('')
        self._orig = orig

    def export(self):
        return "\n".join(('<p>',self._orig,'<br/>', self._export_text(),'</p>'))

    
################################################################################
################################   Exercises   #################################
################################################################################

    
class Exercise(Content):
    """Exercise consists of an assignment and a set of tasks."""

    _task_type = Task
    _name = None
    
    def __init__(self, parent, tasks, sound_file=None, transcript=None):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          tasks -- sequence of 'Task' instances related to this exercise.
          sound_file -- name of the file with a recording (string).  Some
            exercises may not include a recording, so this argument is not
            mandatory.  When specified, the 'transcript' arguemnt below must be
            also given.
          transcript -- name of the file with a textual transcript of the
            recording (string).  This argument is mandatory when the
            'sound_file' arguemnt is specified (and not None).
          
        """
        super(Exercise, self).__init__(parent)
        assert is_sequence_of(tasks, self._task_type), \
               "Tasks must be a sequence of '%s' instances!: %s" % \
               (self._task_type.__name__, tasks)
        assert sound_file is None or type(sound_file) == type('')
        self._number = parent.counter().next()
        self._tasks = tasks
        if sound_file is not None:
            assert transcript is not None, \
                   "Transcript file not specified for file: %s" % sound_file
            assert type(transcript) == type('')
            tts_filename = os.path.join(parent.src_dir(), transcript)
            assert os.path.exists(tts_filename), \
                   "Transcript file not found: %s" % tts_filename
            tts_input = ''.join(open(tts_filename).readlines())
            self._recording = parent.media(sound_file, tts_input=tts_input)
        else:
            self._recording = None
        self._transcript = transcript
        parent.script('audio.js')

    def task_type(self):
        return self._task_type

    task_type = classmethod(task_type)
    
    def export(self):
        return "\n\n".join((self._header(),
                            self._export_instructions(),
                            self._export_tasks()))
    def _export_tasks(self):
        return "\n".join(map(lambda t: t.export(), self._tasks))
    
    def _header(self):
        name = self._name or re.sub('([^^])([A-Z])', '\\1 \\2',
                                    self.__class__.__name__)
        return "<h3>Exercise %d &ndash; %s</h3>" % (self._number, name)

    
    def _instructions(self):
        return ""

    def _export_instructions(self):
        """Return the HTML formatted instructions for this type of exercise."""
        result = "<p>" + self._instructions() + "</p>"
        if self._recording is not None:
            result += '\n\n<form action="">Recording: ' + \
                      '<input type="button" value="Play"' + \
                      ' onclick="play_audio(\'%s\')"> ' % \
                      self._recording.url() + \
                      '<input type="button" value="Stop"' + \
                      ' onclick="stop_audio()">' + \
                      '</form>'

        return result


class Cloze(Exercise):
    """Filling in gaps in text by typing the correct word."""

    _task_type = ClozeTask

    def __init__(self, parent, *args, **kwargs):
        super(Cloze, self).__init__(parent, *args, **kwargs),
        parent.script('eval-cloze.js')
        parent.media('all-correct-response.ogg', shared=True,
                     tts_input='everything correct!')
        parent.media('all-wrong-response.ogg', shared=True,
                     tts_input='all the answers are wrong!')
        parent.media('some-wrong-response.ogg', shared=True,
                     tts_input='some of the answers are wrong!')

    def _instructions(self):
        
        if self._recording is None:
            return """You will hear a short recording.  Listen carefully and
            then fill in the gaps in the text below using the same words.
            After filling all the gaps, check your results using the buttons
            below the text."""
        else:
            return """Fill in the gaps in the text below using the a suitable
            word.  After filling all the gaps, check your results using the
            buttons below the text.  Sometimes there might be more correct
            answers, but the evaluation only recognizes one.  Contact the tutor
            when in doubt."""
        
    def _export_tasks(self):
        form_name = "cloze_%s" % id(self)
        answers = map(lambda a: a.replace("'", "\\'"),
                      reduce(lambda a, b: a + b,
                             map(lambda t: t.answers(), self._tasks)))
        button = '<input type="button" value="%s"' + \
                 ' onClick="%s(document.forms[\'%s\'], [\'%s\'])">'
        b1 = button % ('Evaluate', 'eval_cloze', form_name, "','".join(answers))
        b2 = button % ('Fill', 'fill_cloze', form_name, "','".join(answers))
        result = 'Result: <input class="cloze-result" name="result"' + \
                 ' type="text" size="70" value="%s" readonly>' % \
                 'Use the Evaluate button to see the result.'
        return "\n".join(('<form name="%s" action="">' % form_name,
                          super(Cloze, self)._export_tasks(),
                          b1, b2, '<input type="reset" value="Reset">',
                          result,
                          '</form>'))

    
class TrueFalseStatements(Exercise):
    """Exercise Comprising of a list of statements.

    This class overrides the constructor to provide a more comfortable way to
    specify this concrete type of exercise and to allow more detailed checking
    of this specification.
    
    """

    _task_type = TrueFalseStatement
    _name = "True/False Statements"
    
    def _instructions(self):
        return """A list of %d statements follows.  After each sentence,
        there are two links.  Select [TRUE] if you think the sentence is true,
        or select [FALSE] if you think it is false.""" % len(self._tasks)

    
class MultipleChoiceQuestions(Exercise):
    """An Exercise with MultipleChoiceQuestion tasks."""
    
    _task_type = MultipleChoiceQuestion
    
    def _instructions(self):
        return """Below is a list of %d questions.  For each question choose
        from the list of possible answers and check your choice by activating
        the link.""" % len(self._tasks)

    
class Selections(Exercise):
    """An Exercise with Selection tasks."""
    
    _task_type = Selection
    _name = "Select the Correct One"
    
    def _instructions(self):
        return """For each of the %d pairs of statements, decide which one is
        correct.  Activate the link to check the result.""" % len(self._tasks)

    
class GapFilling(Exercise):
    """An exercise composed of GapFillStatement tasks."""

    _task_type = GapFillStatement

    def _instructions(self):
        return """Select a word from the list below each sentence to fill in
        the gap.  Activate the link made by the word to check the result."""

    
class SentenceCompletion(Cloze):
    """Filling in gaps in sentences by typing in the correct completion."""

    def _instructions(self):
        return """You will hear a recording comprising %d sentences.  Below,
        you will find the same sentences unfinished.  Fill in the missing text
        and check your results using the buttons below all the sentences.""" % \
        len(self._tasks)

        
class Transformation(Cloze):
    """Transform a whole sentence and write it down."""

    _task_type = TransformationTask

    def _instructions(self):
        return """Listen to the recording and transform each of the %d
        sentences below according to the instructions.  Check your results
        using the buttons below all the sentences.""" % len(self._tasks)

    
class Dictation(Cloze):
    
    def _instructions(self):
        return """This exercise type is not yet implemented..."""
    
   
    
