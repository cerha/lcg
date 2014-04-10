# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2014 Brailcom, o.p.s.
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

__version__ = '0.6.1'

"""Learning Content Genarator."""

import urllib

import config
from i18n import *
from locales import *
from util import *
from nodes import *
from resources import *
from units import Unit, UAny, UFont, UMm, UPoint, USpace, FontFamily, \
     HorizontalAlignment, VerticalAlignment, Orientation
from content import *
from widgets import Widget, FoldableTree, Notebook, PopupMenuCtrl, PopupMenuItem, CollapsiblePane
from presentation import *
from export import *
from parse import *
from read import *
from transform import data2content, data2html, html2data, HTML2XML, XML2HTML, XML2Content

# Resolve cyclic dependencies.

import resources, nodes, content, export, parse, i18n, util

for module in (resources, nodes, content, export, parse, i18n, util):
    module.__dict__.update(globals())
