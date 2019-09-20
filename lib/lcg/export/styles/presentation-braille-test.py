# -*- coding: utf-8 -*-

# Copyright (C) 2012-2015 OUI Technology Ltd.
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Default presentation file for Braille output."""

from __future__ import unicode_literals

import lcg
import os

braille_tables = {'en': ['en-us-g1.ctb'],
                  'en2': ['en-us-g2.ctb'],
                  'cs': ['cs-g1.ctb',
                         os.path.join(os.path.dirname(lcg.__file__),
                                      'export/braille-tables/lcg.utb')],
                  'nemeth': ['nemeth.ctb']}
braille_hyphenation_tables = {'en': 'hyph_en_US.dic',
                              'cs': 'hyph_cs_CZ.dic'}
page_width = lcg.UFont(20)
page_height = lcg.UFont(10)
left_page_footer = lcg.Container((lcg.PageNumber(),
                                  lcg.HSpace(lcg.UFont(3)),
                                  lcg.PageHeading(),))
right_page_footer = lcg.Container((lcg.PageHeading(),
                                   lcg.HSpace(lcg.UFont(3)),
                                   lcg.PageNumber(),))

braille_math_rules = 'czech'  # 'nemeth', 'czech'
