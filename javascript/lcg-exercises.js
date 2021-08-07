/* -*- coding: utf-8 -*-
 *
 * Copyright (C) 2004-2017 OUI Technology Ltd.
 * Copyright (C) 2019, 2021 Tomáš Cerha <t.cerha@gmail.com>
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
/* global $, lcg */

"use strict"

// JavaScript support for interactive LCG Tests and Exercises


lcg.Exercise = class extends lcg.Widget {
    /* Generic exercise handler class. */

    constructor(exercise_id, answers, responses, messages) {
        super(exercise_id)
        this._form = this.element[0]
        this._answers = answers
        this._responses = responses
        this._messages = messages
        this._results = []
        this._first_attempt = []
        this._last_answer_index = 0
        this._fields = [...this._form.elements].filter(this._recognize_field.bind(this))
        for (const field of this._fields) {
            this._init_field(field)
        }
        const callbacks = [
            ['.evaluate-button', this._on_evaluate_button],
            ['.fill-button', this._on_fill_button],
            ['.reset-button', this._on_reset_button]
        ]
        for (const [selector, callback] of callbacks) {
            this.element.find(selector).on('click', callback.bind(this))
        }
    }

    response(selector) {
        const responses = this._responses[selector]
        const n = Math.floor(Math.random() * responses.length)
        return responses[n]
    }

    _msg(text) {
        if (text in this._messages)
            return this._messages[text]
        else
            return text
    }

    _set_answer(i, value) {
        this._fields[i].value = value
    }

    _get_value(i) {
        return this._fields[i].value
    }

    _error_handler(field) {
        field.focus()
    }

    _eval_answers() {
        for (let i=0; i < this._answers.length; i++) {
            const value = this._get_value(i)
            if (value !== '' && value !== undefined) {
                this._results[i] = (this._eval_answer(value, i) ? 1 : -1)
                if (this._first_attempt[i] === undefined)
                    this._first_attempt[i] = this._results[i]
            } else {
                this._results[i] = undefined
            }
        }
        this._display_results()
    }

    _eval_answer(value, i) {
        return value == this._answers[i]
    }

    _on_eval_answer(event) {
        this._eval_field_answer(event.target)
    }

    _eval_field_answer(field) {
        this._eval_answers()
        const i = field.answer_index
        const result = this._results[i]
        if (result !== undefined) {
            this._play_audio(this.response(result === 1 ? 'correct':'incorrect'))
            if (result === 1) {
                // if (i < this._fields.length)
                //    This doesn't work in MultipleChoiceQuestions (answer index is not
                //    a field index).  But we probably don't want it anyway...
                //    this._fields[i+1].focus()
            } else {
                this._error_handler(field)
            }
        }
    }

    _on_evaluate_button(event) {
        this._eval_answers()
        for (const field of this._fields) {
            if (this._results[field.answer_index] !== 1) {
                this._error_handler(field)
                break
            }
        }
        let response
        if (this._fields.length > 1) {
            const percentage = this._percentage()
            if      (percentage < 50)  response='poor'
            else if (percentage < 70)  response='sufficient'
            else if (percentage < 85)  response='good'
            else if (percentage < 100) response='excellent'
            else response = 'perfect'
        } else {
            response = this._correct() ? 'correct' : 'incorrect'
        }
        this._play_audio(this.response(response))
    }

    _count(array, value) {
        // Return the count of elements having the given value in the array.
        let count = 0
        for (const item of array) {
            if (item === value) {
                count++
            }
        }
        return count
    }

    _correct() {
        return this._count(this._results, 1)
    }

    _percentage() {
        return Math.round(100 * this._correct() / this._answers.length)
    }

    _display_results() {
        const count = this._answers.length
        const correct = this._correct()
        const incorrect = this._count(this._results, -1)
        const first_attempt_correct = this._count(this._first_attempt, 1)
        const first_attempt_percentage = Math.round(100 * first_attempt_correct / count)
        this._form.answered.value = (correct+incorrect) +'/'+ count
        let result = correct + "/" + count + " ("+ this._percentage() +"%)"
        if (correct !== first_attempt_correct) {
            result += ", "+ first_attempt_correct +" ("+ first_attempt_percentage +"%) "+
                this._msg("on first attempt")
        }
        this._form.result.value = result
    }

    _fill_answer(i) {
        this._set_answer(i, this._answers[i])
    }

    _on_fill_button(event) {
        for (let i=0; i < this._answers.length; i++) {
            this._fill_answer(i)
        }
        this._eval_answers()
    }

    _on_reset_button(event) {
        this._results = []
        this._first_attempt = []
        this._display_results()
    }

    _slide_up(element, duration) {
        if (Effect !== undefined) {
            if (duration === 'undefined') {
                duration = 0.2
            }
            new Effect.SlideUp(element, {duration: duration})
        } else {
            element.hide()
        }
    }

    _slide_down(element, duration) {
        if (Effect !== undefined) {
            if (duration === undefined)
                duration = 0.2
            new Effect.SlideDown(element, {duration: duration})
        } else {
            element.show()
        }
    }

    _play_audio(uri) {
        if (!lcg.audio && typeof Audio !== 'undefined') {
            lcg.audio = new Audio()
        }
        const audio = lcg.audio
        if (audio) {
            if (audio.src !== uri) {
                audio.src = uri
                audio.load()
            }
            audio.play()
        }
    }

}
//=============================================================================
// Choice based exercise handler class.

