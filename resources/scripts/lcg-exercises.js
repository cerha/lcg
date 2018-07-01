/* -*- coding: utf-8 -*-
 *
 * Copyright (C) 2004-2017 OUI Technology Ltd.
 * Copyright (C) 2019 Tomáš Cerha <t.cerha@gmail.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
 * USA */

/* eslint no-unused-vars: 0 */
/* global $, Class, Effect, lcg */

"use strict";

// JavaScript support for interactive LCG Tests and Exercises

lcg.Exercise = Class.create(lcg.KeyHandler, {
    /* Generic exercise handler class.
     */

    initialize: function ($super, exercise_id, answers, responses, messages) {
        $super();
        this._form = $(exercise_id);
        this._answers = answers;
        this._responses = responses;
        this._messages = messages;
        this._results = [];
        this._first_attempt = [];
        this._fields = [];
        this._last_answer_index = 0;
        var i, field;
        for (i=0; i < this._form.elements.length; i++) {
            field = this._form.elements[i];
            if (this._recognize_field(field)) {
                this._init_field(field);
                this._fields.push(field);
            }
        }
        [
            ['.evaluate-button', this._on_evaluate_button],
            ['.fill-button', this._on_fill_button],
            ['.reset-button', this._on_reset_button]
        ].each(function (x) {
            var button = this._form.down(x[0]);
            if (button) {
                button.observe('click', x[1].bind(this));
            }
        }.bind(this));
    },

    response: function (selector) {
        var responses = this._responses[selector];
        var n = Math.floor(Math.random() * responses.length);
        return responses[n];
    },

    _msg: function (text) {
        if (text in this._messages)
            return this._messages[text];
        else
            return text;
    },

    _set_answer: function (i, value) {
        this._fields[i].value = value;
    },

    _get_value: function (i) {
        return this._fields[i].value;
    },

    _error_handler: function (field) {
        field.focus();
    },

    _eval_answers: function () {
        var i, value;
        for (i=0; i < this._answers.length; i++) {
            value = this._get_value(i);
            if (value !== '' && value !== undefined) {
                this._results[i] = (this._eval_answer(value, i) ? 1 : -1);
                if (this._first_attempt[i] === undefined)
                    this._first_attempt[i] = this._results[i];
            } else {
                this._results[i] = undefined;
            }
        }
        this._display_results();
    },

    _eval_answer: function (value, i) {
        return value == this._answers[i];
    },

    _on_eval_answer: function (event) {
        this._eval_field_answer(event.element());
    },

    _eval_field_answer: function (field) {
        this._eval_answers();
        var i = field.answer_index;
        var result = this._results[i];
        if (result !== undefined) {
            this._play_audio(this.response(result === 1 ? 'correct':'incorrect'));
            if (result === 1) {
                // if (i < this._fields.length)
                //    This doesn't work in MultipleChoiceQuestions (answer index is not
                //    a field index).  But we probably don't want it anyway...
                //    this._fields[i+1].focus();
            } else {
                this._error_handler(field);
            }
        }
    },

    _on_evaluate_button: function (event) {
        var i, field;
        this._eval_answers();
        for (i=0; i < this._fields.length; i++) {
            field = this._fields[i];
            if (this._results[field.answer_index] !== 1) {
                this._error_handler(field);
                break;
            }
        }
        var response;
        if (this._fields.length > 1) {
            var percentage = this._percentage();
            if      (percentage < 50)  response='poor';
            else if (percentage < 70)  response='sufficient';
            else if (percentage < 85)  response='good';
            else if (percentage < 100) response='excellent';
            else response='perfect';
        } else {
            response = this._correct() ? 'correct':'incorrect';
        }
        this._play_audio(this.response(response));
    },

    _count: function (array, value) {
        // Return the count of elements having the given value in the array.
        var i, count = 0;
        for (i=0; i<array.length; i++)
            if (array[i] === value) count++;
        return count;
    },

    _correct: function () {
        return this._count(this._results, 1);
    },

    _percentage: function () {
        return Math.round(100 * this._correct() / this._answers.length);
    },

    _display_results: function () {
        var count = this._answers.length;
        var correct = this._correct();
        var incorrect = this._count(this._results, -1);
        var first_attempt_correct = this._count(this._first_attempt, 1);
        var first_attempt_percentage = Math.round(100 * first_attempt_correct / count);
        this._form.answered.value = (correct+incorrect) +'/'+ count;
        var result = correct + "/" + count + " ("+ this._percentage() +"%)";
        if (correct !== first_attempt_correct) {
            result += ", "+ first_attempt_correct +" ("+ first_attempt_percentage +"%) "+
                this._msg("on first attempt");
        }
        this._form.result.value = result;
    },

    _fill_answer: function (i) {
        this._set_answer(i, this._answers[i]);
    },

    _on_fill_button: function (event) {
        var i;
        for (i=0; i < this._answers.length; i++) {
            this._fill_answer(i);
        }
        this._eval_answers();
    },

    _on_reset_button: function (event) {
        this._results = [];
        this._first_attempt = [];
        this._display_results();
    },

    _slide_up: function (element, duration) {
        if (Effect !== undefined) {
            if (duration === 'undefined') {
                duration = 0.2;
            }
            new Effect.SlideUp(element, {duration: duration});
        } else {
            element.hide();
        }
    },

    _slide_down: function (element, duration) {
        if (Effect !== undefined) {
            if (duration === undefined)
                duration = 0.2;
            new Effect.SlideDown(element, {duration: duration});
        } else {
            element.show();
        }
    },

    _play_audio: function (uri) {
        if (!lcg.audio && typeof Audio !== 'undefined') {
            lcg.audio = new Audio();
        }
        var audio = lcg.audio;
        if (audio) {
            if (audio.src !== uri) {
                audio.src = uri;
                audio.load();
            }
            audio.play();
        }
    }

});

