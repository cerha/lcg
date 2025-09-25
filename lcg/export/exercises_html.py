# -*- coding: utf-8 -*-

# Copyright (C) 2004-2017 OUI Technology Ltd.
# Copyright (C) 2019-2020 Tomáš Cerha <t.cerha@gmail.com>
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

from __future__ import unicode_literals

import re
import lcg
from lcg import concat

_ = lcg.TranslatableTextFactory('lcg-exercises')

unistr = type(u'')  # Python 2/3 transition hack.


class ExerciseExporter(object):
    _JAVASCRIPT_CLASS = 'lcg.Exercise'
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
                      u"successfully on the first try.  Use the ‘Reset’ button to start "
                      "again.")))
    _BUTTONS = ((_("Evaluate"), 'button', 'evaluate-button',
                 _("Evaluate the entire exercise.  If an error is found, the cursor is moved to "
                   "the first incorrect answer.  Within a text box, the cursor is also moved to "
                   "the first incorrect character of your answer.")),
                # Translators: Fill (a form with correct answers).
                (_('Fill'), 'button', 'fill-button',
                 _("Fill in the whole exercise with the correct answers.")),
                (_('Reset'), 'reset', 'reset-button',
                 _("Reset all your answers and start again.")))

    # Class methods

    @classmethod
    def help(cls):
        sections = [lcg.Section(title=title, id=section_id, content=lcg.coerce(content))
                    for title, section_id, content in
                    ((_("Instructions"), 'intro', cls._EXERCISE_CLASS.help_intro()),
                     (_("Shortcut Keys"), 'keys', cls._help_keys()),
                     (_("Indicators"), 'indicators', cls._help_indicators()),
                     (_("Control Panel"), 'panel', cls._help_panel()))
                    if content is not None]
        return lcg.Container(sections)

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
                    lcg.dl([(label, hlp) for label, t, name, hlp in cls._BUTTONS]))
        else:
            return None

    # Instance methods

    def _readonly(self, context):
        return False

    def _has_real_answers(self, exercise):
        """Return true if the exersice defines the correct answers.

        If the correct answers are unknown, the exercise will not offer
        automatic evaluation.

        """
        return True

    def _media_control(self, context, media):
        g = context.generator()
        button_id = context.unique_id()
        context.bind_audio_control(button_id, context.uri(media))
        return g.button(_("Play"), id=button_id, cls='media-control')

    def _export_tasks(self, context, exercise, exercise_id):
        exported_tasks = [context.localize(self._export_task(context, exercise, exercise_id, task))
                          for task in exercise.tasks()]
        template = exercise.template()
        if template:
            localized_template = context.localize(template.export(context))
            return localized_template % tuple(exported_tasks)
        else:
            if len(exported_tasks) > 1:
                g = context.generator()
                return g.ol([g.li(t) for t in exported_tasks], cls="tasks")
            elif exported_tasks:
                return exported_tasks[0]
            else:
                return None

    def _export_instructions(self, context, exercise, exercise_id):
        instructions = exercise.instructions()
        if instructions:
            return context.generator().div(instructions.export(context))
        else:
            return None

    def _export_script(self, context, exercise, exercise_id):
        g = context.generator()
        responses = {}
        lang = context.lang()
        for key in ('correct', 'incorrect', 'poor', 'sufficient', 'good', 'excellent', 'perfect'):
            filename = 'exercise-responses/%s/%s-*.mp3' % (lang, key)
            media = context.resource(filename)
            if media is None:
                media = (lcg.Media(filename),)
            elif isinstance(media, lcg.Media):
                media = (media,)
            responses[key] = [context.uri(m) for m in media]
        return g.js_call('new %s' % self._JAVASCRIPT_CLASS,
                         exercise_id, exercise.answers(), responses,
                         dict([(msg, context.localize(translation))
                               for msg, translation in list(self._MESSAGES.items())]))

    def _task_style_cls(self, exercise):
        return 'task %s-task' % lcg.camel_case_to_lower(exercise.__class__.__name__)

    def _export_task(self, context, exercise, exercise_id, task):
        parts = [p for p in self._export_task_parts(context, exercise, exercise_id, task)
                 if p is not None]
        return context.generator().div(parts, cls=self._task_style_cls(exercise))

    def _task_id(self, exercise, exercise_id, task):
        return exercise_id + '-t%d' % (exercise.tasks().index(task) + 1)

    def _export_results(self, context, exercise, exercise_id):
        g = context.generator()
        return g.div((g.div(concat([g.label(label, exercise_id + '.' + name) +
                                    g.input(type='text', name=name, id=exercise_id + '.' + name,
                                            size=30, readonly=True)
                                    for name, label, help in self._INDICATORS],
                                   separator=g.br()),
                            cls='display'),
                      g.div([g.button(label, type=t, cls=name, title=hlp)
                             for label, t, name, hlp in self._BUTTONS],
                            cls='buttons')),
                     cls='results')

    def _export_task_answer(self, context, exercise, exercise_id, task):
        return 'x'

    def _export_answers(self, context, exercise, exercise_id):
        g = context.generator()
        task_answers = [self._export_task_answer(context, exercise, exercise_id, task)
                        for task in exercise.tasks()]
        return g.div(_("Answers: %s", lcg.concat(*task_answers, separator=', ')),
                     cls='answers')

    def export(self, context, exercise):
        g = context.generator()
        exercise_id = context.unique_id()
        context.resource('lcg-exercises.css')
        has_real_answers = self._has_real_answers(exercise)
        allow_interactivity = context.allow_interactivity()
        if not has_real_answers:
            methods = (self._export_tasks,)
        elif not allow_interactivity:
            methods = (self._export_tasks,
                       self._export_answers)
        else:
            context.resource('prototype.js')
            context.resource('lcg.js')
            context.resource('lcg-exercises.js')
            context.resource('effects.js')
            context.resource('media.js')
            methods = (self._export_instructions,
                       self._export_tasks,
                       self._export_results)
        parts = [method(context, exercise, exercise_id) for method in methods]
        content = [x for x in parts if x is not None]
        if allow_interactivity and has_real_answers:
            script = self._export_script(context, exercise, exercise_id)
            if script:
                content = (g.form(content, id=exercise_id),
                           g.script(script))
        return g.div(content,
                     cls='exercise ' + lcg.camel_case_to_lower(exercise.__class__.__name__))


