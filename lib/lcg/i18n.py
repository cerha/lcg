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
    """A helper for defining the `_' identifier bound to a certain domain.

    You may define the `_' function as follows:

      _ = TranslatableTextFactory('domain-name')

    """
    def __init__(self, domain='lcg'):
        assert isinstance(domain, str), domain
        self._domain = domain
        
    def __call__(self, *args, **kwargs):
        kwargs['domain'] = self._domain
        return TranslatableText(*args, **kwargs)
    

class TranslatableText(object):
    """Translatable string with a delayed translation.

    This class is intended to become the '_' identifier.  Thus all strings
    within the LCG code marked by the '_()' construct become 'TranslatableText'
    instances.  They can be mixed with ordinary Python string or unicode
    strings using the 'Concatenation' class defined below.  Then the exporter
    is capable to translate all translatable strings within the content at one
    place to any target language.

    """
    def __init__(self, text, *args, **kwargs):
        """Initialize the instance.

        Arguments:

          text -- the actual text to translate as a string or unicode instance.

          args -- positional substitution values (see below).
          
          kwargs -- named substitution arguments (see below).

        If 'args' or 'kwargs' are passed, the 'text' is considered a formatting
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
        format string or just positional substitution.
        
        """
        assert isinstance(text, (str, unicode)), (text, type(text))
        self._text = text
        kwargs = self._init_kwargs(**kwargs)
        assert not args or not kwargs, (text, args, kwargs)
        self._args = args
        self._kwargs = kwargs

    def _init_kwargs(self, _transforms=(), domain='lcg', **kwargs):
        assert isinstance(_transforms, tuple), _transforms
        assert isinstance(domain, str), domain
        self._transforms = _transforms
        self._domain = domain
        return kwargs

    def __str__(self):
        log("TranslatableText used in string context:", caller())
        return '[TranslatableText "%s"]' % self._text

    def replace(self, old, new):
        """Return a TranslatableText instance which replaces old by new.

        This is the analogy of the string method of the same name and
        arguments.  Here the replacement is left after the translation and
        variable interpolation.  Thus the actual replace is automatically

        """
        transforms = self._transforms + (lambda x: x.replace(old, new),)
        kwargs = dict(self._kwargs, _transforms=transforms, domain=self._domain)
        return TranslatableText(self._text, *self._args, **kwargs)
    
    def translate(self, gettext):
        """Return the translated and interpolated string.
        
        Arguments:

          gettext -- a function of one argument (a string) returning the
            translation of this string as a (unicode) string.  This is
            typically the gettext/ugettext function of the Python gettext
            module.

        The returned string has all the format variables interpolated.  Also
        all values of the format variables are translated (using the same
        function) before interpolation, if they are TranslatableText or
        Concatenation instances.

        Note, that a TypeError may be raised, when the constructor arguments
        didn't correspond to the format string.

        """
        def translate(x):
            if isinstance(x, (Concatenation, TranslatableText)):
                return x.translate(gettext)
            else:
                return x
        result = gettext(self._text)
        if self._args:
            result %= tuple([translate(arg) for arg in self._args])
        elif self._kwargs:
            result %= dict([(k, translate(v)) for k, v in self._kwargs.items()])
        for transform in self._transforms:
            result = transform(result)
        return result

    def __add__(self, other):
        if not isinstance(other, STRINGTYPES):
            raise TypeError("unsupported operand type(s) for +: '%s' and '%s'"
                            % (self.__class__.__name__,
                               other.__class__.__name__))
        return concat((self, other))


class Concatenation(object):
    """A concatenation of translatable and untranslatable text elements.

    Represents a block of text, where ordinary python strings, unicode strings
    and TranslatableText instances are concatenated to make the final text.

    """
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
                if isinstance(item, (str, unicode)) and array \
                       and isinstance(array[-1], (str, unicode)):
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

    def __str__(self):
        log("Concatenation used in string context:", caller())
        return "[Concatenation %s]" % [unicode(item) for item in self._items]
    
    def __add__(self, other):
        if not isinstance(other, STRINGTYPES):
            raise TypeError("unsupported operand type(s) for +: "
                            "'Concatenation' and '%s'" % type(other))
        return Concatenation((self, other))
        
    def _translate(self, item, gettext):
        if isinstance(item, TranslatableText):
            return item.translate(gettext)
        else:
            return item

    def replace(self, old, new):
        """Apply the method to all items and return a new Concatenation.

        The 'replace()' method with given arguments will be applied to all
        arguments and a new Concatenation instance will be returned with the
        modified arguments.  See 'string.replace()' and
        'TranslatableText.replace()' for more information.

        """
        return Concatenation([item.replace(old, new) for item in self._items])

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
        
    def translate(self, gettext):
        """Return the translated text as a string ot a unicode string.

        Arguments:

          gettext -- the same as for 'TranslatableText.translate()'.

        If there was at least one unicode type argument, or if the 'gettext'
        function returnes unicode values, the result will be a unicode type.
        If all the input are plain strings, a plain string is returned.
        
        """
        translated = [self._translate(item, gettext) for item in self._items]
        return ''.join(translated)

    
STRINGTYPES = (str, unicode, TranslatableText, Concatenation)
"""This constant lists all types, which can represent text within LCG.

It is mostly intended to be used for assertions."""


concat = Concatenation
"""A shortcut for constructing 'Concatenation' instances.

See 'Concatenation' constructor for more information about the arguments."""

#def concat(*args, **kwargs):
#    result = Concatenation(*args, **kwargs)
#    items = result.items()
#    if len(items) == 1 and isinstance(items[0], (str, unicode)):
#        return items[0]
#    return result

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

    Of course, with plain strings this makes no sense, but when the
    arguments are translatable texts...

    """
    return concat(reduce(lambda a,b: a+b, zip(text.split('%s'), args+('',))))


#     def __new__(cls, text, *args, **kwargs):
#         self = unicode.__new__(cls, text)
#         assert not args or not kwargs, (text, args, kwargs)
#         self._args = kwargs or args
#         return self
