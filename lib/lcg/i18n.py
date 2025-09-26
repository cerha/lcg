# -*- coding: utf-8 -*-

# Copyright (C) 2004-2015, 2017 OUI Technology Ltd.
# Copyright (C) 2019-2025 Tomáš Cerha <t.cerha@gmail.com>
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

"""LCG Internationalization support.

LCG internationalization is based on the delayed translation mechanism.  It is
important to retain the original strings while constructing LCG content.  This
allows us to decide for the output language at the export time.

"""
from __future__ import unicode_literals
from __future__ import print_function
import lcg

import datetime
import operator
import os
import re
import sys
from functools import reduce

unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


class TranslatableTextFactory(object):
    """A helper for defining the '_' identifier bound to a certain domain.

    You may define the '_' function as follows:

      _ = TranslatableTextFactory('domain-name')

    Note: Make sure the primary argument passed to the instance call is
    unicode, not string, otherwise the argument may remain untranslated!

    """

    def __init__(self, domain, origin='en'):
        assert isinstance(domain, basestring), domain
        assert isinstance(origin, basestring), origin
        self._domain = domain
        self._origin = origin

    def domain(self):
        """Return the domain name as set in the constructor."""
        return self._domain

    def __call__(self, *args, **kwargs):
        kwargs['_domain'] = self._domain
        kwargs['_origin'] = self._origin
        return TranslatableText(*args, **kwargs)

    def ngettext(self, *args, **kwargs):
        kwargs['_domain'] = self._domain
        kwargs['_origin'] = self._origin
        return TranslatablePluralForms(*args, **kwargs)

    def datetime(self, dt, **kwargs):
        return LocalizableDateTime(dt, **kwargs)

    def pgettext(self, context, text, *args, **kwargs):
        kwargs['_context'] = context
        return self.__call__(text, *args, **kwargs)


class TranslatedTextFactory(TranslatableTextFactory):
    """Like 'TranslatableTextFactory', but usable also in desktop application environment.

    We need to maintain the functionality of the base class (produce
    translatable strings), but we need to translate the strings in advance as
    well.  This will make the translation work both in web and desktop
    applications.  Desktop applications expect the string produced by the '_'
    function to be already translated into the current locale's language, like
    with the standard gettext utilities.  On the other hand, web applications
    need a translatable string which is translated later when a client is
    served.  Thus when we write code which defines strings which may be used
    both in web and desktop application environment, we need something which
    satisfies both worlds.  This class does that.

    """

    def __init__(self, domain, origin='en', lang=None, translation_path=(), timezone=None):
        """Arguments:

          domain, origin -- as in base class.

          lang -- target language code as a string.

          translation_path -- a sequence of directory names to search for
            translations.  As in 'GettextTranslator'.

        """
        # Create localizer to make use of its translator instance cache.
        self._localizer = lcg.Localizer(lang=lang, translation_path=translation_path,
                                        timezone=timezone)
        super(TranslatedTextFactory, self).__init__(domain, origin=origin)

    def _gettext(self, text):
        return self._localizer.translator().gettext(text, domain=self._domain, origin=self._origin)

    def __call__(self, text, *args, **kwargs):
        kwargs['_orig_text'] = text
        return super(TranslatedTextFactory, self).__call__(self._gettext(text), *args, **kwargs)

    def ngettext(self, singular, plural, *args, **kwargs):
        if args:
            n = args[0]
        else:
            # Accept missing 'n' here to let the assertion in TranslatablePluralForms.__new__ act.
            n = kwargs.get('n', 0)
        translated = self._localizer.translator().ngettext(singular, plural, n,
                                                           domain=self._domain, origin=self._origin)
        kwargs['_singular_orig_text'] = singular
        kwargs['_plural_orig_text'] = plural
        return super(TranslatedTextFactory, self).ngettext(translated, translated, *args, **kwargs)

    def datetime(self, *args, **kwargs):
        instance = super(TranslatedTextFactory, self).datetime(*args, **kwargs)
        localized = instance.localize(self._localizer)
        kwargs['string'] = localized
        return LocalizableDateTime(*args, **kwargs)

    def pgettext(self, context, text, *args, **kwargs):
        kwargs['_orig_text'] = text
        text = self._gettext(context + '\x04' + text)
        if text == context + '\x04' + text:
            # See TranslatableText._translate for comment on this hack (missing translation).
            text = kwargs['_orig_text']
        return super(TranslatedTextFactory, self).pgettext(context, text, *args, **kwargs)


