# -*- coding: iso8859-2 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006 Brailcom, o.p.s.
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


class TranslatableTextFactory(object):
    """A helper for defining the '_' identifier bound to a certain domain.

    You may define the '_' function as follows:

      _ = TranslatableTextFactory('domain-name')

    """
    def __init__(self, domain):
        assert isinstance(domain, str), domain
        self._domain = domain

    def domain(self):
        """Return the domain name as set in the constructor."""
        return self._domain
        
    def __call__(self, *args, **kwargs):
        kwargs['_domain'] = self._domain
        return TranslatableText(*args, **kwargs)
    

class TranslatableText(unicode):
    """Translatable string with a delayed translation.

    The instances of this class can be mixed with ordinary Python strings
    (plain or unicode) strings using the 'Concatenation' class defined below.
    Then the exporter is capable to translate all translatable strings within
    the content at one place to the desired output language.

    As oposed to the ordinary gettext mechanism, the delayed translation allows
    us to build the content first and translate it afterwards.

    IMPORTANT:

    This class is derived from Python 'unicode' type.  Thus it behaves as an
    ordinary Python string.  However, performing string operations, such as
    concatenation with other python strings, formatting, etc, leads to the loss
    of translation information.  In such a case the instance is unavoidably
    converted to an ordinary unicode string by Python and translation can not
    be performed anymore.  This is why there is the 'Concatenation' class,
    which protects the 'TranslatableText' instance while allowing to mix it
    with ordinary strings.

    To preserve the 'TranslatableText' and 'Concatenation' instances, only the
    following operations are permitted:

      * concatenation using the 'concat' function defined below.
      
      * concatenation using the '+' operator when (and only when) the first
        item in the addition is a 'TranslatableText' or 'Concatenation'
        instance.

      * replacement using the 'replace' method.

      * simple ``formatting'' using the 'format' function defined below.
    
    """
    def __new__(cls, text, *args, **kwargs):
        values = args or dict([(k,v) for k,v in kwargs.items()
                               if not k.startswith('_')])
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

    def _init_kwargs(self, _transforms=(), _domain=None, **kwargs):
        assert isinstance(_transforms, tuple), _transforms
        assert isinstance(_domain, (str)) or _domain is None, _domain
        self._transforms = _transforms
        self._domain = _domain
        self._kwargs = kwargs

    def domain(self):
        """Return the domain name bound to this instance."""
        return self._domain
        
    def replace(self, old, new):
        """Return a TranslatableText instance which replaces old by new.

        This is the analogy of the string method of the same name and
        arguments.  Here the replacement is left after the translation and
        variable interpolation.  Thus the actual replace is automatically

        """
        transforms = self._transforms + (lambda x: x.replace(old, new),)
        kwargs = dict(self._kwargs, _transforms=transforms,
                      _domain=self._domain)
        return TranslatableText(self._text, *self._args, **kwargs)
    
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
            if isinstance(x, (Concatenation, TranslatableText)):
                return x.translate(translator)
            else:
                return x
        result = translator.gettext(self._text, domain=self._domain)
        if self._args:
            result %= tuple([translate(arg) for arg in self._args])
        elif self._kwargs:
            result %= dict([(k, translate(v)) for k, v in self._kwargs.items()])
        for transform in self._transforms:
            result = transform(result)
        return result

    def __add__(self, other):
        if not isinstance(other, (str, unicode)):
            return NotImplemented
        return concat((self, other))

    def __radd__(self, other):
        if not isinstance(other, (str, unicode)):
            return NotImplemented
        return concat((other, self))
    

class Concatenation(unicode):
    """A concatenation of translatable and untranslatable text elements.

    Represents a block of text, where ordinary python strings, unicode strings
    and TranslatableText instances are concatenated to make the final text.

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
            'TranslatableText' instance, a 'Concatenation' instance, tuple or
            list.  
 
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
                assert isinstance(item, (str, unicode, TranslatableText)), item
                if not isinstance(item, TranslatableText) and array \
                       and not isinstance(array[-1], TranslatableText):
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

    def __add__(self, other):
        if not isinstance(other, (str, unicode)):
            return NotImplemented
        return concat(self, other)
        
    def __radd__(self, other):
        if not isinstance(other, (str, unicode)):
            return NotImplemented
        return concat(other, self)
        
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
        strings or 'TranslatableText' instances.
        
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
        assert isinstance(translator, Translator)
        translated = [translator.translate(item) for item in self._items]
        return ''.join(translated)


class Translator(object):
    """A generic translator of translatable objects.

    A translator should be able to translate different translatable objects,
    such as 'TranslatableText' and 'Concatenation' instances.  'Concatenation'
    instances may actually contain 'TranslatableText' instances coming from
    different domains and a translator should be able to deal with them.  This
    is, however only a generic base class.  See 'GettextTranslator' or
    'NullTranslator' for concrete implementations.

    """

    def gettext(self, text, domain=None):
        """Return the translation of the string 'text' from given domain.

        Arguments:

          text -- the text to translate as a string or unicode instance.

          domain -- the name of the domain, form which this text origins.

        Returns a unicode string.
        
        """
        pass

    def translate(self, text):
        """Return the translation of given translatable.

        The argument may be a 'Concatenation', 'TranslatableText' or a plain
        string or unicode instance.

        Returns a string or unicode depending if there was a unicode type
        within the input (as well as 'Concatenation.translate()'.
        
        """
        if isinstance(text, (Concatenation, TranslatableText)):
            return text.translate(self)
        else:
            return text


class NullTranslator(Translator):
    """A translator which just returns identical strings as translations."""
    
    def gettext(self, text, domain=None):
        return text


class GettextTranslator(Translator):
    """Translator based on the GNU gettext interface."""
    
    def __init__(self, lang, path=None, default_domain='lcg', fallback=False):
        """Initialize the instance.

        Arguments:

          lang -- target language code as a string.

          default_domain -- the name of the default domain, used when the
            translatable has no explicit domain defined.

          path -- a dictionary, which may assign an arbitrary directory to each
            domain.  This directory should contain the locale subdirectories as
            usual with GNU getext (eg. 'de/LC_MESSAGES/domain.mo').  If there
            is no item for a domain, the directory defaults to
            'config.translation_dir'.

          fallback -- if true, the translator will silently use a null
            translation in case the desired translation files is not found.
        
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

    def _gettext_instance(self, domain):
        import gettext, config
        path = self._path.get(domain, config.translation_dir)
        try:
            return gettext.translation(domain, path, (self._lang,))
        except IOError, e:
            msg = str(e)+", path: '%s', lang: '%s'" % (path, self._lang)
            if self._fallback or self._lang == 'en':
                # The original strings are in English, so it's ok if we
                # don't find a MO file for them.
                if self._lang != 'en':
                    log(msg)
                return gettext.NullTranslations()
            else:
                raise IOError(msg)
        
    def gettext(self, text, domain=None):
        domain = domain or self._default_domain
        try:
            t = self._cache[domain]
        except KeyError:
            t = self._cache[domain] = self._gettext_instance(domain)
        return t.ugettext(text)
        
    
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
        for filename in files:
            name = os.path.splitext(os.path.basename(filename))[0]
            path = os.path.dirname(filename)
            import imp
            file, pathname, descr = imp.find_module(name, [path])
            module = imp.load_module(name, file, pathname, descr)
            if module.__dict__.has_key('_'):
                x = module.__dict__['_']
                if x.domain() == domain:
                    result.append(filename)
        return result

if __name__ == '__main__':
    print " ".join(source_files_by_domain(*sys.argv[1:]))
