# -*- coding: utf-8 -*-
#
# Copyright (C) 2004-2013 Brailcom, o.p.s.
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

"""Framework for exporting LCG content into various output formats.

The module contains the following important classes:

  'Exporter' :: Generic exporter class defining the common interface that must
    be supported by derived exporters for particular output formats.

See documentation of the individual classes for more details.

"""

import collections
import os
import re
import shutil
import string

from lcg import attribute_value, log, concat, Localizable, Localizer, Resource, \
    ContentNode, Content, Container, ContentVariants, \
    Paragraph, PreformattedText, Section, TableOfContents, \
    DefinitionList, FieldSet, \
    Table, TableCell, TableHeading, TableRow, \
    TextContent, Heading, Title, Anchor, Link, \
    Strong, Emphasized, Underlined, Code, Citation, Quotation, Superscript, Subscript, \
    InlineAudio, InlineExternalVideo, InlineImage, InlineVideo, ItemizedList, \
    NewLine, NewPage, PageHeading, PageNumber, HorizontalSeparator, HSpace, VSpace, \
    Substitution, SetVariable, MathML, Figure
from lcg.exercises import Exercise


class SubstitutionIterator(object):
    """Supporting object for multiple-value substitution variables.

    There are situations where a substitution variable used inside structured
    text markup can provide multiple values repeatedly, e.g. to generate
    several different values for repeated rows of a table.  This is where
    instance of this class is to be used as the variable value in provided
    globals.

    It works as follows: New instance of this class is created.  Before each
    new value is retrieved via 'value()' method, 'next()' method must be called
    and checked for its return value.  The iterator can be reinitialized using
    'reset()' method.  'value()' is called by 'MarkupFormatter', other methods
    must be called by the code providing the globals.

    In order to implement iterating behavior for particular substitution
    situation you should subclass this class and redefine the methods
    '_value()', '_next()' and '_reset()'.
    
    """
    class NotStartedError(Exception):
        """Exception raised when 'value()' without previous 'next()' is called.
        """
        def __init__(self, iterator):
            self._iterator = iterator
        def iterator(self):
            return self._iterator

    class IteratorError(Exception):
        """Exception available to any code to signal iterator related errors.
        """

    def __init__(self):
        self.reset()
        
    def value(self):
        """Return the current value of the iterator.

        It is an error, signalled by 'NotStartedError', if 'next()' method
        hasn't been called after the instance was created or 'reset()' method
        was called.  Once 'next()' method has been called, it's legal to call
        'value()' method several times to retrieve the same value, or to call
        'next()' method any time (even without calling 'value()' method) to
        advance to the next iterator value.

        """
        if not self._started:
            raise self.NotStartedError(self)
        return self._value()

    def _value(self):
        return None
    
    def next(self):
        """Advance the iterator to the next value.

        Return true if the next value is available (via 'value()' method) and
        false if there is no next value.

        """
        self._started = True
        return self._next()

    def _next(self):
        return False
    
    def reset(self):
        """Reset the iterator to its initial state.

        After this operation the iterator can be used to generate all the
        substitution values again.
        
        """
        self._started = False
        self._reset()

    def _reset(self):
        pass


