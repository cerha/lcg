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

"""Course content abstraction.

This module provides classes for representation of content elements in an
abstract container capable of HTML export.

"""

import string
import wiki
import re
import types
import unicodedata

from util import *
from course import *
from _html import *

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
        rows = ['<tr><td>%s %s</td><td>%s</td></tr>' % \
                (speaking_text(i.word(), i.media()), i.note(), i.translation())
                for i in self._items]
        return '<table>\n' + '\n'.join(rows) + "\n</table>\n"

    
class VocabItem(Record):
    """One item of vocabulary listing."""
    _DIACRITICS_MATCHER = re.compile(r" WITH .*")
    _DANGER_CHAR_MATCHER = re.compile(r"[^a-zA-Z0-9-]")
    
    def __init__(self, parent, word, note, translation):
        """Initialize the instance.
        
        Arguments:
          word -- The actual piece of vocabulary as a string
          note -- Notes in parens as a string.  Can contain multiple notes
            in parens separated by spaces.  Typical notes are for example
            (v) for verb etc.
          translation -- the translation of the word into target language.
        
        """
        def safe_char(match):
            char = match.group(0)
            if char in ('.', ',', '?', '!', ':', ';', '(', ')'):
                return ''
            base_name = self._DIACRITICS_MATCHER.sub('', unicodedata.name(char))
            base_char = unicodedata.lookup(base_name)
            if self._DANGER_CHAR_MATCHER.match(base_char):
                return '-'
            return base_char
        assert isinstance(word, types.UnicodeType)
        assert isinstance(note, types.UnicodeType)
        assert isinstance(translation, types.UnicodeType)
        self._word = word
        self._note = note
        self._translation = translation
        name = self._DANGER_CHAR_MATCHER.sub(safe_char, word.replace(' ', '-'))
        filename = os.path.join('vocabulary', name + '.ogg')
        self._media = parent.resource(Media, filename, tts_input=word)


    def word(self):
        return self._word
    
    def translation(self):
        return self._translation
    
################################################################################
################################     Tasks     #################################
################################################################################

class Task(object):
    """This class an abstract base class for various concrete tasks.

    A set of concrete tasks is a part of each 'Exercise'.

    """
    pass


class Choice(Record):
    """Answer text with an information whether it is correct or not.

    One of the choices for 'MultipleChoiceQuestion'.

    """
    
    def __init__(self, answer, correct=False):
        assert isinstance(answer, types.UnicodeType)
        assert isinstance(correct, types.BooleanType)
        self._answer = answer
        self._correct = correct

        
class _ChoiceTask(Task):
    """Select the correct statement out of a list of predefined choices."""
    
    def __init__(self, prompt, choices):
        """Initialize the instance.

        Arguments:
        
          choices -- sequence of 'Choice' instances related to this Task.
          
        """
        super(_ChoiceTask, self).__init__()
        assert isinstance(prompt, types.StringTypes)
        assert is_sequence_of(choices, Choice)
        self._prompt = prompt
        self._choices = list(choices)

    def prompt(self):
        return self._prompt
    
    def choices(self):
        return self._choices

    def choice_index(self, choice):
        return self._choices.index(choice)
        
        
class MultipleChoiceQuestion(_ChoiceTask):
    pass


class Selection(_ChoiceTask):
    
    def __init__(self, choices):
        super(Selection, self).__init__('', choices)

        
class GapFillStatement(_ChoiceTask):
    pass


class TrueFalseStatement(_ChoiceTask):
    """The goal is to indicate whether the statement is true or false."""
    
    def __init__(self, statement, correct=True):
        """Initialize the instance.

        Arguments:
        
          statement --  exercise within the containing section.
          correct -- boolean flag indicating whether the statement is correct
            or not (true when it is correct).
          
        """
        assert isinstance(correct, types.BooleanType)
        choices = (Choice(_('TRUE'), correct), Choice(_('FALSE'), not correct))
        super(TrueFalseStatement, self).__init__(statement, choices)


class ClozeTask(Task):

    _REGEXP = re.compile(r"\[([^\]]+)\]")
    
    def __init__(self, text):
        super(ClozeTask, self).__init__()
        assert isinstance(text, types.UnicodeType)
        self._text = text

    def answers(self):
        return self._REGEXP.findall(self._text)

    def text(self, field_formatter):
        return self._REGEXP.sub(field_formatter, self._text)

    
class TransformationTask(ClozeTask):

    def __init__(self, orig, transformed):
        super(TransformationTask, self).__init__(transformed)
        assert isinstance(orig, types.UnicodeType)
        self._orig = orig

    def orig(self):
        return self._orig

    
