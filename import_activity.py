#!/usr/bin/env python
#
#  Copyright (c) 2013 Robert Iwancz
#  robulouski@gmail.com
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
#
##############################################################################  
#
# import_activity.py
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


#from __future__ import division
import sys
import sqlalchemy
import csv


import models

session = models.Session()



if (len(sys.argv) > 1):
    input_filename = sys.argv[1]
    print "Using input file:", input_filename
else:
    sys.exit("Usage: import_activity.py <inputfile>")


with open(input_filename, 'rb') as csvfile:
    reader = csv.reader(csvfile)

    for row in reader:
        print row[0], row[1], row[2]
        try:
            a = models.OptionActivity(row)
            #a.init_from_list(row)
            session.add(a)
        except models.ModelsError as e:
            print "****** ACTIVITY ERROR AT LINE %d" % (reader.line_num)
            print "****** ", e.msg

session.commit()
