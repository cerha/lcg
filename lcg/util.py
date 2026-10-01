# Copyright (C) 2004-2015 OUI Technology Ltd.
# Copyright (C) 2019-2026 Tomáš Cerha <cerha@truecode.cz>
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


from contextlib import contextmanager
import re
import sys
import unicodedata

from lcg import TranslatableTextFactory
_ = TranslatableTextFactory('lcg')


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
    string = string.replace('´', '').replace('_', ' ')
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
    if not isinstance(message, str):
        message = str(message)
    try:
        message %= args
    except TypeError:
        if not message.endswith(":"):
            message += ":"
        if not message.endswith(" "):
            message += " "
        message += ', '.join([str(a) for a in args])
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
    'aa': _("Afar"),
    'ab': _("Abkhazian"),
    'af': _("Afrikaans"),
    'am': _("Amharic"),
    'ar': _("Arabic"),
    'as': _("Assamese"),
    'ay': _("Aymara"),
    'az': _("Azerbaijani"),
    'ba': _("Bashkir"),
    'be': _("Byelorussian"),
    'bg': _("Bulgarian"),
    'bh': _("Bihari"),
    'bi': _("Bislama"),
    'bn': _("Bengali"),
    'bo': _("Tibetan"),
    'br': _("Breton"),
    'ca': _("Catalan"),
    'co': _("Corsican"),
    'cs': _("Czech"),
    'cy': _("Welsh"),
    'da': _("Danish"),
    'de': _("German"),
    'dz': _("Bhutani"),
    'el': _("Greek"),
    'en': _("English"),
    'eo': _("Esperanto"),
    'es': _("Spanish"),
    'et': _("Estonian"),
    'eu': _("Basque"),
    'fa': _("Persian"),
    'fi': _("Finnish"),
    'fj': _("Fiji"),
    'fo': _("Faroese"),
    'fr': _("French"),
    'fy': _("Frisian"),
    'ga': _("Irish"),
    'gd': _("Scots Gaelic"),
    'gl': _("Galician"),
    'gn': _("Guarani"),
    'gu': _("Gujarati"),
    'ha': _("Hausa"),
    'he': _("Hebrew"),
    'hi': _("Hindi"),
    'hr': _("Croatian"),
    'hu': _("Hungarian"),
    'hy': _("Armenian"),
    'ia': _("Interlingua"),
    'id': _("Indonesian"),
    'ie': _("Interlingue"),
    'ik': _("Inupiak"),
    'is': _("Icelandic"),
    'it': _("Italian"),
    'iu': _("Inuktitut"),
    'ja': _("Japanese"),
    'jw': _("Javanese"),
    'ka': _("Georgian"),
    'kk': _("Kazakh"),
    'kl': _("Greenlandic"),
    'km': _("Cambodian"),
    'kn': _("Kannada"),
    'ko': _("Korean"),
    'ks': _("Kashmiri"),
    'ku': _("Kurdish"),
    'ky': _("Kirghiz"),
    'la': _("Latin"),
    'ln': _("Lingala"),
    'lo': _("Laothian"),
    'lt': _("Lithuanian"),
    'lv': _("Latvian, Lettish"),
    'mg': _("Malagasy"),
    'mi': _("Maori"),
    'mk': _("Macedonian"),
    'ml': _("Malayalam"),
    'mn': _("Mongolian"),
    'mo': _("Moldavian"),
    'mr': _("Marathi"),
    'ms': _("Malay"),
    'mt': _("Maltese"),
    'my': _("Burmese"),
    'na': _("Nauru"),
    'ne': _("Nepali"),
    'nl': _("Dutch"),
    'no': _("Norwegian"),
    'oc': _("Occitan"),
    'om': _("(Afan) Oromo"),
    'or': _("Oriya"),
    'pa': _("Punjabi"),
    'pl': _("Polish"),
    'ps': _("Pashto, Pushto"),
    'pt': _("Portuguese"),
    'qu': _("Quechua"),
    'rm': _("Rhaeto-Romance"),
    'rn': _("Kirundi"),
    'ro': _("Romanian"),
    'ru': _("Russian"),
    'rw': _("Kinyarwanda"),
    'sa': _("Sanskrit"),
    'sd': _("Sindhi"),
    'sg': _("Sangho"),
    'sh': _("Serbo-Croatian"),
    'si': _("Sinhalese"),
    'sk': _("Slovak"),
    'sl': _("Slovenian"),
    'sm': _("Samoan"),
    'sn': _("Shona"),
    'so': _("Somali"),
    'sq': _("Albanian"),
    'sr': _("Serbian"),
    'ss': _("Siswati"),
    'st': _("Sesotho"),
    'su': _("Sundanese"),
    'sv': _("Swedish"),
    'sw': _("Swahili"),
    'ta': _("Tamil"),
    'te': _("Telugu"),
    'tg': _("Tajik"),
    'th': _("Thai"),
    'ti': _("Tigrinya"),
    'tk': _("Turkmen"),
    'tl': _("Tagalog"),
    'tn': _("Setswana"),
    'to': _("Tonga"),
    'tr': _("Turkish"),
    'ts': _("Tsonga"),
    'tt': _("Tatar"),
    'tw': _("Twi"),
    'ug': _("Uighur"),
    'uk': _("Ukrainian"),
    'ur': _("Urdu"),
    'uz': _("Uzbek"),
    'vi': _("Vietnamese"),
    'vo': _("Volapuk"),
    'wo': _("Wolof"),
    'xh': _("Xhosa"),
    'yi': _("Yiddish"),
    'yo': _("Yoruba"),
    'za': _("Zhuang"),
    'zh': _("Chinese"),
    'zu': _("Zulu"),
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
    'AD': _("Andorra"),
    'AE': _("United Arab Emirates"),
    'AF': _("Afghanistan"),
    'AG': _("Antigua and Barbuda"),
    'AI': _("Anguilla"),
    'AL': _("Albania"),
    'AM': _("Armenia"),
    'AO': _("Angola"),
    'AQ': _("Antarctica"),
    'AR': _("Argentina"),
    'AS': _("American Samoa"),
    'AT': _("Austria"),
    'AU': _("Australia"),
    'AW': _("Aruba"),
    'AX': _("Åland Islands"),
    'AZ': _("Azerbaijan"),
    'BA': _("Bosnia and Herzegovina"),
    'BB': _("Barbados"),
    'BD': _("Bangladesh"),
    'BE': _("Belgium"),
    'BF': _("Burkina Faso"),
    'BG': _("Bulgaria"),
    'BH': _("Bahrain"),
    'BI': _("Burundi"),
    'BJ': _("Benin"),
    'BL': _("Saint Barthélemy"),
    'BM': _("Bermuda"),
    'BN': _("Brunei Darussalam"),
    'BO': _("Bolivia"),
    'BQ': _("Bonaire"),
    'BR': _("Brazil"),
    'BS': _("Bahamas"),
    'BT': _("Bhutan"),
    'BV': _("Bouvet Island"),
    'BW': _("Botswana"),
    'BY': _("Belarus"),
    'BZ': _("Belize"),
    'CA': _("Canada"),
    'CC': _("Cocos"),
    'CD': _("Congo"),
    'CF': _("Central African Republic"),
    'CG': _("Congo"),
    'CH': _("Switzerland"),
    'CI': _("Côte d'Ivoire"),
    'CK': _("Cook Islands"),
    'CL': _("Chile"),
    'CM': _("Cameroon"),
    'CN': _("China"),
    'CO': _("Colombia"),
    'CR': _("Costa Rica"),
    'CU': _("Cuba"),
    'CV': _("Cape Verde"),
    'CW': _("Curaçao"),
    'CX': _("Christmas Island"),
    'CY': _("Cyprus"),
    'CZ': _("Czech Republic"),
    'DE': _("Germany"),
    'DJ': _("Djibouti"),
    'DK': _("Denmark"),
    'DM': _("Dominica"),
    'DO': _("Dominican Republic"),
    'DZ': _("Algeria"),
    'EC': _("Ecuador"),
    'EE': _("Estonia"),
    'EG': _("Egypt"),
    'EH': _("Western Sahara"),
    'ER': _("Eritrea"),
    'ES': _("Spain"),
    'ET': _("Ethiopia"),
    'FI': _("Finland"),
    'FJ': _("Fiji"),
    'FK': _("Falkland Islands"),
    'FM': _("Micronesia"),
    'FO': _("Faroe Islands"),
    'FR': _("France"),
    'GA': _("Gabon"),
    'GB': _("United Kingdom"),
    'GD': _("Grenada"),
    'GE': _("Georgia"),
    'GF': _("French Guiana"),
    'GG': _("Guernsey"),
    'GH': _("Ghana"),
    'GI': _("Gibraltar"),
    'GL': _("Greenland"),
    'GM': _("Gambia"),
    'GN': _("Guinea"),
    'GP': _("Guadeloupe"),
    'GQ': _("Equatorial Guinea"),
    'GR': _("Greece"),
    'GS': _("South Georgia and the South Sandwich Islands"),
    'GT': _("Guatemala"),
    'GU': _("Guam"),
    'GW': _("Guinea-Bissau"),
    'GY': _("Guyana"),
    'HK': _("Hong Kong"),
    'HM': _("Heard Island and McDonald Islands"),
    'HN': _("Honduras"),
    'HR': _("Croatia"),
    'HT': _("Haiti"),
    'HU': _("Hungary"),
    'ID': _("Indonesia"),
    'IE': _("Ireland"),
    'IL': _("Israel"),
    'IM': _("Isle of Man"),
    'IN': _("India"),
    'IO': _("British Indian Ocean Territory"),
    'IQ': _("Iraq"),
    'IR': _("Iran"),
    'IS': _("Iceland"),
    'IT': _("Italy"),
    'JE': _("Jersey"),
    'JM': _("Jamaica"),
    'JO': _("Jordan"),
    'JP': _("Japan"),
    'KE': _("Kenya"),
    'KG': _("Kyrgyzstan"),
    'KH': _("Cambodia"),
    'KI': _("Kiribati"),
    'KM': _("Comoros"),
    'KN': _("Saint Kitts and Nevis"),
    'KP': _("Korea"),
    'KR': _("Korea"),
    'KW': _("Kuwait"),
    'KY': _("Cayman Islands"),
    'KZ': _("Kazakhstan "),
    'LA': _("Lao People's Democratic Republic"),
    'LB': _("Lebanon"),
    'LC': _("Saint Lucia"),
    'LI': _("Liechtenstein"),
    'LK': _("Sri Lanka"),
    'LR': _("Liberia"),
    'LS': _("Lesotho"),
    'LT': _("Lithuania"),
    'LU': _("Luxembourg"),
    'LV': _("Latvia"),
    'LY': _("Libyan Arab Jamahiriya"),
    'MA': _("Morocco"),
    'MC': _("Monaco"),
    'MD': _("Moldova"),
    'ME': _("Montenegro"),
    'MF': _("Saint Martin (French part)"),
    'MG': _("Madagascar"),
    'MH': _("Marshall Islands"),
    'MK': _("Macedonia"),
    'ML': _("Mali"),
    'MM': _("Myanmar"),
    'MN': _("Mongolia"),
    'MO': _("Macao"),
    'MP': _("Northern Mariana Islands"),
    'MQ': _("Martinique"),
    'MR': _("Mauritania"),
    'MS': _("Montserrat"),
    'MT': _("Malta"),
    'MU': _("Mauritius"),
    'MV': _("Maldives"),
    'MW': _("Malawi"),
    'MX': _("Mexico"),
    'MY': _("Malaysia"),
    'MZ': _("Mozambique"),
    'NA': _("Namibia"),
    'NC': _("New Caledonia"),
    'NE': _("Niger"),
    'NF': _("Norfolk Island"),
    'NG': _("Nigeria"),
    'NI': _("Nicaragua"),
    'NL': _("Netherlands"),
    'NO': _("Norway"),
    'NP': _("Nepal"),
    'NR': _("Nauru"),
    'NU': _("Niue"),
    'NZ': _("New Zealand"),
    'OM': _("Oman"),
    'PA': _("Panama"),
    'PE': _("Peru"),
    'PF': _("French Polynesia"),
    'PG': _("Papua New Guinea"),
    'PH': _("Philippines"),
    'PK': _("Pakistan"),
    'PL': _("Poland"),
    'PM': _("Saint Pierre and Miquelon"),
    'PN': _("Pitcairn"),
    'PR': _("Puerto Rico"),
    'PS': _("Palestinian Territory"),
    'PT': _("Portugal"),
    'PW': _("Palau"),
    'PY': _("Paraguay"),
    'QA': _("Qatar"),
    'RE': _("Réunion"),
    'RO': _("Romania"),
    'RS': _("Serbia"),
    'RU': _("Russian Federation"),
    'RW': _("Rwanda"),
    'SA': _("Saudi Arabia"),
    'SB': _("Solomon Islands"),
    'SC': _("Seychelles"),
    'SD': _("Sudan"),
    'SE': _("Sweden"),
    'SG': _("Singapore"),
    'SH': _("Saint Helena"),
    'SI': _("Slovenia"),
    'SJ': _("Svalbard and Jan Mayen"),
    'SK': _("Slovakia"),
    'SL': _("Sierra Leone"),
    'SM': _("San Marino"),
    'SN': _("Senegal"),
    'SO': _("Somalia"),
    'SR': _("Suriname"),
    'SS': _("South Sudan"),
    'ST': _("Sao Tome and Principe"),
    'SV': _("El Salvador"),
    'SX': _("Sint Maarten (Dutch part)"),
    'SY': _("Syrian Arab Republic"),
    'SZ': _("Swaziland"),
    'TC': _("Turks and Caicos Islands"),
    'TD': _("Chad"),
    'TF': _("French Southern Territories"),
    'TG': _("Togo"),
    'TH': _("Thailand"),
    'TJ': _("Tajikistan"),
    'TK': _("Tokelau"),
    'TL': _("Timor-Leste"),
    'TM': _("Turkmenistan"),
    'TN': _("Tunisia"),
    'TO': _("Tonga"),
    'TR': _("Turkey"),
    'TT': _("Trinidad and Tobago"),
    'TV': _("Tuvalu"),
    'TW': _("Taiwan"),
    'TZ': _("Tanzania"),
    'UA': _("Ukraine"),
    'UG': _("Uganda"),
    'UM': _("United States Minor Outlying Islands"),
    'US': _("United States"),
    'UY': _("Uruguay"),
    'UZ': _("Uzbekistan"),
    'VA': _("Holy See (Vatican City State)"),
    'VC': _("Saint Vincent and the Grenadines"),
    'VE': _("Venezuela"),
    'VG': _("Virgin Islands, British"),
    'VI': _("Virgin Islands, U.S."),
    'VN': _("Viet Nam"),
    'VU': _("Vanuatu"),
    'WF': _("Wallis and Futuna"),
    'WS': _("Samoa"),
    'YE': _("Yemen"),
    'YT': _("Mayotte"),
    'ZA': _("South Africa"),
    'ZM': _("Zambia"),
    'ZW': _("Zimbabwe"),
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
