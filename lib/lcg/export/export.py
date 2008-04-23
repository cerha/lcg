# -*- coding: utf-8 -*-
#
# Copyright (C) 2004-2008 Brailcom, o.p.s.
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

"""Framework for exporting structured content into output formats.

The framework consists of the following parts:

  'Generator' :: 

  'MarkupFormatter' :: 

  'Exporter' :: This is the top exporting class that exports structured text
    into the output format.

See documentation of the particular classes for more details.

"""

from lcg import *

        
class Generator(object):

    # Basic utilitites

    def escape(self, text):
        """Escape 'text' for the output format and return the resulting string.

        In this class the method returns value of 'text'.
        
        """
        return text

    # Text styles

    def pre(self, text):
        """Return 'text' in a verbatim form.

        In this class the method returns value of 'text'.
        
        """
        return text

    def emphasize(self, text):
        """Return exported 'text' emphasized.

        In this class the method returns value of 'text'.
        
        """
        return text

    def strong(self, text):
        """Return exported 'text' in a bold face.

        In this class the method returns value of 'text'.
        
        """
        return text

    def fixed(self, text):
        """Return exported 'text' in a fixed width font.

        In this class the method returns value of 'text'.
        
        """
        return text
     
    def sup(self, text):
        """Return exported 'text' as a superscript.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def sub(self, text):
        """Return exported 'text' as a subscript.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def underline(self, text):
        """Return exported 'text' underlined.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def citation(self, text):
        """Return exported 'text' as ???.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def quotation(self, text):
        """Return exported 'text' as ???.

        In this class the method returns value of 'text'.
        
        """
        return text

    # Sectioning

    def h(self, title, level):
        """Return heading.

        Arguments:

          title -- exported title of the heading
          level -- level of the heading as a positive integer; the highest
            level is 1

        In this class the method returns value of 'title' separated by empty
        lines.
        
        """
        return '\n' + title + '\n\n'
    
    def list(self, items, ordered=False, style=None, lang=None):
        """Return list of 'items'.

        Arguments:

          items -- sequence of previously exported objects
          ordered, style -- list item markup style; if 'ordered' is true,
            markup for ordered list should be chosen, then 'style' can further
            specify the style, its valid values are 'None' and the string
            'lower-alpha'
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code
        
        In this class method returns concatenation of 'items' elements
        surrounded by new lines.

        """
        items_nl = []
        for i in items:
            items_nl += [i, '\n']
        return self.concat(items_nl)

    def definitions(self, items, lang=None):
        """Return a list of definitions.

        Arguments:

          items -- sequence of '(TERM, DESCRIPTION)' pairs as tuples of
            previously exported objects
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method calls 'fset' on 'items'.
        
        """
        return self.fset(items, lang=lang)

    def fset(self, items, lang=None):
        """Return a list of label/value pairs.

        Arguments:

          items -- sequence of (LABEL, VALUE) pairs as tuples of previously exported
            objects
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns a concatenation of 'items' elements.
        
        """
        exported_items = [self.concat(dt, dd, '\n') for dt, dd in items]
        return self.concat(*exported_items)
            
    def p(self, content, lang=None):
        """Return a single paragraph of exported 'content'.

        Arguments:

          content -- already exported content
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns 'content' surrounded by new line
        characters.
        
        """
        return self.concat(content, '\n\n')

    def div(self, content, lang=None, **kwargs):
        """Return exported 'content' as a general block.

        Arguments:

          content -- already exported content
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns 'content' surrounded by new lines.

        """
        return content + '\n'

    def concat(self, *exported):
        """Return elements of 'exported' objects sequence as a general block.

        In this class the method performs simply text concatenation of
        'exported' objects.

        """
        return concat(*exported)
    
    def br(self):
        """Return a newline separator.

        In this class the method returns a new line character.
        
        """
        return '\n'

    def hr(self):
        """Return a horizontal separator.

        In this class the method returns a form feed character.

        """
        return '\f'

    # Links and images
    
    def link(self, label, uri, **kwargs):
        """Return link with 'label' and pointing to 'uri'.

        Arguments:

          label -- exported content of the link
          uri -- the target URI as a string

        In this class the method returns a text created from 'label' and 'uri'.
        
        """
        if label:
            result = self.concat(label, self.escape('(%s)' % (uri,)))
        else:
            result = uri
        return result

    def link_target(self, label, name, **kwargs):
        """Return link target named 'name' and containing 'label' text.

        Arguments:

          label -- exported content to be put into the place of the link target
          name -- name of the link target as a string

        In this class the method returns a text created from 'label' and
        'name'.
          
        """
        return self.escape('%s#%s' % (label, name,))

    def img(src, alt=None, descr=None, align=None, width=None, height=None, **kwargs):
        """Return image stored at 'src' URI.

        Arguments:

          src -- URI (as a string) where the image is stored
          alt -- title of the image as a string or unicode or 'None'
          descr -- ???
          align -- requested alignment of the image, 'None' or one of the
            strings 'left' or 'right'
          width -- ???
          height -- ???

        In this class the method returns text of 'src'.

        """
        return self.escape(src)

    # Tables

    def gtable(self, rows, title=None, lang=None):
        """A generic table consisting of 'rows'.

        Arguments:

          rows -- sequence of rows cells where each row is a sequence of
            previously formatted cells
          title -- 'None' or table caption as a string or unicode
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns a concatenation of 'rows'.

        """
        return self.concat([self.concat(row) for row in rows])


