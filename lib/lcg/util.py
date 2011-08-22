# -*- coding: utf-8 -*-
# Author: Tomas Cerha <cerha@brailcom.org>
# Copyright (C) 2004, 2005, 2006, 2007, 2008, 2009, 2011 Brailcom, o.p.s.
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

"""Various utilities"""

import glob
import os
import string
import operator
import re
import sys

from lcg import *
_ = TranslatableTextFactory('lcg')

def is_sequence_of(seq, cls):
    """Return true if 'seq' is a sequence of instances of 'cls'."""
    if not operator.isSequenceType(seq):
        return False
    for item in seq:
        if not isinstance(item, cls):
            return False
    return True


_CAMEL_CASE_WORD = re.compile(r'[A-Z][a-z\d]+')
        
def camel_case_to_lower(string, separator='-'):
    """Return a lowercase string using 'separator' to concatenate words."""
    words = _CAMEL_CASE_WORD.findall(string)
    return separator.join([w.lower() for w in words])


def unindent_docstring(docstring):
    """Trim indentation and blank lines from docstring text and return it."""
    if not docstring:
        return docstring
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


def positive_id(obj):
    """Return id(obj) as a non-negative integer."""
    result = id(obj)
    if result < 0:
        # This is a puzzle:  there's no way to know the natural width of
        # addresses on this box (in particular, there's no necessary
        # relation to sys.maxint).  Try 32 bits first (and on a 32-bit
        # box, adding 2**32 gives a positive number with the same hex
        # representation as the original result).
        result += 1L << 32
        if result < 0:
            # Undo that, and try 64 bits.
            result -= 1L << 32
            result += 1L << 64
            assert result >= 0 # else addresses are fatter than 64 bits
    return result


def log(message, *args):
    """Log a processing information.

    Arguments:

      message -- The text of a message.  Any object will be converted to a
        unicode string.
        
      *args -- message arguments.  When formatting the message with these
        arguments doesn't succeed, the arguemnts are simply appended to the end
        of the message.

    The logging is currently only written to STDERR.

    """
    if not isinstance(message, (str, unicode)):
        message = unicode(message)
    try:
        message %= args
    except TypeError:
        if not message.endswith(":"):
            message += ":"
        if not message.endswith(" "):
            message += " "
        message += ', '.join([unicode(a) for a in args])
    if not message.endswith("\n"):
        message += "\n"
    sys.stderr.write("  "+message.encode('iso-8859-2', 'replace'))
    sys.stderr.flush()

def caller():
    """Return the frame stack caller information formatted as a string.

    Allows logging the frame stack information with simillar formatting as the
    Python traceback.

    For debugging purposes only. 

    """
    import inspect
    frame = inspect.stack()[2]
    code = frame[5] and ':\n    %s' % frame[5] or ''
    return 'File "%s", line %d, in %s' % frame[1:4] + code

    
