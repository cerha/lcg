# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2011 Brailcom, o.p.s.
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

from lcg import *

import re, datetime

class TranslatableTextFactory(object):
    """A helper for defining the '_' identifier bound to a certain domain.

    You may define the '_' function as follows:

      _ = TranslatableTextFactory('domain-name')

    """
    def __init__(self, domain, origin='en'):
        assert isinstance(domain, str), domain
        assert isinstance(origin, str), origin
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
        return unicode.__new__(cls, text)

    def __init__(self, _transforms=()):
        assert isinstance(_transforms, tuple), _transforms
        self._transforms = _transforms
    
    def __add__(self, other):
        if not isinstance(other, (str, unicode)):
            return NotImplemented
        return concat((self, other))

    def __radd__(self, other):
        if not isinstance(other, (str, unicode)):
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
    
    def _localize(self, translator):
        raise Exception("This method must be overriden!")
        
    def transform(self, function):
        """Return a copy performing given transformation after localization.

        Creates a copy of the instance which applies given 'function' on the
        final string after the dalayed localization.  The function will receive
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

    def localize(self, translator):
        """Return the localized version of the instance as a string.

        Arguments:

          translator -- a 'Translator' instance.

        The returned string cen be unicode or plain string depending on the
        original instance (and its type) and also on the translator.

        """
        result = self._localize(translator)
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
        def __init__(self, func, translator):
            self._func = func
            self._translator = translator
        def __getitem__(self, key):
            return self._translator.translate(self._func(str(key)))
    
    def __new__(cls, text, *args, **kwargs):
        if not args or __debug__:
            substitution_dict = dict([(k,v) for k,v in kwargs.items()
                                      if not k.startswith('_') and not k in cls._RESERVED_ARGS])
            assert not args or not substitution_dict, \
                   "Can not pass both positional and keyword substitution variables: " + \
                   "(%s, %s, %s)" % (text, args, substitution_dict)
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
        assert isinstance(text, (str, unicode)), (text, type(text))
        self._text = text
        self._args = args
        self._init_kwargs(**kwargs)

    def _init_kwargs(self, _domain=None, _origin='en', _interpolate=None, _transforms=(), **kwargs):
        assert isinstance(_domain, (str)) or _domain is None, _domain
        assert isinstance(_origin, (str)), _origin
        assert _interpolate is None or callable(_interpolate), _interpolate
        self._domain = _domain
        self._origin = _origin
        self._interpolate = _interpolate
        self._kwargs = kwargs
        super(TranslatableText, self).__init__(_transforms=_transforms)

    def _clone_args(self):
        return (self._text,) + self._args
    
    def _clone_kwargs(self):
        return dict(super(TranslatableText, self)._clone_kwargs(), _domain=self._domain, 
                    _origin=self._origin, _interpolate=self._interpolate, **self._kwargs)
    
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
        
    def _translate(self, translator):
        return translator.gettext(self._text, domain=self._domain, origin=self._origin)

    def _localize(self, translator):
        result = self._translate(translator)
        if self._args:
            result %= tuple([translator.translate(arg) for arg in self._args])
        elif self._interpolate:
            result %= self._Interpolator(self._interpolate, translator)
        elif self._kwargs:
            result %= dict([(k, translator.translate(v)) for k, v in self._kwargs.items()])
        return result


class SelfTranslatableText(TranslatableText):
    """Translatable string capable of self-translation.

    The translations of this string are pre-defined by passing them as a constructor argument.  The
    instance than translates itself -- the translator is only used to find out the target language.

    As oposed to the translator-based translation, which uses translation catalogs, this class is
    handy when the translation string is part of application data, rather than application
    definition -- for example when the translated term and its translations are user defined
    strings stored in a database.

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
    
    def _translate(self, translator):
        return self._translations.get(translator.lang(), translator.translate(self._text))
        

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
            assert kwargs.has_key('n'), \
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
        super(TranslatablePluralForms, self).__init__(text, *args, **kwargs)
        self._singular = unicode(singular)
        self._plural = unicode(plural)
        self._n = n

    def _clone_args(self):
        return (self._singular, self._plural) + self._args
    
    def _translate(self, translator):
        return translator.ngettext(self._singular, self._plural, self._n,
                                   domain=self._domain, origin=self._origin)
    
    
class LocalizableDateTime(Localizable):
    """Date/time string which can be converted to a localized format.
    
    See the rules in 'Localizable' class documentation for more information
    about mixing instances of this class with other strings.
    
    """
    _RE = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)(?: (\d\d):(\d\d)(?::(\d\d))?)?$')
    _LEADING_ZEROS = re.compile(r'(?<!\d)0+')

    def __init__(self, string, show_weekday=False, show_time=None, leading_zeros=True, **kwargs):
        super(LocalizableDateTime, self).__init__(**kwargs)
        m = self._RE.match(string)
        if not m:
            raise Exception("Invalid date/time format", self)
        numbers = [int(n) for n in m.groups() if n is not None]
        self._datetime = datetime.datetime(*numbers)
        self._show_weekday = show_weekday
        self._leading_zeros = leading_zeros
        self._show_time = show_time is None and len(numbers) > 3 or show_time
        self._show_seconds = len(numbers) > 5
    
    def _localize(self, translator):
        data = translator.locale_data()
        result = self._datetime.strftime(data.date_format)
        if not self._leading_zeros:
            result = self._LEADING_ZEROS.sub('', result)
        if self._show_time:
            time_format = (self._show_seconds and data.exact_time_format or data.time_format)
            result += ' '+ self._datetime.strftime(time_format)
        if self._show_weekday:
            weekday = translator.translate(week_day_name(self._datetime.weekday(), abbrev=True))
            result = weekday + ' ' + result
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
    
    def _localize(self, translator):
        data = translator.locale_data()
        time_format = (self._show_seconds and data.exact_time_format or data.time_format)
        return self._time.strftime(time_format)


