/* Copyright (C) 2004, 2005, 2002 Brailcom, o.p.s.
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

var windows_media_player_available = detect();

// Detext the existence of Windows Media Player v7 or higher
function detect() {
   if (window.ActiveXObject && navigator.userAgent.indexOf('Win') != -1) {
      try {
	 var control = new ActiveXObject('WMPlayer.OCX.7');
	 if (control) return true;
      }
      catch(e) {}
   }
   return false;
}

function play_audio(url) {
   if (windows_media_player_available && document.media_player)
      document.media_player.URL = url;
   else
      self.location = url;
}

function stop_audio() {
   if (windows_media_player_available && document.media_player)
      document.media_player.controls.stop();
}
