/* -*- coding: utf-8 -*-
 *
 * Copyright (C) 2012-2018 OUI Technology Ltd.
 * Copyright (C) 2019-2022 Tomáš Cerha <t.cerha@gmail.com>
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

"use strict";


window.lcg = {
    dedent: str => ('' + str).replace(/\n\s+/g, ''),
}


lcg.KeyHandler = class {
    _keycodes = {
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
    }

    constructor() {
        this._keymap = this._define_keymap()
    }

    _define_keymap() {
        return {}
    }

    _event_key(event) {
        let code = event.which
        let key = undefined
        if (code >= 65 && code <= 90) {
            key = String.fromCharCode(code).toLowerCase()
        } else {
            key = this._keycodes[code]
        }
        if (key) {
            if (event.shiftKey) {
                key = 'Shift-' + key
            }
            if (event.altKey) {
                key = 'Alt-' + key
            }
            if (event.ctrlKey) {
                key = 'Ctrl-' + key
            }
        }
        return key
    }

    _on_key_down(event) {
        let command = this._keymap[this._event_key(event)]
        if (command) {
            // Returning false doesn't work here for some reason...
            event.preventDefault()
            event.stopPropagation()
            command.bind(this)(event, $(event.target))
        }
    }

    _set_focus(element) {
        if (element) {
            setTimeout(() => element.focus(), 0)
        }
    }

}

lcg.Widget = class extends lcg.KeyHandler {
    /* Generic base class for all LCG JavaScript widgets.
     *
     * Constructor arguments:
     *
     *   element -- The root element of the widget as a string (HTML element id),
     *     DOM element or a jQuery object.
     *
     */
    constructor(element) {
        super()
        this.element = this._element(element)
        for (let e of this.element) {
            e._lcg_widget_instance = this
        }
    }

    _element(element) {
        if (element instanceof jQuery) {
            return element
        } else if (typeof element === 'string') {
            return $('#' + element.replace('.', '\\.'))
        } else {
            return $(element)
        }
    }

    _get_object_by_name(name) {
        let namespaces = name.split(".")
        let last_name = namespaces.pop()
        let context = window
        for (const x of namespaces) {
            context = context[x]
        }
        return context[last_name]
    }

    _ajax(settings, callback, failure) {
        function wrap(func) {
            // Errors in asynchronous callbacks are silently ignored.
            // This wrapper will at least log the error to the console.
            return function() {
                try {
                    return func.apply(this, arguments)
                } catch (e) {
                    console.log(e)
                }
                return undefined
            }
        }
        if (settings.form) {
            // Make AJAX call similar to submission of given form.
            let data = settings.form.serializeArray()
            for (let param in settings.data) {
                if (settings.data.hasOwnProperty(param)) {
                    let item = data.find(item => item.name === param)
                    if (item !== undefined) {
                        item.value = settings.data[param]
                    } else {
                        data.push({name: param, value: settings.data[param]})
                    }
                }
            }
            settings.url ||= settings.form.attr('action')
            settings.method ||= settings.form.attr('method')
            settings.data = data
        }
        document.body.style.cursor = "wait"
        let result = $.ajax(settings).always(() => document.body.style.cursor = "default")
        if (callback) {
            result = result.done(wrap(callback))
        }
        if (failure) {
            result = result.fail(wrap(failure))
        }
        return result
    }
}

lcg.Button = class extends lcg.Widget {
    /* LCG JavaScript Button widget.
     *
     * Constructor arguments:
     *
     *   element -- The root element of the widget as a string (HTML element id),
     *     DOM element or a jQuery object.
     *   callback -- The JavaScript function to be called on item invocation.
     *     May be passed also as a string (function of given name will be
     *     looked up in the current JavaScript name space).  The callback
     *     function will be called with the Button widget instance
     *     as the first argument.
     */
    constructor(element, callback) {
        super(element)
        if (typeof callback === 'string') {
            callback = this._get_object_by_name(callback)
        }
        if (callback) {
            this.element.find('button').on('click', event => {
                callback(this)
                return false
            })
        }
    }

}

