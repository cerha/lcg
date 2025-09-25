# -*- coding: utf-8 -*-

# Copyright (C) 2004-2018 OUI Technology Ltd.
# Copyright (C) 2019-2022, 2025 Tomáš Cerha <t.cerha@gmail.com>
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

from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division
from future import standard_library
from builtins import map

import base64
import io
import random
import re
import sys
import string
import urllib.request
import urllib.parse
import urllib.error
from xml.sax import saxutils

import lcg
from lcg import concat

from . import mathml

_ = lcg.TranslatableTextFactory('lcg')
standard_library.install_aliases()
unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


class HtmlEscapedUnicode(unistr):
    """Escaping wrapper for unicodes.

    In order to prevent display errors, XSS, CSRF, etc., it is necessary to
    HTML escape all strings inserted into the HTML code.  LCG tries to escape
    all incoming strings by default.  This wrapper can and should be used to
    explicitly mark what should be HTML escaped and what not.

    """
    class _EscapingInterpolator(object):

        def __init__(self, interpolator, escape):
            self._interpolator = interpolator
            self._escape = escape

        def __getitem__(self, key):
            return self._escape(self._interpolator[key])

    def __new__(cls, value, escape):
        """
        Arguments:

          value -- unicode to wrap
          escape -- boolean indicating whether the wrapped unicode should be
            HTML escaped or not

        """
        if escape and not isinstance(value, HtmlEscapedUnicode):
            value = saxutils.escape(value)
        return super(HtmlEscapedUnicode, cls).__new__(cls, value)

    def __add__(self, other):
        if isinstance(other, lcg.Localizable):
            result = concat(self, other)
        else:
            result = self.__class__(unistr(self) + unistr(other), escape=False)
        return result

    def __mod__(self, other):
        def escape(x):
            return HtmlEscapedUnicode(x, escape=True) if isinstance(x, basestring) else x
        if isinstance(other, basestring):
            arguments = escape(other)
        elif isinstance(other, (tuple, list)):
            arguments = tuple(map(escape, other))
        elif isinstance(other, dict):
            arguments = dict([(k, escape(v)) for k, v in list(other.items())])
        else:
            # Special dictionary-like object, such as _Interpolator
            arguments = self._EscapingInterpolator(other, escape)
        result = super(HtmlEscapedUnicode, self).__mod__(arguments)
        return HtmlEscapedUnicode(result, escape=False)


