# -*- coding: iso8859-2 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006 Brailcom, o.p.s.
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

"""Course content abstraction.

The classes defined in this module were designed to represent general content
elements of a structured document, such as sections, paragrapgs, lists, tables
etc.  Each content element is represented by an instance of one of the classes
defined below.  Some types of elements can contain other elements and thus the
whole document is represented by a tree of content elements.  When the
construction of the whole tree is finished, each element knows its ancestor
(the container) and all the successors (sub-content) in the tree.

All elements in one content tree are bound to one 'ContentNode'.  Please note
the difference between the hierarchy of content within one node and the
hierarchy of the nodes themselves.  The nodes represent distinct documents,
whereas the content always belongs to one of the documents.

Each content element is able to render itself on the output.  This is currently
limited to HTML, however a possible transition to independent renderers was
kept in mind, so it should be possible to allow also other output formats.

"""

import types
import operator

from lcg import *
import _html


class Content(object):
    """Generic base class for all types of content.

    One instance always makes a part of one document -- it cannot be split over
    multiple output documents.  On the other hand, one document usually
    consists of multiple 'Content' instances (elements).

    Each content element may be contained in another content element (see the
    'Container' class) and thus they make a hierarchical structure.  All the
    elements within this structure have the same parent 'ContentNode' instance
    and through it are able to gather some context information and access other
    objects (i.e. the resources).

    """
    _ALLOWED_CONTAINER = None
    
    def __init__(self, parent, lang=None):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.

        """
        assert isinstance(parent, ContentNode), \
               "Not a 'ContentNode' instance: %s" % parent
        self._parent = parent
        self._container = None
        self._lang = lang
        
    def sections(self):
        """Return the contained sections as a sequence of 'Section' instances.

        This method allows creation of tables of contents and introspection of
        content hierarchy.
        
        An empty list is returned in the base class.  The derived
        classes, however, can override this method to return the list of
        contained subsections.

        """
        return ()
        
    def parent(self):
        """Return the parent 'ContentNone' of this content element."""
        return self._parent

    def set_container(self, container):
        if __debug__:
            cls = self._ALLOWED_CONTAINER or Container
            assert isinstance(container, cls), \
                   "Not a '%s' instance: %s" % (cls.__name__, container)
        self._container = container

    def _container_path(self):
        path = [self]
        while path[0]._container is not None:
            path.insert(0, path[0]._container)
        return tuple(path)

    def lang(self):
        lang = self._lang
        if lang is None and self._container is not None:
            lang = self._container.lang()
        if lang is None:
            lang =  self._parent.language()
        return lang

    def export(self):
        """Return the HTML formatted content as a string."""
        return ''

    
class HorizontalSeparator(Content):
    
    def export(self):
        """Return the HTML formatted content as a string."""
        return '<hr/>'
        

class TextContent(Content):
    """A simple piece of text."""

    def __init__(self, parent, text, **kwargs):
        """Initialize the instance.

        Arguments:

          parent -- same as in the parent class.
          text -- the actual text content of this element as a string.
          kwargs -- keyword arguemnts for parent class constructor.

        """
        assert isinstance(text, types.StringTypes), type(text)
        super(TextContent, self).__init__(parent, **kwargs)
        self._text = text

    def __str__(self):
        text = self._text.strip()
        sample = text.splitlines()[0][:10]
        if len(sample) < len(text):
            sample += '...'
        cls = self.__class__.__name__
        return '<%s at 0x%x text="%s">' % (cls, id(self), sample)

    def export(self):
        return self._text

    
        
class WikiText(TextContent):
    """Structured text in Wiki formatting language (on input)."""
        
    def export(self):
        return self._parent.format_wiki_text(self._text)

    
class PreformattedText(TextContent):
    """Preformatted text."""

    def export(self):
        from xml.sax import saxutils
        text = saxutils.escape(self._text)
        return '<pre class="lcg-preformatted-text">'+text+'</pre>'

    
class Link(TextContent):
    """Hypertext reference."""
    _HTML_TAG = re.compile(r'<[^>]+>')
    
    def __init__(self, parent, target, name=''):
        assert isinstance(target, (Section, ContentNode))
        self._target = target
        super(Link, self).__init__(parent, name)

    def label(self):
        return self._text or self._target.title()
    
    def target(self):
        return self._target

    def descr(self):
        target = self._target
        descr = None
        if isinstance(target, ContentNode):
            descr = target.descr()
        elif target.parent() is not self._parent:
            descr = "%s (%s)" % (target.title(), target.parent().title())
        return descr
    
    def export(self):
        # TODO: This hack removes any html from the description (it is used as
        # an HTML attribute value).
        descr = self.descr() and self._HTML_TAG.sub('', self.descr())
        return _html.link(self.label(), self._target.url(), title=descr)

    
class Anchor(TextContent):
    """An anchor (target of a link)."""
    def __init__(self, parent, anchor, text=''):
        assert isinstance(anchor, types.StringType)
        self._anchor = anchor
        super(Anchor, self).__init__(parent, text)

    def anchor(self):
        return self._anchor
        
    def export(self):
        return _html.link(self._text, None, name=self.anchor())

    
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
    _EXPORT_INLINE = False
    _ALLOWED_CONTENT = Content

    def __init__(self, parent, content, **kwargs):
        """Initialize the instance.

        Arguments:
        
          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          content -- the actual content wrapped into this container as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.
          kwargs -- keyword arguemnts for parent class constructor.

        """
        super(Container, self).__init__(parent, **kwargs)
        cls = self._ALLOWED_CONTENT
        if operator.isSequenceType(content):
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
            
    #def export(self):
    #    return "".join([p.export() for p in self._content])

    def _export_content(self, concat=''):
        return concat.join([p.export() for p in self._content])
    
    def export(self):
        tag = self._TAG
        content = self._export_content()
        attr = self._lang   and ' lang="%s"'  % self._lang  or ''
        attr += self._CLASS and ' class="%s"' % self._CLASS or ''
        attr += self._ATTR  and (' '+self._ATTR) or ''
        if attr and not tag:
            tag = 'div'
        if tag:
            content = '<%s>%s</%s>' % (tag + attr, content, tag)
        if not self._EXPORT_INLINE:
            content += "\n"
        return content
            

class Paragraph(Container):
    """A paragraph of text, where the text can be any 'Content'."""
    _TAG = 'p'

    
class ItemizedList(Container):
    """An itemized list."""

    TYPE_UNORDERED = 'UNORDERED'
    TYPE_ALPHA = 'ALPHA'
    TYPE_NUMERIC = 'NUMERIC'
    
    def __init__(self, parent, content, type=TYPE_UNORDERED, **kwargs):
        assert type in (self.TYPE_UNORDERED,
                        self.TYPE_ALPHA,
                        self.TYPE_NUMERIC)
        self._type = type
        super(ItemizedList, self).__init__(parent, content, **kwargs)

    def export(self):
        o, s = {self.TYPE_UNORDERED: (False, None),
                self.TYPE_NUMERIC: (True, None),
                self.TYPE_ALPHA: (True, 'lower-alpha')}[self._type]
        items = [p.export() for p in self._content]
        return _html.list(items, ordered=o, style=s, lang=self._lang)

    
class Definition(Container):
    """A single definition pair for the 'DefinitionList'."""
    
    def __init__(self, parent, term, description):
        super(Definition, self).__init__(parent, (term, description))

    def export(self):
        t, d = [c.export() for c in self._content]
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

    def __init__(self, parent, content, title=None, **kwargs):
        assert title is None or isinstance(title, types.StringTypes)
        self._title = title
        super(Table, self).__init__(parent, content, **kwargs)
        
    def _export_content(self, concat=''):
        caption = self._title and "<caption>%s</caption>" % self._title or ''
        return caption + super(Table, self)._export_content(concat=concat)
TableRow._ALLOWED_CONTAINER = Table

    
class Field(Container):
    """A pair of label and a value for a FieldSet."""
    
    def __init__(self, parent, label, value):
        super(Field, self).__init__(parent, (label, value))

    def export(self):
        f = '<tr><th align="left" valign="top">%s:</th><td>%s</td></tr>\n'
        return f % tuple([c.export() for c in self._content])

    
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

    def __init__(self, parent, content, toc_depth=99, **kwargs):
        """Initialize the instance.

        Arguments:

          parent, content -- same as in the parent class.
          toc_depth -- the depth of local table of contents.  Corresponds to
            the same constructor argument of 'TableOfContents'.

        """
        super(SectionContainer, self).__init__(parent, content, **kwargs)
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
            self._toc = TableOfContents(parent, self, title=_("Index:"),
                                        depth=toc_depth)
        else:
            self._toc = Content(parent)

    def sections(self):
        return self._sections
    
    def _export_content(self, concat="\n"):
        return concat.join([p.export() for p in (self._toc,) + self._content])
    
    
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
    
    def __init__(self, parent, title, content, anchor=None, toc_depth=0,
                 in_toc=True, **kwargs):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
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
        assert isinstance(title, types.StringTypes)
        assert isinstance(anchor, types.StringTypes) or anchor is None
        assert isinstance(in_toc, types.BooleanType)
        self._title = title
        self._in_toc = in_toc
        self._anchor = anchor
        self._backref_used = False
        super(Section, self).__init__(parent, content, toc_depth=toc_depth,
                                      **kwargs)
        

    def _section_path(self):
        return [c for c in self._container_path() if isinstance(c, Section)]
    
    def section_number(self):
        """Return the number of this section within it's container as int."""
        return list(self._container.sections()).index(self) + 1
    
    def title(self):
        """Return the section title as a string."""
        title = self._title
        if self._container is not None and title.find("%d") != -1:
            title = title % self.section_number()
        return title

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
        if node is self._parent and not self._backref_used:
            self._backref_used = True
            return self._backref()
        else:
            return None
    
    def _backref(self):
        return "backref-" + self.anchor()
        
    def url(self, relative=False):
        """Return the URL of the section relative to the course root."""
        if relative:
            base = ''
        else:
            base = self._parent.url()
        return base + "#" + self.anchor()
    
    def _header(self):
        if self._backref_used:
            href = "#"+self._backref()
        else:
            href = None
        return _html.h(_html.link(self.title(), href, cls='backref',
                                  name=self.anchor()),
                 len(self._section_path()) + 1)+'\n'
               
    def export(self):
        return "\n".join((self._header(), super(Section, self).export()))

    
