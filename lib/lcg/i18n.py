# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2015 Brailcom, o.p.s.
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

import lcg

import collections
import datetime
import operator
import os
import re
import string
import sys

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
    def __init__(self, domain, origin='en', lang=None, translation_path=()):
        """Arguments:
        
          domain, origin -- as in base class.
        
          lang -- target language code as a string.

          translation_path -- a sequence of directory names to search for
            translations.  As in 'GettextTranslator'.
        
        """
        # Create localizer to make use of its translator instance cache.
        localizer = lcg.Localizer(lang=lang, translation_path=translation_path, timezone=None)
        self._translator = localizer.translator()
        super(TranslatedTextFactory, self).__init__(domain, origin=origin)

    def _gettext(self, text):
        return self._translator.gettext(text, domain=self._domain, origin=self._origin)

    def __call__(self, text, *args, **kwargs):
        kwargs['_orig_text'] = text
        return super(TranslatedTextFactory, self).__call__(self._gettext(text), *args, **kwargs)
    
    def ngettext(self, singular, plural, *args, **kwargs):
        kwargs['_singular_orig_text'] = singular
        kwargs['_plural_orig_text'] = plural
        return super(TranslatedTextFactory, self).ngettext(self._gettext(singular),
                                                           self._gettext(plural),
                                                           *args, **kwargs)
    

