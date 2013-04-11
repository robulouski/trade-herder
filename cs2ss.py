#!/usr/bin/python
#
# cs2ss.py
#
# by Robert Iwancz <robulouski@gmail.com>
# Last updated August 2009
#
#
# Convert Commsec trade data to closed trade summary spreadsheet.
#
# Takes CSV file input generated from Commsec contract note page, cut and pasted
# into a spreadsheet, sorted by date, then saved as CSV file.
#
# Outputs CSV file with trade summaries for open and closed trades, and
# profit/loss summary.
#
# Usage: cs2ss.py <data.csv>
#
# Output will be: <data>_closed.csv
#                 <data>_open.csv
#
# Entries not reconcilled will be output on stderr.
#


import csv, sys, struct
#from decimal import *
from datetime import date

class ConfigOptions:
    pass

#
# Initialise configuration options.
#
g_config = ConfigOptions()
g_config.short_selling_allowed = False
g_config.date_range_filter = True
g_config.start_date = date(2008, 7, 1)
g_config.end_date = date(2009, 6, 30)
#g_config.start_date = date(2009, 7, 1)
#g_config.end_date = date(2010, 6, 30)


def parse_date_string(str):
    d = str.split('/')
    return date(int(d[2]), int(d[1]), int(d[0]))


def cmp_trade_position(l, r):
#    print l.close_date, r.close_date
    if (l.close_date < r.close_date):
#       print "less than"
        return -1
    elif (l.close_date > r.close_date):
#        print "greater than"
        return 1
    else:
#        print "equal"
        return 0



I_SYMBOL        = 3
I_DATE          = 1
I_TYPE          = 2 
I_QTY           = 4
I_PRICE         = 5
I_BROKERAGE     = 6
I_TOTAL         = 7
I_ID            = 0

class RawTrade:
    def __str__(self):
        if (self.type[0] == "B"):
            tdesc = "BUY"
        elif (self.type[0] == "S"):
            tdesc = "SELL"
        else:
            tdesc = "ERROR: INVALID TRADE TYPE"
        return '%4s %6i %4s @ %6.2f on %11s' % \
               (tdesc, self.qty, self.symbol, self.price, self.date)


class TradePosition:
    def __init__(self, symbol):
        self.symbol = symbol
        self.trade_list = []
        self.qty = 0
        self.open_date = ""
        self.close_date = ""
        self.buy_total_price = 0
        self.buy_price = 0
        self.buy_qty = 0
        self.sell_total_price = 0
        self.sell_price = 0
        self.sell_qty = 0
        self.gross_profit = 0
        self.total_brokerage = 0

    def add_trade(self, t):
        if (len(self.trade_list) == 0):
            self.open_date = t.date
        self.trade_list.append(t);
        self.qty += t.qty
        if (self.qty == 0):
            if (len(self.trade_list) >= 2):
                self.close_date = t.date
            else:
                sys.stderr.write('Zero quantity for TradePosition %s with '
                                 'less than 2 trades.\n' % (t.symbol))

    def is_closed(self):
        if (self.qty == 0 and len(self.trade_list) >= 2):
            return True
        else:
            return False

    def calc_trade_data(self):
        if (len(self.trade_list) > 2):
            sys.stderr.write('TradePosition %s has more than 2 trades.\n' \
                             % (self.symbol))
            return
        if (len(self.trade_list) < 2):
            if (self.is_closed()):
                sys.stderr.write('TradePosition %s has less than 2 trades.\n' \
                                 % (self.symbol))
            return
        t = self.trade_list[0]
        self.buy_price = t.price
        self.buy_qty = t.qty
        self.buy_total_price = self.buy_price * self.buy_qty
        self.total_brokerage += t.brokerage
        t = self.trade_list[1]
        self.sell_price = t.price
        self.sell_qty = t.qty
        self.sell_total_price = self.sell_price * self.sell_qty
        self.gross_profit = (self.sell_total_price + self.buy_total_price) * -1
        self.total_brokerage += t.brokerage

    def summary_data(self):
        self.calc_trade_data()
        return [str(self.close_date), str(self.open_date), self.symbol,
                str(self.buy_price), str(self.buy_qty), 
                str(self.buy_total_price), str(self.sell_price), 
                str(self.sell_qty), str(self.sell_total_price),
                str(self.gross_profit)]

