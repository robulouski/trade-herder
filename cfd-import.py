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
#  cfd-import.py
#

from __future__ import division, unicode_literals, print_function
import os.path
import sys
sys.path.insert(0, '.')

import sqlalchemy
import csv

import cfd.models


def raw_import():
    if (len(sys.argv) > 1):
        input_filename = sys.argv[1]
        print("Using input file:", input_filename)
    else:
        sys.exit("Usage: import_activity.py <inputfile>")

    session = cfd.models.get_session()

    count = 0
    ok = True

    with open(input_filename, 'rb') as csvfile:
        reader = csv.reader(csvfile)

        for row in reader:
            #print(row[0], row[1], row[2])
            try:
                a = cfd.models.RawData(row, count + 1)
                session.add(a)
                count = count + 1
            except cfd.models.ModelsError as e:
                print("****** IMPORT ERROR AT LINE %d" % (reader.line_num))
                print("****** ", e.msg)
                print(row)
                ok = False
                break

    if ok:
        session.commit()
        print("Imported %d entries." % (count,))

    return ok

if __name__ ==  "__main__":
    raw_import()
