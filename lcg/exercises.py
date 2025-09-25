# -*- coding: utf-8 -*-

# Copyright (C) 2004-2015 OUI Technology Ltd.
# Copyright (C) 2019-2024 Tomáš Cerha <t.cerha@gmail.com>
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

"""Exercises within a learning material as specific LCG Content elements.

This module provides classes for representation of various types of exercises
which can be used within the LCG content tree.

The first part of this module contains the definition of various kinds of
tasks, which make the actual content of exercises (the interactive questions,
fill-in boxes etc).  Each exercise type is a set of several (or no) tasks of
the same kind.

The exercise type determines the type of contained tasks (still, one task type
can be used in differnt exercise types).  Finally, the exercise type determines
the way its tasks are represented on the output.

This module originally comes from the Eurochance project.  It was modified to
allow using interactive exercises within any LCG content.  Some functionality
present in the code may still not be fully supported.

"""

from __future__ import unicode_literals
from builtins import map

import sys
import lcg
import re

_ = lcg.TranslatableTextFactory('lcg-exercises')

unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


################################################################################
################################     Tasks     #################################
################################################################################


class Task(object):
    """Abstract base class of all task types.

    Tasks are not the 'Content' instances.  They are not able to render
    themselves.  They just hold the data.

    """

    def __init__(self, prompt, comment=None, media=None):
        assert isinstance(prompt, lcg.Content) or prompt is None, prompt
        assert isinstance(comment, basestring) or comment is None, comment
        if media is None:
            media = ()
        elif isinstance(media, lcg.Media):
            media = (media,)
        else:
            assert all([isinstance(m, lcg.Media) for m in media])
        self._comment = comment
        self._prompt = prompt
        self._media = media

    def prompt(self):
        return self._prompt

    def comment(self):
        return self._comment

    def media(self):
        return self._media


class TextTask(Task):
    """Tasks, where the answer is a piece of text.

    The answer is typically filled into a text box.  The task may either
    contain explicit text boxes marked by square brackets (the brackets contain
    the correct answer for the text box) or if the text doesn't contain such
    boxes, the whole text is the answer.

    See TODO in ContentTask docstring for possible future changes.

    """
    _FIELD_MATCHER = re.compile(r"([\w\d.,;?!/%$@=*+-]*)"
                                r"\[([^\]]*?)(?:\<([\w\d]+)\>)?\]"
                                r"([\w\d.,;?!/%$@=*+-]*)",
                                flags=re.UNICODE)
    _NEWLINE_MATCHER = re.compile(r"\r?\n")

    def __init__(self, prompt, text, **kwargs):
        super(TextTask, self).__init__(prompt, **kwargs)
        assert isinstance(text, basestring)
        self._text = self._NEWLINE_MATCHER.sub(' ', text)

    def text(self):
        """Return the task answer text as is."""
        return self._text

    def answers(self):
        """Return all answers from all fields found within the task text.

        Returns the whole task text if it doesn't contain explicitly marked
        text fields (the wole text is the answer in this case).

        """
        answers = [answer for word_start, answer, label, word_end
                   in self._FIELD_MATCHER.findall(self._text)]
        if not answers:
            # The whole text is the answer when there is no explicit text box.
            answers = (self._text,)
        return answers

    def has_fields_in_text(self):
        """Return true iff the task text contains explicitly marked text boxes."""
        return self._FIELD_MATCHER.search(self._text) is not None

    def substitute_fields(self, text, make_field):
        """Substitute text boxes within task text.

        Arguments:

          text - the text to be substituted containing textbox markup (answers
            in square brackets).  This is usually the task text as returned by
            'text()', but various export formats may require various
            preprocessing, so the text si passed as argument.

          make_field -- function of four arguments: 'answer', 'label',
            'word_start' and 'word_end', where 'answer' is the correct answer
            for the field (text inside the square brackets without label),
            'label' is the field label if the markup contains it (after a colon
            inside the square brackets) 'word_start' is any text immediately
            preceeding the field and 'word_end' is any text immediately
            following the field.  They are not empty if the field adjoins text
            without interleaving whitespace.  They are processed together with
            the field because it might be appropriate in certain output formats
            to mark these parts together (for example to avoid word wrapping on
            field boundary).  They are empty strings if the field doesn't
            adjoin text immediately.  The function must return the field
            representation for given output format as a string to be
            substituted within 'text'.

        Returns the 'text' with all fields replaced by the results returned by
        'make_field()'.

        """
        def subst(match):
            word_start, answer, label, word_end = match.groups()
            return make_field(answer, label, word_start, word_end)
        return self._FIELD_MATCHER.sub(subst, text)