//=============================================================================
// Choice based exercise handler class.

lcg.ChoiceBasedExercise = Class.create(lcg.Exercise, {

    _recognize_field: function (field) {
        return field.type === 'radio';
    },

    _init_field: function (field) {
        if (field.name !== this._last_group) {
            if (this._last_group !== undefined) {
                this._last_answer_index++;
            }
            this._last_group = field.name;
        }
        field.answer_index = this._last_answer_index;
        field.observe('click', this._on_eval_answer.bind(this));
    },

    _set_answer: function (i, value) {
        var n;
        for (n=0; n < this._fields.length; n++) {
            var field = this._fields[n];
            if (field.answer_index === i) {
                field.checked = (field.value === value.toString());
            }
        }
    },

    _get_value: function (i) {
        var field;
        for (var n=0; n < this._fields.length; n++) {
            field = this._fields[n];
            if (field.answer_index === i && field.checked) {
                return parseInt(field.value);
            }
        }
        return undefined;
    },

    _error_handler: function (field) {
        var n, i = field.answer_index;
        for (n=0; n < this._fields.length; n++) {
            var f = this._fields[n];
            if (f.answer_index === i && f.checked) {
                f.focus();
                return;
            }
        }
        field.focus();
    }

});


lcg.SelectBasedExercise = Class.create(lcg.Exercise, {

    _recognize_field: function (field) {
        return field.options !== undefined;
    },

    _init_field: function (field) {
        field.answer_index = this._last_answer_index++;
        field.observe('change', this._on_eval_answer.bind(this));
    },

    _set_answer: function (i, value) {
        var j, field = this._fields[i];
        for (j=0; j < field.options.length; j++) {
            var option = field.options[j];
            if (option.value === value)
                option.selected = true;
        }
    }

});


