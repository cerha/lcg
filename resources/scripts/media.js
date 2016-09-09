/* Copyright (C) 2004-2016 BRAILCOM, o.p.s.
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

/* Media playback infrastructure for Flash Player embedded within a web page.
 *
 * The primary purpose of this module is to allow media player control using ordinary HTML
 * elements, such as buttons, links, selection boxes etc.  The main advantage of this approach is
 * the accessibility of such controls (Flash applications themselves are not accessible at the time
 * being).
 *
 * The implementation is currently specific for JW FLV Media Player
 * (http://www.longtailvideo.com/players/jw-flv-player).  If the player is not available
 * (i.e. Flash not installed), the media files should be sent to browser to play them using the
 * system player (according to the client machines configuration).
 *
 * There can be exactly one "shared" player instance on one page, plus any number of "dedicated"
 * players.  The shared player may have multiple controls, the dedicated player is always connected
 * to just one set of controls.  Controls are UI elements which control the playback: The play/stop
 * button and optionally a track selection.  Each set of controls operates on one media file (in
 * this case the "set of controls" typically consists of just one play/stop button) or one playlist
 * (if track selection control is used together with the button).  The shared player can play just
 * one media file at a time, so invoking playback from one control stops any playback previously
 * invoked from other controls (reloads the player with different media file).
 */

/* eslint no-unused-vars: 0 */

var _shared_player_id = null;

/* Dictionary with a state object for each player instance (initialized on player export) */
var _player_state = {};

function init_media_player(player_id, shared){
    _player_state[player_id] = {
        position: 0,
        duration: null,
        volume: null,
        //playing: false,
        controls: null,
        loaded_uri: null,
        on_load: null
    };
    if (shared)
        _shared_player_id = player_id;
}

function init_player_controls(player_id, uri, button_id, selection_id, durations, position_id) {
    /* Initialize external media player controls.

       This method makes it possible to connect ordinary HTML controls to an
       embedded Flash media player.  The primary motivation for this trick is to
       make player controls accessible, since flash accessibility is currently
       very limited.

       Arguments:

       player_id -- id of the HTML element containing the player to connect
         with this set of controls.
       uri -- media file URI (string).  If track selection is used
         ('selection_id' is passed), the uri is just a base URI and the actual
         track URI is determined by concatenation of 'uri' and current
         selected value of track selection.
       button_id -- id of the HTML element controlling the player.  This is
         usually a button, but a plain link may be used as well.  Key presses
         and mouse clicks on this element will be handled and will control the
        connected player (space or Enter starts/stops the playback, <, > and
         left/right arrows seek backwards/forward, +, - and up/down arrows
         control the volumne.
       selection_id -- id of the HTML <select> element containing track
         selection.  The options must have track URI's relative to 'uri' in
         their values (track titles may be used as labels).  The currently
         selected option determines the track to play.
       durations -- array of track durations in seconds.  Each item of the
         array corresponds to one option in track selection.  Passing track
         durations makes it possible to display download progress in the
         player.  TODO: make it possible to pass duration also for single file
         controls without track selection.
       position_id -- id of the HTML element containing the playback position.
         It may be an HTML <input> or <hidden> element.  The initial playback
         position may be passed to the player through this element and also
         the current position may be passed back from the player to the web
         application.  The field's value is automatically updated during
         playback, so the form can be submitted to save the last position etc.

    */
    var button = document.getElementById(button_id);
    var select = document.getElementById(selection_id);
    var field = document.getElementById(position_id);
    var ctrl = {
        player_id: player_id,
        uri: uri,
        button: button,
        track_selection: select,
        position_field: field,
        initial_position: null,
        track_durations: durations
    };
    if (button !== null) {
        button._media_player_ctrl = ctrl;
        button.onclick = _on_media_ctrl_click;
        // Not all browsers fire keypress events for arrow keys, so we handle onkeydown as well.
        button.onkeypress = _on_media_ctrl_keypress;
        button.onkeydown = _on_media_ctrl_keydown;
    }
    if (select !== null) {
        select._media_player_ctrl = ctrl;
        select.onchange = _on_media_ctrl_select;
    }
    if (field !== null) {
        // If the position field contains an initial value (position in seconds), the first playback
        // will start from given position.
        var position = field.value;
        if (typeof position != 'undefined' && position !== 0)
            ctrl.initial_position = position;
        field.value = 0;
    }
    if (player_id !== _shared_player_id) {
        _player_state[player_id].controls = ctrl;
    }
}

function play_media(uri) {
    // Play given URI using the shared media player (if available).
    _media_player_play(_shared_player_id, uri, null, null);
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
        state.volume = player.getConfig().volume;
        var ctrl = state.controls;
        if (ctrl !== null && ctrl.initial_position !== null) {
            // If position was saved before, we want to start download on page load, because for
            // seeking we need to download the whole file first.  The player actually starts download
            // after playback is invoked, so the trick below starts and stops playback.  The delay was
            // chosen experimantally.  It may not work 100%, but this feature is not essential.
            _media_player_ctrl_play(ctrl, true);
            setTimeout(function () { player.sendEvent('PLAY', false); }, 500);
        }
    }
}

