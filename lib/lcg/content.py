# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007, 2008 Brailcom, o.p.s.
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
elements of a structured document, such as sections, paragraphs, lists, tables
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
        
    def sections(self, context):
        """Return the contained sections as a sequence of 'Section' instances.

        This method allows creation of tables of contents and introspection of
        content hierarchy.
        
        An empty sequence is returned in the base class.  The derived classes,
        however, can override this method to return the sequence of contained
        subsections.

        """
        return ()
        
    def set_container(self, container):
        """Set the parent 'Container' to 'container'.

        This method is normally called automatically by the container constructor to inform the
        contained 'Content' elements about their position in content hierarchy.  You only need to
        care about calling this method if you implement your own 'Container' class and don't call
        the default constructor for all the contained elements for some reason.

        """
        if __debug__:
            cls = self._ALLOWED_CONTAINER or Container
            assert isinstance(container, cls), "Not a '%s' instance: %s" % (cls.__name__,container)
        self._container = container

    def set_parent(self, node):
        """Set the parent 'ContentNode' to 'node'.

        This method is called automatically by the 'ContentNode' constructor when the content is
        assigned to a node.  The parent node is normally not known (and not needed) in the time of
        content construction.  It is, however, needed in the export time, so you will need to call
        it manually before attempting to export any content which was not assigned to a
        'ContentNode' before.  Content which is contained within a container will automatically
        determine its parent node recursively so it is only needed to set the parent of top level
        elements.

        """
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
        """???"""
        return self._lang or self._container and self._container.lang()

    def export(self, context):
        """Return the formatted content in an output specific form.

        The return value can later be processed by 'Exporter' methods.

        Arguments:

          context -- formatting context as a 'Exporter.Context' instance
            created and returned by 'Exporter.context' method

        """
        g = context.generator()
        return g.escape('')

    
class HorizontalSeparator(Content):
    """Horizontal separator of document section.

    Typically it may be a page separator in paged documents or a horizontal
    separator in documents without pages.

    """
    
    def export(self, context):
        return context.generator().hr()
        