lcg.FillInExercise = Class.create(lcg.Exercise, {

    _define_keymap: function () {
        return {
            'Enter': this._cmd_eval_answer,
            'Alt-Space': this._cmd_hint,
            'Ctrl-Space': this._cmd_hint
        };
    },

    _cmd_eval_answer: function (event, field) {
        this._eval_field_answer(field);
    },

    _cmd_hint: function (event, field) {
        var found = this._find_answer(field);
        var answer = found.answer;
        var i = found.index;
        var val = field.value;
        if (answer.length > i) {
            field.value = answer.slice(0, i+1) + val.slice(i, val.length);
            this._highlight(field, i+1, i+1);
        } else if (field.value.length > i) {
            field.value = val.slice(0, i);
            this._highlight(field, i, i);
        }
        return false;
    },

    _recognize_field: function (field) {
        return ((field.type === 'text' || field.type === 'textarea') &&
                this._last_answer_index < this._answers.length);
    },

    _init_field: function (field) {
        field.answer_index = this._last_answer_index++;
        field.observe('keydown', this._on_key_down.bind(this));
        field.observe('dblclick', this._on_eval_answer.bind(this));
        field.observe('touchstart', this._on_touch_start.bind(this));
    },

    _on_touch_start: function (event) {
        // This is necessary in iBooks on iPhone/iPad as iBooks probably makes all
        // text fields ineditable by default so the keyboard doesnt show up when
        // the field is touched to type.
        var element = event.element();
        if (element.disabled)
            element.disabled = false;
        element.focus();
        event.stop();
    },

    _find_answer: function (field) {
        var answers = this._answers[field.answer_index].split('|');
        var value = field.value;
        var answer_index = 0;
        var char_index = 0; // max last correct char index
        var i, a, j;
        for (i=0; i < answers.length; i++) {
            a = answers[i];
            j = 0;
            while (value.slice(0, j+1) === a.slice(0, j+1) && j < a.length) j++;
            if (j > char_index) {
                char_index = j;
                answer_index = i;
            }
        }
        return {"answer": answers[answer_index], "index": char_index};
    },

    _highlight: function (field, start, end) {
        if (field.setSelectionRange) {
            field.focus();
            field.setSelectionRange(start, end);
        } else if (field.createTextRange) {
            var range = field.createTextRange();
            range.collapse(true);
            range.moveEnd('character', end);
            range.moveStart('character', start);
            range.select();
        }
    },

    _error_handler: function (field) {
        var found = this._find_answer(field);
        var index = found.index;
        field.focus();
        this._highlight(field, index, index);
    },

    _eval_answer: function (value, i) {
        var j, answers = this._answers[i].split('|');
        for (j=0; j < answers.length; j++) {
            // Replace repeated spaces, newlines and tabs with a single space
            if (value.replace(/^\s*|\s(?=\s)|\s*$/g, "") === answers[j])
                return true;
        }
        return false;
    },

    _fill_answer: function (i) {
        var answers = this._answers[i].split('|');
        this._set_answer(i, answers[0]);
    }

});


lcg.HiddenAnswers = Class.create(lcg.Exercise, {

    initialize: function ($super, form_name, answers, responses, messages) {
        $super(form_name, answers, responses, messages);
        this._form.select('.toggle-button').each(function (b) {
            b.observe('click', this._on_toggle_button.bind(this));
        }.bind(this));
    },

    _recognize_field: function (field) {
        return false;
    },

    _show_answer: function (answer) {
        this._slide_down(answer);
        answer.up('.task').down('.toggle-button').update(this._msg("Hide Answer"));
    },

    _hide_answer: function (answer) {
        this._slide_up(answer);
        answer.up('.task').down('.toggle-button').update(this._msg("Show Answer"));
    },

    _on_toggle_button: function (event) {
        var answer = event.element().up('.task').down('.answer');
        if (answer.visible())
            this._hide_answer(answer);
        else
            this._show_answer(answer);
    },

    _on_evaluate_button: function (event) {
        this._form.select('.answer').each(function (a) {
            this._show_answer(a);
        }.bind(this));
    },

    _on_reset_button: function (event) {
        this._form.select('.answer').each(function (a) {
            this._hide_answer(a);
        }.bind(this));
    }

});


lcg.ModelCloze = Class.create(lcg.Exercise, {

    initialize: function ($super, form_name, answers, responses, messages) {
        $super(form_name, answers, responses, messages);
        this._form.down('.model-answers').hide();
    },

    _recognize_field: function (field) {
        return false;
    },

    _on_evaluate_button: function (event) {
        this._form.down('.model-answers').show();
    },

    _on_reset_button: function (event) {
        this._form.down('.model-answers').hide();
    }

});


lcg.Dictation = Class.create(lcg.FillInExercise, {

    initialize: function ($super, form_name, answers, responses, messages, recordings) {
        $super(form_name, answers, responses, messages);
        this._recordings = recordings;
        this._current_recording = -1;
    },

    _define_keymap: function () {
        return {
            'Enter': this._cmd_eval_answer,
            'Ctrl-Space': this._cmd_hint,
            '>': this._cmd_play_next,
            '<': this._cmd_play_previous,
            'Ctrl-Enter': this._cmd_play_current
        };
    },

    _cmd_play_next: function (event, field) {
        if (this._current_recording < this._recordings.length-1) {
            this._current_recording++;
            this._cmd_play_current(event, field);
        }
    },

    _cmd_play_previous: function (event, field) {
        if (this._current_recording > 0) {
            this._current_recording--;
            this._cmd_play_current(event, field);
        }
    },

    _cmd_play_current: function (event, field) {
        this._play_audio(this._recordings[this._current_recording]);
    },

    _display_results: function () {
        var msg = this._msg(this._correct() ? 'Correct':'Error(s) found');
        this._form.result.value = msg;
    }

});
