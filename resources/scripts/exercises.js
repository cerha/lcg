/* Copyright (C) 2004 Brailcom, o.p.s.
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

// Choice based exercise evaluation

function eval_choice(f, n, total, correct, snd) {
   if (f._answered == null) f._answered = [total];
   play_audio(snd);
   if (f._answered[n] == null) f._answered[n] = correct ? 1 : -1;
   display_choice_results(f, total);
}

function reset_choices(f, total) {
   f._answered = new Array(total);
   display_choice_results(f, total);
}

function display_choice_results(f, total) {
   var correct = count(f._answered, 1);
   var done = correct + count(f._answered, -1);
   f.answered.value = done + '/' + total;
   f.result.value = correct + ' (' + Math.round(100*correct/total) + '%)';
}

// Fill-in text exercise evaluation

function init_cloze_form(f, answers) {
   if (document.captureEvents) document.captureEvents(Event.KEYPRESS);
   f._answers = answers;
   for (i=0; i < answers.length; i++) {
      var field = f.elements[i]
      field.onkeypress = handle_cloze_field_keypress;
      field._parent_form = f;
      field._parent_index = i;
   }
}

function last_correct_char_index(field, answer) {
   var i = 0;
   while (field.value.slice(0, i+1) == answer.slice(0, i+1)) i++; 
   return i;
}

function handle_cloze_field_keypress(e) {
   if (document.all) e = window.event;
   var key = event_key(e);
   var field = event_target(e);
   if (key == 'Enter') {
      eval_cloze_field(field._parent_form, field._parent_index);
   } else if (key == 'Ctrl-Space') {
      var answer = field._parent_form._answers[field._parent_index];
      if (field.value != answer.slice(0, field.value.length)) {
	 var i = last_correct_char_index(field, answer);
	 field.value = field.value.slice(0, i);
      } else {
	 var len = field.value.length
	 field.value += answer.slice(len, len+1);
      }
      return false;
   }
   return true;
}

function eval_cloze_field(f, i) {
   var answer = f._answers[i];
   var field = f.elements[i];
   if (field.value == answer)
      play_audio('media/correct-response.ogg');
   else {
      play_audio('media/incorrect-response.ogg');
      var i = last_correct_char_index(field, answer);
      highlight(field, i, i);
   }
}

function eval_cloze(f) {
   var correct = 0;
   var marked = 0;
   for (i=0; i < f._answers.length; i++)
      if (f.elements[i].type == 'text')
         if (f.elements[i].value == f._answers[i]) correct++;
         else if (f.elements[i].value) {
            if (f.elements[i].value[0] != "!")
               f.elements[i].value = "!" + f.elements[i].value;
            marked = 1;
         }
   f.result.value = "Correct answers: "+correct+"/"+f._answers.length+".";
   if (marked) f.result.value +=
	  " Check back for the entries marked with an exclamation mark!";
   if (correct == f._answers.length) snd = "media/all-correct-response.ogg";
   else if (correct == 0) snd = "media/all-wrong-response.ogg";
   else snd = "media/some-wrong-response.ogg";
   play_audio(snd);
}

function fill_cloze(f) {
   for (i=0; i < f._answers.length; i++)
      if (f.elements[i].type == 'text')
	f.elements[i].value = f._answers[i];
}
