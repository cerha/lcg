/* -*- coding: utf-8 -*-
 *
 * Copyright (C) 2012, 2013, 2014, 2015 Brailcom, o.p.s.
 * Author: Tomas Cerha
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
/*jslint browser: true */
/*jslint bitwise: true */
/*jslint unparam: true */
/*jslint todo: true */
/*global Class */
/*global Event */
/*global Element */
/*global Ajax */
/*global Effect */
/*global $ */
/*global $break */
/*global self */
/*global escape */
/*global unescape */

"use strict";

var lcg = {};

lcg.KeyHandler = Class.create({

    initialize: function () {
	this._keymap = this.keymap();
    },
      
    keymap: function () {
	return {};
    },

    event_key: function (event) {
	var code = document.all ? event.keyCode : event.which;
	var map = {
	    8:  'Backspace',
	    10: 'Enter',
	    13: 'Enter',
	    27: 'Escape',
	    32: 'Space',
	    33: 'PageUp',
	    34: 'PageDown',
	    35: 'End',
	    36: 'Home',
	    37: 'Left',
	    39: 'Right',
	    38: 'Up',
	    40: 'Down'
	};
	var key = null;
	if (code >= 65 && code <= 90) {
	    key = String.fromCharCode(code).toLowerCase();
	} else {
	    key = map[code];
	}
	if (key) {
	    var modifiers = '';
	    if (document.all || document.getElementById) {
		if (event.ctrlKey) { modifiers += 'Ctrl-'; }
		if (event.altKey) { modifiers += 'Alt-'; }
		if (event.shiftKey) { modifiers += 'Shift-'; }
	    } else if (document.layers) {
		if (event.modifiers & Event.CONTROL_MASK) { modifiers += 'Ctrl-'; }
		if (event.modifiers & Event.ALT_MASK) { modifiers += 'Alt-'; }
		if (event.modifiers & Event.SHIFT_MASK) { modifiers += 'Shift-'; }
	    }
	    key = modifiers+key;
	}
	return key;
    },

    on_key_down: function (event) {
	var key_name = this.event_key(event);
	var command = this._keymap[key_name];
	if (command) {
	    var element = event.element();
	    command.bind(this)(element);
	    event.stop();
	}
    },

    set_focus: function (element) {
	if (element) {
	    setTimeout(function () { try { element.focus(); } catch (ignore) {} }, 0);
	}
    }
    
});

lcg.Widget = Class.create(lcg.KeyHandler, {
    /* Generic base class for all LCG JavaScript widgets.
     * 
     */ 
    initialize: function ($super, element_id) {
	$super();
	this.element = $(element_id);
	this.element._lcg_widget_instance = this;
    }
});

