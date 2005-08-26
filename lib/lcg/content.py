# -*- coding: iso8859-2 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005 Brailcom, o.p.s.
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

This module provides classes for representation of content elements in an
abstract container capable of HTML export.

"""

import string
import re
import types
import unicodedata
import textwrap
import random

from lcg import *
from _html import *


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
        assert isinstance(container, Container), \
               "Not a 'Container' instance: %s" % container
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
        assert isinstance(text, types.StringTypes)
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
        return wiki.Formatter(self._parent).format(self._text)

    
class PreformattedText(TextContent):
    """Preformatted text."""

    def export(self):
        from xml.sax import saxutils
        text = saxutils.escape(self._text)
        return '<pre class="lcg-preformatted-text">'+text+'</pre>'

    
class Anchor(TextContent):
    """An anchor (target of a link)."""
    def __init__(self, parent, anchor, text=''):
        assert isinstance(anchor, types.StringType)
        self._anchor = anchor
        super(Anchor, self).__init__(parent, text)
        
    def export(self):
        return link(self._text, None, name=self._anchor)

    
class Link(TextContent):
    """An anchor (target of a link)."""
    def __init__(self, parent, target, text=''):
        assert isinstance(target, Section)
        self._target = target
        super(Link, self).__init__(parent, text)
        
    def export(self):
        t = self._target
        return link(self._text or t.title(), t.url())

    
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
    _CLASS = None
    _EXPORT_INLINE = False
    
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
        if operator.isSequenceType(content):
            assert is_sequence_of(content, Content), \
                   "Not a 'Content' instances sequence: %s" % (content,)
            self._content = tuple(content)
        else:
            assert isinstance(content, Content)
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
        return itemize(items, ordered=o, style=s, lang=self._lang)

    
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
    
    def __init__(self, parent, content):
        assert is_sequence_of(content, Definition)
        super(DefinitionList, self).__init__(parent, content)


class Field(Container):
    """A pair of label and a value for a FieldSet."""
    
    def __init__(self, parent, label, value):
        super(Field, self).__init__(parent, (label, value))

    def export(self):
        f = '<tr><th align="left" valign="top">%s:</th><td>%s</td></tr>\n'
        return f % tuple([c.export() for c in self._content])

    
class FieldSet(Container):
    """A list of label, value pairs (fields)."""
    _TAG = 'table'
    _CLASS = 'lcg-fieldset'
    
    def __init__(self, parent, content):
        assert is_sequence_of(content, Field)
        super(FieldSet, self).__init__(parent, content)

    
class TableCell(Container):
    """One cell in a table."""
    _TAG = 'td'
    _EXPORT_INLINE = True

    
class TableRow(Container):
    """One row in a table."""
    _TAG = 'tr'

    def __init__(self, parent, content, **kwargs):
        assert is_sequence_of(content, TableCell)
        super(TableRow, self).__init__(parent, content, **kwargs)
        
        
class Table(Container):
    """One row in a table."""
    _TAG = 'table'
    _CLASS = 'lcg-table'

    def __init__(self, parent, content):
        assert is_sequence_of(content, TableRow)
        super(Table, self).__init__(parent, content)
    
    
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
        self._sections = [s for s in self._content if isinstance(s, Section)]
        toc_sections = [s for s in self._sections if s.in_toc()]
        if toc_depth > 0 and \
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
        return self._container.sections().index(self) + 1
    
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
            return '-'.join([self._ANCHOR_PREFIX] + numbers)
        
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
        return h(link(self.title(), href, cls='backref', name=self.anchor()),
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
                      
        
    def export(self):
        item = self._item
        if not item:
            if isinstance(self._container, SectionContainer):
                item = self._container
            else:
                item = self._parent
        toc = self._make_toc(item, depth=self._depth)
        if self._title is not None:
            return div((b(self._title), toc), cls="table-of-contents")
        else:
            return toc
        
    def _make_toc(self, item, indent=0, depth=1):
        if depth <= 0:
            return ''
        items = ()
        if isinstance(item, ContentNode):
            items = item.children()
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
            links.append(link(i.title(), url, name=name) + \
                         self._make_toc(i, indent=indent+4, depth=depth-1))
        return "\n" + itemize(links, indent=indent) + "\n" + ' '*(indent-2)

    
    
class VocabItem(object):
    """One item of vocabulary listing."""
    _DIACRITICS_MATCHER = re.compile(r" WITH .*")
    _DANGER_CHAR_MATCHER = re.compile(r"[^a-zA-Z0-9-]")
    
    def __init__(self, parent, word, note, translation,
                 translation_language, is_phrase=False):
        """Initialize the instance.
        
        Arguments:
          word -- The actual piece of vocabulary as a string
          note -- Notes in round brackets as a string.  Can contain multiple
            notes in brackets separated by spaces.  Typical notes are for
            example (v) for verb etc.
          translation -- the translation of the word into target language.
          translation_language -- the lowercase ISO 639-1 Alpha-2 language
            code.
          is_phrase a boolean flag indicating, that given vocabulary item is a
            phrase.
          
        """
        assert isinstance(word, types.UnicodeType)
        assert isinstance(note, types.UnicodeType) or note is None
        assert isinstance(translation, types.UnicodeType)
        assert isinstance(translation_language, types.StringTypes) and \
               len(translation_language) == 2
        assert isinstance(is_phrase, types.BooleanType)
        self._word = word
        self._note = note
        self._translation = translation
        self._translation_language = translation_language
        self._is_phrase = is_phrase
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

    def is_phrase(self):
        return self._is_phrase

        
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
        pairs = [(speaking_text(i.word(), i.media()) +
                  (i.note() and " "+i.note() or ""),
                  span(i.translation() or "???", lang=i.translation_language()))
                 for i in self._items]
        rows = ['<tr><td>%s</td><td>%s</td></tr>' %
                (self._reverse and (b,a) or (a,b)) for a,b in pairs]
        return '<table class="vocab-list">\n' + '\n'.join(rows) + "\n</table>\n"

    
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
        terms = [x for x in items if not x.is_phrase()]
        phrases = [x for x in items if x.is_phrase()]
        if phrases:
            c = [Section(parent, _("Terms"),
                         VocabList(parent, terms, reverse=reverse)),
                 Section(parent, _("Phrases"),
                         VocabList(parent, phrases, reverse=reverse))]
        else:
            c = VocabList(parent, terms, reverse=reverse)
        super(VocabSection, self).__init__(parent, title, c)

        
################################################################################
################################     Tasks     #################################
################################################################################

class Task(object):
    """This class an abstract base class for various concrete tasks.

    A set of concrete tasks is a part of each 'Exercise'.

    """

    def __init__(self, prompt, comment=None):
        assert isinstance(prompt, types.UnicodeType) or prompt is None
        assert isinstance(comment, types.UnicodeType) or comment is None
        self._comment = comment
        self._prompt = prompt

    def id(self):
        return 'task_%s' % id(self)
        
    def prompt(self):
        return self._prompt
    
    def comment(self):
        return self._comment


class Choice(object):
    """Answer text with an information whether it is correct or not.

    It is used for representation of the choices for '_ChoiceTask'.

    """
    def __init__(self, answer, correct=False):
        assert isinstance(answer, types.UnicodeType)
        assert isinstance(correct, types.BooleanType)
        self._answer = answer
        self._correct = correct

    def answer(self):
        return self._answer

    def correct(self):
        return self._correct

        
class _ChoiceTask(Task):
    """Select the correct statement out of a list of predefined choices."""
    
    def __init__(self, prompt, choices, **kwargs):
        """Initialize the instance.

        Arguments:
        
          choices -- sequence of 'Choice' instances related to this Task.
          
        """
        assert is_sequence_of(choices, Choice)
        assert len([ch for ch in choices if ch.correct()]) == 1 or not choices
        self._choices = list(choices)
        super(_ChoiceTask, self).__init__(prompt, **kwargs)

    def choices(self):
        return self._choices

    def correct_choice(self):
        for choice in self._choices:
            if choice.correct():
                return choice
        raise Exception("No correct choice found!")

    def choice_index(self, choice):
        return self._choices.index(choice)
        
        
class MultipleChoiceQuestion(_ChoiceTask):
    pass


class Selection(_ChoiceTask):
    
    def __init__(self, choices, **kwargs):
        super(Selection, self).__init__(None, choices, **kwargs)

        
class GapFillStatement(_ChoiceTask):

    _GAP_MATCHER = re.compile(r"(___+)")
    
    def __init__(self, prompt, choices, **kwargs):
        super(GapFillStatement, self).__init__(prompt, choices, **kwargs)
        matches = len(self._GAP_MATCHER.findall(prompt))
        if choices:
            assert matches == 1, \
                   "GapFillStatement must include just one gap " + \
                   "marked by three or more underscores. %d found." % matches

    def substitute_gap(self, replacement):
        return self._GAP_MATCHER.sub(replacement, self.prompt())
    

class TrueFalseStatement(_ChoiceTask):
    """The goal is to indicate whether the statement is true or false."""
    
    def __init__(self, statement, correct=True, comment=None):
        """Initialize the instance.

        Arguments:
        
          statement --  exercise within the containing section.
          correct -- boolean flag indicating whether the statement is correct
            or not (true when it is correct).
          
        """
        assert isinstance(correct, types.BooleanType)
        choices = (Choice(_('TRUE'), correct), Choice(_('FALSE'), not correct))
        super(TrueFalseStatement, self).__init__(statement, choices, comment=comment)


class FillInTask(Task):
    
    def __init__(self, prompt, answer, comment=None):
        assert isinstance(answer, types.UnicodeType)
        self._answer = answer.replace('\n', ' ')
        super(FillInTask, self).__init__(prompt, comment=comment)

    def answer(self):
        return self._answer

    def text(self, field_formatter):
        return field_formatter(self.answer(), id=self.id())

    
class DictationTask(FillInTask):
    _REGEXP = re.compile(r"(\s*/\s*|\s+)")
    
    def __init__(self, text, comment=None):
        assert isinstance(text, types.UnicodeType)
        text = self._REGEXP.sub(' ', text).strip()
        super(DictationTask, self).__init__(None, text, comment=comment)


class _ClozeTask(FillInTask):
    _FIELD_MATCHER = re.compile(r"\[([^\]]*?)(?:\<(?P<label>[\w\d]+)\>)?\]")

    def _fields(self):
        return [(answer.replace('\n', ' '), label)
                for answer, label in self._FIELD_MATCHER.findall(self._text)]
    
    def answers(self):
        return [answer for answer, label in self._fields()]
    
    def answer(self):
        answers = self.answers()
        if answers:
            assert len(answers) == 1
            return answers[0]
        else:
            return None
    
    def text(self, field_formatter, text_transform=None):
        formatter = lambda match: field_formatter(match.group(1))
        text = self._text
        if text_transform:
            text = text_transform(text)
        return self._FIELD_MATCHER.sub(formatter, text)

    def plain_text(self):
        return self._FIELD_MATCHER.sub(lambda match: match.group(1), self._text)

        
class TransformationTask(_ClozeTask):

    def __init__(self, orig, transformation, comment=None):
        if not self._FIELD_MATCHER.search(transformation):
            transformation = '[' + transformation + ']'
        self._text = transformation
        assert len(self.answers()) == 1
        answer = self.answers()[0]
        super(TransformationTask, self).__init__(orig, answer, comment=comment)

        
class ClozeTask(_ClozeTask):
        
    def __init__(self, text, comments=(), comment=None):
        self._text = text
        if comment:
            assert comments == ()
            assert len(self.answers()) == 1
            self._comments = (comment, )
        else:
            assert isinstance(comments, (types.ListType, types.TupleType))
            fields = self._fields()
            if comments:
                dict = {}
                for c in comments:
                    match = re.search("^<(?P<label>[\w\d]+)>\s*", c)
                    assert match, ('Cloze comments must begin with a label ' +
                                   '(e.g. <1> to refer to a field [xxx<1>]).',
                                   c)
                    dict[match.group('label')] = c[match.end():]
                def _comment(dict, label):
                    try:
                        c = dict[label]
                        del dict[label]
                        return c
                    except KeyError:
                        return None
                self._comments = [_comment(dict, label) for a, label in fields]
                assert not dict, ("Unused comments (labels don't match any "
                                  "field label): %s") % dict
            else:
                self._comments = [None for x in fields]
        super(ClozeTask, self).__init__(None, text, comment=comment)

    def comments(self):
        return self._comments


################################################################################
################################   Exercises   #################################
################################################################################

    
class Exercise(Section):
    """Exercise consists of an assignment and a set of tasks."""

    _ANCHOR_PREFIX = 'ex'
    _TASK_TYPE = None
    _NAME = None
    _RECORDING_REQUIRED = False
    _READING_REQUIRED = False
    _AUDIO_VERSION_REQUIRED = False
    _BUTTONS = ()
    _DISPLAYS = ()
    _INSTRUCTIONS = ""
    _AUDIO_VERSION_LABEL = _("""This exercise can be also done purely
    aurally/orally:""")
    _TASK_SEPARATOR = '<br class="task-separator"/>\n'
    _EXPORT_ORDER = None
    
    _used_types = []
    _help_node = None
    
    def __init__(self, parent, tasks, instructions=None, audio_version=None,
                 sound_file=None, transcript=None, reading=None,
                 explanation=None, example=None, template=None,
                 reading_instructions=_("Read the following text:")):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.

          tasks -- sequence of 'Task' instances related to this exercise.

          instructions -- user supplied instructions.  This is a way how to
            include more specific instructions instead of default exercise
            isnstructions (which are intentionally very general).  The given
            text will be printed before the exercise tasks and should be a
            complete sentence (usually starting with a capital letter and
            ending with a dot or a colon).  This, in consequence, also allows
            to use the same exercise type for different purposes.
            
          audio_version -- name of the file with an audio version of this
            exercise.

          sound_file -- name of the file with a recording as a string.  Some
            exercise types may require a recording, some may not.
            
          transcript -- name of the file with a textual transcript of the
            recording as a string.  The transcript file is required to exist
            whenever the 'sound_file' argument is supplied.  This argument,
            however, is not required when the transcript filename is the same
            as the 'sound_file' filename using the '.txt' extension instead of
            the original sound file extension.
            
          reading -- specifies the reading text, which is displayed at the
            begining of the exercise.  Some exercise types may require a
            reading, some may not.  If a one-line value is supplied, this is
            considered a filename.  The file is then searched within the
            `readings' subdirectory of current node's source directory.  A
            multi-line value is used as the reading text itself.  The text
            (regardless whether read from file or not) is a structured text
            using the 'wiki' formatting.

          reading_instructions -- The reading text is introduced by a brief
            label 'Read the following text:' by default.  If you want to change
            this, use this argument su supply any text.  Wiki formatting can be
            used here as-well.
            
          explanation -- any exercise can start with a brief explanation
            (usually of the subject of it's tasks).  Explanations are quite
            similar to readings texts but serve a different purpose.  When both
            are defined, the reading goes first on the output.  They are
            defined as a multi-line structured text using the 'wiki'
            formatting.
            
          example -- a model answer.  If defined, the tasks will be preceeded
            with given example (a multi-line structured text using the 'wiki'
            formatting).  The formatting should usually follow the formatting
            of the tasks within the exercise.

          template -- the tasks are rendered as a simple sequence on the
            output.  If you need something more sophisticated (e.g. have text
            and the tasks 'mixed' within it), you can use a template.  Just
            specify any stuctured text and use '%s' placehodlers to be replaced
            by the actual tasks.  Note that you must have exactly the same
            number of the placeholders within the template as the number of
            tasks you pass as the `tasks' arguemnt.  You must also double any
            '%' signs, which are not a part of a placeholder.
            
        """
        title = _("Exercise %d") +": "+ self._NAME
        super(Exercise, self).__init__(parent, title, Content(parent),
                                       in_toc=False)
        if self.__class__ not in Exercise._used_types:
            Exercise._used_types.append(self.__class__)
        assert instructions is None or \
               isinstance(instructions, types.StringTypes)
        assert isinstance(reading_instructions, types.StringTypes)
        assert is_sequence_of(tasks, self._TASK_TYPE), \
               "Tasks must be a sequence of '%s' instances!: %s" % \
               (self._TASK_TYPE.__name__, tasks)
        assert sound_file is None or isinstance(sound_file, types.StringTypes)
        if self._READING_REQUIRED:
            assert reading is not None, \
            "'%s' requires a reading!" % self.__class__.__name__
        if self._RECORDING_REQUIRED:
            assert sound_file is not None, \
            "'%s' requires a recording!" % self.__class__.__name__
        if self._AUDIO_VERSION_REQUIRED:
            assert audio_version is not None, \
            "'%s' requires an audio version!" % self.__class__.__name__
        self._tasks = list(self._check_tasks(tasks))
        self._custom_instructions = self._wiki_content(instructions)
        self._explanation = self._wiki_content(explanation)
        self._example = self._wiki_content(example)
        self._reading = self._wiki_content(reading, allow_file=True,
                                           subdir='readings')
        self._reading_instructions = self._wiki_content(reading_instructions)
        self._template = self._wiki_content(template, allow_file=True,
                                            subdir='templates')
        if sound_file is not None:
            try:
                self._recording = parent.resource(Media, sound_file)
            except ResourceNotFound, e:
                self._recording = None
                print e
            if transcript is None:
                transcript = os.path.splitext(sound_file)[0] + '.txt'
            assert isinstance(transcript, types.StringTypes)
            t = parent.resource(Transcript, transcript,
                                text=self._transcript_text(),
                                input_encoding=parent.input_encoding())
            self._transcript = t
        else:
            if transcript is not None:
                t = parent.resource(Transcript, transcript)
                print "Transcript without a 'sound_file': %s" % t.url()
            self._recording = None
            self._transcript = None
        if audio_version is not None:
            self._audio_version = parent.resource(Media, audio_version)
        else:
            self._audio_version = None
            
        self._init_resources()

    def _wiki_content(self, text, allow_file=False, subdir=None):
        if text is None:
            return None
        assert isinstance(text, types.StringTypes)
        if allow_file and len(text.splitlines()) == 1:
            name, ext = os.path.splitext(text)
            if subdir:
                name = os.path.join(subdir, name)
            try:
                content = self._parent.parse_wiki_file(name, ext=ext[1:])
            except IOError, e :
                print "Unable to read file: %s" % e
                return None
        else:
            content = self._parent.parse_wiki_text(re.sub('\[', '![', text))
        return Container(self._parent, content)
    
    def _init_resources(self):
        self._parent.resource(Script, 'audio.js')

    # Class methods
        
    def task_type(cls):
        return cls._TASK_TYPE
    task_type = classmethod(task_type)
    
    def name(cls):
        return cls._NAME
    name = classmethod(name)

    def used_types(cls):
        return cls._used_types
    used_types = classmethod(used_types)

    def help(cls, parent, template):
        cls._help_node = parent
        mp = wiki.MacroParser()
        mp.add_globals(cls=cls, displays=[x[0] for x in cls._DISPLAYS],
                       buttons=[x[0] for x in cls._BUTTONS], **globals())
        text = mp.parse(template)
        return wiki.Parser(parent).parse(text)
    help = classmethod(help)
    
    # Instance methods

    def _check_tasks(self, tasks):
        return tasks

    def _transcript_text(self):
        return None

    def _form_name(self):
        return "exercise_%d" % id(self)
    
    def _instructions(self):
        return self._INSTRUCTIONS

    def _sound_controls(self, label, media, transcript=None):
        if transcript is not None:
            t = " " + link(_("show transcript"), transcript.url(),
                           target="transcript")
        else:
            t = ""
        beg  = '<form class="sound-control" action="#">%s\n' % label
        play = button(_("Play"), "play_audio('%s')" % media.url())
        stop = button(_("Stop"), 'stop_audio()')
        end  = t + '\n</form>'
        a = '%s [%s]' % (label, link(_("Play"), media.url()))
        result = (script_write(beg + play),
                  script_write(stop, condition='document.media_player'),
                  script_write(end, p(a+t)))
        return '\n'.join(result)

    def export(self):
        header = div((self._header(),
                      link(_("Exercise Help"), self._help_node.url(),
                           target='help', cls='exercise-help-link')),
                     cls='exercise-header')
        parts = [getattr(self, '_export_'+part)()
                 for part in self._EXPORT_ORDER or ('reading',
                                                    'explanation',
                                                    'instructions',
                                                    'recording',
                                                    'audio_version',
                                                    'example',
                                                    'tasks')]
        parts.append(script(self._init_script()))
        return "\n\n".join([x for x in [header]+parts if x is not None])

    def _export_tasks(self):
        tasks = [self._export_task(t) for t in self._tasks]
        if self._template:
            tasks = self._template.export() % tuple(tasks)
        else:
            tasks = "\n".join(tasks)
        if tasks:
            return form((tasks, self._results() or ''), name=self._form_name())
        else:
            return None

    def _export_explanation(self):
        if self._explanation is not None:
            return _("Explanation:") + \
                   div(self._explanation.export(), cls="explanation")
        else:
            return None
        
    def _export_example(self):
        if self._example is not None:
            return _("Example:") + div(self._example.export(), cls="example")
        else:
            return None
    
    def _export_reading(self):
        if self._reading is not None:
            return self._reading_instructions.export() + \
                   div(self._reading.export(), cls="reading")
        else:
            return None
    
    def _export_instructions(self):
        """Return the HTML formatted instructions for this type of exercise."""
        custom = self._custom_instructions
        return custom and custom.export() or p(self._instructions())

    def _export_recording(self):
        if self._recording:
            return self._sound_controls(_("Recording:"), self._recording,
                                        self._transcript)
        else:
            return None
    
    def _export_audio_version(self):
        if self._audio_version:
            label = self._AUDIO_VERSION_LABEL
            return self._sound_controls(label, self._audio_version)
        else:
            return None

    def _export_task(self, task):
        parts = self._export_task_parts(task)
        if not isinstance(parts, (types.TupleType, types.ListType)):
            parts = (parts, )
        else:
            parts = [p for p in parts if p is not None]
        cls = camel_case_to_lower(self.__class__.__name__)
        return div(parts, cls='task %s-task' % cls) + self._TASK_SEPARATOR

    def _results(self):
        return None

    def _init_script(self):
        return ""
        
    