#
# Globals
#
g_open_trades = {}
g_closed_trades = []
g_discard_date = []


filename = "csin.csv"
reader = csv.reader(open(filename, "rb"))
line_num = 0
print 'Opening input file...processing...'
print '=================================================='

try:
    reader.next();       # skip header
    line_num += 1
    for row in reader:
        line_num += 1
        is_okay = True
        t = RawTrade()
        t.symbol 	=  row[I_SYMBOL].strip()
        t.date 		=  parse_date_string(row[I_DATE])
        t.type 		=  row[I_TYPE]
        t.qty  		=  int(row[I_QTY])
        t.price 	=  float(row[I_PRICE])
        t.brokerage     =  float(row[I_BROKERAGE])
        t.total 	=  float(row[I_TOTAL])
        t.id 		=  row[I_ID]
        if (t.type[0] == "S"):
            t.qty *= -1
        elif (t.type[0] != "B"):
            sys.stderr.write('Invalid Trade Type for %s at line %d\n' %
                             (t.symbol, line_num))
            is_okay = False
        if (t.qty == 0):
            sys.stderr.write('Zero quantity trade for %s at line %d\n' %
                             (t.symbol, line_num))
            is_okay = False
            
        if (not is_okay):
            pass
        elif (t.symbol in g_open_trades):
            position = g_open_trades[t.symbol]
            position.add_trade(t)
            if (position.is_closed()):
                print '%5d: CLOSE %s' % (line_num, str(t))
                if (not g_config.date_range_filter or (position.close_date >=
                                                       g_config.start_date and
                                                       position.close_date <=
                                                       g_config.end_date)):
                    g_closed_trades.append(position)
                else:
                    g_discard_date.append(position)
                del g_open_trades[t.symbol]
            elif (t.qty > 0):
                print '%5d: +++++ %s' % (line_num, str(t))
            else:
                print '%5d: ----- %s' % (line_num, str(t))
        else:
            print '%5d: OPEN  %s' % (line_num, str(t))
            if (t.qty < 0 and not g_config.short_selling_allowed):
                sys.stderr.write('       ERROR: Attempting to short sell '
                                 '%s at line %d\n' % (t.symbol, line_num))
                is_okay = False
            else:
                ot = TradePosition(t.symbol)
                ot.add_trade(t)
                g_open_trades[t.symbol] = ot
except csv.Error, e:
    sys.exit('file %s, line %d: %s' % (filename, reader.line_num, e))


print
print '=================================================='
print '*** Processing Completed ***'
print '=================================================='
print
print 'There are %d remaining open trades.' % (len(g_open_trades))
if (len(g_open_trades) > 0):
    for v in g_open_trades.itervalues():
        print v.summary_data()
print
print '=================================================='
print 

if (g_config.date_range_filter):
    print ('%d closed trades were discarded due to the date filter:\n' %
           (len(g_discard_date)))
    if (len(g_discard_date) > 0):
        for pos in g_discard_date:
            print pos.summary_data()
    print '\n=================================================='
print
print 'There are %d closed trades.\n' % (len(g_closed_trades))

#
# Sort just in case, but should be in the correct order since the input file
# must be in chronological order for correct results.
#
g_closed_trades.sort(cmp_trade_position)

total_gross_profit = 0
total_brokerage = 0
writer = csv.writer(open("csout.csv", "wb"))
for pos in g_closed_trades:
    out = pos.summary_data();
    total_gross_profit += pos.gross_profit
    total_brokerage += pos.total_brokerage
    print out
    writer.writerow(out)


print '\n=================================================='
print '\nSummary\n'
print 'Total Gross Profit/Loss: %10.2f' % total_gross_profit
print 'Total Brokerage:         %10.2f' % total_brokerage
print 'Total Net Profit/Loss:   %10.2f' % (total_gross_profit - total_brokerage)
print 
print '=================================================='
print
