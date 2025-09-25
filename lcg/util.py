# -*- coding: utf-8 -*-

# Copyright (C) 2004-2015 OUI Technology Ltd.
# Copyright (C) 2019-2021 Tomáš Cerha <t.cerha@gmail.com>
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

from __future__ import unicode_literals

from contextlib import contextmanager
import re
import sys
import unicodedata

from lcg import TranslatableTextFactory
_ = TranslatableTextFactory('lcg')

unistr = type(u'')  # Python 2/3 transition hack.

def is_sequence_of(seq, cls):
    """Return true if 'seq' is a sequence of instances of 'cls'."""
    if not isinstance(seq, (tuple, list)):
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


def text_to_id(string, separator='-'):
    """Convert any text to an identifier.

    The returned identifier consists only of safe characters, such as lower
    case letters of English alphabet, numbers and separators, but it attempts
    to keep as much of the input text as possible.  Upper case characters are
    converted to lower case, accents are removed from accented characters,
    spaces are replaced by the 'separator' (dash by default) and other
    characters are removed.

    """
    # Handle certain special cases.
    string = string.replace(u'´', '').replace('_', ' ')
    # Remove accents
    string = unicodedata.normalize('NFKD', string).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^a-z0-9 ]', '', string.lower()).replace(' ', separator)


def unindent_docstring(docstring):
    """Trim indentation and blank lines from docstring text and return it."""
    if not docstring:
        return docstring
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
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
        result += 1 << 32
        if result < 0:
            # Undo that, and try 64 bits.
            result -= 1 << 32
            result += 1 << 64
            assert result >= 0  # else addresses are fatter than 64 bits
    return result


