# Author: Tomas Cerha <cerha@brailcom.org>
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
        
    def __call__(self, text, *args, **kwargs):
        kwargs['_domain'] = self._domain
        kwargs['_origin'] = self._origin
        return TranslatableText(text, *args, **kwargs)
    

class Localizable(unicode):
    """Common superclass of all localizable classes.

    This class is derived from Python 'unicode' type.  Thus it behaves as an
    ordinary Python string.  However, performing string operations, such as
    string formatting, substitution, etc leads to the loss of translation
    information.  In such a case the instance is unavoidably converted to an
    ordinary unicode string by Python and translation can not be performed
    anymore.  This is why there is the 'Concatenation' class, which protects
    the 'TranslatableText' instance while allowing to mix it with ordinary
    strings.

    To preserve the 'Localizable' instances, only the following operations are
    permitted:

      * concatenation using the 'concat' function defined below.
      
      * concatenation using the '+' operator with other string, unicode,
        'TranslatableText' or 'Concatenation' instances.

    """
    def __add__(self, other):
        if not isinstance(other, (str, unicode)):
            return NotImplemented
        return concat((self, other))

    def __radd__(self, other):
        if not isinstance(other, (str, unicode)):
            return NotImplemented
        return concat((other, self))

    
class TranslatableText(Localizable):
    """Translatable string with a delayed translation.

    The instances of this class can be mixed with ordinary Python strings
    (plain or unicode) strings using the 'Concatenation' class defined below.
    Then the exporter is capable to translate all translatable strings within
    the content at one place to the desired output language.

    As oposed to the ordinary gettext mechanism, the delayed translation allows
    us to build the content first and translate it afterwards.

    Instances must be treated cerefully to prevent losing the translation
    information as described in 'Localizable' class documentation.  In addition
    to the safe operations described there, the following two operations are
    also safe on this class.

      * replacement using the 'replace' method.

      * simple ``formatting'' using the 'format' function defined below.

    
    """
    _RESERVED_ARGS = ()
    
    class _Interpolator(object):
        def __init__(self, interpole, translate):
            self._interpole = interpole
            self._translate = translate
        def __getitem__(self, key):
            return self._translate(self._interpole(str(key)))
    
    def __new__(cls, text, *args, **kwargs):
        values = args or dict([(k,v) for k,v in kwargs.items()
                               if not k.startswith('_') and not k in cls._RESERVED_ARGS])
        if values:
            text %= values
        return unicode.__new__(cls, text)

    def __init__(self, text, *args, **kwargs):
        """Initialize the instance.

        Arguments:

          text -- the actual text to translate as a string or unicode instance.

          args -- positional substitution values (see below).
          
          kwargs -- named substitution arguments (see below).

        If 'args' or 'kwargs' are passed, the 'text' is considered a format
        string and it will be automatically interpolated after translation.
        The interpolation must be done after the translation, because we need
        the base string, not the interpolated one for translation.  And because
        the translation is defered, the substitution of the formatting
        variables must be also defered.  This makes the difference between
        using standatad gettex as the '_()' construct and using the
        'TranslatableText' for the same.  With standard gettext, we get the
        translated version right away and we can substitute the variables in
        place.  However with 'TranslatableText', we must pass the variables to
        its constructor and let the instance interplate them later.

        Note, that only 'args' or only 'kwargs' may be passed (not both at
        once).  This depends whether you are using named variables in the
        format string or just positional substitution.  It is recommended to
        use named format variables (with keyword arguments), especially when
        there is more than one variable within the string.
        
        """
        assert isinstance(text, (str, unicode)), (text, type(text))
        self._text = text
        self._args = args
        self._init_kwargs(**kwargs)
        assert not args or not self._kwargs, (text, args, self._kwargs)

    def _init_kwargs(self, _transforms=(), _domain=None, _origin='en', _interpolate=None,
                     **kwargs):
        assert isinstance(_transforms, tuple), _transforms
        assert isinstance(_domain, (str)) or _domain is None, _domain
        assert isinstance(_origin, (str)), _origin
        assert _interpolate is None or callable(_interpolate), _interpolate
        self._transforms = _transforms
        self._domain = _domain
        self._origin = _origin
        self._interpolate = _interpolate
        self._kwargs = kwargs

    def _clone_kwargs(self):
        return dict(self._kwargs, _domain=self._domain, _origin=self._origin,
                    _transforms=self._transforms, _interpolate=self._interpolate)
    
    def _clone(self, **kwargs):
        kwargs = dict(self._clone_kwargs(), **kwargs)
        return self.__class__(self._text, *self._args, **kwargs)
        
    def domain(self):
        """Return the domain name bound to this instance."""
        return self._domain
        
    def interpolate(self, func):
        """Return a new TranslatableText instance using given interpolation function.

        The intrpolation is not performed immediately.  It is left to translation time and also
        translation of the interpolated arguments is performed.  The function passed to this method
        must take one argument -- the interpolation variable name -- and return a string.  The
        original instance must be created without any interpolation arguments passed to the
        constructor if you want to call this method on it.

        """
        return self._clone(_interpolate=func)
        
    def replace(self, old, new):
        """Return a new TranslatableText instance which replaces 'old' by 'new'.

        This is the analogy of the string method of the same name and
        arguments.  Here the replacement is left after the translation and
        variable interpolation.  Thus the actual replace is automatically

        """
        transforms = self._transforms + (lambda x: x.replace(old, new),)
        return self._clone(_transforms=transforms)

    def _translate(self, translator):
        return translator.gettext(self._text, domain=self._domain, origin=self._origin)

    def translate(self, translator):
        """Return the translated and interpolated string.
        
        Arguments:

          translator -- a 'Translator' instance.

        The returned string has all the format variables interpolated.  Also
        all values of the format variables are translated (using the same
        function) before interpolation, if they are TranslatableText or
        Concatenation instances.

        Note, that a TypeError may be raised, when the constructor arguments
        didn't correspond to the format string.

        """
        assert isinstance(translator, Translator)
        def translate(x):
            if isinstance(x, Localizable):
                return translator.translate(x)
            else:
                return x
        result = self._translate(translator)
        if self._args:
            result %= tuple([translate(arg) for arg in self._args])
        elif self._interpolate:
            result %= self._Interpolator(self._interpolate, translate)
        elif self._kwargs:
            result %= dict([(k, translate(v)) for k, v in self._kwargs.items()])
        for transform in self._transforms:
            result = transform(result)
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
        
    
class LocalizableDateTime(Localizable):
    """Date/time string which can be converted to a localized format.
    
    See the rules in 'Localizable' class documentation for more information
    about mixing instances of this class with other strings.
    
    """
    _RE = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)(?: (\d\d):(\d\d)(?::(\d\d))?)?$')

    def __new__(cls, text, **kwargs):
        return unicode.__new__(cls, text)
    
    def __init__(self, string, show_weekday=False, show_time=None):
        super(LocalizableDateTime, self).__init__(string)
        m = self._RE.match(string)
        if not m:
            raise Exception("Invalid date/time format", self)
        numbers = [int(n) for n in m.groups() if n is not None]
        self._datetime = datetime.datetime(*numbers)
        self._show_weekday = show_weekday
        self._show_time = show_time is None and len(numbers) > 3 or show_time
        self._show_seconds = len(numbers) > 5
    
    def format(self, data):
        format = data.date_format
        if self._show_time:
            format += ' '+ (self._show_seconds and data.exact_time_format or data.time_format)
        result = self._datetime.strftime(format)
        if self._show_weekday:
            result = data.weekdays[self._datetime.weekday()] + ' ' + result
        return result