lcg.Menu = class extends lcg.Widget {
    /* Generic base class for several other menu-like widgets.
     *
     * Constructor arguments:
     *
     *   element -- The root element of the widget as a string (HTML element id),
     *     DOM element or a jQuery object.
     *
     * The menu structure is traversed on instance creation and connections
     * between the hierarchical items are initialized, ARIA roles are assigned
     * to HTML elements and event handling is established.
     *
     * Accessibility is supported through automatically managed ARIA roles
     * and states and handling keyboard menu traversal.
     *
     */

    constructor(element) {
        super(element)
        this._init_menu(this.element.find('ul').first())
        this._MANAGE_TABINDEX = true
    }

    _init_menu(ul) {
        // Go through the menu and assign aria roles and key bindings.
        this.items = this._init_items(ul, null)
        // Set the active item.
        let selected = this._initially_selected_item()
        if (selected) {
            this._select_item(selected)
        }
    }

    _init_items(ul, parent) {
        let items = []
        let base_id
        if (parent) {
            base_id = parent.attr('id')
        } else {
            base_id = this.element.attr('id') + '-item'
        }
        for (let li of ul.children('li')) {
            $(li).attr('role', 'presentation')
            let item = $(li).children('a').first()
            let prev = (items.length === 0 ? null : items[items.length - 1])
            item.attr('id', base_id + '.' + (items.length + 1))
            this._init_item(item, prev, parent)
            items.push(item)
        }
        return items
    }

    _init_item(item, prev, parent) {
        item.attr('aria-selected', 'false')
        item.on('keydown', this._on_key_down.bind(this))
        item.on('click', event => this._on_item_click(event, item))
        if (this._MANAGE_TABINDEX) {
            item.attr('tabindex', '-1')
        }
        item[0]._lcg_menu_item_data = {
            prev: prev,
            next: null,
            parent: parent,
            submenu: null,
            menu: this,
        }
        if (prev) {
            this._data(prev).next = item
        }
    }

    _data(item) {
        return item[0]._lcg_menu_item_data
    }

    _initially_selected_item() {
        let item
        if (this.items.length !== 0) {
            let current = this.element.find('a.current').first()
            if (current) {
                item = current
            } else {
                item = this.items[0]
            }
        } else {
            item = null
        }
        return item
    }

    _active_descendant_parent() {
        // The attribute aria-activedescendant may not always be on the root element.
        let element = this.element.find('*[aria-activedescendant]')
        if (!element.length) {
            element = this.element
        }
        return element
    }

    _selected_item() {
        let p = this._active_descendant_parent()
        let id = p.attr('aria-activedescendant')
        if (id) {
            let element = this._element(id)
            if (element.length) {
                return element
            }
        }
        return null
    }

    _select_item(item) {
        let previously_selected_item = this._selected_item()
        this._active_descendant_parent().attr('aria-activedescendant', item.attr('id'))
        if (item.attr('aria-selected') !== undefined) {
            // Note: Derived classes (Wiking's MainMenu) may unset
            // 'aria-selected' because they are using ARIA roles which
            // don't support the aria-selected attribute.  So we
            // manipulate this attribute only when already set.
            item.attr('aria-selected', 'true')
            if (previously_selected_item) {
                previously_selected_item.attr('aria-selected', 'false')
            }
        }
        if (this._MANAGE_TABINDEX) {
            item.attr('tabindex', '0')
            if (previously_selected_item) {
                previously_selected_item.attr('tabindex', '-1')
            }
        }
    }

    _expand_item(item) {
        return false
    }

    _on_item_click(event, item) {
        this._cmd_activate(event, item)
        return false
    }

    _cmd_prev(event, item) {
        this._set_focus(this._data(item).prev)
    }

    _cmd_next(event, item) {
        this._set_focus(this._data(item).next)
    }

    _cmd_activate(event, item) {
        return
    }

    focus() {
        let item = this._selected_item()
        if (item) {
            this._expand_item(item)
            this._set_focus(item)
        }
    }

}

lcg.Notebook = class extends lcg.Menu {
    /* Notebook widget with tabs.
     *
     * This is the Javascript counterpart of the Python class `lcg.Notebook'.
     * The notebook has tabs at the top and there is a content page belonging to
     * each tab.  Switching the tabs switches the visible content below the tab
     * switcher.  There may be multiple instances on one page.
     *
     */
    static _activation_callbacks = {}
    static _COOKIE = 'lcg_last_notebook_tab'

    constructor(element) {
        super(element)
    }

    _define_keymap() {
        return {
            'Left': this._cmd_prev,
            'Right': this._cmd_next,
            'Enter': this._cmd_activate,
            'Space': this._cmd_activate
        }
    }

    _initially_selected_item() {
        // The selected item set in the python code (marked as 'current' in HTML)
        // has the highest precedence.
        let current = this.element.find('.notebook-switcher li a.current').first()
        //this._current_location_selected_item(),
        //this._last_saved_selected_item(),
        //this.items[0])
        if (current.length !== 0) {
            return current
        }
        return (this._current_location_selected_item() || // the tab may be referenced by anchor.
                this._last_saved_selected_item() || // the most recently selected tab.
                this.items[0]) // finally the first item is used with the lowest precedence.
    }

    _init_items(ul, parent) {
        ul.attr('role', 'tablist')
        return super._init_items(ul, parent)
    }

    _init_item(item, prev, parent) {
        super._init_item(item, prev, parent)
        item.attr('role', 'tab')
        let href = item.attr('href') // The href always contains the '#', in MSIE 8 it is even a full asolute URI.
        let page = $(href.substr(href.indexOf('#')))
        item[0]._lcg_notebook_page = page
        page[0]._lcg_notebook_item = item
        page.find('h1,h2,h3,h4,h5,h6').hide()
        page.hide()
        page.addClass('notebook-page')
        page.attr('role', 'tabpanel')
        if (!page.attr('id')) {
            page.attr('id', item.attr('id') + '-tabpanel')
        }
        item.attr('aria-controls', page.attr('id'))
    }

    _current_location_selected_item() {
        // Get the selected item if the anchor is part of the current location.
        let match = self.location.href.match('#.+')
        if (match) {
            let parts = self.location.href.split('#', 2)
            let page = this.element.find('#' + parts[1])
            if (page.length && page[0]._lcg_notebook_item) {
                return page[0]._lcg_notebook_item
            }
        }
    }

    _last_saved_selected_item() {
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
        let cls = this.element.attr('class')
        if (cls) {
            let cookie = lcg.cookies.get(lcg.Notebook._COOKIE)
            if (cookie) {
                let parts = cookie.split(':', 2)
                if (parts[0] === cls) {
                    let page = this.element.find('#' + parts[1])
                    if (page.length && page[0]._lcg_notebook_item) {
                        return page[0]._lcg_notebook_item
                    }
                }
            }
        }
        return null
    }

    _select_item(item) {
        let i, callback, repeat
        let previously_selected_item = this._selected_item()
        super._select_item(item)
        if (previously_selected_item !== item) {
            if (previously_selected_item) {
                previously_selected_item.removeClass('current')
                previously_selected_item[0]._lcg_notebook_page.hide()
            }
            item.addClass('current')
            let page = item[0]._lcg_notebook_page
            let cls = this.element.attr('class')
            if (cls) {
                let cookie = cls + ':' + page.attr('id')
                lcg.cookies.set(lcg.Notebook._COOKIE, cookie)
            }
            page.show()
            let callbacks = lcg.Notebook._activation_callbacks[page.attr('id')]
            if (callbacks) {
                for (let i = callbacks.length - 1; i >= 0; i--) {
                    // Process in reverse to be able to simply remove callbacks
                    // which are not to be repeated.
                    callback = callbacks[i][0]
                    repeat = callbacks[i][1]
                    callback()
                    if (!repeat) {
                        callbacks.splice(i, 1) // Remove the callback.
                    }
                }
            }
        }
    }

    _cmd_activate(event, item) {
        this._select_item(item)
        this._set_focus(item[0]._lcg_notebook_page)
    }

}


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
        repeat = false
    }
    let callbacks = lcg.Notebook._activation_callbacks[page.attr('id')]
    if (!callbacks) {
        callbacks = []
        lcg.Notebook._activation_callbacks[page.attr('id')] = callbacks
    }
    callbacks.push([callback, repeat])
}