lcg.Menu = Class.create(lcg.Widget, {
    /* Generic base class for several other menu-like widgets.
     * 
     * The code here traverses the menu structure, initializes connections
     * between the hierarchical items, assigns ARIA roles to HTML tags and
     * binds keyboard event handling to support keyboard menu traversal.
     * 
     */
    _MANAGE_TABINDEX: true,
    
    initialize: function ($super, element_id) {
	$super(element_id);
	this.element.setAttribute('role', 'application');
	// Go through the menu and assign aria roles and key bindings.
	var ul = this.element.down('ul');
	this.items = this.init_items(ul, null);
	// Set the active item.
	var active = this.initially_active_item();
	if (active) {
	    this.activate_item(active);
	}
    },

    init_items: function (ul, parent) {
	var items = [];
	var base_id;
	if (parent === null) {
	    base_id = this.element.getAttribute('id')+'-item';
	} else {
	    base_id = parent.getAttribute('id');
	}
	ul.childElements().each(function(li) {
	    if (li.nodeName === 'LI') {
		li.setAttribute('role', 'presentation');
		var item = li.down('a');
		var prev = (items.length === 0 ? null : items[items.length-1]);
		item.setAttribute('id', base_id + '.' + (items.length+1));
		this.init_item(item, prev, parent);
		items[items.length] = item;
	    }
	}.bind(this));
	return items;
    },

    init_item: function (item, prev, parent) {
	item.setAttribute('aria-selected', 'false');
	item.observe('keydown', this.on_key_down.bind(this));
	item.observe('click', this.on_menu_click.bind(this));
	item._lcg_menu_prev = prev;
	item._lcg_menu_next = null;
	item._lcg_menu_parent = parent;
	item._lcg_submenu = null;
	item._lcg_menu = this;
	if (this._MANAGE_TABINDEX) {
	    item.setAttribute('tabindex', '-1');
	}
	if (prev) {
	    prev._lcg_menu_next = item;
	}
    },
    
    initially_active_item: function () {
	var item;
	if (this.items.length !== 0) {
	    var current = this.element.down('a.current');
	    if (current) {
		item = current;
	    } else {
		item = this.items[0];
	    }
	} else {
	    item = null;
	}
	return item;
    },
    
    active_item: function () {
	var element_id = this.element.getAttribute('aria-activedescendant');
	return (element_id ? $(element_id) : null);
    },

    activate_item: function (item) {
	var previously_active_item = this.active_item();
	if (previously_active_item) {
	    if (this._MANAGE_TABINDEX) {
		previously_active_item.setAttribute('tabindex', '-1');
	    }
	    previously_active_item.setAttribute('aria-selected', 'false');
	}
	this.element.setAttribute('aria-activedescendant', item.getAttribute('id'));
	item.setAttribute('aria-selected', 'true');
	if (this._MANAGE_TABINDEX) {
	    item.setAttribute('tabindex', '0');
	}
    },

    focus: function () {
	var item = this.active_item();
	if (item) {
	    this.expand_item(item, true);
	    this.set_focus(item);
	}
    },
    
    expand_item: function (item, recourse) {
	return false;
    },

    on_menu_click: function (event) {
	var element = event.element();
	this.cmd_activate(element.nodeName === 'A' ? element : element.down('a'));
	event.stop();
    },
    
    cmd_prev: function (item) {
	this.set_focus(item._lcg_menu_prev);
    },

    cmd_next: function (item) {
	this.set_focus(item._lcg_menu_next);
    },
    
    cmd_activate: function (item) {
	return;
    }

});

lcg.Notebook = Class.create(lcg.Menu, {
    /* Notebook widget with tabs.
     *
     * This is the Javascript counterpart of the Python class `lcg.Notebook'.
     * The notebook has tabs at the top and there is a content page belonging to
     * each tab.  Switching the tabs switches the visible content below the tab
     * switcher.  There may be multiple instances on one page.
     *
     */
    COOKIE: 'lcg_last_notebook_tab',

    keymap: function () {
	return {
	    'Left':	    this.cmd_prev,
	    'Right':	    this.cmd_next,
	    'Enter':	    this.cmd_activate,
	    'Space':	    this.cmd_activate
	};
    },

    initially_active_item: function () {
	// The active item set in the python code (marked as 'current' in HTML)
	// has the highest precedence.
	var current = this.element.down('.notebook-switcher li a.current');
	if (current) {
	    return current;
	}
	return (this.current_location_active_item() || // the tab may be referenced by anchor.
		this.last_saved_active_item() || // the most recently active tab.
		this.items[0]); // finally the first item is used with the lowest precedence.
    },

    init_items: function ($super, ul, parent) {
	ul.setAttribute('role', 'tablist');
	return $super(ul, parent);
    },

    init_item: function ($super, item, prev, parent) {
	$super(item, prev, parent);
	item.setAttribute('role', 'tab');
	var href = item.getAttribute('href'); // The href always starts with '#'.
	var page = $(href.substr(1));
	item._lcg_notebook_page = page;
	page._lcg_notebook_item = item;
	page.down('h1,h2,h3,h4,h5,h6').hide();
	page.hide();
	page.addClassName('notebook-page');
	page.setAttribute('role', 'tabpanel');
	if (!page.getAttribute('id')) {
	    page.setAttribute('id', item.getAttribute('id') + '-tabpanel');
	}
	item.setAttribute('aria-controls', page.getAttribute('id'));
    },

    current_location_active_item: function() {
	// Get the active item if the anchor is part of the current location.
	var match = self.location.href.match('#');
	if (match) {
	    var parts = self.location.href.split('#', 2);
	    var page = this.element.down('#'+parts[1]);
	    if (page && page._lcg_notebook_item) {
		return page._lcg_notebook_item;
	    }
	}
    },

    last_saved_active_item: function() {
	// Get the active item saved most recently in a browser cookie.
	//
	// We remember the last tab only for one notebook (the one which was
	// last switched) to avoid polution of cookies with too many values).
	//
	// The HTML class should identify a particular Notebook widget and
	// should not change across requests, while its id is unique on a page,
	// but may not identify a particulat widget and may change across
	// requests.  So we use the class as a part of cookie value.
	//
	var cls = this.element.getAttribute('class');
	if (cls) {
	    var cookie = lcg.cookies.get(this.COOKIE);
	    if (cookie) {
		var parts = cookie.split(':', 2);
		if (parts[0] === cls) {
		    var page = this.element.down('#'+parts[1]);
		    if (page && page._lcg_notebook_item) {
			return page._lcg_notebook_item;
		    }
		}
	    }
	}
	return null;
    },

    activate_item: function ($super, item) {
	var i, callback, repeat;
	var previously_active_item = this.active_item();
	$super(item);
	if (previously_active_item !== item) {
	    if (previously_active_item) {
		previously_active_item.removeClassName('current');
		previously_active_item._lcg_notebook_page.hide();
	    }
	    item.addClassName('current');
	    var page = item._lcg_notebook_page;
	    var cls = this.element.getAttribute('class');
	    if (cls) {
		var cookie = cls+':'+item._lcg_notebook_page.getAttribute('id');
		lcg.cookies.set(this.COOKIE, cookie);
	    }
	    page.show();
	    var callbacks = lcg.Notebook._activation_callbacks[page.id];
	    if (callbacks) {
		for (i = callbacks.length - 1; i >= 0; i--) {
		    // Process in reverse to be able to simply remove callbacks
		    // which are not to be repeated.
		    callback = callbacks[i][0];
		    repeat = callbacks[i][1];
		    callback();
		    if (!repeat) {
			callbacks.splice(i, 1); // Remove the callback.
		    }
		}
	    }
	}
    },

    cmd_activate: function (item) {
	this.activate_item(item);
	this.set_focus(item._lcg_notebook_page);
    }

});