class Concatenation(Localizable):
    """A concatenation of translatable and untranslatable text elements.

    Represents a block of text, where ordinary python strings, unicode strings
    and 'Localizable' instances are concatenated to make the final text.

    As well as with 'TranslatableText', using an instance of this class in a
    string (or unicode) context leads to the loss of translation information.
    See the documentation of 'TranslatableText' for more information.
    
    """
    def __new__(cls, *items, **kwargs):
        sep = (lambda separator='': separator)(**kwargs)
        def x(item):
            if isinstance(item, (list, tuple)):
                return sep.join(item)
            else:
                return item
        return unicode.__new__(cls, sep.join([x(item) for item in items]))
    
    def __init__(self, *items, **kwargs):
        """Initialize the instance.

        Arguments:

          items -- any number of items may be specified as positional
            arguments.  All these arguments are used to make the final text in
            concatenation.  Each item may be a string, a unicode string, a
            'Localizable' instance, a 'Concatenation' instance, tuple or list.
 
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
            
        """
        
        separator = (lambda separator='': separator)(**kwargs)
        def append(array, item):
            if isinstance(item, Concatenation):
                for p in item.items():
                    append(array, p)
            else:
                assert isinstance(item, (str, unicode)), item
                if not isinstance(item, Localizable) and array \
                       and not isinstance(array[-1], Localizable):
                    array[-1] +=  item
                else:                
                    array.append(item)
        self._items = myitems = []
        last = len(items) - 1
        for i, item in enumerate(items):
            if isinstance(item, (tuple, list)):
                item = Concatenation(*item, **dict(separator=separator))
            #if item is None or item == "":
            #    continue
            append(myitems, item)
            if i != last:
                append(myitems, separator)
        
    def replace(self, old, new):
        """Apply the method to all items and return a new Concatenation.

        The 'replace()' method with given arguments will be applied to all
        arguments and a new Concatenation instance will be returned with the
        modified arguments.  See 'string.replace()' and
        'TranslatableText.replace()' for more information.

        """
        return concat([item.replace(old, new) for item in self._items])

    def items(self):
        """Return the list of items included in this concatenation.

        You can not rely on any relevance of the items passed to the
        constructor and the final items returned by this method.  It is only
        guaranted, that the items will form the same output string.  They may
        be, however, internally merged or otherwise reorganized.

        The items returned byt this method are always either strings, unicode
        strings, 'TranslatableText' or 'LocalizableDateTime' instances.
        
        """
        return self._items
        
    def translate(self, translator):
        """Return the translated text as a string ot a unicode string.

        Arguments:

          translator -- a 'Translator' instance.

        If there was at least one unicode type argument, or if the 'translator'
        returnes unicode values, the result will be a unicode type.  If all the
        input are plain strings, a plain string is returned.
        
        """
        return ''.join([translator.translate(item) for item in self._items])


