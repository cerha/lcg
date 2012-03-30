# -*- coding: utf-8 -*-

# Copyright (C) 2012 Brailcom, o.p.s.
#
# COPYRIGHT NOTICE
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
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

from lcg import UFont

braille_tables = {'en': ['en-us-g1.ctb'],
                  'cs': ['cs-g1.ctb']}
braille_hyphenation_tables = {'en': 'hyph_en_US.dic'}
# Hyphenation is quite buggy in current liblouis,
# so let's disable it for now.
braille_hyphenation_tables = {}
page_width = UFont(40)
page_height = UFont(25)