lcg.Notebook._activation_callbacks = {};

lcg.Notebook.on_activation = function (page, callback, repeat) {
    /* Register a callback to be called on notebook tab activation.
       
    Arguments: 
      page -- notebook page DOM element -- the div enclosing the
        notebook page contents
      callback -- javascript function to be called when the page is activated.
        The callbacked is always called once for the initally active tab in the
        notebook and then on each tab switch for the newly activated tab.
      repeat -- if true, the callback will be repeated on each activation, if
        false (by default), the callback will be called just once, when given
        tab is activated for the first time.

    Note: This is a class method, not an instance method, because the Notebook
    instance often doesn't exist yet, when the caller needs to register a
    callback.  The instance is created when the whole notebook contents (all
    tabs and pages) is available, while the registration is typically done by
    the objects which appear inside the notebook pages.

    */
    if (repeat === undefined) {
	repeat = false;
    }
    var callbacks = lcg.Notebook._activation_callbacks[page.id];
    if (!callbacks) {
	callbacks = [];
	lcg.Notebook._activation_callbacks[page.id] = callbacks;
    }
    callbacks[callbacks.length] = [callback, repeat];
};


lcg.FoldableTree = Class.create(lcg.Menu, {
    /* Foldable tree widget
     *
     * This is the Javascript counterpart of the Python class
     * `lcg.FoldableTree'.
     */ 

    initialize: function ($super, element_id, toggle_button_tooltip) {
	$super(element_id);
	this.element.setAttribute('role', 'tree');
	if (this.foldable && toggle_button_tooltip) {
	    var b = new Element('button',
				{'class': 'toggle-menu-expansion',
				 'title': toggle_button_tooltip});
	    this.element.down('ul').insert({after: b});
	    b.observe('click', this.on_toggle_expansion.bind(this));
	}
    },

    keymap: function () {
	return {
	    'Up':	    this.cmd_up,
	    'Down':         this.cmd_down,
	    'Shift-Up':	    this.cmd_prev,
	    'Shift-Down':   this.cmd_next,
	    'Shift-Right':  this.cmd_expand,
	    'Shift-Left':   this.cmd_collapse,
	    'Right':        this.cmd_expand,
	    'Left':         this.cmd_collapse,
	    'Escape':	    this.cmd_quit,
	    'Enter':	    this.cmd_activate,
	    'Space':	    this.cmd_activate
	};
    },
    
    init_items: function ($super, ul, parent) {
	ul.setAttribute('role', 'group');
	return $super(ul, parent);
    },
    
    init_item: function ($super, item, prev, parent) {
	$super(item, prev, parent);
	item.setAttribute('role', 'treeitem');
	var span = item.down('span');
	if (span) {
	    span.setAttribute('role', 'presentation');
	}
	var li = item.up('li');
	li.setAttribute('role', 'presentation');
	// Append hierarchical submenu if found.
	var submenu = li.down('ul');
	if (submenu) {
	    if (li.hasClassName('foldable')) {
		if (!submenu.getAttribute('id')) {
		    submenu.setAttribute('id', item.getAttribute('id') + '-submenu');
		}
		var hidden = (li.hasClassName('folded') ? 'true' : 'false');
		submenu.setAttribute('aria-hidden', hidden);
		var expanded = (li.hasClassName('folded') ? 'false' : 'true' );
		item.setAttribute('aria-expanded', expanded);
		item.setAttribute('aria-controls', submenu.getAttribute('id'));
		this.foldable = true;
	    }
	    item._lcg_submenu = this.init_items(submenu, item);
	}
    },
    
    toggle_item_expansion: function (item) {
	if (item) {
	    if (this.expanded) {
		this.collapse_item(item);
	    } else {
		this.expand_item(item);
	    }
	    if (item._lcg_submenu) {
		this.toggle_item_expansion(item._lcg_submenu[0]);
	    }
	    this.toggle_item_expansion(item._lcg_menu_next);
	}
    },
    
    expand_item: function (item, recourse) {
	var expanded = false;
	var li = item.up('li');
	if (li.hasClassName('folded')) {
	    li.removeClassName('folded');
	    li.down('ul').setAttribute('aria-hidden', 'false');
	    item.setAttribute('aria-expanded', 'true');
	    expanded = true;
	}
	if (recourse && item._lcg_menu_parent) {
	    this.expand_item(item._lcg_menu_parent, true);
	}
	return expanded;
    },
    
    collapse_item: function (item) {
	var li = item.up('li');
	if (li.hasClassName('foldable') && !li.hasClassName('folded')) {
	    li.addClassName('folded');
	    li.down('ul').setAttribute('aria-hidden', 'true');
	    item.setAttribute('aria-expanded', 'false');
	    return true;
	}
	return false;
    },
    
    next_item: function (item) {
	// Recursively find the next item in sequence by traversing the hierarchy.
	var next;
	if (item._lcg_menu_next) {
	    next = item._lcg_menu_next;
	} else if (item._lcg_menu_parent && item._lcg_menu_parent._lcg_menu === this) {
	    next = this.next_item(item._lcg_menu_parent);
	}
	return next;
    },
    
    cmd_up: function (item) {
	var target = null;
	if (item._lcg_menu_prev) {
	    target = item._lcg_menu_prev;
	    if (target._lcg_submenu && !target.up('li').hasClassName('folded')) {
		target = target._lcg_submenu[target._lcg_submenu.length-1];
	    }
	} else {
	    target = item._lcg_menu_parent;
	}
	this.set_focus(target);
    },

    cmd_down: function (item) {
	var target = null;
	if (item._lcg_submenu && !item.up('li').hasClassName('folded')) {
	    target = item._lcg_submenu[0];
	} else {
	    target = this.next_item(item);
	}
	this.set_focus(target);
    },

    cmd_expand: function (item) {
	if (!this.expand_item(item) && item._lcg_submenu) {
	    this.set_focus(item._lcg_submenu[0]);
	}
    },

    cmd_collapse: function (item) {
	if (!this.collapse_item(item)) {
	    this.set_focus(item._lcg_menu_parent);
	}
    },

    cmd_activate: function (item) {
	self.location = item.getAttribute('href');
    },

    cmd_quit: function (item) {
	this.set_focus($('main-heading'));
    },
    
    on_toggle_expansion: function (event) {
	this.toggle_item_expansion(this.items[0]);
	this.expanded = !this.expanded;
	var b = this.element.down('button.toggle-menu-expansion');
	if (this.expanded) {
	    b.addClassName('expanded');
	} else {
	    b.removeClassName('expanded');
	}
    },
    
    on_menu_click: function (event) {
	var element = event.element();
	if (element.nodeName === 'A' || element.nodeName === 'LI') {
	    // The inner SPAN has a left margin making space for folding controls.
	    // Then, if the user clicks inside the A or LI element, but not inside
	    // SPAN, folding controls were clicked.  The strange hack with the inner
	    // SPAN is needed to make folding work across browsers (particulartly
	    // MSIE).
	    var span = element.down('span');
	    var item = span.parentNode;
	    if (event.pointerX() < span.cumulativeOffset().left) {
		if (item.up('li').hasClassName('folded')) { 
		    this.expand_item(item);
		} else {
		    this.collapse_item(item);
		}
		event.stop();
	    }
	}
    }
    
});

