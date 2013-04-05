# -*- coding: utf-8 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2013 Brailcom, o.p.s.
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
import re, random
from lcg import concat

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
        
          statement --  exercise within the containing section.
          correct -- boolean flag indicating whether the statement is correct
            or not (true when it is correct).
          
        """
        assert isinstance(correct, bool)
        # Translators: Labels for exercise buttons. Keep in capitals.
        choices = (Choice(_('TRUE'), correct), Choice(_('FALSE'), not correct))
        super(TrueFalseStatement, self).__init__(statement, choices,
                                                 comment=comment)


class FillInTask(Task):
    """Abstract base class for all fill-in text tasks."""
    
    def __init__(self, prompt, answer, comment=None, media=()):
        assert isinstance(answer, basestring)
        if isinstance(media, lcg.Media):
            media = (media, )
        else: 
            assert all([isinstance(m, lcg.Media) for m in media])
        self._answer = answer.replace('\n', ' ').replace('\r','')
        self._media = media
        super(FillInTask, self).__init__(prompt, comment=comment)

    def answer(self):
        return self._answer

    def media(self):
        return self._media


class WritingTask(FillInTask):
    
    def __init__(self):
        super(WritingTask, self).__init__(None, '')

    
class MixedTextFillInTask(FillInTask):
    _FIELD_MATCHER = re.compile(r"\[([^\]]*?)(?:\<(?P<label>[\w\d]+)\>)?\]")

    def _fields(self):
        return [(answer.replace('\n', ' ').replace('\r',''), label)
                for answer, label in self._FIELD_MATCHER.findall(self._text)]
    
    def answers(self):
        return [answer for answer, label in self._fields()]
    
    def answer(self):
        answers = self.answers()
        if answers:
            assert len(answers) == 1
            return answers[0]
        else:
            return None

    def is_mixed(self):
        return self._FIELD_MATCHER.match(self._text) is None

    def text(self, context, exercise_id, field_maker):
        def formatter(text):
            if text:
                content = lcg.Parser().parse_inline_markup(text)
                return context.localize(content.export(context))
            else:
                return ''
        def make_field(match):
            return field_maker(context, exercise_id, self, match.group(1))
        text = formatter(self._text.replace('[', '\['))
        return self._FIELD_MATCHER.sub(make_field, text)


    def plain_text(self):
        return self._FIELD_MATCHER.sub(lambda match: match.group(1), self._text)
    
    
class ClozeTask(MixedTextFillInTask):
        
    def __init__(self, text, comments=(), comment=None):
        self._text = text
        if comment:
            assert comments == ()
            assert len(self.answers()) == 1
            self._comments = (comment, )
        else:
            assert isinstance(comments, (list, tuple))
            fields = self._fields()
            if comments:
                dict = {}
                for c in comments:
                    match = re.search("^<(?P<label>[\w\d]+)>\s*", c)
                    assert match, ('Cloze comments must begin with a label ' +
                                   '(e.g. <1> to refer to a field [xxx<1>]).', c)
                    dict[match.group('label')] = c[match.end():]
                def _comment(dict, label):
                    try:
                        c = dict[label]
                        del dict[label]
                        return c
                    except KeyError:
                        return None
                self._comments = [_comment(dict, label) for a, label in fields]
                assert not dict, "Unused comments (labels don't match any field label): %s" % dict
            else:
                self._comments = [None for x in fields]
        super(ClozeTask, self).__init__(None, text, comment=comment)

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
                Selection:              self._read_choices,
                MultipleChoiceQuestion: self._read_prompt_and_choices,
                GapFillStatement:       self._read_gap_fill,
                FillInTask:             self._read_pair_of_statements,
                HiddenAnswerTask:       self._read_hidden_answer,
                TrueFalseStatement:     self._read_true_false_statement,
                ClozeTask:              self._read_generic_task,
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
    
    def _read_generic_task(self, type, text, comment):
        return type(text, comment=comment)

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
        if issubclass(exercise_type, Cloze):
            cstart = src.find("\n.. ") + 1
            if cstart != 0:
                comments = [c[3:] for c in self._split(src[cstart:])]
                src = src[0:cstart].rstrip()
            else:
                comments = []
            tasks = (task_type(src, comments=comments), )
        elif src:
            assert not kwargs.has_key('template')
            pieces = self._split(src)
            i = 0
            while i < len(pieces):
                t = pieces[i]
                if i+1<len(pieces) and pieces[i+1].startswith('.. '):
                    comment = pieces[i+1][3:]
                    i += 2
                else:
                    comment = None
                    i += 1
                tasks.append(self._read_task(task_type, t, comment))
        elif kwargs.has_key('template'):
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
    _JAVASCRIPT_CLASS = 'lcg.Exercise'
    _READING_INSTRUCTIONS = _("Read the following text:")
    _POINTS = 1
    _RESPONSES = (('correct',   'exercise-responses/c*.mp3'),
                  ('incorrect', 'exercise-responses/i*.mp3'),
                  ('f0-49',     'exercise-responses/o0-49*.mp3'),
                  ('f50-69',    'exercise-responses/o50-69*.mp3'),
                  ('f70-84',    'exercise-responses/o70-84*.mp3'),
                  ('f85-99',    'exercise-responses/o85-99*.mp3'),
                  ('f100',      'exercise-responses/o100*.mp3'))
    _MESSAGES = {"on first attempt": _("on first attempt")}
    _INDICATORS = (('answered', _('Answered:'),
                    _("Displays the number of the tasks you have already answered.  For "
                      "example 4/10 means, that you have answered four out of ten "
                      "questions so you should finish the remaining six.")),
                   ('result', _('Correct:'),
                    _("Displays the number and percentage of successful answers.  The "
                      "first pair of numbers shows the results of all current answers.  If "
                      "you didn't answer all of them correctly on first attempt, there is "
                      "also a second pair of numbers showing how many answers you did "
                      u"succesfuly on the first try.  Use the ‘Reset’ button to start "
                      "again.")))
    _BUTTONS = ((_("Evaluate"), 'button', 'evaluate-button',
                 _("Evaluate the entire exercise.  If an error is found, the cursor is moved to "
                   "the first incorrect answer.  Within a text-box, the cursor is also moved to "
                   "the first incorrect character of your answer.")),
                # Translators: Fill (a form with correct answers).
                (_('Fill'), 'button', 'fill-button',
                 _("Fill in the whole exercise with the correct answers.")),
                (_('Reset'), 'reset', 'reset-button',
                 _("Reset all your answers and start again.")))
    _HELP_INTRO = ()
    _SOURCE_FORMATTING = ()
    _SOURCE_EXAMPLE = None

    _used_types = []
    _help = None
    
    def __init__(self, tasks=(), instructions=None, reading=None, 
                 reading_instructions=None, explanation=None, example=None,
                 template=None, media=None, points=None):
        """Initialize the instance.

        Arguments:

          tasks -- sequence of 'Task' instances related to this exercise.
          instructions -- user supplied instructions.  This is a way how to
            include more specific instructions instead of default exercise
            isnstructions (which are intentionally very general).  The given
            text will be printed before the exercise tasks and should be a
            complete sentence (usually starting with a capital letter and
            ending with a dot or a colon).  This, in consequence, also allows
            to use the same exercise type for different purposes.
          reading -- specifies the reading text, which is displayed at the
            begining of the exercise.  Some exercise types may require a
            reading, some may not.  The text may be formatted as a structured
            text.
          reading_instructions -- The reading text is introduced by a brief
            label 'Read the following text:' by default.  If you want to change
            this, use this argument su supply any text.  Wiki formatting can be
            used here as-well.
          explanation -- any exercise can start with a brief explanation
            (usually of the subject of it's tasks).  Explanations are quite
            similar to readings texts but serve a different purpose.  When both
            are defined, the reading goes first on the output.  They are
            defined as a multi-line structured text using the 'wiki'
            formatting.
          example -- a model answer.  If defined, the tasks will be preceeded
            with given example (a multi-line structured text using the 'wiki'
            formatting).  The formatting should usually follow the formatting
            of the tasks within the exercise.
          media -- filename of the media file to be used with the exercise,
            such as an audio recording.  Some exercise types may require a
            recording, some may not.  The filename must refer to an existing
            Resource file available within resources on export.
          template -- the tasks are rendered as a simple sequence on the
            output.  If you need something more sophisticated (e.g. have text
            and the tasks 'mixed' within it), you can use a template.  Just
            specify any stuctured text and use '%s' placehodlers to be replaced
            by the actual tasks.  Note that you must have exactly the same
            number of the placeholders within the template as the number of
            tasks you pass as the `tasks' arguemnt.  You must also double any
            '%' signs, which are not a part of a placeholder.
          points -- number of points per task. Used in tests to count the final
            result in points.  Each exercise type may have a different default
            number of points, which may be overriden by this argument.
          
        """
        assert media is None or isinstance(media, basestring)
        super(Exercise, self).__init__()
        if self.__class__ not in Exercise._used_types:
            Exercise._used_types.append(self.__class__)
        assert instructions is None or isinstance(instructions, lcg.Content), instructions
        assert reading is None or isinstance(reading, (str, lcg.Content)), reading
        assert reading_instructions is None or isinstance(reading_instructions, (str, lcg.Content))
        assert all([isinstance(t, self._TASK_TYPE) for t in tasks]), \
               "Tasks must be a sequence of '%s' instances!: %s" % (self._TASK_TYPE.__name__, tasks)
        assert points is None or isinstance(points, int), points
        self._tasks = list(self._check_tasks(tasks))
        self._instructions = instructions
        self._explanation = explanation
        self._example = example
        self._reading = reading
        self._reading_instructions = reading_instructions
        self._media = media
        self._points = points or self._POINTS
        self._template = template

    def _readonly(self, context):
        return False
    
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
        sections = [lcg.Section(title=title, anchor=anchor, content=lcg.coerce(content))
                    for title, anchor, content in
                    ((_("Instructions"),  'intro',         cls._help_intro()),
                     (_("Shortcut Keys"), 'keys',          cls._help_keys()),
                     (_("Indicators"),    'indicators',    cls._help_indicators()),
                     (_("Control Panel"), 'panel',         cls._help_panel()))
                    if content is not None]
        return lcg.Container(sections)

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

    @classmethod
    def _help_intro(cls):
        return [lcg.p(p) for p in cls._HELP_INTRO]

    @classmethod
    def _help_keys(cls):
        return None

    @classmethod
    def _help_indicators(cls):
        if cls._INDICATORS:
            return (lcg.p(_("The indicator panel below the exercise shows the following values:")),
                    lcg.dl([(label, help) for name, label, help in cls._INDICATORS]))
        else:
            return None
    
    @classmethod
    def _help_panel(cls):
        if cls._BUTTONS:
            return (lcg.p(_("The control panel below the exercise contains the following "
                            "buttons:")),
                    lcg.dl([(label, hlp) for label, t, cls, hlp in cls._BUTTONS]))
        else:
            return None
    
    # Instance methods

    def _check_tasks(self, tasks):
        return tasks

    def _media_control(self, context, media, inline=False):
        g = context.generator()
        if inline:
            img = context.resource('media-play.gif')
            title = label
            label = g.img(context.uri(img))
        else:
            title = None
            label = _("Play")
        button_id = context.unique_id()
        context.connect_shared_player(context.uri(media), button_id)
        return g.button(label, title=title, type='button', id=button_id, cls='media-control')
                  
    def _export_media(self, context, exercise_id):
        if self._media:
            media = context.resource(self._media)
            g = context.generator()
            if isinstance(media, lcg.Audio):
                label = _("Recording:")
                cls = 'recording'
            else:
                label = _("Video:")
                cls = 'recording'
            return g.div((label, self._media_control(context, media)), cls='media-controls '+cls)
        else:
            return None

    def export(self, context):
        g = context.generator()
        context.resource('lcg.js')
        context.resource('lcg-exercises.js')
        context.resource('lcg-exercises.css')
        context.resource('effects.js')
        context.resource('media.js')
        context.resource('audio.gif')
        context.resource('media-play.gif')
        context.connect_shared_player()
        exercise_id = context.unique_id()
        parts = [method(context, exercise_id) for method in (self._export_instructions,
                                                             self._export_reading,
                                                             self._export_explanation,
                                                             self._export_media,
                                                             self._export_example,
                                                             self._export_tasks,
                                                             self._export_results)]
        content = [x for x in parts if x is not None]
        script = self._export_script(context, exercise_id)
        if script:
            content = (g.form(content, id=exercise_id), 
                       g.script(script))
        return g.div(content, cls='exercise '+lcg.camel_case_to_lower(self.__class__.__name__))

    def _wrap_exported_tasks(self, context, tasks):
        return concat(tasks, separator="\n")
    
    def _export_tasks(self, context, exercise_id):
        g = context.generator()
        exported = [context.localize(self._export_task(context, exercise_id, task)) 
                    for task in self._tasks]
        if self._template:
            template = context.localize(self._template.export(context))
            return template % tuple(exported)
        else:
            return self._wrap_exported_tasks(context, exported)

    def _export_explanation(self, context, exercise_id):
        g = context.generator()
        if self._explanation is not None:
            return _("Explanation:") + g.div(self._explanation.export(context), cls="explanation")
        else:
            return None
        
    def _export_example(self, context, exercise_id):
        g = context.generator()
        if self._example is not None:
            return _("Example:") + g.div(self._example.export(context), cls="example")
        else:
            return None
    
    def _export_reading(self, context, exercise_id):
        g = context.generator()
        if self._reading is not None:
            if self._reading_instructions:
                instructions = self._reading_instructions.export(context)
            else:
                instructions = self._READING_INSTRUCTIONS
            return (g.div(instructions, cls="label") +
                    g.div(self._reading.export(context), cls="reading"))
        else:
            return None

    def _export_instructions(self, context, exercise_id):
        if self._instructions:
            return context.generator().div(self._instructions.export(context))
        else:
            return None

    def _export_script(self, context, exercise_id):
        g = context.generator()
        responses = {}
        for key, filename in self._RESPONSES:
            media = context.resource(filename)
            if media is None:
                media = (lcg.Media(filename),)
            elif isinstance(media, lcg.Media):
                media = (media,)
            responses[key] = [context.uri(m) for m in media]
        return g.js_call('new %s' % self._JAVASCRIPT_CLASS,
                         exercise_id, self.answers(), responses,
                         dict([(msg, context.localize(translation)) 
                               for msg, translation in self._MESSAGES.items()]))

    def _task_style_cls(self):
        return 'task %s-task' % lcg.camel_case_to_lower(self.__class__.__name__)
        
    def _export_task(self, context, exercise_id, task):
        parts = [p for p in self._export_task_parts(context, exercise_id, task) if p is not None]
        return context.generator().div(parts, cls=self._task_style_cls())

    def _task_name(self, exercise_id, task):
        return exercise_id + '-a%d' % (self._tasks.index(task)+1)

    def _export_results(self, context, exercise_id):
        g = context.generator()
        return g.div((g.div(concat([g.label(label, id=exercise_id+'.'+name) +
                                    g.field(name=name, id=exercise_id+'.'+name, size=30,
                                            readonly=True)
                                    for name, label, help in self._INDICATORS],
                                   separator=g.br()),
                            cls='display'),
                      g.div([g.button(label, type=t, cls=cls, title=hlp)
                             for label, t, cls, hlp in self._BUTTONS],
                            cls='buttons')),
                     cls='results')

    def answers(self):
        return ()

    def points(self):
        return self._points
    
    
class _NumberedTasksExercise(Exercise):
    
    def _wrap_exported_tasks(self, context, tasks):
        g = context.generator()
        return g.ol(*[g.li(t) for t in tasks], cls="tasks")


################################################################################
################################################################################
  
class _ChoiceBasedExercise(_NumberedTasksExercise):
    "A superclass for all exercises based on choosing from predefined answers."

    _JAVASCRIPT_CLASS = 'lcg.ChoiceBasedExercise'
    _HELP_INTRO = (
        _("You will hear a response immediately after choosing the answer.  When "
          "you choose the wrong answer, you can try again until you find the "
          "correct one.  The results below the exercise will show you how many "
          "answers you got right on the first try."),
        )

    def answers(self):
        return [t.choice_index(t.correct_choice())
                for t in self._tasks if len(t.choices()) > 0]
    
    def _checked(self, context, task, i):
        return False

    def _choice_text(self, context, task, choice):
        return choice.answer()

    def _choice_control(self, context, exercise_id, task, choice):
        g = context.generator()
        i = task.choices().index(choice)
        task_name = self._task_name(exercise_id, task)
        choice_id = task_name + '-ch%d' % (i+1)
        checked = self._checked(context, task, i)
        # Disable only the unchecked fields in the read-only mode.  This makes the selection
        # unchangable in practice and has also the advantage that the checked fields can be
        # navigated, which is even better than using the `readonly' attributte (which doesn't work
        # in browsers anyway).
        disabled = self._readonly(context) and not checked
        ctrl = g.radio(task_name , id=choice_id, value=i,
                       cls='answer-control', checked=checked, disabled=disabled)
        text = self._choice_text(context, task, choice)
        return concat(ctrl, ' ', g.label(text, choice_id))

    def _format_choices(self, context, exercise_id, task):
        g = context.generator()
        return g.ol(*[g.li(self._choice_control(context, exercise_id, task, ch))
                      for ch in task.choices()],
                    cls='choices')

    def _task_style_cls(self):
        cls = super(_ChoiceBasedExercise, self)._task_style_cls()
        return cls + ' choice-based-task'
    
    def _export_task_parts(self, context, exercise_id, task):
        prompt = task.prompt()
        if prompt:      
            prompt = context.localize(prompt.export(context))
        return (prompt, self._format_choices(context, exercise_id, task))

    
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
    
    def _format_choices(self, context, exercise_id, task):
        g = context.generator()
        return g.div([g.div(self._choice_control(context, exercise_id, task, ch))
                       for ch in task.choices()],
                    cls='choices')


class _SelectBasedExercise(_ChoiceBasedExercise):
    # Currently unused due to problematic accessibile interactive evaluation of
    # select boxes.
    _JAVASCRIPT_CLASS = 'lcg.SelectBasedExercise'

    def _format_choices(self, context, exercise_id, task):
        g = context.generator()
        task_name = self._task_name(exercise_id, task)
        return g.select(task_name, id=task_name, readonly=self._readonly(context),
                        options=[(ch.answer(), task.choice_index(ch)) for ch in task.choices()])

    
class GapFilling(_ChoiceBasedExercise):
    """Choosing from a list of words to fill in a gap in a sentence."""

    _TASK_TYPE = GapFillStatement
    # Translators: Type of exercise (use language terminology)
    _NAME = _("Gap Filling")
    _HELP_INTRO = (
        _("Choose the correct word to fill in a gap in a sentence.  For each gap "
          "you have several choices.  Only one of them is correct."),
        ) + _ChoiceBasedExercise._HELP_INTRO
    _GAP_MATCHER = re.compile(r"(___+)")
    
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

    def _export_task_parts(self, context, exercise_id, task):
        g = context.generator()
        prompt = context.localize(task.prompt().export(context))
        return (g.span(self._GAP_MATCHER.sub(g.span("____", cls='exercise-gap'), prompt)),
                self._format_choices(context, exercise_id, task))
    

class HiddenAnswers(_NumberedTasksExercise):
    """Question and a hidden answer which the user can unhide to check."""

    _NAME = _("Hidden Answers")
    _TASK_TYPE = HiddenAnswerTask
    _JAVASCRIPT_CLASS = 'lcg.HiddenAnswers'
    _INDICATORS = ()
    
    _BUTTONS = ((_('Show All'), 'button', 'evaluate-button',
                 _("Show all answers.")),
                (_('Hide All'), 'button', 'reset-button',
                 _("Reset all your answers and start again.")))

    _MESSAGES = {"Show Answer": _("Show Answer"),
                 "Hide Answer": _("Hide Answer")}
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

    def _export_task_parts(self, context, exercise_id, task):
        g = context.generator()
        return (g.div(task.prompt().export(context), cls='question'),
                g.button(_("Show Answer"), cls='toggle-button', 
                         title=_("Show/Hide the correct answer.")),
                # The inner div is needed by the JavaScript effects library for
                # the sliding effect.
                g.div(g.div(task.answer().export(context)),
                      cls='answer', style='display: none;'))


################################################################################
################################################################################

class _FillInExercise(Exercise):
    """A common base class for exercises based on writing text into fields."""

    _TASK_TYPE = FillInTask
    _JAVASCRIPT_CLASS = 'lcg.FillInExercise'
    _HELP_INTRO = (
        _("You can check each answer individually using the shortcut keys. "
          "When your answer is evaluated as incorrect and you do not know "
          "why, always check whether you have used correct punctuation and "
          "capital letters where appropriate. The evaluation will only accept "
          "exactly matching answers."),
        _("Use the control panel at the bottom of the exercise to evaluate all the "
          "answers at once."),
        )

    @classmethod
    def _help_keys(cls):
        return (lcg.p(_("In all the exercises where you fill in the text into a text-box "
                        "you can use the two shortcut keys described below.")),
                lcg.dl(((_("Enter"),
                         _("Use this key within the text-field to evaluate the current answer. "
                           "You hear a sound response and in case of an error, the cursor is "
                           "moved to the position of the first incorrect character within the "
                           "text.  This way you can locate the error, fix it and evaluate again. "
                           u"When you don't know how to fix an error, you can use the ‘hint’ "
                           "key described below.")),
                        (_("Ctrl-Space"),
                         _(u"This function is called a ‘hint’.  It helps you in case you don't "
                           "know the answer or you don't know how to fix an error in your answer. "
                           "Just press the key combination (holding the Ctrl key, press the "
                           "spacebar) and one letter of the correct answer will be filled in "
                           "automatically.  If you have already entered some text, the cursor "
                           "will be moved to after the last correct character and next one will "
                           "be inserted.  This also means that if there is some text after the "
                           "cursor, there is at least one error in it.  Try to locate this error "
                           "and correct it.  Then you can evaluate your answer using the "
                           u"‘Enter’ key (see above) or use ‘hint’ again, until you find the "
                           "complete answer.")))),)
    
    def _check_tasks(self, tasks):
        for t in tasks:
            assert t.answer() is not None or \
                   isnistance(t, MixedTextFillInTask) and \
                   len(t.answers()) == 1, \
                   "%s requires just one textbox per task (%d found)!" % \
                   (self.__class__.__name__, len(t.answers())) 
        return tasks
    
    def answers(self):
        return [t.answer() for t in self._tasks if t.answer() is not None]
        
    def _field_value(self, context, name):
        return ""

    def _field_cls(self, context, name, text):
        return 'fill-in-task'
    
    def _field_result(self, context, name, text):
        return ''
    
    def _make_field(self, context, exercise_id, task, text):
        g = context.generator()
        name = self._task_name(exercise_id, task)
        field = g.field(name=name, id=name, size=max(4, len(text)+1),
                        value=self._field_value(context, name), readonly=self._readonly(context),
                        cls=self._field_cls(context, name, text))
        result = [field] + \
                 [self._media_control(context, m, inline=True) for m in task.media()] + \
                 [self._field_result(context, name, text)]
        return context.localize(concat(result))

    def _export_fill_in_task(self, context, prompt, text):
        return prompt + '<br/>' + text
        
    def _export_task_parts(self, context, exercise_id, task):
        g = context.generator()
        prompt = context.localize(task.prompt().export(context))
        if not (isinstance(task, MixedTextFillInTask) and task.is_mixed()):
            # When the inputfield is embeded within the text, it is confusing to
            # have the prompt marked as a label.  Morover some screeen-readers
            # (JAWs) are confused too and present the task incorrectly.
            prompt = g.label(prompt, self._task_name(exercise_id, task))
        if isinstance(task, MixedTextFillInTask):
            text = task.text(context, exercise_id, self._make_field)
        else:
            text = self._make_field(context, exercise_id, task, task.answer())
        return (self._export_fill_in_task(context, prompt, text),)
                                       
    
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

    def _export_fill_in_task(self, context, prompt, text):
        return prompt +' '+ text


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
        _("If there is more than one possible correct answer, the other correct "
          "answers may be written inside the brackets separated by the pipeline "
          'character "|".'),
        _("Another pair or question and answer may follow after a blank line."),
        )
    _SOURCE_EXAMPLE = _("""
What is the name of the largest continent?
[Asia]

Use the correct form of the verb "to be":
Children [are] our future.
""")