class Localizable(unistr):
    """Common superclass of all localizable classes.

    This class is derived from Python 'unicode' type.  Thus it behaves as an
    ordinary Python string.  However, performing string operations, such as
    string formatting, substitution, etc leads to the loss of translation
    information.  In such a case the instance is unavoidably converted to an
    ordinary unicode string by Python and translation can not be performed
    anymore.  This is why there is the 'Concatenation' class, which protects the
    'Localizable' instances but still allows mixing them with ordinary strings.

    To preserve the 'Localizable' instances, only the following operations are
    permitted:

      * concatenation using the 'concat' function defined below.

      * concatenation using the '+' operator with other string, unicode,
        'TranslatableText' or 'Concatenation' instances.

      * generic transformations using the 'transform()' function.

    """
    def __new__(cls, text, _transforms=(), **kwargs):
        transformed = text
        for f in _transforms:
            transformed = f(transformed)
        try:
            instance = unistr.__new__(cls, transformed)
        except UnicodeDecodeError:
            # Necessary to display some tracebacks
            def escape(text):
                return re.sub(r'[^\x01-\x7F]', '?', text)
            instance = unistr.__new__(cls, escape(transformed))
        instance._text = text
        return instance

    def __init__(self, _transforms=()):
        assert isinstance(_transforms, tuple), _transforms
        self._transforms = _transforms

    def __add__(self, other):
        if not isinstance(other, basestring):
            return NotImplemented
        return concat((self, other))

    def __radd__(self, other):
        if not isinstance(other, basestring):
            return NotImplemented
        return concat((other, self))

    def _clone_args(self):
        return (self._text,)

    def _clone_kwargs(self):
        return dict(_transforms=self._transforms)

    def _clone(self, **kwargs):
        args = self._clone_args()
        kwargs = dict(self._clone_kwargs(), **kwargs)
        return self.__class__(*args, **kwargs)

    def _localize(self, localizer):
        raise Exception("This method must be overriden!")

    def transform(self, function):
        """Return a copy performing given transformation after localization.

        Creates a copy of the instance which applies given 'function' on the
        final string after the delayed localization.  The function will receive
        one argument -- the localized (unicode) string representing given
        instance.

        """
        return self._clone(_transforms=self._transforms + (function,))

    def replace(self, old, new):
        """Return a new 'Localizable' replacing the string 'old' by 'new'.

        This is just a convenience wrapper for:

          x.transform(lambda string: string.replace(old, new))

        """
        return self.transform(lambda x: x.replace(old, new))

    def strip(self, *args):
        """Return a new 'Localizable' stripping the final string after localization.

        This is just a convenience wrapper for:

          x.transform(lambda string: string.strip())

        """
        return self.transform(lambda x: x.strip(*args))

    def lstrip(self, *args):
        """Return a new 'Localizable' stripping the final string from left after localization.

        This is just a convenience wrapper for:

          x.transform(lambda string: string.lstrip())

        """
        return self.transform(lambda x: x.lstrip(*args))

    def rstrip(self, *args):
        """Return a new 'Localizable' stripping the final string from right after localization.

        This is just a convenience wrapper for:

          x.transform(lambda string: string.rstrip())

        """
        return self.transform(lambda x: x.rstrip(*args))

    def localize(self, localizer):
        """Return the localized version of the instance as a string.

        Arguments:

          localizer -- a 'Localizer' instance.

        The returned string can be unicode or plain string depending on the
        original instance (and its type) and also on the localizer.

        """
        result = self._localize(localizer)
        for transform in self._transforms:
            result = transform(result)
        return result