lcg.PopupMenu = Class.create(lcg.Menu, {
    // Popup menu widget.
    
    initialize: function ($super, items) {
	// items -- array of menu items.  Each item is an object with the
	// following attributes:
	//   label -- item title (string)
	//   tooltip -- item description/tooltip (string, optional)
	//   uri -- URI where the item points to (string, optional)
	//   enabled -- if present and false, the item will be disabled (inactive)
        //   callback -- The JavaScript function to be called on item invocation.
        //     May be passed also as a string (function of given name will be 
	//     looked up in the current JavaScript name space).  The callback
        //     function will be called with the element on which the menu was
        //     invoked as the first argument.  Additional arguments may be
        //     optionally specified by 'callback_args'.
        //   callback_args -- Array of additional arguments to pass to the callback function
	// You will typically supply either uri or callback, but both can be used.
	var i, item, a, enabled;
	var ul = new Element('ul', {'role': 'presentation'});
	for (i = 0; i < items.length; i++) {
	    item = items[i];
	    a = new Element('a', {'href': '#', 'onclick': 'return false;'});
	    if (item.tooltip) {
		a.setAttribute('title', item.tooltip);
	    }
	    a._lcg_popup_menu_item_spec = item;
	    a.update(item.label);
	    enabled = (item.enabled === undefined || item.enabled);
	    ul.insert(new Element('li', (enabled ? {'class': 'active'} : {})).update(a));
	}
	var menu = new Element('div', {'class': 'popup-menu-widget'});
	menu.insert(new Element('div', {'role': 'menu'}).update(ul));
	$(document.body).insert(menu);
	$super(menu);
    },

    init_item: function ($super, item, prev, parent) {
	$super(item, prev, parent);
	item.setAttribute('role', 'menuitem');
    },

    keymap: function () {
	return {
	    'Up':     this.cmd_prev,
	    'Down':   this.cmd_next,
	    'Enter':  this.cmd_activate,
	    'Space':  this.cmd_activate,
	    'Escape': this.cmd_quit
	};
    },

    cmd_activate: function (item) {
	var li = item.up('li');
	var spec, namespaces, func, context, i, args;
	if (li.hasClassName('active')) {
	    this.remove();
	    spec = item._lcg_popup_menu_item_spec;
	    var callback = spec.callback;
	    if (callback) {
		if (typeof callback === 'string') {
		    namespaces = callback.split(".");
		    func = namespaces.pop();
		    context = window;
		    for (i = 0; i < namespaces.length; i++) {
			context = context[namespaces[i]];
		    }
		    callback = context[func];
		}
		args = [this.popup_element];
		if (spec.callback_args) {
		    for (i = 0; i < spec.callback_args.length; i++) {
			args[i + 1] = spec.callback_args[i];
		    }
		}
		return callback.apply(this, args);
	    }
	    if (spec.uri) {
		self.location = spec.uri;
	    }
	}
    },

    cmd_quit: function (item) {
	this.remove();
	if (this.popup_element) {
	    this.set_focus(this.popup_element);
	}
    },

    on_document_click: function (event) {
	if (this.ignore_next_click) {
	    // The first click is the one which pops the menu up.
	    this.ignore_next_click = false;
	    return;
	}
	var outside = event.findElement('div') !== this.element;
	this.remove();
	if (outside) {
	    event.stop();
	}
    },
    
    popup: function (event, selected_item_index) {
        // event -- JavaScript event triggering the popup -- either a mouse
        //   action catched by 'contextmenu' handler or mouse/keyboard action
        //   catched by 'click' handler.
	// selected_item_index (optional) -- index of the menu item to be
	//   initially selected
	if (lcg.popup_menu) {
	    lcg.popup_menu.remove();
	}
	event.stop();
	var element = event.element();
	var left, top;
	if (event.clientX === event.pointerX() && event.clientY === event.pointerY()) {
	    left = event.pointerX();
	    top = event.pointerY();
	} else {
	    var offset = element.cumulativeOffset();
	    left = offset.left;
	    top = offset.top+10;
	}
	lcg.popup_menu = this;
	var menu = this.element;
	var window_size = document.viewport.getDimensions();
	if (left + menu.getWidth() > window_size.width) {
	    left = window_size.width - menu.getWidth() - 30;
	}
	if (top + menu.getHeight() > window_size.height) {
	    top -= menu.getHeight();
	}
	menu.setStyle({left: left+'px', top: top+'px', display: 'block'});
	this.popup_element = element;
	this.ignore_next_click = !event.isLeftClick();
	this.on_click_handler = this.on_document_click.bind(this);
	$(document).observe('click', this.on_click_handler);
	var active_item;
	if (selected_item_index !== undefined) {
	    active_item = menu.down('ul').childElements()[selected_item_index].down('a');
	} else {
	    active_item = menu.down('a');
	}
	this.activate_item(active_item);
	this.set_focus(active_item);
    },

    remove: function() {
	$(document).stopObserving('click', this.on_click_handler);
	this.element.remove();
	lcg.popup_menu = null;
    }
});