class MarkupFormatter(object):
    """Simple inline ASCII markup formatter.

    This simple formatter can only format the markup within one block (ie. a
    single paragraph or other non-structured piece of text).  Parsing the
    higher level document structure (headings, paragraphs, bullet lists etc.)
    is done on the LCG input.  Formatting the inline markup, on the other hand,
    is done on LCG output (export).

    """
    _MARKUP = (('linebreak', '//'),
               ('emphasize', ('/',  '/')),
               ('strong',    ('\*', '\*')),
               ('fixed',     ('=',  '=')),
               ('underline', ('_',  '_')),
               ('citation',  ('>>', '<<')),
               ('quotation', ('``', "''")),
               ('link', (r'\['
                         r'(?P<href>[^\[\]\|\#\s]*)'
                         r'(?:#(?P<anchor>[^\[\]\|\s]*))?'
                         r'(?:(?:\s*\|\s*|\s+)(?P<label>[^\[\]\|]*))?'
                         r'(?:(?:\s*\|\s*)(?P<descr>[^\[\]]*))?'
                         r'\]')),
               ('uri', r'(https?|ftp)://\S+?(?=[\),.:;]?(\s|$))'),
               ('email', r'\w[\w\-\.]*@\w[\w\-\.]*\w'),
               ('substitution', (r"(?!\\)\$(?P<subst>[a-zA-Z][a-zA-Z_]*(\.[a-zA-Z][a-zA-Z_]*)?" + \
                                 "|\{[^\}]+\})")),
               ('comment', r'^#.*'),
               ('dash', r'(^|(?<=\s))--($|(?=\s))'),
               ('nbsp', '~'),
               ('lt', '<'),
               ('gt', '>'),
               ('amp', '&'),
               )
    _HELPER_PATTERNS = ('href', 'anchor', 'label', 'descr', 'subst')

    _FORMAT = {'linebreak': '\n',
               'comment': '',
               'dash': u'—',
               'nbsp': u' ',
               'lt':   '<',
               'gt':   '>',
               'amp':  '&',
               }

    def __init__(self):
        regexp = r"(?P<%s>\\*%s)"
        pair_regexp = '|'.join((regexp % ("%s_end",   r"(?<=\S)%s(?!\w)"),
                                regexp % ("%s_start", r"(?<!\w)%s(?=\S)")))
        regexps = [isinstance(markup, str) and regexp % (type, markup)
                   or pair_regexp % (type, markup[1], type, markup[0])
                   for type, markup in self._MARKUP]
        self._rules = re.compile('(?:' +'|'.join(regexps)+ ')', re.MULTILINE|re.UNICODE)
        self._paired_on_output = [type for type, format in self._FORMAT.items()
                                  if isinstance(format, tuple)]
    
    def _markup_handler(self, context, match):
        g = context.generator()
        type = [key for key, m in match.groupdict().items()
                if m and not key in self._HELPER_PATTERNS][0]
        markup = match.group(type)
        backslashes = markup.count('\\')
        markup = g.escape(markup[backslashes:])
        prefix = g.escape(backslashes / 2 * '\\')
        if backslashes % 2:
            return g.concat(prefix, markup)
        # We need two variables (start and end), because both can be False for
        # unpaired markup.
        start = False
        end = False
        if type.endswith('_start'):
            type = type[:-6]
            start = True
        elif type.endswith('_end'):
            type = type[:-4]
            end = True
        if not start and self._open and type == self._open[-1]:
            # Closing an open markup.
            self._open.pop()
            result = self._formatter(context, type, match.groupdict(), close=True)
        elif not end and not (start and type in self._open):
            # Start markup or an unpaired markup.
            if start:
                self._open.append(type)
            result = self._formatter(context, type, match.groupdict())
        else:
            # Markup in an invalid context is just printed as is.
            # This can be end markup, which was not opened or start markup,
            # which was already opened.
            result = markup
        return g.concat(prefix, result)

    def _substitution_formatter(self, context, subst, **kwargs):
        g = context.generator()
        # get the substitution value for _SUBSTITUTION_REGEX match
        if subst.startswith('{') and subst.endswith('}'):
            text = subst[1:-1]
        else:
            text = subst
        if not text:
            return g.escape('$' + subst)
        result = context.node().globals()
        for name in text.split('.'):
            try:
                result = result[str(name)]
            except KeyError:
                return g.escape('$' + subst)
        if not isinstance(result, Localizable):
            result = str(result)
        return g.escape(result)
    
    def _link_formatter(self, context, label=None, href=None, anchor=None, descr=None, **kwargs):
        if label:
            result = label
            if href:
                result += ' (%s)' % (href,)
        elif href:
            result = href
        else:
            result = ''
        return result
    
    def _uri_formatter(self, context, uri, close=False, **kwargs):
        return self._link_formatter(context, href=uri, label=None)

    def _formatter(self, context, type, groups, close=False):
        try:
            formatter = getattr(self, '_'+type+'_formatter')
        except AttributeError:
            formatter = None
        if formatter is not None:
            result = formatter(context, close=close, **groups)
        else:
            f = self._FORMAT.get(type, '')
            if type in self._paired_on_output and f:
                if close:
                    text = f[1]
                else:
                    text = f[0]
            else:
                text = f
            g = context.generator()
            result = g.escape(text)
        return result
        
    def format(self, context, text):
        g = context.generator()
        self._open = []
        result = []
        pos = 0
        for match in self._rules.finditer(text):
            starting_text = g.escape(text[pos:match.start()])
            markup = self._markup_handler(context, match)
            result.extend((starting_text, markup))
            pos = match.end()
        final_text = g.escape(text[pos:])
        result.append(final_text)
        self._open.reverse()
        x = self._open[:]
        for type in x:
            result.append(self._formatter(context, type, {}, close=True))
        return g.concat(*result)