lcg.FoldableTree = class extends lcg.Menu {
    /* Foldable tree widget
     *
     * This is the Javascript counterpart of the Python class
     * `lcg.FoldableTree'.
     */

    constructor(element, toggle_button_tooltip) {
        super(element)
        this._expanded = false
        $(this.element).attr('role', 'tree')
        if (this._foldable && toggle_button_tooltip) {
            $(this.element).find('ul').first().append(
                $(`<button class="toggle-menu-expansion" title="${toggle_button_tooltip}">`)
                    .on('click', this._on_toggle_full_expansion.bind(this)))
        }
    }

    _define_keymap() {
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
        }
    }

    _init_menu(ul) {
        this._foldable = false
        super._init_menu(ul)
    }

    _init_items(ul, parent) {
        ul.attr('role', 'group')
        return super._init_items(ul, parent)
    }

    _init_item(item, prev, parent) {
        super._init_item(item, prev, parent)
        item.attr('role', 'treeitem')
        let icon = item.find('.icon')
        if (icon) {
            icon.attr('role', 'presentation')
        }
        let label = item.find('.label')
        if (label) {
            // Needed for VoiceOver to read the labels after adding the icon span
            // inside the a tag (because of MSIE as described in widgets.py...).
            let label_id = item.attr('id') + '-label'
            label.attr('id', label_id)
            item.attr('aria-labelledby', label_id)
        }
        let li = item.closest('li')
        // Append hierarchical submenu if found.
        let submenu = li.find('ul').first()
        if (submenu) {
            if (li.hasClass('foldable')) {
                if (!submenu.attr('id')) {
                    submenu.attr('id', item.attr('id') + '-submenu')
                }
                item.attr('aria-controls', submenu.attr('id'))
                let expander = li.find('.expander').first()
                expander.attr('aria-controls', submenu.attr('id'))
                expander.on('click', event => this._on_expander_click(event, item))
                this._update_item(item, li.hasClass('expanded'))
                this._foldable = true
            }
            this._data(item).submenu = this._init_items(submenu, item)
        }
    }

    _update_item(item, expanded) {
        let li = item.closest('li')
        let submenu = li.find('ul').first()
        let expander = li.find('.expander').first()
        let label = expander.attr(expanded ? 'data-collapse-label' : 'data-expand-label')
        if (expanded) {
            li.removeClass('collapsed')
            li.addClass('expanded')
        } else {
            li.removeClass('expanded')
            li.addClass('collapsed')
        }
        submenu.attr('aria-hidden', expanded ? 'false' : 'true')
        item.attr('aria-expanded', expanded ? 'true' : 'false')

        expander.attr('aria-expanded', expanded ? 'true' : 'false')
        expander.attr('title', label)
        expander.find('.label').html(label)
    }

    _expand_item(item) {
        let expanded = false
        if (item.closest('li').hasClass('collapsed')) {
            this._update_item(item, true)
            expanded = true
        }
        if (this._data(item).parent) {
            this._expand_item(this._data(item).parent)
        }
        return expanded
    }

    _collapse_item(item) {
        if (item.closest('li').hasClass('expanded')) {
            this._update_item(item, false)
            return true
        }
        return false
    }

    _toggle_expansion(item) {
        if (item.closest('li').hasClass('collapsed')) {
            this._expand_item(item)
        } else {
            this._collapse_item(item)
        }
    }

    _expand_recursively(item, expand) {
        if (expand) {
            this._expand_item(item)
        } else {
            this._collapse_item(item)
        }
        const data = this._data(item)
        if (data.submenu.length) {
            this._expand_recursively(data.submenu[0], expand)
        }
        if (data.next) {
            this._expand_recursively(data.next, expand)
        }
    }

    _next_item(item) {
        // Recursively find the next item in sequence by traversing the hierarchy.
        let next
        const data = this._data(item)
        if (data.next) {
            next = data.next
        } else if (data.parent && this._data(data.parent).menu === this) {
            next = this._next_item(data.parent)
        }
        return next
    }

    _cmd_up(event, item) {
        let target = null
        const data = this._data(item)
        if (data.prev) {
            target = data.prev
            if (this._data(target).submenu && data.prev.closest('li').hasClass('expanded')) {
                let submenu = this._data(target).submenu
                target = submenu[submenu.length-1]
            }
        } else {
            target = data.parent
        }
        this._set_focus(target)
    }

    _cmd_down(event, item) {
        let target = null
        const data = this._data(item)
        if (data.submenu && item.closest('li').hasClass('expanded')) {
            target = this._data(item).submenu[0]
        } else {
            target = this._next_item(item)
        }
        this._set_focus(target)
    }

    _cmd_expand(event, item) {
        const data = this._data(item)
        if (!this._expand_item(item) && data.submenu) {
            this._set_focus(data.submenu[0])
        }
    }

    _cmd_collapse(event, item) {
        if (!this._collapse_item(item)) {
            this._set_focus(this._data(item).parent)
        }
    }

    _cmd_activate(event, item) {
        self.location = item.attr('href')
    }

    _cmd_quit(event, item) {
        this._set_focus($('#main-heading'))
    }

    _on_toggle_full_expansion(event) {
        this._expanded = !this._expanded
        this._expand_recursively(this.items[0], this._expanded)
        let b = $(this.element).find('button.toggle-menu-expansion')
        if (this._expanded) {
            b.addClass('expanded')
        } else {
            b.removeClass('expanded')
        }
    }

    _on_item_click(event, item) {
        if ($(event.target).closest('.label').length === 0) {
            // Clicked outside the label => clicked on the expansion triangle.
            this._toggle_expansion(item)
            return false
        }
        return super._on_item_click(event, item)
    }

    _on_expander_click(event, item) {
        this._toggle_expansion(item)
        return false
    }

}