_LANGUAGE_NAMES = {
    'aa':'Afar', 'ab':'Abkhazian', 'af':_('Afrikaans'),
    'am':'Amharic', 'ar':_('Arabic'), 'as':'Assamese', 'ay':'Aymara',
    'az':'Azerbaijani',
    'ba':'Bashkir', 'be':'Byelorussian', 'bg':_('Bulgarian'), 'bh':'Bihari',
    'bi':'Bislama', 'bn':'Bengali', 'bo':'Tibetan', 'br':'Breton',
    'ca':_('Catalan'), 'co':_('Corsican'), 'cs':_('Czech'), 'cy':'Welsh',
    'da':_('Danish'), 'de':_('German'), 'dz':'Bhutani',
    'el':_('Greek'), 'en':_('English'), 'eo':'Esperanto', 'es':_('Spanish'),
    'et':_('Estonian'), 'eu':_('Basque'),
    'fa':'Persian', 'fi':_('Finnish'), 'fj':'Fiji', 'fo':'Faroese',
    'fr':_('French'),
    'fy':'Frisian',
    'ga':_('Irish'), 'gd':'Scots Gaelic', 'gl':_('Galician'), 'gn':'Guarani',
    'gu':'Gujarati',
    'ha':'Hausa', 'he':'Hebrew', 'hi':_('Hindi'), 'hr':_('Croatian'),
    'hu':_('Hungarian'), 'hy':'Armenian',
    'ia':'Interlingua', 'id':'Indonesian', 'ie':'Interlingue', 'ik':'Inupiak',
    'is':_('Icelandic'), 'it':_('Italian'), 'iu':'Inuktitut',
    'ja':_('Japanese'), 'jw':'Javanese',
    'ka':_('Georgian'), 'kk':'Kazakh', 'kl':'Greenlandic', 'km':'Cambodian',
    'kn':'Kannada', 'ko':_('Korean'), 'ks':'Kashmiri', 'ku':_('Kurdish'),
    'ky':'Kirghiz',
    'la':'Latin', 'ln':'Lingala', 'lo':'Laothian', 'lt':'Lithuanian',
    'lv':'Latvian, Lettish',
    'mg':'Malagasy', 'mi':'Maori', 'mk':_('Macedonian'), 'ml':'Malayalam',
    'mn':'Mongolian', 'mo':_('Moldavian'), 'mr':'Marathi', 'ms':'Malay',
    'mt':'Maltese', 'my':'Burmese',
    'na':'Nauru', 'ne':'Nepali', 'nl':_('Dutch'), 'no':_('Norwegian'),
    'oc':'Occitan', 'om':'(Afan) Oromo', 'or':'Oriya',
    'pa':'Punjabi', 'pl':_('Polish'), 'ps':'Pashto, Pushto',
    'pt':_('Portuguese'),
    'qu':'Quechua',
    'rm':'Rhaeto-Romance', 'rn':'Kirundi', 'ro':_('Romanian'), 'ru':('Russian'),
    'rw':'Kinyarwanda',
    'sa':'Sanskrit', 'sd':'Sindhi', 'sg':'Sangho', 'sh':'Serbo-Croatian',
    'si':'Sinhalese', 'sk':_('Slovak'), 'sl':_('Slovenian'), 'sm':'Samoan',
    'sn':'Shona', 'so':'Somali', 'sq':_('Albanian'), 'sr':_('Serbian'),
    'ss':'Siswati', 'st':'Sesotho', 'su':'Sundanese', 'sv':_('Swedish'),
    'sw':'Swahili',
    'ta':'Tamil', 'te':'Telugu', 'tg':'Tajik', 'th':_('Thai'), 'ti':'Tigrinya',
    'tk':'Turkmen', 'tl':'Tagalog', 'tn':'Setswana', 'to':'Tonga',
    'tr':_('Turkish'), 'ts':'Tsonga', 'tt':'Tatar', 'tw':'Twi',
    'ug':'Uighur', 'uk':_('Ukrainian'), 'ur':'Urdu', 'uz':'Uzbek',
    'vi':'Vietnamese', 'vo':'Volapuk', 'wo':'Wolof', 'xh':'Xhosa',
    'yi':_('Yiddish'), 'yo':'Yoruba', 'za':'Zhuang', 'zh':_('Chinese'), 'zu':'Zulu'
}

def language_name(code):
    """Return the language name corresponding to given ISO 639-1 code.

    The returned string is 'lcg.TranslatableText' instance.
    
    """
    try:
        return _LANGUAGE_NAMES[code]
    except KeyError:
        return code

