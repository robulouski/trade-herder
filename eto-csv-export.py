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
# eto-csv-export.py
# 
# Exports trade data (csv) in a format that can be easily put into a 
# spreadsheet that won't give my tax agent an apoplectic fit.
#
# Current deficiencies:
#  - quick and dirty, fairly minimal error checking
#  - doesn't handle equities, or exercised options!
#  - correctly handles multiple closes for a trade (i.e. taking partial 
#    profit/loss), but not multiple entries.
#

from __future__ import division, print_function
import sys
import logging
import argparse
import csv
import re
import datetime as dt
import sqlalchemy

from eto.util import init_logging
from eto.models import OptionTrade, OptionActivity, ActionType, TradeStatus
from eto.models import db_get_session
from cfd.util import mkdate  # TODO: move mkdate elsewhere???


logger = logging.getLogger(__file__)

g_output_filename = "outeto"


def cmp_trade_data_open_date(l, r):
    if (l.trade.open_date < r.trade.open_date):
        return -1
    elif (l.trade.open_date > r.trade.open_date):
        return 1
    else:
        return 0


def cmp_trade_data_close_date(l, r):
    if (l.trade.close_date < r.trade.close_date):
        return -1
    elif (l.trade.close_date > r.trade.close_date):
        return 1
    else:
        return 0


g_closed_trades = []

g_trade_events = []


g_raw_col_headings = [
    'Open Date',
    'Quantity',
    'Symbol',
    'Description',
    'Open Price',
    'Commission',
    'Reg Fees',
    'Net Open Trade',
    'Close Date',
    'Close Price',
    'Commission',
    'Reg Fees',
    'Net Close Trade',
    'Net Profit / Loss',
    'Total Commissions',
    'Gross Profit / Loss'
]


g_format_col_headings = [
    'Close Date',
    'Open Date',
    'Quantity',
    'Symbol',
    'Description',
    'Open Price',
    'Commission',
    'Reg Fees',
    'Net Open Trade',
    'Close Price',
    'Commission',
    'Reg Fees',
    'Net Close Trade',
    'Net Profit / Loss',
    'Total Commissions',
    'Gross Profit / Loss'
]


class TradeEvent:
    """
    We will consider a "trade event" to be a closing trade, with
    corresponding opening trade data.  For trades with multiple
    legs/parcels, the open trade data will have been adjusted appropriately.
    """

    def __init__(self, symbol, desc, qty):
        self.symbol = symbol
        self.description = desc
        self.qty = qty
        self.parcel = 1
        self.parcel_count = 1

    def open(self, d, p, b, f, net):
        self.open_date = d
        self.open_price = p
        self.open_brokerage = b
        self.open_fees = f
        self.open_net = net
        self.open_gross = self.qty * self.open_price * \
            OptionActivity.OPTION_CONTRACT_SIZE

    def close(self, d, p, b, f, net):
        self.close_date = d
        self.close_price = p
        self.close_brokerage = b
        self.close_fees = f
        self.close_net = net
        self.close_gross = self.qty * self.close_price * \
            OptionActivity.OPTION_CONTRACT_SIZE

        self.net_total = self.close_net - self.open_net
        self.gross_total = self.close_gross - self.open_gross

    def totals(self, n, g):
        pass

    def set_parcel(self, p, c):
        self.parcel = p
        self.parcel_count = c

    def get_total_costs(self):
        return (self.open_brokerage + self.close_brokerage + 
                self.open_fees + self.close_fees)
    

    def get_raw_result(self):
        result =  [
            str(self.open_date),
            self.qty,
            self.symbol,
            self.description,
            self.open_price,
            self.open_brokerage,
            self.open_fees,
            self.open_net,
            str(self.close_date),
            self.close_price,
            self.close_brokerage,
            self.close_fees,
            self.close_net,
            self.net_total,
            self.get_total_costs(),
            self.gross_total
            ]
        if self.parcel_count != 1:
            result.append("Partially closed position %d of %d" % \
                              (self.parcel, self.parcel_count))
        return result


    def get_format_result(self):
        result =  [
            self.close_date.strftime('%d/%m/%Y'),
            self.open_date.strftime('%d/%m/%Y'),
            self.qty,
            self.symbol,
            self.description,
            self.open_price,
            self.open_brokerage,
            self.open_fees,
            self.open_net,
            self.close_price,
            self.close_brokerage,
            self.close_fees,
            self.close_net,
            self.net_total,
            self.get_total_costs(),
            self.gross_total
            ]
        if self.parcel_count != 1:
            result.append("Partially closed position %d of %d" % \
                              (self.parcel, self.parcel_count))
        return result