lcg.PopupMenuBase = class extends lcg.Menu {

    constructor(element) {
        super(element)
        this._ignore_next_click = false
    }

    _define_keymap() {
        return {
            'Up': this._cmd_prev,
            'Down': this._cmd_next,
            'Enter': this._cmd_activate,
            'Space': this._cmd_activate,
            'Escape': this._cmd_quit
        }
    }

    _cmd_quit(event, item) {
        this.dismiss()
    }

    _on_click(event) {
        let outside = $(event.target).closest('div')[0] !== this.element[0]
        if (this._ignore_next_click && !outside) {
            // The first click is the one which pops the menu up.
            this._ignore_next_click = false
            return
        }
        this.dismiss()
        if (outside) {
            return false
        }
    }

    _on_touchend(event) {
        if (!this._touch_moved) {
            let element = $(event.target)
            // Detect touch outside the menu div:
            if (element.closest('div')[0] !== this.element[0]) {
                this.dismiss()
            } else {
                this._cmd_activate(event, element.closest('a'))
            }
            return false
        }
    }

    popup(element, x, y, direction, selected_item_index) {
        let active_menu = lcg.popup_menu
        if (active_menu) {
            active_menu.dismiss()
            if (active_menu === this) {
                return
            }
        }
        lcg.popup_menu = this
        this._popup_element = element
        let menu = this.element
        let selected_item
        if (selected_item_index !== undefined && selected_item_index !== null
            && selected_item_index !== -1) {
            selected_item = $(menu.find('ul').children()[selected_item_index]).find('a')
        } else {
            selected_item = menu.find('li.active a').first()
        }
        this._select_item(selected_item)
        menu.attr('style', 'display: none') // Force consistent initial state
        menu.css({left: x + 'px', top: y + 'px'})
        if (direction === 'up') {
            let total_height = menu.height()
            let css_height = menu.height()
            menu.css({height: 0, display: 'block', overflowY: 'hidden'})
            menu.animate({
                height: css_height + 'px',
                top: y - total_height + 'px',
            }, {
                duration: 200,
                done: () => {
                    menu.css({overflowY: 'auto'})
                    this._set_focus(selected_item)
                },
            })
        } else {
            menu.slideToggle(0.2, () => this._set_focus(selected_item))
        }
        this._on_touchstart_handler = (e) => { this._touch_moved = false }
        this._on_touchmove_handler = (e) => { this._touch_moved = true }
        this._on_touchend_handler = this._on_touchend.bind(this)
        this._on_click_handler = this._on_click.bind(this)

        $(document).on('touchstart', this._on_touchstart_handler)
        $(document).on('touchmove', this._on_touchmove_handler)
        $(document).on('touchend', this._on_touchend_handler)
        $(document).on('click', this._on_click_handler)
        if (element) {
            element.attr('aria-expanded', 'true')
        }
    }

    dismiss() {
        $(document).off('touchstart', this._on_touchstart_handler)
        $(document).off('touchmove', this._on_touchmove_handler)
        $(document).off('touchend', this._on_touchend_handler)
        $(document).off('click', this._on_click_handler)
        this.element.hide()
        lcg.popup_menu = null
        let element = this._popup_element
        if (element) {
            element.attr('aria-expanded', 'false')
            this._set_focus(element)
        }
    }

}

lcg.popup_menu = null


