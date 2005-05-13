# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005 Brailcom, o.p.s.
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

__version__ = '0.9'

import gettext
t = gettext.NullTranslations()
t.install(unicode=True)

from resources import *
from course import *
from content import *
from export import *
import ims
import feed
import wiki
import config

# �e�en� cyklick�ch z�vislost� soubor�
for file in (resources, course, content, feed, wiki):
    file.__dict__.update(globals())
                                                                                                                                                      
