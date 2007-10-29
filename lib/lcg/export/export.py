# -*- coding: utf-8 -*-
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

"""Course exporter."""

from lcg import *

        
class Generator(object):
    
    def __init__(self, exporter):
        self._exporter = exporter
        
        
class MarkupFormatter(object):
    """Simple inline ascii markup formatter.

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
               ('link', (r'\[(?:(?P<xresource>Resource):)?'
                         r'(?P<href>[^\[\]\|\#\s]*)'
                         r'(?:#(?P<anchor>[^\[\]\|\s]*))?'
                         r'(?:(?:\||\s+)(?P<label>[^\[\]]*))?\]')),
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
    _HELPER_PATTERNS = ('href', 'anchor', 'label', 'xresource', 'subst')

    _FORMAT = {}

    def __init__(self, exporter):
        self._exporter = exporter
        regexp = r"(?P<%s>\\*%s)"
        pair_regexp = '|'.join((regexp % ("%s_end",   r"(?<=\S)%s(?!\w)"),
                                regexp % ("%s_start", r"(?<!\w)%s(?=\S)")))
        regexps = [isinstance(markup, str)
                   and regexp % (type, markup)
                   or pair_regexp % (type, markup[1], type, markup[0])
                   for type, markup in self._MARKUP]
        self._rules = re.compile('(?:' +'|'.join(regexps)+ ')',
                                 re.MULTILINE|re.UNICODE)
        self._paired_on_output = [type for type, format in self._FORMAT.items()
                                  if isinstance(format, tuple)]

    def _markup_handler(self, parent, match):
        type = [key for key, m in match.groupdict().items()
                if m and not key in self._HELPER_PATTERNS][0]
        markup = match.group(type)
        backslashes = markup.count('\\')
        markup = markup[backslashes:]
        prefix = backslashes / 2 * '\\'
        if backslashes % 2:
            return prefix + markup
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
            result = self._formatter(parent, type, match.groupdict(), close=True)
        elif not end and not (start and type in self._open):
            # Start markup or an unpaired markup.
            if start:
                self._open.append(type)
            result = self._formatter(parent, type, match.groupdict())
        else:
            # Markup in an invalid context is just printed as is.
            # This can be end markup, which was not opened or start markup,
            # which was already opened.
            result = markup
        return prefix + result

    def _substitution_formatter(self, parent, subst, **kwargs):
        # get the substitution value for _SUBSTITUTION_REGEX match
        if subst.startswith('{') and subst.endswith('}'):
            text = subst[1:-1]
        else:
            text = subst
        if not text:
            return '$' + subst
        result = parent.globals()
        for name in text.split('.'):
            try:
                result = result[name]
            except KeyError:
                return '$' + subst
        return str(result)

    def _formatter(self, parent, type, groups, close=False):
        try:
            formatter = getattr(self, '_'+type+'_formatter')
        except AttributeError:
            f = self._FORMAT[type]
            return type in self._paired_on_output and f[close and 1 or 0] or f
        return formatter(parent, close=close, **groups)
        
    def format(self, parent, text):
        self._open = []
        result = []
        pos = 0
        for match in self._rules.finditer(text):
            result.extend((text[pos:match.start()], self._markup_handler(parent, match)))
            pos = match.end()
        result.append(text[pos:])
        self._open.reverse()
        x = self._open[:]
        for type in x:
            result.append(self._formatter(parent, type, {}, close=True))
        return concat(result)


class Exporter(object):

    _GENERATOR = Generator
    _FORMATTER = MarkupFormatter
    
    def __init__(self, translator=None):
        self._translator = translator or NullTranslator()
        self._generator = self._GENERATOR(self)
        self._formatter = self._FORMATTER(self)

    def translate(self, text):
        return self._translator.translate(text)
    
    def generator(self):
        return self._generator

    def format(self, parent, text):
        """Format formatted text using the current formatter."""
        if text:
            return self._formatter.format(parent, text)
        else:
            return ''
    
    def export(self, node):
        """Return the exported node as a string."""

