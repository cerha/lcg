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

if (navigator.appName=="Microsoft Internet Explorer")
   document.write('<object id="media_player" height="0" width="0"' +
		  ' classid="CLSID:6BF52A52-394A-11d3-B153-00C04F79FAA6">' +
		  '</object>');

function play_audio(url) {
   if (navigator.appName=="Microsoft Internet Explorer") {
      //document.all['bgsound_id'].src=url;
      if (document.media_player.URL != url) {
	 window.status = 'Loading: ' + url;
	 document.media_player.URL = url;
      }
      window.status = 'Playing: ' + document.media_player.URL;
   } else {
      self.location = url;
   }
}

function stop_audio() {
   if (navigator.appName=="Microsoft Internet Explorer") {
      window.status = 'Playback stopped';
      document.media_player.controls.stop();
   } else {

   }
}

