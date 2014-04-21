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
#  cfd-csv-export.py
#

from __future__ import division, unicode_literals, print_function
import os
import sys
import re
import csv
import sqlalchemy
import decimal
import datetime as dt
import argparse

sys.path.insert(0, '.')

from cfd.models import get_session, RawData, ModelsError, StockTrade
from cfd.util import mkdate

D = decimal.Decimal


class ExportError(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, msg):
        self.msg = msg


class ExportData(object):
    ''' Handle writing of output to files.'''

    def __init__(self, dirname):
        # output files
        self.of_div = None
        self.ow_div = None
        self.of_longint = None
        self.ow_longint = None
        self.of_shortint = None 
        self.ow_shortint = None 
        self.of_unk = None 
        self.ow_unk = None 

        self.setup_dir(dirname)
        self.setup_files()

    def setup_dir(self, dirname):
        self.dirname = dirname
        if not dirname:
            raise ExportError("INVALID OUTPUT DIRECTORY")

        if os.path.exists(dirname):
            if not os.path.isdir(dirname):
                raise ExportError("Output directory is a file")
            print("Using directory " + dirname + " for output")
        else:
            print("Creating output directory " + dirname)
            os.mkdir(dirname)

    def setup_files(self):
        self.of_div = open(os.path.join(self.dirname, "div.csv"), "wb")
        self.of_longint = open(os.path.join(self.dirname, "longint.csv"), "wb")
        self.of_shortint = open(os.path.join(self.dirname, "shortint.csv"), "wb")
        self.of_unk = open(os.path.join(self.dirname, "unknown.csv"), "wb")
        self.of_trade = open(os.path.join(self.dirname, "trade.csv"), "wb")

        self.ow_div = csv.writer(self.of_div)
        self.ow_longint = csv.writer(self.of_longint)
        self.ow_shortint = csv.writer(self.of_shortint)
        self.ow_unk = csv.writer(self.of_unk)
        self.ow_trade = csv.writer(self.of_trade)
        self.ow_trade.writerow(
            ['Exit Date', 'Entry Date',
             'Company',
             'Qty',
             'Buy Price', 'Total Position Entry',
             'Sell Price', 'Total Position Exit',
             'Entry Commission', 'Exit Commission', 'Other Commission',	
             'Gross Return'])

    def clean_up(self):
        self.of_div.close()
        self.of_longint.close()
        self.of_shortint.close()
        self.of_unk.close()


    def cash_list(self, raw):
        '''List for "cash" transactions, like dividends, interest, etc'''
        return [str(raw.ref_date), raw.description, str(raw.amount)]

    def div(self, raw):
        self.ow_div.writerow(self.cash_list(raw))

    def shortint(self, raw):
        self.ow_shortint.writerow(self.cash_list(raw))

    def longint(self, raw):
        self.ow_longint.writerow(self.cash_list(raw))

    def unknown(self, raw):
        self.ow_unk.writerow(self.cash_list(raw))

    def trade(self, t):
        #
        # Order of columns we want in the output file:
        #     Exit Date	
        #     Entry Date	
        #     Company	
        #     Qty	
        #     Buy Price	
        #     Total Position Entry	
        #     Sell Price	
        #     Total Position Exit	
        #     Entry Commission	
        #     Exit Commission	
        #     Other Commission	
        #     Gross Return	
        row = [
            t.exit_date.strftime('%d/%m/%Y'), t.entry_date.strftime('%d/%m/%Y'),
            t.symbol,
            str(t.quantity),
            str(t.entry_price), str(t.get_entry_total()),
            str(t.exit_price),  str(t.get_exit_total()),
            str(t.entry_brokerage),
            str(t.exit_brokerage),
            str(t.fees),
            str(t.gross_total_imp)
            ]
        self.ow_trade.writerow(row)



def csv_export(start_date, end_date, dirname):
    export = ExportData(dirname)
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
    q = q.order_by(RawData.import_id, RawData.ref_date)

    #
    # First export "cash" type transactions (dividends, interest, etc)
    #
    for i in q:
        if i.category == RawData.CAT_TRADE or i.category == RawData.CAT_INDEX:
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
                export.shortint(i)
            elif i.type == "WITH":
                interest_long += i.amount
                export.longint(i)
        elif i.category == RawData.CAT_DIVIDEND:
            dividends += i.amount
            export.div(i)
        elif i.category == RawData.CAT_COMM:
            commission += i.amount
        elif i.category == RawData.CAT_RISK:
            other_comm += i.amount
        else:
            unknown += i.amount
            export.unknown(i)
            
        final_balance += i.amount

    #
    # Now export trades
    #
    if start_date and end_date:
        q = session.query(StockTrade).filter(StockTrade.exit_date>=start_date,StockTrade.exit_date<=end_date)
    elif start_date:
        q = session.query(StockTrade).filter(StockTrade.exit_date>=start_date)
    elif end_date:
        q = session.query(StockTrade).filter(StockTrade.exit_date<=end_date)
    else:
        q = session.query(StockTrade)
    q = q.order_by(StockTrade.exit_date, StockTrade.import_id)
    for i in q:
        export.trade(i)

    #
    # Print summary
    #
    print("\nCFD EXPORT SUMMARY")
    if not start_date and not end_date:
        print("[entire data set]\n")
    else:
        datestr = ""
        if start_date:
            datestr += "FROM " + str(start_date) + " "
        if end_date:
            datestr += "TO " + str(end_date)
        datestr += '\n'
        print(datestr)

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

    export.clean_up()


if __name__ ==  "__main__":
    parser = argparse.ArgumentParser(description='ig-csv-export: Export trading data into CSV files')
    parser.add_argument('--start', type=mkdate, help='start date')
    parser.add_argument('--end', type=mkdate, help='end date')
    parser.add_argument('--fyau', type=int, help='Australian financial year (ending)')
    parser.add_argument('DIR', help='output directory for report files.')

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
    
    outdir = args.DIR
    csv_export(start, end, outdir)