class TableOfContents(Content):
    """A contained Table of Contents."""
    
    def __init__(self, parent, item=None, title=None, depth=1, detailed=True):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          item -- the place where to start in the content hierarchy tree.
            'ContentNode' or 'Content' instances are allowed.  None means that
            container should be used (a local Table of Contents).  See
            'Section' documentation for more information how the content tree
            is built.
          title -- the title of the TOC as a string.
          depth -- how deep in the hierarchy should we go.
          detailed -- A True (default) value means that the 'Content' hierarchy
            within the leave nodes of the node tree will be included in the
            TOC.  False means to consider only 'ContentNode' hierarchy.

        """
        super(TableOfContents, self).__init__(parent)
        assert isinstance(item, (ContentNode, Content)) or \
               is_sequence_of(item, Content) or item is None
        assert title is None or isinstance(title, types.StringTypes)
        assert isinstance(depth, types.IntType)
        assert isinstance(detailed, types.BooleanType)
        self._item = item
        self._title = title
        self._depth = depth
        self._detailed = detailed
                      
    def _export_title(self):
        return _html.strong(self._title)
        
    def export(self):
        item = self._item
        if not item:
            if isinstance(self._container, SectionContainer):
                item = self._container
            else:
                item = self._parent
        toc = self._make_toc(item, depth=self._depth)
        if self._title is not None:
            #TODO: add a "skip" link.
            return _html.div((self._export_title(), toc),
                             cls="table-of-contents")
        else:
            return toc
        
    def _make_toc(self, item, indent=0, depth=1):
        if depth <= 0:
            return ''
        items = ()
        if isinstance(item, ContentNode):
            items = [node for node in item.children() if not node.hidden()]
        if len(items) == 0 and self._detailed:
            if isinstance(item, (types.ListType, types.TupleType)):
                items = item
            else:
                items = [s for s in item.sections() if s.in_toc()]
        if len(items) == 0:
            return ''
        links = []
        for i in items:
            url = i.url()
            name = None
            if isinstance(i, Section):
                if i.parent() is self.parent():
                    url = i.url(relative=True)
                name = i.backref(self._parent)
            links.append(_html.link(i.title(), url, name=name) + \
                         self._make_toc(i, indent=indent+4, depth=depth-1))
        return "\n" + _html.list(links, indent=indent) + "\n" + ' '*(indent-2)

    
    
class VocabItem(object):
    """One item of vocabulary listing."""

    ATTR_EXTENDED = 'ATTR_EXTENDED'
    """Special attribute indicating an extended vocabulary item."""
    ATTR_PHRASE = 'ATTR_PHRASE'
    """Special attribute indicating a phrase."""
    
    def __init__(self, parent, word, note, translation, translation_language,
                 attr=None):
        """Initialize the instance.
        
        Arguments:
          word -- the actual piece of vocabulary as a string
          note -- notes in round brackets as a string.  Can contain multiple
            notes in brackets separated by spaces.  Typical notes are for
            example (v) for verb etc.
          translation -- the translation of the word into target language.
          translation_language -- the lowercase ISO 639-1 Alpha-2 language
            code.
          attr -- special attributte.  One of the classes ATTR_* constants or
            None.
          
        """
        assert isinstance(word, types.UnicodeType)
        assert isinstance(note, types.UnicodeType) or note is None
        assert isinstance(translation, types.UnicodeType)
        assert isinstance(translation_language, types.StringTypes) and \
               len(translation_language) == 2
        assert attr in (None, self.ATTR_EXTENDED, self.ATTR_PHRASE)
        self._word = word
        self._note = note
        self._translation = translation
        self._translation_language = translation_language
        self._attr = attr
        filename = "item-%02d.mp3" % parent.counter(self.__class__).next()
        path = os.path.join('vocabulary', filename)
        self._media = parent.resource(Media, path)

    def word(self):
        return self._word

    def note(self):
        return self._note

    def media(self):
        return self._media

    def translation(self):
        return self._translation

    def translation_language(self):
        return self._translation_language

    def attr(self):
        return self._attr

        
class VocabList(Content):
    """Vocabulary listing consisting of multiple 'VocabItem' instances."""

    
    def __init__(self, parent, items, reverse=False):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          items -- sequence of 'VocabItem' instances.
          reverse -- a boolean flag indicating, that the word pairs should be
            printed in reversed order - translation first.

        """
        super(VocabList, self).__init__(parent)
        assert is_sequence_of(items, VocabItem)
        assert isinstance(reverse, types.BooleanType)
        self._items = items
        self._reverse = reverse
        parent.resource(Script, 'audio.js')

    def export(self):
        pairs = [(_html.speaking_text(i.word(), i.media()) +
                  (i.note() and " "+i.note() or ""),
                  _html.span(i.translation() or "???",
                             lang=i.translation_language()))
                 for i in self._items]
        if self._reverse:
            pairs = [(b, a) for a,b in pairs]
        t = ['<table class="vocab-list" title="%s" summary="%s">' % \
             (_("Vocabulary Listing"),
              _("The vocabulary is presented in a two-column table with a "
                "term on the left and its translation on the right in each "
                "row."))] + \
            ['<tr><td scope="row">%s</td><td>%s</td></tr>' % pair
             for pair in pairs] + \
            ["</table>"]
        return '\n'.join(t) + '\n'

    
