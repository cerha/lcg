# -*- coding: utf-8 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2014 Brailcom, o.p.s.
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

import lcg
import re

_ = lcg.TranslatableTextFactory('lcg-exercises')

################################################################################
################################     Tasks     #################################
################################################################################

class Task(object):
    """Abstract base class of all task types.

    Tasks are not the 'Content' instances.  They are not able to render
    themselves.  They just hold the data.
    
    """

    def __init__(self, prompt, comment=None):
        assert isinstance(prompt, lcg.Content) or prompt is None, prompt
        assert isinstance(comment, unicode) or comment is None, comment
        self._comment = comment
        self._prompt = prompt

    def prompt(self):
        return self._prompt
    
    def comment(self):
        return self._comment


class HiddenAnswerTask(Task):

    def __init__(self, prompt, answer, **kwargs):
        self._answer = answer
        super(HiddenAnswerTask, self).__init__(prompt, **kwargs)

    def answer(self):
        return self._answer


class Choice(object):
    """Representation of one choice for '_ChoiceTask'.

    This is the answer text with an information whether it is correct or not.

    """
    def __init__(self, answer, correct=False):
        assert isinstance(answer, (str, unicode))
        assert isinstance(correct, bool)
        self._answer = answer
        self._correct = correct

    def answer(self):
        return self._answer

    def correct(self):
        return self._correct

        
class _ChoiceTask(Task):
    """Abstract base class for all choice-based tasks."""
    
    def __init__(self, prompt, choices, **kwargs):
        """Initialize the instance.

        Arguments:
        
          choices -- sequence of 'Choice' instances related to this Task.
          
        """
        assert all([isinstance(choice, Choice) for choice in choices])
        assert len([ch for ch in choices if ch.correct()]) == 1 or not choices
        self._choices = list(choices)
        super(_ChoiceTask, self).__init__(prompt, **kwargs)

    def choices(self):
        return self._choices

    def correct_choice(self):
        for choice in self._choices:
            if choice.correct():
                return choice
        raise Exception("No correct choice found!")

    def choice_index(self, choice):
        return self._choices.index(choice)
        
        
class MultipleChoiceQuestion(_ChoiceTask):
    pass


class Selection(_ChoiceTask):
    
    def __init__(self, choices, **kwargs):
        super(Selection, self).__init__(None, choices, **kwargs)

        
class GapFillStatement(_ChoiceTask):
    pass
    

class TrueFalseStatement(_ChoiceTask):

    def __init__(self, statement, correct=True, comment=None):
        """Initialize the instance.

        Arguments:
        
          statement -- exercise within the containing section.
          correct -- boolean flag indicating whether the statement is correct
            or not (true when it is correct).
          
        """
        assert isinstance(correct, bool)
        # Translators: Labels for exercise buttons. Keep in capitals.
        choices = (Choice(_('TRUE'), correct), Choice(_('FALSE'), not correct))
        super(TrueFalseStatement, self).__init__(statement, choices,
                                                 comment=comment)


class FillInTask(Task):
    """Tasks, where the answer is to be filled into a text box."""
    
    def __init__(self, prompt, text, comment=None, media=()):
        assert isinstance(text, basestring)
        if isinstance(media, lcg.Media):
            media = (media, )
        else:
            assert all([isinstance(m, lcg.Media) for m in media])
        self._text = text.replace('\n', ' ').replace('\r', '')
        self._media = media
        super(FillInTask, self).__init__(prompt, comment=comment)

    def text(self):
        return self._text

    def media(self):
        return self._media


class WritingTask(FillInTask):
    """Fill-in task with no predefined answer.""" 

    def __init__(self):
        super(WritingTask, self).__init__(None, '')

class SimpleFillInTask(FillInTask):
    """Fill-in task with no prompt, just text with a single textbox.""" 

    def __init__(self, text, comment=None):
        super(SimpleFillInTask, self).__init__(None, text, comment=comment)