class Localizable(unicode):
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
        for f in _transforms:
            text = f(text)
        try:
            return unicode.__new__(cls, text)
        except UnicodeDecodeError:
            # Necessary to display some tracebacks
            def escape(text):
                return re.sub(r'[^\x01-\x7F]', '?', text)
            return unicode.__new__(cls, escape(text))

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
        return (unicode(self),)
    
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
    _RESERVED_ARGS = ()
    
    class _Interpolator(object):
        def __init__(self, func, localizer):
            self._func = func
            self._localizer = localizer
        def __getitem__(self, key):
            value = self._func(str(key))
            localized_value = self._localizer.localize(value)
            if isinstance(value, lcg.HtmlEscapedUnicode):
                localized_value = lcg.HtmlEscapedUnicode(value, escape=True)
            return localized_value
    
    def __new__(cls, text, *args, **kwargs):
        if not args or __debug__:
            substitution_dict = dict([(k, v) for k, v in kwargs.items()
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

    def _init_kwargs(self, _orig_text=None, _domain=None, _origin='en', _interpolate=None,
                     _transforms=(), **kwargs):
        assert isinstance(_domain, basestring) or _domain is None, _domain
        assert isinstance(_origin, basestring), _origin
        assert _interpolate is None or isinstance(_interpolate, collections.Callable), _interpolate
        self._orig_text = _orig_text or self._text
        self._domain = _domain
        self._origin = _origin
        self._interpolate = _interpolate
        self._kwargs = kwargs
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
        translated = translator.gettext(self._orig_text, domain=self._domain, origin=self._origin)
        if isinstance(self._orig_text, lcg.HtmlEscapedUnicode):
            translated = lcg.HtmlEscapedUnicode(translated, escape=True)
        return translated

    def _localize(self, localizer):
        result = self._translate(localizer)
        if self._args:
            result %= tuple([localizer.localize(arg) for arg in self._args])
        elif self._interpolate:
            result %= self._Interpolator(self._interpolate, localizer)
        elif self._kwargs:
            result %= dict([(k, localizer.localize(v)) for k, v in self._kwargs.items()])
        return result


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
    _RESERVED_ARGS = ('translations',)

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
            assert 'n' in kwargs, \
                   "A number determining the plural form must be passed as keyword argument 'n'."
            n = kwargs['n']
        assert isinstance(n, int)
        text = n == 1 and singular or plural
        return TranslatableText.__new__(cls, text, *args, **kwargs)

    def __init__(self, singular, plural, *args, **kwargs):
        if args:
            n = args[0]
        else:
            n = kwargs['n']
        text = n == 1 and singular or plural
        self._singular = unicode(singular)
        self._plural = unicode(plural)
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

    def __init__(self, string, show_weekday=False, show_time=True, leading_zeros=True, utc=False,
                 **kwargs):
        """Initialize the instance.

        Arguments:

          string -- the input date/datetime string in format 'yyyy-mm-dd' for
            date values and 'yyyy-mm-dd HH:MM' or 'yyyy-mm-dd HH:MM:SS' for
            datetime values.  The time precision used on input is respected on
            output.
          show_weekday -- if true, abbreviated localized week day name is added
            to the date/datetime value on output.
          show_time -- if true and the 'string' contains the time part (it is a
            datetime value) the time is also shown on output.  If false, the
            time part is never shown.
          leading_zeros -- if true the numeric values are always padded by
            leading zeros on output to maintain the same character width for
            any value.
          utc -- if true, the time is supposed to be in UTC and will be
            converted to the local time zone on translation.  If false, the
            time is supposed to be in local time zone and no conversion
            applies.

        """
        super(LocalizableDateTime, self).__init__(**kwargs)
        m = self._RE.match(string)
        if not m:
            raise Exception("Invalid date/time format", self)
        numbers = [int(n) for n in m.groups() if n is not None]
        if utc:
            tz = self._UTC_TZ
        else:
            tz = None
        self._datetime = datetime.datetime(*numbers, tzinfo=tz)
        self._show_weekday = show_weekday
        self._leading_zeros = leading_zeros
        self._has_time = len(numbers) > 3
        self._show_time = show_time
        self._show_seconds = len(numbers) > 5
        self._utc = utc

    def _clone_kwargs(self):
        return dict(super(LocalizableDateTime, self)._clone_kwargs(),
                    show_weekday=self._show_weekday,
                    show_time=self._show_time,
                    leading_zeros=self._leading_zeros,
                    utc=self._utc)

    def _localize(self, localizer):
        data = localizer.locale_data()
        dt = self._datetime
        displayed_timezone = ''
        if self._has_time and self._utc:
            timezone = localizer.timezone() or data.default_timezone
            if timezone is not None:
                dt = dt.astimezone(timezone)
            else:
                displayed_timezone = ' UTC'
        result = dt.strftime(data.date_format)
        if not self._leading_zeros:
            result = self._LEADING_ZEROS.sub('', result)
        if self._has_time and self._show_time:
            time_format = (self._show_seconds and data.exact_time_format or data.time_format)
            result += ' ' + dt.strftime(time_format)
        if self._show_weekday:
            weekday = localizer.localize(lcg.week_day_name(dt.weekday(), abbrev=True))
            result = weekday + ' ' + result
        return result + displayed_timezone


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
            if isinstance(items, (list, tuple,)):
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
                if x.__class__ in (unicode, str,):
                    if h_escape:
                        x = lcg.HtmlEscapedUnicode(x, escape=True)
                    last.append(x)
                    last.append(separator)
                elif isinstance(x, Concatenation) and not x._transforms:
                    s = lcg.HtmlEscapedUnicode('', escape=False) if h_escape else ''
                    flatten(x.items(), separator=s)
                    last.append(separator)
                elif isinstance(x, Localizable):
                    text = string.join(last, '')
                    if text:
                        if h_escape:
                            text = lcg.HtmlEscapedUnicode(text, escape=False)
                        flat.append(text)
                    del last[:]
                    flat.append(x)
                    last.append(separator)
                elif isinstance(x, (unicode, str,)):
                    # This is a quick fix for special unicode/str subclasses, such as
                    # HtmlExporter._JavaScriptCode.  Reordering the conditions would
                    # make sense, but it might harm the optimization effort.
                    if h_escape:
                        x = lcg.HtmlEscapedUnicode(x, escape=True)
                    last.append(x)
                    last.append(separator)
                else:
                    assert isinstance(x, (tuple, list,)), (x.__class__, repr(x))
                    flatten(x)
        flatten(items)
        if len(last) > 1:
            text = reduce(operator.add, last[1:-1], last[0])
            if text:
                flat.append(text)

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
        return gettext

    def gettext(self, text, domain=None, origin=None):
        domain = domain or self._default_domain
        gettext = self._cached_gettext_instance(domain, origin)
        return gettext.ugettext(text)

    def ngettext(self, singular, plural, n, domain=None, origin=None):
        domain = domain or self._default_domain
        gettext = self._cached_gettext_instance(domain, origin)
        result = gettext.ungettext(singular, plural, n)
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
            locale_data = globals().get('LocaleData_' + (lang or ''), lcg.LocaleData)()
            cls._locale_data_cache[lang] = locale_data
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
        if len(args) == 1 and isinstance(args[0], (list, tuple,)):
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
    items = result.items()
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


def source_files_by_domain(basedir, domain=None):
    """Return the list of all Python source files, which belong to given domain.

    Arguments:

      basedir -- base directory where the source files are searched
        recursively.

      domain -- the name of the translation domain as a string.  This domain
        corresponds to the 'domain' argument of the 'TranslatableTextFactory'
        used within the source file to define the '_' identifier.  In no domain
        is passed, a list of all Python source files is returned.

    The returned list contains full pathnames of the files as strings.

    """
    def find(searchpath):
        result = []
        for item in os.listdir(searchpath):
            path = os.path.join(searchpath, item)
            if os.path.isfile(path) and item.endswith('.py') and item not in ('__init__.py'):
                result.append(path)
            elif os.path.isdir(path):
                result.extend(find(path))
        return result
    files = find(basedir)
    if domain is None:
        return files
    else:
        result = []
        import imp
        for filename in files:
            name = os.path.splitext(os.path.basename(filename))[0]
            path = os.path.dirname(filename)
            file, pathname, descr = imp.find_module(name, [path])
            try:
                sys.path.append(path)
                module = imp.load_module(name, file, pathname, descr)
            finally:
                file.close()
                sys.path.pop()
            if '_' in module.__dict__:
                x = module.__dict__['_']
                if isinstance(x, lcg.TranslatableTextFactory) and x.domain() == domain:
                    result.append(filename)
        return result


if __name__ == '__main__':
    """Get the list of all Python source files within a directory:

      python -m lcg/i18n directory

    Get the list of all source files which define the '_' operator as a 'TranslatableTextFactory'
    for a particular domain:

      python -m lcg/i18n directory domain

    This is mainly useful for generating Makefile dependencies.  See 'source_files_by_domain()' for
    more details.

    """
    assert len(sys.argv) in (2, 3), \
        "Usage: python -m lcg/i18n directory [domain]"
    directory = sys.argv[1]
    domain = len(sys.argv) == 3 and sys.argv[2] or None
    print " ".join(source_files_by_domain(directory, domain=domain))
