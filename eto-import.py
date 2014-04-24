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
# eto-import.py
# 
# Takes options transactions in a CSV input file, stores the data in an 
# (sqlite) database.
#
# Current deficiencies:
#  - very quick and dirty, minimal error checking
#  - doesn't handle equities, or exercised options!
#  - correctly handles multiple closes for a trade (i.e. taking partial 
#    profit/loss), but not multiple entries.
#

import sys
import logging
import datetime
import csv
import sqlalchemy

from eto.util import init_logging
from eto.models import OptionActivity, ModelsError, db_get_session


init_logging(logging.DEBUG)
logger = logging.getLogger(__file__)
logger.info("IMPORTING ETO DATA: " + str(datetime.datetime.now()))

if (len(sys.argv) > 1):
    input_filename = sys.argv[1]
    logger.info("Using input file: " + input_filename)
else:
    sys.exit("Usage: import_activity.py <inputfile>")


session = db_get_session()

with open(input_filename, 'rb') as csvfile:
    reader = csv.reader(csvfile)

    for row in reader:
        logger.debug("[%s %s %s]", row[0], row[1], row[2])
        try:
            a = OptionActivity(row)
            session.add(a)
        except ModelsError as e:
            logger.error("****** ACTIVITY ERROR AT LINE %d" % (reader.line_num))
            logger.error("****** " + e.msg)


session.commit()
