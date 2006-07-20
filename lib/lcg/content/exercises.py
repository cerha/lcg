# -*- coding: iso8859-2 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006 Brailcom, o.p.s.
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

"""Abstraction of exercises as a specific content in a learning module.

This module provides classes for representation of various types of exercises
which can be used within the LCG content tree.

The first part of this module contains the definition of various kinds of
tasks, which make the actual content of exercises (the interactive questions,
fill-in boxes etc).  Each exercise type is a set of several (or no) tasks of
the same kind (this limitation was intentional).  The type of exercise
determines the kind of tasks, however most of the task types are a little more
general, so that they are not bound to a specific exercise type.  In fact, the
exercise type determines the way its tasks are represented on the output.
That's also why the 'Task' instances are not the 'Content' instances.  They are
not able to render themselves.  They just hold the data.

"""

from lcg import *
from lcg.content import *
from lcg.export import _html

import random
import types
import re

################################################################################
################################     Tasks     #################################
################################################################################

class Task(object):
    """Abstract base class of all task types."""

    def __init__(self, prompt, comment=None):
        assert isinstance(prompt, types.UnicodeType) or prompt is None
        assert isinstance(comment, types.UnicodeType) or comment is None
        self._comment = comment
        self._prompt = prompt

    def prompt(self):
        return self._prompt
    
    def comment(self):
        return self._comment


class Choice(object):
    """Representation of one choice for '_ChoiceTask'.

    This is the answer text with an information whether it is correct or not.

    """
    def __init__(self, answer, correct=False):
        assert isinstance(answer, types.UnicodeType)
        assert isinstance(correct, types.BooleanType)
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
        assert is_sequence_of(choices, Choice)
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

    _GAP_MATCHER = re.compile(r"(___+)")

    def __init__(self, prompt, choices, **kwargs):
        super(GapFillStatement, self).__init__(prompt, choices, **kwargs)
        matches = len(self._GAP_MATCHER.findall(prompt))
        if choices:
            assert matches == 1, \
                   "GapFillStatement must include just one gap " + \
                   "marked by three or more underscores. %d found." % matches

    def substitute_gap(self, replacement):
        return self._GAP_MATCHER.sub(replacement, self.prompt())
    

class TrueFalseStatement(_ChoiceTask):
    
    def __init__(self, statement, correct=True, comment=None):
        """Initialize the instance.

        Arguments:
        
          statement --  exercise within the containing section.
          correct -- boolean flag indicating whether the statement is correct
            or not (true when it is correct).
          
        """
        assert isinstance(correct, types.BooleanType)
        choices = (Choice(_('TRUE'), correct), Choice(_('FALSE'), not correct))
        super(TrueFalseStatement, self).__init__(statement, choices,
                                                 comment=comment)


class FillInTask(Task):
    """Abstract base class for all fill-in text tasks."""
    
    def __init__(self, prompt, answer, comment=None, media=()):
        assert isinstance(answer, types.UnicodeType)
        if isinstance(media, Media):
            media = (media, )
        else: 
            assert is_sequence_of(media, Media)
        self._answer = answer.replace('\n', ' ').replace('\r','')
        self._media = media
        super(FillInTask, self).__init__(prompt, comment=comment)

    def answer(self):
        return self._answer

    def media(self):
        return self._media


class DictationTask(FillInTask):
    _REGEXP = re.compile(r"(\s*/\s*|\s+)")
    
    def __init__(self, text, comment=None):
        assert isinstance(text, types.UnicodeType)
        # TODO: This just fixed the input.  It's probably not needed anymore.
        text = self._REGEXP.sub(' ', text).strip()
        super(DictationTask, self).__init__(None, text, comment=comment)


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

    def text(self, field_maker, formatter):
        def make_field(match):
            return field_maker(self, match.group(1))
        text = formatter(self._text.replace('[', '\['))
        return self._FIELD_MATCHER.sub(make_field, text)

    def plain_text(self):
        return self._FIELD_MATCHER.sub(lambda match: match.group(1), self._text)

    