class TranslatableText(Localizable):
    """Translatable string with a delayed translation.

    The instances of this class can be mixed with ordinary Python strings
    (plain or unicode) strings using the 'Concatenation' class defined below.
    Then the exporter is capable to translate all translatable strings within
    the content at one place to the desired output language.

    As oposed to the ordinary gettext mechanism, the delayed translation allows
    us to build the content first and translate it afterwards.

    Instances must be treated cerefully to prevent losing the translation
    information as described in 'Localizable' class documentation.

    This class also supports variable interpolation.  The string passed to the
    constructor will be considered a format string if any substitution variables
    are passed.  The interpolation is done after translation, because we need
    the base string, not the interpolated one for translation.  And because the
    translation is defered, variable substitution must be also defered.  This
    makes the difference between using standatad gettex as the '_()' construct
    and using the 'TranslatableText' for the same.  With standard gettext, we
    get the translated version right away and we can substitute the variables in
    place.  However with 'TranslatableText', we must pass the variables to its
    constructor and let the instance interpolate them later.

    """
    _RESERVED_ARGS = ('escape_html',)

    class _Interpolator(object):

        def __init__(self, func, localizer):
            self._func = func
            self._localizer = localizer
            self._cache = {}
            self._contains_escaped_html = False

        def __getitem__(self, key):
            # Caching is necessary to avoid calling self._func twice when
            # HTML escaping is needed and formatting is repeated with
            # lcg.HtmlEscapedUnicode in TranslatableText._localize().
            try:
                localized_value = self._cache[key]
            except KeyError:
                value = self._func(unistr(key))
                localized_value = self._localizer.localize(value)
                if isinstance(value, lcg.HtmlEscapedUnicode):
                    self._contains_escaped_html = True
                    localized_value = lcg.HtmlEscapedUnicode(value, escape=True)
                elif isinstance(value, lcg.Concatenation) and value._html_escape:
                    self._contains_escaped_html = True
                self._cache[key] = localized_value
            return localized_value

        def contains_escaped_html(self):
            return self._contains_escaped_html

    def __new__(cls, text, *args, **kwargs):
        if not args or __debug__:
            substitution_dict = dict([(k, v) for k, v in list(kwargs.items())
                                      if not k.startswith('_') and k not in cls._RESERVED_ARGS])
            assert not args or not substitution_dict, \
                ("Cannot pass both positional and keyword substitution variables: " +
                 "(%s, %s, %s)" % (text, args, substitution_dict))
        else:
            substitution_dict = {}
        values = args or substitution_dict
        if values:
            text %= values
        return Localizable.__new__(cls, text, **kwargs)

    def __init__(self, text, *args, **kwargs):
        """Initialize the instance.

        Arguments:

          text -- the actual text to translate as a string or unicode instance.
          escape_html -- if passed as a keyword argument, it indicates, that
            the string should be returned as 'lcg.HtmlEscapedUnicode' after
            translation and variable interpolation.  The value (if not None) is
            a boolean passed to lcg.HtmlEscapedUnicode constructor as the
            argument 'escape'.  In the most typical case, you need to pass
            False here when the translation string directly contains HTML
            markup.  If omitted and the interpolation variables (see below),
            contain an 'lcg.HtmlEscapedUnicode' instance, the translation
            result is automatically returned as 'lcg.HtmlEscapedUnicode', but
            any HTML within the translated string will be escaped in this case.
          args -- positional substitution values (see below).
          kwargs -- named substitution arguments (see below).

        If 'args' or 'kwargs' are passed, the 'text' is considered a format
        string and it will be automatically interpolated after translation.

        Only 'args' or only 'kwargs' may be passed (not both at once).  This
        depends whether you are using named variables in the format string or
        just positional substitution.  It is recommended to use named format
        variables (with keyword arguments), especially when there is more than
        one variable within the string.

        Variable interpolation is performed on localization (when 'localize()'
        is called).  Also all values of format variables are localized
        recursively before interpolation, if they are 'Localizable' instances.
        TypeError may be raised during localization, when the constructor
        arguments didn't correspond to the format string.

        """
        assert isinstance(text, basestring), (text, type(text))
        self._text = text
        self._args = args
        self._init_kwargs(**kwargs)

    def _init_kwargs(self, _context=None, _orig_text=None, _domain=None, _origin='en',
                     _interpolate=None, _transforms=(), escape_html=None, **kwargs):
        assert isinstance(_domain, basestring) or _domain is None, _domain
        assert isinstance(_origin, basestring), _origin
        assert _context is None or isinstance(_context, basestring), _context
        assert _interpolate is None or callable(_interpolate), _interpolate
        assert escape_html is None or isinstance(escape_html, bool), escape_html
        self._orig_text = _orig_text or self._text
        self._domain = _domain
        self._origin = _origin
        self._interpolate = _interpolate
        self._kwargs = kwargs
        self._escape_html = escape_html
        self._context = _context
        super(TranslatableText, self).__init__(_transforms=_transforms)

    def _clone_args(self):
        return (self._text,) + self._args

    def _clone_kwargs(self):
        return dict(super(TranslatableText, self)._clone_kwargs(), _orig_text=self._orig_text,
                    _domain=self._domain, _origin=self._origin, _interpolate=self._interpolate,
                    **self._kwargs)

    def domain(self):
        """Return the domain name bound to this instance."""
        return self._domain

    def interpolate(self, func):
        """Return a new TranslatableText instance using given interpolation function.

        The interpolation is not performed immediately.  It is left to translation time and also
        translation of the interpolated arguments is performed.  The function passed to this method
        must take one argument -- the interpolation variable name -- and return a string.  The
        original instance must be created without any interpolation arguments passed to the
        constructor if you want to call this method on it.

        """
        return self._clone(_interpolate=func)

    def _translate(self, localizer):
        translator = localizer.translator()
        text = self._orig_text
        if self._context is not None:
            text = self._context + '\x04' + text
        translation = translator.gettext(text, domain=self._domain, origin=self._origin)
        if self._context is not None and translation == text:
            # When the translation is found, the context is stripped automatically,
            # but when the translation doesn't exist, text is returned unchanged,
            # so we need to return the original mesg without the context to avoid
            # having contexts clutter the ui.
            translation = self._orig_text
        return translation

    def _localize(self, localizer):
        translated = self._translate(localizer)
        escape = self._escape_html
        if escape is not None:
            translated = lcg.HtmlEscapedUnicode(translated, escape=escape)
        if self._interpolate and not self._args:
            interpolator = self._Interpolator(self._interpolate, localizer)
            interpolated = translated % interpolator
            if escape is None and interpolator.contains_escaped_html():
                translated = lcg.HtmlEscapedUnicode(translated, escape=True) % interpolator
            else:
                translated = interpolated
        elif self._args or self._kwargs:
            if self._args:
                args = tuple([localizer.localize(arg) for arg in self._args])
                values = args if escape is None else None
            else:
                args = dict([(k, localizer.localize(v)) for k, v in list(self._kwargs.items())])
                values = list(args.values()) if escape is None else None
            if escape is None and any(isinstance(v, lcg.HtmlEscapedUnicode) for v in values):
                translated = lcg.HtmlEscapedUnicode(translated, escape=True)
            translated %= args
        return translated