lcg.ChoiceBasedExercise = class extends lcg.Exercise {

    _recognize_field(field) {
        return field.type === 'radio'
    }

    _init_field(field) {
        if (field.name !== this._last_group) {
            if (this._last_group !== undefined) {
                this._last_answer_index++
            }
            this._last_group = field.name
        }
        field.answer_index = this._last_answer_index
        $(field).on('click', this._on_eval_answer.bind(this))
    }

    _set_answer(i, value) {
        for (let n=0; n < this._fields.length; n++) {
            const field = this._fields[n]
            if (field.answer_index === i) {
                field.checked = (field.value === value.toString())
            }
        }
    }

    _get_value(i) {
        for (const field of this._fields) {
            if (field.answer_index === i && field.checked) {
                return parseInt(field.value)
            }
        }
        return undefined
    }

    _error_handler(field) {
        const i = field.answer_index
        for (const f of this._fields) {
            if (f.answer_index === i && f.checked) {
                f.focus()
                return
            }
        }
        field.focus()
    }

}

lcg.SelectBasedExercise = class extends lcg.Exercise {

    _recognize_field(field) {
        return field.options !== undefined
    }

    _init_field(field) {
        field.answer_index = this._last_answer_index++
        $(field).on('change', this._on_eval_answer.bind(this))
    }

    _set_answer(i, value) {
        for (const option of this._fields[i].options) {
            if (option.value === value) {
                option.selected = true
            }
        }
    }

}