class TradeData:
    """
    The TradeData class is essentially a container for an Trade object with
    it's assocaited (open and close) Activity objects.
    """

    def __init__(self, trade_id, symbol):
        self.trade_id = trade_id
        self.symbol = symbol
        self.open_acts = []
        self.close_acts = []
        self.trade = None

    def add_open_activity(self, a):
        self.open_acts.append(a)

    def add_close_activity(self, a):
        self.close_acts.append(a)

    def add_trade(self, t):
        self.trade = t

    def get_raw_events(self, event_list, start_date = None, end_date = None):
        if self.trade.num_opens == 1 and self.trade.num_closes == 1:
            o = self.open_acts[0]
            c = self.close_acts[0]
            
            if (   (start_date is not None and c.ref_date.date() < start_date)
                or (end_date is not None and c.ref_date.date() > end_date)):
                return

            te = TradeEvent(c.symbol, c.description, c.quantity)
            te.open(o.ref_date,
                    o.price,
                    o.brokerage,
                    o.fees,
                    o.net_total_cost)
            te.close(c.ref_date,
                    c.price,
                    c.brokerage,
                    c.fees,
                    c.net_total_cost)
            te.totals(self.trade.net_total_cost,
                      self.trade.gross_total_cost)
            event_list.append(te)

        elif self.trade.num_opens == 1 and self.trade.num_closes > 1:
            o = self.open_acts[0]
            o.closed_quantity = 0
            parcel = 1
            for c in self.close_acts:
                te = TradeEvent(c.symbol, c.description, c.quantity)
                o.closed_quantity += c.quantity
                te.open(o.ref_date,
                        o.price,
                        o.brokerage / self.trade.num_closes,
                        o.fees / self.trade.num_closes,
                        o.net_total_cost / self.trade.num_closes)
                te.close(c.ref_date,
                         c.price,
                         c.brokerage,
                         c.fees,
                         c.net_total_cost)
                te.totals(self.trade.net_total_cost / self.trade.num_closes,
                          self.trade.gross_total_cost / self.trade.num_closes)
                te.set_parcel(parcel, self.trade.num_closes)
                parcel += 1

                # TODO: Optimise by eliminating TradeData that can't
                #       possibly contain TradeEvents for the date range
                #       specified.
                if (    (start_date is None or c.ref_date.date() >= start_date) 
                        and 
                        (end_date is None or c.ref_date.date() <= end_date)):
                    event_list.append(te)
            
            if o.closed_quantity != o.quantity:
                logging.error("*** QTY MISMATCH %s %s: %d of %d closed for multi-trade",
                              self.trade.symbol, self.trade.description, 
                              int(o.closed_quantity), int(o.quantity))
        else:
            logging.error("*** UNSUPPORTED: Multiple opens %s %s", 
                          self.trade.symbol, self.trade.description)



def get_trades():
    session = db_get_session()

    for t in session.query(OptionTrade):
        logging.debug("TRADE: %s %s", t.symbol, t.description)
        if t.num_closes == 0:
            if t.status_id == TradeStatus.OPEN:
                logging.debug("*** Ignoring open trade %d", t.id)
            else:
                logging.error("*** Zero count closing activities for trade %d", t.id)
            continue

        td = TradeData(t.id, t.symbol)
        td.add_trade(t)

        for a in session.query(OptionActivity).filter(
                OptionActivity.trade_id==t.id).order_by(
                OptionActivity.ref_date): 
            if a.action_id == ActionType.BUY_TO_OPEN:
                td.add_open_activity(a)
            elif a.action_id == ActionType.SELL_TO_CLOSE:
                td.add_close_activity(a)
            else:
                logging.warn("*** Unexpected action in acivity %d", a.id)

        if len(td.open_acts) != t.num_opens or t.num_opens == 0:
            logging.error("*** open activity mismatch for trade %d", t.id)
        if len(td.close_acts) != t.num_closes or t.num_closes == 0:
            logging.error("*** close activity mismatch for trade %d", t.id)
        g_closed_trades.append(td)


def generate_events(start, end):
    if start is None and end is None:
        logging.info("Generating trade events for all date data.")
    else:
        if start is None:
            logging.info("Generating trade events until %s", str(end))
        elif end is None:
            logging.info("Generating trade events from %s", str(start))
        else:
            logging.info("Generating trade events from %s to %s", 
                         str(start), str(end))
    g_closed_trades.sort(cmp_trade_data_close_date)
    for td in g_closed_trades:
        td.get_raw_events(g_trade_events, start, end)


def export_raw_events():
    total_net_profit = 0
    total_gross_profit = 0
    total_costs = 0

    filename = g_output_filename + "_raw_events.csv"
    logging.info("Exporting raw closing trade events to %s", filename)
    writer = csv.writer(open(filename, "wb"))
    writer.writerow(g_raw_col_headings)
    for te in g_trade_events:
        total_net_profit += te.net_total
        total_gross_profit += te.gross_total
        total_costs += te.get_total_costs()
        out = te.get_raw_result()
        writer.writerow(out)
    
    print('\n==================================================')
    print('\nSummary "Raw"\n')
    print('Total Gross Profit/Loss: %10.2f' % total_gross_profit)
    print('Total brokerage/costs:   %10.2f' % total_costs)
    print('Total Net Profit/Loss:   %10.2f' % total_net_profit)
    print('\n==================================================')



#
#  "formatted" events have columns in slightly different order, and
#  datetime fields are output as just the date in AU format (DMY).
#
def export_formatted_events():
    filename = g_output_filename + "_format_events.csv"
    logging.info("Exporting closing trade events to %s", filename)
    with open(filename, "wb") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(g_format_col_headings)
        for te in g_trade_events:
            out = te.get_format_result()
            writer.writerow(out)
        


if __name__ ==  "__main__":
    parser = argparse.ArgumentParser(description='eto-csv-export: ' + 
                         'Export options trading data summary into CSV files')
    parser.add_argument('--start', type=mkdate, help='start date')
    parser.add_argument('--end', type=mkdate, help='end date')
    parser.add_argument('--fyau', type=int, help='Australian financial year (ending)')
    parser.add_argument('outprefix', help='output filename prefix')

    start = None
    end = None
    args = parser.parse_args()

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

    g_output_filename = args.outprefix

    loglevel = logging.DEBUG
    init_logging(loglevel)
    logger.info("ETO EXPORT: " + str(dt.datetime.now()))

    get_trades()
    generate_events(start, end)
    export_formatted_events()
    export_raw_events()