class Translator(object):
    """A generic translator of translatable objects.

    A translator should be able to translate different translatable objects,
    such as 'TranslatableText' and 'Concatenation' instances.  Also
    'LocalizableDateTime' instances will be formatted to a proper output
    format.  'Concatenation' instances may contain 'TranslatableText' instances
    coming from different domains and a translator should be able to deal with
    them.

    This is class only defines the basic tr.  See 'GettextTranslator'
    or 'NullTranslator' for concrete implementations.

    """
    def __init__(self):
        self._locale_data = LocaleData(self)
        
    def lang(self):
        """Return the target language of this translator."""
        return None

    def gettext(self, text, domain=None, origin=None):
        """Return the translation of the string 'text' from given domain.

        Arguments:

          text -- the text to translate as a string or unicode instance.

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
        if isinstance(text, (Concatenation, TranslatableText)):
            return text.translate(self)
        elif isinstance(text, Localizable):
            return text.format(self._locale_data)
        else:
            return text


class NullTranslator(Translator):
    """A translator which just returns identical strings as translations."""
    
    def gettext(self, text, domain=None, origin=None):
        return text

    
class GettextTranslator(Translator):
    """Translator based on the GNU gettext interface."""
    
    def __init__(self, lang, path=None, default_domain='lcg', fallback=False):
        """Initialize the instance.

        Arguments:

          lang -- target language code as a string.

          default_domain -- the name of the default domain, used when the translatable has no
            explicit domain defined.

          path -- a dictionary, which may assign an arbitrary directory to each domain.  This
            directory should contain the locale subdirectories as usual with GNU getext
            (eg. 'de/LC_MESSAGES/domain.mo').  If there is no item for a domain, the directory
            defaults to 'config.translation_dir'.

          fallback -- if true, the translator will silently use a null translation in case the
            desired translation files are not found.
        
        """
        assert isinstance(lang, str), lang
        assert isinstance(default_domain, str), default_domain
        assert isinstance(path, dict) or path is None, path
        assert isinstance(fallback, bool), fallback
        self._lang = lang
        self._default_domain = default_domain
        self._fallback = fallback
        self._path = path or {}
        self._cache = {}
        super(GettextTranslator,self).__init__()

    def lang(self):
        return self._lang
    
    def _gettext_instance(self, domain, origin):
        import gettext, config
        path = self._path.get(domain, config.translation_dir)
        try:
            return gettext.translation(domain, path, (self._lang,))
        except IOError, e:
            # The MO file was not found.
            msg = str(e)+", path: '%s', lang: '%s', origin: '%s'" % (path, self._lang, origin)
            if self._fallback or self._lang == origin:
                if self._lang != origin:
                    log(msg)
                return gettext.NullTranslations()
            else:
                raise IOError(msg)
        
    def gettext(self, text, domain=None, origin=None):
        domain = domain or self._default_domain
        try:
            t = self._cache[(domain, origin)]
        except KeyError:
            t = self._cache[(domain, origin)] = self._gettext_instance(domain, origin)
        return t.ugettext(text)

    
_ = TranslatableTextFactory('lcg-locale')

class LocaleData(object):
    date_format = _('%Y-%m-%d')
    time_format = _('%H:%M')
    exact_time_format = _('%H:%M:%S')
    weekdays = (_('Mon'), _('Tue'), _('Wed'), _('Thu'), _('Fri'), _('Sat'), _('Sun'))
    negative_sign = '-'
    positive_sign = ''
    decimal_point = '.'
    thousands_sep = ','
    grouping = (3,)
    mon_decimal_point = None
    mon_thousands_sep = None 
    mon_grouping = None
 
    def __init__(self, translator):
        self.date_format = str(translator.translate(self.date_format))
        self.time_format = str(translator.translate(self.time_format))
        self.exact_time_format = str(translator.translate(self.exact_time_format))
        self.weekdays = tuple([translator.translate(day) for day in self.weekdays])
        if self.mon_decimal_point is None:
            self.mon_decimal_point = self.decimal_point
        if self.mon_thousands_sep is None:
            self.mon_thousands_sep = self.thousands_sep
        if self.mon_grouping is None:
            self.mon_grouping = self.grouping
            

def concat(*args, **kwargs):
    """Concatenate the 'args' into a 'Concatenation' or a string.

    This function has exactly the same effect as creating a 'Concatenation' by
    calling its constructor.  All the arguments are the same.  The only
    difference is, that when the whole concatenation is a plain Python string
    (there were no translatable texts within the input), this string is
    returned directly (without the surrounding 'Concatenation' instance).

    See 'Concatenation' constructor for more information about the arguments.

    """
    result = Concatenation(*args, **kwargs)
    items = result.items()
    if len(items) == 1 and not isinstance(items[0], TranslatableText):
        return items[0]
    return result

def format(text, *args):
    """A 'Concatenation' constructor for very simplified string formatting.

    This function allows to construct a Concatenation using a format-like
    construct.  It is however very limited.  The ONLY suported format is '%s'
    and only positional arguments are converted.  It, however, becomes handy
    in certain cases.

    Example:

       format('Hi %s, say hello to %s.', 'Bob', 'John')

    This is the same like:

       concat('Hi ', 'Bob', ', say hello to ', 'John', '.')

    Of course, with plain strings this makes no sense, but when the arguments
    are translatable texts, the original instances are preserved.

    """
    return concat(reduce(lambda a,b: a+b, zip(text.split('%s'), args+('',))))


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
            module = imp.load_module(name, file, pathname, descr)
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
    sys.path.append(directory)
    print " ".join(source_files_by_domain(directory, domain=domain))