lcg.PopupMenu = class extends lcg.PopupMenuBase {
    /* Popup menu widget.
     *
     * Constructor arguments:
     *
     *   element -- The root element of the widget as a string (HTML element id),
     *     DOM element or a jQuery object.
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

    constructor(element, items, close_button_label) {
        super(element)
        this.items = items
        this._close_button_label = close_button_label
    }

    update(items) {
        this.items = items
        if (this.element.children().length) {
            this.element.children().off()
            this.element.empty()
        }
    }

    create() {
        /* Create and initialize menu HTML elements.
         *
         * You normally don't need to call this method explicitly.  It is called
         * automatically when needed internally.  You may need to call it
         * explicitly for example to be able to manipupate menu items from
         * JavaScript before menu invocation.  See class documentation for
         * more details about delayed menu creation.  The method does nothing
         * if the the menu was already created before.
         */
        if (this.element.children().length !== 0) {
            return
        }
        var ul = $('<ul role="menu">')
        this.element.html(ul)
        if (this.items.some(item => item.icon)) {
            this.element.addClass('with-icons')
        }

        for (let attr of ['aria-label', 'aria-activedescendant']) {
            // The ul must be to root element of the menu, because otherwise
            // the close button would be considered as another menu item by
            // screen readers and item count would be announced incorrectly.
            ul.attr(attr, this.element.attr(attr))
            this.element.removeAttr(attr)
        }
        let label_class = 'label'
        for (let spec of this.items) {
            let item = $(`<a href="${spec.uri || '#'}"><span class="label">${spec.label}</span></a>`)
            let li = $('<li>').append(item)
            if (spec.tooltip) {
                item.attr('title', spec.tooltip)
            }
            item[0]._lcg_popup_menu_item_spec = spec
            if (spec.enabled === undefined || spec.enabled) {
                li.addClass('active')
            }
            if (spec.icon) {
                item.prepend(`<span class="icon ${spec.icon}"></span>`)
            }
            if (spec.cls) {
                li.addClass(spec.cls)
            }
            ul.append(li)
        }
        let close = this._close_button_label;
        if (close) {
            this.element.append(
                $(`<a href="#" title="${close}" class="close-menu" role="button">${close}</a>`)
                    .on('click', e => { this.dismiss(); return false }))
        }
        this._init_menu(ul)
    }

    _init_item(item, prev, parent) {
        super._init_item(item, prev, parent)
        item.attr('role', 'menuitem')
    }

    _on_key_down(event) {
        this.element.addClass('keyboard-navigated')
        super._on_key_down(event)
    }

    _on_item_click(event, item) {
        if (item.closest('li').hasClass('active')) {
            this.dismiss()
            let result = this._run_callback(event, item)
            let uri = item[0]._lcg_popup_menu_item_spec.uri
            if (uri && result !== false) {
                // If the item has a uri, the link has an href and we want to
                // let the browser perform its default event processing.  This
                // way the browser may apply its configuration and for example
                // open a link in a new tab when Ctrl is pressed on Linux/Windows
                // or Cmd on Mac.
                // TODO: "return true" should work in jQuery, but does not!
                // "self.location = uri" doesn't respect the browser!
                self.location = uri;
            }
        }
        return false
    }

    _cmd_activate(event, item) {
        if (item.closest('li').hasClass('active')) {
            this.dismiss()
            this._run_callback(event, item)
            if (!event.isPropagationStopped()) {
                let uri = item[0]._lcg_popup_menu_item_spec.uri
                if (uri) {
                    self.location = uri
                }
            }
        }
    }

    _run_callback(event, item) {
        let spec = item[0]._lcg_popup_menu_item_spec
        let callback = spec.callback
        if (callback) {
            if (typeof callback === 'string') {
                callback = this._get_object_by_name(callback)
            }
            let args = [event, this._popup_element]
            if (spec.callback_args) {
                args = args.concat(spec.callback_args)
            }
            return callback.apply(this, args)
        }
    }

    popup(event, element, selected_item_index) {
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
            event.stopPropagation()
        }
        if (element === undefined) {
            element = $(event.target)
        }
        let menu = this.element
        if (menu.children().length === 0) {
            this.create()
        }
        let offset = element.offset()
        let bottom = $(window).scrollTop() + $(window).height()
        let menu_height = menu.height()
        let direction, x, y
        if (offset.top + element.height() + menu_height > bottom && offset.top > menu_height) {
            direction = 'up'
        } else {
            direction = 'down'
        }
        if (event && event.detail === 1) {
            // Math.min limits the pointer position to the boundary of the
            // element invoking the menu, because VoiceOver emits click events
            // with a wrong position and the menu would be placed radiculously.
            x = Math.min(event.pageX - offset.left, element.width())
            y = Math.min(event.pageY - offset.top, element.height())
            menu.removeClass('keyboard-navigated')
        } else {
            x = 0
            y = direction === 'up' ? 0 : element.height()
            menu.addClass('keyboard-navigated')
        }
        //let correction = offset.relativeTo(element.offsetParent.offset())
        //x += correction.left
        //y += correction.top
        if (offset.left + x + menu.width() > $(window).width() + window.pageXOffset) {
            x -= menu.width()
        }
        this._ignore_next_click = event && event.which !== 1
        super.popup(element, x, y, direction, selected_item_index)
    }

}


