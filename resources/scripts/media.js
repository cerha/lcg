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

var MIN_FLASH_VERSION = '9.0.115';

var _shared_player_id = null;

function export_shared_audio_player(uri, id, msg) {
   // TODO: Degrade gracefully when running locally (the player doesn't work in this case
   // because of Flash security restrictions).
   //var vars = {id: id};
   if (swfobject.hasFlashPlayerVersion(MIN_FLASH_VERSION)) {
      var vars = {id: id};
      var params = {allowfullscreen: 'false',
		    allowscriptaccess: 'always'};
      swfobject.embedSWF(uri, id, 300, 20, MIN_FLASH_VERSION, false, vars, params);
      _shared_player_id = id;
   } else {
      // Replace the "JavaScript disabled" error message by a "Flash not available" error message.
      var node = document.getElementById(id);
      if (node != null)
	 node.innerHTML = msg.replace(/\$version/g, MIN_FLASH_VERSION);
   }
}

function _media_control_attr(uri, field_id) {
   uri = "'"+uri+"'";
   if (typeof field_id != 'undefined') field_id = "'"+field_id+"'";
   return (' onclick="play_media('+ uri +', '+ field_id +'); return false;"'+
	   ' onkeydown="return on_media_ctrl_keydown(event, '+ uri +', '+ field_id +');"'+
	   ' onkeypress="return on_media_ctrl_keypress(event, '+ uri +', '+ field_id +');"'+
	   ' class="media-control"');
}

function export_media_control(uri, label, image, field_id) {
   var attr = _media_control_attr(uri, field_id);
   var html;
   if (typeof image != 'undefined' && image != null)
      html = '<button title="'+ label +'"'+ attr +'><img src="'+ image +'" alt="" /></button>';
   else 
      html = '<input type="button" value="'+ label +'"'+ attr +' />';
   document.write(html);
}

var _player;
var _player_state = {
   position: null,
   volume: null,
   state: null,
};
var _current_playlist = null;

function playerReady(obj) {
   if (obj.id == _shared_player_id) {
      _player = document.getElementById(_shared_player_id);
      _player.addControllerListener("VOLUME", "_on_player_volume_changed");
      _player.addModelListener("STATE", "_on_player_state_changed");
      _player.addModelListener("TIME", "_on_player_time_changed");
      _player_state.volume = _player.getConfig()['volume'];
   }
}
function _on_player_time_changed(event) { 
   _player_state.position = event.position;
}
function _on_player_volume_changed(event) {
   _player_state.volume = event.percentage; 
}
function _on_player_state_changed(event) { //IDLE, BUFFERING, PLAYING, PAUSED, COMPLETED
   _player_state.state = event.newstate; 
   if (event.newstate == "COMPLETED" && event.oldstate == "PLAYING" && _current_playlist != null) {
      var field = _current_playlist.field;
      if (field.selectedIndex < field.options.length) {
	 field.selectedIndex++;
	 play_media(_current_playlist.uri, field.id);
      }
   }
}

function _media_player_command(cmd, uri, field_id) {
   // Available commands: 'play', 'forward', 'rewind', 'volume+', 'volume-'
   _current_playlist = null;
   if (typeof field_id != 'undefined') {
      var field = document.getElementById(field_id);
      if (field != null) {
	 if (field.type == 'select-one')
	    _current_playlist = {uri: uri, field: field};
	 uri += '/'+ field.value;
      }
   }
   if (_player) {
      // Use the player if possible.
      playlist = _player.getPlaylist();
      if (playlist != null && playlist.length != null)
	 item = playlist[0]
      else
	 item = null
      if (cmd == 'play') {
	 if (item == null || item.file != uri)
	    _player.sendEvent('LOAD', {file: uri});
	 _player.sendEvent('PLAY');
      } else if ((cmd == 'forward' || cmd == 'rewind') && item.file == uri) {
	 position = _player_state.position;
	 skip = item.duration / 20; // Seconds
	 if (skip < 3) skip = 3;
	 if (skip > 30) skip = 30;
	 if (cmd == 'forward' && item.duration > position+skip)
	    position += skip;
	 if (cmd == 'rewind')
	    position = (position-skip >= 0) ? position-skip : 0;
	 _player.sendEvent('SEEK', position);
      } else if ((cmd == 'volume+' || cmd == 'volume-') && item.file == uri) {
	 volume = _player_state.volume;
	 skip = 5; // Percents
	 if (cmd == 'volume+' && volume+skip <= 100)
	    volume += skip;
	 if (cmd == 'volume-' && volume-skip >= 20)
	    volume -= skip;
	 _player.sendEvent('VOLUME', volume);
      }
   } else if (cmd == 'play') {
      // Play the sound through the system if the player is not available.
      self.location = uri;
   }
}

function play_media(uri, field_id) {
   _media_player_command('play', uri, field_id);
}

function on_media_ctrl_keydown(event, uri, field_id) {
   // Not all browsers fire keypress events for arrow keys, so we handle them in onkeydown as well.
   var code = document.all ? event.keyCode : event.which;
   var map = {37: '<', // left arrow
	      39: '>', // right arrow
	      38: '+', // up arrow
	      40: '-'} // down arrow
   var key = map[code];
   if (key != null) 
      return _handle_media_ctrl_keys(uri, map[code], 'keydown', field_id);
   else
      return true;
}

function on_media_ctrl_keypress(event, uri, field_id) {
   var code = event.charCode || event.keyCode;
   return _handle_media_ctrl_keys(uri, String.fromCharCode(code), 'keypress', field_id);
}

function _handle_media_ctrl_keys(uri, key, type, field_id) {
   if (key == '<') { 
      _media_player_command('rewind', uri, field_id);
      return false;
   }
   if (key == '>') { // right arrow
      _media_player_command('forward', uri, field_id);
      return false;
   }
   if (key == '+') { // up arrow
      _media_player_command('volume+', uri, field_id);
      return false;
   }
   if (key == '-') { // down arrow
      _media_player_command('volume-', uri, field_id);
      return false;
   }
   return true;
}
