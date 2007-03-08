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

"""Generic content abstraction.

The classes defined in this module were designed to represent general content
elements of a structured document, such as sections, paragrapgs, lists, tables
etc.  Each content element is represented by an instance of one of the classes
defined below.  Some types of elements can contain other elements and thus the
whole document is represented by a tree of content elements.  When the
construction of the whole tree is finished, each element knows its ancestor
(the container) and all the successors (sub-content) in the tree.

The content hierarchy may be built independently, however you need to assign a
content to a 'ContentNode' instance to be able to export it.

Please note the difference between the hierarchy of content within one node and
the hierarchy of the nodes themselves.

"""

from lcg import *

_ = TranslatableTextFactory('lcg')

class Content(object):
    """Generic base class for all types of content.

    One instance always makes a part of one document/node -- it cannot be split
    over multiple output nodes.  On the other hand, one node usually consists
    of multiple 'Content' instances (elements).  Each content element may be
    contained in another content element (see the 'Container' class) and thus
    they make a hierarchical structure.

    """
    _ALLOWED_CONTAINER = None
    
    def __init__(self, lang=None, **kwargs):
        """Initialize the instance.

        Arguments:

          lang -- content language as an ISO 639-1 Alpha-2
            language code (lowercase).

        """
        self._parent = None
        self._container = None
        self._lang = lang
        super(Content, self).__init__(**kwargs)
        
    def sections(self):
        """Return the contained sections as a sequence of 'Section' instances.

        This method allows creation of tables of contents and introspection of
        content hierarchy.
        
        An empty list is returned in the base class.  The derived
        classes, however, can override this method to return the list of
        contained subsections.

        """
        return ()
        
    def set_container(self, container):
        if __debug__:
            cls = self._ALLOWED_CONTAINER or Container
            assert isinstance(container, cls), \
                   "Not a '%s' instance: %s" % (cls.__name__, container)
        self._container = container

    def set_parent(self, node):
        assert isinstance(node, ContentNode), \
               "Not a 'ContentNode' instance: %s" % node
        assert self._parent is None or self._parent is node, \
               "Reparenting not allowed: %s -> %s" % (self._parent, node)
        self._parent = node

    def parent(self):
        """Return the parent 'ContentNode' of this content element."""
        parent = self._parent or self._container and self._container.parent()
        assert parent is not None, "Parent unknown: %s" % self
        return parent

    def _container_path(self):
        path = [self]
        while path[0]._container is not None:
            path.insert(0, path[0]._container)
        return tuple(path)

    def lang(self):
        return self._lang or self._container and self._container.lang()

    def export(self, exporter):
        """Return the HTML formatted content as a string."""
        return ''

    
class HorizontalSeparator(Content):
    
    def export(self, exporter):
        """Return the HTML formatted content as a string."""
        return exporter.generator().hr()
        

class TextContent(Content):
    """A simple piece of text."""

    def __init__(self, text, **kwargs):
        """Initialize the instance.

        Arguments:

          text -- the actual text content of this element as a string.
          kwargs -- keyword arguemnts for parent class constructor.

        """
        assert isinstance(text, (str, unicode)), text
        super(TextContent, self).__init__(**kwargs)
        self._text = text

    def __str__(self):
        text = str(self._text).strip()
        sample = text and text.splitlines()[0] or ''
        if len(sample) > 20:
            sample = sample[:20]
        if len(sample) < len(text):
            sample += '...'
        cls = self.__class__.__name__
        return '<%s at 0x%x text="%s">' % (cls, id(self), sample)

    def export(self, exporter):
        return self._text

    
class WikiText(TextContent):
    """Formatted text using a simple Wiki-based markup.

    See 'MarkupFormatter' for more information about the formatting rules.
    
    """
    def export(self, exporter):
        return exporter.format(self.parent(), self._text)

    
class PreformattedText(TextContent):
    """Preformatted text."""
    def export(self, exporter):
        g = exporter.generator()
        return g.pre(g.escape(self._text), cls="lcg-preformatted-text")

    
