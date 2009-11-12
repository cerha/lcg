/* Copyright (C) 2009 Brailcom, o.p.s.
 * Author: Tomas Cerha
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

/* Helper function for embedding flash objects through SWFobject library. */

function embed_swf_object(uri, id, width, height, flashvars, min_flash_version, 
			  alternative_content, allow_fullscreen) {
   /* Arguments:

      uri -- URI of the Flash object to embed
      id -- target HTML element id
      width -- width in pixels
      height -- height in pixels
      flashvars -- url encoded string of variables to pass to the flash object
        (such as 'name=value&foo=bar')
      min_flash_version -- minimal required Flash version as a string, such as '9' or '9.0.25'
      alternative_content -- content to display (put inside the target HTML element) when Flash
        is not available or its version doesn't match min_flash_version.
      allow_fullscreen -- allow switching 

   */
   // TODO: Detect and handle when running locally (JavaScript communication
   // doesn't work in this case because of Flash security restrictions).
   if (min_flash_version == null) 
      min_flash_version = '9';
   if (swfobject.hasFlashPlayerVersion(min_flash_version)) {
      var vars = {id: id};
      var params = {allowfullscreen: (allow_fullscreen?'true':'false'),
		    allowscriptaccess: 'always',
		    flashvars: flashvars};
      var attrs = {id: id, name: id};
      swfobject.embedSWF(uri, id, width, height, min_flash_version, false, vars, params, attrs);
   } else if (alternative_content != null) {
      // Replace the original content of the div by an error message or some
      // other content.  This allows, for example, to replace a message like
      // "Javascript disabled" by a message "Flash not installed".  If the
      // browser supports both Flash and JS, the content is replaced by the
      // object, otherwise the appropriate message is displayed (if JS doesn't
      // work, original message stays, if it does, but flash does not, the
      // later message replaces it).
      var node = document.getElementById(id);
      if (node != null)
	 node.innerHTML = alternative_content;
   }
}