class ContentTask(Task):
    """Tasks, where the answer is LCG Content.

    This task type is currently used just for hidden answers, where the answer
    itself has no interactivity.

    TODO: It would make sense to use this task type also for cloze and similar
    exercises.  Fill-in boxes would be LCG elements and we wouldn't need to
    parse the answer text during export.

    """

    def __init__(self, prompt, answer, **kwargs):
        super(ContentTask, self).__init__(prompt, **kwargs)
        assert isinstance(answer, lcg.Content)
        self._answer = answer

    def answer(self):
        return self._answer


class Choice(object):
    """Representation of one choice for 'ChoiceTask'.

    This is the answer text with an information whether it is correct or not.

    """

    def __init__(self, answer, correct=False):
        assert isinstance(answer, basestring), answer
        assert correct is None or isinstance(correct, bool), correct
        self._answer = answer
        self._correct = correct

    def __repr__(self):
        return '<choice correct={} answer="{}">'.format(self._correct, self._answer)

    def answer(self):
        return self._answer

    def correct(self):
        return self._correct


class ChoiceTask(Task):
    """Abstract base class for all choice-based tasks."""

    def __init__(self, prompt, choices, **kwargs):
        """Initialize the instance.

        Arguments:

          choices -- sequence of 'Choice' instances related to this Task.

        """
        assert all(isinstance(choice, Choice) for choice in choices), choices
        self._choices = list(choices)
        if all(ch.correct() is None for ch in choices):
            self._correct_choice = None
        else:
            correct = [choice for choice in choices if choice.correct()]
            assert len(correct) == 1 and not any(ch.correct() is None for ch in choices)
            self._correct_choice = correct[0]
        super(ChoiceTask, self).__init__(prompt, **kwargs)

    def choices(self):
        return self._choices

    def correct_choice(self):
        return self._correct_choice

    def choice_index(self, choice):
        return self._choices.index(choice)


class TrueFalseTask(ChoiceTask):

    def __init__(self, statement, correct=True, **kwargs):
        """Initialize the instance.

        Arguments:

          statement -- exercise within the containing section.
          correct -- boolean flag indicating whether the statement is correct
            or not (true when it is correct).

        """
        assert isinstance(correct, bool)
        # Translators: Labels for exercise buttons. Keep in capitals.
        choices = (Choice(_('TRUE'), correct), Choice(_('FALSE'), not correct))
        super(TrueFalseTask, self).__init__(statement, choices, **kwargs)