class TransformationTask(MixedTextFillInTask):

    def __init__(self, orig, transformation, comment=None):
        if not self._FIELD_MATCHER.search(transformation):
            transformation = '[' + transformation + ']'
        self._text = transformation
        assert len(self.answers()) == 1
        answer = self.answers()[0]
        super(TransformationTask, self).__init__(orig, answer, comment=comment)
        
    
class ClozeTask(MixedTextFillInTask):
        
    def __init__(self, text, comments=(), comment=None):
        self._text = text
        if comment:
            assert comments == ()
            assert len(self.answers()) == 1
            self._comments = (comment, )
        else:
            assert isinstance(comments, (types.ListType, types.TupleType))
            fields = self._fields()
            if comments:
                dict = {}
                for c in comments:
                    match = re.search("^<(?P<label>[\w\d]+)>\s*", c)
                    assert match, ('Cloze comments must begin with a label ' +
                                   '(e.g. <1> to refer to a field [xxx<1>]).',
                                   c)
                    dict[match.group('label')] = c[match.end():]
                def _comment(dict, label):
                    try:
                        c = dict[label]
                        del dict[label]
                        return c
                    except KeyError:
                        return None
                self._comments = [_comment(dict, label) for a, label in fields]
                assert not dict, ("Unused comments (labels don't match any "
                                  "field label): %s") % dict
            else:
                self._comments = [None for x in fields]
        super(ClozeTask, self).__init__(None, text, comment=comment)

    def comments(self):
        return self._comments


################################################################################
################################   Exercises   #################################
################################################################################


