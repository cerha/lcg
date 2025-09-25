# -*- coding: utf-8 -*-

# Copyright (C) 2004-2016 OUI Technology Ltd.
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

"""Framework for exporting LCG content into various output formats.

The module contains the following important classes:

  'Exporter' :: Generic exporter class defining the common interface that must
    be supported by derived exporters for particular output formats.

See documentation of the individual classes for more details.

"""
from __future__ import unicode_literals
from __future__ import division
from builtins import range
from past.utils import old_div

from contextlib import contextmanager
import os
import re
import shutil
import sys

import lcg

_ = lcg.TranslatableTextFactory('lcg')

unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


INFO = 'INFO'
"""Constant denoting informational messages for 'kind' argument of 'Exporter.Context.log()'."""
WARNING = 'WARNING'
"""Constant denoting warning messages for 'kind' argument of 'Exporter.Context.log()'."""
ERROR = 'ERROR'
"""Constant denoting error messages for 'kind' argument of 'Exporter.Context.log()'."""


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
    _RE_MARKER_MATCHER = re.compile(u'[\ue000-\uffff]')
    _TOC_MARKER_CHAR = u'\ue000'
    _HFILL = u'\ue001\ue001\ue001'
    _END_MARKER_CHAR = u'\n'

    MATPLOTLIB_RESCALE_FACTOR = 1
    """Hack to improve matplotlib output in PDF.  See 'PDFExporter.MATPLOTLIB_RESCALE_FACTOR'."""

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
              log -- external logging function for export progress messages.
                If passed, it must be a callable object with the same arguments
                as the 'log()' method of this class.  This function will be
                called during export.  If not passed, the default logging
                function will store all messages internally and these massages
                can be later obtained using the method 'messages()'.

            The constructor should not be called directly.  Use the method
            'context()' instead.

            """
            self._exporter = exporter
            self._node = node
            self._toc_markers = {}
            self._secondary_language_active = False
            self.position_info = []
            self._init_kwargs(lang=lang, **kwargs)
            self._page_heading = None
            self.list_level = 0
            self.max_list_level = 0
            self.text_preprocessor = None
            self.toc_elements = ()

        def _init_kwargs(self, lang, sec_lang=None, log=None, presentation=None, timezone=None,
                         text_preprocessor=None):
            self._lang = lang
            self._sec_lang = sec_lang
            if log is not None:
                assert callable(log)
                self._messages = None
                self._log = log
            else:
                self._messages = []
                self._log = self._default_logging_function
            self._presentation = presentation
            self._localizer = self._exporter.localizer(lang, timezone=timezone)
            self._text_preprocessor = text_preprocessor

        def _default_logging_function(self, message, kind=INFO):
            assert kind in (ERROR, WARNING, INFO)
            assert isinstance(message, basestring)
            self._messages.append((kind, message))

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

        @contextmanager
        def let_lang(self, lang):
            old_lang = self._lang
            if lang is not None:
                self._lang = lang
            try:
                yield None
            finally:
                self._lang = old_lang

        def node(self):
            return self._node

        def locale_data(self):
            return self._localizer.locale_data()

        def timezone(self):
            return self._localizer.timezone()

        def localize(self, text):
            return self._localizer.localize(text)

        translate = localize  # For backwards compatibility...

        def presentation(self):
            return self._presentation

        def resource(self, filename, **kwargs):
            if 'warn' not in kwargs:
                kwargs['warn'] = lambda m: self.log(m, kind=WARNING)
            return self._node.resource(filename, **kwargs)

        def uri(self, target, **kwargs):
            return self._exporter.uri(self, target, **kwargs)

        def toc_element(self, marker):
            return self._toc_markers[marker]

        def add_toc_marker(self, element):
            marker = unistr(len(self._toc_markers))
            self._toc_markers[marker] = element
            return marker

        def page_heading(self):
            return self._page_heading

        def set_page_heading(self, heading):
            self._page_heading = heading

        def log(self, message, kind=INFO):
            """Record error or important information about the export progress.

            This method should be used by export backends to report problems,
            errors or important information about the progress of the export.
            This information will be displayed to the user who invoked the
            export.  It should typically inform the user about the problems
            which occured in the input data possibly in connection with export
            paramaters or features supported by given exporter.

            The kind can be one of following lcg constants:

              'lcg.ERROR' -- for problems which make the output or its parts
                unusable or significantly damaged.

              'lcg.WARNING' -- for minor or potential problems which don't make the
                output unusable, but may require some attention.

              'lcg.INFO' -- to display information about normal export progress.

            The problems are typically also visibly marked within the output,
            but it would be hard to detect them for the user without logging as
            it would require reading through the whole output.  The logged
            messages thus serve as a summary of problems.

            """
            position = ' / '.join(self.position_info)
            if position:
                message = position + ': ' + message
            self._log(message, kind=kind)

        def messages(self):
            """Return all messages logged during the export through the 'log()' method.

            Return a tuple of pairs (KIND, MESSAGE) corresponding to the
            relevant 'log()' method arguments.  Returns None when the argument
            'log' is passed to the constructor (logging is performed through an
            external function).

            """
            return self._messages

    def __init__(self, translations=()):
        self._translation_path = translations
        self._export_method = self._define_export_methods()

    def _uri_node(self, context, node, lang=None):
        return node.id()

    def _uri_section(self, context, section, local=False):
        result = "#" + section.id()
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
        return {lcg.Content: self._export_content,
                lcg.HorizontalSeparator: self._export_horizontal_separator,
                lcg.NewPage: self._export_new_page,
                lcg.NewLine: self._export_new_line,
                lcg.PageNumber: self._export_page_number,
                lcg.PageHeading: self._export_page_heading,
                lcg.Title: self._export_title,
                lcg.HSpace: self._export_hspace,
                lcg.VSpace: self._export_vspace,
                lcg.Strong: self._export_strong,
                lcg.Emphasized: self._export_emphasized,
                lcg.Underlined: self._export_underlined,
                lcg.Code: self._export_code,
                lcg.Citation: self._export_citation,
                lcg.Quotation: self._export_quotation,
                lcg.Superscript: self._export_superscript,
                lcg.Subscript: self._export_subscript,
                lcg.TextContent: self._export_text_content,
                lcg.PreformattedText: self._export_preformatted_text,
                lcg.Abbreviation: self._export_abbreviation,
                lcg.Anchor: self._export_anchor,
                lcg.Container: self._export_container,
                lcg.Paragraph: self._export_paragraph,
                lcg.Link: self._export_link,
                lcg.Section: self._export_section,
                lcg.Heading: self._export_heading,
                lcg.TableOfContents: self._export_table_of_contents,
                lcg.ItemizedList: self._export_itemized_list,
                lcg.DefinitionList: self._export_definition_list,
                lcg.FieldSet: self._export_field_set,
                lcg.Table: self._export_table,
                lcg.TableRow: self._export_table_row,
                lcg.TableCell: self._export_table_cell,
                lcg.TableHeading: self._export_table_heading,
                lcg.InlineImage: self._export_inline_image,
                lcg.InlineAudio: self._export_inline_audio,
                lcg.InlineVideo: self._export_inline_video,
                lcg.InlineExternalVideo: self._export_inline_external_video,
                lcg.SetVariable: self._export_set_variable,
                lcg.Substitution: self._export_substitution,
                lcg.MathML: self._export_mathml,
                lcg.Figure: self._export_figure,
                lcg.Exercise: self._export_exercise,
                lcg.Exercise: self._export_exercise,
                lcg.InlineSVG: self._export_inline_svg,
                }

    def _export(self, node, context, recursive=False):
        context.position_info.append(node.heading().text())
        try:
            heading = node.heading().export(context)
            newline = self._newline(context, 2)
            content = node.content(context.lang()).export(context)
            if recursive:
                # FIXME: The context should be cloned here with the correct node in
                # it, but it doesn't seem to matter in Braille output, which is
                # currently the only use case for the recursive export.  When
                # cloned, the new context should be passed the 'log' argument
                # to forward logging to the root context (log=context.log).
                content = self.concat(content,
                                      *[self._export(n, context, recursive=True)
                                        for n in node.children()])
            exported = self.concat(heading, newline, content)
            return self._adjusted_export(context, exported)
        finally:
            context.position_info.pop()

    def _adjusted_export(self, context, exported):
        return exported

    def uri(self, context, target, **kwargs):
        """Return the URI of the target as string.

        Arguments:

          context -- exporting object created in the 'context' method and
            propagated from the 'export' method
          target -- URI target that can be one of: 'ContentNode', 'Section',
            'Link.ExternalTarget' or 'lcg.Resource' instance

        """
        if isinstance(target, lcg.ContentNode):
            method = self._uri_node
        elif isinstance(target, lcg.Section):
            method = self._uri_section
        elif isinstance(target, lcg.Resource):
            method = self._uri_resource
        elif isinstance(target, lcg.Link.ExternalTarget):
            method = self._uri_external
        else:
            raise Exception("Invalid URI target:", target)
        return method(context, target, **kwargs)

    def localizer(self, lang, timezone=None):
        """Return a 'lcg.Localizer' instance for given language and time zone."""
        return lcg.Localizer(lang, timezone=timezone, translation_path=self._translation_path)

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
        exported = method(context, element)
        if element in context.toc_elements:
            toc_marker = context.add_toc_marker(element)
            exported = self.concat(self._marker(self._TOC_MARKER_CHAR, toc_marker), exported)
        return exported

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
        return lcg.concat(*items)

    def text(self, context, text, lang=None, reformat=False):
        """Return exported 'text'.

        Arguments:

          context -- current 'Context' instance
          text -- text to convert; unicode
          lang -- target language as an ISO 639-1 Alpha-2 lowercase
            language code or 'None'
          reformat -- iff true, make some 'text' sanitization

        """
        assert isinstance(text, basestring), text
        if reformat:
            text = self._reformat_text(context, text)
        elif self._text_mark(text):
            return ''
        if context.text_preprocessor is not None:
            text = context.text_preprocessor(text)
        if isinstance(text, lcg.Localizable):
            text = context.localize(text)
        return self.escape(text)

    def _reformat_text(self, context, text):
        text = context.localize(text)
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        text = self._RE_MARKER_MATCHER.sub('', text)  # prevent crashes on marker chars in input
        text = self._RE_SPACE_MATCHER.sub(' ', text)
        return text

    def _newline(self, context, number=1, soft=False, page_start=None, page_end=False):
        return u'\n' * number

    def _ensure_newlines(self, context, exported, number=1):
        real_number = 0
        while (real_number < number and len(exported) > real_number and
               exported[-real_number - 1] == '\n'):
            real_number += 1
        return exported + '\n' * (number - real_number)

    def _space(self, context, number=1):
        return u' ' * number

    def _indent(self, exported, indentation, init_indentation=None, no_page_break=False,
                first_indented=0, restart=False):
        if init_indentation is None:
            init_indentation = indentation
        lines = exported.split('\n')
        if lines:
            space = u' ' * indentation
            lines = (lines[:first_indented] +
                     [u' ' * init_indentation + lines[first_indented]] +
                     [space + l if l else '' for l in lines[first_indented + 1:]])
        return '\n'.join(lines)

    def _list_item_prefix(self, context, lang=None):
        return u'• '

    def _separator(self, context, lang=None):
        return self.text(context, u' — ', lang=lang)

    def _marker(self, marker, argument=''):
        return u'%s%s%s' % (marker, argument, self._END_MARKER_CHAR,)

    def _text_mark(self, text):
        if text:
            char = text[0]
            char_code = ord(char)
            if 57344 <= char_code and char_code <= 63743:
                return char, text[1:]
        return None

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
        return self.text(context, element.text(), lang=element.lang(), reformat=True)

    def _export_abbreviation(self, context, element):
        """Export the given 'Abbreviation' element.

        In this class the method just returns the escaped anchor text.

        """
        return self._export_text_content(context, element)

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

    def _export_horizontal_separator(self, context, element, width=64):
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
                extra.append(self.text(context, u' ' + source, lang=lang, reformat=True))
            if uri:
                format_ = u' (%s)' if source else u' %s'
                extra.append(self.text(context, format_ % (uri,), lang=lang, reformat=True))
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
            item = parent.find_section(context.lang(), id)
            if not item:
                item = parent.root().find_node(id)
        if item:
            title = item.title()
        else:
            title = id
        return self.text(context, title, lang=element.lang(), reformat=True)

    def _export_preformatted_text(self, context, element):
        """Export verbatim text of given 'lcg.PreformattedText' element.

        In this class the method returns just the escaped element text.

        """
        text = element.text()
        lang = element.lang()
        text_lines = text.split('\n')
        text_lines = [self._RE_MARKER_MATCHER.sub('', l) for l in text_lines]
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
        value = context.node().global_(unistr(names[0]))
        for xname in names[1:]:
            if value is None:
                break
            if isinstance(value, SubstitutionIterator):
                value = value.value()
            key = unistr(xname)
            dictionary = value
            try:
                value = value.get(key)
            except Exception:
                dictionary = None
                break
            if callable(value):
                value = value()
                # It is necessary to store the computed value in order to
                # prevent repeated object initializations in it.  Otherwise it
                # fails e.g. with substitution iterators.
                dictionary[key] = value
        if value is None:
            result = self.escape(element.markup())
        elif isinstance(value, lcg.Content):
            result = value.export(context)
        else:
            if not isinstance(value, lcg.Localizable):
                value = unistr(value)
            result = self.escape(value)
        return result

    def _export_set_variable(self, context, element):
        """Set node variable defined by 'element'.

        The method returns export of an empty content.

        """
        context.node().set_global(element.name(), element.value(), top=True)
        return self._export_content(context, lcg.Content())

    # Container elements

    def _export_container(self, context, element):
        """Export given 'lcg.Container' element.

        In this class the method exports the contained content elements and concatenates them.

        """
        exported = []
        for content in element.content():
            if isinstance(content, (lcg.ItemizedList, lcg.DefinitionList)) and exported:
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
            if isinstance(target, (lcg.ContentNode, lcg.Section)):
                label = self._transform_link_heading(context, target.heading())
            elif isinstance(target, lcg.Resource):
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
        context.position_info.append(element.title())
        try:
            return self.concat(self._marker(self._TOC_MARKER_CHAR, toc_marker),
                               self.text(context, element.title(), element.lang(), reformat=True),
                               self._newline(context, 2),
                               self._export_container(context, element))
        finally:
            context.position_info.pop()

    def _export_heading(self, context, element):
        """Export given 'Heading' element."""
        return self._export_container(context, element)

    def _export_itemized_list(self, context, element, lang=None):
        """Export given 'ItemizedList' element."""
        numbering = element.order()
        letters = u'abcdefghijklmnopqrstuvwxyz'
        n_letters = len(letters)
        item_number = [1]

        def number():
            n = item_number[0]
            item_number[0] += 1
            if numbering == lcg.ItemizedList.NUMERIC:
                result = u'%d. ' % (n,)
                exported = self.text(context, result, lang=lang)
            elif numbering in (lcg.ItemizedList.LOWER_ALPHA, lcg.ItemizedList.UPPER_ALPHA,):
                result = letters[(n - 1) % n_letters]
                while n > n_letters:
                    n = old_div(n, n_letters)
                    result = letters[(n - 1) % n_letters] + result
                if numbering == lcg.ItemizedList.UPPER_ALPHA:
                    result = result.upper()
                result += u'. '
                exported = self.text(context, result, lang=lang)
            else:
                exported = self._list_item_prefix(context, lang=lang)
            return exported
        list_level = context.list_level + 1
        if list_level == 1:
            def level(element):
                if isinstance(element, lcg.Container) and element.content():
                    result = max([level(c) for c in element.content()])
                    if isinstance(element, lcg.ItemizedList):
                        result += 1
                else:
                    result = 0
                return result
            max_list_level = level(element)
        else:
            max_list_level = context.max_list_level
        content = []
        with lcg.attribute_value(context, 'list_level', list_level):
            with lcg.attribute_value(context, 'max_list_level', max_list_level):
                element_content = element.content()
                no_page_break = len(element_content) > 1
                indentation = max_list_level * 2
                init_indentation = (list_level - 1) * 2
                for c in element_content:
                    content.append(self._indent(number(), indentation, init_indentation,
                                                no_page_break=no_page_break, restart=True))
                    no_page_break = False
                    exported = c.export(context)
                    exported = self._indent(exported, indentation, init_indentation,
                                            first_indented=1, restart=True)
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
        """Export given 'lcg.Paragraph' element."""
        items = [self._export_container(context, element),
                 self._newline(context)]
        if context.list_level == 0:
            items.append(self._newline(context, soft=True))
        return self.concat(*items)

    def _export_table_of_contents(self, context, element):
        """Generate a Table of Contents for given 'lcg.TableOfContents' element."""
        lang = element.lang()
        presentation_set = context.presentation()
        presentation = presentation_set and presentation_set.presentation(None, lang)
        page_width = presentation and presentation.page_width
        item_list = []
        node_list = context.toc_elements = []

        def export(items):
            for node, subitems in items:
                node_list.append(node.heading() if isinstance(node, lcg.ContentNode) else node)
                current_lang = (node.lang() or lang)
                if isinstance(node, lcg.Section):
                    item_list.append(self.text(context, node.title(), lang=current_lang,
                                               reformat=True))
                else:
                    item_list.append(node.export(context))
                item_list.append(self.text(context, self._HFILL if page_width else ' '))
                item_list.append(self.text(context, node.page_number(), lang=current_lang))
                item_list.append(self._newline(context))
                if subitems:
                    export(subitems)
        items = []

        def add_item(node, subitems):
            if isinstance(node, lcg.ContentNode):
                items.append((node.heading(), (),))
            else:
                items.append((node, subitems,))
        for node, subitems in element.items(context.lang()):
            add_item(node, subitems)
        export(items)
        result = self.concat(self.concat(*item_list),
                             self._newline(context))
        title = element.title()
        if title:
            result = self.concat(self.text(context, element.title(), lang=lang, reformat=True),
                                 self._newline(context, 2),
                                 result)
        return result

    # Tables

    def _export_table(self, context, element):
        """Export given 'Table' element."""
        content = element.content()
        heading_present = False
        if content:
            row_content = content[0].content()
            if row_content and isinstance(row_content[0], lcg.TableHeading):
                heading_present = True
        separator = lcg.HorizontalSeparator()
        vertical_separator = self._vertical_cell_separator(context, 1)
        first_vertical_separator = self._vertical_cell_separator(context, 0)
        last_vertical_separator = self._vertical_cell_separator(context, -1)
        try:
            n_cells = max([len(row.content()) for row in content if isinstance(row, lcg.TableRow)])
        except ValueError:
            raise Exception("No row found in the table", content)
        widths = [0] * n_cells
        total_width = len(first_vertical_separator) + len(last_vertical_separator)
        if widths:
            total_width += len(vertical_separator) * (len(widths) - 1)
        table_intro = self._set_table_column_widths(context, element, total_width, widths)
        total_width += sum(widths)
        item_list = []
        if table_intro:
            item_list.append(table_intro)
        item_list.append(self._newline(context, number=0, page_start=1))
        exported_rows = []
        for row in content:
            if row.line_above():
                exported_rows.append(separator)
            exported_rows.append(row.export(context))
            if row.line_below():
                exported_rows.append(separator)
        n_real_rows = len(content)
        last_row = None
        n = 0
        for row in exported_rows:
            if isinstance(row, list):
                if n > 0:
                    item_list.append(self._newline(context, number=0, page_start=2))
                n += 1
                last_row = row
                if n_cells > 0:
                    item_list.append(first_vertical_separator)
                for i in range(n_cells):
                    if i < len(row):
                        cell = row[i]
                    else:
                        cell = self.text(context, '')
                    item_list.append(cell)
                    space = self._space(context, widths[i] - len(cell))
                    item_list.append(self.text(context, space))
                    if i == n_cells - 1:
                        item_list.append(last_vertical_separator)
                    else:
                        item_list.append(vertical_separator)
                item_list.append(self._newline(context))
            elif row is separator:
                row_number = -1 if n == n_real_rows else n
                s = self._table_row_separator(context, total_width, widths, row_number,
                                              vertical_separator, last_row, heading_present)
                if s is not None:
                    item_list.append(s)
            else:
                item_list.append(row)
        item_list.append(self._newline(context, soft=True, page_end=True))
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

    def _vertical_cell_separator(self, context, position):
        if position == 0:
            return u'│ '
        elif position == -1:
            return u' │'
        else:
            return u' │ '

    def _table_row_separator(self, context, width, cell_widths, outer, vertical_separator,
                             last_row, heading_present):
        return self._export_horizontal_separator(context, None, width=width)

    def _table_cell_width(self, context, table, cell):
        return len(cell)

    def _set_table_column_widths(self, context, element, extra_width, widths):
        exported_rows = [r.content() for r in element.content() if isinstance(r, lcg.TableRow)]
        for row in exported_rows:
            if isinstance(row, (tuple, list)):
                for i in range(len(row)):
                    cell_width = self._table_cell_width(context, element, row[i].export(context))
                    widths[i] = max(widths[i], cell_width)
        return None

    # Media (represented by resources wrapped in inline content elements)

    def _inline_export(self, context, element, resource, lang=None):
        label = element.title()
        if label is None and resource is not None:
            label = resource.title() or resource.filename()
        if resource is not None:
            descr = resource.descr()
            if descr:
                label = '%s (%s)' % (label, descr,)
        exported = self.text(context, label, lang=lang, reformat=True)
        exported = self._ensure_newlines(context, exported)
        return exported

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

    # Exercises

    def _export_exercise(self, context, element):
        content = [self._newline(context, 0, page_start=1)]
        # Instructions
        instructions = element.instructions()
        if instructions:
            content.append(self.concat(instructions.export(context),
                                       self._newline(context, 1, page_start=3)))
        # Tasks
        fill_in_char = u'_'
        fill_in_area = fill_in_char * 4

        def choice_text(task, choice, show_answers):
            if not show_answers or choice.correct():
                return self.text(context, choice.answer(), reformat=True)
            else:
                return None

        def format_choices(task, show_answers):
            choices = []
            for c in task.choices():
                output = choice_text(task, c, show_answers)
                if output is not None:
                    choices.append(output)
            choices_nl = []
            for c in choices[:-1]:
                choices_nl.append(c)
                choices_nl.append(self._newline(context))
            if choices:
                choices_nl.append(choices[-1])
            return self.concat(*choices_nl)

        def format_task_text(context, task, field_maker):
            text = task.text()
            if text:
                def make_field(answer, label, word_start, word_end):
                    return word_start + field_maker(context, task, answer) + word_end
                text = task.substitute_fields(text.replace('[', r'\['), make_field)
                content = lcg.Parser().parse_inline_markup(text)
                text = context.localize(content.export(context))
            else:
                text = self.text(context, '')
            return text

        def make_field(show_answers, context, task, text):
            if show_answers:
                result = fill_in_char + self._reformat_text(context, text) + fill_in_char
            else:
                result = fill_in_area
            return result

        def export_task_parts(task, show_answers):
            # if isinstance(element, lcg.WritingTest):
            #    return (None if show_answers else self.text(context, fill_in_area),)
            if isinstance(element, lcg.FillInExercise):
                if task.has_fields_in_text():
                    text = format_task_text(context, task,
                                            lambda *args: make_field(show_answers, *args))
                else:
                    text = self.text(context,
                                     make_field(show_answers, context, task, task.text()))
                if not show_answers and task.prompt():
                    prompt = context.localize(task.prompt().export(context))
                    prompt = self._ensure_newlines(context, prompt)
                    if isinstance(element, lcg.VocabExercise):
                        separator = self.text(context, ' ')
                    else:
                        separator = self._newline(context)
                    result = (self.concat(prompt, separator, text),)
                else:
                    result = (text,)
                return result
            elif isinstance(element, lcg.HiddenAnswers):
                if show_answers:
                    result = (task.answer().export(context),)
                else:
                    result = (task.prompt().export(context),)
                return result
            elif isinstance(element, lcg.GapFilling):
                gap_matcher = re.compile(r"(___+)")

                def text_preprocessor(text):
                    if show_answers:
                        for c in task.choices():
                            if c.correct():
                                replacement = fill_in_char + c.answer() + fill_in_char
                                break
                        else:
                            raise Exception("No correct answer found", text)
                    else:
                        replacement = fill_in_area
                    return gap_matcher.sub(replacement, text)
                with lcg.attribute_value(context, 'text_preprocessor', text_preprocessor):
                    task_prompt = task.prompt()
                    prompt = context.localize(task_prompt.export(context))
                prompt = self._ensure_newlines(context, prompt)
                if show_answers:
                    result = (prompt,)
                else:
                    result = (prompt, format_choices(task, show_answers),)
                return result
            else:
                result = []
                if not show_answers:
                    prompt = task.prompt()
                    if prompt:
                        prompt = context.localize(prompt.export(context))
                        prompt = self._ensure_newlines(context, prompt)
                        result.append(prompt)
                result.append(format_choices(task, show_answers))
                return result

        def export_task(task):
            def add_part(with_answers, add_page_start):
                parts = [p for p in export_task_parts(task, with_answers) if p is not None]
                result = []
                if parts:
                    last_part = parts[-1]
                    for p in parts:
                        page_start = 2 if add_page_start and p is last_part else None
                        result.append(self.concat(p, self._newline(context, page_start=page_start)))
                return result
            with_answers = add_part(True, True)
            result = add_part(False, not with_answers)
            if with_answers:
                result.append(self.text(context, u'-----------------'))
                result.append(self._newline(context, page_start=3))
                result.append(self.concat(*with_answers))
            return self.concat(*result)
        exported_tasks = [context.localize(export_task(task)) for task in element.tasks()]
        template = element.template()
        if template:
            exported_template = context.localize(template.export(context))
            exported_tasks = exported_template % tuple(exported_tasks)
        else:
            separated_tasks = []
            numbered = len(exported_tasks) > 1
            n = 1
            for t in exported_tasks:
                if numbered:
                    separated_tasks.append(self.text(context, u'%d. ' % (n,)))
                    n += 1
                separated_tasks.append(t)
                separated_tasks.append(self._newline(context))
            exported_tasks = self.concat(*separated_tasks)
        if exported_tasks is not None:
            content.append(exported_tasks)
        content.append(self._newline(context, 0, page_end=True))
        return self.concat(*content)

    # Special constructs

    def _export_mathml(self, context, element):
        """Export 'MathML' element.

        In this class the method returns the raw MathML content.

        """
        return element.content()

    def _export_inline_svg(self, context, element):
        return element.svg(context)


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
        if isinstance(content, unistr):
            content = content.encode('utf-8')
        file = open(filename, 'wb')
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
                    lcg.log(_("%s: file created.", outfile))
        elif (not os.path.exists(outfile) or
              os.path.exists(infile) and os.path.getmtime(outfile) < os.path.getmtime(infile)):
            if not os.path.isdir(os.path.dirname(outfile)):
                os.makedirs(os.path.dirname(outfile))
            shutil.copyfile(infile, outfile)
            lcg.log(_("%s: file copied.", outfile))

    def dump(self, node, directory, filename=None, variant=None, recursive=False,
             **kwargs):
        """Write node's content into the output file.

        Arguments:

           node -- the 'lcg.ContentNode' instance to dump.
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
            for kind, message in context.messages():
                sys.stderr.write('%s: %s\n' % (kind, message,))


class UnsupportedElementType(Exception):

    def __init__(self, element_type):
        msg = "Element type not supported by the exporter: %s" % element_type
        super(UnsupportedElementType, self).__init__(msg)


class TextExporter(FileExporter, Exporter):
    _OUTPUT_FILE_EXT = 'text'

    def _adjusted_export(self, context, exported):
        return '\n'.join([line for line in exported.split('\n')
                          if self._text_mark(line) is None])