class ExerciseParser(object):
    """Turns a textual exercise spec. into an 'Exercise' instance.

    This is an intermediate solution to use the old text based exercise
    specifications known from the Eurochance project to define exercises within
    the LCG HTML source code (processed by 'lcg.HTMLProcessor').

    """
    class ExerciseParserError(Exception):
        """Exception raised when exercise parsing fails due to invalid input data."""

        def __init__(self, message, task_number=None):
            self._message = message
            self._task_number = task_number

        def message(self):
            return self._message

        def task_number(self):
            return self._task_number

    _BLANK_LINE_SPLITTER = re.compile(r"\r?\n\s*\r?\n")
    _GAP_MATCHER = re.compile(r"(___+)")

    def __init__(self):
        self._parser = lcg.Parser()

    def _error(self, *args, **kwargs):
        raise self.ExerciseParserError(*args, **kwargs)

    def _parse_text(self, text):
        return self._parser.parse_inline_markup(text.strip())

    def _single_text_box_task(self, prompt, text, **kwargs):
        task = TextTask(prompt, text.strip(), **kwargs)
        if len(task.answers()) != 1:
            self._error(_("Just one text box per task allowed, but %d found.", len(task.answers())))
        return task

    def _split(self, text):
        return [piece.strip() for piece in self._BLANK_LINE_SPLITTER.split(text)]

    def _process_choices(self, lines):
        def choice(text):
            if text.startswith('+ '):
                correct = True
            elif text.startswith('- '):
                correct = False
            elif text.startswith('? '):
                correct = None
            else:
                self._error(_("All choices must start with +/-/? sign and a space."))
            return Choice(text[2:].strip(), correct=correct)
        if not lines:
            self._error(_("No choices defined."))
        choices = list(map(choice, lines))
        correct_choices = [ch for ch in choices if ch.correct()]
        unknown_choices = [ch.correct() is None for ch in choices]
        if len(correct_choices) == 1 and not any(unknown_choices) or all(unknown_choices):
            pass
        elif len(correct_choices) > 1:
            self._error(_("More than one choice is marked as correct."))
        elif any(unknown_choices):
            self._error(_("All or none choices must be marked as unknown."))
        else:
            self._error(_("None of the choices is marked as correct."))
        return choices

    def _read_numbered_cloze_task(self, text, comment):
        return self._single_text_box_task(None, text, comment=comment)

    def _read_cloze_task(self, text, comment):
        # Cloze comments unsupported for now.
        #comments = ()
        #cstart = text.find("\n.. ") + 1
        # if cstart != 0:
        #    src_comments = [c[3:] for c in self._split(text[cstart:])]
        #    text = text[0:cstart].rstrip()
        #    if src_comments:
        #        cdict = {}
        #        fields = []
        #        for c in src_comments:
        #            match = re.search("^<(?P<label>[\w\d]+)>\s*", c)
        #            assert match, ('Cloze comments must begin with a label ' +
        #                           '(e.g. <1> to refer to a field [xxx<1>]).', c)
        #            cdict[match.group('label')] = c[match.end():]
        #        def _comment(cdict, label):
        #            try:
        #                c = cdict[label]
        #                del cdict[label]
        #                return c
        #            except KeyError:
        #                return None
        #        comments = [_comment(cdict, label) for a, label in fields]
        #        assert not cdict,
        #            "Unused comments (labels don't match any field label): %s" % cdict
        return TextTask(None, text)

    def _read_multiple_choice_task(self, text, comment):
        lines = text.splitlines()
        return ChoiceTask(self._parse_text(lines[0]),
                          self._process_choices(lines[1:]), comment=comment)

    def _read_gap_filling_task(self, text, comment):
        lines = text.splitlines()
        if len(self._GAP_MATCHER.findall(lines[0])) != 1:
            self._error(_("Gap mark (three or more underscores) not found statement."))
        prompt = self._GAP_MATCHER.sub(r'\____', lines[0])
        choices = self._process_choices(lines[1:])
        return ChoiceTask(self._parse_text(prompt), choices, comment=comment)

    def _read_selections_task(self, text, comment):
        return ChoiceTask(None, self._process_choices(text.splitlines()), comment=comment)

    def _split_pair_of_statements(self, text):
        lines = text.splitlines()
        if len(lines) != 2:
            self._error(_("Task specification must consist of 2 lines (%d given).", len(lines)))
        return [l.strip() for l in lines]

    def _read_written_answers_task(self, text, comment):
        prompt, answer = self._split_pair_of_statements(text)
        return self._single_text_box_task(self._parse_text(prompt), answer, comment=comment)

    def _read_vocab_exercise_task(self, text, comment):
        prompt, answer = text.split(':', 1)
        return self._single_text_box_task(self._parse_text(prompt), answer, comment=comment)

    def _read_hidden_answers_task(self, text, comment):
        prompt, answer = self._split_pair_of_statements(text)
        return ContentTask(self._parse_text(prompt), self._parse_text(answer), comment=comment)

    def _read_true_false_statements_task(self, text, comment):
        text = text.strip()
        correct = text.endswith('[T]')
        if not correct and not text.endswith('[F]'):
            # Translators: Error message. Don't translate [T] and [F].
            # They mean True and False but don't change with localization.
            self._error(_("A true/false statement must end with '[T]' or '[F]'."))
        text = ' '.join([line.strip() for line in text.splitlines()])[:-3].strip()
        return TrueFalseTask(self._parse_text(text), correct=correct, comment=comment)

    def parse(self, exercise_type, src, **kwargs):
        """Convert textual exercise specification into an Exercise instance.

        Returns 'lcg.Exercise' instance on success or 'lcg.Container' instance
        with error information if the exercise specification is invalid.

        """
        try:
            try:
                read_task = {
                    MultipleChoiceQuestions: self._read_multiple_choice_task,
                    GapFilling: self._read_gap_filling_task,
                    Selections: self._read_selections_task,
                    TrueFalseStatements: self._read_true_false_statements_task,
                    HiddenAnswers: self._read_hidden_answers_task,
                    WrittenAnswers: self._read_written_answers_task,
                    VocabExercise: self._read_vocab_exercise_task,
                    NumberedCloze: self._read_numbered_cloze_task,
                    Cloze: self._read_cloze_task,
                    ModelCloze: self._read_cloze_task,
                }[exercise_type]
            except KeyError:
                self._error(_("Unknown exercise type: %s", exercise_type))
            tasks = []
            try:
                if src:
                    assert 'template' not in kwargs
                    if issubclass(exercise_type, Cloze):
                        pieces = (src,)
                    else:
                        pieces = self._split(src)
                    i = 0
                    while i < len(pieces):
                        t = pieces[i]
                        if i + 1 < len(pieces) and pieces[i + 1].startswith('.. '):
                            comment = pieces[i + 1][3:]
                            i += 2
                        else:
                            comment = None
                            i += 1
                        tasks.append(read_task(t, comment))
                elif 'template' in kwargs:
                    def maketask(match):
                        tasks.append(read_task(match.group(1), None))
                        return "%s"
                    m = self._TEMPLATE_TASK_MATCHER
                    kwargs['template'] = m.sub(maketask, kwargs['template'].replace('%', '%%'))
            except self.ExerciseParserError as e:
                self._error(e.message(), task_number=len(tasks) + 1)
        except self.ExerciseParserError as e:
            if e.task_number() is not None:
                message = _("Error in task %d: %s", e.task_number(), e.message())
            else:
                message = _("Error: %s", e.message())
            return lcg.Container((lcg.p(message, name='error-message'),
                                  lcg.PreformattedText(src)),
                                 name='exercise-specification-error')
        return exercise_type(tasks, **kwargs)