class Listening(Exercise):
    _NAME = _("Listening")
    _RECORDING_REQUIRED = True

    
class Reading(Exercise):
    _NAME = _("Reading")
    _READING_REQUIRED = True
        
    
class SentenceCompletion(Exercise):
    _NAME = _("Sentence Completion")
    _AUDIO_VERSION_REQUIRED = True
    _TASK_TYPE = None
    _INSTRUCTIONS = _("""Practise speech according to the instructions within
    the recording.""")
    _AUDIO_VERSION_LABEL = _("""This exercise can be only done purely
    aurally/orally:""")
    
    
class _InteractiveExercise(Exercise):
    """A common super class for exercises which can be interactively evaluated.

    These exercises allow the user to indicate his answers and the computer
    gives him a feedback.
    
    """
    _ANSWER_SHEET_LINK_CLASS = 'answer-sheet-link'
    _RESPONSES = (('correct', 'responses/c*.mp3'),
                  ('incorrect', 'responses/i*.mp3'))
    
    _FORM_HANDLER = 'Handler'
    _MESSAGES = {", $x ($y%) on first attempt":_(", $x ($y%) on first attempt")}

    _DISPLAYS = (('answered', _('Answered:')),
                 ('result', _('Correct:')))
    _BUTTONS = (('fill',  _('Fill'),  button, "this.form.handler.fill()"),
                ('reset', _('Reset'), reset,  "this.form.handler.reset()"))

    def _init_resources(self):
        super(_InteractiveExercise, self)._init_resources()
        self._parent.resource(Script, 'exercises.js')
        self._parent.resource(Script, 'audio.js')
        self._responses = {}
        for key, filename in self._RESPONSES:
            media = self._parent.resource(SharedMedia, filename)
            if not isinstance(media, (types.ListType, types.TupleType)):
                media = (media,)
            self._responses[key] = tuple(media)
            
    def _response(self, selector):
        responses = self._responses[selector]
        return responses[random.randint(0, len(responses)-1)]
        
    def _answers(self):
        return ()

    def _init_script(self):
        #return "init_form(document.forms['%s'], '%s', NULL, NULL, NULL);" % \
        #       (self._form_name(), self._FORM_HANDLER)
        responses = dict([(key, [media.url() for media in values])
                          for key, values in self._responses.items()])
        return "init_form(document.forms['%s'], new %s(), %s, %s, %s);" % \
               (self._form_name(), self._FORM_HANDLER,
                js_array(self._answers()), js_dict(responses),
                js_dict(self._MESSAGES))

    def _results(self):
        displays = [' '.join((label, field(name=name, size=50, readonly=True)))
                    for name, label in self._DISPLAYS]
        buttons = [type(label, handler)
                   for id, label, type, handler in self._BUTTONS]
        panel = div((div('<br/>'.join(displays), 'display'),
                     div(buttons, 'buttons')), 'results')
        l = p(_("See the %s to check your results.") %
              link(_("answer sheet"), self._answer_sheet_url(), target="help"))
        return script_write(panel, l)

    def _answer_sheet_items(self):
        return ()
    
    def _answer_sheet_anchor(self, index=None):
        a = self.anchor()
        if index is None:
            return a
        else:
            return "%s-a%d" % (a, index)
    
    def _answer_sheet_url(self, index=None):
        return self._answer_sheet_node.url() + "#" + \
               self._answer_sheet_anchor(index)

    def _answer_sheet_link(self, index):
        lnk = link("?", self._answer_sheet_url(index),
                   title=_("Show the answer sheet."),
                   target='help', cls=self._ANSWER_SHEET_LINK_CLASS)
        return lnk
        #return span(lnk, cls=self._ANSWER_SHEET_LINK_CLASS)
        
    def answer_sheet(self, parent):
        self._answer_sheet_node = p = parent
        i = 0
        items = []
        for answer, comment in self._answer_sheet_items():
            a = Anchor(p, self._answer_sheet_anchor(i), answer)
            if comment:
                c = Paragraph(p, WikiText(p, comment))
                items.append(Container(p, (a, c)))
            else:
                items.append(a)
            i += 1
        anchor = Anchor(p, self._answer_sheet_anchor())
        answers = ItemizedList(p, items, type=ItemizedList.TYPE_NUMERIC)
        return Container(p, (anchor, answers))
    