################################################################################
################################   Exercises   #################################
################################################################################

    
class Exercise(Content):
    """Exercise consists of an assignment and a set of tasks."""

    _TASK_TYPE = Task
    _NAME = None
    
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
        assert is_sequence_of(tasks, self._TASK_TYPE), \
               "Tasks must be a sequence of '%s' instances!: %s" % \
               (self._TASK_TYPE.__name__, tasks)
        assert sound_file is None or isinstance(sound_file, types.StringTypes)
        self._number = parent.counter().next()
        self._tasks = list(tasks)
        if sound_file is not None:
            if transcript is None:
                transcript = os.path.splitext(sound_file)[0] + '.txt'
            assert isinstance(transcript, types.StringTypes)
            self._recording = parent.resource(Media, sound_file)
            self._transcript = parent.resource(Transcript, transcript)
        else:
            self._recording = None
            self._transcript = None
        parent.resource(Script, 'audio.js')
        parent.resource(Script, 'exercises.js')

    def task_type(self):
        return self._TASK_TYPE
    task_type = classmethod(task_type)

    def export(self):
        return "\n\n".join((self._header(),
                            self._export_instructions(),
                            '<form name="%s" action="">' % self._form_name(),
                            "\n".join(map(self._export_task, self._tasks)),
                            self._results(),
                            '</form>',
                            script(self._init_script())))
    
    def _form_name(self):
        return "exercise_%s" % id(self)
    
    def _form(self):
        return "document.forms['%s']" % self._form_name()
    
    def _header(self):
        return "<h3>%s %d &ndash; %s</h3>" % (_("Exercise"), self._number,
                                              self._NAME)
    
    def _instructions(self):
        return ""

    def _export_instructions(self):
        """Return the HTML formatted instructions for this type of exercise."""
        result = "<p>" + self._instructions() + "</p>"
        if self._recording is not None:
            f = ('<form class="sound-control" action="">%s:' % _("Recording"),
                 button(_("Play"), "play_audio('%s')" % self._recording.url()),
                 button(_("Stop"), 'stop_audio()'),
                 link(_("show transcript"), self._transcript.url(),
                      target="transcript", brackets=True),
                 '</form>')
            a = '<p>' + _("Recording") + ': ' + \
                link(_("Play"), self._recording.url(), brackets=True) + '</p>'
            result += '\n\n'+ script_write('\n'.join(f), a)
        return result

    def _init_script(self):
        return ''
        
    def _export_task(self, task):
        raise "This Method must be overriden"