################################################################################
################################   Exercises   #################################
################################################################################


class Exercise(lcg.Content):
    """Exercise consists of an assignment and a set of tasks."""

    _TASK_TYPE = None
    _NAME = None
    _HELP_INTRO = ()
    _SOURCE_FORMATTING = ()
    _SOURCE_EXAMPLE = None

    _used_types = []
    _help = None

    def __init__(self, tasks=(), instructions=None, template=None, points=None):
        """Initialize the instance.

        Arguments:

          tasks -- sequence of 'Task' instances related to this exercise.
          instructions -- Instructions for the exercise as 'lcg.Content'
            instance.  Given content will appear before the exercise tasks.
          template -- the tasks are rendered as a simple sequence on the
            output.  If you need something more sophisticated (e.g. have text
            and the tasks 'mixed' within it), you can use a template.  Just
            specify any stuctured text and use '%s' placehodlers to be replaced
            by the actual tasks.  Note that you must have exactly the same
            number of the placeholders within the template as the number of
            tasks you pass as the `tasks' arguemnt.  You must also double any
            '%' signs, which are not a part of a placeholder.
        """
        super(Exercise, self).__init__()
        if self.__class__ not in Exercise._used_types:
            Exercise._used_types.append(self.__class__)
        assert instructions is None or isinstance(instructions, lcg.Content), instructions
        self._check_tasks(tasks)
        self._tasks = tuple(tasks)
        self._instructions = instructions
        self._template = template

    # Class methods

    @classmethod
    def name(cls):
        return cls._NAME

    @classmethod
    def used_types(cls):
        return cls._used_types

    @classmethod
    def help(cls):
        return lcg.Container([lcg.p(p) for p in cls._HELP_INTRO])

    @classmethod
    def authoring(cls):
        content = [lcg.p(p) for p in cls._HELP_INTRO]
        if cls._SOURCE_FORMATTING:
            content.append(lcg.Section(title=_("Exercise Definition"),
                                       content=[lcg.p(p) for p in cls._SOURCE_FORMATTING]))
        if cls._SOURCE_EXAMPLE:
            content.append(lcg.Section(title=_("Definition Example"),
                                       content=lcg.pre(cls._SOURCE_EXAMPLE.strip())))
        return lcg.Section(title=cls.name(), content=content)

    # Instance methods

    def _check_tasks(self, tasks):
        for task in tasks:
            self._check_task(task)

    def _check_task(self, task):
        assert isinstance(task, self._TASK_TYPE), \
            "Not a %s instance: %r" % (self._TASK_TYPE.__name__, task)

    def instructions(self):
        return self._instructions

    def answers(self):
        """Return all correct answers for all tasks within the exercise.

        Returns a sequence of answers in the form expected by the Javascript
        exercise evaluation handler.  Typically this is a list of choice
        indexex for choice based exercises or a list of text answers for
        fill-in exercises.

        """
        return ()

    def tasks(self):
        return self._tasks

    def template(self):
        return self._template