class TextContent(Content):
    """A simple piece of text."""

    def __init__(self, text, **kwargs):
        """Initialize the instance.

        Arguments:

          text -- the actual text content of this element as a string or
            unicode
          kwargs -- keyword arguments for parent class constructor.

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

    def export(self, context):
        g = context.generator()
        return g.escape(self._text)

    
class FormattedText(TextContent):
    """Formatted text using a simple wiki-based markup.

    See 'MarkupFormatter' for more information about the formatting rules.
    
    """
    def export(self, context):
        if self._text:
            result = context.formatter().format(context, context.translate(self._text))
        else:
            result = context.generator().escape('')
        return result

# Backwards compatibility alias.        
WikiText = FormattedText

    
class PreformattedText(TextContent):
    """Preformatted text."""
    
    def export(self, context):
        g = context.generator()
        return g.pre(self._text)


class Anchor(TextContent):
    """Target of a link (an anchor)."""
    
    def __init__(self, anchor, text=''):
        """Arguments:

          anchor -- name of the target place as a string
          text -- text of the target place as a string or unicode

        """
        assert isinstance(anchor, str)
        self._anchor = anchor
        super(Anchor, self).__init__(text)

    def anchor(self):
        """Return link target place name given in the constructor."""
        return self._anchor
        
    def export(self, context):
        g = context.generator()
        return g.anchor(g.escape(self._text), self.anchor())


class InlineImage(Content):
    """Image put inside the document.

    It is unspecified whether the image is floating or to be put directly into
    the place of invocation.

    """
    
    LEFT = 'left'
    RIGHT = 'right'
    
    def __init__(self, image, align=None, title=None, name=None):
        """Arguments:

          image -- 'Image' instance
          align -- requested alignment of the image to the surrounding text;
            one of the constants 'InlineImage.LEFT', 'InlineImage.RIGHT' or
            'None'
          title -- title of the image (or alternative text in some output
            formats) as a string or unicode; if not given 'image' title (if
            present) is used
          name -- ???

        """
        assert isinstance(image, Image), image
        assert align in (None, self.LEFT, self.RIGHT), align
        assert title is None or isinstance(title, (str, unicode)), title
        assert name is None or isinstance(name, (str, unicode)), name
        self._image = image
        self._align = align
        self._title = title
        self._name = name
        super(InlineImage, self).__init__()

    def export(self, context):
        g = context.generator()
        img = self._image
        return g.img(context.uri(img), alt=self._title or img.title() or '', descr=img.descr(),
                     align=self._align, cls=self._name, width=img.width(), height=img.height())


class Container(Content):
    """Container of multiple parts, each of which is a 'Content' instance.

    Containers allow to build a hierarchy of 'Content' instances inside the
    scope of one node.  This is an addition to the hierarchy of the actual
    nodes (separate pages).

    All the contained (wrapped) content elements will be notified about the
    fact, that they are contained within this container and thus belong to the
    hierarchy.

    """
    _ALLOWED_CONTENT = Content
    _SUBSEQUENCES = False
    _SUBSEQUENCE_LENGTH = None
    
    def __init__(self, content, **kwargs):
        """Initialize the instance.

        Arguments:
        
          content -- the actual content wrapped into this container as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.

        """
        super(Container, self).__init__(**kwargs)
        if self._SUBSEQUENCES:
            assert isinstance(content, (list, tuple)), "Not a sequence: %s" % content
            self._content = tuple([tuple(subseq) for subseq in content])
            for subseq in content:
                assert isinstance(subseq, (list, tuple)), "Not a sequence: %s" % subseq
                if self._SUBSEQUENCE_LENGTH is not None:
                    assert len(subseq) == self._SUBSEQUENCE_LENGTH
                for c in subseq:
                    assert isinstance(c, self._ALLOWED_CONTENT), \
                           "Not a '%s' instance: %s" % (self._ALLOWED_CONTENT, c)
                    c.set_container(self)
        elif isinstance(content, (list, tuple)):
            assert is_sequence_of(content, self._ALLOWED_CONTENT), \
                   "Not a '%s' instances sequence: %s" % (self._ALLOWED_CONTENT, content)
            self._content = tuple(content)
            for c in content:
                c.set_container(self)
        else:
            assert isinstance(content, self._ALLOWED_CONTENT), \
                   "Not a '%s' instance: %s" % (self._ALLOWED_CONTENT, content)
            self._content = (content,)
            content.set_container(self)
            
    def content(self):
        """Return content nodes given in the constructor."""
        return self._content
            
    def _exported_content(self, context):
        if self._SUBSEQUENCES:
            return [[c.export(context) for c in seq] for seq in self._content]
        else:
            return [c.export(context) for c in self._content]

    def export(self, context):
        g = context.generator()
        exported = self._exported_content(context)
        result = g.concat(*exported)
        if self._lang is not None:
            result = g.div(result, lang=self._lang)
        return result


class Paragraph(Container):
    """A paragraph of text, where the text can be any 'Content'."""

    def export(self, context):
        g = context.generator()
        exported = self._exported_content(context)
        exported_result = g.concat(*exported)
        return g.p(exported_result, lang=self._lang)

    
class ItemizedList(Container):
    """An itemized list."""

    TYPE_UNORDERED = 'UNORDERED'
    TYPE_ALPHA = 'ALPHA'
    TYPE_NUMERIC = 'NUMERIC'
    
    def __init__(self, content, type=TYPE_UNORDERED, **kwargs):
        """Arguments:
        
          content -- sequence of list items containing exported contents
          type -- one of the class 'TYPE_' constants determining the list style
          
        """
        assert type in (self.TYPE_UNORDERED,
                        self.TYPE_ALPHA,
                        self.TYPE_NUMERIC)
        self._type = type
        super(ItemizedList, self).__init__(content, **kwargs)

    def _styles(self):
        return {self.TYPE_UNORDERED: (False, None),
                self.TYPE_NUMERIC: (True, None),
                self.TYPE_ALPHA: (True, 'lower-alpha'),
                }

    def export(self, context):
        ordered, style = self._styles()[self._type]
        items = self._exported_content(context)
        return context.generator().list(items, ordered=ordered, style=style, lang=self._lang)


class DefinitionList(Container):
    """A list of definitions.

    The constructor accepts a sequence of definitions, where each definition is a pair '(TERM,
    DESCRIPTION)', where both items are 'Content' instances.
    
    """
    _SUBSEQUENCES = True
    _SUBSEQUENCE_LENGTH = 2

    def export(self, context):
        return context.generator().definitions(self._exported_content(context), lang=self._lang)

    
class FieldSet(Container):
    """A list of label and value pairs.

    The constructor accepts a sequence of '(LABEL, VALUE)' pairs, where both
    items are 'Content' instances.  Logically similar to 'DefinitionList', but
    more suitable for an enumeration of shorter fields presented side by side
    (while definition description usually follows on another line below the
    term).

    """
    _SUBSEQUENCES = True
    _SUBSEQUENCE_LENGTH = 2

    def export(self, context):
        return context.generator().fset(self._exported_content(context), lang=self._lang)
    
        
class Table(Container):
    """Table of rows and cells.

    The constructor accepts a sequence of sequences.  Each outer sequence represents one table row,
    the inner sequences consist of a 'Content' instance for each cell.

    """
    _SUBSEQUENCES = True

    def __init__(self, content, title=None, **kwargs):
        """Arguments:

          content -- sequence (rows items) of sequences (cell items)
          title -- 'None' or table caption as a string or unicode

        """
        assert title is None or isinstance(title, (str, unicode))
        self._title = title
        super(Table, self).__init__(content, **kwargs)
        
    def export(self, context):
        return context.generator().gtable(self._exported_content(context),
                                          title=self._title, lang=self._lang)


class SectionContainer(Container):
    """A 'Container' which recognizes contained sections.

    'SectionContainer' acts as a 'Container', but for any contained 'Section'
    instances, a local 'TableOfContents' can be created automatically,
    preceding the actual content (depending on the 'toc_depth' constructor
    argument).  The contained sections are also returned by the 'sections()'
    method to allow building a global `TableOfContents'.

    """
    def __init__(self, content, toc_depth=None, **kwargs):
        """Arguments:

          content -- same as in the parent class
          toc_depth -- the depth of local table of contents; see 'depth' argument
            of 'TableOfContents' constructor

        """
        self._toc_depth = toc_depth
        super(SectionContainer, self).__init__(content, **kwargs)

    def sections(self, context):
        """Return content elements which are 'Section' instances."""
        return [c for c in self._content if isinstance(c, Section)]
    
    def _exported_content(self, context):
        result = super(SectionContainer, self)._exported_content(context)
        toc_sections = []
        for c in self._content:
            if isinstance(c, TableOfContents) and not toc_sections:
                return result
            if isinstance(c, Section) and c.in_toc():
                toc_sections.append(c)
        if (self._toc_depth is None or self._toc_depth > 0) and \
               (len(toc_sections) > 1 or len(toc_sections) == 1 and 
                len([s for s in toc_sections[0].sections(context) if s.in_toc()])):
            toc = TableOfContents(self, _("Index:"), depth=self._toc_depth)
            toc.set_container(self)
            toc.set_parent(self.parent())
            result = [toc.export(context)] + result
        return result
    
    
class Section(SectionContainer):
    """Section wraps the subordinary contents into an inline section.

    Section is very similar to a 'SectionContainer', but there are a few
    differences:

      * Every section has a title, which appears in the output document as a
        heading.

      * Link targets are attached to sections.

      * Sections are numbered.  Each section knows its number within its
        container.
    
    """
    _ANCHOR_PREFIX = 'sec'
    
    def __init__(self, title, content, anchor=None, toc_depth=0,
                 in_toc=True, **kwargs):
        """Arguments:

          title -- section title as a string
          content -- the actual content wrapped into this section as a
            sequence of 'Content' instances in the order in which they should
            appear in the output
          anchor -- section link target name as a string.  If 'None' (default)
            the link target name will be generated automatically.  If you want
            to refer to a section explicitly from somewhere, you will probably
            not rely on the default anchor name, so that's how you can define
            your own.  This also allows you to find a section by its anchor
            name in the hierarchy (see 'ContentNode.find_section()').
          toc_depth -- the depth of the local Table of Contents (see
            'SectionContainer')
          in_toc -- a boolean flag indicating whether this section is supposed
            to be included in the Table of Contents
            
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
        """Return the number of this section within its container as int."""
        return list(self._container.sections(None)).index(self) + 1
    
    def title(self):
        """Return the section title as a string."""
        return self._title

    def in_toc(self):
        """Return true if the section is supposed to appear in TOC."""
        return self._in_toc
    
    def anchor(self):
        """Return the link target name of this section."""
        if self._anchor is None:
            numbers = [str(x.section_number()) for x in self._section_path()]
            self._anchor = self._ANCHOR_PREFIX + '.'.join(numbers)
        return self._anchor
        
    def backref(self, node):
        """???"""
        # We can allow just one backref target on the page.  Links on other
        # pages are not backreferenced.
        if node is self.parent() and not self._backref_used and config.allow_backref:
            self._backref_used = True
            return self._backref()
        else:
            return None
    
    def _backref(self):
        return "backref-" + self.anchor()
        
    def _export_heading(self, context):
        # This method may be used in derived classes (currently in Eurochance exercises).
        g = context.generator()
        level = len(self._section_path()) + 1
        backref = self._backref_used and self._backref() or None
        return g.heading(self.title(), level, anchor=self.anchor(), backref=backref)
    
    def export(self, context):
        g = context.generator()
        exported = g.concat(self._export_heading(context),
                            super(Section, self).export(context))
        return g.div(exported, id='section-' + self.anchor())


class NodeIndex(Content):
    """A Table of Contents which lists the node subtree of the current node."""

    def __init__(self, title=None, node=None, depth=None, detailed=False):
        """Arguments:

          title -- the title of the index as a string or unicode
          node -- the top level node to place the index in; if 'None', the
            parent node of the node is used
          depth -- hierarchy depth limit as an integer or 'None' for unlimited depth
          detailed -- boolean indicating whether the whole 'Content' hierarchy
            ('True') or only 'ContentNode' hierarchy ('False') of the leaf
            nodes of the node tree will be included in the index

        """
        super(NodeIndex, self).__init__()
        assert title is None or isinstance(title, (str, unicode))
        assert node is None or isinstance(node, ContentNode)
        assert depth is None or isinstance(depth, int)
        assert isinstance(detailed, bool)
        self._title = title
        self._node = node
        self._depth = depth
        self._detailed = detailed
                      
    def _start_item(self):
        return self._node or self.parent()
        
    def export(self, context):
        toc = self._make_toc(context, self._start_item(), depth=self._depth)
        if self._title is not None:
            #TODO: add a "skip" link?
            g = context.generator()
            return g.div(g.concat(g.div(g.strong(self._title), cls='title'), toc), cls='table-of-contents')
        else:
            return toc
        
    def _make_toc(self, context, item, indent=0, depth=1):
        g = context.generator()
        if depth is not None:
            if depth <= 0:
                return g.escape('')
            depth -= 1 # Decrease for further calls.
        items = ()
        if isinstance(item, ContentNode):
            items = [node for node in item.children() if not node.hidden()]
        if len(items) == 0 and self._detailed:
            if isinstance(item, (tuple, list)):
                items = item
            else:
                items = [s for s in item.sections(context) if s.in_toc()]
        if len(items) == 0:
            return g.escape('')
        links = []
        parent = current = self.parent()
        while current is not None and current.hidden():
            current = current.parent()
        for i in items:
            name = None
            uri_kwargs = {}
            descr = None
            cls = i is current and 'current' or None
            if isinstance(i, ContentNode):
                descr = i.descr()
                if not i.active():
                    cls = (cls and cls + ' ' or '') + 'inactive'
            elif isinstance(i, Section):
                name = i.backref(parent)
                uri_kwargs['local'] = parent is i.parent()
            uri = context.uri(i, **uri_kwargs)
            if isinstance(g, HtmlGenerator):
                # Wrapping <a href=...><a name=...>...</a></a> is invalid in HTML!
                current_link = g.link(i.title(), uri, name=name, title=descr, cls=cls)
            else:
                if name is None:
                    current_anchor = i.title()
                else:
                    current_anchor = g.anchor(i.title(), name)
                current_link = g.link(current_anchor, uri, title=descr, cls=cls)
            subtoc = self._make_toc(context, i, indent=indent+4, depth=depth)
            links.append(g.concat(current_link, subtoc))
        if isinstance(g, HtmlGenerator):
            result = concat("\n", g.list(links, indent=indent), ' '*(indent-2))
        else:
            result = g.list(links)
        return result


class RootIndex(NodeIndex):
    """ ??? """
    
    def _start_item(self):
        return self.parent().root()

    
class TableOfContents(NodeIndex):
    """A Table of Contents which lists the content subtree.

    ??? I don't understand this class. ???

    """
    
    def __init__(self, start=None, title=None, depth=None):
        """Arguments:
        
          item -- the place where to start in the content hierarchy tree as a 'Content' instance.
            None means to start at the container (a local Table of Contents).  See 'Section'
            documentation for more information how the content tree is built.
            
          All other arguments have the same meaning as in the parent class constructor.
        
        """
        assert isinstance(start, Content) or start is None
        self._start_item_ = start
        super(TableOfContents, self).__init__(title=title, detailed=True, depth=depth)
        
    def _start_item(self):
        start_item = self._start_item_
        if not start_item:
            assert isinstance(self._container, SectionContainer)
            start_item = self._container
        return start_item
    

class Link(Container):
    """Link to internal or external location."""
    
    class ExternalTarget(object):
        """Representation of an external target specified by its URI."""
        def __init__(self, uri, title, descr=None):
            """Arguments:

              uri -- URI of the link target as a string
              title -- title of the target as a string or unicode
              descr -- ???
              
            """
            self._uri = uri
            self._title = title
            self._descr = descr
        def uri(self):
            return self._uri
        def title(self):
            return self._title
        def descr(self):
            return self._descr
    
    def __init__(self, target, label=None, descr=None, type=None):
        """Arguments:

          target -- target of the link, it may be either a 'Section' instance
            or a 'ContentNode' instance, a 'Link.ExternalTarget' instance or a
            'Resource' instance
          label -- label of the link
          descr -- ???
          type -- ???
        
        """
        assert isinstance(target, (Section, ContentNode, self.ExternalTarget, Resource)), target
                                   #unicode, str)), target
        assert label is None or isinstance(label, (str, unicode, InlineImage)), label
        assert descr is None or isinstance(descr, (str, unicode)), descr
        assert type is None or isinstance(type, (str, unicode)), type
        if label is None:
            label = target.title()
        if isinstance(label, (str, unicode)):
            content = (TextContent(label),)
        else:
            content = (label)
        self._target = target
        self._descr = descr
        self._type = type
        super(Link, self).__init__(content)

    def export(self, context):
        g = context.generator()
        target = self._target
        #if isinstance(target, (str, unicode)):
        #    target = self.parent().find_section(target, context)
        if self._descr is not None:
            descr = self._descr
        elif isinstance(target, (ContentNode, self.ExternalTarget, Resource)):
            descr = target.descr()
        elif target.parent() is not self.parent():
            descr = g.concat(g.escape(target.title()), g.escape(' (%s)' % (target.parent().title(),)))
        else:
            descr = None
        label = g.concat(*self._exported_content(context))
        uri = context.uri(target)
        return g.link(label, uri, title=descr, type=self._type)


class Title(Content):
    """Inline element, which is substituted by the title of the requested item in export time.

    It may not be possible to find out what is the title of the current node or some other element
    in the time of content construction.  So this symbolic element may be used to refer to the item
    an it will be simply replaced by the title text in export time.

    The constructor argument 'id' may be used to refer to the required item.  It may be a section
    id in the current page or an identifier of another node.  The default value (None) refers to
    the title of the current node.  If the item refered by id can not be found, the id itself is
    used for substitution.

    """
    def __init__(self, id=None):
        """Arguments:

          id -- reference to the item providing the required title; it may be a
            section id (??? what is it ???) in the current page or an
            identifier of another node (??? what is it ???).  'None' refers to
            the title of the current node.  If the item refered by 'id' cannot
            be found, the id itself is used for substitution.

        """
        super(Title, self).__init__()
        self._id = id
        
    def export(self, context):
        g = context.generator()
        parent = self.parent()
        if self._id is None:
            item = parent
        else:
            item = parent.find_section(self._id, context)
            if not item:
                item = parent.root().find_node(self._id)
            if not item:
                return self._id
        return g.escape(item.title())


class NoneContent(Content):
    """Empty content.

    Useful in places where 'Content' is required but there is nothing to put
    in.
    
    """
    
    def export(self, context):
        g = context.generator()
        return g.escape('')


class ContentVariants(Container):
    """Container of multiple language variants of the same content.

    This implements one of two LCG methods for creating multilingual documents.  The second method
    uses 'TranslatableText' within the content and is mostly useful for content, which has
    identical structure in all language variants, only the user visible texts are translated.
    'ContentVariants', on the other hand, allows you to include a completely arbitrary subcontent
    for each language within one document.  Only the relevant variant is used in export time (when
    the target language is already known).

    """
    def __init__(self, variants):
        """Arguments:
        
          variants -- a sequence of pairs '(LANG, CONTENT)', where 'LANG' is an
            ISO 639-1 Alpha-2 language code and 'CONTENT' is the actual content
            variant for this language as a 'Content' instance or a sequence of
            'Content' instances
            
        """
        self._variants = {}
        for lang, content in variants:
            if isinstance(content, (list, tuple)): 
                content = SectionContainer(content)
            self._variants[lang] = content
        super(ContentVariants, self).__init__(self._variants.values())

    def sections(self, context):
        return self._variants[context.lang()].sections(context)
        
    def export(self, context):
        return self._variants[context.lang()].export(context)
    
    
# Convenience functions for simple content construction.

def coerce(content, formatted=False):
    """Coerce the argument into an LCG content element.

    Arguments:

      content -- can be a sequence, string or a Content instance.  A sequence is turned to a
        'Container' of the items.  Moreover each item is coerced recursively and 'None' items are
        omitted.  A string is turned into a 'TextContent' or 'FormattedText' instance according to
        the 'formatted' argument.  A 'Content' instance is returned as is.  Any other argument
        raises AssertionError.
        
      formatted -- a boolean flag indicating that strings should be treated as formatted, so
        'FormattedText' is used instead of plain 'TextContent'.  Applies recursively if a sequence
        is passed as the 'content' argument.

    """
    assert isinstance(formatted, bool)
    if isinstance(content, (list, tuple)):
        container = Container
        items = []
        for item in content:
            if item is not None:
                if isinstance(item, Section):
                    container = SectionContainer
                elif not isinstance(item, Content):
                    item = coerce(item, formatted=formatted)
                items.append(item)
        return container(items)
    elif isinstance(content, (str, unicode)):
        if formatted:
            return FormattedText(content)
        else:
            return TextContent(content)
    else:
        assert isinstance(content, Content), ('Invalid content', content,)
        return content

def link(target, label=None, type=None, descr=None):
    """Return a 'Link' instance.

    Arguments:

      target -- link target.  It can be a direct URI as a string or unicode
        instance or any referable content element, such as 'Section',
        'ContentNode', 'Resource' or 'Link.ExternalTarget'.
      label -- link labe is mandatory when the target is a direct URI (string
        or unicode) and optional for LCG content element targets.  In this case
        it just overrides the default title of the refered object.
      type -- mime type specification of the refered object.
      descr -- additional description of the link target.  Only applicable when
        the link target is a direct URI.

    """
    assert isinstance(target, (str, unicode, ContentNode, Section,
                               Link.ExternalTarget, Resource)), target
    if isinstance(target, (str, unicode)):
        assert label is not None
        target = Link.ExternalTarget(target, label, descr=descr)
        label = None
    else:
        assert descr is None
    return Link(target, label=label, type=type)
    
def dl(items, formatted=False):
    """Create a 'DefinitionList' from a sequence of (TERM, DESCRIPTION) pairs.

    Each term and description in the sequence is automatically coerced into a content instance, but
    only the description is treated as formatted.

    """
    return DefinitionList([(coerce(term), coerce(descr, formatted=formatted))
                           for term, descr in items])

def ul(items, formatted=False):
    """Create an 'ItemizedList' by coercing given sequence of items."""
    return ItemizedList([coerce(item, formatted=formatted) for item in items])

def ol(items, formatted=False, alpha=False):
    """Create an 'ItemizedList' by coercing given sequence of items."""
    return ItemizedList([coerce(item, formatted=formatted) for item in items],
                        type=(alpha and ItemizedList.TYPE_ALPHA or ItemizedList.TYPE_NUMERIC))

def fieldset(pairs, title=None, formatted=False):
    """Create a 'FieldSet' out of given sequence of (LABEL, VALUE) pairs.

    Both label and value are coerced, but only value is treated as formatted.
    
    """
    fields = [(coerce(label), coerce(value, formatted=formatted)) for label, value in pairs]
    return FieldSet(fields, title=title)

def p(*items, **kwargs):
    """Create a 'Paragraph' by coercing all arguments."""
    return Paragraph([coerce(item, **kwargs) for item in items])

def join(items, separator=' '):
    """Coerce all items and put the coerced separator in between them."""
    sep = coerce(separator)
    result = []
    for item in items:
        if result:
            result.append(sep)
        result.append(coerce(item))
    return coerce(result)