class HtmlGenerator(object):
    """Generate HTML tags through a simple Pythonic API.

    Generator produces strings in HTML syntax.  The API methods usually map 1:1
    to HTML tags and their arguments to the attributes.  There are exceptions,
    such as the 'class' HTML attribute which is named 'cls' here to avoid
    conflict with the Python keyword.  The attribute 'for' of the 'label' tag
    is named 'for_' for the same reason.

    There are also a few additional methods, such as 'h()' (allows passing the
    header level as a numeric value) or 'radio()', 'upload()', 'checkbox()' and
    'hidden()' (simplify creation of specific input fields).

    Example usage:

    def _export_something(self, context, element):
        # Generator instance is typically obtained from the export context
        # and aliassed locally as 'g'.
        g = context.generator()
        return g.div((g.p(g.strong("Some text"), ' ',
                          g.a("Link label", href="/link/uri", title="Link tooltip")),
                      g.ul((g.li("First list item"),
                            g.li("Second list item"))),
                      ),
                     cls="div-class-name")

    Produced HTML:

    <div class="div-class-name">
    <p><strong>Some text</strong> <a title="Link tooltip" href="/link/uri">Link label</a></p>
    <ul>
      <li>First list item</li>
      <li>Second list item</li>
    </ul>
    </div>

    Generator is by purpose ignorant about HTML semantics.  The semantics
    should be handled by the 'Exporter'.  For example, if there are different
    HTML tags or attributes to be used in differnt HTML versions for a certain
    content element, it is the responsibility of the exporter to call the
    genarator appropriately.  The generator should only care about the syntax.

    The scope of supported tags and their attributes is incomplete.  It is
    limited to the tags and attributes which are actually used by LCG's export
    methods when exporting LCG content into HTML.  If you miss a method or an
    attribute, please help your self and add it.

    """
    class _JavaScriptCode(unistr):
        def __new__(cls, text):
            return unistr.__new__(cls, text)

    # Characters to be replaced in Javascript string literals for their
    # safe usage within HTML <script> tags.
    _JAVASCRIPT_ESCAPES = {'<': '\\u003c',
                           '>': '\\u003e',
                           '&': '\\u0026',
                           '"': '\\u0022',
                           '\'': '\\u0027',
                           '\\': '\\u005c',
                           '\n': '\\n'}
    _JAVASCRIPT_ESCAPE_REGEX = re.compile(r'[<>&"\'\n\\]')

    def __init__(self, sorted_attributes=False):
        """Arguments:

          sorted_attributes -- set to True when deterministic attribute order in HTML tags
            is needed (mostly useful for unit testing).

        """
        self._sorted_attributes = sorted_attributes

    def _js_escape_char(self, match):
        return self._JAVASCRIPT_ESCAPES[match.group(0)]

    def _tag(self, tag, content=None, attr=None, paired=True, allow=()):
        common_attributes = ('accesskey', 'class', 'id', 'lang',
                             'role', 'style', 'tabindex', 'title')
        dirty = False
        result = [self.noescape('<' + tag)]
        attributes = list((attr or {}).items())
        if self._sorted_attributes:
            attributes = sorted(attributes)
        for name, value in attributes:
            if value is not None and value is not False:
                if name.endswith('_'):
                    # Python keywords, such as 'for' or 'async' must be suffixed by underscore.
                    name = name[:-1]
                name = name.replace('_', '-')
                if name == 'cls':
                    name = 'class'
                if not (name in common_attributes or name in allow or
                        name.startswith('aria-') or name.startswith('data-')):
                    raise Exception("Invalid attribute '%s' for HTML tag '%s'." % (name, tag))
                result.append(' ' + name + '=')
                if value is True:
                    # Use boolean value syntax, which is compatible with both HTML4 and XHTML.
                    str_value = '"' + name + '"'
                elif isinstance(value, int):
                    str_value = '"%d"' % value
                elif isinstance(value, lcg.Localizable):
                    str_value = value.transform(saxutils.quoteattr)
                    dirty = True
                else:
                    str_value = self.noescape(saxutils.quoteattr(value))
                result.append(str_value)
        if content is not None and not isinstance(content, HtmlEscapedUnicode):
            if content.__class__ in (str, unistr):
                content = self.escape(content)
            else:
                dirty = True
        if paired:
            result.extend((self.noescape('>'), content or '', self.noescape('</' + tag + '>')))
        else:
            assert content is None, "Non-empty non-paired content"
            result.append(self.noescape('/>'))
        if dirty:
            return self.concat(*result)
        else:
            return self.noescape(''.join(result))

    def uri(self, base, *args, **kwargs):
        """Return a URI constructed from given base URI and arguments.

        Arguments:

          base -- base URI.  A relative path such as '/xx/yy'.
          *args -- pairs (NAME, VALUE) representing arguments appended to
            'base_uri' in the order in which they appear.  The first positional
            argument may also be a string representing an anchor name.  If
            that's the case, the anchor is appended to 'base_uri' after a '#'
            sign and the first argument is not considered to be a (NAME, VALUE)
            pair.
          **kwargs -- keyword arguments representing additional arguments to
            append to the URI.  Use 'kwargs' if you don't care about the order
            of arguments in the returned URI, otherwise use 'args'.

        If any of 'args' or 'kwargs' VALUE is None, the argument is omitted.

        The URI and the arguments may be unicode strings.  All strings are
        encoded as 'utf-8' and properly quoted and in the returned URI.

        """
        uri = urllib.parse.quote(base.encode('utf-8'))
        if args and isinstance(args[0], basestring):
            anchor = urllib.parse.quote(unistr(args[0]).encode('utf-8'))
            args = args[1:]
        else:
            anchor = None

        query = ';'.join([k + '=' + urllib.parse.quote(unistr(v).encode('utf-8'))
                          for k, v in args + tuple(kwargs.items()) if v is not None])
        if query:
            uri += '?' + query
        if anchor:
            uri += '#' + anchor
        return uri

    def escape(self, text):
        return HtmlEscapedUnicode(text, escape=True)

    def noescape(self, text):
        return HtmlEscapedUnicode(text, escape=False)

    def _concat_escape(self, element):
        if isinstance(element, lcg.Concatenation):
            result = element
        elif isinstance(element, lcg.Localizable):
            if self._concat_escape not in element._transforms:
                result = element.transform(self._concat_escape)
        elif isinstance(element, HtmlEscapedUnicode):
            result = element
        elif isinstance(element, basestring):
            result = self.escape(element)
        elif isinstance(element, (tuple, list)):
            result = [self._concat_escape(e) for e in element]
        else:
            raise Exception("Unexpected concatenation element type", element)
        return result

    def concat(self, *items):
        return concat(*self._concat_escape(items))

    def html(self, content, **kwargs):
        return self._tag('html', content, kwargs, allow=('xmlns',))

    def head(self, content, **kwargs):
        return self._tag('head', content, kwargs)

    def title(self, content, **kwargs):
        return self._tag('title', content, kwargs)

    def link(self, **kwargs):
        return self._tag('link', None, kwargs, paired=False,
                         allow=('rel', 'type', 'href', 'media'))

    def style(self, content, **kwargs):
        return self._tag('style', content, kwargs, allow=('type', 'media'))

    def meta(self, **kwargs):
        return self._tag('meta', None, kwargs, paired=False,
                         allow=('name', 'content', 'property', 'http-equiv'))

    def body(self, content, **kwargs):
        return self._tag('body', content, kwargs, allow=('onkeydown', 'onload'))

    def div(self, content, **kwargs):
        return self._tag('div', content, kwargs)

    def nav(self, content, **kwargs):
        return self._tag('nav', content, kwargs)

    def template(self, content, **kwargs):
        return self._tag('template', content, kwargs)

    def section(self, content, **kwargs):
        return self._tag('section', content, kwargs)

    def span(self, content, **kwargs):
        return self._tag('span', content, kwargs)

    def h(self, content, level, **kwargs):
        return self._tag('h%d' % level, content, kwargs)

    def h1(self, content, **kwargs):
        return self.h(content, level=1, **kwargs)

    def h2(self, content, **kwargs):
        return self.h(content, level=2, **kwargs)

    def h3(self, content, **kwargs):
        return self.h(content, level=3, **kwargs)

    def h4(self, content, **kwargs):
        return self.h(content, level=4, **kwargs)

    def h5(self, content, **kwargs):
        return self.h(content, level=5, **kwargs)

    def h6(self, content, **kwargs):
        return self.h(content, level=6, **kwargs)

    def map(self, content, **kwargs):
        return self._tag('map', content, kwargs, allow=('name',))

    def strong(self, content, **kwargs):
        return self._tag('strong', content, kwargs)

    def em(self, content, **kwargs):
        return self._tag('em', content, kwargs)

    def u(self, content, **kwargs):
        return self._tag('u', content, kwargs)

    def i(self, content, **kwargs):
        return self._tag('i', content, kwargs)

    def code(self, content, **kwargs):
        return self._tag('code', content, kwargs)

    def pre(self, content, **kwargs):
        return self._tag('pre', content, kwargs)

    def sup(self, content, **kwargs):
        return self._tag('sup', content, kwargs)

    def sub(self, content, **kwargs):
        return self._tag('sub', content, kwargs)

    def p(self, *args, **kwargs):
        # Passing content as several positional arguments is deprecated.
        # Use a single 'content' argument.
        content = args[0] if len(args) == 1 else args or tuple(kwargs.pop('content', ()))
        if content and content[0].find('object') != -1:
            # This is a nasty hack to suppress <p>...</p> around a video player.  In any case,
            # wrapping a block-level element in another block level element is invalid HTML, so
            # this should never be wrong to omit the paragraph.
            if ((content and content[0].strip().startswith('<div') and
                 content[-1].strip().endswith('</div>'))):
                return self.concat(content)
        return self._tag('p', content, kwargs)

    def blockquote(self, content, **kwargs):
        return self._tag('blockquote', content, kwargs)

    def footer(self, content, **kwargs):
        return self._tag('footer', content, kwargs)

    def figure(self, content, **kwargs):
        return self._tag('figure', content, kwargs)

    def figcaption(self, content, **kwargs):
        return self._tag('figcaption', content, kwargs)

    def br(self, **kwargs):
        return self._tag('br', None, kwargs, paired=False)

    def hr(self, **kwargs):
        return self._tag('hr', None, kwargs, paired=False)

    def a(self, content, **kwargs):
        return self._tag('a', content, kwargs,
                         allow=('href', 'type', 'name', 'target', 'rel',
                                'onclick', 'onmouseover', 'onmouseout'))

    def ol(self, *args, **kwargs):
        # Passing content as several positional arguments is deprecated.
        # Use a single 'content' argument.
        content = args[0] if len(args) == 1 else args or tuple(kwargs.pop('content', ()))
        return self._tag('ol', content, kwargs)

    def ul(self, *args, **kwargs):
        # Passing content as several positional arguments is deprecated.
        # Use a single 'content' argument.
        content = args[0] if len(args) == 1 else args or tuple(kwargs.pop('content', ()))
        return self._tag('ul', content, kwargs)

    def li(self, content, **kwargs):
        return self._tag('li', content, kwargs)

    def dl(self, *args, **kwargs):
        # Passing content as several positional arguments is deprecated.
        # Use a single 'content' argument.
        content = args[0] if len(args) == 1 else args or tuple(kwargs.pop('content', ()))
        return self._tag('dl', content, kwargs)

    def dt(self, content, **kwargs):
        return self._tag('dt', content, kwargs)

    def dd(self, content, **kwargs):
        return self._tag('dd', content, kwargs)

    def img(self, src, alt='', **kwargs):
        return self._tag('img', None, dict(kwargs, src=src, alt=alt), paired=False,
                         allow=('src', 'alt', 'longdesc', 'width', 'height', 'align', 'border'))

    def abbr(self, content, **kwargs):
        return self._tag('abbr', content, kwargs)

    def time(self, content, **kwargs):
        return self._tag('time', content, kwargs, allow=('datetime',))

    def table(self, content, **kwargs):
        return self._tag('table', content, kwargs,
                         allow=('summary', 'border', 'cellspacing', 'cellpadding', 'width'))

    def tr(self, content, **kwargs):
        return self._tag('tr', content, kwargs)

    def th(self, content, **kwargs):
        return self._tag('th', content, kwargs,
                         allow=('colspan', 'width', 'align', 'valign', 'scope'))

    def td(self, content, **kwargs):
        return self._tag('td', content, kwargs,
                         allow=('colspan', 'width', 'align', 'valign', 'scope'))

    def thead(self, content, **kwargs):
        return self._tag('thead', content, kwargs)

    def tfoot(self, content, **kwargs):
        return self._tag('tfoot', content, kwargs)

    def tbody(self, content, **kwargs):
        return self._tag('tbody', content, kwargs)

    def iframe(self, src, **kwargs):
        return self._tag('iframe', self.a(src, href=src), dict(kwargs, src=src),
                         allow=('src', 'type', 'width', 'height', 'frameborder',
                                'webkitallowfullscreen', 'mozallowfullscreen', 'allowfullscreen'))

    def object(self, content, **kwargs):
        return self._tag('object', content, kwargs, allow=(
            'align', 'archive', 'border', 'classid', 'codebase', 'codetype',
            'data', 'declare', 'height', 'hspace', 'name', 'standby', 'type',
            'usemap', 'vspace', 'width', 'dir',
        ))

    def param(self, **kwargs):
        return self._tag('param', None, kwargs, paired=False,
                         allow=('name', 'value', 'valuetype', 'type'))

    def form(self, content, action="#", **kwargs):
        return self._tag('form', content, dict(kwargs, action=action),
                         allow=('name', 'action', 'method', 'enctype', 'onsubmit', 'novalidate'))

    def legend(self, content, **kwargs):
        return self._tag('legend', content, kwargs)

    def fieldset(self, content, **kwargs):
        return self._tag('fieldset', content, kwargs)

    def label(self, content, for_=None, **kwargs):
        # The argument for_ may be also used as positional.  It
        # should to be kept as the second argument in future.
        kwargs['for'] = for_
        return self._tag('label', content, kwargs, allow=('for',))

    def input(self, type='text', **kwargs):
        assert type in ('button', 'checkbox', 'color', 'date', 'datetime', 'datetime-local',
                        'email', 'file', 'hidden', 'image', 'month', 'number', 'password',
                        'radio', 'range', 'reset', 'search', 'submit', 'tel', 'text', 'time',
                        'url', 'week'), type
        return self._tag('input', None, dict(kwargs, type=type), paired=False,
                         allow=('type', 'name', 'value', 'size', 'maxlength', 'autocomplete',
                                'autofocus', 'onclick', 'onmousedown', 'onmouseup', 'onkeydown',
                                'onkeypress', 'onchange', 'readonly', 'disabled', 'checked',
                                'multiple'))

    def field(self, value='', name='', size=20, password=False, cls=None, **kwargs):
        # Deprecated!  Use 'input()' instead.
        type = password and 'password' or 'text'
        cls = type + (cls and ' ' + cls or '')
        return self.input(type=type, name=name, value=value, size=size, cls=cls, **kwargs)

    def upload(self, name, **kwargs):
        return self.input(type='file', name=name, **kwargs)

    def radio(self, name, **kwargs):
        return self.input(type='radio', name=name, **kwargs)

    def checkbox(self, name, **kwargs):
        return self.input(type='checkbox', name=name, **kwargs)

    def hidden(self, name, value, id=None):
        return self.input(type='hidden', name=name, value=value, id=id)

    def button(self, content, type=None, **kwargs):
        assert type in (None, 'button', 'reset', 'submit', 'menu'), type
        return self._tag('button', content, dict(kwargs, type=type),
                         allow=('name', 'value', 'type', 'onclick', 'disabled'))

    def submit(self, content, **kwargs):
        return self.button(content, type='submit', **kwargs)

    def select(self, content, **kwargs):
        return self._tag('select', content, kwargs,
                         allow=('name', 'onchange', 'disabled', 'readonly'))

    def optgroup(self, content, **kwargs):
        return self._tag('optgroup', content, kwargs, allow=('label',))

    def option(self, content, **kwargs):
        return self._tag('option', content, kwargs, allow=('value', 'selected', 'disabled'))

    def textarea(self, content=None, **kwargs):
        return self._tag('textarea', content, kwargs,
                         allow=('name', 'rows', 'cols', 'disabled', 'readonly'))

    def audio(self, src, content=None, controls=True, **kwargs):
        return self._tag('audio', content, dict(kwargs, src=src, controls=controls),
                         paired=content is not None,
                         allow=('autoplay', 'controls', 'loop', 'preload', 'src'))

    def video(self, src, content=None, controls=True, **kwargs):
        return self._tag('video', content, dict(kwargs, src=src, controls=controls),
                         paired=content is not None,
                         allow=('autoplay', 'controls', 'height', 'loop', 'muted',
                                'poster', 'preload', 'src', 'width'))

    def source(self, src, **kwargs):
        return self._tag('source', None, dict(kwargs, src=src), paired=False,
                         allow=('src', 'type'))

    def script(self, content=None, type="text/javascript", **kwargs):
        return self._tag('script', content, dict(kwargs, type=type),
                         allow=('src', 'type', 'integrity', 'crossorigin', 'async'))

    def noscript(self, content):
        return self._tag('noscript', content)

    def js_value(self, value):
        """Return Javascript representation of given python value as a unicode."""
        if value is None:
            return 'null'
        elif isinstance(value, self._JavaScriptCode):
            return value
        elif isinstance(value, basestring):
            # Use double quotes (not single) to make output JSON compatible!
            return '"' + self._JAVASCRIPT_ESCAPE_REGEX.sub(self._js_escape_char, value) + '"'
        elif isinstance(value, bool):
            return (value and 'true' or 'false')
        elif isinstance(value, int):
            return unistr(value)
        elif isinstance(value, (tuple, list)):
            return concat('[', concat([self.js_value(v) for v in value], separator=", "), ']')
        elif isinstance(value, dict):
            # Only string keys are supported in JavaScript (int works too, but is actually
            # converted to string, which might be unexpected, so we don't support it).
            assert lcg.is_sequence_of(list(value.keys()), basestring)
            return concat('{', concat([concat(self.js_value(k), ': ', self.js_value(v))
                                       for k, v in list(value.items())],
                                      separator=", "),
                          '}')
        else:
            raise Exception("Unsupported value type for JavaScript conversion:", value)

    def js_call(self, fname, *args):
        fargs = [self.js_value(arg) for arg in args]
        return self._JavaScriptCode('%s(%s)' % (fname, concat(fargs, separator=", ")))