class Link(TextContent):
    _HTML_TAG = re.compile(r'<[^>]+>')
    
    class ExternalTarget(object):
        def __init__(self, uri, title, descr=None):
            self._uri = uri
            self._title = title
            self._descr = descr
        def uri(self):
            return self._uri
        def title(self):
            return self._title
        def descr(self):
            return self._descr
    
    def __init__(self, target, label=None, type=None):
        assert isinstance(target, (Section, ContentNode,
                                   self.ExternalTarget)), target
        self._target = target
        self._type = type
        super(Link, self).__init__(label or '')

    def _descr(self):
        target = self._target
        if isinstance(target, (ContentNode, self.ExternalTarget)):
            descr = target.descr()
        elif target.parent() is not self.parent():
            # TODO: This hack removes any html from the section title (it is
            # used as an HTML attribute value).  But section titles should
            # probably rather not be allowed to contain html.
            section_title = self._HTML_TAG.sub('', target.title())
            descr = concat(section_title, " (", target.parent().title(), ")")
        else:
            descr = None
        return descr
    
    def export(self, exporter):
        label = self._text or self._target.title()
        uri = exporter.uri(self._target)
        g = exporter.generator()
        return g.link(label, uri, title=self._descr(), type=self._type)


class Anchor(TextContent):
    """An anchor (target of a link)."""
    def __init__(self, anchor, text=''):
        assert isinstance(anchor, str)
        self._anchor = anchor
        super(Anchor, self).__init__(text)

    def anchor(self):
        return self._anchor
        
    def export(self, exporter):
        return exporter.generator().link(self._text, None, name=self.anchor())


class InlineImage(Content):

    def __init__(self, image):
        assert isinstance(image, Image)
        self._image = image
        super(InlineImage, self).__init__()

    def export(self, exporter):
        img = self._image
        return exporter.generator().img(img.uri(), alt=img.title(),
                                        width=img.width(), height=img.height())


class Container(Content):
    """Container of multiple parts, each of which is a 'Content' instance.

    Containers allow to build a hierarchy of 'Content' instances inside the
    scope of one node.  This is an addition to the hierarchy of the actual
    nodes (separate pages).

    All the contained (wrapped) content elements will be notified about the
    fact, that they are contained within this container and thus belong to the
    hierarchy.

    """
    _TAG = None
    _ATTR = None
    _CLASS = None
    _ALLOWED_CONTENT = Content
    _EXPORT_INLINE = False
    _CONTENT_SEPARATOR = ''

    def __init__(self, content, **kwargs):
        """Initialize the instance.

        Arguments:
        
          content -- the actual content wrapped into this container as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.
          kwargs -- keyword arguemnts for parent class constructor.

        """
        super(Container, self).__init__(**kwargs)
        cls = self._ALLOWED_CONTENT
        if isinstance(content, (list, tuple)):
            assert is_sequence_of(content, cls), \
                   "Not a '%s' instances sequence: %s" % (cls.__name__, content)
            self._content = tuple(content)
        else:
            assert isinstance(content, cls), \
                   "Not a '%s' instance: %s" % (cls.__name__, content)
            self._content = (content,)
        for c in self._content:
            c.set_container(self)

    def content(self):
        return self._content
            
    #def export(self, exporter):
    #    return "".join([p.export(exporter) for p in self._content])

    def _exported_content(self, exporter):
        return [p.export(exporter) for p in self._content]
    
    def export(self, exporter):
        tag = self._TAG
        exported = self._exported_content(exporter)
        attr = self._lang   and ' lang="%s"'  % self._lang  or ''
        attr += self._CLASS and ' class="%s"' % self._CLASS or ''
        attr += self._ATTR  and (' '+self._ATTR) or ''
        if attr and not tag:
            tag = 'div'
        if tag:
            exported = ['<%s>' % (tag+attr)] + exported + ['</%s>' % tag]
        result = concat(exported, separator=self._CONTENT_SEPARATOR)
        if not self._EXPORT_INLINE:
            result += "\n"
        return result
            
class Paragraph(Container):
    """A paragraph of text, where the text can be any 'Content'."""
    _TAG = 'p'

    
