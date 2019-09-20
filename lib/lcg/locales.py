# -*- coding: utf-8 -*-

# Copyright (C) 2004-2015 OUI Technology Ltd.
# Copyright (C) 2019 Tomáš Cerha <t.cerha@gmail.com>
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

"""LCG locale data.

This module defines the base class for locale data and a derived class for each supported locale.

"""

from __future__ import unicode_literals


class LocaleData(object):
    """Locale data base class.

    The attributtes defined by this class form the LCG locale data API and assign default values.
    Locale data for a particular locale are defined by defining a derived class and overriding
    those attributes, which differ from the defaults.  When this derived class has a name in the
    form 'LocaleData_<name>', where '<name>' is the name of the locale, this definition will be
    used by LCG 'Translator' automatically when formatting localizable values.

    The instances of this class should always be treated read-only and thus can be considered
    immutable.

    """
    date_format = '%Y-%m-%d'
    time_format = '%H:%M'
    exact_time_format = '%H:%M:%S'
    first_week_day = 0
    """First day of the week as a numeric index according to ISO-8601 (0=Monday, 6=Sunday)."""
    negative_sign = '-'
    positive_sign = ''
    decimal_point = '.'
    thousands_sep = None
    grouping = (3, 3, 3, 3)
    mon_decimal_point = None
    mon_thousands_sep = None
    mon_grouping = None
    default_timezone = None

    def __init__(self):
        if self.mon_decimal_point is None:
            self.mon_decimal_point = self.decimal_point
        if self.mon_thousands_sep is None:
            self.mon_thousands_sep = self.thousands_sep
        if self.mon_grouping is None:
            self.mon_grouping = self.grouping


class LocaleData_cs(LocaleData):
    date_format = "%d.%m.%Y"
    decimal_point = ','
    thousands_sep = u'\xa0'


class LocaleData_de(LocaleData):
    date_format = "%d.%m.%Y"
    first_week_day = 6
    thousands_sep = ','


class LocaleData_en(LocaleData):
    date_format = "%d/%m/%Y"
    time_format = "%I:%M %p"
    exact_time_format = "%I:%M:%S %p"
    first_week_day = 6
    thousands_sep = ','


class LocaleData_es(LocaleData):
    date_format = "%d/%m/%Y"


class LocaleData_no(LocaleData):
    date_format = "%d.%m.%Y"
    time_format = "%H.%M"
    exact_time_format = "%H.%M.%S"


class LocaleData_pl(LocaleData):
    date_format = "%Y-%m-%d"


class LocaleData_sk(LocaleData):
    date_format = "%d.%m.%Y"
    decimal_point = ','
    thousands_sep = u'\xa0'