class Cloze(Exercise):
    """Filling in gaps in text by typing the correct word."""

    _TASK_TYPE = ClozeTask
    _NAME = _("Cloze")

    
    def __init__(self, parent, *args, **kwargs):
        super(Cloze, self).__init__(parent, *args, **kwargs),
        parent.resource(Media, 'all-correct-response.ogg', shared=True,
                        tts_input='everything correct!')
        parent.resource(Media, 'all-wrong-response.ogg', shared=True,
                        tts_input='all the answers are wrong!')
        parent.resource(Media, 'some-wrong-response.ogg', shared=True,
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

    def _init_script(self):
        answers = ",".join(map(lambda a: "'%s'" % a.replace("'", "\\'"),
                               reduce(lambda a, b: a + b,
                                      map(lambda t: t.answers(), self._tasks))))
        return "init_cloze_form(%s, [%s])" % (self._form(), answers)

    def _results(self):
        r = ('<p class="results">Results: ', 
             field('Use the Evaluate button to see the results.',
                   name='result', size=70, readonly=True), '<br/>',
             button('Evaluate', "eval_cloze(%s)" % self._form()),
             button('Fill', "fill_cloze(%s)" % self._form()),
             '<input type="reset" value="Reset">',
             '</p>')
        return script_write("\n".join(r))

    def _make_field(self, match):
        return field(cls='cloze', size=len(match.group(1))+1)
    
    def _export_task(self, task):
        return "\n".join(('<p>', task.text(self._make_field), '</p>'))
    

class _ChoiceBasedExercise(Exercise):

    _TASK_FORMAT = '<p>%s\n<div class="choices">\n%s\n</div></p>\n'

    def _answer_control(self, task, text, correct):
        self._parent.resource(Script, 'audio.js')
        if correct: 
            media = self._parent.resource(Media, 'correct-response.ogg',
                                          shared=True,
                                          tts_input=_('Correct'))
        else:
            media = self._parent.resource(Media, 'incorrect-response.ogg',
                                          shared=True,
                                          tts_input=_('You are wrong!'))
        handler = "eval_choice(%s, %d, %d, %d, '%s')" % \
                  (self._form(), self._tasks.index(task), len(self._tasks),
                   correct and 1 or 0, media.url())
        b = button(text, handler, cls='answer-control')
        a = link(text, media.url())
        return script_write(b, a)
    
    def _results(self):
        r = '<p class="results">Answered: %s<br/>\nCorrect: %s %s</p>' % \
            (field(name='answered', size=5, readonly=True),
             field(name='result', size=8, readonly=True),
             button('Reset', "reset_choices(%s, %d)" % \
                    (self._form(), len(self._tasks))))
        return script_write(r, '')

    def _format_choice(self, task, choice):
        a = chr(ord('a') + task.choice_index(choice)) + ')'
        ctrl = self._answer_control(task, a, choice.correct())
        return '&nbsp;' + ctrl + '&nbsp;' + choice.answer() + '<br/>'
        
    def _export_task(self, task):
        choices = "\n".join(map(lambda ch: self._format_choice(task, ch),
                                task.choices()))
        return self._TASK_FORMAT % (task.prompt(), choices)
        
    
class TrueFalseStatements(_ChoiceBasedExercise):
    """Exercise Comprising of a list of statements.

    This class overrides the constructor to provide a more comfortable way to
    specify this concrete type of exercise and to allow more detailed checking
    of this specification.
    
    """

    _TASK_TYPE = TrueFalseStatement
    _NAME = _("True/False Statements")
    _TASK_FORMAT = "<p>%s\n%s</p>\n"
    
    def _instructions(self):
        return """A list of %d statements follows.  After each sentence,
        there are two links.  Select 'TRUE' if you think the sentence is true,
        or select 'FALSE' if you think it is false.""" % len(self._tasks)

    def _format_choice(self, task, choice):
        return self._answer_control(task, choice.answer(), choice.correct())
    
    
class MultipleChoiceQuestions(_ChoiceBasedExercise):
    """An Exercise with MultipleChoiceQuestion tasks."""
    
    _TASK_TYPE = MultipleChoiceQuestion
    _NAME = _("Multiple Choice Questions")
    
    def _instructions(self):
        return """Below is a list of %d questions.  For each question choose
        from the list of possible answers and check your choice by activating
        the link.""" % len(self._tasks)

    
class Selections(_ChoiceBasedExercise):
    """An Exercise with Selection tasks."""
    
    _TASK_TYPE = Selection
    _NAME = _("Select the Correct One")
    
    def _instructions(self):
        return """For each of the %d pairs of statements, decide which one is
        correct.  Activate the link to check the result.""" % len(self._tasks)

    
class GapFilling(_ChoiceBasedExercise):
    """An exercise composed of GapFillStatement tasks."""

    _TASK_TYPE = GapFillStatement
    _NAME = _("Gap Filling")

    def _instructions(self):
        return """Select a word from the list below each sentence to fill in
        the gap.  Activate the link made by the word to check the result."""

    
class VocabExercise(Cloze):
    _NAME = _("Vocabulary from English")

    def __init__(self, parent, items, *args, **kwargs):
        kwargs['tasks'] = [self._create_task(item) for item in items]
        super(Cloze, self).__init__(parent, *args, **kwargs),

    def _create_task(self, item):
        return ClozeTask("%s: [%s]" % (item.word(), item.translation()))

    def _instructions(self):
        return _("""Listen to the expression in English and repeat. You will
        hear a transltion into your language.""")
    
    def _export_task(self, task):
        return task.text(self._make_field)+'<br/>'

    
class VocabExercise2(VocabExercise):
    _NAME = _("Vocabulary to English")

    def _create_task(self, item):
        return ClozeTask("%s: [%s]" % (item.translation(), item.word()))

    def _instructions(self):
        return _("""You will hear each item in your language.  Say the word or
        expression in English and listen to the model pronunciation, then type
        the word into the box.""")

    
class SentenceCompletion(Cloze):
    """Filling in gaps in sentences by typing in the correct completion."""

    _NAME = _("Sentence Completion")

    def _instructions(self):
        return """You will hear a recording comprising %d sentences.  Below,
        you will find the same sentences unfinished.  Fill in the missing text
        and check your results using the buttons below all the sentences.""" % \
        len(self._tasks)

        
class Transformation(Cloze):
    """Transform a whole sentence and write it down."""

    _TASK_TYPE = TransformationTask
    _NAME = _("Transformation")

    def _instructions(self):
        return """Listen to the recording and transform each of the %d
        sentences below according to the instructions.  Check your results
        using the buttons below all the sentences.""" % len(self._tasks)

    def _export_task(self, task):
        return "\n".join(('<p>',
                          task.orig(), '<br/>',
                          task.text(self._make_field),
                          '</p>'))


class Dictation(Cloze):
    
    def _instructions(self):
        return """This exercise type is not yet implemented..."""
