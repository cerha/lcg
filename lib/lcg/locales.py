# -*- coding: utf-8 -*-
#
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

"""LCG locale data.

This module defines the base class for locale data and a derived class for each supported locale.

"""

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
    weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    negative_sign = '-'
    positive_sign = ''
    decimal_point = '.'
    thousands_sep = None
    grouping = (3,)
    mon_decimal_point = None
    mon_thousands_sep = None 
    mon_grouping = None
 
    def __init__(self):
        if self.mon_decimal_point is None:
            self.mon_decimal_point = self.decimal_point
        if self.mon_thousands_sep is None:
            self.mon_thousands_sep = self.thousands_sep
        if self.mon_grouping is None:
            self.mon_grouping = self.grouping


class LocaleData_cs(LocaleData):
    date_format = "%d.%m.%Y"
    exact_time_format = "%H:%M:%S"
    weekdays = (u"Po", u"Út", u"St", u"Čt", u"Pá", u"So", u"Ne")
    decimal_point = ','
    thousands_sep = u'\xa0'

class LocaleData_de(LocaleData):
    date_format = "%d.%m.%Y"
    weekdays = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")
    thousands_sep = ','

class LocaleData_en(LocaleData):
    date_format = "%m/%d/%Y"
    time_format = "%I:%M %p"
    exact_time_format = "%I:%M:%S %p"
    thousands_sep = ','
            
class LocaleData_es(LocaleData):
    date_format = "%d/%m/%Y"
    weekdays = (u"lun", u"mar", u"mié", u"jue", u"vie", u"sáb", u"dom")

    
class LocaleData_no(LocaleData):
    date_format = "%d.%m.%Y"
    time_format = "%H.%M"
    exact_time_format = "%H.%M.%S"
    weekdays = (u"ma", u"ti", u"on", u"to", u"fr", u"lø", u"sø")


class LocaleData_pl(LocaleData):
    date_format = "%Y-%m-%d"
    weekdays = (u"Pn", u"Wt", u"Śr", u"Cz", u"Pt", u"So", u"N")

class LocaleData_sk(LocaleData):
    date_format = "%d.%m.%Y"
    weekdays = (u"Po", u"Ut", u"St", u"Št", u"Pi", u"So", u"Ne")
    thousands_sep = u'\xa0'
