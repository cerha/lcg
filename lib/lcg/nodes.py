# -*- coding: utf-8 -*-

# Copyright (C) 2004-2015 OUI Technology Ltd.
# Copyright (C) 2019-2020 Tomáš Cerha <t.cerha@gmail.com>
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

The complete LCG publication typically consists of multiple documents which
form a hierarchy.  See the module 'content' for classes representing the
content hierarchy within one document.  Each document in the hierarchy is
represented by a single 'ContentNode' instance (defined below).

"""

from __future__ import unicode_literals

import sys
import lcg
import functools
import copy

from lcg import is_sequence_of

unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str

class ContentNode(object):
    """Representation of one node within an LCG publication.

    This class represents a generic node of publication structure.  Each node
    has its 'Content' and may have several child nodes.  The meaning of one
    node is not strictly defined.  It is typically used for top level chapters,
    but it may be used flexibly together with 'Content' sections to express the
    content structure to fit a particular application.

    """

    def __init__(self, id, title=None, brief_title=None, heading=None,
                 descr=None, children=(), hidden=False, active=True,
                 foldable=False, resource_provider=None, globals=None,
                 cover_image=None, metadata=None, variants=(), **kwargs):
        """Initialize the instance.

        Arguments:

          id -- a unique textual identifier of this node (as a string).
          title -- the title of this node (as a unicode string).
          brief_title -- the brief (shorter) form of title of this node (as a
            unicode string).  If given, this title will be used to refer to
            this node from places, where brevity matters.  If None, the 'title'
            will be used instead.
          heading -- content to be used as node heading.  By default (when
            None), the content is created automatically as TextContent(title),
            but you may pass any lcg.Content instance when some more fancy
            content is desired.
          descr -- a short textual description of this node (as a uni code
            string).  Additional information, which may determine the content
            of the node in addition to the title.
          children -- a sequence of child nodes in the hierarchy.
          hidden -- a boolean flag indicating, that this node should not appear
            in the automatically generated Indexes (Tables of Contents).  Such
            a node will usually be refered explicitely.
          active -- a boolean flag indicating, that this node is active.  Usage
            of this flag may be application specific and there is currently no
            difference in behavior of LCG in respect to this flag, except for
            marking the items by css class 'inactive' on export.
          foldable -- iff true, the node's submenu will be presented as a
            foldable in foldable tree presentations which support it.
          resource_provider -- a 'ResourceProvider' instance or None.
          globals -- node global variables as a dictionary keyed by variable
            names.  The variables are allowed to contain nested dictionaries.
            The variables are used for substitution by `Substitution'
            instances, but they may be also used for other purposes depending
            on the application.
          cover_image -- 'lcg.Resource' instance to be used as a cover image.
          metadata -- an instance of 'lcg.Metadata' defining the publication
            meta data; Only relevant for the root node of the publication.
          variants -- available language variants of this node as a sequence of
            'Variant' instances.  Each item may define a language specific
            variant of language dependent attributes, such as 'content',
            'page_header', 'page_footer' etc. (see 'Variant' constructor
            arguments for a complete list).  These variant specific values will
            take precedence over the same attributes passed directly as
            'ContentNode' arguments (see below).
          content, page_header, first_page_header,
          page_footer, left_page_footer,
          right_page_footer, page_background,
          presentation -- default variants of node content and parameters may
            be passed directly as node keyword arguments.  The names and
            meaning of the arguments match the names of 'lcg.Variant'
            constructor arguments.  These defaults are used when no matching
            variant is found in 'variants' for given export language, when that
            variant does not define given attribute (such as 'page_footer') or
            when 'lang' is not passed to the methods obtaining given content or
            parameter.  The most typical usage is for language independent
            content, which consists of localizable texts (see
            'lcg.Localizable') or for content of undefined language --
            'ContentNode' doesn't force you to define the language of the
            content.

        """
        assert isinstance(id, basestring), repr(id)
        assert isinstance(hidden, bool), hidden
        assert isinstance(active, bool), active
        assert isinstance(foldable, bool), foldable
        assert is_sequence_of(variants, Variant)
        assert is_sequence_of(children, ContentNode)
        assert cover_image is None or isinstance(cover_image, lcg.Image), cover_image
        assert metadata is None or isinstance(metadata, Metadata)
        assert heading is None or isinstance(heading, lcg.Content), heading
        self._id = id
        self._parent = None  # parent
        self._title = title if title is not None else brief_title or id
        self._heading = heading or lcg.TextContent(self._title)
        self._brief_title = brief_title or title
        self._descr = descr
        self._hidden = hidden
        self._active = active
        self._foldable = foldable
        for child in children:
            child._set_parent(self)
        self._children = tuple(children)
        self._resource_provider = resource_provider
        if globals is None:
            self._globals = {}
        else:
            self._globals = copy.copy(globals)
        self._metadata = metadata
        self._variants = tuple(v.lang() for v in variants)
        self._variants_dict = dict((v.lang(), v) for v in variants)
        self._default_variant = Variant('--', **kwargs)
        self._cover_image = cover_image
        for variant in tuple(variants) + (self._default_variant,):
            if variant.content():
                variant.content().set_parent(self)
        self._empty_content = lcg.Content()
        # if __debug__:
        #    seen = {}
        #    for n in self.linear():
        #        nid = n.id()
        #        assert nid not in seen, \
        #               "Duplicate node id: %s, %s" % (n, seen[nid])
        #        seen[nid] = n
        self._used_content_resources = []

    def __repr__(self):
        return "<%s[%x] id='%s'>" % (self.__class__.__name__, lcg.positive_id(self), self.id())

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
        """Return node heading as a 'Content' instance (see constructor)."""
        return self._heading

    def descr(self):
        """Return a short description of this node as a string or None."""
        return self._descr

    def hidden(self):
        """Return True if this is a hidden node (should not appear in TOC)."""
        return self._hidden

    def active(self):
        """Return the value of the 'active' flag as passed in the constructor.."""
        return self._active

    def foldable(self):
        """Return the value of the 'foldable' flag as passed in the constructor.."""
        return self._foldable

    def children(self):
        """Return all subordinate nodes as a tuple."""
        return self._children

    def find_section(self, lang, section_id):
        def find(section_id, sections):
            for s in sections:
                if s.id() == section_id:
                    return s
                found = find(section_id, s.sections())
                if found:
                    return found
            return None
        return find(section_id, self.content(lang).sections())

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
        if i < len(linear) - 1:
            return linear[i + 1]
        else:
            return None

    def prev(self):
        """Return the node preceding this node in the linearized structure."""
        linear = self.root().linear()
        i = linear.index(self)
        if i > 0:
            return linear[i - 1]
        else:
            return None

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
        assert isinstance(name, basestring), name
        assert isinstance(value, lcg.Content), value
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

        The optional argument 'cls' allows restriction of the returned
        resources by their type (class).

        """
        resources = tuple(self._used_content_resources)
        if cls is not None:
            resources = tuple([r for r in resources if isinstance(r, cls)])
        if self._resource_provider:
            resources += tuple(self._resource_provider.resources(cls=cls, node=self))
        return resources

    def resource(self, filename, **kwargs):
        """Get the resource instance by its type and relative filename."""
        for lang in self.variants() or (None,):
            for resource in self.content(lang).resources():
                if resource.filename() == filename:
                    # Hmm, why don't have images here src_file set?
                    if resource not in self._used_content_resources:
                        self._used_content_resources.append(resource)
                    return resource
        if self._resource_provider:
            return self._resource_provider.resource(filename, node=self, **kwargs)
        else:
            return None

    def resource_provider(self):
        """Get the 'ResourceProvider' instance associated with this node."""
        return self._resource_provider

    def cover_image(self):
        """Return the cover image."""
        # TODO: Handle through variants
        return self._cover_image

    def metadata(self):
        """Return metadata of this node."""
        return self._metadata

    def variants(self):
        """Return the tuple of available language variants of this node.

        The returned tuple consists of just the language codes as basestrings.

        """
        return self._variants

    def _variant(self, lang, attr):
        assert lang is not None or not self._variants_dict, \
            ("Passing 'lang' to lcg.ContentNode.%s() is mandatory "
             "when language variants are a defined %s.") % (attr, self._variants)
        for variant in (self._variants_dict.get(lang), self._default_variant,):
            if variant:
                method = getattr(variant, attr)
                result = method()
                if result is not None:
                    return result
        return None

    def content(self, lang=None):
        """Return the main document content for given language.

        If 'lang' is not None, the appropriate language specific content passed
        to the constructor argument 'variants' is returned if found.  If given
        language is not found in variants or if given variant doesn't define
        'content', the content passed to the constructor argument 'content' is
        returned.  This is particularly practical for language neutral content
        (e.g. consisting of translatable texts).  When 'lang' is None (or
        omitted), the content passed to the constructor argument 'content' is
        returned as well, which may be useful for content of undefined
        language.

        """
        return self._variant(lang, 'content') or self._empty_content

    def page_header(self, lang=None):
        """Return the page header content for given language.

        The same rules as described for the method 'content()' apply here
        analogously.

        """
        return self._variant(lang, 'page_header')

    def first_page_header(self, lang=None):
        """Return the first page header content for given language.

        The same rules as described for the method 'content()' apply here
        analogously.

        """
        return self._variant(lang, 'first_page_header') or self.page_header(lang)

    def page_footer(self, lang=None):
        """Return the page footer content for given language.

        The same rules as described for the method 'content()' apply here
        analogously.

        """
        return self._variant(lang, 'page_footer')

    def left_page_footer(self, lang=None):
        """Return the page footer content for left pages for given language.

        The same rules as described for the method 'content()' apply here
        analogously.

        """
        return self._variant(lang, 'left_page_footer') or self.page_footer(lang)

    def right_page_footer(self, lang=None):
        """Return the page footer content for right pages for given language.

        The same rules as described for the method 'content()' apply here
        analogously.

        """
        return self._variant(lang, 'right_page_footer') or self.page_footer(lang)

    def page_background(self, lang=None):
        """Return the page background content for given language.

        The same rules as described for the method 'content()' apply here
        analogously.

        """
        return self._variant(lang, 'page_background')

    def presentation(self, lang=None):
        """Return presentation of this node.

        The same rules as described for the method 'content()' apply here
        analogously.

        """
        return self._variant(lang, 'presentation')


class Variant(object):
    """Definition of language specific values of certain 'ContentNode' attributes."""

    def __init__(self, lang, content=None, page_header=None, first_page_header=None,
                 page_footer=None, left_page_footer=None, right_page_footer=None,
                 page_background=None, presentation=None):
        """Arguments:

          lang -- an ISO 639-1 Alpha-2 language code
          content -- The actual document content as a 'Content' instance or a
            sequence of 'Content' instances.
          page_header -- 'Content' instance to be inserted at the top of each
            output page.  If 'None', no page header is inserted.
          first_page_header -- 'Content' instance to be inserted at the top of
            the first output page.  If 'None', page_header (if any) is used on
            all pages.
          page_footer -- 'Content' instance to be inserted at the bottom of
            each output page.  If 'None', no page footer is inserted.
          left_page_footer -- 'Content' instance to be inserted at the bottom
            of each left side output page.  If 'None', page_footer (if any) is
            used on all pages.
          right_page_footer -- 'Content' instance to be inserted at the bottom
            of each right side output page.  If 'None', page_footer (if any) is
            used on all pages.
          page_background -- 'Content' instance to be put on the background of
            each output page.  If 'None', nothing is put on the background.
          presentation -- 'Presentation' instance to be used for output page
            presentation customization.  If 'None', no specific presentation is
            used.

        """
        def _content(x):
            if isinstance(x, dict) and tuple(x.keys()) == (None,):
                # Handle old hacks gracefully.
                x = x[None]
            if isinstance(x, (tuple, list)):
                x = lcg.Container(x)
            assert x is None or isinstance(x, lcg.Content), x
            return x
        assert isinstance(lang, basestring) and len(lang) == 2, lang
        if isinstance(presentation, dict) and tuple(presentation.keys()) == (None,):
            # Handle old hacks gracefully.
            presentation = presentation[None]
        assert presentation is None or isinstance(presentation, lcg.Presentation), presentation
        self._lang = lang
        self._content = _content(content)
        self._page_header = _content(page_header)
        self._first_page_header = _content(first_page_header)
        self._page_footer = _content(page_footer)
        self._left_page_footer = _content(left_page_footer)
        self._right_page_footer = _content(right_page_footer)
        self._page_background = _content(page_background)
        self._presentation = presentation

    def lang(self):
        return self._lang

    def content(self):
        return self._content

    def page_header(self):
        return self._page_header

    def first_page_header(self):
        return self._first_page_header

    def page_footer(self):
        return self._page_footer

    def left_page_footer(self):
        return self._left_page_footer

    def right_page_footer(self):
        return self._right_page_footer

    def page_background(self):
        return self._page_background

    def presentation(self):
        return self._presentation


class Metadata(object):
    """Meta data describing a publication."""
    authors = ()
    """A sequence of full names of publication content authors."""
    contributors = ()
    """A sequence of full names of publication content contributors.

    Contributors are authors with less significant.

    """
    isbn = None
    """ISBN identifier of the publication."""
    original_isbn = None
    """ISBN identifier of the original work the publication was derived from."""
    uuid = None
    """UUID of the publication (used when ISBN is not assigned)."""
    publisher = None
    """Publisher of the original."""
    published = None
    """Date of publication of the original work."""
    # TODO: Year as a string is currenty expected for publication date.

    def __init__(self, **kwargs):
        """Call with keyword arguments to assign values to instance attributes."""
        if __debug__:
            for key, value in kwargs.items():
                assert hasattr(self, key), "Unknown meta data attribute: %s" % key
                if key in ('authors', 'contributors'):
                    assert isinstance(value, (tuple, list)) and \
                        all(isinstance(name, basestring) for name in value), \
                        "Invalid value for meta data attribute %s: %s" % (key, value)
                else:
                    assert value is None or isinstance(value, basestring), \
                        "Invalid value for meta data attribute %s: %s" % (key, value)
            self.__dict__.update(**kwargs)