class SelfTranslatableText(TranslatableText):
    """Translatable string capable of self-translation.

    The translations of this string are pre-defined by passing them as a
    constructor argument.  The instance than translates itself -- the localizer
    is only used to find out the target language.

    As oposed to the translator-based translation, which uses translation
    catalogs, this class is handy when the translation string is part of
    application data, rather than application definition -- for example when
    the translated term and its translations are user defined strings stored in
    a database.

    Additional constructor arguments:

      translations -- a dictionary of translations keyed by a language code.

    """
    _RESERVED_ARGS = TranslatableText._RESERVED_ARGS + ('translations',)

    def _init_kwargs(self, translations=None, **kwargs):
        assert isinstance(translations, dict), translations
        self._translations = translations
        super(SelfTranslatableText, self)._init_kwargs(**kwargs)

    def _clone_kwargs(self):
        return dict(super(SelfTranslatableText, self)._clone_kwargs(),
                    translations=self._translations)

    def _translate(self, localizer):
        return self._translations.get(localizer.lang(), localizer.localize(self._orig_text))


class TranslatablePluralForms(TranslatableText):
    """Translatable string with plural forms.

    This class has the same purpose as the 'ngettext' family of GNU gettext calls.  The constructor
    accepts two forms of the translation text (singular and plural) and a number determining which
    form should be used.  If this number is 1, the singular form is used, if 2 or greater, the
    plural form is used.  For languages other than English, more plural forms may be defined in the
    translation file and the correct form will be selected according to the number.

    The number determining the plural form may be passed as positional or keyword argument.  If
    positional arguments are used for text substitution (as implemented by the parent class), the
    number must be passed as the first positional argument.  If keyword arguments are used, the
    number is passed as the keyword argument named 'n'.

    Note: The current implementation restricted to 'origin' languages with just two plural forms,
    such as English, but it would be possible to remove this limitation if needed.

    """
    def __new__(cls, singular, plural, *args, **kwargs):
        if args:
            n = args[0]
        else:
            assert 'n' in kwargs, ("A number determining the plural form must be passed as "
                                   "the first positional argument or as keyword argument 'n'.")
            n = kwargs['n']
        assert isinstance(n, int), n
        text = n == 1 and singular or plural
        return TranslatableText.__new__(cls, text, *args, **kwargs)

    def __init__(self, singular, plural, *args, **kwargs):
        if args:
            n = args[0]
        else:
            n = kwargs['n']
        text = n == 1 and singular or plural
        self._singular = unistr(singular)
        self._plural = unistr(plural)
        self._n = n
        super(TranslatablePluralForms, self).__init__(text, *args, **kwargs)

    def _init_kwargs(self, _singular_orig_text=None, _plural_orig_text=None, **kwargs):
        self._singular_orig_text = _singular_orig_text or self._singular
        self._plural_orig_text = _plural_orig_text or self._plural
        super(TranslatablePluralForms, self)._init_kwargs(**kwargs)

    def _clone_args(self):
        return (self._singular, self._plural) + self._args

    def _clone_kwargs(self):
        return dict(super(TranslatablePluralForms, self)._clone_kwargs(),
                    _singular_orig_text=self._singular_orig_text,
                    _plural_orig_text=self._plural_orig_text,
                    **self._kwargs)

    def _translate(self, localizer):
        translator = localizer.translator()
        return translator.ngettext(self._singular_orig_text, self._plural_orig_text, self._n,
                                   domain=self._domain, origin=self._origin)


