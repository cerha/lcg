# -*- coding: utf-8 -*-

# Copyright (C) 2004-2017 OUI Technology Ltd.
# Copyright (C) 2019 Tomáš Cerha <t.cerha@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Interactive HTML specific widgets with JavaScript handling.

This module includes HTML specific content elements.  Their export is not
performed by the exporter, but by the widget code itself.  Thus it is only
implemented for one output format - the HTML.

The widgets are interactive controls typically used in web applications, such
as foldable tree, notebook, popup menu etc.  All widgets defined here support
keyboard interaction and accessibility through WAI ARIA roles.

The implementation also attempts to make the widgets degrade gracefully when
JavaScript is off (this is important for SEO even if you don't care about non
Javascript browsers).  That is usually done by making the HTML export as simple
as possible (but not missing important information and links) and adding the
interactive controls later by JavaScript, so that they don't disturb when they
don't work.

"""

from __future__ import unicode_literals
import lcg

_ = lcg.TranslatableTextFactory('lcg')


class Widget(object):
    """Mix-in class for content elements implementing HTML Widgets.

    The class itself doesn't implement any particular widget, but implements
    the common parts of widget export.  The widget export is always as follows:

    1. The actual widget content is exported by the particular derived widget
    class by the method '_export_widget()'.

    2. This content is wrapped by the method '_wrap_exported_widget()' into a
    an outer element ('div' by default) which is automatically assigned a
    unique id and defines a CSS class according to derived widget class name,
    such as 'foldable-tree-widget' for the 'FoldableTree' class.

    3. New instance of a JavaScript class of the same name as the derived
    Python class is created and it's constructor is passed the element id
    created in step 2.  Additional arguments may be passed to this JavaScript
    constructor by overriding the method '_javascript_widget_arguments()'.  The
    constructor will usually locate the HTML element by ID and modify its
    content to add interactive controls, assign aria roles and establish
    keyboard and mouse event handling.

    Required JavaScript libraries and CSS files are also loaded automatically.

    """

    def __init__(self, *args, **kwargs):
        """Arguments:

           label -- text to be used for aria-label attribute or the widget's
             root HTML element
           **kwargs -- other arguments passed to parent classes

        """
        self._label = kwargs.pop('label', None)
        self._widget_id = kwargs.pop('id', None)
        super(Widget, self).__init__(*args, **kwargs)

    def _export_widget(self, context):
        """Export the actual widget content.

        Must be overriden in derived classes.  See class documentation for more
        info.

        """
        pass

    def _wrap_exported_widget(self, context, content, **kwargs):
        """Wrap exported widget content by an outer HTML element.

        May be overriden in derived classes to change the element from a 'div'
        to something else.  See class documentation for more info.

        """
        g = context.generator()
        return g.div(content, **kwargs)

    def _javascript_widget_class(self, context):
        """Return the name of the JavaScript class controlling the widget.

        An instance of this class will be created for every widget.  The
        constructor will receive the HTML id of the widget root DOM element.
        The name is by default the same as the name of the Python class and is
        inside the 'lcg' JavaScript namespace.  Derived classes may override
        this method to use a specific (typically derived) JavaScript class.

        """
        return 'lcg.' + self.__class__.__name__

    def _javascript_widget_arguments(self, context):
        """Return a sequence of additional JavaScript class constructor arguments.

        May be overriden in derived classes to add specific arguments.  See
        class documentation for more info.

        """
        return ()

    def _css_class_name(self, context):
        """Return the name of the CSS class assigned to the widget root DOM element.

        The name is by default created by converting the camel-case Python
        class name to hyphen separated words and adding '-widget' to the end
        (for example 'foldable-tree-widget' for the 'FoldableTree' Python
        class).  Derived classes may override this method to use a specific CSS
        class name.

        """

        return lcg.camel_case_to_lower(self.__class__.__name__) + '-widget'

    def export(self, context):
        context.resource('prototype.js')
        context.resource('effects.js')
        context.resource('gettext.js')
        context.resource('lcg.js')
        context.resource('lcg-widgets.css')
        g = context.generator()
        element_id = self._widget_id or context.unique_id()
        return g.concat(
            self._wrap_exported_widget(
                context,
                self._export_widget(context),
                id=element_id,
                aria_label=self._label,
                cls=self._css_class_name(context),
            ),
            g.script(g.js_call('new ' + self._javascript_widget_class(context), element_id,
                               *self._javascript_widget_arguments(context))),
        )


class Button(Widget, lcg.Content):
    """HTML button submitting given values to given URI."""

    def __init__(self, label, uri, values=(), callback=None, tooltip=None, enabled=True,
                 icon=None, **kwargs):
        """Arguments:

           label -- button label as a string
           uri -- target URI where the form is submitted
           values -- list of name/value pairs or a dict containing values
             to be submitted as request parameters to given URI when the
             button is clicked
           callback -- name of the JavaScript function to be called on
             button invocation (will be looked up in the current JavaScript
             name space).  The callback function will be called with the
             instance of 'lcg.Button' JavaScript class as the first argument.
           tooltip -- button description/tooltip as a string
           enabled -- the buton is enabled iff True; False makes it gray
           icon -- icon CSS class name.  If not None, a span with this class
             name will be added before the item label.  The CSS definition of
             the icon must be present in stylesheets.
           **kwargs -- other arguments defined by the parent class

        """
        self._uri = uri
        self._callback = callback
        self._tooltip = tooltip
        self._enabled = enabled
        self._icon = icon
        self._values = list(values.items()) if isinstance(values, dict) else values
        super(Button, self).__init__(label=label, **kwargs)

    def _export_widget(self, context):
        g = context.generator()
        return g.form(
            [g.hidden(name, value is True and 'true' or value) for name, value in self._values] +
            [g.button(g.span('', cls='icon' + ((' ' + self._icon) if self._icon else '')) +
                      g.span(self._label or 'x', cls='label'),
                      title=self._tooltip,
                      disabled=not self._enabled,
                      type='submit',
                      cls='disabled' if not self._enabled else None)],
            action=self._uri,
            method='POST',
        )

    def _javascript_widget_arguments(self, context):
        return (self._callback,)

    def _wrap_exported_widget(self, context, content, **kwargs):
        g = context.generator()
        # Using spans is important to make display: inline-block work in MSIE 8.
        return g.span(content, **kwargs)


class FoldableTree(Widget, lcg.Content):
    """HTML interactive foldable tree menu widget.

    The widget renders as a foldable tree representing the structure of LCG
    nodes.  Folding is performed within the browser (client-side) by the
    supporting JavaScript code.  Note, that folding must be enabled at each
    level of the tree by the 'foldable' flag of the node.  See
    'ContentNode.foldable()'.

    """

    def __init__(self, node=None, tooltip=None, **kwargs):
        """Arguments:

           tooltip -- tooltip of a button to expand/collapse the whole foldable
             tree at once.  If None, the button will not be created at all.
           **kwargs -- other arguments defined by the parent class

        """
        self._node = node
        self._tooltip = tooltip
        super(FoldableTree, self).__init__(**kwargs)

    def _javascript_widget_arguments(self, context):
        return (self._tooltip and context.translate(self._tooltip),)

    def _export_widget(self, context):
        g = context.generator()
        current = context.node()
        while current.parent() is not None and current.hidden():
            current = current.parent()
        path = current.path()

        def item(child):
            submenu = menu(child)
            in_path = child in path
            labels = [x + ' ' + child.title() for x in (_("Expand"), _("Collapse"))]
            label = labels[1 if in_path else 0]
            return g.li(
                content=(
                    g.a(content=(g.span('', cls='icon'),
                                 g.span(child.title(), cls='label')),
                        href=context.uri(child), title=child.descr(),
                        cls=('item ' + ('current ' if child is current else '') +
                             ('inactive ' if not child.active() else '')).strip()),
                    g.a((g.span('', cls='icon'),
                         g.span(label, cls='label')),
                        data_expand_label=labels[0],
                        data_collapse_label=labels[1],
                        role='button', title=label, tabindex=-1,
                        cls='expander') if child.foldable() and submenu else '',
                    submenu),
                cls=((('foldable ' + ('expanded ' if in_path else 'collapsed '))
                      if child.foldable() and submenu else '') +
                     ('in-path' if in_path else '')).strip() or None,
            )

        def menu(node):
            # The 'icon' span must be inside the A tag because MSIE doesn't fire on click
            # events outside.  The span indents the link title and creates a space for
            # the clickable folding controls (if the item is foldable).
            items = [item(child) for child in node.children() if not child.hidden()]
            if items:
                # Add empty <template> tag to work around JavaScript SlideDown effect
                # bug which slides the first element strangely (<template> is one of
                # the few other permitted elements inside <ul>).
                return g.ul([g.template('')] + items, cls='level-%d' % len(node.path()))
            else:
                return g.escape('')
        return menu(self._node or current.root())


class Notebook(Widget, lcg.Container):
    """HTML Notebook widget.

    The widget renders as a notebook with tabs at the top and their content
    below.  Tab switching is performed within the browser (client-side) by the
    supporting JavaScript code.  Only the active tab content is visible at any
    moment.

    The notebook tabs are represented by 'lcg.Section' instances.  The sections
    define tab titles, descriptions and content.  This makes the notebook
    degrade gracefully in non-javascript browsers and possibly also in other
    output formats.

    """
    _ALLOWED_CONTENT = (lcg.Section,)

    def __init__(self, content, active=None, **kwargs):
        """Arguments:

           content -- sequence of 'lcg.Section' instances representing the tabs
           active -- id of the active tab or None
           **kwargs -- other arguments defined by the parent class

        """
        self._active = active
        super(Notebook, self).__init__(content, **kwargs)

    def names(self):
        # Avoid creation of the inner div (the name is present in outer div's cls).
        return ()

    def _wrap_exported_widget(self, context, content, **kwargs):
        if self._names:
            kwargs['cls'] += ' ' + ' '.join(self._names)
        return super(Notebook, self)._wrap_exported_widget(context, content, **kwargs)

    def _export_widget(self, context):
        g = context.generator()
        switcher = g.ul([g.li(g.a(s.title(), href='#' + s.id(), title=s.descr(),
                                  cls=(s.id() == self._active and 'current' or None)),
                              cls="notebook-tab")
                         for s in self.sections()],
                        cls='notebook-switcher')
        return g.concat(switcher, lcg.Container.export(self, context))


class PopupMenuItem(object):
    """Popup menu item specification."""

    def __init__(self, label, tooltip=None, uri=None, enabled=True, callback=None,
                 callback_args=(), icon=None, cls=None):
        """Arguments:
          label -- item title (string)
          tooltip -- item description/tooltip (string).
          enabled -- indicates whether the item is active.
          uri -- URI where the item points to (string).  If None, 'callback'
            must be defined.
          callback -- JavaScript function name to execute (string).  This
            function will be called with the element on which the menu was
            invoked as the first argument.  Additional arguments may be
            optionally specified by 'callback_args'.
          callback_args -- Additional JavaScript callback function arguments
            (tuple of values capable of JSON conversion).
          icon -- icon CSS class name.  If not None, a span with this class
            name will be added before the item label.  The CSS definition of
            the icon must be present in stylesheets.
          cls -- CSS class name to be used for the item.  No class assigned
             when None.

        """
        self.label = label
        self.tooltip = tooltip
        self.uri = uri
        self.enabled = enabled
        self.callback = callback
        self.callback_args = callback_args
        self.icon = icon
        self.cls = cls


class PopupMenu(Widget, lcg.Content):
    """Popup menu widget.

    The popup menu is created as initially hidden.  It must be later popped up
    through JavaScript.  See also 'PopupMenuCtrl' for a control which may be
    used to invoke the menu from the UI.

    Menu items are created in JavaScript only when the menu is actually used
    (when first popped up).  This reduces the browser resource usage as well as
    page initialization overhead, so many menus can be present on one page.

    """

    def __init__(self, items, **kwargs):
        """Arguments:

           items -- sequence of 'lcg.PopupMenuItem' instances representing menu
             items.
           **kwargs -- other arguments defined by the parent class

        """
        self._items = items
        super(PopupMenu, self).__init__(**kwargs)

    def _javascript_widget_arguments(self, context):
        items = [dict(label=context.translate(item.label),
                      tooltip=context.translate(item.tooltip),
                      enabled=item.enabled,
                      uri=item.uri,
                      callback=item.callback,
                      callback_args=item.callback_args,
                      icon=item.icon,
                      cls=item.cls)
                 for item in self._items]
        return (items, context.translate(_("Close menu %s", self._label) if self._label else
                                         _("Close menu")))

    def _wrap_exported_widget(self, context, content, **kwargs):
        return super(PopupMenu, self)._wrap_exported_widget(context, content,
                                                            style='display: none;', **kwargs)

    def _export_widget(self, context):
        # Menu is actually rendered in javascript.
        return ''


class PopupMenuCtrl(Widget, lcg.Container):
    """Popup menu invocation control.

    The control is rendered as a label with a small down pointing arrow on the
    right.  The label is any inner content of the container (this widget is
    lcg.Container).  If the content is empty, only the arrow icon is displayed.
    Clicking the label or the arrow will display a popup menu.  The widget may
    also make a surrounding HTML element active on right mouse button click to
    display the same menu.  Thus, for example, a whole table row may display a
    context menu when clicked.  The presence of the arrow is still important
    for visual indication and for accessibility.  The arrow works as an html
    link which is keyboard navigable and invokes the menu when activated
    (moving keyboard focus to the menu).  This makes the menu completely
    accessible from keyboard.

    """

    def __init__(self, title, items, content=(), active_area_selector=None,
                 **kwargs):
        """Arguments:

           title -- menu title displayed as a tooltip of the popup control and
             also used as accessible title of the arrow icon element.
           items -- sequence of 'lcg.PopupMenuItem' instances representing menu
             items.
           content -- content displayed inside the control (typically a label)
             which invokes the menu when clicked.  If empty, the control will
             only display as a clickable icon.
           active_area_selector -- CSS selector string (such as 'tr',
             'div.title', '.menu li' etc.) to identify a surrounding DOM
             element to be observed for 'contextmenu' event.  If passed, the
             corresponding element will also invoke the context menu on right
             mouse button click.
           **kwargs -- other arguments defined by the parent class

        """
        self._items = items
        self._title = title
        self._active_area_selector = active_area_selector
        super(PopupMenuCtrl, self).__init__(content, **kwargs)

    def _javascript_widget_arguments(self, context):
        return (self._active_area_selector,)

    def _export_widget(self, context):
        g = context.generator()
        content = lcg.Container.export(self, context)
        return g.concat(
            g.span((content, g.span(self._title, title=self._title, cls='popup-arrow')),
                   cls='invoke-menu' + (' labeled' if content else ''), tabindex='0'),
            PopupMenu(self._items, label=self._title).export(context),
        )

    def _wrap_exported_widget(self, context, content, **kwargs):
        g = context.generator()
        # Using spans is important to make display: inline-block work in MSIE 8.
        return g.span(content, **kwargs)


class CollapsibleWidget(Widget):
    """Common base class for CollapsiblePane and CollapsibleSection."""

    def __init__(self, collapsed=True, **kwargs):
        self._collapsed = collapsed
        super(CollapsibleWidget, self).__init__(**kwargs)

    def _javascript_widget_arguments(self, context):
        return (self._collapsed,)


class CollapsiblePane(CollapsibleWidget, lcg.Container):
    """HTML Collapsible pane widget.

    The pane content can be collapsed or expanded.  When collapsed, the pane
    title is displayed.  The title may be clicked to toggle the content
    expansion state.

    """

    def __init__(self, title, content, **kwargs):
        """Arguments:

           title -- pane title as a string
           content -- 'lcg.Content' instance representing collapsible pane content
           collapsed -- pass False to make the pane initially expanded
           **kwargs -- other arguments defined by the parent class

        """
        self._title = title
        super(CollapsiblePane, self).__init__(content=content, **kwargs)

    def _export_widget(self, context):
        g = context.generator()
        return (
            g.div(g.a(self._title, href='javascript:void(0)', role='button'), cls='pane-title') +
            g.div(context.exporter().export_element(context, self), cls='pane-content')
        )


class CollapsibleSection(CollapsibleWidget, lcg.Section):
    """HTML Collapsible section widget.

    Exported like ordinary LCG section, but the section heading
    expands/collapses the section content when clicked.

    """

    def _export_widget(self, context):
        return context.exporter().export_element(context, self)