lcg.PopupMenuCtrl = class extends lcg.Widget {
    /* Control for invocation of a popup menu.
     *
     * Constructor arguments:
     *
     *   element -- The root element of the widget as a string (HTML element id),
     *     DOM element or a jQuery object.
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

    constructor(element, selector) {
        super(element)
        let menu = lcg.widget_instance(this.element.find('.popup-menu-widget'))
        let ctrl = this.element.find('.invoke-menu')
        ctrl.on('click', e => menu.popup(e, ctrl))
        ctrl.on('keydown', this._on_key_down.bind(this))
        ctrl.find('.popup-arrow').on('click', e => menu.popup(e, ctrl))
        ctrl.attr('role', 'button')
        ctrl.attr('aria-hapsopup', 'true')
        ctrl.attr('aria-expanded', 'false')
        ctrl.attr('aria-controls', menu.element.attr('id'))
        if (selector) {
            this.element.closest(selector).on('contextmenu', e => menu.popup(e, ctrl))
        }
        this._menu = menu
    }

    _define_keymap() {
        return {
            'Enter': this._cmd_activate,
            'Space': this._cmd_activate
        }
    }

    _cmd_activate(event, element) {
        this._menu.popup(undefined, element)
    }

}


lcg.DropdownSelection = class extends lcg.PopupMenuBase {
    /* Dropdown selection menu widget
     *
     * Constructor arguments:
     *
     *   element -- The root element of the widget as a string (HTML element id),
     *     DOM element or a jQuery object.
     *   button_id -- HTML id of the element inoking the selection
     *   activation_callback -- callback called on item item activation
     *     with one argument (the activated item)
     *   get_selected_item_index -- function returning the initially selected
     *     item.  Called with no arguments every time before the dropdown
     *     is expanded.
     */

    constructor(element, button_id, activation_callback, get_selected_item_index) {
        super(element)
        if (get_selected_item_index === undefined) {
            get_selected_item_index = function () { return 0 }
        }
        this._activation_callback = activation_callback
        this._get_selected_item_index = get_selected_item_index
        this.element.attr('role', 'listbox')
        let button = this._element(button_id)
        this._button = button
        button.attr('tabindex', '0')
        button.attr('role', 'button')
        button.attr('aria-haspopup', 'true')
        button.attr('aria-expanded', 'false')
        button.attr('aria-controls', this.element.attr('id'))
        button.on('click', this._on_button_click.bind(this))
        button.on('keydown', this._on_button_key_down.bind(this))
    }

    _on_button_key_down(event) {
        let key = this._event_key(event)
        if (key === 'Enter' || key === 'Space' || key === 'Alt-Down') {
            this.dropdown()
            return false
        }
    }

    _on_button_click(event) {
        if (this._button.attr('aria-expanded') === 'true') {
            this.dismiss()
        } else {
            this.dropdown()
        }
        return false
    }

    _cmd_activate(event, item) {
        this.dismiss()
        this._activation_callback(item)
    }

    _define_keymap() {
        return {
            'Up': this._cmd_prev,
            'Down': this._cmd_next,
            'Enter': this._cmd_activate,
            'Space': this._cmd_activate,
            'Escape': this._cmd_quit
        }
    }

    _init_items(ul, parent) {
        let items = super._init_items(ul, parent)
        ul.attr('role', 'presentation')
        return items
    }

    _init_item(item, prev, parent) {
        super._init_item(item, prev, parent)
        item.attr('role', 'option')
        item.on('mouseover', e => this._select_item($(e.target)))
    }

    _select_item(item) {
        let previously_selected_item = this._selected_item()
        super._select_item(item)
        if (previously_selected_item && previously_selected_item !== item) {
            previously_selected_item.closest('li').removeClass('selected')
        }
        item.closest('li').addClass('selected')
        this._set_focus(item)
    }

    dropdown() {
        let y, direction
        let menu = this.element
        let bottom = $(window).scrollTop() + $(window).height()
        let height = menu.height()
        let offset = this._button.offset()
        if (offset.top + this._button.height() + height > bottom && offset.top > height) {
            y = 0
            direction = 'up'
        } else {
            y = this._button.height()
            direction = 'down'
        }
        let padding = menu.outerWidth() - menu.innerWidth()
        menu.css({width: this._button.width() - padding + 'px'})
        this.popup(this._button, 0, y, direction, this._get_selected_item_index())
    }

}


lcg.Tooltip = class extends lcg.Widget {
    // Tooltip widget with asynchronlusly loaded content.
    // The content returned by the URL passed to constructor can be either an image or html
    // TODO: The class should be probably derived from lcg.Widget.

    constructor(url, x, y) {
        // url -- The URL from which the tooltip content should be loaded
        super($())
        this._abort = false
        this._ajax({
            url: url,
            method: 'GET',
        }, (response, status, xhr) => {
            if (this._abort) {
                return
            }
            let div = this.element = $(`<div class="tooltip-widget">`)
            let content_type = xhr.getResponseHeader('Content-Type')
            if (content_type === 'text/html') {
                div.html(response)
            } else if (content_type.substring(0, 6) === 'image/') {
                // The AJAX request was redundant in this case (the image will
                // be loaded again by the browser for the new img tag) but
                // there's no better way to tell automatically what the URL
                // points to and thanks to browser caching it should not
                // normally be a serious problem.
                div.append(`<img src="${url}" border="0" style="vertical-align: middle">`)
            } else {
                return
            }
            $(document.body).append(div)
            div.css({
                // Show a little on right to avoid onmouseout and infinite loop.
                left: (x + 20) + 'px',
                top: y + 'px',
                position: 'fixed',
                display: 'block',
            })

        })
    }

    remove() {
        this.element.remove()
        this._abort = true
    }

}