class _ChoiceBasedExerciseExporter(ExerciseExporter):
    "A superclass for all exercises based on choosing from predefined answers."

    _JAVASCRIPT_CLASS = 'lcg.ChoiceBasedExercise'

    def _has_real_answers(self, exercise):
        return all(t.correct_choice() is not None for t in exercise.tasks())

    def _checked(self, context, exercise, exercise_id, task, i):
        return False

    def _choice_text(self, context, exercise, exercise_id, task, choice):
        return choice.answer()

    def _choice_control(self, context, exercise, exercise_id, task, choice):
        g = context.generator()
        result = self._choice_text(context, exercise, exercise_id, task, choice)
        if context.allow_interactivity():
            i = task.choices().index(choice)
            task_name = self._task_id(exercise, exercise_id, task)
            choice_id = task_name + '-ch%d' % (i + 1)
            checked = self._checked(context, exercise, exercise_id, task, i)
            # Disable only the unchecked fields in the read-only mode.  This makes the selection
            # unchangable in practice and has also the advantage that the checked fields can be
            # navigated, which is even better than using the `readonly' attribute (which doesn't
            # work in browsers anyway).
            disabled = self._readonly(context) and not checked
            ctrl = g.radio(task_name, id=choice_id, value=i,
                           cls='answer-control', checked=checked, disabled=disabled)
            result = concat(ctrl, ' ', g.label(result, choice_id))
        return result

    def _format_choices(self, context, exercise, exercise_id, task):
        g = context.generator()
        return g.ol([g.li(self._choice_control(context, exercise, exercise_id, task, ch))
                     for ch in task.choices()],
                    cls='choices')

    def _task_style_cls(self, exercise):
        cls = super(_ChoiceBasedExerciseExporter, self)._task_style_cls(exercise)
        return cls + ' choice-based-task'

    def _export_task_parts(self, context, exercise, exercise_id, task):
        prompt = task.prompt()
        if prompt:
            prompt = context.localize(prompt.export(context))
        return (prompt, self._format_choices(context, exercise, exercise_id, task))

    def _export_task_answer_name(self, context, exercise, exercise_id, task):
        import string
        i = task.choice_index(task.correct_choice())
        return string.ascii_letters[i]

    def _export_task_answer(self, context, exercise, exercise_id, task):
        i = exercise.tasks().index(task)
        answer = self._export_task_answer_name(context, exercise, exercise_id, task)
        return lcg.format('%s. %s', i + 1, answer)