// Media player control functions.

function _media_player(player_id) {
    if (player_id !== null) {
        var player = document.getElementById(player_id);
        // Check that this really is the player instance, not its empty container.
        if (typeof player.getPlaylist != 'undefined')
            return player;
    }
    return null;
}

function _media_player_current_uri(player) {
    var playlist = player.getPlaylist();
    if (playlist !== null && playlist.length !== null)
        return playlist[0].file;
    else
        return null;
}

function _media_player_play(player_id, uri, duration, position) {
    var player = _media_player(player_id);
    if (player !== null) {
        if (uri !== _media_player_current_uri(player))
            player.sendEvent('LOAD', {file: uri, duration: duration});
        player.sendEvent('PLAY');
        if (position !== null) {
            var state = _player_state[player_id];
            if (uri === state.loaded_uri) {
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
    } else if (typeof Audio != 'undefined') {
        var audio = new Audio();
        audio.src = uri;
        audio.load();
        audio.play();
    }
}

function _media_player_ctrl_play(ctrl, preserve_initial_position) {
    var uri = ctrl.uri;
    var duration = null;
    var position = null;
    var select = ctrl.track_selection;
    if (select !== null) {
        uri += '/'+ select.value;
        if (ctrl.track_durations !== null)
            duration = ctrl.track_durations[select.selectedIndex];
    }
    if (typeof preserve_initial_position == 'undefined') {
        // HACK: Don't reset initial position when called from playerReady() just to start download.
        position = ctrl.initial_position;
        ctrl.initial_position = null;
    }
    _media_player_play(ctrl.player_id, uri, duration, position);
}

function _media_player_seek(player_id, forward) {
    var player = _media_player(player_id);
    if (player !== null) {
        var state = _player_state[player_id];
        var position = state.position;
        var duration = state.duration;
        if (duration !== null) {
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
    if (player !== null) {
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
    for (var attr in obj)
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
    if (ctrl !== null) {
        var field = ctrl.position_field;
        if (field !== null) {
            var value = Math.floor(position);
            if (value !== field.value)
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
    //state.playing = (event.newstate === 'BUFFERING' || event.newstate === 'PLAYING');
    var ctrl = state.controls;
    // Warning: The player behaves strangely with short recordings.  The state normally changes form
    // 'PLAYING' to 'COMPLETED', but sometimes also 'PLAYING' -> 'PAUSED', 'PAUSED' -> 'COMPLETED'.
    if (ctrl !== null && event.newstate === "COMPLETED" && event.oldstate !== "COMPLETED") {
        var select = ctrl.track_selection;
        if (select !== null && select.selectedIndex < select.options.length-1) {
            // Automatically advance to the next track if track selection control is present.
            select.selectedIndex++;
            _media_player_ctrl_play(ctrl);
        }
    }
}

function _on_player_loading_progress_changed(event) {
    if (event.loaded === event.total) {
        var state = _player_state[event.id];
        state.loaded_uri = _media_player_current_uri(_media_player(event.id));
        var on_load = state.on_load;
        if (on_load !== null) {
            state.on_load = null;
            setTimeout(on_load, 100);
        }
    }
}

// UI callbacks.

function _on_media_ctrl_click(event) {
    _media_player_ctrl_play(this._media_player_ctrl);
    return false;
}

function _on_media_ctrl_select(event) {
    var ctrl = this._media_player_ctrl;
    var field = ctrl.position_field;
    if (field !== null)
        field.value = 0;
    return true;
}

function _on_media_ctrl_keydown(event) {
    if (document.all) event = window.event;
    var code = document.all ? event.keyCode : event.which;
    var map = {37: '<', // left arrow
               39: '>', // right arrow
               38: '+', // up arrow
               40: '-'}; // down arrow
    var key = map[code];
    if (key !== null)
        return _handle_media_ctrl_keys(key, this._media_player_ctrl);
    else
        return true;
}

function _on_media_ctrl_keypress(event) {
    if (document.all) event = window.event;
    var code = event.charCode || event.keyCode;
    var key = String.fromCharCode(code);
    return _handle_media_ctrl_keys(key, this._media_player_ctrl);
}

function _handle_media_ctrl_keys(key, ctrl) {
    if (key === ' ' && ctrl.button.nodeName === 'A') {
        // Pressing space invokes the click event on buttons, but not on links,
        // so we must handle space on links explicitly here.
        _media_player_ctrl_play(ctrl);
        return false;
    }
    var player_id = ctrl.player_id;
    if (key === '>') {
        _media_player_seek(player_id, true);
        return false;
    }
    if (key === '<') {
        _media_player_seek(player_id, false);
        return false;
    }
    if (key === '+') {
        _media_player_volume(player_id, +5);
        return false;
    }
    if (key === '-') {
        _media_player_volume(player_id, -5);
        return false;
    }
    return true;
}