lcg.PopupMenuCtrl = Class.create({
    /* Control for invocation of a popup menu.
     *
     * This is the Javascript counterpart of the Python class
     * `lcg.PopupMenuCtrl'.  See its documentation for description of
     * constructor arguments.
     *
     */
    
    initialize: function (element_id, items, tooltip, selector) {
	this.items = items;
	var link = new Element('a', {'aria-haspopup': 'true'});
        $(element_id).insert(link);
        link.observe('click', this.popup_menu.bind(this));
        if (tooltip) {
     	    link.setAttribute('title', tooltip);
	}
        if (selector) {
      	    link.up(selector).observe('contextmenu', this.popup_menu.bind(this));
	}
    },

    popup_menu: function (event) { 
	var menu = new lcg.PopupMenu(this.items);
	menu.popup(event);
    }

});

lcg.Tooltip = Class.create({
    // Tooltip widget with asynchronlusly loaded content.
    // The content returned by the URL passed to constructor can be either an image or html
    // TODO: The class should be probably derived from lcg.Widget.

    initialize: function (uri) {
	// uri -- The URI from which the tooltip content should be loaded
	this.tooltip = null;
	this.show_when_ready = null;
	new Ajax.Request(uri, {
	    method: 'GET',
	    onSuccess: function(transport) {
		try {
		    var element = new Element('div', {'class': 'tooltip-widget'});
		    var content_type = transport.getHeader('Content-Type');
		    if (content_type === 'text/html') {
			element.update(transport.responseText);
		    } else if (content_type.substring(0, 6) === 'image/') {
			// The AJAX request was redundant in this case (the image will 
			// be loaded again by the browser for the new img tag) but 
			// there's no better way to tell automatically what the URL
			// points to and thanks to browser caching it should not
			// normally be a serious problem.
			element.insert(new Element('img', {'src': uri, 'border': 0,
							   'style': 'vertical-align: middle;'}));
		    } else {
			return;
		    }
		    element.hide(); // Necessary to make visible() work before first shown.
		    $(document.body).insert(element);
		    this.tooltip = element;
		    if (this.show_when_ready) {
			this.show(this.show_when_ready[0], this.show_when_ready[1]);
		    }
		} catch (e) {
		    // Errors in asynchronous handlers are otherwise silently
		    // ignored.  This will only work in Firefox with Firebug,
		    // but it is only useful for debugging anyway...
		    console.log(e);
		}
	    }.bind(this)
	});
    },

    show: function(x, y) {
	if (this.tooltip) {
	    var left = x + 3; // Show a little on right to avoid onmouseout and infinite loop.
	    var top = y  - this.tooltip.getHeight();
	    this.tooltip.setStyle({left: left+'px', top: top+'px', display: 'block'});
	    this.show_when_ready = null;
	} else {
	    this.show_when_ready = [x, y];
	}
    },

    hide: function() {
	if (this.tooltip) {
	    this.tooltip.hide();
	}
	this.show_when_ready = null;
    }

});