class VocabSection(Section):
    """Section of vocabulary listing.

    The section is automatically split into two subsections -- the Vocabulary
    and the Phrases.

    """
    def __init__(self, parent, title, items, reverse=False):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          title -- The title of the section.
          items -- sequence of 'VocabItem' instances.
          reverse -- see the same constructor argument for `VocabList'.

        """
        assert isinstance(title, types.StringTypes)
        assert is_sequence_of(items, VocabItem)
        assert isinstance(reverse, types.BooleanType)
        subsections = [(t, i) for t, i in self._subsections(items) if i]
        if len(subsections) > 1:
            c = [Section(parent, t, VocabList(parent, i, reverse=reverse))
                 for t, i in subsections]
        else:
            c = VocabList(parent, subsections[0][1])
        super(VocabSection, self).__init__(parent, title, c)

    def _subsections(self, items):
        return ((_("Terms"),
                 [x for x in items if x.attr() is None]),
                (_("Phrases"),
                 [x for x in items if x.attr() is VocabItem.ATTR_PHRASE]),
                (_("Extended vocabulary"),
                 [x for x in items if x.attr() is VocabItem.ATTR_EXTENDED]))
    
        
class VocabIndexSection(VocabSection):
    def _subsections(self, items):
        return ((_("Terms"),
                 [x for x in items if x.attr() is not VocabItem.ATTR_PHRASE]),
                (_("Phrases"),
                 [x for x in items if x.attr() is VocabItem.ATTR_PHRASE]))

    