################################################################################
################################################################################
  
class _ChoiceBasedExercise(_InteractiveExercise):
    "A superclass for all exercises based on choosing from predefined answers."

    _FORM_HANDLER = 'ChoiceBasedExerciseHandler'

    def _answers(self):
        return [t.choice_index(t.correct_choice())
                for t in self._tasks if len(t.choices()) > 0]
    
    def _answer_sheet_items(self):
        return [(t.correct_choice().answer(), t.comment())
                for t in self._tasks if len(t.choices()) > 0]

    def _non_js_choice_control(self, task, choice):
        media = self._response(choice.correct() and 'correct' or 'incorrect')
        return link(choice.answer(), media.url())
    
    def _js_choice_control(self, task, choice):
        choice_id = 'choice_%s' % id(choice)
        ctrl = radio('task-%d' % self._tasks.index(task), id=choice_id,
                     onclick="this.form.handler.eval_answer(this)", 
                     value=task.choice_index(choice), cls='answer-control')
        return ctrl +' '+ label(choice.answer(), choice_id)

    def _choice_label(self, task, choice):
        return chr(ord('a') + task.choice_index(choice)) + '.&nbsp;'
        
    def _format_choice(self, task, choice):
        ctrl = script_write(self._js_choice_control(task, choice),
                            self._non_js_choice_control(task, choice))
        return self._choice_label(task, choice) + ctrl + '<br/>'

    def _format_choices(self, task):
        formatted = [self._format_choice(task, ch) for ch in task.choices()]
        return div(formatted, 'choices')

    def _export_task_parts(self, task):
        lnk = self._answer_sheet_link(self._tasks.index(task))
        return (task.prompt(), self._format_choices(task), lnk)

    