class _ChoiceBasedExercise(Exercise):
    "A superclass for all exercises based on choosing from predefined answers."

    _TASK_TYPE = ChoiceTask
    _HELP_INTRO = (
        _("You will hear a response immediately after choosing the answer.  When "
          "you choose the wrong answer, you can try again until you find the "
          "correct one.  The results below the exercise will show you how many "
          "answers you got right on the first try."),
    )

    def answers(self):
        return [t.choice_index(t.correct_choice())
                for t in self._tasks if len(t.choices()) > 0]


class MultipleChoiceQuestions(_ChoiceBasedExercise):
    """Choosing one of several answers for a given question."""

    # Translators: Type of exercise (use language terminology)
    _NAME = _("Multiple Choice Questions")
    _HELP_INTRO = (
        _("Each question in this exercise is followed by two or more possible "
          "answers. Only one answer is correct."),
    ) + _ChoiceBasedExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of a definition of several "
          "questions, where each question has two or more possible answers."),
        _("The question and its possible answers (choices) are written each "
          "at a separate line. The correct answer begins with a plus sign "
          "followed by a space. Incorrect answers begin with a minus sign "
          "and a space."),
        _("Another question and its answers may follow after a blank line."),
    )
    _SOURCE_EXAMPLE = _("""
Screen reader is:
- a person.
- a device.
+ a program.

GNU/Linux is:
- a word processor
+ an operating system
- a computer manufacturer
""")


class Selections(_ChoiceBasedExercise):
    """Selecting one of several statements/sentences (the correct one)."""

    # Translators: Type of exercise (use language terminology)
    _NAME = _("Selections")
    _HELP_INTRO = (
        _("There are several groups of two or three statements. "
          "Only one statement in each group is correct. "
          "Your goal is to decide which one."),
    ) + _ChoiceBasedExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("The exercise definition consists of several groups of statements, "
          "typically two or three statements in a group."),
        _("Each statement in a group is written at a separate line and begins "
          "by a plus sign to mark a correct statement or a minus sign to mark "
          "an incorrect statement.  Just one statement in each "
          "group is correct."),
        _("Another group of statements may follow after a blank line. There are "
          "no blank lines between statements which belong to the same group."),
    )
    _SOURCE_EXAMPLE = _("""
+ India is located in Asia.
- China is located in Africa.

+ Australia is the smallest continent.
- Australia is the largest continent.
""")