class ClozeTask(FillInTask):
    """Fill in task, which may contain more than one answer."""

    def __init__(self, text, comments=()):
        super(ClozeTask, self).__init__(None, text)
        assert isinstance(comments, (list, tuple))
        self._comments = comments

    def comments(self):
        return self._comments


class ExerciseParser(object):
    """Turns a textual exercise spec. into an 'Exercise' instance.

    This is an intermediate solution to use the old text based exercise
    specifications known from the Eurochance project to define exercises within
    the LCG HTML source code (processed by 'lcg.HTMLProcessor').

    """

    _BLANK_LINE_SPLITTER = re.compile(r"\r?\n\s*\r?\n")
    _GAP_MATCHER = re.compile(r"(___+)")

    def __init__(self):
        self._parser = lcg.Parser()

    def _parse_text(self, text):
        return self._parser.parse_inline_markup(text)
    def _split(self, text):
        return [piece.strip() for piece in self._BLANK_LINE_SPLITTER.split(text)]

    def _read_task(self, type, text, comment):
        # Read a task specification using a method according to given task type.
        try:
            method = {
                Selection: self._read_choices,
                MultipleChoiceQuestion: self._read_prompt_and_choices,
                GapFillStatement: self._read_gap_fill,
                FillInTask: self._read_pair_of_statements,
                SimpleFillInTask: self._read_simple_fillin_task,
                HiddenAnswerTask: self._read_hidden_answer,
                TrueFalseStatement: self._read_true_false_statement,
                ClozeTask: self._read_cloze_task,
            }[type]
        except KeyError:
            raise Exception("Unknown type:", type)
        return method(type, text, comment)

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

    def _read_simple_fillin_task(self, type, text, comment):
        return type(text, comment=comment)

    def _read_cloze_task(self, type, text, comment):
        comments = ()
        cstart = text.find("\n.. ") + 1
        if cstart != 0:
            src_comments = [c[3:] for c in self._split(text[cstart:])]
            text = text[0:cstart].rstrip()
            if src_comments:
                cdict = {}
                fields = [] # Comments unsupported for now.
                for c in src_comments:
                    match = re.search("^<(?P<label>[\w\d]+)>\s*", c)
                    assert match, ('Cloze comments must begin with a label ' +
                                   '(e.g. <1> to refer to a field [xxx<1>]).', c)
                    cdict[match.group('label')] = c[match.end():]
                def _comment(cdict, label):
                    try:
                        c = cdict[label]
                        del cdict[label]
                        return c
                    except KeyError:
                        return None
                comments = [_comment(cdict, label) for a, label in fields]
                assert not cdict, "Unused comments (labels don't match any field label): %s" % cdict
        return type(text, comments=comments)

    def _read_choices(self, type, text, comment):
        return type(self._process_choices(text.splitlines()), comment=comment)

    def _read_prompt_and_choices(self, type, text, comment):
        lines = text.splitlines()
        return type(self._parse_text(lines[0]),
                    self._process_choices(lines[1:]), comment=comment)

    def _read_gap_fill(self, type, text, comment):
        lines = text.splitlines()
        if lines[0].find('___') != -1:
            assert len(self._GAP_MATCHER.findall(lines[0])) == 1, lines[0]
            prompt = self._GAP_MATCHER.sub("\____", lines[0])
            choices = self._process_choices(lines[1:])
        else:
            prompt = text
            choices = ()
        return type(self._parse_text(prompt.strip()), choices, comment=comment)

    def _split_pair_of_statements(self, text):
        lines = text.splitlines()
        assert len(lines) == 2, \
            "Task specification must consist of just 2 lines (%d given)." % \
            len(lines)
        return [l.strip() for l in lines]

    def _read_pair_of_statements(self, type, text, comment):
        prompt, answer = self._split_pair_of_statements(text)
        if answer.startswith('[') and answer.endswith(']'):
            answer = answer[1:-1]
        return type(self._parse_text(prompt.strip()), answer, comment=comment)

    def _read_hidden_answer(self, type, text, comment):
        prompt, answer = self._split_pair_of_statements(text)
        return type(self._parse_text(prompt), self._parse_text(answer), comment=comment)

    def _read_true_false_statement(self, type, text, comment):
        text = text.strip()
        assert text.endswith('[T]') or text.endswith('[F]'), \
            "A true/false statement must end with '[T]' or '[F]'!"
        correct = text.endswith('[T]')
        text = ' '.join([line.strip() for line in text.splitlines()])[:-3].strip()
        return type(self._parse_text(text), correct=correct, comment=comment)

    def parse(self, exercise_type, src, **kwargs):
        """Convert textual exercise specification into an Exercise instance."""
        tasks = []
        task_type = exercise_type.task_type()
        if src:
            assert 'template' not in kwargs
            if issubclass(task_type, ClozeTask):
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
                tasks.append(self._read_task(task_type, t, comment))
        elif 'template' in kwargs:
            def maketask(match):
                tasks.append(self._read_task(task_type, match.group(1), None))
                return "%s"
            m = self._TEMPLATE_TASK_MATCHER
            kwargs['template'] = m.sub(maketask, kwargs['template'].replace('%', '%%'))
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
        assert all([isinstance(t, self._TASK_TYPE) for t in tasks]), \
            "Tasks must be a sequence of '%s' instances!: %s" % (self._TASK_TYPE.__name__, tasks)
        self._tasks = list(self._check_tasks(tasks))
        self._instructions = instructions
        self._template = template

    # Class methods

    @classmethod
    def task_type(cls):
        return cls._TASK_TYPE

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
        return tasks

    def instructions(self):
        return self._instructions

    def _task_name(self, exercise_id, task):
        return exercise_id + '-a%d' % (self._tasks.index(task) + 1)
        
    def task_name(self, exercise_id, task):
        return self._task_name(exercise_id, task)

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