class MultipleChoiceQuestions(_ChoiceBasedExercise):
    """Choosing one of several answers for a given question."""
    
    _TASK_TYPE = MultipleChoiceQuestion
    _NAME = _("Multiple Choice Questions")
    _INSTRUCTIONS = _("""For each of the questions below choose the correct
    answer from the list.""")

    
class Selections(_ChoiceBasedExercise):
    """Selecting one of several statements/sentences (the correct one)."""
    
    _TASK_TYPE = Selection
    _NAME = _("Selections")
    _INSTRUCTIONS = _("""Decide which statement is correct for each of the
    groups below .""")

    
class TrueFalseStatements(_ChoiceBasedExercise):
    """Deciding whether the sentence is true or false."""
    
    _TASK_TYPE = TrueFalseStatement
    _NAME = _("True/False Statements")
    _INSTRUCTIONS = _("""For each of the statements below indicate whether
    you think they are true or false.""")
    
    def _choice_label(self, task, choice):
        return ""

    
class _SelectBasedExercise(_ChoiceBasedExercise):

    _FORM_HANDLER = 'SelectBasedExerciseHandler'

    def _format_choices(self, task):
        choices = task.choices()
        js = select('task-%d' % self._tasks.index(task),
                    [(ch.answer(), task.choice_index(ch)) for ch in choices],
                    onchange="this.form.handler.eval_answer(this)",
                    id=task.id())
        nonjs = [self._non_js_choice_control(task, ch) for ch in task.choices()]
        return script_write(js, "("+"|".join(nonjs)+")")

    
