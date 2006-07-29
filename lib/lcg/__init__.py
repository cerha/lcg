# -*- coding: iso8859-2 -*-
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

__version__ = '0.3.3'

"""Learning Content Genarator."""

from i18n import *

import __builtin__
if not __builtin__.__dict__.has_key('_'):
    __builtin__.__dict__['_'] = TranslatableText

from util import *
from nodes import *
from resources import *
from content import *
from export import *
from wiki import *
import feed

from export import _html

# Resolve cyclic dependencies.
for module in (resources, nodes, content, exercises, export, html, wiki, feed,
               i18n):
    module.__dict__.update(globals())
