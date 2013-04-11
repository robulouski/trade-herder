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
# gen_trades.py
#
# Matches up open/close options transactions ("activities") and generates a 
# consolidated record ("trade") with total profit and loss data for that 
# trade (which may consist of many open/close transactions, if, for example,
# partial profits were taken).
#
# Current deficiencies:
#  - very quick and dirty, minimal error checking
#  - doesn't handle equities, or exercised options!
#  - correctly handles multiple closes for a trade (i.e. taking partial 
#    profit/loss), but not multiple entries.
#


from __future__ import division
import sys
import decimal
import sqlalchemy

import models


def gen_trades(session):
    for i in session.query(models.OptionActivity).order_by(models.OptionActivity.ref_date): 
        if i.action_id == models.ActionType.BUY_TO_OPEN:
            print "OPENING OPTION TRADE:", i.symbol, i.description
            q = session.query(models.OptionTrade).filter(
                    models.OptionTrade.status_id==models.TradeStatus.OPEN).filter(
                    models.OptionTrade.symbol==i.symbol)
            t = q.first()
            if (t is None):
                t = models.OptionTrade(i.symbol, i.description, i.ref_date)
                # TODO: need to adjust this later if there are  multiple entries.
                t.entry_price = i.price
            else:
                print "*************** EXISTING OPEN TRADE  **********************"

            t.num_opens += 1
            t.entry_quantity += i.quantity
            t.brokerage += i.brokerage
            t.fees += i.fees
            t.net_total_cost += (i.net_total_cost * -1)
            t.gross_total_cost += (i.gross_total_cost * -1)
            session.add(t)
            session.commit()
            i.trade_id = t.id
            session.commit()
        elif i.is_closing_action():
            print "CLOSING OPTION TRADE:", i.symbol, i.description
            q = session.query(models.OptionTrade).filter(
                    models.OptionTrade.status_id==models.TradeStatus.OPEN).filter(
                    models.OptionTrade.symbol==i.symbol)
            t = q.first()
            if (t is None):
                print "***  ERROR: NO EXISTING OPEN TRADE FOUND FOR CLOSING TRADE!  **********************"
            else:
                t.num_closes += 1
                t.exit_quantity += i.quantity
                if t.exit_quantity > t.entry_quantity:
                    print "***  ERROR:  Exit quantity greater than entry quantity! *******************"
                elif t.entry_quantity - t.exit_quantity == 0:
                    print "\tTRADE CLOSED"
                    t.status_id = models.TradeStatus.CLOSED
                    t.close_date = i.ref_date
                else:
                    print "*** WARNING: Trade not yet closed, could have multiple parcels. ***********"
        
                # This is adjusted later if there are multiple closes.
                t.exit_price = i.price
                t.brokerage += i.brokerage
                t.fees += i.fees
                t.net_total_cost += i.net_total_cost
                t.gross_total_cost += i.gross_total_cost
                i.trade_id = t.id
                session.commit()
        else:
            print "\tTODO:", i.symbol, i.description

    #
    # Find any trades with more than one closing trade, and adjust exit price.
    #
    for t in session.query(models.OptionTrade).filter(
                models.OptionTrade.status_id==models.TradeStatus.CLOSED).filter(
                models.OptionTrade.num_closes>1):
        print "*** Adjusting exit price, %d closes for OPTION trade: %s %s" % \
            (t.num_closes, t.symbol, t.description)
        q = session.query(models.OptionActivity).filter(
            models.OptionActivity.action_id==models.ActionType.SELL_TO_CLOSE).filter(
            models.OptionActivity.trade_id==t.id)
        l = q.all()
        if len(l) == 0:
            print "*** ERROR: No closing trades found!!! ******"
            continue     
        if len(l) != t.num_closes:
            print "*** ERROR: Number of closing trades does not match num_closes value!!! ******"
        t.exit_price = decimal.Decimal(0)
        for a in l:
            t.exit_price += a.price
        t.exit_price /= t.num_closes
        session.commit()


if __name__ ==  "__main__":
    models.db_refresh_trades()
    session = models.Session()
    gen_trades(session)

