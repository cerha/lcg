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

__version__ = '0.3.1'

"""Learning Content Genarator.

Set the environment variable LCG_LANGUAGE to an ISO 639-1 Alpha-2 language code
before importing this module to set the language used to lookup for the
translations of the texts inserted by the LCG to the generated documents.

"""

import config, gettext, os

_lang = os.environ.get('LCG_LANGUAGE')
if _lang and _lang != 'en':
    _t = gettext.translation('lcg', config.translation_dir, (_lang,))
else:
    _t = gettext.NullTranslations()
_t.install(unicode=True)

from util import *
from nodes import *
from resources import *
from content import *
from export import *
from wiki import *
import feed

from export import _html

# Resolve cyclic dependencies.
for module in (resources, nodes, content, exercises, export, html, wiki, feed):
    module.__dict__.update(globals())                                                                                                                                                      