class ItemizedList(Container):
    """An itemized list."""

    TYPE_UNORDERED = 'UNORDERED'
    TYPE_ALPHA = 'ALPHA'
    TYPE_NUMERIC = 'NUMERIC'
    
    def __init__(self, content, type=TYPE_UNORDERED, **kwargs):
        assert type in (self.TYPE_UNORDERED,
                        self.TYPE_ALPHA,
                        self.TYPE_NUMERIC)
        self._type = type
        super(ItemizedList, self).__init__(content, **kwargs)

    def export(self, exporter):
        o, s = {self.TYPE_UNORDERED: (False, None),
                self.TYPE_NUMERIC: (True, None),
                self.TYPE_ALPHA: (True, 'lower-alpha')}[self._type]
        items = [p.export(exporter) for p in self._content]
        return exporter.generator().list(items, ordered=o, style=s, lang=self._lang)

    
class Definition(Container):
    """A single definition pair for the 'DefinitionList'."""
    
    def __init__(self, term, description):
        super(Definition, self).__init__((term, description))

    def export(self, exporter):
        t, d = [c.export(exporter) for c in self._content]
        return "<dt>%s</dt><dd>%s</dd>\n" % (t,d)

    
class DefinitionList(Container):
    """A list of definitions."""
    _TAG = 'dl'
    _ALLOWED_CONTENT = Definition
Definition._ALLOWED_CONTAINER = DefinitionList

    
class TableCell(Container):
    """One cell in a table."""
    _TAG = 'td'
    _EXPORT_INLINE = True

    
class TableRow(Container):
    """One row in a table."""
    _TAG = 'tr'
    _ALLOWED_CONTENT = TableCell
TableCell._ALLOWED_CONTAINER = TableRow
    
        
class Table(Container):
    """One row in a table."""
    _TAG = 'table'
    _CLASS = 'lcg-table'
    _ALLOWED_CONTENT = TableRow
    _CONTENT_SEPARATOR = "\n"

    def __init__(self, content, title=None, **kwargs):
        assert title is None or isinstance(title, (str, unicode))
        self._title = title
        super(Table, self).__init__(content, **kwargs)
        
    def _exported_content(self, exporter):
        caption = self._title and "<caption>%s</caption>" % self._title or ''
        return [caption] + super(Table, self)._exported_content(exporter)
TableRow._ALLOWED_CONTAINER = Table

    
class Field(Container):
    """A pair of label and a value for a FieldSet."""
    
    def __init__(self, label, value):
        super(Field, self).__init__((label, value))

    def export(self, exporter):
        f = '<tr><th align="left" valign="top">%s:</th><td>%s</td></tr>\n'
        return f % tuple([c.export(exporter) for c in self._content])

    
class FieldSet(Table):
    """A list of label, value pairs (fields)."""
    _CLASS = 'lcg-fieldset'
    _ALLOWED_CONTENT = Field
Field._ALLOWED_CONTAINER = FieldSet

    
class SectionContainer(Container):
    """A 'Container' which recognizes contained sections.

    'SectionContainer' acts as a 'Container', but for any contained 'Section'
    instances, a local 'TableOfContents' can be created automatically,
    preceding the actual content (depending on the 'toc_depth' constructor
    argument).  The contained sections are also returned by the 'sections()'
    method to allow building a global `TableOfContents'.

    """

    def __init__(self, content, toc_depth=99, **kwargs):
        """Initialize the instance.

        Arguments:

          content -- same as in the parent class.
          toc_depth -- the depth of local table of contents.  Corresponds to
            the same constructor argument of 'TableOfContents'.

        """
        super(SectionContainer, self).__init__(content, **kwargs)
        sections = []
        toc_sections = []
        already_has_toc = False
        for s in self._content:
            if isinstance(s, TableOfContents) and not sections:
                already_has_toc = True
            elif isinstance(s, Section):
                sections.append(s)
                if s.in_toc():
                    toc_sections.append(s)
        self._sections = sections
        if toc_depth > 0 and not already_has_toc and \
               (len(toc_sections) > 1 or len(toc_sections) == 1 and 
                len([s for s in toc_sections[0].sections() if s.in_toc()])):
            self._toc = TableOfContents(self, title=_("Index:"),
                                        depth=toc_depth)
        else:
            self._toc = Content()
        self._toc.set_container(self)
        

    def sections(self):
        return self._sections
    
    def _exported_content(self, exporter):
        toc = self._toc.export(exporter)
        sections = super(SectionContainer, self)._exported_content(exporter)
        return [toc] + sections
    
    
