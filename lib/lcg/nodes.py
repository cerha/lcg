# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2012 Brailcom, o.p.s.
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

"""Document structure abstraction.

The complete LCG publication typically consists of multiple documents which form a hierarchy.  See
the module 'content' for classes representing the content hierarchy within one document.  Each
document in the hierarchy is represented by a single 'ContentNode' instance (defined below).

"""

from lcg import *

import functools

class ContentNode(object):
    """Representation of one output document within an LCG publication.

    This class represents a generic node of the document structure.  Each node
    has its 'Content' and may have several child nodes.

    By instantiating a node, the content is ready for export (see 'Content' for
    more details).
    
    """

    def __init__(self, id, title=None, brief_title=None, descr=None, variants=(), content=None,
                 children=(), hidden=False, active=True, resource_provider=None, globals=None,
                 page_header=None, page_footer=None, left_page_footer=None, right_page_footer=None,
                 first_page_header=None, page_background=None, presentation=None):
        """Initialize the instance.

        Arguments:

          id -- a unique textual identifier of this node (as a string).
          title -- the title of this node (as a unicode string).
          brief_title -- the brief (shorter) form of title of this node (as a unicode string).  If
            given, this title will be used to refer to this node from places, where brevity
            matters.  If None, the 'title' will be used instead.
          descr -- a short textual description of this node (as a uni code string).  Additional
            information, which may determine the content of the node in addition to the title.
          variants -- a sequence of all available language variants of this node.  The
            sequence contains lowercase ISO 639-1 Alpha-2 language codes as strings.  
          content -- a content element hierarchy.  This is the actual content of this node.  The
            value can be a `Content' instance or a sequence of `Content' instances.            
          children -- a sequence of child nodes in the hierarchy.
          hidden -- a boolean flag indicating, that this node should not appear in the
            automatically generated Indexes (Tables of Contents).  Such a node will usually be
            refered explicitely.
          active -- a boolean flag indicating, that this node is active.  Usage of this flag may be
            application specific and there is currently no difference in behavior of LCG in respect
            to this flag, except for marking the links by css class 'inactive' on export.
          resource_provider -- a 'ResourceProvider' instance or None.
          globals -- node global variables as a dictionary keyed by variable names.  The variables
            are allowed to contain nested dictionaries.  The variables are used for substitution
            within `MarkupFormatter', but they may be also used for other purposes depending on the
            application.
          page_header -- dictionary of 'Content' instances, with language codes
            as keys, to be inserted at the top of each generated page.  If content is
            'None', no page header is inserted.
          page_footer -- dictionary of 'Content' instances, with language codes
            as keys, to be inserted at the bottom of each generated page.  If
            content is 'None', no page footer is inserted.
          first_page_header -- dictionary of 'Content' instances, with language
            codes as keys, to be inserted at the top of the first generated
            page.  If content is 'None', page_header (if any) is used on all
            pages.
          page_background -- dictionary of 'Content' instances, with language codes
            as keys, to be put on the background of each generated page.  If content is
            'None', nothing is put on the background.
          presentation -- dictionary of 'Presentation' instances (or 'None'
            values) associated with this node, with language codes as keys.
          
        """
        assert isinstance(id, basestring), repr(id)
        assert isinstance(hidden, bool), hidden
        assert isinstance(active, bool), active
        assert isinstance(variants, (list, tuple))
        self._id = id
        self._parent = None #parent
        self._title = title or brief_title or id
        self._brief_title = brief_title or title
        self._descr = descr
        self._hidden = hidden
        self._active = active
        self._variants = tuple(variants)
        assert page_header is None or isinstance(page_header, dict) and all ([x is None or isinstance(x, Content) for x in page_header.values()]), page_header
        self._page_header = page_header
        assert first_page_header is None or isinstance(first_page_header, dict) and all ([x is None or isinstance(x, Content) for x in first_page_header.values()]), first_page_header
        self._first_page_header = first_page_header
        assert page_footer is None or isinstance(page_footer, dict) and all ([x is None or isinstance(x, Content) for x in page_footer.values()]), page_footer
        self._page_footer = page_footer
        assert left_page_footer is None or isinstance(left_page_footer, dict) and all ([x is None or isinstance(x, Content) for x in left_page_footer.values()]), left_page_footer
        self._left_page_footer = left_page_footer
        assert right_page_footer is None or isinstance(right_page_footer, dict) and all ([x is None or isinstance(x, Content) for x in right_page_footer.values()]), right_page_footer
        self._right_page_footer = right_page_footer
        assert page_background is None or isinstance(page_background, dict) and all ([x is None or isinstance(x, Content) for x in page_background.values()]), page_background
        self._page_background = page_background
        assert presentation is None or isinstance(presentation, dict) and all ([x is None or isinstance(x, Presentation) for x in presentation.values()]), presentation
        self._presentation = presentation
        if isinstance(content, (tuple, list)):
            content = Container(content)
        assert isinstance(content, Content), content
        content.set_parent(self)
        self._content = content
        for child in children:
            assert isinstance(child, ContentNode)
            child._set_parent(self)
        self._children = children
        self._resource_provider = resource_provider
        if globals is None:
            self._globals = {}
        else:
            self._globals = copy.copy(globals)
        #if __debug__:
        #    seen = {}
        #    for n in self.linear():
        #        nid = n.id()
        #        assert nid not in seen, \
        #               "Duplicate node id: %s, %s" % (n, seen[nid])
        #        seen[nid] = n
        
    def __str__(self):
        return "<%s[%x] id='%s'>" % (self.__class__.__name__, positive_id(self), self.id())

    def _set_parent(self, node):
        assert isinstance(node, ContentNode)
        assert self._parent is None
        self._parent = node

    # Public methods

    def parent(self):
        """Return the parent node of this node."""
        return self._parent
    
    def id(self):
        """Return a unique id of this node as a string."""
        return self._id
        
    def title(self, brief=False):
        """Return the title of this node as a string.

        If a true value is passed to the optional argument 'brief', a shorter
        version of the title will be returned, when available.
        
        """
        return brief and self._brief_title or self._title
    
    def heading(self):
        """Return formatted node title as a 'Content' instance.

        The title is interpreted as a markup text and corresponding 'Content'
        instance was created.

        """
        return FormattedText(self.title())
    
    def descr(self):
        """Return a short description of this node as a string or None."""
        return self._descr

    def hidden(self):
        """Return True if this is a hidden node (should not appear in TOC)."""
        return self._hidden
        
    def active(self):
        """Return the value of the 'active' flag as passed in the constructor.."""
        return self._active
        
    def children(self):
        """Return the list of all subordinate nodes as a tuple."""
        return tuple(self._children)

    def content(self):
        return self._content
    
    def sections(self, context):
        """Return all the top-level sections within this node's content."""
        return self._content.sections(context)
    
    def find_section(self, anchor, context):
        def find(anchor, sections):
            for s in sections:
                if s.anchor() == anchor:
                    return s
                found = find(anchor, s.sections(context))
                if found:
                    return found
            return None
        return find(anchor, self.sections(context))

    def find_node(self, id):
        def find(id, node):
            if node.id() == id:
                return node
            for n in node.children():
                found = find(id, n)
                if found:
                    return found
            return None
        return find(id, self)
    
    def root(self):
        """Return the top-most node of the hierarchy."""
        if self._parent is None:
            return self
        else:
            return self._parent.root()

    def path(self, relative_to=None):
        """Return the path from root to this node as a sequence of nodes.

        When the optional argument `relative_to' is specified, the returned
        path is relative to this node, when it exists in the path.
        
        """
        if self._parent is None or self._parent is relative_to:
            return (self,)
        else:
            return self._parent.path(relative_to=relative_to) + (self,)
        
    def linear(self):
        """Return the linearized subtree of this node as a list."""
        return [self] + functools.reduce(lambda l, n: l + n.linear(), self.children(), [])

    def next(self):
        """Return the node following this node in the linearized structure."""
        linear = self.root().linear()
        i = linear.index(self)
        if i < len(linear)-1:
            return linear[i+1]
        else:
            return None
    
    def prev(self):
        """Return the node preceding this node in the linearized structure."""
        linear = self.root().linear()
        i = linear.index(self)
        if i > 0:
            return linear[i-1]
        else:
            return None

    def index(self, node):
        """Return the child node's index number within this node's children.

        The numbering begins at zero and corresponds to the natural order of
        child nodes.
        
        """
        return self._children.index(node)

    def top(self):
        """Return the top level node in the hierarchy as a 'ContentNode' instance."""
        parent = self._parent
        if parent is None:
            return self
        else:
            return parent.top()
        
    def variants(self):
        """Return the tuple of available language variants of this node.

        The returned tuple consists of language codes including the language of
        the current node.
        
        """
        return self._variants
        
    def globals(self):
        """Return the node variables as a dictionary keyed by variable names."""
        return self._globals

    def global_(self, name):
        """Return value of node variable named 'name'.

        If the variable is not present in this instance globals, look for it in
        parent nodes.

        Arguments:

          name -- name of the variable, string

        """
        if name in self._globals:
            result = self._globals[name]
        elif self._parent is not None:
            result = self._parent.global_(name)
        else:
            result = None
        return result

    def set_global(self, name, value, top=False):
        """Set node variable 'name' to 'value'.

        Arguments:

          name -- name of the variable, string
          value -- value of the variable, 'Content' instance
          top -- iff true, set the value in the top node

        """
        assert isinstance(name, str), name
        assert isinstance(value, Content), value
        node = self
        if top:
            while True:
                parent = node.parent()
                if parent is None:
                    break
                node = parent
        node.globals()[name] = value

    def resources(self, cls=None):
        """Return the list of all resources this node depends on.

        The optional argument 'cls' allows restriction of the returned resources by their type
        (class).
        
        """
        if self._resource_provider:
            return self._resource_provider.resources(cls=cls, node=self)
        else:
            return ()
        
    def resource(self, filename, **kwargs):
        """Get the resource instance by its type and relative filename."""
        if self._resource_provider:
            return self._resource_provider.resource(filename, node=self, **kwargs)
        else:
            return None

    def resource_provider(self):
        """Get the 'ResourceProvider' instance associated with this node."""
        return self._resource_provider

    def _lang_parameter(self, dictionary, lang):
        if dictionary is None:
            result = None
        elif lang in dictionary:
            result = dictionary[lang]
        else:
            result = dictionary.get(None)
        return result            
        
    def page_header(self, lang):
        """Return the page header."""
        return self._lang_parameter(self._page_header, lang)

    def page_footer(self, lang):
        """Return the page footer."""
        return self._lang_parameter(self._page_footer, lang)

    def left_page_footer(self, lang):
        """Return the page footer for left pages."""
        return (self._lang_parameter(self._left_page_footer, lang) or
                self._lang_parameter(self._page_footer, lang))

    def right_page_footer(self, lang):
        """Return the page footer for right pages."""
        return (self._lang_parameter(self._right_page_footer, lang) or
                self._lang_parameter(self._page_footer, lang))

    def first_page_header(self, lang):
        """Return the first page header."""
        return self._lang_parameter(self._first_page_header, lang)
        
    def page_background(self, lang):
        """Return the page background."""
        return self._lang_parameter(self._page_background, lang)

    def presentation(self, lang):
        """Return presentation of this node."""
        return self._lang_parameter(self._presentation, lang)