lcg.CollapsiblePane = Class.create(lcg.Widget, {
    /* Collapsible Pane.
     *
     * This is the Javascript counterpart of the Python class `lcg.CollapsiblePane'.
     * The panel content can be collapsed or expanded.  When collapsed, only a one
     * line panel title is displayed.  The title may be clicked to toggle the content
     * expansion state.
     *
     */
    initialize: function ($super, element_id, collapsed) {
	$super(element_id);
	var content = this.element.down('div.section-content');
	var heading = this.element.down('h1,h2,h3,h4,h5,h6,h7,h8');
	this.heading = heading;
	this.content = content;
	if (collapsed) {
	    this.element.addClassName('collapsed');
	    content.hide();
	} else {
	    this.element.addClassName('expanded');
	}
	heading.addClassName('collapsible-pane-heading');
	heading.on('click', function(event) {
	    this.toggle();
	    event.stop();
	}.bind(this));
	if (!content.getAttribute('id')) {
	    content.setAttribute('id', this.element.getAttribute('id') + '-collapsible-content');
	}
	heading.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
	heading.setAttribute('aria-controls', content.getAttribute('id'));
    },

    expanded: function() {
	return this.element.hasClassName('expanded');
    },

    expand: function() {
	this.element.removeClassName('collapsed');
	this.element.addClassName('expanded');
	this.heading.setAttribute('aria-expanded', 'true');
	if (Effect !== undefined) {
	    Effect.SlideDown(this.content, {duration: 0.2});
	} else {
	    this.content.show();
	}
    },

    collapse: function() {
	this.element.removeClassName('expanded');
	this.element.addClassName('collapsed');
	this.heading.setAttribute('aria-expanded', 'false');
	if (Effect !== undefined) {
	    Effect.SlideUp(this.content, {duration: 0.2});
	} else {
	    this.content.hide();
	}
    },

    toggle: function() {
	if (this.element.hasClassName('collapsed')) {
	    this.expand();
	} else {
	    this.collapse();
	}
    }
});