class TrueFalseStatements(_ChoiceBasedExercise):
    """Deciding whether the sentence is true or false."""

    _TASK_TYPE = TrueFalseTask
    # Translators: Type of exercise (use language terminology)
    _NAME = _("True/False Statements")
    _HELP_INTRO = (
        _("Each sentence in this exercise is followed by two controls labeled "
          u"‘TRUE’ and ‘FALSE’.  Decide whether the sentence is true or not "
          "and press the corresponding button."),
    ) + _ChoiceBasedExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("The exercise definition consists of several statements separated "
          "by blank lines."),
        _("Each statement is marked as either true using [T] or false "
          "using [F] at the end of the line."),
    )
    _SOURCE_EXAMPLE = _("""
The Microsoft Windows operating system never crashes. [F]

The largest tropical rainforest in the world is in Brazil. [T]
""")


class GapFilling(_ChoiceBasedExercise):
    """Choosing from a list of words to fill in a gap in a sentence."""

    # Translators: Type of exercise (use language terminology)
    _NAME = _("Gap Filling")
    _HELP_INTRO = (
        _("Choose the correct word to fill in a gap in a sentence.  For each gap "
          "you have several choices.  Only one of them is correct."),
    ) + _ChoiceBasedExercise._HELP_INTRO

    _SOURCE_FORMATTING = (
        _("One exercise typically consists of a definition of several "
          "statements, where there is one missing word in each statement."),
        _("The missing word is replaced by a series of underscores (at "
          "least three) and possible completions of the gap follow at "
          "separate lines. The correct completion begins with a plus sign "
          "followed by a space. Incorrect completions begin with a minus sign "
          "and a space."),
        _("Another statement and its completions may follow after a blank line."),
    )
    _SOURCE_EXAMPLE = _("""
If you want to send money to somebody, you can ____ a transfer.
- do
+ make
- have

To change money between two currencies you need to know the ____ rate.
- success
- interest
+ exchange
""")


class HiddenAnswers(Exercise):
    """Question and a hidden answer which the user can unhide to check."""

    _NAME = _("Hidden Answers")
    _TASK_TYPE = ContentTask

    _HELP_INTRO = (
        _("You should simply think of the correct answer and when "
          "you believe you know it, you can unhide the correct answer "
          "below each question and check whether you were right or not."),
    )
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of a definition of several "
          "questions and answers."),
        _("The question and the answer are written each at a separate line."),
        _("Another pair or question and answer may follow after a blank line."),
    )
    _SOURCE_EXAMPLE = _("""
What is the name of the highest mountain in the world?
Mount Everest.

What is its height?
8,848m
""")


class FillInExercise(Exercise):
    """A common base class for exercises based on writing text into fields."""

    _TASK_TYPE = TextTask
    _HELP_INTRO = (
        _("You can check each answer individually using the shortcut keys. "
          "When your answer is evaluated as incorrect and you do not know "
          "why, always check whether you have used correct punctuation and "
          "capital letters where appropriate. The evaluation will only accept "
          "exactly matching answers."),
        _("Use the control panel at the bottom of the exercise to evaluate all the "
          "answers at once."),
    )
    _SOURCE_FORMATTING = (
        #_("If there is more than one possible correct answer, the other correct "
        #  "answers may be written inside the brackets separated by the pipeline "
        #  'character "|".'),
        _("The brackets may also contain a series of underscores instead of the "
          "real answer. This means that the real answer is either not known or "
          "not needed. The exercise will not offer automatic evaluation, but the "
          "text box will allow the user to fill in any text.  The number of "
          "underscores determines the size of the box."),
    )

    def answers(self):
        answers = []
        for task in self._tasks:
            answers.extend(task.answers())
        return tuple(answers)