class Exporter(object):
    """Transforming structured content objects to various output formats.

    This class is a base class of all exporters.  It provides basic exporting
    framework to be extended and customized for particular kinds of outputs.
    When defining a real exporter you may wish to extend the 'Context' which is
    passed throughout the export process (see below) to be able to pass otput
    format specific information or provide specific functionality.  For example
    in web server invironment, it might be practical to pass the request object
    along with the context (this is done in Wiking Exporter).

    The exporting process itself is run by subsequent calls to the 'export()'
    method, passing it a context created by the 'context()' method.
    
    """

    _RE_SPACE_MATCHER = re.compile('  +')
    _TOC_MARKER_CHAR = u'\ue000'
    _HFILL = u'\ue001\ue001\ue001'
    
    class Context(object):
        """Storage class containing complete data necessary for export.

        An instance of this class is passed to export methods of content
        classes.  It is possible to access all information about the current
        context (exported node, target language, etc) and also all the
        components involved in the export process (the exporter, generator and
        localizer instances).

        The class is designed to be extensible.  The derived classes may accept
        additional constructor arguments to expose additional context
        information to the export process (for example the current request may
        be passed through the context in the on-line web environment).  The
        method '_init_kwargs()' may be overriden to process these specific
        arguments without the need to override the default constructor.
        
        To use an extended context class, just define it as the 'Context'
        attribute of the derived 'Exporter' class (it is a nested class).

        """
        def __init__(self, exporter, node, lang, **kwargs):
            """Initialize the export context.

            Arguments:
            
              exporter -- 'Exporter' instance to which this context belongs.
              node -- 'ContentNode' instance to be exported.
              lang -- Target language as an ISO 639-1 Alpha-2 lowercase
                language code or None.  If None, the export will be language
                neutral (no information about the content language will be
                present in the output and no translation will be performed).

            The constructor should not be called directly.  Use the method
            'context()' instead.
            
            """
            self._exporter = exporter
            self._node = node
            self._toc_markers = {}
            self._secondary_language_active = False
            self._init_kwargs(lang=lang, **kwargs)
            self._page_heading = None
            self.list_level = 0

        def _init_kwargs(self, lang, sec_lang=None, presentation=None, timezone=None):
            self._lang = lang
            self._sec_lang = sec_lang
            self._presentation = presentation
            self._localizer = self._exporter.localizer(lang, timezone=timezone)
            
        def exporter(self):
            return self._exporter
        
        def lang(self):
            if self._secondary_language_active:
                lang = self._sec_lang or self._lang
            else:
                lang = self._lang
            return lang

        def sec_lang(self):
            return self._sec_lang

        def set_lang(self, lang):
            orig_lang = self._lang
            self._lang = lang
            return orig_lang
    
        def node(self):
            return self._node
            
        def locale_data(self):
            return self._localizer.locale_data()

        def presentation(self):
            return self._presentation

        def localize(self, text):
            return self._localizer.localize(text)

        translate = localize # For backwards compatibility...

        def resource(self, filename, **kwargs):
            return self._node.resource(filename, **kwargs)
        
        def uri(self, target, **kwargs):
            return self._exporter.uri(self, target, **kwargs)

        def toc_element(self, marker):
            return self._toc_markers[marker]
            
        def add_toc_marker(self, element):
            marker = unicode(len(self._toc_markers))
            self._toc_markers[marker] = element
            return marker
        
        def page_heading(self):
            return self._page_heading

        def set_page_heading(self, heading):
            self._page_heading = heading
            
    def __init__(self, translations=()):
        self._translation_path = translations
        self._export_method = self._define_export_methods()

    def _uri_node(self, context, node, lang=None):
        return node.id()

    def _uri_section(self, context, section, local=False):
        result = "#" + section.anchor()
        if not local:
            result = self._uri_node(context, section.parent()) + result
        return result

    def _resource_uri_prefix(self, context, resource):
        return resource.SUBDIR

    def _uri_resource(self, context, resource):
        if resource.uri() is not None:
            result = resource.uri()
        else:
            result = resource.filename()
            prefix = self._resource_uri_prefix(context, resource)
            if prefix:
                result = prefix + '/' + result
        return result
    
    def _uri_external(self, context, target):
        return target.uri()
    
    def _define_export_methods(self):
        return {Content: self._export_content,
                HorizontalSeparator: self._export_horizontal_separator,
                NewPage: self._export_new_page,
                NewLine: self._export_new_line,
                PageNumber: self._export_page_number,
                PageHeading: self._export_page_heading,
                Title: self._export_title,
                HSpace: self._export_hspace,
                VSpace: self._export_vspace,
                Strong: self._export_strong,
                Emphasized: self._export_emphasized,
                Underlined: self._export_underlined,
                Code: self._export_code,
                Citation: self._export_citation,
                Quotation: self._export_quotation,
                Superscript: self._export_superscript,
                Subscript: self._export_subscript,
                TextContent: self._export_text_content,
                PreformattedText: self._export_preformatted_text,
                Anchor: self._export_anchor,
                Container: self._export_container,
                Paragraph: self._export_paragraph,
                Link: self._export_link,
                Section: self._export_section,
                Heading: self._export_heading,
                ContentVariants: self._export_content_variants,
                TableOfContents: self._export_table_of_contents,
                ItemizedList: self._export_itemized_list,
                DefinitionList: self._export_definition_list,
                FieldSet: self._export_field_set,
                Table: self._export_table,
                TableRow: self._export_table_row,
                TableCell: self._export_table_cell,
                TableHeading: self._export_table_heading,
                InlineImage: self._export_inline_image,
                InlineAudio: self._export_inline_audio,
                InlineVideo: self._export_inline_video,
                InlineExternalVideo: self._export_inline_external_video,
                SetVariable: self._export_set_variable,
                Substitution: self._export_substitution,
                MathML: self._export_mathml,
                Figure: self._export_figure,
                Exercise: self._export_exercise,
                }
    
    def _export(self, node, context, recursive=False):
        heading = node.heading().export(context)
        newline = self._newline(context, 2)
        context.set_page_heading(heading)
        content = node.content().export(context)
        if recursive:
            # FIXME: The context should be cloned here with the correct node in
            # it, but it doesn't seem to matter in Braille output, which is
            # currently the only use case for the recursive export.
            content = self.concat(content,
                                  *[self._export(n, context, recursive=True)
                                    for n in node.children()])
        return self.concat(heading, newline, content)

    def uri(self, context, target, **kwargs):
        """Return the URI of the target as string.

        Arguments:

          context -- exporting object created in the 'context' method and
            propagated from the 'export' method
          target -- URI target that can be one of: 'ContentNode', 'Section',
            'Link.ExternalTarget' or 'Resource' instance

        """
        if isinstance(target, ContentNode):
            method = self._uri_node
        elif isinstance(target, Section):
            method = self._uri_section
        elif isinstance(target, Resource):
            method = self._uri_resource
        elif isinstance(target, Link.ExternalTarget):
            method = self._uri_external
        else:
            raise Exception("Invalid URI target:", target)
        return method(context, target, **kwargs)

    def localizer(self, lang, timezone=None):
        """Return a 'lcg.Localizer' instance for given language and time zone."""
        return Localizer(lang, timezone=timezone, translation_path=self._translation_path)
    
    translator = localizer
    """Deprecated backwards compatibility alias - please use 'localizer' instead."""

    def context(self, node, lang, **kwargs):
        """Return the export context instance to be used as an argument to the 'export' method.

        All arguments are passed to the 'Context' constructor.  See its
        documentation for more details.

        Returns an instance of 'self.Context' class, thus if the derived
        exporter class overrides the definition of its 'Context' class, the
        instance of this overriden class is returned.  This is also the
        recommended approach for extending the exporter context with specific
        context information (see 'Exporter.Context' documentation for more
        information).

        """
        return self.Context(self, node, lang, **kwargs)

    def export_element(self, context, element):
        """Export the given content element and return its output representation.

        Arguments:

          context -- export context object created by the 'context()' method and
            propagated from the 'export()' method.  Instance of 'self.Context'.
          element -- 'Content' instance to be exported.
          
        The supported element types are defined by the method '_define_export_methods()'.  If the
        'element' class is not found there directly, all its base classes are searched.

        """
        if element.parent() is None:
            # Temporary hack to avoid the need to call set_parent() explicitly.
            # The methods Content.set_parent() and Content.parent() should be
            # removed alltogether.
            element.set_parent(context.node())
        cls = element.__class__
        if cls not in self._export_method:
            def base_classes(cls):
                result = list(cls.__bases__)
                for x in result:
                    result.extend(base_classes(x))
                return result
            bases = base_classes(cls)
            while bases and cls not in self._export_method:
                cls = bases.pop(0)
        try:
            method = self._export_method[cls]
        except KeyError:
            raise UnsupportedElementType(element.__class__)
        return method(context, element)
        
    def export(self, context, recursive=False):
        """Export the node represented by 'context' and return the corresponding output string.

        'context' is the exporter 'Context' instance as returned by the
        'context()' method.  The context holds the actual 'ContentNode'
        instance to be exported.

        """
        return self._export(context.node(), context, recursive=recursive)

    # Basic utilitites

    def escape(self, text):
        """Escape 'text' for the output format and return the resulting string.

        In this class the method returns value of 'text'.
        
        """
        return text

    def concat(self, *items):
        """Return elements of 'exported' objects sequence as a general block.

        In this class the method performs simply text concatenation of
        'exported' objects.

        """
        return concat(*items)

    def text(self, context, text, lang=None):
        """Return exported 'text'.

        Arguments:

          context -- current 'Context' instance
          text -- text to convert; unicode
          lang -- target language as an ISO 639-1 Alpha-2 lowercase
            language code or 'None'

        """
        assert isinstance(text, basestring), text
        if text and self._private_char(text[0]):
            text = ''
        return self.escape(text)

    def _reformat_text(self, text):
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        text = self._RE_SPACE_MATCHER.sub(' ', text)
        return text

    def _newline(self, context, number=1, inline=False):
        return u'\n' * number

    def _ensure_newlines(self, context, exported, number=1):
        real_number = 0
        while (real_number < number and len(exported) > real_number and
               exported[-real_number - 1] == '\n'):
            real_number += 1
        return exported + '\n' * (number - real_number)

    def _space(self, context, number=1):
        return u' ' * number

    def _indent(self, exported, indentation, init_indentation=None):
        if init_indentation is None:
            init_indentation = indentation
        lines = exported.split('\n')
        if lines:
            space = u' ' * indentation
            lines = ([u' ' * init_indentation + lines[0]] +
                     [space + l if l else '' for l in lines[1:]])
        return string.join(lines, '\n')

    def _list_item_prefix(self, context):
        return u'• '

    def _separator(self, context, lang=None):
        return self.text(context, u' — ', lang=lang)

    def _private_char(self, char):
        char_code = ord(char)
        return 57344 <= char_code and char_code <= 63743

    # Content element export methods (defined by _define_export_methods).

    def _export_content(self, context, element):
        """Export the base 'Content' element.

        This element actually doesn't hold any content, so the method just
        returns escaped empty string.  It should not be necessary to override
        this method in derived classes.

        """
        return self.text(context, '')

    def _export_text_content(self, context, element):
        """Export the given 'TextContent' element.

        In this class the method just returns the escaped element text.  It
        should not be necessary to override this method in derived classes.
        
        """
        t = self._reformat_text(element.text())
        return self.text(context, t, lang=element.lang())
        
    def _export_anchor(self, context, element):
        """Export the given 'Anchor' element.

        In this class the method just returns the escaped anchor text.
        
        """
        return self._export_text_content(context, element)
    
    def _export_new_page(self, context, element):
        """Export the given 'NewPage' element.

        In this class the method just returns the page break character.
        
        """
        return '\f'

    def _export_new_line(self, context, element):
        """Export the given 'NewLine' element.

        In this class the method just returns the page break character.
        
        """
        return self._newline(context)

    def _export_horizontal_separator(self, context, element, width=64, in_table=False):
        """Export the given 'HorizontalSeparator' element."""
        separator = u'─' * width
        return self.concat(self.text(context, separator), self._newline(context))

    def _export_page_number(self, context, element):
        """Export the given 'PageNumber' element.

        In this class this method returns an escaped empty text.

        """
        return self.text(context, '')

    def _export_page_heading(self, context, element):
        """Export the given 'PageHeading' element.

        In this class this method returns an escaped empty text.

        """
        return self.text(context, '')

    def _export_hspace(self, context, element):
        """Export the given 'HSpace' element."""
        if element.size(context):
            text = self._space(context)
        else:
            text = ''
        return self.text(context, text, lang=element.lang())

    def _export_vspace(self, context, element):
        """Export the given 'VSpace' element."""
        return self._newline(context, 2 if element.size(context) else 1)

    def _export_strong(self, context, element):
        """Export the given 'Strong' element."""
        return self._export_container(context, element)
                
    def _export_emphasized(self, context, element):
        """Export the given 'Emphasized' element."""
        return self._export_container(context, element)
                
    def _export_underlined(self, context, element):
        """Export the given 'Underlined' element."""
        return self._export_container(context, element)
                
    def _export_code(self, context, element):
        """Export the given 'Code' element."""
        return self._export_container(context, element)
                
    def _export_citation(self, context, element):
        """Export the given 'Citation' element."""
        return self._export_container(context, element)
                
    def _export_quotation(self, context, element):
        """Export the given 'Quotation' element."""
        exported = self._export_container(context, element)
        source = element.source()
        uri = element.uri()
        if source or uri:
            lang = element.lang()
            extra = [self.text(context, '--', lang=lang)]
            if source:
                extra.append(self.text(context, u' ' + source, lang=lang))
            if uri:
                format_ = u' (%s)' if source else u' %s'
                extra.append(self.text(context, format_ % (uri,), lang=lang))
            exported = self.concat(exported, *extra)
        exported = self._ensure_newlines(context, exported, 2)
        exported = self._indent(exported, 1)
        return exported

    def _export_figure(self, context, element):
        """Export the given 'Figure' element."""
        return self._export_container(context, element)

    def _export_superscript(self, context, element):
        """Export the given 'Superscript' element."""
        return self._export_container(context, element)
                
    def _export_subscript(self, context, element):
        """Export the given 'Subscript' element."""
        return self._export_container(context, element)
                
    def _export_title(self, context, element):
        """Export the given 'Title' element.

        This method returns the escaped title of the requested content node.  There should be no
        need to override this method in derived classes.

        """
        id = element.id()
        parent = element.parent()
        if id is None:
            item = parent
        else:
            item = parent.find_section(id, context)
            if not item:
                item = parent.root().find_node(id)
        if item:
            title = item.title()
        else:
            title = id
        return self.text(context, title, lang=element.lang())

    def _export_preformatted_text(self, context, element):
        """Export verbatim text of given 'PreformattedText' element.

        In this class the method returns just the escaped element text.
        
        """
        text = element.text()
        lang = element.lang()
        text_lines = text.split('\n')
        output_lines = [self.text(context, text_lines[0], lang=lang)]
        for l in text_lines[1:]:
            output_lines.append(self._newline(context))
            output_lines.append(self.text(context, l, lang=lang))
        output_lines.append(self._newline(context))
        return self.concat(*output_lines)

    def _export_substitution(self, context, element):
        """Substitute the node variable defined by 'element'.

        The method returns export of the variable value.

        """
        name = element.name()
        if not name:
            return self.escape(element.markup())
        names = name.split('.')
        value = context.node().global_(str(names[0]))
        for xname in names[1:]:
            if value is None:
                break
            if isinstance(value, SubstitutionIterator):
                value = value.value()
            key = str(xname)
            dictionary = value
            try:
                value = value.get(key)
            except:
                dictionary = None
                break
            if isinstance(value, collections.Callable):
                value = value()
                # It is necessary to store the computed value in order to
                # prevent repeated object initializations in it.  Otherwise it
                # fails e.g. with substitution iterators.
                dictionary[key] = value
        if value is None:
            result = self.escape(element.markup())
        elif isinstance(value, Content):
            result = value.export(context)
        else:
            if not isinstance(value, Localizable):
                value = unicode(value)
            result = self.escape(value)
        return result
    
    def _export_set_variable(self, context, element):
        """Set node variable defined by 'element'.

        The method returns export of an empty content.

        """
        context.node().set_global(element.name(), element.value(), top=True)
        return self._export_content(context, Content())

    # Container elements
    
    def _export_container(self, context, element):
        """Export given 'Container' element.

        In this class the method exports the contained content elements and concatenates them.
        
        """
        exported = []
        for content in element.content():
            if isinstance(content, (ItemizedList, DefinitionList,)) and exported:
                exported[-1] = self._ensure_newlines(context, exported[-1])
            exported.append(content.export(context))
        return self.concat(*exported)

    def _transform_link_content(self, context, element):
        return self._export_container(context, element)

    def _transform_link_heading(self, context, heading):
        return heading.export(context)

    def _link_content_is_url(self, context, label):
        return label.startswith('http:')
        
    def _export_link(self, context, element):
        """Export given 'Link' element.

        In this class the method returns link description (if available) and
        the link target URL.
        
        """
        label = element.descr()
        if not label:
            label = self._transform_link_content(context, element)
        target = element.target(context)
        if not label:
            if isinstance(target, (ContentNode, Section)):
                label = self._transform_link_heading(context, target.heading())
            elif isinstance(target, Resource):
                label = target.title() or target.filename()
        if isinstance(target, element.ExternalTarget):
            uri = target.uri()
            if uri and label and self._link_content_is_url(context, label):
                # Try to prevent displaying image URLs
                label = uri
            else:
                if label is None:
                    title = target.title()
                    label = title or uri
                if uri and label != uri:
                    label = '%s (%s)' % (label, uri,)
        return label

    def _export_section(self, context, element):
        """Export given 'Section' element.

        In this class the method returns section title and contents separated by empty
        lines.
        
        """
        toc_marker = context.add_toc_marker(element)
        return self.concat(self.text(context, u'%s%s' % (self._TOC_MARKER_CHAR, toc_marker,)),
                           self.text(context, element.title(), element.lang()),
                           self._newline(context, 2),
                           self._export_container(context, element))

    def _export_heading(self, context, element):
        """Export given 'Heading' element."""
        return self._export_container(context, element)
        
    def _export_content_variants(self, context, element):
        """Export the proper language variant of 'ContentVariants' element.

        Returns the exported content for language determined by
        'context.lang()'.  There should be no need to override this method in
        derived classes.

        """
        return element.variant(context.lang()).export(context)
 
    def _export_itemized_list(self, context, element, lang=None):
        """Export given 'ItemizedList' element."""
        numbering = element.order()
        letters = u'abcdefghijklmnopqrstuvwxyz'
        n_letters = len(letters)
        item_number = [1]
        def number():
            n = item_number[0]
            item_number[0] += 1
            if numbering == ItemizedList.NUMERIC:
                result = u'%d. ' % (n,)
            elif numbering in (ItemizedList.LOWER_ALPHA, ItemizedList.UPPER_ALPHA,):
                result = letters[(n - 1) % n_letters]
                while n > n_letters:
                    n = n / n_letters
                    result = letters[(n - 1) % n_letters] + result
                if numbering == ItemizedList.UPPER_ALPHA:
                    result = result.upper()
                result += u'. '
            else:
                result = self._list_item_prefix(context)
            return result
        content = []
        with attribute_value(context, 'list_level', context.list_level + 1):
            for c in element.content():
                content.append(self._indent(self.text(context, number(), lang=lang), 0))
                exported = self._indent(c.export(context), 2, 0)
                exported = self._ensure_newlines(context, exported)
                content.append(exported)
        if context.list_level == 0:
            content.append(self._newline(context))
        return self.concat(*content)

    def _export_definition_list(self, context, element):
        """Export given 'DefinitionList' element."""
        lang = element.lang()
        exported = []
        for dt, dd in element.content():
            item = self.concat(dt.export(context),
                               self.text(context, self._separator(context), lang=lang),
                               dd.export(context))
            item = self._ensure_newlines(context, item)
            exported.append(item)
        result = self.concat(*exported)
        if result:
            n_newlines = 1 if context.list_level > 0 else 2
            result = self._ensure_newlines(context, result, n_newlines)
        return result

    def _export_field_set(self, context, element):
        """Export given 'FieldSet' element."""
        return self._export_definition_list(context, element)
            
    def _export_paragraph(self, context, element):
        """Export given 'Paragraph' element."""
        return self.concat(self._export_container(context, element),
                           self._newline(context, 2, inline=True))

    def _export_table_of_contents(self, context, element):
        """Generate a Table of Contents for given 'TableOfContents' element."""
        lang = element.lang()
        presentation_set = context.presentation()
        presentation = presentation_set and presentation_set.presentation(None, lang)
        page_width = presentation and presentation.page_width
        item_list = []
        def export(items):
            for node, subitems in items:
                current_lang = (node.lang() or lang)
                if isinstance(node, Section):
                    item_list.append(self.text(context, node.title(), lang=current_lang))
                else:
                    item_list.append(node.export(context))
                item_list.append(self.text(context, self._HFILL if page_width else ' '))
                item_list.append(self.text(context, node.page_number(context), lang=current_lang))
                item_list.append(self._newline(context))
                if subitems:
                    export(subitems)
        items = []
        def add_item(node, subitems):
            if isinstance(node, ContentNode):
                items.append((node.heading(), (),))
            else:
                items.append((node, subitems,))
        for node, subitems in element.items(context):
            add_item(node, subitems)
        export(items)
        return self.concat(self.text(context, element.title() or '???', lang=lang),
                           self._newline(context, 2),
                           self.concat(*item_list),
                           self._newline(context))

    # Tables

    def _export_table(self, context, element):
        """Export given 'Table' element."""
        separator = HorizontalSeparator()
        content = element.content()
        exported_rows = []
        if content and content[0].line_above:
            exported_rows.append(separator)
        for row in element.content():
            exported_rows.append(row.export(context))
            if row.line_below:
                exported_rows.append(separator)
        widths = []
        n_cells = 0
        for row in exported_rows:
            if isinstance(row, list):
                n_cells = len(row)
                widths = [0] * n_cells
                break
        else:
            return self.concat(*exported_rows)
        for row in exported_rows:
            if isinstance(row, list):
                for i in range(n_cells):
                    widths[i] = max(widths[i], len(row[i]))
        total_width = 0
        # Unclean (but easy): the separators are exported out of context
        vertical_separator, vertical_separator_width = self._vertical_cell_separator(context)
        for w in widths:
            total_width += w + vertical_separator_width + 1
        if widths:
            total_width += 1
        exported_separator = self._export_horizontal_separator(context, separator,
                                                               width=total_width, in_table=True)
        item_list = []
        for row in exported_rows:
            if isinstance(row, list):
                if n_cells > 0:
                    item_list.append(vertical_separator)
                for i in range(n_cells):
                    cell = row[i]
                    item_list.append(cell)
                    space = self._space(context, widths[i] - len(cell) + 1)
                    item_list.append(self.text(context, space))
                    item_list.append(vertical_separator)
                item_list.append(self._newline(context))
            elif row is separator:
                if exported_separator is not None:
                    item_list.append(exported_separator)
            else:
                item_list.append(row)
        item_list.append(self._newline(context))
        return self.concat(*item_list)

    def _export_table_row(self, context, element):
        """Export given 'TableRow' element."""
        return [c.export(context) for c in element.content()]
        
    def _export_table_cell(self, context, element):
        """Export given 'TableCell' element."""
        return self._export_container(context, element)

    def _export_table_heading(self, context, element):
        """Export given 'TableHeading' element."""
        return self._export_table_cell(context, element)

    def _vertical_cell_separator(self, context):
        return u'│ ', 2

    # Media (represented by resources wrapped in inline content elements)

    def _inline_export(self, context, element, resource, lang=None):
        label = element.title()
        if label is None and resource is not None:
            label = resource.title() or resource.filename()
        if resource is not None:
            descr = resource.descr()
            if descr:
                label = '%s (%s)' % (label, descr,)
        return self.text(context, label, lang=lang)

    def _export_inline_image(self, context, element):
        """Export embedded image for given 'InlineImage' element.
        
        In this class the method returns just the escaped image title.
        
        """
        return self._inline_export(context, element, element.image(context), lang=element.lang())

    def _export_inline_audio(self, context, element):
        """Export embedded audio player for given 'InlineAudio' element.

        In this class the method returns just the escaped audio title.

        """
        return self._inline_export(context, element, element.audio(context), lang=element.lang())

    def _export_inline_video(self, context, element):
        """Export embedded video player for given 'InlineVideo' element.

        In this class the method returns just the escaped video title.

        """
        return self._inline_export(context, element, element.video(context), lang=element.lang())

    def _export_inline_external_video(self, context, element):
        """Export embedded video player for given 'InlineExternalVideo' element.

        In this class the method returns just the escaped video title.
        
        """
        label = (element.title() or
                 "Embedded Video %s id=%s" % (element.service(), element.video_id()))
        return self._inline_export(context, label, None, lang=element.lang())

    # Special constructs

    def _export_mathml(self, context, element):
        """Export 'MathML' element.

        In this class the method returns the raw MathML content.
        
        """
        return element.content()
    
        