def log(message, *args):
    """Log processing information.

    Arguments:

      message -- The text of a message.  Any object will be converted to a
        string.

      *args -- message arguments.  When formatting the message with these
        arguments doesn't succeed, the arguemnts are simply appended to the end
        of the message.

    The logging is currently only written to STDERR.

    """
    if not isinstance(message, unistr):
        message = unistr(message)
    try:
        message %= args
    except TypeError:
        if not message.endswith(":"):
            message += ":"
        if not message.endswith(" "):
            message += " "
        message += ', '.join([unistr(a) for a in args])
    if not message.endswith("\n"):
        message += "\n"
    sys.stderr.write("  " + message)
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
    # Translators: The following 139 strings represent names of languages.
    # Feel free to consider which language names are worth a translation and
    # which are fine to be left untranslated.  Many of these languages are so
    # exotic, that a proper translation may even not exist in your language.
    # Please, copy the untranslated string into the translation field in such
    # cases to distinguish the "not yet" and "not to be" translated entries.
    'aa': _(u"Afar"),
    'ab': _(u"Abkhazian"),
    'af': _(u"Afrikaans"),
    'am': _(u"Amharic"),
    'ar': _(u"Arabic"),
    'as': _(u"Assamese"),
    'ay': _(u"Aymara"),
    'az': _(u"Azerbaijani"),
    'ba': _(u"Bashkir"),
    'be': _(u"Byelorussian"),
    'bg': _(u"Bulgarian"),
    'bh': _(u"Bihari"),
    'bi': _(u"Bislama"),
    'bn': _(u"Bengali"),
    'bo': _(u"Tibetan"),
    'br': _(u"Breton"),
    'ca': _(u"Catalan"),
    'co': _(u"Corsican"),
    'cs': _(u"Czech"),
    'cy': _(u"Welsh"),
    'da': _(u"Danish"),
    'de': _(u"German"),
    'dz': _(u"Bhutani"),
    'el': _(u"Greek"),
    'en': _(u"English"),
    'eo': _(u"Esperanto"),
    'es': _(u"Spanish"),
    'et': _(u"Estonian"),
    'eu': _(u"Basque"),
    'fa': _(u"Persian"),
    'fi': _(u"Finnish"),
    'fj': _(u"Fiji"),
    'fo': _(u"Faroese"),
    'fr': _(u"French"),
    'fy': _(u"Frisian"),
    'ga': _(u"Irish"),
    'gd': _(u"Scots Gaelic"),
    'gl': _(u"Galician"),
    'gn': _(u"Guarani"),
    'gu': _(u"Gujarati"),
    'ha': _(u"Hausa"),
    'he': _(u"Hebrew"),
    'hi': _(u"Hindi"),
    'hr': _(u"Croatian"),
    'hu': _(u"Hungarian"),
    'hy': _(u"Armenian"),
    'ia': _(u"Interlingua"),
    'id': _(u"Indonesian"),
    'ie': _(u"Interlingue"),
    'ik': _(u"Inupiak"),
    'is': _(u"Icelandic"),
    'it': _(u"Italian"),
    'iu': _(u"Inuktitut"),
    'ja': _(u"Japanese"),
    'jw': _(u"Javanese"),
    'ka': _(u"Georgian"),
    'kk': _(u"Kazakh"),
    'kl': _(u"Greenlandic"),
    'km': _(u"Cambodian"),
    'kn': _(u"Kannada"),
    'ko': _(u"Korean"),
    'ks': _(u"Kashmiri"),
    'ku': _(u"Kurdish"),
    'ky': _(u"Kirghiz"),
    'la': _(u"Latin"),
    'ln': _(u"Lingala"),
    'lo': _(u"Laothian"),
    'lt': _(u"Lithuanian"),
    'lv': _(u"Latvian, Lettish"),
    'mg': _(u"Malagasy"),
    'mi': _(u"Maori"),
    'mk': _(u"Macedonian"),
    'ml': _(u"Malayalam"),
    'mn': _(u"Mongolian"),
    'mo': _(u"Moldavian"),
    'mr': _(u"Marathi"),
    'ms': _(u"Malay"),
    'mt': _(u"Maltese"),
    'my': _(u"Burmese"),
    'na': _(u"Nauru"),
    'ne': _(u"Nepali"),
    'nl': _(u"Dutch"),
    'no': _(u"Norwegian"),
    'oc': _(u"Occitan"),
    'om': _(u"(Afan) Oromo"),
    'or': _(u"Oriya"),
    'pa': _(u"Punjabi"),
    'pl': _(u"Polish"),
    'ps': _(u"Pashto, Pushto"),
    'pt': _(u"Portuguese"),
    'qu': _(u"Quechua"),
    'rm': _(u"Rhaeto-Romance"),
    'rn': _(u"Kirundi"),
    'ro': _(u"Romanian"),
    'ru': _(u"Russian"),
    'rw': _(u"Kinyarwanda"),
    'sa': _(u"Sanskrit"),
    'sd': _(u"Sindhi"),
    'sg': _(u"Sangho"),
    'sh': _(u"Serbo-Croatian"),
    'si': _(u"Sinhalese"),
    'sk': _(u"Slovak"),
    'sl': _(u"Slovenian"),
    'sm': _(u"Samoan"),
    'sn': _(u"Shona"),
    'so': _(u"Somali"),
    'sq': _(u"Albanian"),
    'sr': _(u"Serbian"),
    'ss': _(u"Siswati"),
    'st': _(u"Sesotho"),
    'su': _(u"Sundanese"),
    'sv': _(u"Swedish"),
    'sw': _(u"Swahili"),
    'ta': _(u"Tamil"),
    'te': _(u"Telugu"),
    'tg': _(u"Tajik"),
    'th': _(u"Thai"),
    'ti': _(u"Tigrinya"),
    'tk': _(u"Turkmen"),
    'tl': _(u"Tagalog"),
    'tn': _(u"Setswana"),
    'to': _(u"Tonga"),
    'tr': _(u"Turkish"),
    'ts': _(u"Tsonga"),
    'tt': _(u"Tatar"),
    'tw': _(u"Twi"),
    'ug': _(u"Uighur"),
    'uk': _(u"Ukrainian"),
    'ur': _(u"Urdu"),
    'uz': _(u"Uzbek"),
    'vi': _(u"Vietnamese"),
    'vo': _(u"Volapuk"),
    'wo': _(u"Wolof"),
    'xh': _(u"Xhosa"),
    'yi': _(u"Yiddish"),
    'yo': _(u"Yoruba"),
    'za': _(u"Zhuang"),
    'zh': _(u"Chinese"),
    'zu': _(u"Zulu"),
}


def language_name(code):
    """Return the language name corresponding to given ISO 639-1 code.

    The returned string is 'lcg.TranslatableText' instance or None if given
    code is not known.

    """
    return _LANGUAGE_NAMES.get(code)


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


@contextmanager
def attribute_value(obj, name, value):
    """Set 'obj' attribute 'name' to 'value' and run the code.

    Restore the original attribute value after the code is exited in any way.

    Arguments:

      obj -- any object
      name -- attribute name; string
      value -- value of the attribute; arbitrary object

    """
    orig_value = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, orig_value)


class ParseError(Exception):
    "Exception raised on various parsing errors."
    pass