class _NumberedTasksExercise(Exercise):
    pass

################################################################################
################################################################################

class _ChoiceBasedExercise(_NumberedTasksExercise):
    "A superclass for all exercises based on choosing from predefined answers."

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

    _TASK_TYPE = MultipleChoiceQuestion
    # Translators: Type of exercise (use language terminology)
    _NAME = _("Multiple Choice Questions")
    _HELP_INTRO = (
        _("Each question in this exercise is followed by two or more possible "
          "answers. Only one answer is correct."),
    ) + _ChoiceBasedExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of a definition of several "
          "questions, where each question has two or more possbile answers."),
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

    _TASK_TYPE = Selection
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

    _TASK_TYPE = TrueFalseStatement
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

The largest tropical rainforest in the world is in Brasil. [T]
""")


class _SelectBasedExercise(_ChoiceBasedExercise):
    # Currently unused due to problematic accessibile interactive evaluation of
    # select boxes.
    pass
    # HTML formatting moved to HTML formatter.
    # def _format_choices(self, context, exercise_id, task):
    #     g = context.generator()
    #     task_name = self._task_name(exercise_id, task)
    #     return g.select(task_name, id=task_name, readonly=self._readonly(context),
    #                     options=[(ch.answer(), task.choice_index(ch)) for ch in task.choices()])


class GapFilling(_ChoiceBasedExercise):
    """Choosing from a list of words to fill in a gap in a sentence."""

    _TASK_TYPE = GapFillStatement
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


class HiddenAnswers(_NumberedTasksExercise):
    """Question and a hidden answer which the user can unhide to check."""

    _NAME = _("Hidden Answers")
    _TASK_TYPE = HiddenAnswerTask

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


################################################################################
################################################################################

class _FillInExercise(Exercise):
    """A common base class for exercises based on writing text into fields."""

    _TASK_TYPE = FillInTask
    _HELP_INTRO = (
        _("You can check each answer individually using the shortcut keys. "
          "When your answer is evaluated as incorrect and you do not know "
          "why, always check whether you have used correct punctuation and "
          "capital letters where appropriate. The evaluation will only accept "
          "exactly matching answers."),
        _("Use the control panel at the bottom of the exercise to evaluate all the "
          "answers at once."),
    )
    FIELD_MATCHER = re.compile(r"\[([^\]]*?)(?:\<(?P<label>[\w\d]+)\>)?\]")

    def _task_fields(self, task):
        return [(answer.replace('\n', ' ').replace('\r', ''), label)
                for answer, label in self.FIELD_MATCHER.findall(task.text())]

    def _task_answers(self, task):
        fields = self._task_fields(task)
        if fields:
            return [answer for answer, label in fields]
        else:
            return (task.text(),)

    def _task_answer(self, task):
        answers = self._task_answers(task)
        if answers and len(answers) == 1:
            return answers[0]
        else:
            return None

    def _check_tasks(self, tasks):
        for task in tasks:
            answers = self._task_answers(task)
            assert len(answers) == 1, \
                "%s requires just one textbox per task (%d found): %s" % \
                (self.__class__.__name__, len(answers), task.text())
        return tasks

    def answers(self):
        return [self._task_answer(t) for t in self._tasks if t.text() is not None]
    


class VocabExercise(_FillInExercise, _NumberedTasksExercise):
    """A small text-field for each vocabulary item on a separate row."""

    _NAME = _("Vocabulary exercise")
    _HELP_INTRO = (
        _("There are two ways to do the exercise: orally and written.  Do the "
          "exercise both ways to get the best results."),
        _("To do the exercise orally is simple.  Go through the vocabulary list "
          "and think of the correct translation for each word or expression. "
          u"There is a ‘Play’ button after the text-box for each item which "
          "allows you to hear the correct answer.  Repeat the answer to practise "
          "the correct pronunciation.  Some items have more than one correct "
          "answer, so there may be multiple buttons to play each of them.  Since "
          "there is no way of checking your oral answers, the results are not "
          "available.  If you want to see your score, you must do the written "
          "exercise."),
        _("To do the exercise in written form, simply type the translation of "
          "each item into the text-box.  Be careful to use capital letters where "
          "this is appropriate, since an answer without correct capitalization is "
          "always considered incorrect.  When the prompt is a complete sentence, "
          "you must also use correct punctuation."),
    ) + _FillInExercise._HELP_INTRO


class WrittenAnswers(_FillInExercise, _NumberedTasksExercise):
    """A prompt (a sentence) and a big text-field for each task."""

    # Translators: Type of exercise (use language terminology)
    _NAME = _("Written Answers")
    _HELP_INTRO = (
        _("Fill in the answer to the box below each question."),
    ) + _FillInExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of a definition of several "
          "questions and answers."),
        _("The question and the correct answer are written each at a separate line."),
        _("Either whole or a part of the answer is written inside square "
          "brackets.  The text inside the brackets is supposed to be filled "
          "into the text box by the user. The text before and after will "
          "appear on the screen providing a hint or a templete of the "
          "expected answer for the user."),
        #_("If there is more than one possible correct answer, the other correct "
        #  "answers may be written inside the brackets separated by the pipeline "
        #  'character "|".'),
        _("Another pair or question and answer may follow after a blank line."),
    )
    _SOURCE_EXAMPLE = _("""