_COUNTRY_NAMES = {
    # Translators: The following 249 strings represent names of countries.
    # Feel free to consider which country names are worth a translation and
    # which are fine to be left untranslated.  Many of these countries are so
    # exotic, that a proper translation may even not exist in your language.
    # Please, copy the untranslated string into the translation field in such
    # cases to distinguish the "not yet" and "not to be" translated entries.
    'AD': _(u"Andorra"),
    'AE': _(u"United Arab Emirates"),
    'AF': _(u"Afghanistan"),
    'AG': _(u"Antigua and Barbuda"),
    'AI': _(u"Anguilla"),
    'AL': _(u"Albania"),
    'AM': _(u"Armenia"),
    'AO': _(u"Angola"),
    'AQ': _(u"Antarctica"),
    'AR': _(u"Argentina"),
    'AS': _(u"American Samoa"),
    'AT': _(u"Austria"),
    'AU': _(u"Australia"),
    'AW': _(u"Aruba"),
    'AX': _(u"Åland Islands"),
    'AZ': _(u"Azerbaijan"),
    'BA': _(u"Bosnia and Herzegovina"),
    'BB': _(u"Barbados"),
    'BD': _(u"Bangladesh"),
    'BE': _(u"Belgium"),
    'BF': _(u"Burkina Faso"),
    'BG': _(u"Bulgaria"),
    'BH': _(u"Bahrain"),
    'BI': _(u"Burundi"),
    'BJ': _(u"Benin"),
    'BL': _(u"Saint Barthélemy"),
    'BM': _(u"Bermuda"),
    'BN': _(u"Brunei Darussalam"),
    'BO': _(u"Bolivia"),
    'BQ': _(u"Bonaire"),
    'BR': _(u"Brazil"),
    'BS': _(u"Bahamas"),
    'BT': _(u"Bhutan"),
    'BV': _(u"Bouvet Island"),
    'BW': _(u"Botswana"),
    'BY': _(u"Belarus"),
    'BZ': _(u"Belize"),
    'CA': _(u"Canada"),
    'CC': _(u"Cocos"),
    'CD': _(u"Congo"),
    'CF': _(u"Central African Republic"),
    'CG': _(u"Congo"),
    'CH': _(u"Switzerland"),
    'CI': _(u"Côte d'Ivoire"),
    'CK': _(u"Cook Islands"),
    'CL': _(u"Chile"),
    'CM': _(u"Cameroon"),
    'CN': _(u"China"),
    'CO': _(u"Colombia"),
    'CR': _(u"Costa Rica"),
    'CU': _(u"Cuba"),
    'CV': _(u"Cape Verde"),
    'CW': _(u"Curaçao"),
    'CX': _(u"Christmas Island"),
    'CY': _(u"Cyprus"),
    'CZ': _(u"Czech Republic"),
    'DE': _(u"Germany"),
    'DJ': _(u"Djibouti"),
    'DK': _(u"Denmark"),
    'DM': _(u"Dominica"),
    'DO': _(u"Dominican Republic"),
    'DZ': _(u"Algeria"),
    'EC': _(u"Ecuador"),
    'EE': _(u"Estonia"),
    'EG': _(u"Egypt"),
    'EH': _(u"Western Sahara"),
    'ER': _(u"Eritrea"),
    'ES': _(u"Spain"),
    'ET': _(u"Ethiopia"),
    'FI': _(u"Finland"),
    'FJ': _(u"Fiji"),
    'FK': _(u"Falkland Islands"),
    'FM': _(u"Micronesia"),
    'FO': _(u"Faroe Islands"),
    'FR': _(u"France"),
    'GA': _(u"Gabon"),
    'GB': _(u"United Kingdom"),
    'GD': _(u"Grenada"),
    'GE': _(u"Georgia"),
    'GF': _(u"French Guiana"),
    'GG': _(u"Guernsey"),
    'GH': _(u"Ghana"),
    'GI': _(u"Gibraltar"),
    'GL': _(u"Greenland"),
    'GM': _(u"Gambia"),
    'GN': _(u"Guinea"),
    'GP': _(u"Guadeloupe"),
    'GQ': _(u"Equatorial Guinea"),
    'GR': _(u"Greece"),
    'GS': _(u"South Georgia and the South Sandwich Islands"),
    'GT': _(u"Guatemala"),
    'GU': _(u"Guam"),
    'GW': _(u"Guinea-Bissau"),
    'GY': _(u"Guyana"),
    'HK': _(u"Hong Kong"),
    'HM': _(u"Heard Island and McDonald Islands"),
    'HN': _(u"Honduras"),
    'HR': _(u"Croatia"),
    'HT': _(u"Haiti"),
    'HU': _(u"Hungary"),
    'ID': _(u"Indonesia"),
    'IE': _(u"Ireland"),
    'IL': _(u"Israel"),
    'IM': _(u"Isle of Man"),
    'IN': _(u"India"),
    'IO': _(u"British Indian Ocean Territory"),
    'IQ': _(u"Iraq"),
    'IR': _(u"Iran"),
    'IS': _(u"Iceland"),
    'IT': _(u"Italy"),
    'JE': _(u"Jersey"),
    'JM': _(u"Jamaica"),
    'JO': _(u"Jordan"),
    'JP': _(u"Japan"),
    'KE': _(u"Kenya"),
    'KG': _(u"Kyrgyzstan"),
    'KH': _(u"Cambodia"),
    'KI': _(u"Kiribati"),
    'KM': _(u"Comoros"),
    'KN': _(u"Saint Kitts and Nevis"),
    'KP': _(u"Korea"),
    'KR': _(u"Korea"),
    'KW': _(u"Kuwait"),
    'KY': _(u"Cayman Islands"),
    'KZ': _(u"Kazakhstan "),
    'LA': _(u"Lao People's Democratic Republic"),
    'LB': _(u"Lebanon"),
    'LC': _(u"Saint Lucia"),
    'LI': _(u"Liechtenstein"),
    'LK': _(u"Sri Lanka"),
    'LR': _(u"Liberia"),
    'LS': _(u"Lesotho"),
    'LT': _(u"Lithuania"),
    'LU': _(u"Luxembourg"),
    'LV': _(u"Latvia"),
    'LY': _(u"Libyan Arab Jamahiriya"),
    'MA': _(u"Morocco"),
    'MC': _(u"Monaco"),
    'MD': _(u"Moldova"),
    'ME': _(u"Montenegro"),
    'MF': _(u"Saint Martin (French part)"),
    'MG': _(u"Madagascar"),
    'MH': _(u"Marshall Islands"),
    'MK': _(u"Macedonia"),
    'ML': _(u"Mali"),
    'MM': _(u"Myanmar"),
    'MN': _(u"Mongolia"),
    'MO': _(u"Macao"),
    'MP': _(u"Northern Mariana Islands"),
    'MQ': _(u"Martinique"),
    'MR': _(u"Mauritania"),
    'MS': _(u"Montserrat"),
    'MT': _(u"Malta"),
    'MU': _(u"Mauritius"),
    'MV': _(u"Maldives"),
    'MW': _(u"Malawi"),
    'MX': _(u"Mexico"),
    'MY': _(u"Malaysia"),
    'MZ': _(u"Mozambique"),
    'NA': _(u"Namibia"),
    'NC': _(u"New Caledonia"),
    'NE': _(u"Niger"),
    'NF': _(u"Norfolk Island"),
    'NG': _(u"Nigeria"),
    'NI': _(u"Nicaragua"),
    'NL': _(u"Netherlands"),
    'NO': _(u"Norway"),
    'NP': _(u"Nepal"),
    'NR': _(u"Nauru"),
    'NU': _(u"Niue"),
    'NZ': _(u"New Zealand"),
    'OM': _(u"Oman"),
    'PA': _(u"Panama"),
    'PE': _(u"Peru"),
    'PF': _(u"French Polynesia"),
    'PG': _(u"Papua New Guinea"),
    'PH': _(u"Philippines"),
    'PK': _(u"Pakistan"),
    'PL': _(u"Poland"),
    'PM': _(u"Saint Pierre and Miquelon"),
    'PN': _(u"Pitcairn"),
    'PR': _(u"Puerto Rico"),
    'PS': _(u"Palestinian Territory"),
    'PT': _(u"Portugal"),
    'PW': _(u"Palau"),
    'PY': _(u"Paraguay"),
    'QA': _(u"Qatar"),
    'RE': _(u"Réunion"),
    'RO': _(u"Romania"),
    'RS': _(u"Serbia"),
    'RU': _(u"Russian Federation"),
    'RW': _(u"Rwanda"),
    'SA': _(u"Saudi Arabia"),
    'SB': _(u"Solomon Islands"),
    'SC': _(u"Seychelles"),
    'SD': _(u"Sudan"),
    'SE': _(u"Sweden"),
    'SG': _(u"Singapore"),
    'SH': _(u"Saint Helena"),
    'SI': _(u"Slovenia"),
    'SJ': _(u"Svalbard and Jan Mayen"),
    'SK': _(u"Slovakia"),
    'SL': _(u"Sierra Leone"),
    'SM': _(u"San Marino"),
    'SN': _(u"Senegal"),
    'SO': _(u"Somalia"),
    'SR': _(u"Suriname"),
    'SS': _(u"South Sudan"),
    'ST': _(u"Sao Tome and Principe"),
    'SV': _(u"El Salvador"),
    'SX': _(u"Sint Maarten (Dutch part)"),
    'SY': _(u"Syrian Arab Republic"),
    'SZ': _(u"Swaziland"),
    'TC': _(u"Turks and Caicos Islands"),
    'TD': _(u"Chad"),
    'TF': _(u"French Southern Territories"),
    'TG': _(u"Togo"),
    'TH': _(u"Thailand"),
    'TJ': _(u"Tajikistan"),
    'TK': _(u"Tokelau"),
    'TL': _(u"Timor-Leste"),
    'TM': _(u"Turkmenistan"),
    'TN': _(u"Tunisia"),
    'TO': _(u"Tonga"),
    'TR': _(u"Turkey"),
    'TT': _(u"Trinidad and Tobago"),
    'TV': _(u"Tuvalu"),
    'TW': _(u"Taiwan"),
    'TZ': _(u"Tanzania"),
    'UA': _(u"Ukraine"),
    'UG': _(u"Uganda"),
    'UM': _(u"United States Minor Outlying Islands"),
    'US': _(u"United States"),
    'UY': _(u"Uruguay"),
    'UZ': _(u"Uzbekistan"),
    'VA': _(u"Holy See (Vatican City State)"),
    'VC': _(u"Saint Vincent and the Grenadines"),
    'VE': _(u"Venezuela"),
    'VG': _(u"Virgin Islands, British"),
    'VI': _(u"Virgin Islands, U.S."),
    'VN': _(u"Viet Nam"),
    'VU': _(u"Vanuatu"),
    'WF': _(u"Wallis and Futuna"),
    'WS': _(u"Samoa"),
    'YE': _(u"Yemen"),
    'YT': _(u"Mayotte"),
    'ZA': _(u"South Africa"),
    'ZM': _(u"Zambia"),
    'ZW': _(u"Zimbabwe"),
}