class LocalizableDateTime(Localizable):
    """Date/time string which can be converted to a localized format.

    See the rules in 'Localizable' class documentation for more information
    about mixing instances of this class with other strings.

    """
    _RE = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)(?: (\d\d):(\d\d)(?::(\d\d))?)?$')
    _LEADING_ZEROS = re.compile(r'(?<!\d)0+')

    class _UTCTimezone(datetime.tzinfo):
        _ZERO_DIFF = datetime.timedelta(0)

        def utcoffset(self, dt):
            return self._ZERO_DIFF

        def tzname(self, dt):
            return "UTC"

        def dst(self, dt):
            return self._ZERO_DIFF
    _UTC_TZ = _UTCTimezone()

    def __new__(cls, dt, string=None, **kwargs):
        if string is None:
            if isinstance(dt, datetime.datetime):
                string = dt.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(dt, datetime.date):
                string = dt.isoformat()
            else:
                string = dt
        else:
            assert isinstance(dt, (datetime.datetime, datetime.date)), dt
        return Localizable.__new__(cls, string, **kwargs)

    def __init__(self, dt, string=None, show_seconds=True, show_weekday=False, show_time=True,
                 utc=False, leading_zeros=True, **kwargs):
        """Initialize the instance.

        Arguments:

          dt -- the input date/datetime as a python datetime.datetime,
            datetime.date or string.  If string is passed, it must be in format
            'yyyy-mm-dd' for date values or one of 'yyyy-mm-dd HH:MM' or
            'yyyy-mm-dd HH:MM:SS' for datetime values.

          string -- the string representation of 'dt' when passed as a datetime
            instance.  If None, the default string representation of the
            instance before localization is 'yyyy-mm-dd' for date values or
            'yyyy-mm-dd HH:MM:SS' for datetime values.

          show_time -- if true and if the passed datetime contains the time
            information, the time is also shown on output.  If false, only date
            is shown even if the input contains time.  The difference between
            passing a date and passing a datetime with show_time=False is that
            time zone conversion may apply before the date is displayed.
          show_seconds -- if true and the passed datetime's precision is
            sufficient (datetime instance or 'yyyy-mm-dd HH:MM:SS' string is
            passed), the time is displayed including seconds on output.
            Otherwise seconds are stripped.
          show_weekday -- if true, abbreviated localized week day name is added
            to the date/datetime value on output.

          utc -- this argument is only used if 'dt' is passed as a string or as
            a timezone naive datetime instance.  If true, the time is supposed
            to be in UTC and will be converted to local time zone on
            localization.  If false, the time is not subject to time zone
            conversion.  If timezone aware datetime instance is passed, its
            timezone is always respected and converted to local timezone on
            output (if known).

          leading_zeros -- if true the numeric values are always padded by
            leading zeros on output to maintain the same character width for
            any value.

        """
        super(LocalizableDateTime, self).__init__(**kwargs)
        if isinstance(dt, basestring):
            assert string is None
            m = self._RE.match(dt)
            if not m:
                raise ValueError("Invalid date/time format", dt)
            numbers = [int(n) for n in m.groups() if n is not None]
            if len(numbers) > 3:
                if utc:
                    tz = self._UTC_TZ
                else:
                    tz = None
                dt = datetime.datetime(*numbers, tzinfo=tz)
                is_datetime = True
                if len(numbers) < 6:
                    show_seconds = False
            else:
                dt = datetime.date(*numbers)
                is_datetime = False
        else:
            is_datetime = isinstance(dt, datetime.datetime)
            assert is_datetime or isinstance(dt, datetime.date), dt
            if is_datetime and not dt.tzinfo and utc:
                dt = dt.replace(tzinfo=self._UTC_TZ)
        self._datetime = dt
        self._show_weekday = show_weekday
        self._leading_zeros = leading_zeros
        self._is_datetime = is_datetime
        self._show_time = show_time
        self._show_seconds = show_seconds
        self._utc = utc

    def _clone_args(self):
        return (self._datetime,)

    def _clone_kwargs(self):
        return dict(super(LocalizableDateTime, self)._clone_kwargs(),
                    show_time=self._show_time,
                    show_seconds=self._show_seconds,
                    show_weekday=self._show_weekday,
                    leading_zeros=self._leading_zeros,
                    utc=self._utc)

    def _localize(self, localizer):
        dt = self._datetime
        data = localizer.locale_data()
        result = dt.strftime(data.date_format)
        if not self._leading_zeros:
            result = self._LEADING_ZEROS.sub('', result)
        if self._show_weekday:
            weekday = localizer.localize(lcg.week_day_name(dt.weekday(), abbrev=True))
            result = weekday + ' ' + result
        if self._is_datetime:
            timezone = localizer.timezone() or data.default_timezone
            # TODO: Add tests for corner cases, such as all (dt.tzinfo, timezone,
            # self._show_time) combinations (in their existence or nonexistence).
            if dt.tzinfo and timezone:
                dt = dt.astimezone(timezone)
            if self._show_time:
                time_format = (self._show_seconds and data.exact_time_format or data.time_format)
                result += ' ' + dt.strftime(time_format)
            if not timezone and dt.tzinfo:
                result += ' ' + dt.tzinfo.tzname(dt)
        return result


class LocalizableTime(Localizable):
    """Time string which can be converted to a localized format.

    See the rules in 'Localizable' class documentation for more information
    about mixing instances of this class with other strings.

    """
    _RE = re.compile(r'^(\d\d):(\d\d)(?::(\d\d))?$')

    def __init__(self, string, **kwargs):
        super(LocalizableTime, self).__init__(**kwargs)
        m = self._RE.match(string)
        if not m:
            raise Exception("Invalid time format", self)
        numbers = [int(n) for n in m.groups() if n is not None]
        self._time = datetime.time(*numbers)
        self._show_seconds = len(numbers) > 2

    def _localize(self, localizer):
        data = localizer.locale_data()
        time_format = (self._show_seconds and data.exact_time_format or data.time_format)
        return self._time.strftime(time_format)


