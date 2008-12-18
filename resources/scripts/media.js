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

/* There can be exactly one player instance on one page, that is shared by multiple player
 * controls.  Each control usually operates on one media file or one playlist (set of media files).
 * The shared player can play just one media file at a time, so invoking playback from one control
 * stops any playback previously invoked from other controls (reloads the player with different
 * media file).
 */
var _shared_player_id = null;

/* Dictionary with a state object for each player instance (initialized on player export) */
var _player_state = {};

function export_media_player(uri, id, width, height, shared, media, flash_errmsg) {
   // TODO: Degrade gracefully when running locally (the player doesn't work in this case
   // because of Flash security restrictions).
   if (swfobject.hasFlashPlayerVersion(MIN_FLASH_VERSION)) {
      var vars = {id: id};
      var params = {allowfullscreen: 'false',
		    allowscriptaccess: 'always'};
      var attrs = {id: id, name: id};
      swfobject.embedSWF(uri, id, width, height, MIN_FLASH_VERSION, false, vars, params, attrs);
      _player_state[id] = {
	 position: 0,
	 duration: null,
	 volume: null,
	 playing: false,
	 controls: null,
	 loaded_uri: null,
	 on_load: null
      };
      if (shared)
	 _shared_player_id = id;
   } else {
      // Replace the "JavaScript disabled" error message by a "Flash not available" error message.
      var node = document.getElementById(id);
      if (node != null)
	 node.innerHTML = flash_errmsg.replace(/\$version/g, MIN_FLASH_VERSION);
   }
}

function playerReady(obj) {
   //Called automatically by JW Media Player when a player instance is initialized.
   var player = document.getElementById(obj.id);
   var state = _player_state[obj.id];
   if (player && typeof state != 'undefined') {
      player.addControllerListener('VOLUME', '_on_player_volume_changed');
      player.addModelListener('STATE', '_on_player_state_changed');
      player.addModelListener('TIME', '_on_player_time_changed');
      player.addModelListener('LOADED', '_on_player_loading_progress_changed');
      state.volume = player.getConfig()['volume'];
      var ctrl = state.controls;
      if (ctrl != null) {
	 var uri = ctrl.uri;
	 if (ctrl.track_selection != null)
	    uri +='/'+ ctrl.track_selection.value;
	 player.sendEvent('LOAD', uri);
	 // The player actually starts download after playback is invoked, so this trick tries to
	 // preload the initial track on page load.  The delay was chosen experimantally.  It may
	 // not work 100%, but this feature is not essential.
	 player.sendEvent('PLAY', true);
	 setTimeout(function () { player.sendEvent('PLAY', false); }, 500);
      }
   }
}

function init_player_controls(player_id, uri, position, button_id, selection_id, position_id) {
   // null in player_id means to use the shared player (its real id is not known to the caller and
   // at this time also not to this module).
   var button = document.getElementById(button_id);
   var select = document.getElementById(selection_id);
   var field = document.getElementById(position_id);
   var ctrl = {
      player_id: player_id,
      uri: uri,
      initial_position: position,
      button: button,
      track_selection: select,
      position_field: field
   };
   if (button != null) {
      button._media_player_ctrl = ctrl;
      button.onclick = _on_media_ctrl_click;
      // Not all browsers fire keypress events for arrow keys, so we handle onkeydown as well.
      button.onkeypress = _on_media_ctrl_keypress;
      button.onkeydown = _on_media_ctrl_keydown;
   }
   if (select != null) {
      select._media_player_ctrl = ctrl;
      select.onchange = _on_media_ctrl_select;
   }
   if (player_id != null)
      _player_state[player_id].controls = ctrl
}

function play_media(uri) {
   // Play given URI using the shared media player (if available).
   _media_player_play(null, uri, null);
}

// Media player control functions.

function _media_player(player_id) {
   if (player_id == null)
      player_id = _shared_player_id;
   if (player_id != null) {
      var player = document.getElementById(player_id);
      // Check that this really is the player instance, not its empty container.
      if (typeof player.getPlaylist != 'undefined')
	 return player;
   } 
   return null;
}

function _media_player_current_uri(player) {
   var playlist = player.getPlaylist();
   if (playlist != null && playlist.length != null)
      return playlist[0].file;
   else
      return null
}

function _media_player_play(player_id, uri, position) {
   var player = _media_player(player_id);
   if (player != null) {
      if (uri != _media_player_current_uri(player))
	 player.sendEvent('LOAD', uri);
      player.sendEvent('PLAY');
      if (position != null) {
	 var state = _player_state[player_id];
	 if (uri == state.loaded_uri) {
	    // When the file was already loaded, we can seek immediately.
	    player.sendEvent('SEEK', position);
	 } else {
	    // If new file is being loaded, we need to postpone the SEEK until loading is finished
	    // (SEEK doesn't work while loading).
	    player.sendEvent('PLAY'); // Pause the playback for now.
	    state.on_load = function () {
	       player.sendEvent('PLAY');
	       player.sendEvent('SEEK', position);
	    };
	 }
      }
   } else {
      // Play the sound through the system if the player is not available.
      self.location = uri;
   }
}