class GapFilling(_SelectBasedExercise):
    """Choosing from a list of words to fill in a gap in a sentence."""

    _TASK_TYPE = GapFillStatement
    _NAME = _("Gap Filling")
    _INSTRUCTIONS = _("""For each of the statements below choose the correct
    word to fill in the gap.""")

    def _export_task_parts(self, task):
        statement = task.substitute_gap("%s")
        lnk = self._answer_sheet_link(self._tasks.index(task))
        return statement.replace('%s', self._format_choices(task)) +'\n'+ lnk 
    

################################################################################
################################################################################

class _FillInExercise(_InteractiveExercise):
    """A common base class for exercises based on writing text into fields."""

    _TASK_TYPE = FillInTask
    
    _RESPONSES = (('all_correct', 'responses/all-correct.mp3'),
                  ('all_wrong',   'responses/all-wrong.mp3'),
                  ('some_wrong',  'responses/some-wrong.mp3')) + \
                  _InteractiveExercise._RESPONSES
        
    _FORM_HANDLER = 'FillInExerciseHandler'

    _BUTTONS = (('eval', _("Evaluate"), button,
                 "this.form.handler.evaluate()"),) + \
                 _InteractiveExercise._BUTTONS
    
    _TASK_FORMAT = "%s<br/>%s"

    def _check_tasks(self, tasks):
        for t in tasks:
            assert not isinstance(t, ClozeTask) or len(t.answers()) == 1, \
                       "%s requires just one textbox per task (%d found)!" % \
                   (self.__class__.__name__, len(t.answers())) 
        return tasks
    
    def _answers(self):
        return [t.answer() for t in self._tasks if t.answer() is not None]
        
    def _answer_sheet_items(self):
        return [('; '.join(t.answer().split('|')), t.comment())
                for t in self._tasks if t.answer() is not None]
    
    def _make_field(self, text, id=None):
        try:
            counter = self._field_counter
        except AttributeError:
            self._field_counter = counter = Counter(0)
        n = counter.next()
        f = field(cls='fill-in-task', name="task-%d" % n,
                  size=max(4, len(text)+1), id=id)
        return f + self._answer_sheet_link(n)
    
    def _export_task_parts(self, task):
        text = task.text(self._make_field)
        return self._TASK_FORMAT % (label(task.prompt(), task.id()), text)
                               
        
    
