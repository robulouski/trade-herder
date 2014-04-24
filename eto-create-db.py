#!/usr/bin/env python
#
#   The Trade Herder Scripts
#   Copyright (C) 2013-2014 Robert Iwancz
#   www.voidynullness.net
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################
#
#  eto-create-db.py
#

import os.path
import sys
import logging
import datetime
sys.path.insert(0, '.')

from eto.util import init_logging
from eto.models import db_create

logger = logging.getLogger(__file__)

if __name__ ==  "__main__":
    loglevel = logging.DEBUG
    init_logging(loglevel)
    logger.info("CREATING NEW ETO DATABASE: " + str(datetime.datetime.now()))
    db_create()