lcg.CollapsibleWidget = class extends lcg.Widget {
    /* Abstract base class for CollapsibleSection and CollapsiblePane.
     *
     * The content can be collapsed or expanded.  When collapsed, only
     * the title is displayed.  The title may be clicked to toggle the
     * content expansion state.
     *
     */

    constructor(element, collapsed) {
        super(element)
        let heading = this._heading = this._collapsible_heading()
        let content = this._content = this._collapsible_content()
        heading.append('<span class="icon">')
        if (collapsed) {
            this.element.addClass('collapsed')
            content.hide()
        } else {
            this.element.addClass('expanded')
        }
        heading.on('click', e => {
            this.toggle()
            return false
        })
        if (!content.attr('id')) {
            content.attr('id', this.element.attr('id') + '-collapsible-content')
        }
        heading.attr('aria-expanded', collapsed ? 'false' : 'true')
        heading.attr('aria-controls', content.attr('id'))
    }

    _collapsible_heading() {
    }

    _collapsible_content() {
    }

    expanded() {
        return this.element.hasClass('expanded')
    }

    expand() {
        this.element.removeClass('collapsed')
        this.element.addClass('expanded')
        this._heading.attr('aria-expanded', 'true')
        this._content.slideDown(0.2)
    }

    collapse() {
        this.element.removeClass('expanded')
        this.element.addClass('collapsed')
        this._heading.attr('aria-expanded', 'false')
        this._content.slideUp(0.2)
    }

    toggle() {
        if (this.element.hasClass('collapsed')) {
            this.expand()
        } else {
            this.collapse()
        }
    }

}

lcg.CollapsibleSection = class extends lcg.CollapsibleWidget {
    /* Collapsible section widget.
     *
     * This is the Javascript counterpart of the Python class `lcg.CollapsibleSection'.
     */

    _collapsible_heading() {
        let heading = this.element.find('h1,h2,h3,h4,h5,h6,h7,h8').first()
        heading.addClass('collapsible-section-heading')
        let backref = heading.find('a.backref')
        if (backref) {
            backref.attr('href', '')
        }
        return heading
    }

    _collapsible_content() {
        return this.element.find('div.section-content').first()
    }

}


lcg.CollapsiblePane = class extends lcg.CollapsibleWidget {
    /* Collapsible pane widget.
     *
     * This is the Javascript counterpart of the Python class `lcg.CollapsiblePane'.
     */

    _collapsible_heading() {
        return this.element.find('.pane-title').find('a')
    }

    _collapsible_content() {
        return this.element.find('.pane-content').first()
    }

}