class VocabExercise(_FillInExercise):
    """A small text-field for each vocabulary item on a separate row."""

    _NAME = _("Vocabulary Practice Exercise")
    _TASK_FORMAT = "%s %s"
    _INSTRUCTIONS = _("""Fill in a correct translation for each of the terms
    below.""")
    _AUDIO_VERSION_LABEL = _("""Use the recording to hear the model
    pronunciation:""")
    _TASK_SEPARATOR = ''

    def _check_tasks(self, tasks):
        if not tasks:
            dict = {}
            for item in self._parent.vocab:
                translation, word = (item.translation(), item.word())
                if translation:
                    if dict.has_key(translation):
                        word = dict[translation] +'|'+ word
                    dict[translation] = word
            tasks = [FillInTask(t, w) for t, w in dict.items()]
        return tasks
   

class Substitution(_FillInExercise):
    """A prompt (a sentence) and a big text-field for each task."""

    _NAME = _("Substitution")
    _INSTRUCTIONS = _("Use the text in brackets to transform each sentence.")
    

class Transformation(_FillInExercise):
    """Pairs of sentences, the later with a gap (text-field)."""


    _NAME = _("Transformation")
    _TASK_TYPE = TransformationTask
    _TASK_FORMAT = "A. %s<br/>B. %s"
    _INSTRUCTIONS = _("""Fill in the gap in sentence B so that it means the same
    as sentence A.""")
    
    def _instructions(self):
        if self._example:
            return _("Transform the sentences below according to the example.")
        else:
            return self._INSTRUCTIONS

        
