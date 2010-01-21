# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007, 2008, 2009, 2010 Brailcom, o.p.s.
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

__version__ = '0.4.0'

"""Learning Content Genarator."""

import urllib

import config
from i18n import *
from locales import *
from util import *
from nodes import *
from resources import *
from content import *
from export import *
from parse import *
from read import *

# Resolve cyclic dependencies.

import resources, nodes, content, export, parse, i18n, util

for module in (resources, nodes, content, export, parse, i18n, util):
    module.__dict__.update(globals())
