/* Copyright (C) 2004, 2005 Brailcom, o.p.s.
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

// General use functions

function count(array, value) {
   // Return the count of elements having the given value in the array.
   var count = 0;
   for (i=0; i<array.length; i++)
      if (array[i] == value) count++;
   return count;
}

function event_key(e) {
   // Return a textual representation of a pressed key.
   var code = document.all ? e.keyCode : e.which;
   var cap = code >= 65 && code <= 90;
   var modifiers = '';
   if (document.all || document.getElementById) {
      modifiers += e.ctrlKey ? 'Ctrl-' : '';
      modifiers += e.altKey ? 'Alt-' : '';
      modifiers += e.shiftKey && !cap ? 'Shift-' : '';
   } else if (document.layers) {
      modifiers += e.modifiers & Event.CONTROL_MASK ? 'Ctrl-' : '';
      modifiers += e.modifiers & Event.ALT_MASK ? 'Alt-' : '';
      modifiers += e.modifiers & Event.SHIFT_MASK && !cap ? 'Shift-' : '';
   }
   var map = [];
   map[13] = 'Enter';
   map[32] = 'Space';
   map[10] = 'Enter';
   var key = map[code] != null ? map[code] : String.fromCharCode(code);
   //alert(modifiers+key +' ('+code+')');
   return modifiers+key;
}

function event_target(e) {
   var target;
   if (e.target) target = e.target;
   else if (e.srcElement) target = e.srcElement;
   if (target.nodeType == 3) // defeat Safari bug
      target = targ.parentNode;
   return target;
}

function highlight(field, start, end) {
  if (field.setSelectionRange) {
    field.focus();
    field.setSelectionRange(start, end);
  }
  else if (field.createTextRange) {
    var range = field.createTextRange();
    range.collapse(true);
    range.moveEnd('character', end);
    range.moveStart('character', start);
    range.select();
  }
}

function last_correct_char_index(field, answer) {
   var i = 0;
   while (field.value.slice(0, i+1) == answer.slice(0, i+1) && i<answer.length)
      i++; 
   return i;
}

// Exercises

function init_form(f, handler, answers, responses, messages) {
   f.handler = handler;
   handler.init(f, answers, responses, messages);
}

//=============================================================================
// Generic exercise form handler class.

function Handler() {
   if (document.captureEvents) document.captureEvents(Event.KEYPRESS);
}

Handler.prototype.init = function(form, answers, responses, messages) {
   this._form = form;
   this._answers = answers;
   this._responses = responses;
   this._messages = messages;
   this._answered = new Array(answers.length);
   this._fields = new Array();
   this._last_answer_index = 0;
   for (i=0; i < this._form.elements.length; i++) {
      var field = this._form.elements[i];
      if (this._recognize_field(field)) {
	 this._init_field(field);
	 this._fields.push(field);
      }
   }
}

Handler.prototype._eval_answer = function(field) {
   var i = field.answer_index;
   //window.defaultStatus = "*"+i+'/'+this._fields.length+": "+field.value+" | "+this._answers[i];
   if (field.value != '') {
      var answer = this._answers[i];
      var correct = (field.value == answer);
      if (this._answered[i] == null) this._answered[i] = correct ? 1 : -1;
      return correct;
   } else {
      this._answered[i] = null;
      return null;
   }
}

Handler.prototype.eval_answer = function(field) {
   var correct = this._eval_answer(field)
   play_audio(this.response(correct ? 'correct':'incorrect'));
   this.display_results();
   if (!correct) this._error_handler(field);
   return correct;
}

Handler.prototype._error_handler = function(field) {}

Handler.prototype.response = function(selector) {
   var array = this._responses[selector];
   var n = Math.floor(Math.random() * array.length);
   return array[n];
}

Handler.prototype.msg = function(text) {
   if (text in this._messages) return this._messages[text];
   else return text;
}

Handler.prototype.correct = function() {
   return count(this._answered, 1);
}

Handler.prototype.incorrect = function() {
   return count(this._answered, -1);
}

Handler.prototype.percentage = function() {
   return Math.round(100 * this.correct() / this._answers.length)
}

Handler.prototype.display_results = function() {
   var correct = this.correct();
   var incorrect =  this.incorrect();
   this._form.answered.value = (correct+incorrect) +'/'+ this._answers.length;
   this._form.result.value = correct +' ('+ this.percentage() +'%)';
}

Handler.prototype.fill = function() {
   for (var i=0; i < this._fields.length; i++) {
      var field = this._fields[i];
      this.set_field(field, this._answers[field.answer_index]);
   }
}

Handler.prototype.set_field = function(field, value) {
   field.value = value;
}

Handler.prototype.reset = function() {
   this._answered = new Array(this._answers.length);
   this.display_results();
}

//=============================================================================
// Choice based exercise handler class.

function ChoiceBasedExerciseHandler() {}
ChoiceBasedExerciseHandler.prototype = new Handler();

ChoiceBasedExerciseHandler.prototype._recognize_field = function(field) {
   return field.type == 'radio';
}

ChoiceBasedExerciseHandler.prototype._init_field = function(field) {
   if (field.name != this._last_group) {
      if (this._last_group != null) this._last_answer_index++;
      this._last_group = field.name;
   }
   field.answer_index = this._last_answer_index;
}

ChoiceBasedExerciseHandler.prototype.set_field = function(field, value) {
   field.checked = (field.value == value);
}

//=============================================================================

function SelectBasedExerciseHandler() {}
SelectBasedExerciseHandler.prototype = new ChoiceBasedExerciseHandler()

SelectBasedExerciseHandler.prototype._recognize_field = function(field) {
   return field.options != null;
}

SelectBasedExerciseHandler.prototype.set_field = function(field, value) {
   for (var i=0; i < field.options.length; i++) {
      var option = field.options[i];
      if (option.value == value) option.selected = true;
   }
}

//=============================================================================
// Fill-in text exercise handler class.

function FillInExerciseHandler() {}
FillInExerciseHandler.prototype = new Handler();

FillInExerciseHandler.prototype._recognize_field = function(field) {
   return ((field.type == 'text' || field.type == 'textarea') && 
	   this._last_answer_index < this._answers.length);
}

FillInExerciseHandler.prototype._init_field = function(field) {
   field.answer_index = this._last_answer_index++;
   field.onkeypress = this._handle_text_field_keypress;
}

FillInExerciseHandler.prototype._error_handler = function(field) {
   var answer = this._answers[field.answer_index]
   var index = last_correct_char_index(field, answer);
   field.focus()
   highlight(field, index, index);
}

FillInExerciseHandler.prototype._handle_text_field_keypress = function(e) {
   // 'this' does not refer to the FillInExerciseHandler instance here!
   if (document.all) e = window.event;
   var key = event_key(e);
   var field = event_target(e);
   if (key == 'Enter') {
      field.form.handler.eval_answer(field);
      return false;
   } else if (key == 'Ctrl-Space') {
      var answer = field.form.handler._answers[field.answer_index];
      if (field.value != answer.slice(0, field.value.length)) {
	 var i = last_correct_char_index(field, answer);
	 field.value = answer.slice(0, i+1) +
	    field.value.slice(i, field.value.length);
	 highlight(field, i+1, i+1);
      } else {
	 var len = field.value.length;
	 field.value += answer.slice(len, len+1);
      }
      return false;
   }
   return true;
}

FillInExerciseHandler.prototype.evaluate = function() {
   var focused = false;
   for (var i=0; i < this._fields.length; i++) {
      correct = this._eval_answer(this._fields[i]);
      if (!correct && !focused) {
	 this._error_handler(this._fields[i]);
	 focused = true;
      }
   }
   if (this._fields.length > 1) {
      switch (this.percentage()) {
	 case 100: selector = 'all_correct'; break;
	 case   0: selector = 'all_wrong'; break;
	 default:  selector = 'some_wrong';
      }
   } else {
      selector = this.correct() ? 'correct':'incorrect';
   }
   play_audio(this.response(selector));
   this.display_results();
}

function DictationHandler() {}
DictationHandler.prototype = new FillInExerciseHandler();

DictationHandler.prototype.display_results = function() {
   msg = this.msg(this.correct() ? 'Correct':'Error(s) found');
   this._form.result.value = msg
}

DictationHandler.prototype._eval_answer = function(field) {
   // In Dictation, we don't want to remember the first answer.
   var i = field.answer_index;
   var correct = (field.value == this._answers[i]);
   this._answered[i] = correct ? 1 : -1;
   return correct
}