class Dictation(_FillInExercise):
    """One big text-field for a whole exercise."""

    _NAME = _("Dictation")
    _TASK_TYPE = DictationTask
    _FORM_HANDLER = 'DictationHandler'
    _RECORDING_REQUIRED = True
    _MESSAGES = {'Correct': _('Correct'),
                 'Error(s) found': _('Error(s) found')}
    _MESSAGES.update(_FillInExercise._MESSAGES)
    _DISPLAYS = (('result', _('Result:')),)
    _INSTRUCTIONS = _("""Listen to the recording and type exactly what you hear
    into the textbox below.""")

    def _check_tasks(self, tasks):
        assert len(tasks) == 1
        return tasks
    
    def _transcript_text(self):
        return self._tasks[0].answer()

    def _export_task_parts(self, task):
        return '<textarea rows="10" cols="60"></textarea>'
    

class _Cloze(_FillInExercise):
    _NAME = _("Cloze")
    _TASK_TYPE = ClozeTask
    _INSTRUCTIONS = _("""Fill in the gaps in the text below.  There is just one
    correct answer for each gap.""")
    
    def _transcript_text(self):
        return "\n\n".join([t.plain_text() for t in self._tasks])
    
    def _instructions(self):
        if self._recording is not None:
            return _("""Listen to the recording carefully and then fill in the
            gaps in the text below using the same words.""")
        else:
            return self._INSTRUCTIONS

        
