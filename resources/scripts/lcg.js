/* -*- coding: utf-8 -*-
 *
 * Copyright (C) 2012-2018 OUI Technology Ltd.
 * Copyright (C) 2019 Tomáš Cerha <t.cerha@gmail.com>
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
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

/* eslint no-unused-vars: 0 */
/* global Class, Event, Element, Ajax, Effect, $, $break, self, escape, unescape, console */
/* global jQuery */

"use strict";

var lcg = {};

lcg.KeyHandler = Class.create({

    initialize: function () {
        this._keymap = this._define_keymap();
    },

    _define_keymap: function () {
        return {};
    },

    _event_key: function (event) {
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

    _on_key_down: function (event) {
        var key_name = this._event_key(event);
        var command = this._keymap[key_name];
        if (command) {
            command.bind(this)(event, event.element());
            if (!event.stopped) {
                event.stop();
            }
        }
    },

    _set_focus: function (element) {
        if (element) {
            setTimeout(function () { try { element.focus(); } catch (e) { /* ignore */ } }, 0);
        }
    }

});

lcg.Widget = Class.create(lcg.KeyHandler, {
    /* Generic base class for all LCG JavaScript widgets.
     *
     * Constructor arguments:
     *
     *   element_id -- HTML id of the widget root element as a string.
     *     May also be the element itself as Prototype.js Element instance.
     *
     */
    initialize: function ($super, element_id) {
        $super();
        this.element = $(element_id);
        this.element._lcg_widget_instance = this;
    }
});

lcg.Button = Class.create(lcg.Widget, {
    /* LCG JavaScript Button widget handler.
     *
     * Constructor arguments:
     *
     *   element_id -- HTML id of the widget root element as a string.
     *     May also be the element itself as Prototype.js Element instance.
     *   callback -- The JavaScript function to be called on item invocation.
     *     May be passed also as a string (function of given name will be
     *     looked up in the current JavaScript name space).  The callback
     *     function will be called with the Button widget instance
     *     as the first argument.
     */
    initialize: function ($super, element_id, callback) {
        var i;
        $super(element_id);
        if (typeof callback === 'string') {
            var namespaces = callback.split(".");
            var func = namespaces.pop();
            var context = window;
            for (i = 0; i < namespaces.length; i++) {
                context = context[namespaces[i]];
            }
            callback = context[func];
        }
        if (callback) {
            this.element.down('button').on('click', function (event) {
                callback(this);
                event.stop();
            }.bind(this));
        }
    }

});

lcg.Menu = Class.create(lcg.Widget, {
    /* Generic base class for several other menu-like widgets.
     *
     * Constructor arguments:
     *
     *   element_id -- HTML id of the widget root element (described in the parent class).
     *
     * The menu structure is traversed on instance creation and connections
     * between the hierarchical items are initialized, ARIA roles are assigned
     * to HTML elements and event handling is established.
     *
     * Accessibility is supported through automatically managed ARIA roles
     * and states and handling keyboard menu traversal.
     *
     */
    _MANAGE_TABINDEX: true,

    initialize: function ($super, element_id) {
        $super(element_id);
        var ul = this.element.down('ul');
        if (ul) {
            this._init_menu(ul);
        }
    },

    _init_menu: function (ul) {
        // Go through the menu and assign aria roles and key bindings.
        this.items = this._init_items(ul, null);
        // Set the active item.
        var selected = this._initially_selected_item();
        if (selected) {
            this._select_item(selected);
        }
    },

    _init_items: function (ul, parent) {
        var items = [];
        var base_id;
        if (parent === null) {
            base_id = this.element.getAttribute('id')+'-item';
        } else {
            base_id = parent.getAttribute('id');
        }
        ul.childElements().each(function (li) {
            if (li.nodeName === 'LI') {
                li.setAttribute('role', 'presentation');
                var item = li.down('a');
                var prev = (items.length === 0 ? null : items[items.length-1]);
                item.setAttribute('id', base_id + '.' + (items.length+1));
                this._init_item(item, prev, parent);
                items[items.length] = item;
            }
        }.bind(this));
        return items;
    },

    _init_item: function (item, prev, parent) {
        item.setAttribute('aria-selected', 'false');
        item.observe('keydown', this._on_key_down.bind(this));
        item.observe('click', function (event) { this._on_item_click(event, item); }.bind(this));
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

    _initially_selected_item: function () {
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

    _selected_item: function () {
        // The attribute aria-activedescendant may not always be on the root element.
        var element = this.element.down('*[aria-activedescendant]') || this.element;
        var id = element.getAttribute('aria-activedescendant');
        return (id ? $(id) : null);
    },

    _select_item: function (item) {
        var previously_selected_item = this._selected_item();
        // The attribute aria-activedescendant may not always be on the root element.
        var element = this.element.down('*[aria-activedescendant]') || this.element;
        element.setAttribute('aria-activedescendant', item.getAttribute('id'));
        if (item.hasAttribute('aria-selected')) {
            // Note: Derived classes (Wiking's MainMenu) may unset
            // 'aria-selected' because they are using ARIA roles which
            // don't support the aria-selected attribute.  So we
            // manipulate this attribute only when already set.
            item.setAttribute('aria-selected', 'true');
            if (previously_selected_item) {
                previously_selected_item.setAttribute('aria-selected', 'false');
            }
        }
        if (this._MANAGE_TABINDEX) {
            item.setAttribute('tabindex', '0');
            if (previously_selected_item) {
                previously_selected_item.setAttribute('tabindex', '-1');
            }
        }
    },

    _expand_item: function (item) {
        return false;
    },

    _on_item_click: function (event, item) {
        this._cmd_activate(event, item);
        event.stop();
    },

    _cmd_prev: function (event, item) {
        this._set_focus(item._lcg_menu_prev);
    },

    _cmd_next: function (event, item) {
        this._set_focus(item._lcg_menu_next);
    },

    _cmd_activate: function (event, item) {
        return;
    },

    focus: function () {
        var item = this._selected_item();
        if (item) {
            this._expand_item(item);
            this._set_focus(item);
        }
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
    _COOKIE: 'lcg_last_notebook_tab',

    _define_keymap: function () {
        return {
            'Left':         this._cmd_prev,
            'Right':        this._cmd_next,
            'Enter':        this._cmd_activate,
            'Space':        this._cmd_activate
        };
    },

    _initially_selected_item: function () {
        // The selected item set in the python code (marked as 'current' in HTML)
        // has the highest precedence.
        var current = this.element.down('.notebook-switcher li a.current');
        if (current) {
            return current;
        }
        return (this._current_location_selected_item() || // the tab may be referenced by anchor.
                this._last_saved_selected_item() || // the most recently selected tab.
                this.items[0]); // finally the first item is used with the lowest precedence.
    },

    _init_items: function ($super, ul, parent) {
        ul.setAttribute('role', 'tablist');
        return $super(ul, parent);
    },

    _init_item: function ($super, item, prev, parent) {
        $super(item, prev, parent);
        item.setAttribute('role', 'tab');
        var href = item.href; // The href always contains the '#', in MSIE 8 it is even a full asolute URI.
        var page = $(href.substr(href.indexOf('#') + 1));
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

    _current_location_selected_item: function () {
        // Get the selected item if the anchor is part of the current location.
        var match = self.location.href.match('#.+');
        if (match) {
            var parts = self.location.href.split('#', 2);
            var page = this.element.down('#'+parts[1]);
            if (page && page._lcg_notebook_item) {
                return page._lcg_notebook_item;
            }
        }
    },

    _last_saved_selected_item: function () {
        /* Get the selected item saved most recently in a browser cookie.
         *
         * We remember the last tab only for one notebook (the one which was
         * last switched) to avoid polution of cookies with too many values).
         *
         * The HTML class should identify a particular Notebook widget and
         * should not change across requests, while its id is unique on a page,
         * but may not identify a particulat widget and may change across
         * requests.  So we use the class as a part of cookie value.
         *
         */
        var cls = this.element.getAttribute('class');
        if (cls) {
            var cookie = lcg.cookies.get(this._COOKIE);
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

    _select_item: function ($super, item) {
        var i, callback, repeat;
        var previously_selected_item = this._selected_item();
        $super(item);
        if (previously_selected_item !== item) {
            if (previously_selected_item) {
                previously_selected_item.removeClassName('current');
                previously_selected_item._lcg_notebook_page.hide();
            }
            item.addClassName('current');
            var page = item._lcg_notebook_page;
            var cls = this.element.getAttribute('class');
            if (cls) {
                var cookie = cls+':'+item._lcg_notebook_page.getAttribute('id');
                lcg.cookies.set(this._COOKIE, cookie);
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

    _cmd_activate: function (event, item) {
        this._select_item(item);
        this._set_focus(item._lcg_notebook_page);
    }

});

lcg.Notebook._activation_callbacks = {};

lcg.Notebook.on_activation = function (page, callback, repeat) {
    /* Register a callback to be called on notebook tab activation.
     *
     * Arguments:
     *   page -- notebook page DOM element -- the div enclosing the
     *     notebook page contents
     *   callback -- javascript function to be called when the page is activated.
     *     The callbacked is always called once for the initally active tab in the
     *     notebook and then on each tab switch for the newly activated tab.
     *   repeat -- if true, the callback will be repeated on each activation, if
     *     false (by default), the callback will be called just once, when given
     *     tab is activated for the first time.
     *
     * Note: This is a class method, not an instance method, because the Notebook
     * instance often doesn't exist yet, when the caller needs to register a
     * callback.  The instance is created when the whole notebook contents (all
     * tabs and pages) is available, while the registration is typically done by
     * the objects which appear inside the notebook pages.
     *
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
        this._foldable = false;
        this._expanded = false;
        $super(element_id);
        this.element.setAttribute('role', 'tree');
        if (this._foldable && toggle_button_tooltip) {
            var b = new Element('button', {
                'class': 'toggle-menu-expansion',
                'title': toggle_button_tooltip
            });
            this.element.down('ul').insert({after: b});
            b.observe('click', this._on_toggle_full_expansion.bind(this));
        }
    },

    _define_keymap: function () {
        // Arrow keys are duplicated with Ctrl-Shift- to get them accessible to VoiceOver
        // users as VO doesn't pass single arrow keypresses to the application.
        return {
            'Up': this._cmd_up,
            'Ctrl-Shift-Up': this._cmd_up,
            'Down': this._cmd_down,
            'Ctrl-Shift-Down': this._cmd_down,
            'Shift-Up': this._cmd_prev,
            'Shift-Shift-Down': this._cmd_next,
            'Shift-Right': this._cmd_expand,
            'Shift-Left': this._cmd_collapse,
            'Right': this._cmd_expand,
            'Ctrl-Shift-Right': this._cmd_expand,
            'Left': this._cmd_collapse,
            'Ctrl-Shift-Left': this._cmd_collapse,
            'Escape': this._cmd_quit,
            'Enter': this._cmd_activate,
            'Space': this._cmd_activate
        };
    },

    _init_items: function ($super, ul, parent) {
        ul.setAttribute('role', 'group');
        return $super(ul, parent);
    },

    _init_item: function ($super, item, prev, parent) {
        $super(item, prev, parent);
        item.setAttribute('role', 'treeitem');
        var icon = item.down('.icon');
        if (icon) {
            icon.setAttribute('role', 'presentation');
        }
        var label = item.down('.label');
        if (label) {
            // Needed for VoiceOver to read the labels after adding the icon span
            // inside the a tag (because of MSIE as described in widgets.py...).
            var label_id = item.getAttribute('id') + '-label';
            label.setAttribute('id', label_id);
            item.setAttribute('aria-labelledby', label_id);
        }
        var li = item.up('li');
        // Append hierarchical submenu if found.
        var submenu = li.down('ul');
        if (submenu) {
            if (li.hasClassName('foldable')) {
                if (!submenu.getAttribute('id')) {
                    submenu.setAttribute('id', item.getAttribute('id') + '-submenu');
                }
                item.setAttribute('aria-controls', submenu.getAttribute('id'));
                var expander = li.down('.expander');
                expander.setAttribute('aria-controls', submenu.getAttribute('id'));
                expander.on('click', this._on_expander_click.bind(this));
                this._update_item(item, li.hasClassName('expanded'));
                this._foldable = true;
            }
            item._lcg_submenu = this._init_items(submenu, item);
        }
    },

    _update_item: function (item, expanded) {
        var li = item.up('li');
        var submenu = li.down('ul');
        var expander = li.down('.expander');
        var label = expander.getAttribute(expanded ? 'data-collapse-label' : 'data-expand-label');
        if (expanded) {
            li.removeClassName('collapsed');
            li.addClassName('expanded');
        } else {
            li.removeClassName('expanded');
            li.addClassName('collapsed');
        }
        submenu.setAttribute('aria-hidden', expanded ? 'false' : 'true');
        item.setAttribute('aria-expanded', expanded ? 'true' : 'false');

        expander.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        expander.setAttribute('title', label);
        expander.down('.label').innerHTML = label;
    },

    _expand_item: function (item) {
        var expanded = false;
        if (item.up('li').hasClassName('collapsed')) {
            this._update_item(item, true);
            expanded = true;
        }
        if (item._lcg_menu_parent) {
            this._expand_item(item._lcg_menu_parent);
        }
        return expanded;
    },

    _collapse_item: function (item) {
        if (item.up('li').hasClassName('expanded')) {
            this._update_item(item, false);
            return true;
        }
        return false;
    },

    _toggle_expansion: function (item) {
        if (item.up('li').hasClassName('collapsed')) {
            this._expand_item(item);
        } else {
            this._collapse_item(item);
        }
    },

    _expand_recursively: function (item, expand) {
        if (expand) {
            this._expand_item(item);
        } else {
            this._collapse_item(item);
        }
        if (item._lcg_submenu) {
            this._expand_recursively(item._lcg_submenu[0], expand);
        }
        if (item._lcg_menu_next) {
            this._expand_recursively(item._lcg_menu_next, expand);
        }
    },

    _next_item: function (item) {
        // Recursively find the next item in sequence by traversing the hierarchy.
        var next;
        if (item._lcg_menu_next) {
            next = item._lcg_menu_next;
        } else if (item._lcg_menu_parent && item._lcg_menu_parent._lcg_menu === this) {
            next = this._next_item(item._lcg_menu_parent);
        }
        return next;
    },

    _cmd_up: function (event, item) {
        var target = null;
        if (item._lcg_menu_prev) {
            target = item._lcg_menu_prev;
            if (target._lcg_submenu && target.up('li').hasClassName('expanded')) {
                target = target._lcg_submenu[target._lcg_submenu.length-1];
            }
        } else {
            target = item._lcg_menu_parent;
        }
        this._set_focus(target);
    },

    _cmd_down: function (event, item) {
        var target = null;
        if (item._lcg_submenu && item.up('li').hasClassName('expanded')) {
            target = item._lcg_submenu[0];
        } else {
            target = this._next_item(item);
        }
        this._set_focus(target);
    },

    _cmd_expand: function (event, item) {
        if (!this._expand_item(item) && item._lcg_submenu) {
            this._set_focus(item._lcg_submenu[0]);
        }
    },

    _cmd_collapse: function (event, item) {
        if (!this._collapse_item(item)) {
            this._set_focus(item._lcg_menu_parent);
        }
    },

    _cmd_activate: function (event, item) {
        self.location = item.getAttribute('href');
    },

    _cmd_quit: function (event, item) {
        this._set_focus($('main-heading'));
    },

    _on_toggle_full_expansion: function (event) {
        this._expanded = !this._expanded;
        this._expand_recursively(this.items[0], this._expanded);
        var b = this.element.down('button.toggle-menu-expansion');
        if (this._expanded) {
            b.addClassName('expanded');
        } else {
            b.removeClassName('expanded');
        }
    },

    _on_item_click: function (event, item) {
        if (!event.findElement('.label')) {
            this._toggle_expansion(item);
            event.stop();
        }
    },

    _on_expander_click: function (event, expander) {
        this._toggle_expansion(expander.up('li').firstChild);
        event.stop();
    }

});


lcg.PopupMenuBase = Class.create(lcg.Menu, {

    initialize: function ($super, element_id) {
        $super(element_id);
        this._ignore_next_click = false;
    },

    _define_keymap: function () {
        return {
            'Up':     this._cmd_prev,
            'Down':   this._cmd_next,
            'Enter':  this._cmd_activate,
            'Space':  this._cmd_activate,
            'Escape': this._cmd_quit
        };
    },

    _cmd_quit: function (event, item) {
        this.dismiss();
    },

    _on_click: function (event) {
        var outside = event.findElement('div') !== this.element;
        if (this._ignore_next_click && !outside) {
            // The first click is the one which pops the menu up.
            this._ignore_next_click = false;
            return;
        }
        this.dismiss();
        if (outside) {
            event.stop();
        }
    },

    _on_touchend: function (event) {
        if (!this._touch_moved) {
            // Detect touch outside the menu div:
            if (event.findElement('div') !== this.element) {
                this.dismiss();
            } else {
                this._cmd_activate(event, event.findElement('a'));
            }
            event.stop();
        }
    },

    popup: function (element, x, y, direction, selected_item_index) {
        var active_menu = lcg.popup_menu;
        if (active_menu) {
            active_menu.dismiss();
            if (active_menu === this) {
                return;
            }
        }
        lcg.popup_menu = this;
        this._popup_element = element;
        var menu = this.element;
        var selected_item;
        if (selected_item_index !== undefined && selected_item_index !== null
            && selected_item_index !== -1) {
            selected_item = menu.down('ul').childElements()[selected_item_index].down('a');
        } else {
            selected_item = menu.down('a');
        }
        this._select_item(selected_item);
        menu.setAttribute('style', 'display: none;'); // Force consistent initial state;
        menu.setStyle({left: x + 'px', top: y + 'px'});
        if (Effect !== undefined) {
            if (direction === 'up') {
                var total_height = menu.getHeight();
                var css_height = menu.getLayout().get('height');
                menu.setStyle({height: 0, display: 'block', overflowY: 'hidden'});
                new Effect.Morph(menu, {
                    style: {
                        height: css_height + 'px',
                        top: y - total_height + 'px'
                    },
                    duration: 0.2,
                    afterFinish: function () {
                        menu.setStyle({overflowY: 'auto'});
                        this._set_focus(selected_item);
                    }.bind(this)
                });
            } else {
                menu.slideDown({
                    duration: 0.2,
                    afterFinish: function () {
                        this._set_focus(selected_item);
                    }.bind(this)
                });
            }
        } else {
            if (direction === 'up') {
                menu.setStyle({top: y - menu.getHeight() + 'px'});
            }
            menu.show();
            this._set_focus(selected_item);
        }
        this._on_touchstart_handler = function (e) { this._touch_moved = false; }.bind(this);
        this._on_touchmove_handler = function (e) { this._touch_moved = true; }.bind(this);
        this._on_touchend_handler = this._on_touchend.bind(this);
        this._on_click_handler = this._on_click.bind(this);
        $(document).observe('touchstart', this._on_touchstart_handler);
        $(document).observe('touchmove', this._on_touchmove_handler);
        $(document).observe('touchend', this._on_touchend_handler);
        $(document).observe('click', this._on_click_handler);
        if (element) {
            element.setAttribute('aria-expanded', 'true');
        }
    },

    dismiss: function () {
        $(document).stopObserving('touchstart', this._on_touchstart_handler);
        $(document).stopObserving('touchmove', this._on_touchmove_handler);
        $(document).stopObserving('touchend', this._on_touchend_handler);
        $(document).stopObserving('click', this._on_click_handler);
        this.element.hide();
        lcg.popup_menu = null;
        var element = this._popup_element;
        if (element) {
            element.setAttribute('aria-expanded', 'false');
            this._set_focus(element);
        }
    }

});

lcg.popup_menu = null;


lcg.PopupMenu = Class.create(lcg.PopupMenuBase, {
    /* Popup menu widget.
     *
     * Constructor arguments:
     *
     *   element_id -- HTML id of the widget root element (described in
     *     the parent class)
     *   items -- array of menu items as objects with the following attributes:
     *     label -- item title (string)
     *     tooltip -- item description/tooltip (string, optional)
     *     uri -- URI where the item points to (string, optional)
     *     enabled -- if present and false, the item will be disabled
     *       (inactive)
     *     callback -- The JavaScript function to be called on item invocation.
     *       May be passed also as a string (function of given name will be
     *       looked up in the current JavaScript name space).    The callback
     *       function will be called with the element on which the menu was
     *       invoked as the first argument.  Additional arguments may be
     *       optionally specified by 'callback_args'.
     *     callback_args -- Array of additional arguments to pass to the
     *       callback function
     *     icon -- CSS class name of item's icon (string, optional)
     *     cls -- CSS class name to be used for the item (string, optional)
     *   close_button_label -- if defined, the menu will have a close button
     *     with given label.  The close button is displayed at the top right
     *     corner, but comes as the last item in sequential navigation.  It
     *     is actually most needed for screen reader users on touch screen
     *     devices, such as iOS VoiceOver, where there is no other easilly
     *     discoverable way to close the menu (activating the PopupMenuCtrl
     *     again actually does it, but the user would have to go back through
     *     the menu items).
     *
     * You will typically supply either uri or callback, but both can be used
     * as well.
     *
     * This is the Javascript counterpart of the Python class
     * `lcg.PopupMenu'.
     *
     * The widget is initially created as hidden and must be invoked (popped up)
     * by calling the method 'popup()'.  Morover, the element is initially empty.
     * The menu is created and initialized only when needed (when first invoked).
     * This reduces the browser resource usage (DOM elements and their event
     * handlers) as well as page initialization overhead, so many menus can be
     * present on one page.  If needed the method 'create()' may be called to
     * create and initialize the menu HTML elements explicitly.
     */

    initialize: function ($super, element_id, items, close_button_label) {
        $super(element_id);
        this.items = items;
        this._close_button_label = close_button_label;
    },

    update: function (items) {
        this.items = items;
        if (!this.element.empty()) {
            this.element.descendants().each(function (element) {
                Event.stopObserving(element);
            });
            this.element.update();
        }
    },

    create: function () {
        /* Create and initialize menu HTML elements.
         *
         * You normally don't need to call this method explicitly.  It is called
         * automatically when needed internally.  You may need to call it
         * explicitly for example to be able to manipupate menu items from
         * JavaScript before menu invocation.  See class documentation for
         * more details about delayed menu creation.  The method does nothing
         * if the the menu was already created before.
         */
        if (!this.element.empty()) {
            return;
        }
        var ul = new Element('ul', {'role': 'menu'});
        ['aria-label', 'aria-activedescendant'].each(function (attr) {
            // The ul must be to root element of the menu, because otherwise
            // the close button would be considered as another menu item by
            // screen readers and item count would be announced incorrectly.
            ul.setAttribute(attr, this.element.getAttribute(attr));
            this.element.removeAttribute(attr);
        }.bind(this));
        var label_class = 'label';
        if (this.items.some(function (item) { return item.icon; })) {
            label_class += ' indented';
        }
        this.items.each(function (item) {
            var a = new Element('a', {'href': item.uri || '#'})
                .update(new Element('span', {'class': label_class}).update(item.label));
            if (item.tooltip) {
                a.setAttribute('title', item.tooltip);
            }
            a._lcg_popup_menu_item_spec = item;
            var li = new Element('li').update(a);
            if (item.enabled === undefined || item.enabled) {
                li.addClassName('active');
            }
            if (item.icon) {
                a.insert({top: new Element('span', {'class': 'icon ' + item.icon})});
            }
            if (item.cls) {
                li.addClassName(item.cls);
            }
            ul.insert(li);
        });
        this.element.update(ul);
        if (this._close_button_label) {
            this.element.insert(
                new Element('a', {
                    'href': '#',
                    'title': this._close_button_label,
                    'class': 'close-menu',
                    'role': 'button'
                })
                    .update(this._close_button_label)
                    .observe('click', function (event) {
                        this.dismiss();
                        event.stop();
                    }.bind(this))
            );
        }
        this._init_menu(ul);
    },

    _init_item: function ($super, item, prev, parent) {
        $super(item, prev, parent);
        item.setAttribute('role', 'menuitem');
    },

    _on_key_down: function ($super, event) {
        this.element.addClassName('keyboard-navigated');
        $super(event);
    },

    _on_item_click: function (event, item) {
        if (item.up('li').hasClassName('active')) {
            this.dismiss();
            this._run_callback(event, item);
            // If the item has a uri, the link has an href and we want to
            // let the event bubble up and get to standard browser processing
            // as a link click.  This way the browser may apply its configuration
            // and for example open a link in a new tab when Ctrl is pressed
            // on Linux/Windows or Cmd on Mac.
            if (!event.stopped && !item._lcg_popup_menu_item_spec.uri) {
                event.stop();
            }
        } else {
            event.stop();
        }
    },

    _cmd_activate: function (event, item) {
        if (item.up('li').hasClassName('active')) {
            this.dismiss();
            this._run_callback(event, item);
            if (!event.stopped) {
                var uri = item._lcg_popup_menu_item_spec.uri;
                if (uri) {
                    self.location = uri;
                }
            }
        }
    },

    _run_callback: function (event, item) {
        var spec = item._lcg_popup_menu_item_spec;
        var callback = spec.callback;
        if (callback) {
            if (typeof callback === 'string') {
                var namespaces = callback.split(".");
                var func = namespaces.pop();
                var context = window;
                var i;
                for (i = 0; i < namespaces.length; i++) {
                    context = context[namespaces[i]];
                }
                callback = context[func];
            }
            var args = [event, this._popup_element];
            if (spec.callback_args) {
                args = args.concat(spec.callback_args);
            }
            return callback.apply(this, args);
        }
    },

    popup: function ($super, event, element, selected_item_index) {
        /* Arguments:
         *   event -- JavaScript event triggering the popup -- either a mouse
         *     action catched by 'contextmenu' handler or mouse/keyboard action
         *     catched by 'click' handler.
         *   element -- HTML element that invoked the menu from the UI.  The
         *     menu will appear above this element.  If undefined, the element
         *     is obtained from the given event.
         *   selected_item_index (optional) -- index of the menu item to be
         *     initially selected
         */
        if (event) {
            event.stop();
        }
        if (element === undefined) {
            element = event.element();
        }
        var menu = this.element;
        if (menu.empty()) {
            this.create();
        }
        var offset = element.cumulativeOffset();
        var scroll_offset = document.viewport.getScrollOffsets();
        var viewport = document.viewport.getDimensions();
        var x, y;
        var direction;
        if (offset.top + element.getHeight() + menu.getHeight() > scroll_offset.top + viewport.height
            && offset.top > menu.getHeight()) {
            direction = 'up';
        } else {
            direction = 'down';
        }
        if (event && (event.isLeftClick() || event.isRightClick())) {
            // Math.min limits the pointer position to the boundary of the
            // element invoking the menu, because VoiceOver emits click events
            // with a wrong position and the menu would be placed radiculously.
            x = Math.min(event.pointerX() - offset.left, element.getWidth());
            y = Math.min(event.pointerY() - offset.top, element.getHeight());
            menu.removeClassName('keyboard-navigated');
        } else {
            x = 0;
            y = direction === 'up' ? 0 : element.getHeight();
            menu.addClassName('keyboard-navigated');
        }
        var correction = offset.relativeTo(element.getOffsetParent().cumulativeOffset());
        x += correction.left;
        y += correction.top;
        if (offset.left + x + menu.getWidth() > viewport.width + scroll_offset.left) {
            x -= menu.getWidth();
        }
        this._ignore_next_click = event && !event.isLeftClick();
        $super(element, x, y, direction, selected_item_index);
    }

});


lcg.PopupMenuCtrl = Class.create(lcg.Widget, {
    /* Control for invocation of a popup menu.
     *
     * Constructor arguments:
     *
     *   element_id -- HTML id of the widget root element (described in
     *     the parent class)
     *   selector -- optional CSS selector string to find the HTML element
     *     on which the 'contextmenu' event (right click) should be handled
     *     by popping the menu up.  The selector is searched up in the DOM
     *     treee so the element must be the parent of the PopupMenuCtrl
     *     widget.  If undefined, no context menu event is handled.
     *
     * This is the Javascript counterpart of the Python class
     * `lcg.PopupMenuCtrl'.
     *
     */

    initialize: function ($super, element_id, selector) {
        $super(element_id);
        var menu = lcg.widget_instance(this.element.down('.popup-menu-widget'));
        var ctrl = this.element.down('.invoke-menu');
        ctrl.observe('click', function (e) { menu.popup(e, ctrl); });
        ctrl.observe('keydown', this._on_key_down.bind(this));
        ctrl.down('.popup-arrow').observe('click', function (e) { menu.popup(e, ctrl); });
        ctrl.setAttribute('role', 'button');
        ctrl.setAttribute('aria-haspopup', 'true');
        ctrl.setAttribute('aria-expanded', 'false');
        ctrl.setAttribute('aria-controls', menu.element.getAttribute('id'));
        if (selector) {
            this.element.up(selector).observe(
                'contextmenu',
                function (e) { menu.popup(e, ctrl); }
            );
        }
        this._menu = menu;
    },

    _define_keymap: function () {
        return {
            'Enter': this._cmd_activate,
            'Space': this._cmd_activate
        };
    },

    _cmd_activate: function (event, element) {
        this._menu.popup(undefined, element);
    }

});


lcg.DropdownSelection = Class.create(lcg.PopupMenuBase, {
    /* Dropdown selection menu widget
     *
     * Constructor arguments:
     *
     *   element_id -- HTML id of the widget root element (described in
     *     the parent class)
     *   button_id -- HTML id of the element inoking the selection
     *   activation_callback -- callback called on item item activation
     *     with one argument (the activated item)
     *   get_selected_item_index -- function returning the initially selected
     *     item.  Called with no arguments every time before the dropdown
     *     is expanded.
     */

    initialize: function ($super, element_id, button_id, activation_callback,
        get_selected_item_index)
    {
        $super(element_id);
        if (get_selected_item_index === undefined) {
            get_selected_item_index = function () { return 0; };
        }
        this._activation_callback = activation_callback;
        this._get_selected_item_index = get_selected_item_index;
        this.element.setAttribute('role', 'listbox');
        var button = $(button_id);
        this._button = button;
        button.setAttribute('tabindex', '0');
        button.setAttribute('role', 'button');
        button.setAttribute('aria-haspopup', 'true');
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('aria-controls', this.element.getAttribute('id'));
        button.on('click', this._on_button_click.bind(this));
        button.on('keydown', this._on_button_key_down.bind(this));
    },

    _on_button_key_down: function (event) {
        var key = this._event_key(event);
        if (key === 'Enter' || key === 'Space' || key === 'Alt-Down') {
            this.dropdown();
            event.stop();
        }
    },

    _on_button_click: function (event) {
        event.stop();
        if (this._button.getAttribute('aria-expanded') === 'true') {
            this.dismiss();
        } else {
            this.dropdown();
        }
    },

    _cmd_activate: function (event, item) {
        this.dismiss();
        this._activation_callback(item);
    },

    _define_keymap: function () {
        return {
            'Up':     this._cmd_prev,
            'Down':   this._cmd_next,
            'Enter':  this._cmd_activate,
            'Space':  this._cmd_activate,
            'Escape': this._cmd_quit
        };
    },

    _init_items: function ($super, ul, parent) {
        var items = $super(ul, parent);
        ul.setAttribute('role', 'presentation');
        return items;
    },

    _init_item: function ($super, item, prev, parent) {
        $super(item, prev, parent);
        item.setAttribute('role', 'option');
        item.on('mouseover', function (event) {
            this._select_item(event.element());
        }.bind(this));
    },

    _select_item: function ($super, item) {
        var previously_selected_item = this._selected_item();
        $super(item);
        if (previously_selected_item && previously_selected_item !== item) {
            previously_selected_item.up('li').removeClassName('selected');
        }
        item.up('li').addClassName('selected');
        this._set_focus(item);
    },

    dropdown: function () {
        var y, direction;
        var menu = this.element;
        var viewport = document.viewport.getDimensions();
        var scroll_offset = document.viewport.getScrollOffsets();
        var height = menu.getHeight();
        var offset = this._button.cumulativeOffset().top;
        if (offset + this._button.getHeight() + height > viewport.height + scroll_offset.top && offset > height) {
            y = 0;
            direction = 'up';
        } else {
            y = this._button.getHeight();
            direction = 'down';
        }
        var padding = menu.getWidth() - menu.getLayout().get('width');
        menu.setStyle({width: this._button.getWidth() - padding + 'px'});
        this.popup(this._button, 0, y, direction, this._get_selected_item_index());
    }

});


lcg.Tooltip = Class.create({
    // Tooltip widget with asynchronlusly loaded content.
    // The content returned by the URL passed to constructor can be either an image or html
    // TODO: The class should be probably derived from lcg.Widget.

    initialize: function (uri) {
        // uri -- The URI from which the tooltip content should be loaded
        this._tooltip = null;
        this._show_when_ready = null;
        new Ajax.Request(uri, {
            method: 'GET',
            onSuccess: function (transport) {
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
                        element.insert(new Element('img', {
                            'src': uri,
                            'border': 0,
                            'style': 'vertical-align: middle;'
                        }));
                    } else {
                        return;
                    }
                    element.hide(); // Necessary to make visible() work before first shown.
                    $(document.body).insert(element);
                    this._tooltip = element;
                    if (this._show_when_ready) {
                        this.show(this._show_when_ready[0], this._show_when_ready[1]);
                    }
                } catch (e) {
                    // Errors in asynchronous handlers are otherwise silently ignored.
                    // Calling console.log will raise error in some browsers but there
                    // is a problem anyway and it helps debugging...
                    console.log(e); // eslint-disable-line no-console
                }
            }.bind(this)
        });
    },

    show: function (x, y) {
        if (this._tooltip) {
            var left = x + 3; // Show a little on right to avoid onmouseout and infinite loop.
            var top = y  - this._tooltip.getHeight();
            this._tooltip.setStyle({left: left+'px', top: top+'px', display: 'block'});
            this._show_when_ready = null;
        } else {
            this._show_when_ready = [x, y];
        }
    },

    hide: function () {
        if (this._tooltip) {
            this._tooltip.hide();
        }
        this._show_when_ready = null;
    }

});


lcg.CollapsibleWidget = Class.create(lcg.Widget, {
    /* Abstract base class for CollapsibleSection and CollapsiblePane.
     *
     * The content can be collapsed or expanded.  When collapsed, only
     * the title is displayed.  The title may be clicked to toggle the
     * content expansion state.
     *
     */

    initialize: function ($super, element_id, collapsed) {
        $super(element_id);
        var heading = this._heading = this._collapsible_heading();
        var content = this._content = this._collapsible_content();
        heading.insert({bottom: new Element('span', {'class': 'icon'})});
        if (collapsed) {
            this.element.addClassName('collapsed');
            content.hide();
        } else {
            this.element.addClassName('expanded');
        }
        heading.on('click', function (event) {
            this.toggle();
            event.stop();
        }.bind(this));
        if (!content.getAttribute('id')) {
            content.setAttribute('id', this.element.getAttribute('id') + '-collapsible-content');
        }
        heading.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        heading.setAttribute('aria-controls', content.getAttribute('id'));
    },

    _collapsible_heading: function() {
    },

    _collapsible_content: function() {
    },

    expanded: function () {
        return this.element.hasClassName('expanded');
    },

    expand: function () {
        this.element.removeClassName('collapsed');
        this.element.addClassName('expanded');
        this._heading.setAttribute('aria-expanded', 'true');
        if (Effect !== undefined) {
            this._content.slideDown({duration: 0.2});
        } else {
            this._content.show();
        }
    },

    collapse: function () {
        this.element.removeClassName('expanded');
        this.element.addClassName('collapsed');
        this._heading.setAttribute('aria-expanded', 'false');
        if (Effect !== undefined) {
            this._content.slideUp({duration: 0.2});
        } else {
            this._content.hide();
        }
    },

    toggle: function () {
        if (this.element.hasClassName('collapsed')) {
            this.expand();
        } else {
            this.collapse();
        }
    }

});

lcg.CollapsibleSection = Class.create(lcg.CollapsibleWidget, {
    /* Collapsible section widget.
     *
     * This is the Javascript counterpart of the Python class `lcg.CollapsibleSection'.
     */

    _collapsible_heading: function() {
        var heading = this.element.down('h1,h2,h3,h4,h5,h6,h7,h8');
        heading.addClassName('collapsible-section-heading');
        var backref = heading.down('a.backref');
        if (backref) {
            backref.setAttribute('href', '');
        }
        return heading;
    },

    _collapsible_content: function() {
        return this.element.down('div.section-content');
    }

});


lcg.CollapsiblePane = Class.create(lcg.CollapsibleWidget, {
    /* Collapsible pane widget.
     *
     * This is the Javascript counterpart of the Python class `lcg.CollapsiblePane'.
     */

    _collapsible_heading: function() {
        return this.element.down('.pane-title').down('a');
    },

    _collapsible_content: function() {
        return this.element.down('.pane-content');
    }

});


lcg.AudioPlayer = Class.create(lcg.Widget, {

    initialize: function ($super, element_id, swf_uri) {
        $super(element_id);
        this._volume = 0.8;
        this._player = jQuery('#' + element_id + ' .jp-player');
        this._player.jPlayer({
            volumechange: this._on_player_volume_change.bind(this),
            play: this._on_player_play.bind(this),
            pause: this._on_player_pause.bind(this),
            timeupdate: this._on_player_time_update.bind(this),
            swfPath: swf_uri || undefined,
            supplied: "mp3",
            wmode: "window",
            useStateClassSkin: true,
            autoBlur: false,
            smoothPlayBar: true,
            keyEnabled: true,
            remainingDuration: true,
            captureDuration: false,
            toggleDuration: true,
            volume: this._volume
        });
        this.element.down('.jp-volume-bar-value').innerHTML = Math.round(100 * this._volume) + '%';
        var play_button = this.element.down('button.play-pause');
        this._play_label = play_button.getAttribute('title');
        this._pause_label = play_button.getAttribute('data-pause-label');
        this._remaining_label = this.element.down('.jp-duration').getAttribute('title');
        this._duration_label = this.element.down('.jp-duration').getAttribute('data-duration-label');
        this._bind('play-pause', this._play_pause);
        this._bind('fast-forward', this._skip, true);
        this._bind('rewind', this._skip, false);
        this._bind('volume-up', this._change_volume, true);
        this._bind('volume-down', this._change_volume, false);
        this.element.down('.jp-duration').on('click', this._on_toggle_duration.bind(this));
        play_button.on('keydown', this._on_key_down.bind(this));
    },

    _bind: function (name, handler, arg) {
        this.element.down('button.' + name).on('click', function (event) {
            handler.bind(this)(arg);
            event.element().focus();
            event.stop();
        }.bind(this));
    },

    _define_keymap: function () {
        return {
            'Space': function (event, button) { this._play_pause(); },
            'Left': function (event, button) { this._skip(false); },
            'Right': function (event, button) { this._skip(true); },
            'Up': function (event, button) { this._change_volume(true); },
            'Down': function (event, button) { this._change_volume(false); },
            'Ctrl-Shift-Left': function (event, button) { this._skip(false); },
            'Ctrl-Shift-Right': function (event, button) { this._skip(true); },
            'Ctrl-Shift-Up': function (event, button) { this._change_volume(true); },
            'Ctrl-Shift-Down': function (event, button) { this._change_volume(false); }
        };
    },

    _play_pause: function () {
        var status = this._player.data('jPlayer').status;
        var action = (status.paused ? 'play' : 'pause');
        this._player.jPlayer(action);
    },

    _seek: function (time, play) {
        var command = (play ? 'play' : 'pause');
        this._player.jPlayer(command, time);
    },

    _skip: function (forward) {
        var player = this._player;
        var status = player.data('jPlayer').status;
        var position = status.currentTime;
        var duration = status.duration;
        var playing = !status.paused;
        if (position !== null && duration !== null) {
            var skip = Math.max(Math.min(duration / 20, 30), 3); // Seconds
            position += skip * (forward ? 1 : -1);
            if (position > duration) {
                return;
            }
            if (position < 0) {
                position = 0;
            }
            this._seek(position, playing);
        }
    },

    _change_volume: function (up) {
        var player = this._player;
        if (up && this._volume < 1) {
            this._volume = Math.min(this._volume + 0.05, 1);
            player.jPlayer('volume', this._volume);
        }
        if (!up && this._volume > 0) {
            this._volume = Math.max(this._volume - 0.05, 0);
            player.jPlayer('volume', this._volume);
        }
    },

    _on_player_volume_change: function (event) {
        this._volume = event.jPlayer.options.volume;
        this.element.down('.jp-volume-bar-value').innerHTML = Math.round(100 * this._volume) + '%';
    },

    _set_play_button_label: function (label) {
        var button = this.element.down('button.play-pause');
        button.setAttribute('title', label);
        button.down('span').innerHTML = label;
    },

    _on_player_play: function (event) {
        this._set_play_button_label(this._pause_label);
    },

    _on_player_pause: function (event) {
        this._set_play_button_label(this._play_label);
    },

    _on_toggle_duration: function (event) {
        var label;
        if (this._player.data('jPlayer').options.remainingDuration) {
            label = this._remaining_label;
        } else {
            label = this._duration_label;
        }
        this.element.down('.jp-duration').setAttribute('title', label);
        this.element.down('.duration-label').innerHTML = label;
    },

    _on_player_time_update: function (event) {
        var status = event.jPlayer.status;
    },

    _absolute_uri: function (uri) {
        var origin = window.location.origin;
        if (!origin) {
            // Fix for some older browsers (such as MSIE <= 8)...
            origin = window.location.protocol + "//" + window.location.hostname;
            if (window.location.port && window.location.port !== 80) {
                origin += ':' + window.location.port;
            }
        }
        if (uri.indexOf(origin) !== 0) {
            uri = origin + uri;
        }
        return uri;
    },

    _load_if_needed: function (uri) {
        var status = this._player.data('jPlayer').status;
        if (status.media.mp3 !== this._absolute_uri(uri)) {
            this.load(uri);
        }
    },

    _media_type: function (uri) {
        var ext = uri.split('.').pop().toLowerCase();
        if (ext === 'mp3') {
            return {type: 'mp3', media: 'audio/mpeg;'};
        } else if (ext === 'ogg' || ext === 'oga') {
            return {type: 'oga', media: 'audio/ogg; codecs="vorbis"'};
        } else if (ext === 'wav' || ext === 'wave') {
            return {type: 'wav', media: 'audio/wav; codecs="1"'};
        } else if (ext === 'aac' || ext === 'm4a') {
            return {type: 'aac', media: 'audio/mp4; codecs="mp4a.40.2"'};
        } else {
            return undefined;
        }
    },

    _can_play_audio: function (uri) {
        var type = this._media_type(uri);
        if (!type) {
            return false;
        }
        var audio = this.element.down('audio');
        if (audio) {
            // If the browser supports the <audio> tag, jPlayer will use it and
            // we can get the media support information from its API.
            return !!(audio.canPlayType && audio.canPlayType(type.media).replace(/no/, ''));
        } else if (!this.element.down('.jp-no-solution').visible()) {
            // The div 'jp-no-solution' made visible by jPlayer if Flash is unavailable
            // so the above condition means that the Flash fallback will be used and
            // thus we return true only for formats known to be supported by Flash.
            return (type.type == 'mp3' || type.type == 'aac');
        } else {
            return false;
        }
    },

    load: function (uri) {
        this._player.jPlayer('setMedia', {
            mp3: uri
        });
    },

    play: function () {
        this._player.jPlayer('play');
    },

    bind_audio_control: function (element_id, uri) {
        if (this._can_play_audio(uri)) {
            // Only bind the player to the control if it is capable of playing
            // given media type.  Otherwise leave the original HTML element
            // untouched.  Suppose that it already provides some fallback
            // functionality (such as download).
            var element = $(element_id);
            element.on('click', function (event) {
                this._load_if_needed(uri);
                this._play_pause();
                event.stop();
            }.bind(this));
            element.on('keydown', function (event) {
                this._load_if_needed(uri);
                this._on_key_down(event);
            }.bind(this));
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
        document.cookie.split(';').invoke('strip').each(function (s) {
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

lcg.widget_instance = function (element) {
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