class MultipleChoiceQuestionsExporter(_ChoiceBasedExerciseExporter):
    pass


class SelectionsExporter(_ChoiceBasedExerciseExporter):
    pass


class TrueFalseStatementsExporter(_ChoiceBasedExerciseExporter):

    def _format_choices(self, context, exercise, exercise_id, task):
        if not context.allow_interactivity():
            return None
        g = context.generator()
        return g.div([g.div(self._choice_control(context, exercise, exercise_id, task, ch))
                      for ch in task.choices()],
                     cls='choices')

    def _export_task_answer_name(self, context, exercise, exercise_id, task):
        return task.correct_choice().answer()


class _SelectBasedExerciseExporter(_ChoiceBasedExerciseExporter):
    # Currently unused due to problematic accessibile interactive evaluation of
    # select boxes.
    _JAVASCRIPT_CLASS = 'lcg.SelectBasedExercise'

    def _format_choices(self, context, exercise, exercise_id, task):
        g = context.generator()
        task_name = self._task_id(exercise, exercise_id, task)
        return g.select(name=task_name, id=task_name, readonly=self._readonly(context),
                        content=[g.option(ch.answer(), value=task.choice_index(ch))
                                 for ch in task.choices()])


class GapFillingExporter(_ChoiceBasedExerciseExporter):

    _GAP_MATCHER = re.compile(r"(___+)")

    def _export_task_parts(self, context, exercise, exercise_id, task):
        g = context.generator()
        html = context.localize(task.prompt().export(context))
        return (g.span(g.noescape(self._GAP_MATCHER.sub(g.span("____", cls='exercise-gap'), html))),
                self._format_choices(context, exercise, exercise_id, task))


class HiddenAnswersExporter(ExerciseExporter):

    _JAVASCRIPT_CLASS = 'lcg.HiddenAnswers'
    _INDICATORS = ()

    _BUTTONS = ((_('Show All'), 'button', 'evaluate-button',
                 _("Show all answers.")),
                (_('Hide All'), 'button', 'reset-button',
                 _("Reset all your answers and start again.")))

    _MESSAGES = {"Show Answer": _("Show Answer"),
                 "Hide Answer": _("Hide Answer")}

    def _export_task_parts(self, context, exercise, exercise_id, task):
        g = context.generator()
        result = (g.div(task.prompt().export(context), cls='question'),)
        if context.allow_interactivity():
            result += (g.button(_("Show Answer"), cls='toggle-button',
                                title=_("Show/Hide the correct answer.")),
                       # The inner div is needed by the JavaScript effects library for
                       # the sliding effect.
                       g.div(g.div((g.span(_("Correct answer:"), cls='label'), ' ',
                                    task.answer().export(context))),
                             cls='answer', style='display: none;'))
        return result

    def _export_task_answer(self, context, exercise, exercise_id, task):
        i = exercise.tasks().index(task)
        return lcg.format('%s. %s', i + 1, task.answer().export(context))


