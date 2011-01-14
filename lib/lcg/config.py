# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2009, 2011 Brailcom, o.p.s.
#
# This program is free software; you can redistribute it and/or modify it under the terms of the
# GNU General Public License as published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
# even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; if
# not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# 02111-1307 USA

"""LCG configuration variables."""

default_resource_dir = None
"""The LCG comes with a set of default resources (style sheets, scripts and
media files).  They are used if no custom files of the same name are present in
the source directory.  This variable specifies the name of the directory, where
LCG default resources are installed."""

allow_backref = True
"""Boolean flag indicating, whether using backreferences in section titles is
allowed."""
