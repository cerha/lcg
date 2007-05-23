# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007 Brailcom, o.p.s.
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

The complete LCG publication typically consists of multiple documents which form a hiararchy.  See
the module 'content' for classes representing the content hierarchy within one document.  Each
document in the hierarchy is represented by a single 'ContentNode' instance (defined below).

"""

from lcg import *

class ContentNode(object):
    """Representation of one output document within an LCG publication.

    This class represents a generic node of the document structure.  Each node
    has its 'Content' and may have several child nodes.

    By instantiating a node, the content is ready for export (see 'Content' for
    more details).
    
    """

    def __init__(self, id, title=None, brief_title=None, descr=None, language=None,
                 secondary_language=None, language_variants=(), content=None, children=(),
                 hidden=False, resource_provider=None):
        """Initialize the instance.

        Arguments:

          id -- a unique textual identifier of this node (as a string).

          title -- the title of this node (as a unicode string).

          brief_title -- the brief (shorter) form of title of this node (as a unicode string).  If
            given, this title will be used to refer to this node from places, where brevity
            matters.  If None, the 'title' will be used instead.

          descr -- a short textual description of this node (as a uni code string).  Additional
            information, which may determine the content of the node in addition to the title.
          
          language -- content language as a lowercase ISO 639-1 Alpha-2
            language code.
            
          secondary_language -- secondary content language (used in citations) as a lowercase ISO
            639-1 Alpha-2 language code.
            
          language_variants -- a sequence of all available language variants of this node.  The
            sequence contains language codes as strings.  The current language variant is added
            automatically to the list if it is not already there.

          content -- a content element hierarchy.  This is the actual content of this node.  The
            value can be a `Content' instance or a sequence of `Content' instances.
            
          children -- a sequence of child nodes in the hierarchy.
            
          hidden -- a boolean flag indicating, that this node should not appear in the
            automatically generated Indexes (Tables of Contents).  Such a node will usually be
            referenced explicitely.

          resource_provider -- a 'ResourceProvider' instance or None.  This provider handles
            all resources used within this node.
        
            
        """
        assert isinstance(id, str), repr(id)
        assert isinstance(hidden, bool), hidden
        assert language is None or isinstance(language, str) and \
               len(language) == 2, repr(language)
        assert secondary_language is None or \
               isinstance(secondary_language, str) and \
               len(secondary_language) == 2, repr(secondary_language)
        assert isinstance(language_variants, (list, tuple))
        self._id = id
        self._parent = None #parent
        self._title = title or brief_title or id
        self._brief_title = brief_title or title
        self._descr = descr
        self._hidden = hidden
        self._language = language
        self._secondary_language = secondary_language
        current_language = self.current_language_variant()
        if current_language and current_language not in language_variants:
            language_variants += (current_language,)
        self._language_variants = tuple(language_variants)
        if isinstance(content, (tuple, list)):
            content = SectionContainer(content)
        assert isinstance(content, Content), content
        content.set_parent(self)
        self._content = content
        for child in children:
            assert isinstance(child, ContentNode)
            child._set_parent(self)
        self._children = children
        self._resource_provider = resource_provider
        #if __debug__:
        #    seen = {}
        #    for n in self.linear():
        #        nid = n.id()
        #        assert not seen.has_key(nid), \
        #               "Duplicate node id: %s, %s" % (n, seen[nid])
        #        seen[nid] = n
        
    def __str__(self):
        return "<%s[%x] id='%s'>" % (self.__class__.__name__, positive_id(self), self.id())

    def _set_parent(self, node):
        assert isinstance(node, ContentNode)
        assert self._parent is None
        self._parent = node
        
    def _node_path(self, relative_to=None):
        """Return the path from root to this node as a sequence of nodes.

        When the optional argument `relative_to' is specified, the returned
        path is relative to this node, when it exists in the path.
        
        """
        if self._parent is None or self._parent is relative_to:
            return (self,)
        else:
            return self._parent._node_path(relative_to=relative_to) + (self,)

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

    def descr(self):
        """Return a short description of this node as a string or None."""
        return self._descr

    def hidden(self):
        """Return True if this is a hidden node (should not appear in TOC)."""
        return self._hidden
        
    def children(self):
        """Return the list of all subordinate nodes as a tuple."""
        return tuple(self._children)

    def content(self):
        return self._content
    
    def sections(self):
        """Return all the top-level sections within this node's content."""
        return self._content.sections()
    
    def find_section(self, anchor):
        def find(anchor, sections):
            for s in sections:
                if s.anchor() == anchor:
                    return s
                found = find(anchor, s.sections())
                if found:
                    return found
            return None
        return find(anchor, self.sections())

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
        
    def linear(self):
        """Return the linearized subtree of this node as a list."""
        return [self] + reduce(lambda l, n: l + n.linear(), self.children(), [])

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

    def language(self):
        """Return the content language as an ISO 639-1 Alpha-2 code."""
        return self._language

    def secondary_language(self):
        """Return the secondary language as an ISO 639-1 Alpha-2 code."""
        return self._secondary_language

    def language_variants(self):
        """Return the tuple of available language variants of this node.

        The returned tuple consists of language codes including the language of
        the current node.
        
        """
        return self._language_variants
        
    def current_language_variant(self):
        # This is in fact only here to allow a strange language setup in
        # eurochance courses.  In other cases, 'self.language()' should
        # directly determine the current language variant.
        return self.language()

    def meta(self):
        """Return the meta data as a tuple of (name, value) pairs."""
        return ()
    
    def resources(self, cls=None):
        """Return the list of all resources this node depends on.

        The optional argument 'cls' allows restriction of the returned resources by their type
        (class).
        
        """
        if self._resource_provider:
            return self._resource_provider.resources(cls=cls)
        else:
            return ()
        
    def resource(self, cls, file, **kwargs):
        """Get the resource instance by its type and relative filename."""
        if self._resource_provider:
            return self._resource_provider.resource(cls, file, **kwargs)
        else:
            return ()
