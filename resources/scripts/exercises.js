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

function eval_cloze(f, answers) {
   var correct = 0;
   var marked = 0;
   for (i=0; i < answers.length; i++)
      if (f.elements[i].type == 'text')
         if (f.elements[i].value == answers[i]) correct++;
         else if (f.elements[i].value) {
            if (f.elements[i].value[0] != "!")
               f.elements[i].value = "!" + f.elements[i].value;
            marked = 1;
         }
   f.result.value = "Correct answers: "+correct+"/"+answers.length+".";
   if (marked) f.result.value +=
		  " Check back for the entries marked with an exclamation mark!";
   if (correct == answers.length) self.location="media/all-correct-response.ogg";
   else if (correct == 0) self.location="media/all-wrong-response.ogg";
   else self.location="media/some-wrong-response.ogg";
}

function fill_cloze(f, answers) {
   for (i=0; i < answers.length; i++)
      if (f.elements[i].type == 'text')
	f.elements[i].value = answers[i];
}
