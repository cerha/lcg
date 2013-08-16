/* -*- coding: utf-8 -*-
 *
 * Copyright (C) 2012, 2013 Brailcom, o.p.s.
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

var lcg = new Object();

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
	if (code >= 65 && code <= 90) key = String.fromCharCode(code).toLowerCase();
	else key = map[code];
	if (key != null) {
	    var modifiers = '';
	    if (document.all || document.getElementById) {
		if (event.ctrlKey) modifiers += 'Ctrl-';
		if (event.altKey) modifiers += 'Alt-';
		if (event.shiftKey) modifiers += 'Shift-';
	    } else if (document.layers) {
		if (event.modifiers & Event.CONTROL_MASK) modifiers += 'Ctrl-';
		if (event.modifiers & Event.ALT_MASK) modifiers += 'Alt-';
		if (event.modifiers & Event.SHIFT_MASK) modifiers += 'Shift-';
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
	};
    },

    set_focus: function (element) {
	if (element != null) 
	    setTimeout(function () { try { element.focus(); } catch (e) {} }, 0);
    }
    
});

lcg.Menu = Class.create(lcg.KeyHandler, {
    /* Generic base class for several other menu-like widgets.
     * 
     * The code here traverses the menu structure, initializes connections
     * between the hierarchical items, assigns ARIA roles to HTML tags and
     * binds keyboard event handling to support keyboard menu traversal.
     * 
     */ 
    
    initialize: function ($super, element_id) {
	$super();
	var node = this.node = $(element_id);
	node._lcg_widget_instance = this;
	node.setAttribute('role', 'application');
	// Go through the menu and assign aria roles and key bindings.
	var ul = node.down('ul');
	this.items = this.init_items(ul, null);
	// Set the active item.
	var active = this.initially_active_item();
	if (active != null)
	    this.activate_item(active);
    },

    init_items: function (ul, parent) {
	var items = [];
	var base_id;
	if (parent == null)
	    base_id = this.node.getAttribute('id')+'-item';
	else
	    base_id = parent.getAttribute('id');
	for (var i = 0; i < ul.childNodes.length; i++) {
	    var child = $(ul.childNodes[i]);
	    if (child.nodeName == 'LI') {
		var prev = (items.length == 0 ? null : items[items.length-1]);
		var id = base_id + '.' + (items.length+1);
		this.init_item(child, id, prev, parent);
		items[items.length] = child;
	    }
	}
	return items;
    },

    init_item: function (li, id, prev, parent) {
	var link = li.down('a');
	link.setAttribute('tabindex', '-1');
	li.setAttribute('role', 'presentation');
	li.setAttribute('id', id);
	li.setAttribute('tabindex', '-1');
	li._lcg_menu_prev = prev;
	li._lcg_menu_next = null;
	li._lcg_menu_parent = parent;
	li._lcg_submenu = null;
	li._lcg_menu = this;
	if (prev != null)
	    prev._lcg_menu_next = li;
	li.observe('keydown', this.on_key_down.bind(this));
    },
    
    initially_active_item: function () {
	if (this.items.length != 0) {
	    var current = this.node.down('a.current');
	    if (current)
		return current.up('li');
	    else
		return this.items[0];
	} else {
	    return null;
	}
    },
    
    active_item: function () {
	var element_id = this.node.getAttribute('aria-activedescendant');
	return (element_id ? $(element_id) : null);
    },

    activate_item: function (item) {
	var previously_active_item = this.active_item()
	if (previously_active_item != null)
	    previously_active_item.setAttribute('tabindex', '-1');
	this.node.setAttribute('aria-activedescendant', item.getAttribute('id'));
	item.setAttribute('tabindex', '0');
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
    
    cmd_prev: function (item) {
	this.set_focus(item._lcg_menu_prev);
    },

    cmd_next: function (item) {
	this.set_focus(item._lcg_menu_next);
    },
    
    cmd_activate: function (item) {
    }

});