function _media_player_seek(player_id, forward) {
   var player = _media_player(player_id);
   if (player != null) {
      var state = _player_state[player_id];
      var position = state.position;
      var duration = state.duration;
      if (duration != null) {
	 var skip = duration / 20; // Seconds
	 if (skip < 3) skip = 3;
	 if (skip > 30) skip = 30;
	 if (forward)
	    position += skip;
	 else 
	    position -= skip;
	 if (position < 0)
	    position = 0;
	 if (position < duration)
	    player.sendEvent('SEEK', position);
      }
   }
}

function _media_player_volume(player_id, diff) {
   // Increase/decrease the player volume by +/- diff percent.
   var player = _media_player(player_id);
   if (player != null) {
      var state = _player_state[player_id];
      var volume = state.volume + diff;
      //alert(_str(state) +': '+ volume);
      if (volume > 100)
	 volume = 100;
      if (volume < 20)
	 volume = 20;
      player.sendEvent('VOLUME', volume);
   }
}

function _str(obj) {
   // For debugging only.
   var str = '';
   for (attr in obj)
      str += (str ? ', ' : '') + attr +': '+ obj[attr];
   return '{'+ str +'}';
}

// Callbacks invoked by the media player.

function _on_player_time_changed(event) { 
   var state = _player_state[event.id];
   var ctrl = state.controls;
   var position = event.position;
   state.position = position;
   state.duration = event.duration;
   // Update the position stored in player controls.
   if (ctrl != null) {
      var field = ctrl.position_field;
      if (field != null) {
	 var value = Math.floor(position);
	 if (value != field.value)
	    field.value = value;
      }
   }
}

function _on_player_volume_changed(event) {
   var state = _player_state[event.id];
   state.volume = event.percentage; 
}

function _on_player_state_changed(event) {
   // Player states: IDLE, BUFFERING, PLAYING, PAUSED, COMPLETED
   var state = _player_state[event.id];
   state.playing = (event.newstate == 'BUFFERING' || event.newstate == 'PLAYING'); 
   var ctrl = state.controls;
   if (ctrl != null && event.newstate == "COMPLETED" && event.oldstate == "PLAYING") {
      var select = ctrl.track_selection;
      //alert(select.selectedIndex +':'+ select.options.length);
      if (select != null && select.selectedIndex < select.options.length-1) {
	 select.selectedIndex++;
	 _media_player_play(event.id, ctrl.uri +'/'+ select.value, null);
      }
   }
}

function _on_player_loading_progress_changed(event) { 
   if (event.loaded == event.total) {
      var state = _player_state[event.id];
      state.loaded_uri = _media_player_current_uri(_media_player(event.id));
      var on_load = state.on_load;
      if (on_load != null) {
	 state.on_load = null;
	 setTimeout(on_load, 100);
      }
   }
}

// UI callbacks.

function _on_media_ctrl_click(event) {
   var ctrl = this._media_player_ctrl;
   var uri = ctrl.uri;
   if (ctrl.track_selection != null)
      uri += '/'+ ctrl.track_selection.value;
   var position = ctrl.initial_position;
   ctrl.initial_position = null;
   _media_player_play(ctrl.player_id, uri, position);
   return false;
}

function _on_media_ctrl_select(event) {
   var ctrl = this._media_player_ctrl;
   var field = ctrl.position_field;
   if (field != null)
      field.value = 0;
   return true;
}

function _on_media_ctrl_keydown(event) {
   if (document.all) event = window.event;
   var code = document.all ? event.keyCode : event.which;
   var map = {37: '<', // left arrow
	      39: '>', // right arrow
	      38: '+', // up arrow
	      40: '-'} // down arrow
   var key = map[code];
   if (key != null) 
      return _handle_media_ctrl_keys(key, this._media_player_ctrl.player_id);
   else
      return true;
}

function _on_media_ctrl_keypress(event) {
   if (document.all) event = window.event;
   var code = event.charCode || event.keyCode;
   var key = String.fromCharCode(code);
   return _handle_media_ctrl_keys(key, this._media_player_ctrl.player_id);
}

function _handle_media_ctrl_keys(key, player_id) {
   if (key == '>') { 
      _media_player_seek(player_id, true);
      return false;
   }
   if (key == '<') { // right arrow
      _media_player_seek(player_id, false);
      return false;
   }
   if (key == '+') { // up arrow
      _media_player_volume(player_id, +5);
      return false;
   }
   if (key == '-') { // down arrow
      _media_player_volume(player_id, -5);
      return false;
   }
   return true;
}