class _ExposedCloze(_Cloze):
    _NAME = _("Exposed Cloze")
    _INSTRUCTIONS = _("""Fill in gaps in the sentences using words or
    expressions listed below.""")

    def _export_instructions(self):
        answers = self._answers()
        answers.sort()
        instructions = super(_ExposedCloze, self)._export_instructions()
        return instructions + itemize(answers)

    
class NumberedCloze(_Cloze):

    def _export_task_parts(self, task):
        text = task.text(self._make_field)
        return "%d. " % (self._tasks.index(task) + 1) + text

    
class NumberedExposedCloze(NumberedCloze, _ExposedCloze):
    pass
    

class Cloze(_Cloze):
    """Paragraphs of text including text-fields for the marked words."""
    _ANSWER_SHEET_LINK_CLASS = 'cloze-answer-sheet-link'
    _TASK_SEPARATOR = ''

    def _check_tasks(self, tasks):
        assert len(tasks) == 1
        return tasks
    
    def _answers(self):
        return self._tasks[0].answers()
        
    def _answer_sheet_items(self):
        t = self._tasks[0]
        return zip(t.answers(), t.comments())
        
    def _export_task_parts(self, task):
        transform = lambda t: self._wiki_content(t).export()
        return task.text(self._make_field, transform)


class ExposedCloze(Cloze, _ExposedCloze):
    pass