class Transformation(WrittenAnswers):
    pass
class Substitution(WrittenAnswers):
    pass
    

class _Cloze(_FillInExercise):
    # Translators: Type of exercise (use language terminology)
    _NAME = _("Cloze")
    _TASK_TYPE = ClozeTask
    _HELP_INTRO = (
        _("Your goal in this exercise is to fill in the gaps in a longer piece of "
          "text. There is just one correct answer for each gap."),
        ) + _FillInExercise._HELP_INTRO
    _SOURCE_FORMATTING = (
        _("One exercise typically consists of one or more paragraphs of text. "
          "Selected parts of the text (typically words), which are to be replaced "
          "by text entry fields are written in square brackets. The text inside "
          "brackets is the correct answer."),
        _("If there is more than one possible correct answer, the other correct "
          "answers may be written inside the brackets separated by the pipeline "
          'character "|".'),
        )
    _SOURCE_EXAMPLE = _("""
Commercial banks and savings banks receive and hold deposits
[in] current accounts, savings accounts and deposit accounts,
make payments [for] their customers, lend money, [and] offer
investment advice, foreign exchange facilities, and so on.
""")

    def _export_task_parts(self, context, exercise_id, task):
        return (task.text(context, exercise_id, self._make_field),)


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
          "gap. Each word in the list is used just once."),
        ) + _FillInExercise._HELP_INTRO
    
    def _export_instructions(self, context, exercise_id):
        g = context.generator()
        instructions = super(_ExposedCloze, self)._export_instructions(context, exercise_id) or ''
        return instructions + g.ul(*[g.li(a) for a in sorted(self.answers())])

    
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
        _("If there is more than one possible correct answer, the other correct "
          "answers may be written inside the brackets separated by the pipeline "
          'character "|".'),
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

    def _check_tasks(self, tasks):
        assert len(tasks) == 1
        return tasks
    
    def answers(self):
        return self._tasks[0].answers()
        
    def _make_field(self, context, exercise_id, task, text):
        g = context.generator()
        self._field_number += 1
        name = exercise_id + '-a%d' % self._field_number
        field = g.field(name=name, size=len(text),
                        value=self._field_value(context, name),
                        readonly=self._readonly(context),
                        cls=self._field_cls(context, name, text))
        result = concat(field, self._field_result(context, name, text))
        return context.localize(result)

    def _export_task_parts(self, context, exercise_id, task):
        self._field_number = 0
        return (task.text(context, exercise_id, self._make_field),)

    
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
    
    def _export_script(self, context, exercise_id):
        return None

    def _show_results(self, context):
        if not hasattr(context, 'req'):
            return False
        else:
            return context.req().has_param('--evaluate')

    def _param(self, req, name, default=None):
        answers = req.param('--answers')
        if answers is not None:
            return answers.get(name, default)
        else:
            return req.param(name, default)

    def _result_fields(self, context):
        points = self.eval(context.req())
        return [(_("Total points:"), 'total-points', True, '%d/%d' % (points, self.max_points()))]
        
    def _export_results(self, context, exercise_id):
        if not self._show_results(context):
            return None
        g = context.generator()
        points = self.eval(context.req())
        # TODO: Display invalid value of entered added points within tutor's evaluation
        # (to let the tutor fix it).
        added = self.added_points(context.req())
        max = self.max_points()
        def field(label, name, value, size=6, readonly=True, **kwargs):
            id = exercise_id +'-'+ name
            return g.label(label, id=id) +' '+\
                   g.field(value, name=id, id=id, size=size, readonly=readonly,
                           cls=(readonly and 'display' or None), **kwargs)
        if points < max and isinstance(self, FillInTest):
            if added is None:
                total_points = points
            else:
                total_points = points + added
            # Javascript code to update the displayed total points dynamically.
            onchange = ("if (this.value=='') { points = 0; err='' } "
                        "else if (isNaN(this.value)) { points = 0; err=' %(err_invalid)s' } "
                        "else { points = parseInt(this.value); err='' }; "
                        "if (points+%(points)d > %(max)d) { points=0; err=' %(err_exceed)s' } "
                        "this.form.elements['%(exercise_id)s-total-points'].value = "
                        "(points + %(points)d) + '/%(max)d'+err" %
                        dict(points=points, max=max, exercise_id=exercise_id,
                             err_invalid=_("Invalid value in added points!"),
                             err_exceed=_("Max. points exceeded!")))
            readonly = context.req().param('--allow-tutor-evaluation') is not True
            fields = [field(_("Automatic evaluation:"), 'points', points),
                      field(_("Additional points by tutor:"), 'added-points', added or 0,
                            readonly=readonly, onchange=(not readonly and onchange or None)),
                      field(_("Total points:"), 'total-points', '%d/%d' % (total_points, max),
                            size=40)]
        else:
            fields = [field(_("Total points:"), 'total-points', '%d/%d' % (points, max))]
        return g.div(concat(fields, separator=g.br()+"\n"), cls='results')
    
    def _readonly(self, context):
        return self._show_results(context)

    def eval(self, req):
        """Evaluate the answers of given request and return the number of points."""
        points = 0
        for i, correct_answer in enumerate(self.answers()):
            name = '%s-a%d' % (self.anchor(), i+1)
            answer = self._param(req, name)
            # Correct answer is a numer or string.
            if answer == unicode(correct_answer):
                points += self.points()
            #elif not answer:
            #    empty += self.points()
        return points
 
    def added_points(self, req):
        # TODO: _exercise_id() doesn't exist anymore. Another identification
        # must be used if this is ever needed...
        if req.has_param('--added-points'):
            return req.param('--added-points').get(self._exercise_id(), 0)
        elif req.has_param(self._exercise_id()+'-added-points'):
            points = req.param(self._exercise_id()+'-added-points')
            try:
                return int(points)
            except ValueError:
                return None
        else:
            return 0
    
    def max_points(self):
        return self.points() * len(self.answers())
    