def country_name(code):
    """Return the country name corresponding to given ISO 3166-1 code.

    The returned string is 'lcg.TranslatableText' instance or None if given
    code is not known.
    
    """
    return _COUNTRY_NAMES.get(code)

# Translators: The following 7 strings represent full week day names.  Please, take care to use
# upper/lower case letters according to the rules of the target language.
_FULL_DAY_NAMES = (_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"),
                   _("Saturday"), _("Sunday"))

# Translators: The following 7 strings represent the abbreviated week day names.  The
# abbreviations should normally take up to three characters.  Feel free to use whatever form
# usual in the target language.
_SHORT_DAY_NAMES = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))

def week_day_name(number, abbrev=False):
    """Return the week day name corresponding to given numeric index.

    Arguments:
      number -- numeric index from 0 to 6, where 0 corresponds to Monday and 6 to Sunday (according
        to ISO-8601).
      abbrev -- iff true, the abbreviated variant is returned (up to 3 characters in most
        languages).  Full name is returned otherwise (by default).
      
    The returned string is 'lcg.TranslatableText' instance.
    
    """
    if abbrev:
        names = _SHORT_DAY_NAMES
    else:
        names = _FULL_DAY_NAMES
    return names[number]

# Translators: The following 12 strings represent full month names.  Please, take care to use
# upper/lower case letters according to the rules of the target language.
_FULL_MONTH_NAMES = (_("January"), _("February"), _("March"), _("April"), _("May"), _("June"),
                     _("July"), _("August"), _("September"), _("October"), _("November"),
                     _("December"))

# Translators: The following 12 strings represent the abbreviated month names.  The
# abbreviations should normally take up to three characters.  Feel free to use whatever form
# usual in the target language.
_SHORT_MONTH_NAMES = (_("Jan"), _("Feb"), _("Mar"), _("Apr"), _("May"), _("Jun"), _("Jul"),
                      _("Aug"), _("Sep"), _("Oct"), _("Nov"), _("Dec"))

def month_name(number, abbrev=False):
    """Return the calendar month name corresponding to given numeric index.

    Arguments:
      number -- numeric index from 0 to 11, where 0 corresponds to June and 11 to December.
      abbrev -- iff true, the abbreviated variant is returned (up to 3 characters in most
        languages).  Full name is returned otherwise (by default).
      
    The returned string is 'lcg.TranslatableText' instance.
    
    """
    if abbrev:
        names = _SHORT_MONTH_NAMES
    else:
        names = _FULL_MONTH_NAMES
    return names[number]