What is the name of the largest continent?
[Asia]

Use the correct form of the verb "to be":
Children [are] our future.
""")
    
    def _check_tasks(self, tasks):
        for task in tasks:
            answers = self._task_answers(task)
            assert len(answers) == 1
        return tasks


class _Cloze(_FillInExercise):
    # Translators: Type of exercise (use language terminology)
    _NAME = _("Cloze")
    _TASK_TYPE = SimpleFillInTask
    _HELP_INTRO = (
        _("The goal is to fill in the gaps in given piece of text.  The answers "
          "are written into a text box and there is just one correct answer "
          "for each gap."),
    ) + _FillInExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of one or more paragraphs of text. "
          "Selected parts of the text (typically words), which are to be replaced "
          "by text entry fields are written in square brackets. The text inside "
          "brackets is the correct answer."),
        #_("If there is more than one possible correct answer, the other correct "
        #  "answers may be written inside the brackets separated by the pipeline "
        # 'character "|".'),
    )
    _SOURCE_EXAMPLE = _("""
Commercial banks and savings banks receive and hold deposits
[in] current accounts, savings accounts and deposit accounts,
make payments [for] their customers, lend money, [and] offer
investment advice, foreign exchange facilities, and so on.
""")


class _ExposedCloze(_Cloze):
    # Translators: Type of exercise (use language
    # terminology). Exposed cloze is lika Cloze, where students fill
    # in the gaps in a text. In *exposed* cloze however the student
    # chooses from the list of offered answers.
    _NAME = _("Cloze with Selection")
    _HELP_INTRO = (
        _("Your goal is to pick the right words from the list at the "
          "beginning of the exercise to fill in the gaps in the following "
          "piece of text. There is just one correct answer for each "
          "gap. Each word from the list is used just once."),
    ) + _FillInExercise._HELP_INTRO


class NumberedCloze(_Cloze, _NumberedTasksExercise):
    _NAME = _("Complete the Statements")
    _HELP_INTRO = (
        _("The goal is to fill in the gaps in given statements.  The answers "
          "are written into a text box and there is just one correct answer "
          "for each gap."),
    ) + _FillInExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of several statements separated by "
          "blank lines from each other. Certain part of each statement is "
          "written in square brackets.  This part will be replaced by a text "
          "entry field. The text inside brackets is the correct answer. There "
          "is just one pair of brackets in each statement."),
        #_("If there is more than one possible correct answer, the other correct "
        #  "answers may be written inside the brackets separated by the pipeline "
        #  'character "|".'),
    )
    _SOURCE_EXAMPLE = _("""