class XhtmlGenerator(HtmlGenerator):
    pass


class HtmlExporter(lcg.Exporter):
    Generator = HtmlGenerator

    class Context(lcg.Exporter.Context):

        class IdGenerator(object):
            """HTML identifier class for the 'id_generator()' method."""

            def __init__(self, context):
                self._context = context

            def __getattr__(self, name):
                id = self._context.unique_id()
                self.__dict__[name] = id
                return id

        def __init__(self, *args, **kwargs):
            self._generator = kwargs.pop('generator')
            self._audio_controls = []
            # We generate a random string prefix for all unique identifiers.
            # This makes the identifiers unique even if we compose a page from
            # pieces exported in different contexts, which is typical when
            # using AJAX.
            self._unique_id_prefix = (random.choice(string.ascii_lowercase) +
                                      ''.join(random.sample(string.digits +
                                                            string.ascii_lowercase +
                                                            '-',
                                                            11)))
            self._unique_id_index = 0
            self._backref = {}
            super(HtmlExporter.Context, self).__init__(*args, **kwargs)

        def _init_kwargs(self, allow_interactivity=True, **kwargs):
            self._allow_interactivity = allow_interactivity
            super(HtmlExporter.Context, self)._init_kwargs(**kwargs)

        def generator(self):
            return self._generator

        def allow_interactivity(self):
            return self._allow_interactivity

        def unique_id(self):
            """Return a unique id string in the curent context.

            The returned string may typically be used as a unique HTML element
            id.

            """
            self._unique_id_index += 1
            return '%s%x' % (self._unique_id_prefix, self._unique_id_index)

        def id_generator(self):
            """Return a new instance of unique HTML id generator.

            The generator may be used to generate named HTML identifiers on the
            fly as the attributes of the instance.  When an instance attribute
            is accessed for the first time, a new id is generated using the
            method 'unique_id()' and saved for given attribute name.
            Subsequent acces to the same attributte will return the same
            identifier value.

            The identifier values are unique in the scope of the current
            context, but their names are unique in the scope of the instance
            returned by each call of this method.

            Example usage:

            g = context.generator()
            ids = context.id_generator()
            html = g.div((
                g.div((
                    g.label('Name:', for_=ids.name),
                    g.input(name='name', id=ids.name),
                )),
                g.div((
                    g.label('Age:', for_=ids.age),
                    g.input(name='age', id=ids.age),
                )),
                ...
            ))

            """
            return self.IdGenerator(self)

        def bind_audio_control(self, element_id, uri):
            """Bind audio player to play given audio file on given element.

            Connects the audio player to play a particular audio file for a
            particular control element (typically button or link).

            If this method is called at least once during document export, a
            shared audio player instance is created at the bottom of the page
            and connected to all controls for which this method was called.

            """
            self._audio_controls.append((element_id, uri))

        def audio_controls(self):
            """Return a list of all audio player controls on current page.

            Returns a list of (element_id, uri) pairs for which
            'bind_audio_control()' was called.

            """
            return self._audio_controls

        def create_backref(self, item):
            """Create a back reference anchor for given section and return it as a string.

            Arguments:
              item -- the lcg.Section instance for which the back reference should be
                created.

            Back reference is a reference leading from section heading to
            its corresponding item in the table of contents.  TOC asks the back
            reference creation using this method.  The section then asks
            whether the back reference exists using the 'backref()' method.

            Just one back reference may exist so only the first call returns
            the anchor.  Following calls in the same context (on the same page)
            return None.

            """
            if item not in self._backref:
                backref = self._backref[item] = "backref-" + item.id()
            else:
                backref = None
            return backref

        def backref(self, item):
            """Return the back reference if it was previously created or None."""
            return self._backref.get(item)

    class Part(object):
        """Representation of the HTML page <body> element content structure.

        Defines one part of page structure hierarchy as defined by the
        'HtmlExporter._PAGE_STRUCTURE' constant.  The contents of these parts
        changes for each 'lcg.ContentNode', but the overall structure of the
        parts remains unchanged for all pages produced by the exporter (a page
        typically always consists of a header, menu, main content, footer and
        similar parts).  Each part is represented by a single HTML <div>
        element on the output.  The div either contains dynamic content
        generated by a corresponding exporter method or nested parts.  Each
        part has a unique id (used for the HTML div's id attributte) and may
        define additional static attributes for the HTML tag which may be
        overriden dynamically.

        Constructor arguments:

          id -- string identifier used for the id attribute of the resulting
            HTML div element as well as to locate the corresponding exporter
            methods generating the element's content and dynamic attributes
            (see below).  Thus the id should be a valid HTML id.

          content -- sequence of nested parts as 'lcg.HtmlExporter.Part'
            instances.  If not None, the part content is generated by exporting
            the nested parts.  If None, the exporter method with a name
            matching the part id is used to generate the content.  The 'id' is
            prefixed by an underscore and dashes in the id are replaced by
            underscores to get the method name.  Thus for example the part
            'main-menu' would have a corresponding exporter method
            '_main_menu()'.  The method will get the current exporter context
            instance as argument and should return an exported HTML string.  If
            None is returned, the part is completely omitted from the output,
            including its <div> tag, while if an empty string is returned, the
            tag is present but empty.  If content is not None, the method is
            not used (even if it exists) and if None, the method must exist,
            otherwise AttributeError will be raised on export.  To define an
            empty div you may pass an empty list (or None and define a method
            returning an empty string).

          **attr -- all remaining keyword arguments are passed on to
            'HtmlGenerator.div()' so they will be translated to HTML tag
            attributes (typicaly 'aria_label', 'role', 'cls', etc.).
            Additional attributes may be defined dynamically using a special
            exporter method of a name matching the part id prefixed by
            underscore and suffixed by '_attr' with dashes replaced by
            underscores, so for example '_main_menu_attr()' for 'main-menu'.
            The method will get the current exporter context as argument and
            returns a dictionary of additional attributes, which override the
            statically defined attributes passed to 'Part' constructor.

        """

        def __init__(self, id, content=None, **attr):
            self.id = id
            self.name = '_' + id.replace('-', '_')
            self.content = content
            self.attr = attr

    _PAGE_STRUCTURE = (
        Part('heading'),
        Part('language-selection'),
        Part('content'),
    )
    """The HTML page <body> element content structure as a sequence of 'Part' instances."""

    _LANGUAGE_SELECTION_COMBINED = False
    _MATHML_XMLNS = re.compile(r'<math[^>]* xmlns=".*')
    _ALLOW_BACKREF = True
    """Allow using back references from section titles to related TOC items (if TOC exists)."""

    def __init__(self, *args, **kwargs):
        """Arguments:

          sorted_attributes: set to True when deterministic attribute order in
            HTML tags is needed (mostly useful for unit testing).
          allow_svg: if True (the default), SVG content will be included in
            HTML directly.  If False, SVG content will be converted to PNG and
            embedded in HTML as an image (requires cairosvg to be installed).

        """
        self._generator = self.Generator(sorted_attributes=kwargs.pop('sorted_attributes', False))
        self._allow_svg = kwargs.pop('allow_svg', True)
        super(HtmlExporter, self).__init__(*args, **kwargs)

    def _title(self, context):
        return context.node().title()

    def _meta(self, context):
        """Return the list of pairs (NAME, CONTENT) for meta tags of given context/node."""
        return (('generator', 'LCG %s (http://www.freebsoft.org/lcg)' % lcg.__version__),)

    def _scripts(self, context):
        """Return the list of 'Script' instances for given context/node."""
        return context.node().resources(lcg.Script)

    def _script(self, context, script):
        g = context.generator()
        result = g.script(src=context.uri(script) if script.src_file() else None,
                          type=script.type() or "text/javascript",
                          content=script.content().decode('utf-8') if script.content() else None)
        if script.filename() in ('jquery.js', 'jquery.min.js'):
            result += g.script('jQuery.noConflict()')
        return result

    def _head(self, context):
        g = context.generator()
        node = context.node()
        return (
            [g.title(self._title(context))] +
            [g.meta(http_equiv=header, content=value)
             for header, value in (('Content-Language', context.lang()),
                                   ('Content-Script-Type', 'text/javascript'),
                                   ('Content-Style-Type', 'text/css'),
                                   ('X-UA-Compatible', 'edge'))] +
            [g.meta(name=name, content=value) for name, value in self._meta(context)] +
            [g.link(rel='alternate', lang=lang, href=self._uri_node(context, node, lang=lang))
             for lang in node.variants() if lang != context.lang()] +
            [g.link(rel='gettext', type='application/x-po', href=context.uri(t))
             for t in context.node().resources(lcg.Translations)] +
            [self._script(context, script) for script in self._scripts(context)]
        )

    def _part(self, context, part):
        if part.content is not None:
            content = self._parts(context, part.content)
        else:
            method = getattr(self, part.name)
            content = method(context)
        if content is not None:
            attr = part.attr
            dynattr = getattr(self, part.name + '_attr', None)
            if dynattr:
                attr = dict(attr, **dynattr(context))
            content = self._generator.div(content, id=part.id, **attr)
        return content

    def _parts(self, context, parts):
        result = []
        for part in parts:
            content = self._part(context, part)
            if content is not None:
                result.append(content)
        return result

    def _heading(self, context):
        return self._generator.h1(context.node().title())

    def _language_selection(self, context):
        g = context._generator
        node = context.node()
        variants = list(node.variants())
        if len(variants) <= 1:
            return None
        variants.sort()
        links = []
        for lang in variants:
            localizer = self.localizer(lang)
            label = localizer.localize(lcg.language_name(lang) or lang)
            cls = 'lang-' + lang
            if lang == context.lang():
                cls += ' current'
                sign = g.span(' *', cls='hidden')
            else:
                sign = ''
            image = self._language_selection_image(context, lang)
            if image:
                if self._LANGUAGE_SELECTION_COMBINED:
                    label += g.img(image, border=None)
                else:
                    label = g.img(image, alt=label, border=None)
            links.append(g.a(label, href=self._uri_node(context, node, lang=lang),
                             lang=lang, cls=cls) + sign)
        space = g.escape(' ')
        return concat(g.a(_("Choose your language:"),
                          id='language-selection-anchor', name='language-selection-anchor'), ' ',
                      concat(links, separator=(space + g.span('|', cls='sep') + space)))

    def _language_selection_image(self, context, lang):
        # return context.uri(context.resource('flags/%s.gif' % lang))
        return None

    def _content(self, context):
        return context.node().content(context.lang()).export(context)

    def _body_attr(self, context):
        return {}

    def _body_content(self, context):
        content = self._parts(context, self._PAGE_STRUCTURE)
        if context.audio_controls():
            # Automatically add the shared audio player if needed.
            content = concat(content, self._export_audio_player(context))
        return content

    def _css_dimension(self, dimension):
        if dimension is None:
            return None
        try:
            unit = {
                lcg.UPx: 'px',
                lcg.UFont: 'em',
                lcg.UMm: 'mm',
            }[dimension.__class__]
        except KeyError:
            raise Exception("Unsupported unit in HTML output: %r" % dimension)
        value = dimension.size()
        if isinstance(value, float):
            strvalue = '%.2f' % (value,)
        else:
            strvalue = unistr(value)
        return strvalue + unit

    def _image_style(self, width, height):
        return ' '.join('%s: %s;' % (attr, self._css_dimension(x))
                        for attr, x in (('width', width), ('height', height))
                        if x is not None) or None

    def context(self, *args, **kwargs):
        kwargs['generator'] = self._generator
        return super(HtmlExporter, self).context(*args, **kwargs)

    # Specific methods for exporting content elements.

    def _export_horizontal_separator(self, context, element):
        return self._generator.hr()

    def _export_new_line(self, context, element):
        return self._generator.br()

    def _export_new_page(self, context, element):
        return self._generator.hr(cls='new-page')

    def _export_vspace(self, context, element):
        """Export the given 'VSpace' element."""
        return self._generator.div('', style='height: %dmm' % element.size(context).size())

    def _export_strong(self, context, element):
        return self._export_container(context, element, wrap=self._generator.strong)

    def _export_emphasized(self, context, element):
        return self._export_container(context, element, wrap=self._generator.em)

    def _export_underlined(self, context, element):
        return self._export_container(context, element, wrap=self._generator.u)

    def _export_code(self, context, element):
        return self._export_container(context, element, wrap=self._generator.code)

    def _export_citation(self, context, element):
        return self._export_container(context, element, wrap=self._generator.span,
                                      lang=element.lang(inherited=False) or context.sec_lang(),
                                      cls='lcg-citation')

    def _export_quotation(self, context, element):
        g = self._generator

        def wrap(content, cls='lcg-quotation', **kwargs):
            uri = element.uri()
            if uri:
                source = g.a(element.source(), href=uri)
            else:
                source = element.source()
            if source or uri:
                content += g.footer(g.escape(u'— ') + source)
            return g.blockquote(content, cls=cls, **kwargs)

        return self._export_container(context, element, wrap=wrap)

    def _export_footer(self, context, element):
        return self._export_container(context, element, wrap=self._generator.footer)

    def _export_figure(self, context, element):
        g = self._generator

        def wrap(content, **kwargs):
            caption = element.caption()
            if caption:
                content += g.figcaption(caption.export(context))
            align = element.align()
            if align == 'left':
                cls = 'left-aligned'
            elif align == 'right':
                cls = 'right-aligned'
            else:
                cls = None
            return g.figure(content, cls=cls, **kwargs)

        return self._export_container(context, element, wrap=wrap)

    def _export_superscript(self, context, element):
        return self._export_container(context, element, wrap=self._generator.sup)

    def _export_subscript(self, context, element):
        return self._export_container(context, element, wrap=self._generator.sub)

    def _export_abbreviation(self, context, element):
        g = self._generator
        return g.abbr(self._export_text_content(context, element), title=element.descr(),
                      aria_label=element.descr())

    def _export_anchor(self, context, element):
        g = self._generator
        return g.span(self._export_text_content(context, element), id=element.anchor())

    def _export_link(self, context, element):
        target = element.target(context)
        label = self.concat(self._exported_container_content(context, element))
        descr = element.descr()
        if not label:
            if isinstance(target, (lcg.ContentNode, lcg.Section)):
                label = target.heading().export(context)
            elif isinstance(target, lcg.Resource):
                label = target.title() or target.filename()
            elif isinstance(target, element.ExternalTarget):
                label = target.title() or target.uri()
        if descr is None:
            if isinstance(target, (lcg.ContentNode, element.ExternalTarget, lcg.Resource)):
                descr = target.descr()
            elif isinstance(target, lcg.Section) and target.parent() is not element.parent():
                descr = target.title() + ' (' + target.parent().title() + ')'
        return self._generator.a(label, href=context.uri(target), title=descr, type=element.type())

    def _container_attr(self, element, cls=None, lang=None, style=None, **kwargs):
        style = style or {}
        if element.halign():
            style['text-align'] = {lcg.HorizontalAlignment.RIGHT: 'right',
                                   lcg.HorizontalAlignment.LEFT: 'left',
                                   lcg.HorizontalAlignment.CENTER: 'center',
                                   lcg.HorizontalAlignment.JUSTIFY: 'justify',
                                   }[element.halign()]
        presentation = element.presentation()
        if presentation and presentation.indent_left:
            style['margin-left'] = '%dem' % element.presentation().indent_left.size()
        attr = dict(id=element.id(),
                    cls=' '.join([x for x in element.names() + ((cls,) if cls else ())]) or None,
                    role=element.role(), aria_label=element.label(),
                    lang=lang or element.lang(inherited=False),
                    style=style and ' '.join(['%s: %s;' % x for x in list(style.items())]) or None,
                    **kwargs)
        return dict([(key, value) for key, value in list(attr.items()) if value is not None])

    def _exported_container_content(self, context, element):
        return [subcontent.export(context) for subcontent in element.content()]

    def _export_container(self, context, element, wrap=None, **kwargs):
        result = self.concat(self._exported_container_content(context, element))
        attr = self._container_attr(element, **kwargs)
        if wrap or attr:
            if wrap is None:
                wrap = self._generator.div
            result = wrap(result, **attr)
        return result

    def _export_paragraph(self, context, element):
        return self._export_container(context, element, wrap=self._generator.p)

    def _export_heading(self, context, element):
        return self._export_container(context, element)

    def _export_section(self, context, element):
        # Use div in HTML4, but allow overriding for HTML 5.
        g = self._generator
        level = len(element.section_path()) + 1
        return g.div(self._export_section_container(context, element), id=element.id(),
                     cls=' '.join(('section', 'section-level-%d' % level,) + element.names()))

    def _export_section_container(self, context, element):
        context.position_info.append(element.title())
        try:
            g = self._generator
            level = len(element.section_path()) + 1
            # Get rid of the outer Heading instance and only consider the contained content.
            lang = None
            heading = element.heading()
            if len(heading.content()) == 1 and isinstance(heading.content()[0], lcg.Container):
                # In this case, we want replace the Container created in
                # HTMLProcessor._section() and may have the lang attribute set by a
                # container with no lang (to avoid <div> tag when calling
                # heading.export()) and use the lang for the <h> tag.
                lang = heading.content()[0].lang()
                heading = lcg.Container(heading.content()[0].content())
            exported_heading = heading.export(context)
            backref = context.backref(element)
            if backref:
                exported_heading = self._generator.a(exported_heading, href="#" + backref,
                                                     cls='backref')
            attr = self._container_attr(element)
            # Replace the 'cls' attribute, because it will be used in the parent HTML tag.
            attr['cls'] = 'section-container section-level-%d' % level
            attr['id'] = None
            return g.div(
                (g.div(g.h(exported_heading, level, lang=lang),
                       cls='section-heading section-level-%d' % level),
                 g.div(g.div(self._exported_container_content(context, element),
                             cls='section-content-wrapper'),
                       cls='section-content section-level-%d' % level)),
                **attr
            )
        finally:
            context.position_info.pop()

    def _export_preformatted_text(self, context, element):
        g = self._generator
        text = element.text()
        mime_type = element.mime_type()
        if mime_type:
            try:
                import pygments
                import pygments.lexers
                import pygments.formatters
            except ImportError:
                pass
            else:
                lexer = pygments.lexers.get_lexer_for_mimetype(mime_type)
                if lexer:
                    html = pygments.highlight(text, lexer, pygments.formatters.HtmlFormatter())
                    context.resource('pygments.css')
                    return g.div(g.noescape(html), cls="lcg-preformatted-text")
        return g.div(g.pre(self.escape(text)), cls="lcg-preformatted-text")

    def _export_itemized_list(self, context, element):
        g = self._generator
        order = element.order()
        if order is None:
            method = g.ul
            style = None
        else:
            method = g.ol
            if order == 'lower-alpha':
                style = 'list-style-type: lower-alpha'
            elif order == 'upper-alpha':
                style = 'list-style-type: upper-alpha'
            else:
                style = None
        return method([g.li(item.export(context), cls="i%d" % (i + 1,))
                       for i, item in enumerate(element.content())],
                      style=style)

    def _export_definition_list(self, context, element):
        g = self._generator
        content = [g.dt(dt.export(context)) + g.dd(dd.export(context))
                   for dt, dd in element.content()]
        return g.dl(content)

    def _export_field_set(self, context, element):
        g = self._generator
        return g.table([g.tr((g.td(name.export(context), cls='label'),
                              g.td(value.export(context))))
                        for name, value in element.content()],
                       cls='lcg-fieldset', role="presentation")

    def _export_table_of_contents(self, context, element):
        g = self._generator
        parent = element.parent()

        def toc_link(item):
            if isinstance(item, lcg.ContentNode):
                descr = item.descr()
                name = None
                uri_kwargs = {}
            else:
                assert isinstance(item, lcg.Section)
                descr = None
                if item.parent() == parent and self._ALLOW_BACKREF:
                    name = context.create_backref(item)
                else:
                    name = None
                uri_kwargs = dict(local=(parent is item.parent()))
            uri = context.uri(item, **uri_kwargs)
            return g.a(item.heading().export(context), href=uri, name=name, title=descr)

        def make_toc(items):
            if len(items) == 0:
                return g.escape('')
            else:
                return g.ul([g.li((toc_link(item), make_toc(subitems)), cls="i%d" % (i + 1,))
                             for i, (item, subitems) in enumerate(items)])

        result = make_toc(element.items(context.lang()))
        title = element.title()
        if title is not None:
            g = self._generator
            # TODO: add a "skip" link?
            result = g.div(g.concat(g.div(g.strong(title), cls='title'), result),
                           cls='table-of-contents')
        return result

    def _export_table(self, context, element):
        return self._export_container(context, element, wrap=self._generator.table,
                                      cls='lcg-table', title=element.title())

    def _export_table_row(self, context, element):
        return self._export_container(context, element, wrap=self._generator.tr)

    def _export_table_cell(self, context, element):
        style = None
        row = element.container()
        widths = row.container().column_widths()
        if widths:
            index = row.content().index(element)
            if index < len(widths):
                width = widths[index]
                if width:
                    style = {'width': str(width.size()) + 'em',
                             'max-width': str(width.size()) + 'em'}
        return self._export_container(context, element, wrap=self._generator.td,
                                      align=element.align(), style=style)

    def _export_table_heading(self, context, element):
        return self._export_container(context, element, wrap=self._generator.th,
                                      align=element.align())

    def _export_inline_image(self, context, element):
        g = self._generator
        image = element.image(context)
        thumbnail = image.thumbnail()
        size = image.size()
        link = None
        if thumbnail:
            if not any(isinstance(c, lcg.Link) for c in element.container_path()):
                link = context.uri(image)
            image = thumbnail
        title = element.title()
        if title is None:
            title = image.title()
        descr = element.descr()
        if descr is None:
            descr = image.descr()
        if descr:
            if title:
                title = self.concat(title, ': ', descr)
            else:
                title = descr
        if title and not link:
            alt = title
        else:
            alt = ''
        width, height = element.width(), element.height()
        if width is None and height is None and image.size():
            width, height = list(map(lcg.UPx, image.size()))
        cls = ['lcg-image']
        if element.align():
            cls.append(element.align() + '-aligned')
        if element.name():
            cls.append('image-' + element.name())
        img = g.img(src=context.uri(image), alt=alt, align=element.align(), cls=' '.join(cls),
                    style=self._image_style(width, height))
        if link:
            if size:
                context.resource('photoswipe.js', type='module', content=(
                    "import PhotoSwipeLightbox from '{}';new PhotoSwipeLightbox({}).init();".format(
                        context.uri(lcg.Script('photoswipe-lightbox.esm.min.js')),
                        g.js_value(dict(
                            gallerySelector='#main',
                            childSelector='a.photoswipe-image',
                            pswpModule=context.uri(lcg.Script('photoswipe.esm.min.js')),
                            pswpCSS=context.uri(lcg.Stylesheet('photoswipe.css')),
                        )))
                ).encode('utf-8'))
                kwargs = dict(
                    cls='photoswipe-image',
                    data_pswp_width='%spx' % size[0],
                    data_pswp_height='%spx' % size[1],
                )
            else:
                kwargs = {}
            img = g.a(img, href=link, title=title, **kwargs)
        return img

    def _export_inline_audio(self, context, element):
        """Export emedded audio player for given audio file.

        Inline audio is rendered as a simple link which controls the LCG's
        shared audio player (usually located at the bottom right corner of a
        webpage).  If JavaScript is not available, the link will just download
        the audio file.

        """
        g = self._generator
        audio = element.audio(context)
        image = element.image(context)
        title = element.title() or audio.title()
        descr = element.descr() or audio.descr()
        uri = context.uri(audio)
        if image:
            label = g.img(context.uri(image), alt=title)
            descr = descr or title
        else:
            label = title or audio.filename()
        link_id = context.unique_id()
        context.bind_audio_control(link_id, uri)
        return g.a(label, href=uri, id=link_id, title=descr, cls='media-control-link')

    def _export_inline_video(self, context, element):
        """Export emedded video player for given video file.

        The video is represented by an HTML 5 <video> tag.

        """
        g = self._generator
        video = element.video(context)
        uri = context.uri(video)
        title = element.title() or video.title() or video.filename()
        descr = element.descr() or video.descr()
        image = element.image(context)
        if element.size() is None:
            width, height = (None, None)
        else:
            width, height = element.size()
        return g.video(
            src=uri, title=descr or title,
            poster=image and context.uri(image),
            width=width, height=height,
            # 'content' is displayed only in browsers not supporting the audio tag.
            content=g.a(title, href=uri, title=descr)
        )

    def _export_inline_external_video(self, context, element):
        """Export emedded video player for external services such as YouTube or Vimeo.

        A remote player from the video service is embedded into the page.

        """
        g = context.generator()
        service = element.service()
        if service == 'youtube':
            # rel=0 means do not load related videos
            uri = "https://www.youtube.com/embed/%s" % element.video_id()
        elif service == 'vimeo':
            uri = ("https://player.vimeo.com/video/%s" %
                   (element.video_id(),))
        else:
            Exception("Unsupported video service %s" % service)
        width, height = element.size() or (640, 480)
        return g.div(cls='external-video', style='max-width: %dpx;' % width, content=(
            g.div(cls='wrapper', style='padding-bottom: %.1f%%' % (100 * height / width), content=(
                g.iframe(
                    src=uri,
                    type="text/html",
                    width=width,
                    height=height,
                    title=element.title() or _("Video"),
                    frameborder=0,
                    webkitallowfullscreen=True,
                    mozallowfullscreen=True,
                    allowfullscreen=True,
                )
            ))
        ))

    def _export_exercise(self, context, element):
        from . import exercises_html
        exporter_cls = getattr(exercises_html, element.__class__.__name__ + 'Exporter')
        exporter = exporter_cls()
        return exporter.export(context, element)

    def _export_mathml(self, context, element):
        # Check the element content for basic sanity before passing it to noescape.
        mathml_elements = mathml.elements
        top_node = element.tree_content(top_only=True)
        for e in top_node.iter():
            if e.tag not in mathml_elements:
                raise lcg.ParseError("Unexpected MathML element", e)
        content = element.content().strip()
        if not self._MATHML_XMLNS.match(content):
            # HACK: xmlns sometimes disappears, so we make sure to put it
            # back here, but it would be better to ensure it doesn't
            # disappear through editation.
            assert content.startswith('<math') and content[5] in (' ', '>'), repr(content)
            content = '<math xmlns="http://www.w3.org/1998/Math/MathML"' + content[5:]
        return self._generator.noescape(content)

    def _export_inline_svg(self, context, element):
        svg = element.svg(context)
        if self._allow_svg:
            return self._generator.noescape(svg.decode('utf-8'))
        else:
            import cairosvg
            png = io.BytesIO()
            cairosvg.svg2png(bytestring=svg, write_to=png)
            return self._generator.img(src='data:image/png;base64, ' +
                                       base64.b64encode(png.getvalue()).decode('ascii'))

    def _export_audio_player(self, context):
        g = self._generator
        ids = context.id_generator()

        def button(label, **kwargs):
            return g.button(g.span(label), title=label, **kwargs)

        context.resource('lcg.js')
        context.resource('lcg-widgets.css')
        context.resource('jquery.min.js')
        context.resource('jplayer.min.js')
        player = (
            g.div(cls='jp-controls', content=(
                button(_("Play"), cls='play-pause', data_pause_label=_("Pause")),
                button(_("Rewind"), cls='rewind'),
                button(_("Fast Forward"), cls='fast-forward'),
            )),
            g.div(cls='jp-progress', content=(
                g.div(cls='jp-seek-bar', content=g.div('', cls='jp-play-bar')),
            )),
            # aria-live should be off by default, but Orca doesn't think so...
            g.div(cls='status', content=(
                g.div(_("Current position"), id=ids.cp_label, cls='hidden-label'),
                g.div(g.noescape('&nbsp;'), title=_("Current position"), cls='jp-current-time',
                      id=ids.cp_value, aria_labelledby=' '.join((ids.cp_label, ids.cp_value)),
                      aria_live='off'),
                g.div(_("Remaining time"), id=ids.rt_label, cls='hidden-label duration-label'),
                g.div(g.noescape('&nbsp;'), title=_("Remaining time"), cls='jp-duration',
                      data_duration_label=_("Total time"),
                      id=ids.rt_value, aria_labelledby=' '.join((ids.rt_label, ids.rt_value)),
                      aria_live='off'),
            )),
            g.div(cls='jp-volume-controls', content=(
                g.div(cls='jp-volume-bar', content=(
                    g.div(_("Volume"), id=ids.vol_label, cls='hidden-label'),
                    g.div('', cls='jp-volume-bar-value', id=ids.vol_value, aria_live='polite',
                          aria_labelledby=' '.join((ids.vol_label, ids.vol_value))),
                )),
                button(_("Volume Down"), cls='volume-down'),
                button(_("Volume Up"), cls='volume-up'),
            )),
        )
        content = [
            g.div(id=ids.player, cls='audio-player-widget', content=(
                g.div('', cls='jp-player'),
                g.div(id='jp_container_1', role='application',
                      aria_label=_("Player"), cls='jp-audio',
                      content=(
                          g.div(cls='jp-no-solution', content=(
                              g.strong(_("Update Required:")), ' ',
                              _("To play audio you will need to either update your "
                                "browser to a recent version or update %s.",
                                g.a(_("Flash plugin"),
                                    href="http://get.adobe.com/flashplayer/", target='_blank')),
                          )),
                          g.div(cls='jp-gui jp-interface', content=player),
                      )),
            )),
        ]
        swf = context.resource('jplayer.swf')
        script = [g.js_call('var player = new lcg.AudioPlayer', ids.player,
                            swf and context.uri(swf))]
        for element_id, uri in context.audio_controls():
            script.append(g.js_call('player.bind_audio_control', element_id, uri))
        content.append(g.script(''.join(line + ';\n' for line in script)))
        return content

    def escape(self, text):
        return self._generator.escape(text)

    def concat(self, *items):
        return self._generator.concat(*items)

    def _reformat_text(self, context, text):
        return text

    def _html_content(self, context):
        g = self._generator
        context.position_info.append(context.node().title())
        try:
            # Export body first to allocate all resources before generating the head.
            body = g.body(self._body_content(context), **self._body_attr(context))
            head = g.head(self._head(context))
            return concat(head, body)
        finally:
            context.position_info.pop()

    def export(self, context):
        g = self._generator
        return concat(g.noescape('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                                 '"http://www.w3.org/TR/html4/strict.dtd">\n\n'),
                      g.html(self._html_content(context), lang=context.lang()))


class Html5Exporter(HtmlExporter):
    Generator = XhtmlGenerator

    def _export_section(self, context, element):
        g = self._generator
        level = len(element.section_path()) + 1
        return g.section(self._export_section_container(context, element), id=element.id(),
                         cls=' '.join(('section', 'section-level-%d' % level,) + element.names()))

    def export(self, context):
        g = self._generator
        return concat(g.noescape('<?xml version="1.0" encoding="UTF-8"?>\n'
                                 '<!DOCTYPE html>\n'),
                      g.html(self._html_content(context), lang=context.lang(),
                             xmlns='http://www.w3.org/1999/xhtml'))


class HtmlFileExporter(lcg.FileExporter, HtmlExporter):
    """Export the content as a set of html files."""

    _OUTPUT_FILE_EXT = 'html'

    def _uri_node(self, context, node, lang=None):
        return self._filename(node, context, lang=lang)

    def dump(self, node, directory, filename=None, **kwargs):
        super(HtmlFileExporter, self).dump(node, directory, filename=filename, **kwargs)
        for n in node.children():
            self.dump(n, directory, **kwargs)
        for r in node.resources():
            self._export_resource(r, directory)


class StyledHtmlExporter(object):
    """Mix-in class for HTML exporter with a CSS support."""

    def __init__(self, styles=(), inlinestyles=False, **kwargs):
        """Initialize the exporter."""
        super(StyledHtmlExporter, self).__init__(**kwargs)
        self._styles = styles
        self._inlinestyles = inlinestyles

    def _stylesheets(self, context):
        """Return the list of 'Stylesheet' instances for given context/node."""
        return context.node().resources(lcg.Stylesheet)

    def _head(self, context):
        g = self._generator
        for style in self._styles:
            context.resource(style)
        styles = self._stylesheets(context)
        if self._inlinestyles:
            tags = [g.style(content, type='text/css', media=media)
                    for media, content in [(s.media(), s.get().decode('utf-8')) for s in styles]
                    if content is not None]
        else:
            tags = [g.link(rel='stylesheet', type='text/css', href=context.uri(s), media=s.media())
                    for s in styles]
        return super(StyledHtmlExporter, self)._head(context) + tags

    def _export_resource(self, resource, dir):
        if self._inlinestyles and isinstance(resource, lcg.Stylesheet):
            pass
        else:
            super(StyledHtmlExporter, self)._export_resource(resource, dir)


class HtmlStaticExporter(StyledHtmlExporter, HtmlFileExporter):
    """Export the content as a set of static web pages with navigation."""

    _accesskey = {
        'prev': '1',
        'next': '3',
        'up': '2',
        'index': '4',
    }

    _PAGE_STRUCTURE = (
        HtmlExporter.Part('top-navigation'),
        HtmlExporter.Part('heading'),
        HtmlExporter.Part('language-selection'),
        HtmlExporter.Part('content'),
        HtmlExporter.Part('bottom-navigation'),
    )

    def _head(self, context):
        g = self._generator
        node = context.node()
        return super(HtmlStaticExporter, self)._head(context) + [
            g.link(rel=kind, href=self.uri(context, n), title=n.title())
            for kind, n in (('top', node.root()),
                            ('prev', node.prev()),
                            ('next', node.next()),
                            ('parent', node.parent()))
            if n is not None and n is not node
        ] + [g.meta(http_equiv='Content-Type', content='text/html; charset=utf-8')]

    def _language_selection(self, context):
        if context.node() is not context.node().root():
            return None
        else:
            return super(HtmlStaticExporter, self)._language_selection(context)

    def _top_navigation(self, context):
        navigation = self._navigation(context)
        if navigation:
            g = self._generator
            return navigation + g.hr()
        else:
            return None

    def _bottom_navigation(self, context):
        navigation = self._navigation(context)
        if navigation:
            g = self._generator
            return g.hr() + navigation
        else:
            return None

    def _navigation(self, context):
        node = context.node()
        root = node.root()
        if len(root.linear()) <= 1:
            return None
        g = self._generator
        parent = node.parent()

        def link(target, label=None, key=None):
            if target:
                hidden = ''
                if label is None:
                    label = target.title(brief=True)
                if not key:
                    if target == root:
                        key = 'index'
                        if target == parent:
                            hidden = g.a('', href=self.uri(context, target),
                                         accesskey=self._accesskey['up'], cls='hidden')
                    elif target == parent:
                        key = 'up'
                return g.a(label, href=self.uri(context, target), title=target.title(),
                           accesskey=key and self._accesskey[key]) + hidden
            else:
                # Translators: Label used instead of a link when the target does not exist.  For
                # example sequential navigation may contain: "Previous: Introduction, Next: None".
                return _("None")

        breadcrumbs = g.div(_("You are here:") + ' ' +
                            concat([link(n) for n in node.path()], separator=' / '))
        nav = [
            # Translators: Label of a link to the next page in sequential navigation.
            g.span(_('Next') + ': ' + link(node.next(), key='next'), cls='next'),
            # Translators: Label of a link to the next page in sequential navigation.
            g.span(_('Previous') + ': ' + link(node.prev(), key='prev'), cls='prev')]
        return breadcrumbs + concat(nav, separator=g.span(' |\n', cls='separator'))


_URL_MATCHER = re.compile(r'(https?://.+?)(?=[\),.:;?!\]]?\.*(\s|&nbsp;|&lt;|&gt;|<br/?>|$))')


def format_text(text):
    """Format given string into HTML preserving linebreaks and indentation in multiline text.

    Returns the input text with all special characters correctly escaped and
    whitespace preserved.

    """
    nbsp = '&nbsp;'
    len_nbsp = len(nbsp)

    def convert_line(line):
        line_length = len(line)
        i = 0
        while i < line_length and line[i] == ' ':
            i += 1
        if i > 0:
            line = nbsp * i + line[i:]
            line_length += (len_nbsp - 1) * i
            i = len_nbsp * i
        while i < line_length:
            if line[i] == ' ':
                j = i + 1
                while j < line_length and line[j] == ' ':
                    j += 1
                if j > i + 1:
                    line = line[:i] + nbsp * (j - i) + line[j:]
                    line_length += (len_nbsp - 1) * (j - i)
                    i += len_nbsp * (j - i)
                else:
                    i += 1
            else:
                i += 1
        return line
    # Join lines and substitute links for HTML links
    lines = saxutils.escape(text).splitlines()
    converted_text = '<br>\n'.join(convert_line(l) for l in lines)
    formatted_text = _URL_MATCHER.sub(r'<a href="\1">\1</a>', converted_text)
    return HtmlEscapedUnicode(formatted_text, escape=False)