class Decimal(Localizable):
    """Localizable decimal number."""

    def __new__(cls, value, precision=None, **kwargs):
        if isinstance(value, int):
            format = '%d'
        elif precision is None:
            format = '%f'
        else:
            format = '%%.%df' % precision
        return Localizable.__new__(cls, format % value, **kwargs)

    def __init__(self, value, precision=None, **kwargs):
        self._value = value
        self._precision = precision
        if precision is not None:
            self._format = '%%.%df' % precision
        elif isinstance(value, int):
            self._format = '%d'
        else:
            self._format = '%f'
        super(Decimal, self).__init__(**kwargs)

    def _clone_args(self):
        return (self._value,)

    def _clone_kwargs(self):
        return dict(super(Decimal, self)._clone_kwargs(),
                    precision=self._precision)

    def _locales(self, data):
        return data.decimal_point, data.grouping, data.thousands_sep

    def _group(self, grouping, thousands_sep, string_):
        if not grouping or not thousands_sep:
            return string_
        result = ""
        while string_ and grouping:
            if grouping[0] == -1:
                break
            elif grouping[0] != 0:
                # Process last group
                group = grouping[0]
                grouping = grouping[1:]
            if result:
                result = string_[-group:] + thousands_sep + result
            else:
                result = string_[-group:]
            string_ = string_[:-group]
            if len(string_) == 1 and string_[0] not in "0123456789":
                # the leading string_ is only a sign
                return string_ + result
        if not result:
            return string_
        if string_:
            result = string_ + thousands_sep + result
        return result

    def _localize(self, localizer):
        data = localizer.locale_data()
        formatted = self._format % self._value
        if formatted.find('.') == -1:
            pre, post = formatted, None
        else:
            pre, post = formatted.split(".")
        decimal_point, grouping, thousands_sep = self._locales(data)
        pre = self._group(grouping, thousands_sep, pre)
        if post:
            return pre + decimal_point + post
        else:
            return pre


class Monetary(Decimal):
    """Localizable monetary amount."""

    def __init__(self, value, precision=2, **kwargs):
        super(Monetary, self).__init__(value, precision=precision, **kwargs)

    def _locales(self, data):
        return data.mon_decimal_point, data.mon_grouping, data.mon_thousands_sep


class Concatenation(Localizable):
    """A concatenation of translatable and untranslatable text elements.

    Represents a block of text, where ordinary python strings, unicode strings
    and 'Localizable' instances are concatenated to make the final text.

    See 'Localizable' documentation for more information.

    """
    def __new__(cls, items, separator='', **kwargs):
        def escape(text):
            return re.sub(r'[^\x01-\x7F]', '?', text)

        def x(item):
            if isinstance(item, (list, tuple)):
                try:
                    return separator.join(item)
                except UnicodeDecodeError:
                    # Necessary to display some tracebacks
                    return separator.join([escape(i) for i in item])
            else:
                return item
        try:
            return Localizable.__new__(cls, separator.join([x(item) for item in items]), **kwargs)
        except UnicodeDecodeError:
            # Necessary to display some tracebacks
            return Localizable.__new__(cls, separator.join([escape(x(item)) for item in items]),
                                       **kwargs)

    def __init__(self, items, separator='', **kwargs):
        """Initialize the instance.

        Arguments:

          items -- a sequence of items composing the concatenation.  Each item
            may be a string, a unicode string, a 'Localizable' instance, tuple
            or list.

          separator -- this optional argument may be a string or a unicode
            string.  If specified, the items will be concatenated using this
            string between them.  By default the separator is an empty string,
            resulting in concatenating the items right next to each other.
            From the point of view of the separator, all items are atomic,
            except for sequences (lists and tuples).  If a sequence is included
            within items, its items are first concatenated using the separator
            and the result is then used for further concatenation with the rest
            of the items.  Thus, sequences behave like being unpacked.  If you
            want to prevent sequences from being unpacked, just pack them into
            a 'Concatenation'.

        If there is at least one unicode type argument, the concatenation will
        produce a unicode string on output (as the result of 'localize()'.  If
        all the input items (including the separator) are plain strings, a plain
        string is produced.

        """
        super(Concatenation, self).__init__(**kwargs)

        def html_escaped(items):
            if isinstance(items, (list, tuple)):
                for i in items:
                    if html_escaped(i):
                        return True
            elif isinstance(items, Concatenation):
                return items._html_escape
            else:
                return isinstance(items, lcg.HtmlEscapedUnicode)
        h_escape = self._html_escape = html_escaped(items)
        if h_escape:
            separator = lcg.HtmlEscapedUnicode(separator, escape=True)
        self._items = flat = []
        last = []

        def flatten(sequence, separator=separator):
            for x in sequence:
                if isinstance(x, Concatenation) and not x._transforms:
                    s = lcg.HtmlEscapedUnicode('', escape=False) if h_escape else ''
                    flatten(list(x.items()), separator=s)
                    last.append(separator)
                elif isinstance(x, Localizable):
                    text = ''.join(last)
                    if text:
                        if h_escape:
                            text = lcg.HtmlEscapedUnicode(text, escape=False)
                        flat.append(text)
                    del last[:]
                    flat.append(x)
                    last.append(separator)
                elif isinstance(x, (tuple, list)):
                    flatten(x)
                else:
                    assert isinstance(x, basestring)
                    if h_escape:
                        x = lcg.HtmlEscapedUnicode(x, escape=True)
                    last.append(x)
                    last.append(separator)
        flatten(items)
        if len(last) > 1:
            text = reduce(operator.add, last[1:-1], last[0])
            if text:
                flat.append(text)

    def __setstate__(self, state):
        # Prevent traceback on unpickling an instance which was pickled
        # with older LCG versions (this actually happens when loading
        # recent forms on Pytis application startup)
        self.__dict__ = state
        if '_html_escape' not in state:
            self._html_escape = False

    def _clone_args(self):
        return (self._items,)

    def _localize(self, localizer):
        h_escape = self._html_escape
        items = []
        for i in self._items:
            localized = localizer.localize(i)
            if isinstance(i, lcg.HtmlEscapedUnicode):
                localized = lcg.HtmlEscapedUnicode(localized, escape=(i != localized))
            elif h_escape:
                localized = lcg.HtmlEscapedUnicode(localized, escape=True)
            items.append(localized)
        try:
            result = ''.join(items)
        except UnicodeDecodeError:
            # Necessary to display some tracebacks
            def escape(text):
                return re.sub(r'[^\x01-\x7F]', '?', text)
            result = ''.join(items)
        if h_escape:
            result = lcg.HtmlEscapedUnicode(result, escape=False)
        return result

    def startswith(self, *args, **kwargs):
        """Return the result of 'startswidth()' call the method on the first item."""
        return self._items and self._items[0].startswith(*args, **kwargs)

    def endswith(self, *args, **kwargs):
        """Return the result of 'endwidth()' call the method on the last item."""
        return self._items and self._items[-1].endswith(*args, **kwargs)

    def items(self):
        """Return the list of items included in this concatenation.

        The items may not be returned in the same form as passed to the
        constructor, since the nested 'Concatenation' instances may be merged or
        otherwise reorganized.  It is only guaranted, that the items will form
        the same output string.

        The items returned byt this method are always either strings, unicode
        strings or other 'Localizable' instances.

        """
        return self._items