class _SingleTextBoxFillInExercise(FillInExercise):
    """Fill In Exercise with one text box per task."""

    def _check_task(self, task):
        super(_SingleTextBoxFillInExercise, self)._check_task(task)
        assert len(task.answers()) == 1


class VocabExercise(_SingleTextBoxFillInExercise):
    """A small text-field for each vocabulary item on a separate row."""

    _NAME = _("Vocabulary Exercise")
    _HELP_INTRO = (
        _("There are two ways to do the exercise: orally and written.  Do the "
          "exercise both ways to get the best results."),
        _("To do the exercise orally is simple.  Go through the vocabulary list "
          "and think of the correct translation for each word or expression. "
          u"There is a ‘Play’ button after the text box for each item which "
          "allows you to hear the correct answer.  Repeat the answer to practice "
          "the correct pronunciation.  Some items have more than one correct "
          "answer, so there may be multiple buttons to play each of them.  Since "
          "there is no way of checking your oral answers, the results are not "
          "available.  If you want to see your score, you must do the written "
          "exercise."),
        _("To do the exercise in written form, simply type the translation of "
          "each item into the text box.  Be careful to use capital letters where "
          "this is appropriate, since an answer without correct capitalization is "
          "always considered incorrect.  When the prompt is a complete sentence, "
          "you must also use correct punctuation."),
    ) + FillInExercise._HELP_INTRO


class WrittenAnswers(_SingleTextBoxFillInExercise):
    """A prompt (a sentence) and a big text-field for each task."""

    # Translators: Type of exercise (use language terminology)
    _NAME = _("Written Answers")
    _HELP_INTRO = (
        _("Fill in the answer to the box below each question."),
    ) + _SingleTextBoxFillInExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of a definition of several "
          "questions and answers."),
        _("The question and the correct answer are written each at a separate line."),
        _("Either whole or a part of the answer is written inside square "
          "brackets.  The text inside the brackets is supposed to be filled "
          "into the text box by the user. The text before and after will "
          "appear on the screen providing a hint or a template of the "
          "expected answer for the user."),
        _("Another pair or question and answer may follow after a blank line."),
    ) + FillInExercise._SOURCE_FORMATTING
    _SOURCE_EXAMPLE = _("""
What is the name of the largest continent?
[Asia]

Use the correct form of the verb "to be":
Children [are] our future.
""")


class NumberedCloze(_SingleTextBoxFillInExercise):
    _NAME = _("Complete the Statements")
    _HELP_INTRO = (
        _("The goal is to fill in the gaps in given statements.  The answers "
          "are written into a text box and there is just one correct answer "
          "for each gap."),
    ) + FillInExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of several statements separated by "
          "blank lines from each other. Certain part of each statement is "
          "written in square brackets.  This part will be replaced by a text "
          "entry field. The text inside brackets is the correct answer. There "
          "is just one pair of brackets in each statement."),
    ) + FillInExercise._SOURCE_FORMATTING
    _SOURCE_EXAMPLE = _("""
[London] is the capital of the United Kingdom.

The city is split by the River [Thames] into North and South.
""")


class Cloze(FillInExercise):
    """Paragraphs of text including text-fields for the marked words."""
    # Translators: Type of exercise (use language terminology)
    _NAME = _("Cloze")
    _HELP_INTRO = (
        _("The goal is to fill in the gaps in given piece of text.  The answers "
          "are written into text boxes and there is just one correct answer "
          "for each gap."),
    ) + FillInExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of one or more paragraphs of text. "
          "Selected parts of the text (typically words), which are to be replaced "
          "by text entry fields are written in square brackets. The text inside "
          "brackets is the correct answer."),
    ) + FillInExercise._SOURCE_FORMATTING
    _SOURCE_EXAMPLE = _("""
Commercial banks and savings banks receive and hold deposits
[in] current accounts, savings accounts and deposit accounts,
make payments [for] their customers, lend money, [and] offer
investment advice, foreign exchange facilities, and so on.
""")