class Decimal(Localizable):
    """Localizable decimal number."""
    
    def __new__(cls, value, precision=None, **kwargs):
        if precision is None:
            format = '%f'
        else:
            format = '%%.%df' % precision
        return Localizable.__new__(cls, format % value, **kwargs)

    def __init__(self, value, precision=None, **kwargs):
        self._value = value
        if precision is None:
            self._format = '%f'
        else:
            self._format = '%%.%df' % precision
        super(Decimal, self).__init__(**kwargs)

    def _clone_args(self):
        return (self._value,)
    
    def _locales(self, data):
        return data.decimal_point, data.grouping, data.thousands_sep
    
    def _group(self, grouping, thousands_sep, string):
        if not grouping or not thousands_sep:
            return string
        result=""
        while string and grouping:
            if grouping[0] == -1:
                break
            elif grouping[0] != 0:
                #process last group
                group = grouping[0]
                grouping = grouping[1:]
            if result:
                result = string[-group:] + thousands_sep + result
            else:
                result = string[-group:]
            string = string[:-group]
            if len(string) == 1 and string[0] not in "0123456789":
                # the leading string is only a sign
                return string + result
        if not result:
            return string
        if string:
            result = string + thousands_sep + result
        return result
      
    def _localize(self, translator):
        data = translator.locale_data()
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
        def x(item):
            if isinstance(item, (list, tuple)):
                return separator.join(item)
            else:
                return item
        return Localizable.__new__(cls, separator.join([x(item) for item in items]), **kwargs)
    
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
        def append(array, item):
            if isinstance(item, Concatenation) and not item._transforms:
                for p in item.items():
                    append(array, p)
            else:
                assert isinstance(item, basestring), repr(item)
                if not isinstance(item, Localizable) and array \
                       and not isinstance(array[-1], Localizable):
                    array[-1] +=  item
                else:                
                    array.append(item)
        self._items = myitems = []
        last = len(items) - 1
        for i, item in enumerate(items):
            if isinstance(item, (tuple, list)):
                item = Concatenation(item, separator=separator)
            #if item is None or item == "":
            #    continue
            append(myitems, item)
            if i != last:
                append(myitems, separator)
        
    def _clone_args(self):
        return (self._items,)
    
    def _localize(self, translator):
        return ''.join([translator.translate(item) for item in self._items])
    
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

    A translator should be able to localize different 'Localizable' objects,
    such as 'TranslatableText', 'LocalizableDateTime' or 'Concatenation'
    instances.  'TranslatableText' instances coming from different can be mixed.

    This class only defines the basic API.  See 'GettextTranslator' or
    'NullTranslator' for concrete implementations.

    """
    def __init__(self, lang=None):
        self._lang = lang
        self._locale_data = globals().get('LocaleData_'+(lang or ''), LocaleData)()
        
    def lang(self):
        """Return the target language of this translator."""
        return self._lang

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

    def locale_data(self):
        return self._locale_data

    def translate(self, text):
        """Return the translation of given translatable.

        The argument may be a 'Localizable' instance or a plain or unicode
        string instance.

        Returns a string or unicode depending if there was a unicode type
        within the input (as well as 'Concatenation.translate()'.
        
        """
        if isinstance(text, Localizable):
            return text.localize(self)
        else:
            return text


class NullTranslator(Translator):
    """A translator which just returns identical strings as translations."""
    
    def gettext(self, text, domain=None, origin=None):
        return text

    def ngettext(self, singular, plural, n, domain=None, origin=None):
        return n == 1 and singular or plural

    
class GettextTranslator(Translator):
    """Translator based on the GNU gettext interface."""
    
    def __init__(self, lang, path=(), default_domain='lcg', fallback=False):
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
        assert isinstance(lang, str), lang
        assert isinstance(path, (list, tuple)), path
        assert isinstance(default_domain, str), default_domain
        assert isinstance(fallback, bool), fallback
        self._default_domain = default_domain
        self._fallback = fallback
        self._path = tuple(path)
        self._cache = {}
        super(GettextTranslator, self).__init__(lang)

    def _gettext_instance(self, domain, origin):
        import gettext
        for dir in self._path:
            try:
                return gettext.translation(domain, dir, (self._lang,))
            except IOError, e:
                continue
        # The MO file was not found.
        msg = "No translation file found: domain=%r, path=%r, lang=%r, origin=%r" % \
              (domain, self._path, self._lang, origin)
        if self._fallback or self._lang == origin:
            if self._lang != origin:
                log(msg)
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
    result = Concatenation(args, **kwargs)
    items = result.items()
    if len(items) == 1 and not isinstance(items[0], Localizable):
        return items[0]
    return result

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
            if os.path.isfile(path) and item.endswith('.py') \
                   and item not in ('__init__.py'):
                result.append(path)
            elif os.path.isdir(path):
                result.extend(find(path))
        return result
    files = find(basedir)
    if domain is None:
        return files
    else:
        result = []
        import imp, lcg
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
            if module.__dict__.has_key('_'):
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
