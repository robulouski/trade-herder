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
#  cfd-report.py
#

from __future__ import division, unicode_literals, print_function
import os.path
import sys
import re
import sqlalchemy
import decimal
import datetime as dt
import argparse

sys.path.insert(0, '.')

from cfd.models import get_session, RawData, ModelsError
from cfd.util import mkdate

D = decimal.Decimal

def legacy_summary(start_date, end_date):
    session = get_session()

    total_profit = D(0)
    count_trades = 0
    interest_long = D(0)
    interest_short = D(0)
    commission= D(0)
    other_comm= D(0)
    xfee= D(0)
    dividends= D(0)
    deposit= D(0)
    withdraw= D(0)
    final_balance = D(0)
    unknown = D(0)

    if start_date and end_date:
        q = session.query(RawData).filter(RawData.ref_date>=start_date,RawData.ref_date<=end_date)
    elif start_date:
        q = session.query(RawData).filter(RawData.ref_date>=start_date)
    elif end_date:
        q = session.query(RawData).filter(RawData.ref_date<=end_date)
    else:
        q = session.query(RawData)

    for i in q:
        if i.category == RawData.CAT_TRADE:
            total_profit += i.amount
            count_trades += 1
        elif i.category == RawData.CAT_TRANSFER:
            if i.type == "DEPO":
                deposit += i.amount
            elif i.type == "WITH":
                withdraw += i.amount
        elif i.category == RawData.CAT_XFEE:
            xfee += i.amount
        elif i.category == RawData.CAT_INTEREST:
            if i.type == "DEPO":
                interest_short += i.amount            
            elif i.type == "WITH":
                interest_long += i.amount
        elif i.category == RawData.CAT_DIVIDEND:
            dividends += i.amount
        elif i.category == RawData.CAT_COMM:
            commission += i.amount
        elif i.category == RawData.CAT_RISK:
            other_comm += i.amount
        else:
            unknown += i.amount
            
        final_balance += i.amount


    print("CFD LEGACY SUMMARY\n")
    print("Total profit/loss:                      $%s" % (str(total_profit),))
    print("Number of trades: ", count_trades)
    print("\nInterest paid on long positions:        $%s\n"
          "Interest earned on short positions:     $%s\n" % (str(interest_long), str(interest_short)))
    print("Commissions:                            $%s\n"
          "Guaranteed stop loss commissions:       $%s\n" % (str(commission), str(other_comm)))
    print("ASX Exchange data fees:                 $%s\n\n"
          "Total dividend adjustments:             $%s\n" % (str(xfee), str(dividends)))

    print("Deposits:      $%s\nWithdrawals:   $%s" % (str(deposit), str(withdraw)))
    print("Unknown:       $%s\n\nFINAL BALANCE: $%s" % (str(unknown), str(final_balance)))

if __name__ ==  "__main__":
    parser = argparse.ArgumentParser(description='ig-csv-export: Export trading data into CSV files')
    parser.add_argument('--start', type=mkdate, help='start date')
    parser.add_argument('--end', type=mkdate, help='end date')
    parser.add_argument('--fyau', type=int, help='Australian financial year (ending)')

    start = None
    end = None
    args = parser.parse_args()
    #print(args)
    if args.fyau:
        year = args.fyau
        if args.start or args.end:
            sys.exit("Can't specify fyau with start and/or end dates.")
        if year < 1900 or year > 9999:
            sys.exit("Invalid year")
        start = dt.date(year - 1, 7, 1)
        end = dt.date(year, 6, 30)
    else:
        if args.start:
            start = args.start
        if args.end:
            end = args.end

    legacy_summary(start, end)