class _FillInExerciseExporter(ExerciseExporter):
    """A common base class for exercises based on writing text into fields."""

    _JAVASCRIPT_CLASS = 'lcg.FillInExercise'
    _UNKNOWN_ANSWER_REGEXP = re.compile(r'(_+|\?\?+)')

    @classmethod
    def _help_keys(cls):
        return (lcg.p(_("In all the exercises where you fill in the text into a text box "
                        "you can use the two shortcut keys described below.")),
                lcg.dl(((_("Enter"),
                         _("Use this key within the text field to evaluate the current answer. "
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

    def _has_real_answers(self, exercise):
        return all(not self._UNKNOWN_ANSWER_REGEXP.match(a) for a in exercise.answers())

    def _export_task_text(self, context, exercise, exercise_id, task):
        g = context.generator()

        def make_field(answer, label, word_start, word_end):
            field, field_id = self._make_field(context, exercise, exercise_id, task, answer)
            if word_start or word_end:
                return g.span(g.noescape(word_start + field + word_end), cls='nowrap')
            else:
                return field
        text = task.text().replace('[', r'\[')
        if text:
            content = lcg.Parser().parse_inline_markup(text)
            html = context.localize(content.export(context))
        else:
            html = ''
        return g.noescape(task.substitute_fields(html, make_field))

    def _field_value(self, context, field_id):
        return ''

    def _field_cls(self, context, field_id, text):
        return 'fill-in-task'

    def _field_result(self, context, field_id, text):
        return ''

    def _make_field(self, context, exercise, exercise_id, task, text):
        g = context.generator()
        self._field_number += 1
        field_id = self._task_id(exercise, exercise_id, task) + '-f%d' % self._field_number
        size = len(text)
        if size >= 2 and text == (size * '?'):
            # If the box contains just question marks, it means an unknown answer of one
            # word (two question marks) or one sencence (three or more question marks).
            size = 10 if size == 2 else 50
        if not context.allow_interactivity():
            field = g.span('_' * size, title=text,
                           cls=self._field_cls(context, field_id, text))
        else:
            field = concat(
                g.input(type='text', name=field_id, id=field_id, size=size,
                        value=self._field_value(context, field_id),
                        readonly=self._readonly(context),
                        # Set the width through CSS. Otherwise the fields are too wide in FF.
                        style='box-model: content-box; width: %dem;' % size,
                        cls=self._field_cls(context, field_id, text)),
                [self._media_control(context, m) for m in task.media()],
                self._field_result(context, field_id, text)
            )
        return (context.localize(field), field_id)

    def _export_fill_in_task(self, context, prompt, text):
        if prompt:
            return prompt + context.generator().br() + text
        else:
            return text

    def _export_task_parts(self, context, exercise, exercise_id, task):
        g = context.generator()
        self._field_number = 0
        if task.prompt():
            prompt = context.localize(task.prompt().export(context))
        else:
            prompt = None
        if task.has_fields_in_text():
            text = self._export_task_text(context, exercise, exercise_id, task)
            # When the inputfield is embeded within the text, it is confusing to
            # have the prompt marked as a label.  Morover some screeen-readers
            # (JAWs) are confused too and present the task incorrectly.
        else:
            text, field_id = self._make_field(context, exercise, exercise_id, task, task.text())
            if prompt:
                prompt = g.label(prompt, field_id)
        return (self._export_fill_in_task(context, prompt, text),)

    def _export_task_answer(self, context, exercise, exercise_id, task):
        answer = ', '.join(task.answers())
        if len(exercise.tasks()) > 1:
            i = exercise.tasks().index(task)
            answer = lcg.format('%s. %s', i + 1, answer)
        return answer


class VocabExerciseExporter(_FillInExerciseExporter, ExerciseExporter):

    def _export_fill_in_task(self, context, prompt, text):
        return prompt + ' ' + text


class WrittenAnswersExporter(_FillInExerciseExporter):
    pass


class NumberedClozeExporter(_FillInExerciseExporter):
    pass


class ClozeExporter(NumberedClozeExporter):
    pass


class ModelClozeExporter(ClozeExporter):
    _JAVASCRIPT_CLASS = 'lcg.ModelCloze'
    _INDICATORS = ()

    _BUTTONS = ((_('Show Answers'), 'button', 'evaluate-button',
                 _("Show model answers.")),
                (_('Reset'), 'reset', 'reset-button',
                 _("Reset all your answers and start again.")))

    _MESSAGES = {"Show Answer": _("Show Answer"),
                 "Hide Answer": _("Hide Answer")}

    def _export_tasks(self, context, exercise, exercise_id):
        result = super(ModelClozeExporter, self)._export_tasks(context, exercise, exercise_id)
        if context.allow_interactivity():
            g = context.generator()

            def make_field(answer, label, word_start, word_end):
                field = g.span(answer, cls='model-answer')
                if word_start or word_end:
                    return g.span(g.noescape(word_start + field + word_end), cls='nowrap')
                else:
                    return field

            def export_task(task):
                text = task.text().replace('[', r'\[')
                if text:
                    content = lcg.Parser().parse_inline_markup(text)
                    html = context.localize(content.export(context))
                else:
                    html = ''
                return g.noescape(task.substitute_fields(html, make_field))
            result += g.div([export_task(task) for task in exercise.tasks()], cls='model-answers')
        return result


################################################################################
##################################   Tests   ###################################
################################################################################

class _TestExporter(object):
    """Tests are similar to exercises, but instead of practise, they are used for testing.

    It would be more logical to derive exercises from tests, since tests are simpler (they are not
    interactive).  Due to historical reasons, however, they are implemented by overriding
    exercises and leaving out everything, what is not necesarry...

    """

    def _export_script(self, context, exercise, exercise_id):
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

    def _export_results(self, context, exercise, exercise_id):
        if not self._show_results(context):
            return None
        g = context.generator()
        points = self.eval(context.req())
        # TODO: Display invalid value of entered added points within tutor's evaluation
        # (to let the tutor fix it).
        added = self.added_points(context.req())
        max = self.max_points()

        def field(label, name, value, size=6, readonly=True, **kwargs):
            field_id = exercise_id + '-' + name
            return (g.label(label, field_id) + ' ' +
                    g.input(type='text', name=id, value=value, id=field_id, size=size,
                            readonly=readonly, cls=(readonly and 'display' or None), **kwargs))
        if points < max and isinstance(self, FillInTestExporter):
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
        return g.div(concat(fields, separator=g.br()), cls='results')

    def _readonly(self, context):
        return self._show_results(context)


class ChoiceBasedTestExporter(_TestExporter, _ChoiceBasedExerciseExporter):

    def _checked(self, context, exercise, exercise_id, task, i):
        task_name = self._task_id(exercise, exercise_id, task)
        return self._param(context.req(), task_name, False) == unistr(i)

    def _choice_text(self, context, exercise, exercise_id, task, choice):
        text = super(ChoiceBasedTestExporter, self)._choice_text(context, exercise, exercise_id,
                                                                 task, choice)
        if self._show_results(context):
            result = None
            if choice.correct():
                result = _("correct answer")
            else:
                name = self._task_id(exercise, exercise_id, task)
                if self._param(context.req(), name) == unistr(task.choices().index(choice)):
                    # Translators: Incorrect (answer)
                    result = _("incorrect")
            if result:
                g = context.generator()
                text += ' ' + g.span(('(', result, ')'), cls='test-answer-comment')
        return text

    def _choice_control(self, context, exercise, exercise_id, task, choice):
        result = super(ChoiceBasedTestExporter, self)._choice_control(context, exercise,
                                                                      exercise_id, task, choice)
        if self._show_results(context):
            name = self._task_id(exercise, exercise_id, task)
            if self._param(context.req(), name) == unistr(task.choices().index(choice)):
                cls = choice.correct() and 'correct-answer' or 'incorrect-answer'
            else:
                cls = 'non-selected-answer'
            result = context.generator().span(result, cls=cls)
        return result


class FillInTestExporter(_TestExporter, _FillInExerciseExporter):

    def _field_value(self, context, name):
        return self._param(context.req(), name, "")

    def _field_cls(self, context, name, text):
        cls = super(FillInTestExporter, self)._field_cls(context, name, text)
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


class WritingTestExporter(FillInTestExporter):

    def _export_task_parts(self, context, exercise, exercise_id, task):
        g = context.generator()
        name = self._task_id(exercise, exercise_id, task)
        return (g.textarea(self._field_value(context, name), name=name,
                           rows=10, cols=60, readonly=self._readonly(context),
                           cls=self._field_cls(context, name, task.answer())),
                self._field_result(context, name, task.answer()))

    def _field_result(self, context, name, text):
        return ''
