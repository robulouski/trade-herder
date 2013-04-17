#!/usr/bin/env python
#
# csv_us2au_date.py
#
# by Robert Iwancz <robulouski@gmail.com>
# Last updated Apr 2013
#
# Takes CSV file with a date/datetime field in US format: 
#   MM/DD/YYYY <optional-time-part> 
# and converts date field to sane format: 
#   DD/MM/YYY <optional-time-part>
# If there's any text after the date, it's included in the results unmodified,
# so should work for both date and date-time fields.
# Assumes:
# - comma seperator
# - first line in file is header, and discarded, so output is without header.
#

import sys
import re
import csv


if (len(sys.argv) > 3):
    input_filename = sys.argv[1]
    print "Using input file:", input_filename
    output_filename = sys.argv[2]
    print "Using output file:", output_filename
    field_index = int(sys.argv[3])
else:
    sys.exit("Usage: csv_us2au_date.py <inputfile> <outputfile> <fieldindex>")


prog = re.compile(r'(\d+)/(\d+)/(\d+)(.*)')

of = open(output_filename, "wb")

with open(input_filename, 'rb') as csvfile:
    writer = csv.writer(of)
    reader = csv.reader(csvfile)
    next(csvfile) 	# skip first line!

    for row in reader:
        m = prog.search(row[field_index])
        if m is None:
            print "INVALID DATE AT LINE %d" % (reader.line_num)
            v = row[field_index]
            row[field_index] = '"' + v + '"'
        else:
            row[field_index] = "%02d/%02d/%d" % (int(m.group(2)), 
                                                 int(m.group(1)), 
                                                 int(m.group(3)))
            if m.group(4):
                row[field_index] += m.group(4)
        writer.writerow(row)