class Exporter(object):
    """Transforming structured content objects to various output formats.

    This class is a base class of all transformers.  It provides basic
    exporting framework to be extended and customized for particular kinds of
    outputs.  When defining a real exporter you should assign the 'Generator'
    and 'Formatter' attributes to corresponding utility classes.  The exporter
    instantiates and uses them as needed.

    The exporting process itself is run by subsequent calls of methods
    'context' and 'export'.
    
    """

    Generator = Generator
    Formatter = MarkupFormatter

    class Context(object):
        """Storage class containing complete data necessary for export."""
        def __init__(self, exporter, generator, formatter, translator, node, **kwargs):
            self._exporter = exporter
            self._generator = generator
            self._formatter = formatter
            self._translator = translator
            self._node = node
            self._init_kwargs(**kwargs)

        def _init_kwargs(self, sec_lang=None):
            self._sec_lang = sec_lang
            
        def exporter(self):
            return self._exporter
        
        def generator(self):
            return self._generator
        
        def formatter(self):
            return self._formatter
        
        def lang(self):
            return self._translator.lang()

        def sec_lang(self):
            return self._sec_lang
    
        def node(self):
            return self._node
            
        def translate(self, text):
            return self._translator.translate(text)

    def __init__(self, translations=()):
        self._generator = self.Generator()
        self._formatter = self.Formatter()
        self._translations = translations
        self._translators = {}

    def _translator(self, lang):
        return GettextTranslator(lang, path=self._translations, fallback=True)

    def _uri_document(self, context, target, **kwargs):
        return target.id()

    def _uri_section(self, context, target, **kwargs):
        return '#' + target.anchor()

    def _uri_external(self, context, target, **kwargs):
        return target.uri()
    
    def uri(self, context, target, **kwargs):
        """Return the URI of the target as string.

        Arguments:

          context -- exporting object created in the 'context' method and
            propagated from the 'export' method
          target -- URI target that can be one of: document ('ContentNode'
            instance), section ('Section' instance), external target
            ('Link.ExternalTarget' or 'Resource' instance)

        """
        if isinstance(target, ContentNode):
            method = self._uri_document
        elif isinstance(target, Section):
            method = self._uri_section
        elif isinstance(target, (Link.ExternalTarget, Resource)):
            method = self._uri_external
        else:
            raise Exception("Invalid URI target:", target)
        return method(context, target, **kwargs)

    def context(self, node, lang, **kwargs):
        """Return context to be used as an argument to the 'export' method.

        Arguments:

          node -- 'Content' instance to be exported
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        """
        if lang is None:
            translator = NullTranslator()
        else:
            try:
                translator = self._translators[lang]
            except KeyError:
                translator = self._translators[lang] = self._translator(lang)
        return self.Context(self, self._generator, self._formatter, translator, node, **kwargs)

    def _initialize(self, context):
        generator = context.generator()
        title = generator.escape(context.node().title())
        content = generator.h(title, 1)
        return content

    def _finalize(self, context):
        return ''

    def _export(self, node, context):
        return node.content().export(context)
        
    def export(self, context):
        """Export the object represented by 'context' and return the corresponding output string.

        'context' is an object returned by the 'context' method.

        In this class the method calls 'export' method of the 'context' node
        and returns the result.

        """
        node = context.node()
        initial_export = self._initialize(context)
        export = self._export(node, context)
        final_export = self._finalize(context)
        generator = context.generator()
        result = export
        if initial_export is not None:
            result = generator.concat(initial_export, result)
        if final_export is not None:
            result = generator.concat(result, final_export)
        return result

    def dump(*args, **kwargs):
        """????"""
        pass