class FileExporter(object):
    """Mix-in class exporting content into files.

    This class defines the 'dump()' method for writing the result of the export
    into filesystem.  See its documentation for more information.

    """

    _OUTPUT_FILE_EXT = None

    def __init__(self, force_lang_ext=False, **kwargs):
        super(FileExporter, self).__init__(**kwargs)
        self._force_lang_ext = force_lang_ext

    def _write_file(self, filename, content):
        directory = os.path.split(filename)[0]
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        file = open(filename, 'w')
        try:
            file.write(content)
        finally:
            file.close()

    def _filename(self, node, context, lang=None):
        """Return the pathname of node's output file relative to the output directory."""
        name = node.id().replace(':', '-')
        if lang is None:
            lang = context.lang()
        if lang is not None and ((len(node.variants()) > 1) or (self._force_lang_ext)):
            name += '.' + lang
        return name + '.' + self._OUTPUT_FILE_EXT
    
    def _export_resource(self, resource, dir):
        infile = resource.src_file()
        if resource.SUBDIR:
            dir = os.path.join(dir, resource.SUBDIR)
        outfile = os.path.join(dir, resource.filename())
        if infile is None:
            data = resource.get()
            if data is not None:
                created = not os.path.exists(outfile)
                self._write_file(outfile, data)
                if created:
                    log("%s: file created.", outfile)
        elif (not os.path.exists(outfile) or
              os.path.exists(infile) and os.path.getmtime(outfile) < os.path.getmtime(infile)):
            if not os.path.isdir(os.path.dirname(outfile)):
                os.makedirs(os.path.dirname(outfile))
            input_format = os.path.splitext(infile)[1].lower()[1:]
            output_format = os.path.splitext(outfile)[1].lower()[1:]
            if input_format == output_format:
                shutil.copyfile(infile, outfile)
                log("%s: file copied.", outfile)
            else:
                if input_format != 'wav':
                    raise Exception("Unsupported conversion: %s -> %s" %
                                    (input_format, output_format))
                var = 'LCG_%s_COMMAND' % output_format.upper()
                def cmd_err(msg):
                    info = "Specify a command encoding %s file '%%infile' to %s file '%%outfile'."
                    raise Exception(msg % var + "\n" + info % (input_format, output_format))
                try:
                    cmd = os.environ[var]
                except KeyError:
                    cmd_err("Environment variable %s not set.")
                if cmd.find("%infile") == -1 or cmd.find("%outfile") == -1:
                    cmd_err("Environment variable %s must refer to '%%infile' and '%%outfile'.")
                log("%s: converting to %s: %s", outfile, output_format, cmd)
                command = cmd.replace('%infile', infile).replace('%outfile', outfile)
                if os.system(command):
                    raise IOError("Subprocess returned a non-zero exit status.")
    
    def dump(self, node, directory, filename=None, variant=None, recursive=False,
             **kwargs):
        """Write node's content into the output file.

        Arguments:

           node -- the 'ContentNode' instance to dump.
           directory -- name of the destination directory as a string.
           filename -- the name of the output file as a string.  If None, the
             name will be determined automatically based on the node id and
             corresponding language and file type suffix.
           variant -- the language variant to write.  The value must be the ISO
             language code corresponding to one of the node's available
             language variants.  If None, all available variants will be
             written.
           recursive -- iff true, perform recursive export, i.e. export the
             whole set of documents

        All other keyword arguments will be passed to the exporter context
        constructor (See the .

        """
        variants = variant and (variant,) or node.variants() or (None,)
        for lang in variants:
            context = self.context(node, lang, **kwargs)
            export_kwargs = {}
            if recursive:
                export_kwargs['recursive'] = True
            data = context.localize(self.export(context, **export_kwargs))
            if filename:
                fn = filename
            else:
                fn = self._filename(node, context)
            self._write_file(os.path.join(directory, fn), data)


class UnsupportedElementType(Exception):
    def __init__(self, element_type):
        msg = "Element type not supported by the exporter: %s" % element_type
        super(UnsupportedElementType, self).__init__(msg)


class TextExporter(FileExporter, Exporter):
    _OUTPUT_FILE_EXT = 'text'