class Exercise(Section):
    """Exercise consists of an assignment and a set of tasks."""

    _ANCHOR_PREFIX = 'ex'
    _TASK_TYPE = None
    _NAME = None
    _RECORDING_REQUIRED = False
    _READING_REQUIRED = False
    _AUDIO_VERSION_REQUIRED = False
    _BUTTONS = ()
    _INDICATORS = ()
    _INSTRUCTIONS = ""
    _AUDIO_VERSION_LABEL = _("This exercise can be also done purely "
                             "aurally/orally:")
    _READING_INSTRUCTIONS = _("Read the following text:")
    _EXPORT_ORDER = None
    _ANSWER_SHEET_LINK_PER_TASK = True

    _used_types = []
    _help_node = None
    
    def __init__(self, parent, tasks, instructions=None, audio_version=None,
                 sound_file=None, transcript=None, reading=None,
                 explanation=None, example=None, template=None,
                 reading_instructions=None):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.

          tasks -- sequence of 'Task' instances related to this exercise.

          instructions -- user supplied instructions.  This is a way how to
            include more specific instructions instead of default exercise
            isnstructions (which are intentionally very general).  The given
            text will be printed before the exercise tasks and should be a
            complete sentence (usually starting with a capital letter and
            ending with a dot or a colon).  This, in consequence, also allows
            to use the same exercise type for different purposes.
            
          audio_version -- name of the file with an audio version of this
            exercise.

          sound_file -- name of the file with a recording as a string.  Some
            exercise types may require a recording, some may not.
            
          transcript -- name of the file with a textual transcript of the
            recording as a string.  The transcript file is required to exist
            whenever the 'sound_file' argument is supplied.  This argument,
            however, is not required when the transcript filename is the same
            as the 'sound_file' filename using the '.txt' extension instead of
            the original sound file extension.
            
          reading -- specifies the reading text, which is displayed at the
            begining of the exercise.  Some exercise types may require a
            reading, some may not.  If a one-line value is supplied, this is
            considered a filename.  The file is then searched within the
            `readings' subdirectory of current node's source directory.  A
            multi-line value is used as the reading text itself.  The text
            (regardless whether read from file or not) is a structured text
            using the 'wiki' formatting.

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

          template -- the tasks are rendered as a simple sequence on the
            output.  If you need something more sophisticated (e.g. have text
            and the tasks 'mixed' within it), you can use a template.  Just
            specify any stuctured text and use '%s' placehodlers to be replaced
            by the actual tasks.  Note that you must have exactly the same
            number of the placeholders within the template as the number of
            tasks you pass as the `tasks' arguemnt.  You must also double any
            '%' signs, which are not a part of a placeholder.
            
        """
        title = _("Exercise %d") +": "+ self._NAME
        super(Exercise, self).__init__(title, Content(), in_toc=False)
        self.set_parent(parent)
        if self.__class__ not in Exercise._used_types:
            Exercise._used_types.append(self.__class__)
        assert instructions is None or \
               isinstance(instructions, types.StringTypes)
        assert reading_instructions is None \
               or isinstance(reading_instructions, types.StringTypes)
        assert is_sequence_of(tasks, self._TASK_TYPE), \
               "Tasks must be a sequence of '%s' instances!: %s" % \
               (self._TASK_TYPE.__name__, tasks)
        assert sound_file is None or isinstance(sound_file, types.StringTypes)
        if self._READING_REQUIRED:
            assert reading is not None, \
            "'%s' requires a reading!" % self.__class__.__name__
        if self._RECORDING_REQUIRED:
            assert sound_file is not None, \
            "'%s' requires a recording!" % self.__class__.__name__
        if self._AUDIO_VERSION_REQUIRED:
            assert audio_version is not None, \
            "'%s' requires an audio version!" % self.__class__.__name__
        self._tasks = list(self._check_tasks(tasks))
        self._custom_instructions = self._wiki_content(instructions)
        self._explanation = self._wiki_content(explanation)
        self._example = self._wiki_content(example, escape=True)
        self._reading = self._wiki_content(reading, allow_file=True,
                                           subdir='readings')
        if reading_instructions is None:
            reading_instructions = self._READING_INSTRUCTIONS
        self._reading_instructions = self._wiki_content(reading_instructions)
        self._template = self._wiki_content(template, allow_file=True,
                                            subdir='templates')
        if sound_file is not None:
            self._recording = parent.resource(Media, sound_file)
            if transcript is None:
                transcript = os.path.splitext(sound_file)[0] + '.txt'
            assert isinstance(transcript, types.StringTypes)
            t = parent.resource(Transcript, transcript,
                                text=self._transcript_text(),
                                input_encoding=parent.input_encoding(),
                                fallback=False)
            self._transcript = t
        else:
            if transcript is not None:
                t = parent.resource(Transcript, transcript)
                log("Transcript without a 'sound_file': %s", t.url())
            self._recording = None
            self._transcript = None
        if audio_version is not None:
            self._audio_version = parent.resource(Media, audio_version)
        else:
            self._audio_version = None
        self._init_resources()

    def _wiki_content(self, text, allow_file=False, subdir=None, escape=False):
        if text is None:
            return None
        assert isinstance(text, types.StringTypes)
        if allow_file and len(text.splitlines()) == 1:
            name, ext = os.path.splitext(text)
            if subdir:
                name = os.path.join(subdir, name)
            try:
                content = self._parent.parse_wiki_file(name, ext=ext[1:])
            except IOError, e :
                log("Unable to read file: %s", e)
                return None
        else:
            if escape:
                text = re.sub('\[', '\\[', text)
            content = self._parent.parse_wiki_text(text)
        container = Container(content)
        container.set_parent(self._parent)
        return container
    
    def _init_resources(self):
        self.parent().resource(Script, 'audio.js')

    # Class methods
        
    def task_type(cls):
        return cls._TASK_TYPE
    task_type = classmethod(task_type)
    
    def name(cls):
        return cls._NAME
    name = classmethod(name)

    def used_types(cls):
        return cls._used_types
    used_types = classmethod(used_types)

    def set_help_node(cls, node):
        cls._help_node = node
    set_help_node = classmethod(set_help_node)
    
    def typedict(cls):
        # Quick hack: globals already contain all types...
        return globals()
    typedict = classmethod(typedict)
    
    # Instance methods

    def _check_tasks(self, tasks):
        return tasks

    def _transcript_text(self):
        return None

    def _exercise_id(self):
        return self.anchor()
    
    def _form_name(self):
        return self._exercise_id().replace('.', '_')
    
    def _instructions(self):
        return self._INSTRUCTIONS

    def _play_button(self, media):
        button = _html.button(_("Play"), "play_audio('%s')" % media.url(),
                              cls='sound-control')
        link = _html.link(_("Play"), media.url())
        return _html.script_write(button, '[' + link + ']')
                  
    def _sound_controls(self, label, media, transcript=None, cls=None):
        if transcript is not None:
            t = _html.link(_("show transcript"), transcript.url(),
                           target="transcript") + "\n"
        else:
            t = ""
        result = ('<form class="sound-control%s" action="#">%s\n' % \
                  (cls and ' '+cls or '', label),
                  self._play_button(media),
                  _html.script_write(_html.button(_("Stop"), 'stop_audio()'),
                                     condition='document.media_player'),
                  t + '</form>')
        return '\n'.join(result)

    def export(self, exporter):
        header = _html.div((self._header(),
                      _html.link(_("Exercise Help"), self._help_node.url(),
                                 target='help', cls='exercise-help-link')),
                           cls='exercise-header')
        parts = [getattr(self, '_export_'+part)(exporter)
                 for part in self._EXPORT_ORDER or ('reading',
                                                    'explanation',
                                                    'instructions',
                                                    'recording',
                                                    'audio_version',
                                                    'example',
                                                    'tasks')]
        parts.append(_html.script(self._init_script()))
        return "\n\n".join([x for x in [header]+parts if x is not None])

    def _wrap_exported_tasks(self, tasks):
        return "\n".join(tasks)
    
    def _export_tasks(self, exporter):
        exported = [self._export_task(exporter, t) for t in self._tasks]
        if self._template:
            exported = self._template.export(exporter) % tuple(exported)
        else:
            exported = self._wrap_exported_tasks(exported)
        if exported:
            return _html.form((exported, self._results()),
                              name=self._form_name())
        else:
            return None

    def _export_explanation(self, exporter):
        if self._explanation is not None:
            return _("Explanation:") + \
                   _html.div(self._explanation.export(exporter),
                             cls="explanation")
        else:
            return None
        
    def _export_example(self, exporter):
        if self._example is not None:
            return _("Example:") + \
                   _html.div(self._example.export(exporter), cls="example")
        else:
            return None
    
    def _export_reading(self, exporter):
        if self._reading is not None:
            return _html.div(self._reading_instructions.export(exporter), cls="label")+\
                   _html.div(self._reading.export(exporter), cls="reading")
        else:
            return None
    
    def _export_instructions(self, exporter):
        """Return the HTML formatted instructions for this type of exercise."""
        custom = self._custom_instructions
        if custom:
            return custom.export(exporter)
        else:
            default = self._instructions()
            return default and _html.p(default)

    def _export_recording(self, exporter):
        if self._recording:
            return self._sound_controls(_("Recording:"), self._recording,
                                        self._transcript)
        else:
            return None
    
    def _export_audio_version(self, exporter):
        if self._audio_version:
            label = self._AUDIO_VERSION_LABEL
            return self._sound_controls(label, self._audio_version,
                                        cls='audio-version')
        else:
            return None

        
    def _task_style_cls(self):
        return 'task %s-task' % camel_case_to_lower(self.__class__.__name__)
        
    def _export_task(self, exporter, task):
        parts = self._export_task_parts(exporter, task)
        if not isinstance(parts, (types.TupleType, types.ListType)):
            parts = [parts]
        else:
            parts = [p for p in parts if p is not None]
        if self._ANSWER_SHEET_LINK_PER_TASK:
            parts.append(self._answer_sheet_link(self._tasks.index(task)))
        return _html.div(parts, cls=self._task_style_cls())

    def _task_name(self, task):
        return self._exercise_id() + '-t%d' % (self._tasks.index(task)+1)

    def _results(self):
        return ""

    def _init_script(self):
        return ""
        
    
class _NumberedTasksExercise(Exercise):
    
    def _wrap_exported_tasks(self, tasks):
        return _html.list(tasks, ordered=True, cls="tasks")

    
class Listening(Exercise):
    _NAME = _("Listening")
    _RECORDING_REQUIRED = True

    
class Reading(Exercise):
    _NAME = _("Reading")
    _READING_REQUIRED = True
        
    
class SentenceCompletion(Exercise):
    _NAME = _("Sentence Completion")
    _AUDIO_VERSION_REQUIRED = True
    _TASK_TYPE = None
    _INSTRUCTIONS = _("Speaking Practice.  Complete the sentences you hear, "
                      "using the example as a model.")
    _AUDIO_VERSION_LABEL = _("Press Play to listen to the instructions:")
    
    
class _InteractiveExercise(Exercise):
    """A common super class for exercises which can be interactively evaluated.

    These exercises allow the user to indicate his answers and the computer
    gives him a feedback.
    
    """
    _RESPONSES = (('correct',   'responses/c*.mp3'),
                  ('incorrect', 'responses/i*.mp3'),
                  ('f0-49',     'responses/o0-49*.mp3'),
                  ('f50-69',    'responses/o50-69*.mp3'),
                  ('f70-84',    'responses/o70-84*.mp3'),
                  ('f85-99',    'responses/o85-99*.mp3'),
                  ('f100',      'responses/o100*.mp3'))
    
    _FORM_HANDLER = 'Handler'
    _MESSAGES = {", $x ($y%) on first attempt":_(", $x ($y%) on first attempt")}

    _INDICATORS = (('answered', _('Answered:')),
                   ('result', _('Correct:')))
    
    def _init_resources(self):
        super(_InteractiveExercise, self)._init_resources()
        parent = self.parent()
        parent.resource(Script, 'exercises.js')
        parent.resource(Script, 'audio.js')
        self._responses = {}
        for key, filename in self._RESPONSES:
            media = parent.resource(SharedMedia, filename)
            if not isinstance(media, (types.ListType, types.TupleType)):
                media = (media,)
            self._responses[key] = tuple(media)
            
    def _response(self, selector):
        responses = self._responses[selector]
        return responses[random.randint(0, len(responses)-1)]
        
    def _answers(self):
        return ()

    def _init_script(self):
        args = (_html.js_array(self._answers()),
                _html.js_dict(dict([(key, [media.url() for media in values])
                                    for key, values
                                    in self._responses.items()])),
                _html.js_dict(self._MESSAGES))
        return """
        form = document.forms['%s'];
        handler = new %s();
        form.handler = handler;
        handler.init(form, %s);
        """ % (self._form_name(), self._FORM_HANDLER, ", ".join(args))

    def _results(self):
        field_id = lambda name: self._exercise_id() + '.' + name
        displays = [' '.join((_html.label(label, id=field_id(name)),
                              _html.field(name=name, size=50, readonly=True,
                                          id=field_id(name))))
                    for name, label in self._INDICATORS]
        buttons = [f(label, handler) for f, label, handler in
                   ((_html.button,_("Evaluate"),"this.form.handler.evaluate()"),
                    (_html.button,_('Fill'),    "this.form.handler.fill()"),
                    (_html.reset, _('Reset'),   "this.form.handler.reset()"))]
        panel = _html.div((_html.div('<br/>'.join(displays), 'display'),
                           _html.div(buttons, 'buttons')), 'results')
        l = _html.p(_("See the %s to check your results.") %
                    _html.link(_("answer sheet"), self._answer_sheet_url(),
                               target='help'))
        return _html.script_write(panel, l)

    def _answer_sheet_items(self):
        return ()
    
    def _answer_sheet_anchor(self, index=None):
        a = self.anchor()
        if index is None:
            return a
        else:
            return "%s-a%d" % (a, index)
    
    def _answer_sheet_url(self, index=None):
        return self._answer_sheet_node.url() + "#" + \
               self._answer_sheet_anchor(index)

    def _answer_sheet_link(self, index):
        lnk = _html.link('?', self._answer_sheet_url(index),
                         title=_("Show the answer sheet."),
                         target='help', cls='answer-sheet-link')
        b1, b2 = [_html.span(b, cls='hidden') for b in ('[', ']')]
        return b1 + lnk + b2
        
    def answer_sheet(self, parent):
        self._answer_sheet_node = parent
        i = 0
        items = []
        for answer, comment in self._answer_sheet_items():
            a = Anchor(self._answer_sheet_anchor(i), answer)
            if comment:
                c = Paragraph(WikiText(comment))
                items.append(Container((a, c)))
            else:
                items.append(a)
            i += 1
        anchor = Anchor(self._answer_sheet_anchor())
        answers = ItemizedList(items, type=ItemizedList.TYPE_NUMERIC)
        return Container((anchor, answers))

    
################################################################################
################################################################################
  
class _ChoiceBasedExercise(_InteractiveExercise, _NumberedTasksExercise):
    "A superclass for all exercises based on choosing from predefined answers."

    _FORM_HANDLER = 'ChoiceBasedExerciseHandler'
    _INSTRUCTIONS = _("Chose the correct answer.")

    def _answers(self):
        return [t.choice_index(t.correct_choice())
                for t in self._tasks if len(t.choices()) > 0]
    
    def _answer_sheet_items(self):
        return [(t.correct_choice().answer(), t.comment())
                for t in self._tasks if len(t.choices()) > 0]

    def _non_js_choice_control(self, task, choice):
        media = self._response(choice.correct() and 'correct' or 'incorrect')
        return _html.link(choice.answer(), media.url())
    
    def _js_choice_control(self, task, choice):
        i = task.choices().index(choice)
        task_name = self._task_name(task)
        choice_id = task_name + '-ch%d' % (i+1)
        ctrl = _html.radio(task_name , id=choice_id,
                           onclick="this.form.handler.eval_answer(this)", 
                           value=i, cls='answer-control')
        return ctrl +' '+ _html.label(choice.answer(), choice_id)

    def _choice_label(self, task, choice):
        return chr(ord('a') + task.choice_index(choice)) + '.&nbsp;'
        
    def _format_choice(self, task, choice):
        ctrl = _html.script_write(self._js_choice_control(task, choice),
                                  self._non_js_choice_control(task, choice))
        return self._choice_label(task, choice) + ctrl + '<br/>'

    def _format_choices(self, task):
        formatted = [self._format_choice(task, ch) for ch in task.choices()]
        return _html.div(formatted, 'choices')

    def _task_style_cls(self):
        cls = super(_ChoiceBasedExercise, self)._task_style_cls()
        return cls + ' choice-based-task'
    
    def _export_task_parts(self, exporter, task):
        prompt = exporter.format_wiki_text(self.parent(), task.prompt())
        return (prompt, self._format_choices(task))

    
class MultipleChoiceQuestions(_ChoiceBasedExercise):
    """Choosing one of several answers for a given question."""
    
    _TASK_TYPE = MultipleChoiceQuestion
    _NAME = _("Multiple Choice Questions")

    
class Selections(_ChoiceBasedExercise):
    """Selecting one of several statements/sentences (the correct one)."""
    
    _TASK_TYPE = Selection
    _NAME = _("Selections")

    
class TrueFalseStatements(_ChoiceBasedExercise):
    """Deciding whether the sentence is true or false."""
    
    _TASK_TYPE = TrueFalseStatement
    _NAME = _("True/False Statements")
    _INSTRUCTIONS = _("For each of the statements below, choose True or False.")
    
    def _choice_label(self, task, choice):
        return ""

    
class _SelectBasedExercise(_ChoiceBasedExercise):

    _FORM_HANDLER = 'SelectBasedExerciseHandler'

    def _format_choices(self, task):
        task_name = self._task_name(task)
        js = _html.select(task_name, id=task_name,
                          options=[(ch.answer(), task.choice_index(ch))
                                   for ch in task.choices()],
                          onchange="this.form.handler.eval_answer(this)")
        nonjs = [self._non_js_choice_control(task, ch) for ch in task.choices()]
        return _html.script_write(js, "("+"|".join(nonjs)+")")

    
class GapFilling(_ChoiceBasedExercise):
    """Choosing from a list of words to fill in a gap in a sentence."""

    _TASK_TYPE = GapFillStatement
    _NAME = _("Gap Filling")
    _INSTRUCTIONS = _("Choose the correct option to fill the gaps in the "
                      "following sentences.")


    def _export_task_parts(self, exporter, task):
        prompt = exporter.format_wiki_text(self.parent(),
                                           task.substitute_gap("\____"))
        #return prompt.replace('%s', self._format_choices(task)) +'\n'
        return (prompt, self._format_choices(task))
    

################################################################################
################################################################################

class _FillInExercise(_InteractiveExercise):
    """A common base class for exercises based on writing text into fields."""

    _TASK_TYPE = FillInTask
    
    _FORM_HANDLER = 'FillInExerciseHandler'

    _TASK_FORMAT = "%s<br/>%s"

    def _check_tasks(self, tasks):
        for t in tasks:
            assert t.answer() is not None or \
                   isnistance(t, MixedTextFillInTask) and \
                   len(t.answers()) == 1, \
                   "%s requires just one textbox per task (%d found)!" % \
                   (self.__class__.__name__, len(t.answers())) 
        return tasks
    
    def _answers(self):
        return [t.answer() for t in self._tasks if t.answer() is not None]
        
    def _answer_sheet_items(self):
        return [('; '.join(t.answer().split('|')), t.comment())
                for t in self._tasks if t.answer() is not None]
    
    def _make_field(self, task, text):
        name = self._task_name(task)
        field = _html.field(cls='fill-in-task', name=name, id=name,
                            size=max(4, len(text)+1))
        controls = [self._play_button(m) for m in task.media()]
        field += ''.join(controls)
        return field
    
    def _export_task_parts(self, exporter, task):
        prompt = exporter.format_wiki_text(self.parent(), task.prompt())
        if isinstance(task, MixedTextFillInTask):
            formatter = lambda t: exporter.format_wiki_text(self.parent(), t)
            text = task.text(self._make_field, formatter)
        else:
            text = self._make_field(task, task.answer())
        if not (isinstance(task, MixedTextFillInTask) and task.is_mixed()):
            # When the inputfield is emeded within the text, it is confusing to
            # have the prompt marked as a label.  Morover some screeen-readers
            # (JAWs) are confused too and present the task incorrectly.
            prompt = _html.label(prompt, self._task_name(task))
        return self._TASK_FORMAT % (prompt, text)
                               
        
    
class VocabExercise(_FillInExercise, _NumberedTasksExercise):
    """A small text-field for each vocabulary item on a separate row."""

    _NAME = _("Test Yourself")
    _TASK_FORMAT = "%s %s"
    _INSTRUCTIONS = _("Fill in the correct translation for each "
                      "of the terms below.")

    def _check_tasks(self, tasks):
        if not tasks:
            dict = {}
            for item in self._parent.vocab:
                translation = item.translation()
                if translation:
                    words, media = dict.get(translation, ([], []))
                    if item.word() in words:
                        continue
                    words.append(item.word())
                    media.append(item.media())
                    dict[translation] = (words, media)
            tasks = [FillInTask(t, '|'.join(x[0]), media=x[1])
                     for t, x in dict.items()]
        return tasks    


class Substitution(_FillInExercise, _NumberedTasksExercise):
    """A prompt (a sentence) and a big text-field for each task."""

    _NAME = _("Substitution")
    _INSTRUCTIONS = _("Use the text in brackets to transform each sentence.")
    

class Transformation(_FillInExercise, _NumberedTasksExercise):
    """Pairs of sentences, the later with a gap (text-field)."""


    _NAME = _("Transformation")
    _TASK_TYPE = TransformationTask
    _TASK_FORMAT = "A. %s<br/>B. %s"
    _INSTRUCTIONS = _("Fill in the gap in sentence B so that it means the "
                      "same as sentence A.")
    
    def _instructions(self):
        if self._example:
            return _("Using the example as a model, change the structure "
                     "and make a new sentence.")
        else:
            return self._INSTRUCTIONS

        
class Dictation(_FillInExercise):
    """One big text-field for a whole exercise."""

    _NAME = _("Dictation")
    _TASK_TYPE = DictationTask
    _FORM_HANDLER = 'DictationHandler'
    _RECORDING_REQUIRED = True
    _MESSAGES = {'Correct': _('Correct'),
                 'Error(s) found': _('Error(s) found')}
    _MESSAGES.update(_FillInExercise._MESSAGES)
    _INDICATORS = (('result', _('Result:')),)
    
    _INSTRUCTIONS = _("""Listen to the complete recording first.  Then go to
    the textbox and use the > key to listen to the text section by section.
    Type what you hear into the textbox.  For detailed instructions, read the
    Exercise Help.""")

    def __init__(self, parent, tasks, pieces=None, **kwargs):
        if pieces is not None:
            media = parent.resource(Media, pieces)
            if not isinstance(media, (types.ListType, types.TupleType)):
                media = ()
            self._pieces = media
        else:
            self._pieces = None
        super(Dictation, self).__init__(parent, tasks, **kwargs)

    def _check_tasks(self, tasks):
        assert len(tasks) == 1
        return tasks
    
    def _transcript_text(self):
        return self._tasks[0].answer()

    def _export_task_parts(self, exporter, task):
        return '<textarea rows="10" cols="60"></textarea>'
        
    def _init_script(self):
        init_script = super(Dictation, self)._init_script()
        if self._pieces:
            init_script += "handler.init_recordings(%s);" % \
                           _html.js_array([m.url() for m in self._pieces])
        return init_script
    

class _Cloze(_FillInExercise):
    _NAME = _("Cloze")
    _TASK_TYPE = ClozeTask
    _INSTRUCTIONS = _("Fill in the gaps in the text below. "
                      "For each gap there is only one correct answer.")
    
    def _transcript_text(self):
        return "\n\n".join([t.plain_text() for t in self._tasks])
    
    def _instructions(self):
        if self._recording is not None:
            return _("Listen to the recording carefully and then fill in the "
                     "gaps in the text below using the same words.")
        else:
            return self._INSTRUCTIONS

    def _export_task_parts(self, exporter, task):
        formatter = lambda t: exporter.format_wiki_text(self.parent(), t)
        return task.text(self._make_field, formatter)


class _ExposedCloze(_Cloze):
    _NAME = _("Exposed Cloze")
    _INSTRUCTIONS = _("Use the correct word or expression from the list below "
                      "to fill in the gaps in the sentences.")

    def _export_instructions(self, exporter):
        answers = self._answers()
        answers.sort()
        instr = super(_ExposedCloze, self)._export_instructions(exporter)
        return instr + _html.list(answers)

    
class NumberedCloze(_Cloze, _NumberedTasksExercise):
    pass

    
class NumberedExposedCloze(NumberedCloze, _ExposedCloze):
    pass
    

class Cloze(_Cloze):
    """Paragraphs of text including text-fields for the marked words."""

    # Here we want an answer-sheet link per field (see _maike_field).
    # Tasks and answers are not 1:1.
    _ANSWER_SHEET_LINK_PER_TASK = False

    def _check_tasks(self, tasks):
        assert len(tasks) == 1
        return tasks
    
    def _answers(self):
        return self._tasks[0].answers()
        
    def _answer_sheet_items(self):
        t = self._tasks[0]
        return zip(t.answers(), t.comments())

    def _make_field(self, task, text):
        try:
            counter = self._field_counter
        except AttributeError:
            counter = self._field_counter = Counter(0)
        n = counter.next()
        name = self._exercise_id() + '-f%d' % n
        field = _html.field(name=name,
                            size=max(4, len(text)+1), cls='fill-in-task')
        return field + self._answer_sheet_link(n-1)

    def _export_task_parts(self, exporter, task):
        # The formatter here actually works as a parser and formatter.
        formatter = lambda t: self._wiki_content(t).export(exporter)
        return task.text(self._make_field, formatter)
    
class ExposedCloze(Cloze, _ExposedCloze):
    pass