lcg.NotebookMenu = Class.create(lcg.Menu, {
    /* Notebook menu widget with tabs.
     *  
     * This class is only intended for static notebook-like menus.  The widget
     * has tabs but doesnt's care about their content.  Clicking a tab invokes
     * the underlying link URL.  See also 'Notebook' for an interactive
     * notebook widget switching the tab contents on tab click.
     *
     */

    init_items: function ($super, ul, parent) {
	ul.setAttribute('role', 'tablist');
	return $super(ul, parent);
    },

    init_item: function ($super, li, id, prev, parent) {
	$super(li, id, prev, parent);
	li.setAttribute('role', 'tab');
	li.down('a').onclick = (function() { this.cmd_activate(li); return false; }).bind(this);
    },
    
    keymap: function () {
	return {
	    'Left':	    this.cmd_prev,
	    'Right':	    this.cmd_next,
	    'Enter':	    this.cmd_activate,
	    'Space':	    this.cmd_activate
	};
    },

    cmd_activate: function (item) {
	self.location = item.down('a').getAttribute('href');
    }

});

lcg.Notebook = Class.create(lcg.NotebookMenu, {
    /* Notebook widget with tabs.
     *
     * This is the Javascript counterpart of the Python class `lcg.Notebook'.
     * The notebook has tabs at the top and there is a content page belonging to
     * each tab.  Switching the tabs switches the visible content below the tab
     * switcher.  There may be multiple instances on one page.
     *
     */ 
    COOKIE: 'lcg_last_notebook_tab',

    initially_active_item: function () {
	// The active item set in the python code (marked as 'current' in HTML)
	// has the highest precedence.
	var current = this.node.down('.notebook-switcher li a.current');
	if (current)
	    return current.up('li');
	else
	    return (this.current_location_active_item() || // the tab may be referenced by anchor.
		    this.last_saved_active_item() || // the most recently active tab.
		    this.items[0]); // finally the first item is used with the lowest precedence.
    },


    init_item: function ($super, li, id, prev, parent) {
	$super(li, id, prev, parent);
	var link = li.down('a');
	var href = link.getAttribute('href'); // The href always starts with '#'.
	var page = $('section-'+href.substr(1));
	li._lcg_notebook_page = page;
	page._lcg_notebook_item = li;
	page.down('h1,h2,h3,h4,h5,h6').hide();
	page.hide();
	page.addClassName('notebook-page');
    },

    current_location_active_item: function() {
	// Get the active item if the anchor is part of the current location.
	var match = self.location.href.match('#');
	if (match != null) {
	    var parts = self.location.href.split('#', 2);
	    var page = this.node.down('#section-'+parts[1]);
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
	var cls = this.node.getAttribute('class');
	if (cls) {
	    var cookie = lcg.cookies.get(this.COOKIE);
	    if (cookie) {
		var parts = cookie.split(':', 2);
		if (parts[0] == cls) {
		    var page = this.node.down('#'+parts[1]);
		    if (page && page._lcg_notebook_item) {
			return page._lcg_notebook_item;
		    }
		}
	    }
	}
	return null;
    },

    activate_item: function ($super, item) {
	var previously_active_item = this.active_item()
	$super(item);
	if (previously_active_item != item) {
	    if (previously_active_item) {
		previously_active_item.down('a').removeClassName('current');
		previously_active_item._lcg_notebook_page.hide();
	    }
	    item.down('a').addClassName('current');
	    var page = item._lcg_notebook_page;
	    var cls = this.node.getAttribute('class');
	    if (cls) {
		var cookie = cls+':'+item._lcg_notebook_page.getAttribute('id');
		lcg.cookies.set(this.COOKIE, cookie);
	    }
	    page.show();
	    var callbacks = lcg.Notebook._activation_callbacks[page.id];
	    if (callbacks)
		for (var i = callbacks.length - 1; i >= 0; i--) {
		    // Process in reverse to be able to simply remove callbacks
		    // which are not to be repeated.
		    var callback = callbacks[i][0];
		    var repeat = callbacks[i][1];
		    callback()
		    if (!repeat)
			callbacks.splice(i, 1); // Remove the callback.
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
    if (typeof repeat == 'undefined')
	repeat = false;
    var callbacks = lcg.Notebook._activation_callbacks[page.id];
    if (!callbacks)
	var callbacks = lcg.Notebook._activation_callbacks[page.id] = [];
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
	this.node.setAttribute('role', 'tree');
	if (this.foldable && toggle_button_tooltip) {
	    var b = new Element('button',
				{'class': 'toggle-menu-expansion',
				 'title': toggle_button_tooltip});
	    this.node.down('ul').insert({after: b});
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
    
    init_item: function ($super, li, id, prev, parent) {
	$super(li, id, prev, parent);
	li.down('a').setAttribute('role', 'presentation');
	li.observe('click', this.on_menu_click.bind(this));
	li.setAttribute('role', 'treeitem');
	var span = li.down('span');
	if (span != null)
	    span.setAttribute('role', 'presentation');
	// Append hierarchical submenu if found.
	var submenu = li.down('ul');
	if (submenu != null) {
	    if (li.hasClassName('foldable')) {
		var hidden = (li.hasClassName('folded') ? 'true' : 'false');
		submenu.setAttribute('aria-hidden', hidden);
		var expanded = (li.hasClassName('folded') ? 'false' : 'true' );
		li.setAttribute('aria-expanded', expanded);
		this.foldable = true;
	    }
	    li._lcg_submenu = this.init_items(submenu, li);
	}
    },
    
    toggle_item_expansion: function (item) {
	if (item != null) {
	    if (this.expanded)
		this.collapse_item(item);
	    else
		this.expand_item(item);
	    if (item._lcg_submenu != null)
		this.toggle_item_expansion(item._lcg_submenu[0]);
	    this.toggle_item_expansion(item._lcg_menu_next);
	}
    },
    
    expand_item: function (item, recourse) {
	var expanded = false;
	if (item.hasClassName('folded')) {
	    item.removeClassName('folded');
	    item.down('ul').setAttribute('aria-hidden', 'false');
	    item.setAttribute('aria-expanded', 'true');
	    expanded = true;
	}
	if (recourse && item._lcg_menu_parent != null)
	    this.expand_item(item._lcg_menu_parent, true);
	return expanded;
    },
    
    collapse_item: function (item) {
	if (item.hasClassName('foldable') && !item.hasClassName('folded')) {
	    item.addClassName('folded');
	    item.down('ul').setAttribute('aria-hidden', 'true');
	    item.setAttribute('aria-expanded', 'false');
	    return true;
	}
	return false;
    },
    
    next_item: function (item) {
	// Recursively find the next item in sequence by traversing the hierarchy.
	var next;
	if (item._lcg_menu_next != null)
	    next = item._lcg_menu_next;
	else if (item._lcg_menu_parent != null
		 && item._lcg_menu_parent._lcg_menu == this)
	    next = this.next_item(item._lcg_menu_parent);
	return next;
    },
    
    cmd_up: function (item) {
	var target = null;
	if (item._lcg_menu_prev != null) {
	    target = item._lcg_menu_prev;
	    if (target._lcg_submenu != null && !target.hasClassName('folded'))
		target = target._lcg_submenu[target._lcg_submenu.length-1];
	} else {
	    target = item._lcg_menu_parent;
	}
	this.set_focus(target);
    },

    cmd_down: function (item) {
	var target = null;
	if (item._lcg_submenu != null && !item.hasClassName('folded'))
	    target = item._lcg_submenu[0];
	else
	    target = this.next_item(item);
	this.set_focus(target);
    },

    cmd_expand: function (item) {
	if (!this.expand_item(item) && item._lcg_submenu != null)
	    this.set_focus(item._lcg_submenu[0]);
    },

    cmd_collapse: function (item) {
	if (!this.collapse_item(item))
	    this.set_focus(item._lcg_menu_parent);
    },

    cmd_activate: function (item) {
	self.location = item.down('a').getAttribute('href');
    },

    cmd_quit: function (item) {
	this.set_focus($('main-heading'));
    },
    
    on_toggle_expansion: function (event) {
	this.toggle_item_expansion(this.items[0]);
	this.expanded = !this.expanded;
	var b = this.node.down('button.toggle-menu-expansion');
	if (this.expanded)
	    b.addClassName('expanded');
	else
	    b.removeClassName('expanded');
    },
    
    on_menu_click: function (event) {
	var element = event.element();
	if (element.nodeName == 'A' || element.nodeName == 'LI') {
	    // The inner SPAN has a left margin making space for folding controls.
	    // Then, if the user clicks inside the A or LI element, but not inside
	    // SPAN, folding controls were clicked.  The strange hack with the inner
	    // SPAN is needed to make folding work across browsers (particulartly
	    // MSIE).
	    var span = element.down('span');
	    var item = span.parentNode.parentNode;
	    if (event.pointerX() < span.cumulativeOffset().left) {
		if (item.hasClassName('folded'))
		    this.expand_item(item);
		else
		    this.collapse_item(item);
		event.stop();
	    }
	}
    }
    
});

lcg.PopupMenu = Class.create(lcg.Menu, {
    // Popup menu widget.
    
    initialize: function ($super, items) {
	// items -- array of menu items.  Each item is a dictionary with the
	// following keys:
	//   label -- item title (string)
	//   tooltip -- item description/tooltip (string, optional)
	//   uri -- URI where the item points to (string, optional)
	//   enabled -- if present and false, the item will be disabled (inactive)
	//   onclick -- JavaScript code to execute on invocation (string, optional)
	// You will typically supply either onclick or href.
	var ul = new Element('ul');
	for (var i = 0; i < items.length; i++) {
	    var item = items[i];
	    var a = new Element('a', {'href': item.uri, 
				      'title': item.tooltip, 
				      'onclick': item.onclick});
	    a.update(item.label);
	    var enabled = (typeof item.enabled == 'undefined' || item.enabled);
	    ul.insert(new Element('li', (enabled ? {'class': 'active'} : {})).update(a));
	}
	var menu = new Element('div', {'class': 'popup-menu-widget'});
	menu.insert(ul)
	$(document.body).insert(menu);
	$super(menu);
    },

    init_items: function ($super, ul, parent) {
	ul.setAttribute('role', 'menu');
	return $super(ul, parent);
    },

    init_item: function ($super, li, id, prev, parent) {
	$super(li, id, prev, parent);
	li.setAttribute('role', 'menuitem');
	li.down('a').onclick = (function() { this.cmd_activate(li); return false; }).bind(this);
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
	this.remove();
	self.location = item.down('a').getAttribute('href');
    },

    cmd_quit: function (item) {
	this.remove();
	if (this.return_keyboard_focus != null)
	    this.set_focus(this.return_keyboard_focus);
    },

    on_document_click: function (event) {
	if (this.ignore_next_click) {
	    // The first click is the one which pops the menu up.
	    this.ignore_next_click = false;
	    return;
	}
	var outside = event.findElement('div') != this.node;
	this.remove();
	if (outside)
	    event.stop();
    },
    
    popup: function (event) {
        // event -- JavaScript event triggering the popup -- either a mouse
        // action catched by 'contextmenu' handler or mouse/keyboard action
        // catched by 'click' handler.
	if (lcg.popup_menu)
	    lcg.popup_menu.remove();
	event.stop();
	var left, top;
	if (event.pointerX() >=0 && event.pointerY() >= 0) {
	    this.return_keyboard_focus = null;
	    left = event.pointerX();
	    top = event.pointerY();
	} else {
	    this.return_keyboard_focus = event.element();
	    var pos = event.element().cumulativeOffset();
	    left = pos.left;
	    top = pos.top+10;
	}
	lcg.popup_menu = this;
	var menu = this.node;
	var window_size = document.viewport.getDimensions();
	if (left + menu.getWidth() > window_size.width)
	    left = window_size.width - menu.getWidth() - 30;
	if (top + menu.getHeight() > window_size.height)
	    top -= menu.getHeight();
	menu.setStyle({left: left+'px', top: top+'px', display: 'block'});
	this.ignore_next_click = !event.isLeftClick();
	if (this.return_keyboard_focus != null)
	    this.set_focus(menu.down('li'));
	this.on_click_handler = this.on_document_click.bind(this)
	$(document).observe('click', this.on_click_handler);
    },

    remove: function() {
	$(document).stopObserving('click', this.on_click_handler);
	this.node.remove();
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
	this.items = items
	var link = new Element('a', {href: '#'});
        $(element_id).insert(link);
        link.observe('click', this.popup_menu.bind(this));
        if (tooltip)
     	    link.setAttribute('title', tooltip);
        if (selector)
      	    link.up(selector).observe('contextmenu', this.popup_menu.bind(this));
    },

    popup_menu: function (event) { 
	var menu = new lcg.PopupMenu(this.items);
	menu.popup(event);
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
        if (typeof key != 'string') throw "Invalid key";
        if (typeof value != 'string' && typeof value != 'number') throw "Invalid value";
        if (days && typeof days != 'number') throw "Invalid expiration time";
	var cookie = escape(new String(value)) + '; path=' + escape(this.path);
        if (days) {
            var date = new Date();
            date.setTime(date.getTime() + (days*24*60*60*1000));
            cookie += "; expires=" + date.toGMTString();
        }
        if (this.domain)
	    cookie += '; domain=' + escape(this.domain);
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
    if (element._lcg_widget_instance)
	return element._lcg_widget_instance;
    else
	return null;
};