lcg.FillInExercise = class extends lcg.Exercise {

    _define_keymap() {
        return {
            'Enter': this._cmd_eval_answer,
            'Alt-Space': this._cmd_hint,
            'Ctrl-Space': this._cmd_hint
        }
    }

    _cmd_eval_answer(event, field) {
        this._eval_field_answer(field)
    }

    _cmd_hint(event, field) {
        const found = this._find_answer(field)
        const answer = found.answer
        const i = found.index
        const val = field.value
        if (answer.length > i) {
            field.value = answer.slice(0, i+1) + val.slice(i, val.length)
            this._highlight(field, i+1, i+1)
        } else if (field.value.length > i) {
            field.value = val.slice(0, i)
            this._highlight(field, i, i)
        }
        return false
    }

    _recognize_field(field) {
        return ((field.type === 'text' || field.type === 'textarea')
                && $(field).closest('.task').length)
    }

    _init_field(field) {
        field.answer_index = this._last_answer_index++
        console.log('>>', field.answer_index, field)
        $(field).on('keydown', this._on_key_down.bind(this))
        $(field).on('dblclick', this._on_eval_answer.bind(this))
        $(field).on('touchstart', this._on_touch_start.bind(this))
    }

    _on_touch_start(event) {
        // This is necessary in iBooks on iPhone/iPad as iBooks probably makes all
        // text fields ineditable by default so the keyboard doesnt show up when
        // the field is touched to type.
        const element = event.target
        if (element.disabled)
            element.disabled = false
        element.focus()
        event.stop()
    }

    _find_answer(field) {
        console.log('--', field, field.answer_index, this._answers)
        const answers = this._answers[field.answer_index].split('|')
        const value = field.value
        let answer_index = 0
        let char_index = 0; // max last correct char index
        for (let i=0; i < answers.length; i++) {
            const a = answers[i]
            let j = 0
            while (value.slice(0, j+1) === a.slice(0, j+1) && j < a.length) {
                j++
            }
            if (j > char_index) {
                char_index = j
                answer_index = i
            }
        }
        return {"answer": answers[answer_index], "index": char_index}
    }

    _highlight(field, start, end) {
        if (field.setSelectionRange) {
            field.focus()
            field.setSelectionRange(start, end)
        } else if (field.createTextRange) {
            const range = field.createTextRange()
            range.collapse(true)
            range.moveEnd('character', end)
            range.moveStart('character', start)
            range.select()
        }
    }

    _error_handler(field) {
        console.log('..', field)
        const found = this._find_answer(field)
        const index = found.index
        field.focus()
        this._highlight(field, index, index)
    }

    _eval_answer(value, i) {
        // Replace repeated spaces, newlines and tabs with a single space
        value = value.replace(/^\s*|\s(?=\s)|\s*$/g, "")
        for (const answer of this._answers[i].split('|')) {
            if (value === answer) {
                return true
            }
        }
        return false
    }

    _fill_answer(i) {
        this._set_answer(i, this._answers[i].split('|')[0])
    }

}

lcg.HiddenAnswers = class extends lcg.Exercise {

    constructor(form_name, answers, responses, messages) {
        super(form_name, answers, responses, messages)
        this.element.find('.toggle-button').on('click', this._on_toggle_button)
    }

    _recognize_field(field) {
        return false
    }

    _on_toggle_button(event) {
        $(event.target).closest('.task').find('.answer').slideToggle(200)
        return false;
    }

    _on_evaluate_button(event) {
        this.element.find('.answer').slideDown(200)
    }

    _on_reset_button(event) {
        this.element.find('.answer').slideUp(200)
    }

}

lcg.ModelCloze = class extends lcg.Exercise {

    constructor(form_name, answers, responses, messages) {
        super(form_name, answers, responses, messages)
        this.element.find('.model-answers').hide()
    }

    _recognize_field(field) {
        return false
    }

    _on_evaluate_button(event) {
        this.element.find('.model-answers').show()
    }

    _on_reset_button(event) {
        this.element.find('.model-answers').hide()
    }

}

lcg.Dictation = class extends lcg.FillInExercise {

    constructor(form_name, answers, responses, messages, recordings) {
        super(form_name, answers, responses, messages)
        this._recordings = recordings
        this._current_recording = -1
    }

    _define_keymap() {
        return {
            'Enter': this._cmd_eval_answer,
            'Ctrl-Space': this._cmd_hint,
            '>': this._cmd_play_next,
            '<': this._cmd_play_previous,
            'Ctrl-Enter': this._cmd_play_current
        }
    }

    _cmd_play_next(event, field) {
        if (this._current_recording < this._recordings.length-1) {
            this._current_recording++
            this._cmd_play_current(event, field)
        }
    }

    _cmd_play_previous(event, field) {
        if (this._current_recording > 0) {
            this._current_recording--
            this._cmd_play_current(event, field)
        }
    }

    _cmd_play_current(event, field) {
        this._play_audio(this._recordings[this._current_recording])
    }

    _display_results() {
        const msg = this._msg(this._correct() ? 'Correct':'Error(s) found')
        this._form.result.value = msg
    }

}