class Section(SectionContainer):
    """Section wraps the subordinary contents into an inline section.

    Section is very similar to a 'SectionContainer', but there are a few
    differences:

      * Every section has a title, which appears in the output document as a
        heading.

      * Section can be referenced using an HTML anchor.

      * Sections are numbered.  Each section knows it's number within it's
        container.
    
    """
    _ANCHOR_PREFIX = 'sec'
    
    def __init__(self, title, content, anchor=None, toc_depth=0,
                 in_toc=True, **kwargs):
        """Initialize the instance.

        Arguments:

          title -- section title as a string.
          content -- the actual content wrapped into this section as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.
          anchor -- section anchor name as a string.  If None (default) the
            anchor name will be generated automatically.  If you want to refer
            to a section explicitly from somewhere, you will probably not rely
            on the default anchor name, so that's how you can define your own.
            This also allows you to find a section by it's anchor name in the
            hierarchy (see 'ContentNode.find_section()').
          toc_depth -- The depth of the local Table of Contents (see
            'SectionContainer').
          in_toc -- a boolean flag indicating whether this section is supposed
            to be included in the Table of Contents.
            
        """
        assert isinstance(title, (str, unicode)), title
        assert isinstance(anchor, (str, unicode)) or anchor is None, anchor
        assert isinstance(in_toc, bool), in_toc
        self._title = title
        self._in_toc = in_toc
        self._anchor = anchor
        self._backref_used = False
        super(Section, self).__init__(content, toc_depth=toc_depth, **kwargs)
        

    def _section_path(self):
        return [c for c in self._container_path() if isinstance(c, Section)]
    
    def section_number(self):
        """Return the number of this section within it's container as int."""
        return list(self._container.sections()).index(self) + 1
    
    def title(self):
        """Return the section title as a string."""
        return self._title

    def in_toc(self):
        """Return True if the section is supposed to appear in TOC."""
        return self._in_toc
    
    def anchor(self):
        """Return the anchor name for this section."""
        if self._anchor is not None:
            return self._anchor
        else:
            numbers = [str(x.section_number()) for x in self._section_path()]
            return self._ANCHOR_PREFIX + '.'.join(numbers)
        
    def backref(self, node):
        # We can allow just one backref target on the page.  Links on other
        # pages are not backreferenced.
        if node is self.parent() and not self._backref_used:
            self._backref_used = True
            return self._backref()
        else:
            return None
    
    def _backref(self):
        return "backref-" + self.anchor()
        
    def _header(self, exporter):
        if self._backref_used:
            href = "#"+self._backref()
        else:
            href = None
        g = exporter.generator()
        return g.h(g.link(self.title(), href, cls='backref',
                          name=self.anchor()),
                   len(self._section_path()) + 1)+'\n'

    def export(self, exporter):
        return concat(self._header(exporter),
                      super(Section, self).export(exporter),
                      separator="\n")


