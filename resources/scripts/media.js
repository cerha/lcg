/* Copyright (C) 2004-2008 Brailcom, o.p.s.
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

var MIN_FLASH_VERSION = '9'; //.0.115';

function export_media_player(uri, target, msg) {
   // TODO: Degrade gracefully when running locally (the player doesn't work in this case
   // because of Flash security restrictions).
   var so = new SWFObject(uri, 'mediaplayer', '300', '20', MIN_FLASH_VERSION);
   so.addParam('allowscriptaccess', 'always');
   so.addVariable('width', '300');
   so.addVariable('height', '20');
   so.addVariable('javascriptid', 'mediaplayer');
   so.addVariable('enablejs', 'true');
   if (!so.write(target)) {
      // Supply the error message here to prevent it when Javascript is disabled.
      document.getElementById(target).innerHTML = msg.replace(/\$version/g, MIN_FLASH_VERSION);
   }
   // Detect the existence of Windows Media Player v7 or higher as the fallback player.
   /* Currently unused because the player (even if hidden) insists on rendering animations 
      on the page (across our content).
   if (window.ActiveXObject && navigator.userAgent.indexOf('Win') != -1)
      try { 
	 var wmp = new ActiveXObject('WMPlayer.OCX.7'); 
	 if (wmp)
	    document.write('<object id="windows_media_player" height="0" width="0"' +
			   ' classid="CLSID:6BF52A52-394A-11d3-B153-00C04F79FAA6"' +
			   ' type="application/x-oleobject">' +
			   '<param name="uiMode" value="none">' +
			   '</object>');
      }
      catch(e) {}
   */
}

function export_media_controls(uri, label, image) {
   var attr = (' onclick="play_media(\''+ uri +'\'); return false;"'+
	       ' onkeydown="return on_media_ctrl_keydown(event, \''+ uri +'\');"'+
	       ' onkeypress="return on_media_ctrl_keypress(event, \''+ uri +'\');"'+
	       ' class="sound-control"');
   var html;
   if (image)
      html = '<button title="'+ label +'"'+ attr +'><img src="'+ image +'" alt="" /></button>';
   else 
      html = '<input type="button" value="'+ label +'"'+ attr +' />';
   document.write(html)
}

function _media_player() {
   var player;
   if (navigator.appName.indexOf("Microsoft") != -1)
      player = window.mediaplayer;
   else 
      player = document.mediaplayer;
   if (player && player.itemData)
      return player;
   else
      return null;
}
      

function _media_player_command(cmd, uri) {
   // Available commands: 'playpause', 'forward', 'rewind', 'volume+', 'volume-'
   var player = _media_player();
   // Use Flash player if possible.
   if (player) {
      data = player.itemData(0);
      if (cmd == 'playpause') {
	 if (data.file != uri) player.loadFile({file: uri});
	 player.sendEvent('playpause');
      } else if ((cmd == 'forward' || cmd == 'rewind') && data.file == uri) {
	 position = _player_state.position;
	 skip = 3; // Seconds
	 if (cmd == 'forward' && data.duration > position+skip)
	    position += skip;
	 if (cmd == 'rewind')
	    position = (position-skip >= 0) ? position-skip : 0;
	 player.sendEvent('scrub', position);
      } else if ((cmd == 'volume+' || cmd == 'volume-') && data.file == uri) {
	 volume = _player_state.volume;
	 skip = 5; // Percents
	 if (cmd == 'volume+' && volume+skip <= 100)
	    volume += skip;
	 if (cmd == 'volume-' && volume-skip >= 20)
	    volume -= skip;
	 player.sendEvent('volume', volume);
      }
   }
   // Use Windows Media Player as the second option.
   else if (document.windows_media_player) {
      player = document.windows_media_player
      if (cmd == 'playpause') {
	 if (player.URL != uri)
	    player.URL = uri;
	 if (player.PlayState == 3)
	    player.controls.pause();
	 else
	    player.controls.play();
      } else if (cmd == 'forward' && player.controls.isAvailable('FastForward'))
	 player.controls.fastForward();
      else if (cmd == 'rewind' && player.controls.isAvailable('FastReverse'))
	 player.controls.fastReverse();
   } 
   // Play the sound by system as the last resort.
   else if (cmd == 'playpause')
      self.location = uri;
}

function play_media(uri) {
   _media_player_command('playpause', uri)
}

function on_media_ctrl_keydown(event, uri) {
   // Not all browsers fire fire the keypress events for arrow keys, so we handle then on keydown.
   var code = document.all ? event.keyCode : event.which;
   var map = {37: '<', // left arrow
	      39: '>', // right arrow
	      38: '+', // up arrow
	      40: '-'} // down arrow
   var key = map[code];
   if (key != null) 
      return _handle_media_ctrl_keys(uri, map[code], 'keydown');
   else
      return true;
}

function on_media_ctrl_keypress(event, uri) {
   var code = event.charCode || event.keyCode;
   return _handle_media_ctrl_keys(uri, String.fromCharCode(code), 'keypress');
}

function _handle_media_ctrl_keys(uri, key, type) {
   if (key == '<') { 
      _media_player_command('rewind', uri);
      return false;
   }
   if (key == '>') { // right arrow
      _media_player_command('forward', uri);
      return false;
   }
   if (key == '+') { // up arrow
      _media_player_command('volume+', uri);
      return false;
   }
   if (key == '-') { // down arrow
      _media_player_command('volume-', uri);
      return false;
   }
   return true;
}

var _player_state = {};
function getUpdate(type, arg, arg2, swf) { 
   if (type == 'state') _player_state.state = arg;
   else if (type == 'time') _player_state.position = arg;
   else if (type == 'volume') _player_state.volume = arg;
};