class Translator(object):
    """A generic translator of translatable objects.

    A translator is used to translate instances of 'TranslatableText' and
    derived classes.  Translatable instances coming from different translation
    domains can be mixed.

    This class only defines the basic API.  See 'GettextTranslator' or
    'NullTranslator' for concrete implementations.

    """

    def __init__(self, lang=None):
        self._lang = lang

    def gettext(self, text, domain=None, origin=None):
        """Return the translation of the string 'text' from given domain.

        Arguments:

          text -- the text to translate as a string or unicode instance.

          domain -- the name of the domain, form which this text origins.

        Returns a unicode string.

        """
        pass

    def ngettext(self, singular, plural, n, domain=None, origin=None):
        """Return the translation of the plural form.

        Arguments:


          domain -- the name of the domain, form which this text origins.

        Returns a unicode string.

        """
        pass


class NullTranslator(Translator):
    """A translator which just returns identical strings as translations."""

    def gettext(self, text, domain=None, origin=None):
        return text

    def ngettext(self, singular, plural, n, domain=None, origin=None):
        return n == 1 and singular or plural


class GettextTranslator(Translator):
    """Translator based on the GNU gettext interface."""

    def __init__(self, lang, path=(), default_domain='lcg', fallback=False, **kwargs):
        """Initialize the instance.

        Arguments:

          lang -- target language code as a string.

          default_domain -- the name of the default domain, used when the translatable has no
            explicit domain defined.

          path -- a sequence of directory names to search for translations.
            The listed directories should contain the locale subdirectories as
            usual with GNU getext (eg. 'de/LC_MESSAGES/domain.mo', where 'de'
            is the language code and 'domain' is the translation domain name).

          fallback -- if true, the translator will silently use a null translation in case the
            desired translation files are not found.

        """
        assert isinstance(lang, basestring), lang
        assert isinstance(path, (list, tuple)), path
        assert isinstance(default_domain, basestring), default_domain
        assert isinstance(fallback, bool), fallback
        self._default_domain = default_domain
        self._fallback = fallback
        self._path = tuple(path)
        self._cache = {}
        super(GettextTranslator, self).__init__(lang, **kwargs)

    def _gettext_instance(self, domain, origin):
        import gettext
        for dir in self._path:
            try:
                return gettext.translation(domain, dir, (self._lang,))
            except IOError:
                continue
        # The MO file was not found.
        msg = "No translation file found: domain=%r, path=%r, lang=%r, origin=%r" % \
              (domain, self._path, self._lang, origin)
        if self._fallback or self._lang == origin:
            if self._lang != origin:
                lcg.log(msg)
            return gettext.NullTranslations()
        else:
            raise IOError(msg)

    def _cached_gettext_instance(self, domain, origin):
        try:
            gettext = self._cache[(domain, origin)]
        except KeyError:
            gettext = self._cache[(domain, origin)] = self._gettext_instance(domain, origin)
            if sys.version_info[0] == 2:
                gettext.gettext = gettext.ugettext
                gettext.ngettext = gettext.ungettext
        return gettext

    def gettext(self, text, domain=None, origin=None):
        domain = domain or self._default_domain
        gettext = self._cached_gettext_instance(domain, origin)
        return gettext.gettext(text)

    def ngettext(self, singular, plural, n, domain=None, origin=None):
        domain = domain or self._default_domain
        gettext = self._cached_gettext_instance(domain, origin)
        result = gettext.ngettext(singular, plural, n)
        return result