class NodeIndex(Content):
    """A Table of Contents which lists the node subtree of the current node."""

    def __init__(self, title=None, depth=1, detailed=True):
        """Initialize the instance.

        Arguments:

          title -- the title of the TOC as a string.
          
          depth -- how deep in the hierarchy should we go.
          
          detailed -- A True (default) value means that the 'Content' hierarchy
            within the leave nodes of the node tree will be included in the
            TOC.  False means to consider only 'ContentNode' hierarchy.

        """
        super(NodeIndex, self).__init__()
        assert title is None or isinstance(title, (str, unicode))
        assert isinstance(depth, int)
        assert isinstance(detailed, bool)
        self._title = title
        self._depth = depth
        self._detailed = detailed
                      
    def _export_title(self, exporter):
        return exporter.generator().strong(self._title)

    def _start_item(self):
        return self.parent()
        
    def export(self, exporter):
        toc = self._make_toc(exporter, self._start_item(), depth=self._depth)
        if self._title is not None:
            #TODO: add a "skip" link?
            return exporter.generator().div((self._export_title(exporter),
                                             toc),
                                            cls="table-of-contents")
        else:
            return toc
        
    def _make_toc(self, exporter, item, indent=0, depth=1):
        g = exporter.generator()
        if depth <= 0:
            return ''
        items = ()
        if isinstance(item, ContentNode):
            items = [node for node in item.children() if not node.hidden()]
        if len(items) == 0 and self._detailed:
            if isinstance(item, (tuple, list)):
                items = item
            else:
                items = [s for s in item.sections() if s.in_toc()]
        if len(items) == 0:
            return ''
        links = []
        for i in items:
            uri = exporter.uri(i, relative_to=self.parent())
            name = isinstance(i, Section) and i.backref(self.parent()) or None
            links.append(g.link(i.title(), uri, name=name) + \
                         self._make_toc(exporter, i, indent=indent+4,
                                        depth=depth-1))
        return concat("\n", g.list(links, indent=indent), "\n", ' '*(indent-2))

    
class TableOfContents(NodeIndex):
    """A Table of Contents which lists the content subtree."""
    
    def __init__(self, start=None, **kwargs):
        """Initialize the instance.
        
        Arguments:
        
          item -- the place where to start in the content hierarchy tree as a
            'Content' instance.  None means to start at the container (a local
            Table of Contents).  See 'Section' documentation for more
            information how the content tree is built.
            
          **kwargs -- all other arguments are passed to parent class
            constructor.
        
        """
        assert isinstance(start, Content) or start is None
        self._start_item_ = start
        super(TableOfContents, self).__init__(**kwargs)
        
    def _start_item(self):
        start_item = self._start_item_
        if not start_item:
            assert isinstance(self._container, SectionContainer)
            start_item = self._container
        return start_item
    
    
# Convenience functions for simple content construction.

def coerce(content):
    """Coerce the argument into an LCG content element.

    If the argument is a sequence, a 'Container' of all items is returned.
    Moreover each item is coerced as-well and 'None' items are omitted.  It the
    argument is a string, it is turned into a 'TextContent' instance and if it
    is a 'Content' element, it is returned as is.  Any other argument raises
    AssertionError.

    """
    if isinstance(content, (list, tuple)):
        return Container([coerce(item)
                          for item in content if item is not None])
    elif isinstance(content, (str, unicode)):
        return TextContent(content)
    else:
        assert isinstance(content, Content)
        return content
    
def link(target, label=None, type=None, descr=None):
    """Return a 'Link' instance.

    Arguments:
      target


    """
    if isinstance(target, (str, unicode)):
        assert label is not None
        target = Link.ExternalTarget(target, label, descr=descr)
        label = None
    else:
        assert descr is None
        assert isinstance(target, (ContentNode, Section, Link.ExternalTarget))
    return Link(target, label=label, type=type)
    
def dl(items):
    """Create a 'DefinitionList' from a sequence of (TERM, DESCRIPTION) pairs.

    Each term and definition in the sequence is coerced and the pair is
    automatically turned into a 'Definition' instance.

    """
    return DefinitionList([Definition(coerce(term), coerce(descr))
                           for term, descr in items])

def ul(items):
    """Create an 'ItemizedList' by coercing given sequence of items."""
    return ItemizedList([coerce(item) for item in items])

def p(*items):
    """Create a 'Paragraph' by coercing all arguments."""
    return Paragraph([coerce(item) for item in items])

def join(items, separator=' '):
    """Coerce all items and put the coerced separator in between them."""
    sep = coerce(separator)
    result = []
    for item in items:
        if result:
            result.append(sep)
        result.append(coerce(item))
    return coerce(result)