lcg.Cookies = Class.create({
    // This class is taken from 
    // http://codeinthehole.com/writing/javascript-cookie-objects-using-prototype-and-json/
    initialize: function (path, domain) {
        this.path = path || '/';
        this.domain = domain || null;
    },

    // Sets a cookie
    set: function (key, value, days) {
        if (typeof key !== 'string') { 
	    throw "Invalid key";
	}
        if (typeof value !== 'string' && typeof value !== 'number') {
	    throw "Invalid value";
	}
        if (days && typeof days !== 'number') {
	    throw "Invalid expiration time";
	}
	var cookie = escape(String(value)) + '; path=' + escape(this.path);
        if (days) {
            var date = new Date();
            date.setTime(date.getTime() + (days*24*60*60*1000));
            cookie += "; expires=" + date.toGMTString();
        }
        if (this.domain) {
	    cookie += '; domain=' + escape(this.domain);
	}
        document.cookie = key +'='+ cookie;
    },
    // Returns a cookie value or false
    get: function (key) {
        var value = false;
        document.cookie.split(';').invoke('strip').each(function(s) {
            if (s.startsWith(key+"=")) {
                value = unescape(s.substring(key.length+1, s.length));
                throw $break;
            }
        });
        return value;
    },
    // Clears a cookie
    clear: function (key) {
        this.set(key,'',-1);
    },
    // Clears all cookies
    clearAll: function () {
        document.cookie.split(';').collect(function (s) {
            return s.split('=').first().strip();
        }).each(function (key) {
            this.clear(key);
        }.bind(this));
    }

});

lcg.cookies = new lcg.Cookies();

lcg.popup_menu = null;

lcg.widget_instance = function(element) {
    /* Return a JavaScript widget instance for given DOM element or null.
     *
     * If given DOM element has an associated JavaScript widget instance,
     * return this instance or return null if the element doesn't belong to a
     * JavaScript widget.
     *
     */
    if (element && element._lcg_widget_instance) {
	return element._lcg_widget_instance;
    }
    return null;
};