class ChoiceBasedTest(_Test, _ChoiceBasedExercise):
    
    def _checked(self, context, task, i):
        return self._param(context.req(), self._task_name(exercise_id, task), False) == str(i)

    def _choice_text(self, context, task, choice):
        text = super(ChoiceBasedTest, self)._choice_text(context, task, choice)
        if self._show_results(context):
            result = None
            if choice.correct():
                result = _("correct answer")
            else:
                name = self._task_name(exercise_id, task)
                if self._param(context.req(), name) == str(task.choices().index(choice)):
                    # Translators: Incorrect (answer)
                   result = _("incorrect")
            if result:
                g = context.generator()
                text += ' ' + g.span(('(', result, ')'), cls='test-answer-comment')
        return text

    
    def _choice_control(self, context, exercise_id, task, choice):
        result = super(ChoiceBasedTest, self)._choice_control(context, exercise_id, task, choice)
        if self._show_results(context):
            name = self._task_name(exercise_id, task)
            if self._param(context.req(), name) == str(task.choices().index(choice)):
                cls = choice.correct() and 'correct-answer' or 'incorrect-answer'
            else:
                cls = 'non-selected-answer'
            result = context.generator().span(result, cls=cls)
        return result
               

class FillInTest(_Test, _FillInExercise):
    
    def _field_value(self, context, name):
        return self._param(context.req(), name, "")
        
    def _field_cls(self, context, name, text):
        cls = 'fill-in-task'
        if self._show_results(context):
            if self._param(context.req(), name) == text:
                cls += ' correct-answer'
            else:
                cls += ' incorrect-answer'
        return cls
    
    def _field_result(self, context, name, text):
        if self._show_results(context) and self._param(context.req(), name) != text:
            return context.generator().span((' (', text, ')'), cls='test-answer-comment')
        return ''

        
class MultipleChoiceQuestionsTest(ChoiceBasedTest, MultipleChoiceQuestions):
    pass
    
class SelectionsTest(ChoiceBasedTest, Selections):
    pass
    
class TrueFalseStatementsTest(ChoiceBasedTest, TrueFalseStatements):
    pass
    
class GapFillingTest(ChoiceBasedTest, GapFilling):
    pass

class TransformationTest(FillInTest, Transformation):
    pass
        
class WritingTest(FillInTest):
    _POINTS = 10
    # Translators: Type of exercise
    _NAME = _("Writing")
    
    def _export_task_parts(self, context, exercise_id, task):
        g = context.generator()
        name = self._task_name(exercise_id, task)
        return (g.textarea(name=name, value=self._field_value(context, name),
                           rows=10, cols=60, readonly=self._readonly(context),
                           cls=self._field_cls(context, name, task.answer())),
                self._field_result(context, name, task.answer()))
        
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
    