class Localizer(object):
    """Localizer of localizable objects.

    A localizer is able to localize different 'Localizable' objects, such as
    'TranslatableText', 'LocalizableDateTime' or 'Concatenation' instances.
    'TranslatableText' instances coming from different gettext domains can be
    mixed.


    """
    _translator_cache = {}
    _locale_data_cache = {}

    @classmethod
    def _get_translator(cls, lang, translation_path):
        key = (lang, tuple(translation_path))
        try:
            translator = cls._translator_cache[key]
        except KeyError:
            if lang is None:
                translator = NullTranslator()
            else:
                translator = GettextTranslator(lang, path=translation_path, fallback=True)
            cls._translator_cache[key] = translator
        return translator

    @classmethod
    def _get_locale_data(cls, lang):
        try:
            locale_data = cls._locale_data_cache[lang]
        except KeyError:
            try:
                locale_data_class = getattr(lcg, 'LocaleData_' + (lang or ''))
            except AttributeError:
                locale_data_class = lcg.LocaleData
            cls._locale_data_cache[lang] = locale_data = locale_data_class()
        return locale_data

    def __init__(self, lang=None, translation_path=(), timezone=None):
        assert lang is None or isinstance(lang, basestring)
        assert timezone is None or isinstance(timezone, datetime.tzinfo)
        self._lang = lang
        self._timezone = timezone
        self._translator = self._get_translator(lang, translation_path)
        self._locale_data = self._get_locale_data(lang)

    def lang(self):
        """Return the target language of this localizer."""
        return self._lang

    def timezone(self):
        """Return the target time zone for output datetime conversion."""
        return self._timezone

    def locale_data(self):
        """Return the locale data for the current locale as a 'LocaleData' instance."""
        return self._locale_data

    def translator(self):
        """Return the currently user 'Translator' instance."""
        return self._translator

    def localize(self, text):
        """Return the localized string for given localizable or string instance.

        The argument may be a 'Localizable' instance or a plain or unicode
        string instance.

        Returns a string or unicode depending if there was a unicode type
        within the input (as well as 'Concatenation.localize()'.

        """
        if isinstance(text, Localizable):
            return text.localize(self)
        else:
            return text

    translate = localize
    """Deprecated backwards compatibility alias - please use 'localize' instead."""


def concat(*args, **kwargs):
    """Concatenate the 'args' into a 'Concatenation' or a string.

    This function has the same effect as creating a 'Concatenation' by calling
    its constructor, but the items can be passed as positional arguments for
    convenience.  Keyword arguments are passed on without change.

    One special case is handled differently.  When the whole concatenation is an
    ordinary Python string or unicode type (there were no 'Localizable'
    instances within the input), this string is returned directly (without the
    surrounding 'Concatenation' instance).

    See 'Concatenation' constructor for more information about the arguments.

    """
    # Optimization: It may slow down processing in some cases but I guess it
    # usually helps a bit.
    if not kwargs:
        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            args = args[0]
        for a in args:
            if not isinstance(a, basestring) or isinstance(a, Localizable):
                break
        else:
            if len(args) == 0:
                return u''
            else:
                return reduce(operator.add, args[1:], args[0])
    # Standard processing
    result = Concatenation(args, **kwargs)
    items = list(result.items())
    if len(items) == 1 and not isinstance(items[0], Localizable):
        return items[0]
    return result


def format(template, *args, **kwargs):
    """Return a translatable string with interpolated format values.

    Positional interpolation variables are passed as positional arguments,
    named variables are passed as keyword arguments.

    This is a translatable replacement of Python's built in string formatting
    operator %.  Python's built in formatting returns a plain Python string or
    unicode object and thus destroys the translatability.  Use this function if
    you need a translatable result.  All interpolation variables may be
    translatable objects and the result remains a translatable object.  The
    translated result is simply the result of python's built in formatting, but
    all interpolation variables are translated *before* interpolation, so the
    behavior and available formatting conversion characters are otherwise the
    the same as for standard Python's formatting.

    """
    return TranslatableText(template, *args, **kwargs)
