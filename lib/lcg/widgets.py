# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012 Brailcom, o.p.s.
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

import lcg

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
        
    def _javascript_widget_arguments(self, context):
        """Return a sequence of additional JavaScript class constructor arguments.

        May be overriden in derived classes to add specific arguments.  See
        class documentation for more info.

        """
        return ()

    def export(self, context):
        context.resource('prototype.js')
        context.resource('gettext.js')
        context.resource('lcg.js')
        context.resource('lcg-widgets.css')
        g = context.generator()
        name = self.__class__.__name__
        element_id = context.unique_id()
        return g.concat(self._wrap_exported_widget(context,
                                                   self._export_widget(context),
                                                   id=element_id,
                                                   cls=lcg.camel_case_to_lower(name)+'-widget'),
                        g.script(g.js_call('new lcg.%s' % name, element_id,
                                           *self._javascript_widget_arguments(context))))
    

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
        def is_foldable(node):
            if node.foldable():
                for item in node.children():
                    if not item.hidden():
                        return True
            return False
        def li_cls(node):
            if is_foldable(node):
                cls = 'foldable'
                if node not in path:
                    cls += ' folded'
                return cls
            return None
        def item(node):
            cls = []
            if node is current:
                cls.append('current')
            if not node.active():
                cls.append('inactive')
            # The inner span is necessary because MSIE doesn't fire on click events outside the A
            # tag, so we basically need to indent the link title inside and draw folding controls
            # in this space.  This is only needed for foldable trees, but we render also fixed
            # trees in the same manner for consistency.  The CSS class 'bullet' represents either
            # fixed tree items or leaves in foldable trees (where no further folding is possible).
            content = g.span(node.title(), cls=not is_foldable(node) and 'bullet' or None)
            return g.link(content, context.uri(node), title=node.descr(),
                          cls=' '.join(cls) or None)
        def menu(node, indent=0):
            spaces = ' ' * indent
            items = [g.concat(spaces, '  ',
                              g.li(g.concat(item(n),
                                            menu(n, indent+4)),
                                   cls=li_cls(n)),
                              '\n')
                     for n in node.children() if not n.hidden()]
            if items:
                return g.concat("\n", spaces,
                                g.ul(g.concat('\n', items, spaces)),
                                '\n', ' '*(indent-2))
            else:
                return ''
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
           active -- id (anchor name) of the active tab or None
           **kwargs -- other arguments defined by the parent class
           
        """
        self._active = active
        super(Notebook, self).__init__(content, **kwargs)
    
    def name(self):
        # Avoid creation of the inner div (the name is present in outer div's cls).
        return None
    
    def _export_widget(self, context):
        g = context.generator()
        switcher = g.ul(g.concat([g.li(g.a(s.title(), href='#'+s.anchor(), title=s.descr(),
                                           cls=(s.anchor()==self._active and 'current' or None)),
                                       cls="notebook-tab")
                                  for s in self.sections(context)]),
                        cls='notebook-switcher')
        return g.concat(switcher, lcg.Container.export(self, context))

    
class PopupMenuItem(Widget, lcg.Content):
    """Popup menu item specification."""

    def __init__(self, label, tooltip=None, uri=None, enabled=True, onclick=None):
        """Arguments:
          label -- item title (string)
          tooltip -- item description/tooltip (string)
          uri -- URI where the item points to (string)
          enabled -- indicates whether the item is active
          onclick -- JavaScript code to execute on invocation (string)
        
        """
        self._label = label
        self._tooltip = tooltip
        self._uri = uri
        self._enabled = enabled
        self._onclick = onclick
    def label(self):
        return self._label
    def tooltip(self):
        return self._tooltip
    def uri(self):
        return self._uri
    def enabled(self):
        return self._enabled
    def onclick(self):
        return self._onclick

    
class PopupMenuCtrl(Widget, lcg.Content):
    """Popup menu invocation control.

    The control is rendered as a small down pointing arrow.  Clicking the arrow
    will create and display a popup menu.  The widget may also make a
    surrounding HTML element active on right mouse button click to create the
    same menu.  Thus, for example, a whole table row may display a context menu
    when clicked.  The presence of the arrow is still important for visual
    indication and for accessibility.  The arrow works as an html link which is
    keyboard navigable and invokes the menu when activated (moving keyboard
    focus to the menu).  This makes the menu completely accessible from
    keyboard.

    """

    def __init__(self, items, tooltip=None, active_area_selector=None, **kwargs):
        """Arguments:

           items -- sequence of 'lcg.PopupMenuItem' instances representing menu items.
           tooltip -- tooltip of the popup menu control as a string.
           active_area_selector -- CSS selector string (such as 'tr',
             'div.title', '.menu li' etc.) to identify a surrounding DOM
             element to be observed for 'contextmenu' event.  If passed, the
             corresponding element will also invoke the context menu on right
             mouse button click.
           **kwargs -- other arguments defined by the parent class
           
        """
        self._items = items
        self._tooltip = tooltip
        self._active_area_selector = active_area_selector
        super(PopupMenuCtrl, self).__init__(**kwargs)
        
    def _export_widget(self, context):
        return ''
    
    def _wrap_exported_widget(self, context, content, **kwargs):
        return context.generator().span(content, **kwargs)
    
    def _javascript_widget_arguments(self, context):
        items = [dict(label=context.translate(item.label()),
                      tooltip=context.translate(item.tooltip()),
                      enabled=item.enabled(),
                      uri=item.uri(),
                      onclick=item.onclick())
                 for item in self._items]
        return (items, context.translate(self._tooltip), self._active_area_selector)
