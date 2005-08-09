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

function simulate_click_on_keypress(e) {
   if (document.all) e = window.event;
   var key = event_key(e);
   var target = event_target(e);
   if (key == 'Enter' || key == 'Space') target.onclick();
   return true;
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
   this._results = new Array(answers.length);
   this._first_attempt = new Array(answers.length);
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

Handler.prototype.response = function(selector) {
   var array = this._responses[selector];
   var n = Math.floor(Math.random() * array.length);
   return array[n];
}

Handler.prototype.msg = function(text) {
   if (text in this._messages) return this._messages[text];
   else return text;
}

Handler.prototype.set_answer = function(i, value) {
   this._fields[i].value = value;
}

Handler.prototype.get_value = function(i) {
   return this._fields[i].value;
}

Handler.prototype._error_handler = function(field) {
   field.focus();
}

Handler.prototype._eval_answer = function(value, i) {
   return value == this._answers[i];
}

Handler.prototype._eval_answers = function() {
   for (var i=0; i < this._answers.length; i++) {
      var value = this.get_value(i);
      if (value != '' && value != null) {
	 this._results[i] = (this._eval_answer(value, i) ? 1:-1);
	 if (this._first_attempt[i] == null)
	    this._first_attempt[i] = this._results[i];
      } else {
	 this._results[i] = null;
      }
   }
   this.display_results();
}

Handler.prototype.eval_answer = function(field) {
   this._eval_answers();
   var i = field.answer_index;
   var result = this._results[i];
   if (result != null) {
      play_audio(this.response(result == 1 ? 'correct':'incorrect'));
      if (result == 1) {
	 // if (i < this._fields.length)
	 //    This doesn't work in MultipleChoiceQuestions (answer index is not
	 //    a field index).  But we probably don't want it anyway...
	 //    this._fields[i+1].focus();
      } else {
	 this._error_handler(field);
      }
   }
}

Handler.prototype.evaluate = function() {
   this._eval_answers();
   for (var i=0; i < this._results.length; i++) {
      if (this._results[i] != 1) {
	 this._error_handler(this._fields[i]);
	 break;
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
}

Handler.prototype.correct = function() {
   return count(this._results, 1);
}

Handler.prototype.incorrect = function() {
   return count(this._results, -1);
}

Handler.prototype.percentage = function() {
   return Math.round(100 * this.correct() / this._answers.length)
}

Handler.prototype.first_attempt_correct = function() {
   return count(this._first_attempt, 1);
}

Handler.prototype.first_attempt_percentage = function() {
   return Math.round(100 * this.first_attempt_correct() / this._answers.length)
}

Handler.prototype.display_results = function() {
   var correct = this.correct();
   var incorrect =  this.incorrect();
   var first_attempt_correct = this.first_attempt_correct();
   this._form.answered.value = (correct+incorrect) +'/'+ this._answers.length;
   result = correct + " ($x%)".replace("\$x", this.percentage());
   if (correct != first_attempt_correct) {
      msg = this.msg(", $x ($y%) on first attempt");
      msg = msg.replace("\$x", first_attempt_correct);
      msg = msg.replace("\$y", this.first_attempt_percentage());
      result += msg
   }
   this._form.result.value = result;
}

Handler.prototype.fill = function() {
   for (var i=0; i < this._answers.length; i++) {
      this._fill_answer(i);
   }
   this._eval_answers();
}

Handler.prototype._fill_answer = function(i) {
      this.set_answer(i, this._answers[i]);
}

Handler.prototype.reset = function() {
   this._results = new Array(this._answers.length);
   this._first_attempt = new Array(this._answers.length);
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

ChoiceBasedExerciseHandler.prototype.set_answer = function(i, value) {
   for (var n=0; n < this._fields.length; n++) {
      var field = this._fields[n];
      if (field.answer_index == i) {
	 field.checked = (field.value == value);
      }
   }
}

ChoiceBasedExerciseHandler.prototype.get_value = function(i) {
   for (var n=0; n < this._fields.length; n++) {
      var field = this._fields[n];
      if (field.answer_index == i && field.checked) {
	 return field.value;
      }
   }
   return null;
}

//=============================================================================

function SelectBasedExerciseHandler() {}
SelectBasedExerciseHandler.prototype = new Handler()

SelectBasedExerciseHandler.prototype._recognize_field = function(field) {
   return field.options != null;
}

SelectBasedExerciseHandler.prototype._init_field = function(field) {
   field.answer_index = this._last_answer_index++;
}

SelectBasedExerciseHandler.prototype.set_answer = function(i, value) {
   var field = this._fields[i];
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

FillInExerciseHandler.prototype._find_answer = function(field) {
   var answers = this._answers[field.answer_index].split('|');
   var value = field.value;
   var answer_index = 0;
   var char_index = 0; // max last correct char index
   for (var i=0; i < answers.length; i++) {
      var a = answers[i];
      var j = 0;
      while (value.slice(0, j+1) == a.slice(0, j+1) && j < a.length) j++; 
      if (j > char_index) {
	 char_index = j;
	 answer_index = i;
      }
   }
   return {"answer": answers[answer_index], "index": char_index};
}

FillInExerciseHandler.prototype._error_handler = function(field) {
   var found = this._find_answer(field);
   var index = found.index
   field.focus()
   highlight(field, index, index);
}

FillInExerciseHandler.prototype._eval_answer = function(value, i) {
   var answers = this._answers[i].split('|');
   for (var j=0; j < answers.length; j++) {
      if (value == answers[j]) return true;
   }
   return false;
}

FillInExerciseHandler.prototype._fill_answer = function(i) {
   var answers = this._answers[i].split('|');
   this.set_answer(i, answers[0]);
}

FillInExerciseHandler.prototype._handle_text_field_keypress = function(e) {
   if (document.all) e = window.event;
   var key = event_key(e);
   var field = event_target(e);
   // 'this' does not refer to the FillInExerciseHandler instance here!
   var _this = field.form.handler;
   if (key == 'Enter') { // Eval
      _this.eval_answer(field);
      return false;
   } else if (key == 'Ctrl-Space') { // Hint
      var found = _this._find_answer(field);
      var answer = found.answer; 
      var i = found.index; 
      var val = field.value
      if (answer.length > i) {
	 field.value = answer.slice(0, i+1) + val.slice(i, val.length);
	 highlight(field, i+1, i+1);
      } else if (field.value.length > i) {
	 field.value = val.slice(0, i);
	 highlight(field, i, i);
      }
      return false;
   }
   return true;
}

function DictationHandler() {}
DictationHandler.prototype = new FillInExerciseHandler();

DictationHandler.prototype.display_results = function() {
   msg = this.msg(this.correct() ? 'Correct':'Error(s) found');
   this._form.result.value = msg
}