class ModelCloze(FillInExercise):
    """Same as Cloze, but with model answers (more correct answers are possible)."""
    # Translators: Type of exercise (use language terminology)
    _NAME = _("Cloze with Model Answers")
    _HELP_INTRO = (
        _("The goal is to fill in the gaps in given piece of text.  The answers "
          "are written into text boxes.  The provided model answers are just "
          "suggestions.  Other answers may be correct as well so the exercise is "
          "not evaluated automatically.  Model answers may be unhidden."),
    ) + FillInExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of one or more paragraphs of text. "
          "Selected parts of the text (typically words), which are to be replaced "
          "by text entry fields are written in square brackets. The text inside "
          "brackets is the model answer."),
    )
    _SOURCE_EXAMPLE = _("The [sun] is shining. Mom has bought a [yogurt]. "
                        "The sailor holds a [telescope].")


################################################################################
##################################   Tests   ###################################
################################################################################

class _Test(object):
    """Tests are similar to exercises, but instead of practice, they are used for testing.

    It would be more logical to derive exercises from tests, since tests are simpler (they are not
    interactive).  Due to historical reasons, however, they are implemented by overriding
    exercises and leaving out everything, what is not necesarry...

    """
    _POINTS = 1

    def __init__(self, *args, **kwargs):
        """Initialize the instance.

        Arguments:

          points -- number of points per task. Used in tests to count the final
            result in points.  Each exercise type may have a different default
            number of points, which may be overriden by this argument.

        Other arguments are the same as in parent class.

        """
        self._points = points = kwargs.pop('points', self._POINTS)
        assert isinstance(points, int), points
        super(_Test, self).__init__(*args, **kwargs)

    def _result_fields(self, context):
        points = self.eval(context.req())
        return [(_("Total points:"), 'total-points', True, '%d/%d' % (points, self.max_points()))]

    def eval(self, req):
        """Evaluate the answers of given request and return the number of points."""
        points = 0
        for i, correct_answer in enumerate(self.answers()):
            name = '%s-a%d' % (self.id(), i + 1)
            answer = self._param(req, name)
            # Correct answer is a numer or string.
            if answer == unistr(correct_answer):
                points += self.points()
            # elif not answer:
            #    empty += self.points()
        return points

    def points(self):
        return self._points

    def added_points(self, req):
        # TODO: _exercise_id() doesn't exist anymore. Another identification
        # must be used if this is ever needed...
        if req.has_param('--added-points'):
            return req.param('--added-points').get(self._exercise_id(), 0)
        elif req.has_param(self._exercise_id() + '-added-points'):
            points = req.param(self._exercise_id() + '-added-points')
            try:
                return int(points)
            except ValueError:
                return None
        else:
            return 0

    def max_points(self):
        return self.points() * len(self.answers())


class ChoiceBasedTest(_Test, _ChoiceBasedExercise):
    pass


class FillInTest(_Test, FillInExercise):
    pass


class MultipleChoiceQuestionsTest(ChoiceBasedTest, MultipleChoiceQuestions):
    pass


class SelectionsTest(ChoiceBasedTest, Selections):
    pass


class TrueFalseStatementsTest(ChoiceBasedTest, TrueFalseStatements):
    pass


class GapFillingTest(ChoiceBasedTest, GapFilling):
    pass


class WritingTest(FillInTest):
    _POINTS = 10
    # Translators: Type of exercise
    _NAME = _("Writing")

    def __init__(self, tasks=(), **kwargs):
        assert len(tasks) == 0
        super(WritingTest, self).__init__(tasks=(TextTask(None, ''),), **kwargs)

    def _field_result(self, context, name, text):
        return ''

    def eval(self, req):
        # Prevent returning full points on empty answer.
        return 0


class ClozeTest(FillInTest, Cloze):
    pass


class NumberedClozeTest(FillInTest, NumberedCloze):
    pass