[London] is the capital of the United Kingdom.

The city is split by the River [Thames] into North and South.
""")


class NumberedExposedCloze(NumberedCloze, _ExposedCloze):
    _NAME = _("Complete the Statements with Selection")
    _HELP_INTRO = (
        _("Your goal is to pick the right words from the list at the "
          "beginning of the exercise to fill in the gaps in the statements "
          "below. There is just one correct answer for each "
          "gap. Each word from the list is used just once."),
    ) + _FillInExercise._HELP_INTRO


class Cloze(_Cloze):
    """Paragraphs of text including text-fields for the marked words."""

    _TASK_TYPE = ClozeTask

    def _check_tasks(self, tasks):
        assert len(tasks) == 1
        return tasks

    def answers(self):
        return self._task_answers(self._tasks[0])


class ExposedCloze(Cloze, _ExposedCloze):
    pass

################################################################################
##################################   Tests   ###################################
################################################################################

class _Test(object):
    """Tests are similar to exercises, but instead of practise, they are used for testing.

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
        assert points is None or isinstance(points, int), points
        self._points = kwargs.pop(points, self._POINTS)
        super(_Test, self).__init__(*args, **kwargs)

    def _result_fields(self, context):
        points = self.eval(context.req())
        return [(_("Total points:"), 'total-points', True, '%d/%d' % (points, self.max_points()))]

    def eval(self, req):
        """Evaluate the answers of given request and return the number of points."""
        points = 0
        for i, correct_answer in enumerate(self.answers()):
            name = '%s-a%d' % (self.anchor(), i + 1,)
            answer = self._param(req, name)
            # Correct answer is a numer or string.
            if answer == unicode(correct_answer):
                points += self.points()
            #elif not answer:
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

class FillInTest(_Test, _FillInExercise):
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

    def _field_result(self, context, name, text):
        return ''

    def _check_tasks(self, tasks):
        assert len(tasks) == 0
        return (WritingTask(),)

    def eval(self, req):
        # Prevent returning full points on empty answer.
        return 0


class ClozeTest(FillInTest, Cloze):
    pass

class ExposedClozeTest(FillInTest, ExposedCloze):
    pass

class NumberedClozeTest(FillInTest, NumberedCloze):
    pass

class NumberedExposedClozeTest(FillInTest, NumberedExposedCloze):
    pass