lcg.AudioPlayer = class extends lcg.Widget {

    constructor(elements, swf_uri) {
        super(element)
        this._volume = 0.8
        this._player = this.element.find('.jp-player')
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
        })
        this.element.find('.jp-volume-bar-value').html(Math.round(100 * this._volume) + '%')
        let play_button = this.element.find('button.play-pause')
        this._play_label = play_button.attr('title')
        this._pause_label = play_button.attr('data-pause-label')
        this._remaining_label = this.element.find('.jp-duration').attr('title')
        this._duration_label = this.element.find('.jp-duration').attr('data-duration-label')
        this._bind('play-pause', this._play_pause)
        this._bind('fast-forward', this._skip, true)
        this._bind('rewind', this._skip, false)
        this._bind('volume-up', this._change_volume, true)
        this._bind('volume-down', this._change_volume, false)
        this.element.find('.jp-duration').on('click', this._on_toggle_duration.bind(this))
        play_button.on('keydown', this._on_key_down.bind(this))
    }

    _bind(name, handler, arg) {
        this.element.find('button.' + name).on('click', event => {
            handler.bind(this)(arg)
            $(event.target).focus()
            return false
        })
    }

    _define_keymap() {
        return {
            'Space': function (event, button) { this._play_pause() },
            'Left': function (event, button) { this._skip(false) },
            'Right': function (event, button) { this._skip(true) },
            'Up': function (event, button) { this._change_volume(true) },
            'Down': function (event, button) { this._change_volume(false) },
            'Ctrl-Shift-Left': function (event, button) { this._skip(false) },
            'Ctrl-Shift-Right': function (event, button) { this._skip(true) },
            'Ctrl-Shift-Up': function (event, button) { this._change_volume(true) },
            'Ctrl-Shift-Down': function (event, button) { this._change_volume(false) }
        }
    }

    _play_pause() {
        let status = this._player.data('jPlayer').status
        let action = (status.paused ? 'play' : 'pause')
        this._player.jPlayer(action)
    }

    _seek(time, play) {
        let command = (play ? 'play' : 'pause')
        this._player.jPlayer(command, time)
    }

    _skip(forward) {
        let player = this._player
        let status = player.data('jPlayer').status
        let position = status.currentTime
        let duration = status.duration
        let playing = !status.paused
        if (position !== null && duration !== null) {
            let skip = Math.max(Math.min(duration / 20, 30), 3) // Seconds
            position += skip * (forward ? 1 : -1)
            if (position > duration) {
                return
            }
            if (position < 0) {
                position = 0
            }
            this._seek(position, playing)
        }
    }

    _change_volume(up) {
        let player = this._player
        if (up && this._volume < 1) {
            this._volume = Math.min(this._volume + 0.05, 1)
            player.jPlayer('volume', this._volume)
        }
        if (!up && this._volume > 0) {
            this._volume = Math.max(this._volume - 0.05, 0)
            player.jPlayer('volume', this._volume)
        }
    }

    _on_player_volume_change(event) {
        this._volume = event.jPlayer.options.volume
        this.element.find('.jp-volume-bar-value').html(Math.round(100 * this._volume) + '%')
    }

    _set_play_button_label(label) {
        let button = this.element.find('button.play-pause')
        button.attr('title', label)
        button.find('span').html(label)
    }

    _on_player_play(event) {
        this._set_play_button_label(this._pause_label)
    }

    _on_player_pause(event) {
        this._set_play_button_label(this._play_label)
    }

    _on_toggle_duration(event) {
        let label
        if (this._player.data('jPlayer').options.remainingDuration) {
            label = this._remaining_label
        } else {
            label = this._duration_label
        }
        this.element.find('.jp-duration').attr('title', label)
        this.element.find('.duration-label').html(label)
    }

    _on_player_time_update(event) {
        let status = event.jPlayer.status
    }

    _absolute_uri(uri) {
        let origin = window.location.origin
        if (!origin) {
            // Fix for some older browsers (such as MSIE <= 8)...
            origin = window.location.protocol + "//" + window.location.hostname
            if (window.location.port && window.location.port !== 80) {
                origin += ':' + window.location.port
            }
        }
        if (uri.indexOf(origin) !== 0) {
            uri = origin + uri
        }
        return uri
    }

    _load_if_needed(uri) {
        let status = this._player.data('jPlayer').status
        if (status.media.mp3 !== this._absolute_uri(uri)) {
            this.load(uri)
        }
    }

    _media_type(uri) {
        let ext = uri.split('.').pop().toLowerCase()
        if (ext === 'mp3') {
            return {type: 'mp3', media: 'audio/mpeg'}
        } else if (ext === 'ogg' || ext === 'oga') {
            return {type: 'oga', media: 'audio/ogg codecs="vorbis"'}
        } else if (ext === 'wav' || ext === 'wave') {
            return {type: 'wav', media: 'audio/wav codecs="1"'}
        } else if (ext === 'aac' || ext === 'm4a') {
            return {type: 'aac', media: 'audio/mp4 codecs="mp4a.40.2"'}
        } else {
            return undefined
        }
    }

    _can_play_audio(uri) {
        let type = this._media_type(uri)
        if (!type) {
            return false
        }
        let audio = this.element.find('audio')
        if (audio) {
            // If the browser supports the <audio> tag, jPlayer will use it and
            // we can get the media support information from its API.
            return !!(audio.canPlayType && audio.canPlayType(type.media).replace(/no/, ''))
        } else if (!this.element.find('.jp-no-solution').visible()) {
            // The div 'jp-no-solution' made visible by jPlayer if Flash is unavailable
            // so the above condition means that the Flash fallback will be used and
            // thus we return true only for formats known to be supported by Flash.
            return (type.type == 'mp3' || type.type == 'aac')
        } else {
            return false
        }
    }

    load(uri) {
        this._player.jPlayer('setMedia', {
            mp3: uri
        })
    }

    play() {
        this._player.jPlayer('play')
    }

    bind_audio_control(element_id, uri) {
        if (this._can_play_audio(uri)) {
            // Only bind the player to the control if it is capable of playing
            // given media type.  Otherwise leave the original HTML element
            // untouched.  Suppose that it already provides some fallback
            // functionality (such as download).
            let element = this._element(element_id)
            element.on('click', event => {
                this._load_if_needed(uri)
                this._play_pause()
                return false
            })
            element.on('keydown', event => {
                this._load_if_needed(uri)
                this._on_key_down(event)
            })
        }
    }

}

lcg.Cookies = class {

    constructor(path, domain) {
        this.path = path || '/'
        this.domain = domain || null
    }

    set(name, value, days) {
        let cookie = (name +'='+ escape(String(value)) + '; ' +
                      'SameSite=Lax; ' +
                      'Path=' + escape(this.path))
        if (days) {
            let date = new Date()
            date.setTime(date.getTime() + (days*24*60*60*1000))
            cookie += '; Expires=' + date.toGMTString()
        }
        if (this.domain) {
            cookie += '; Domain=' + escape(this.domain)
        }

        document.cookie = cookie
    }

    get(name) {
        return document.cookie.split('; ').reduce((r, v) => {
            const parts = v.split('=')
            return parts[0] === name ? decodeURIComponent(parts[1]) : r
        }, '')
    }

    clear(name) {
        this.set(name, '', -1)
    }

    clearAll() {
        for (let name of document.cookie.split(';').collect(s => s.split('=').first().trim())) {
            this.clear(name)
        }
    }

}

lcg.cookies = new lcg.Cookies()

lcg.widget_instance = function (element) {
    /* Return a JavaScript widget instance for given DOM element or null.
     *
     * If given DOM element has an associated JavaScript widget instance,
     * return this instance or return null if the element doesn't belong to a
     * JavaScript widget.
     *
     */
    if (element instanceof jQuery) {
        element = element[0]
    } else if (typeof element === 'string') {
        element = document.getElementById(element)
    }
    if (element && element._lcg_widget_instance) {
        return element._lcg_widget_instance
    }
    return null
}
