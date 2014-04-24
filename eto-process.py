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
# eto-process.py
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
import logging
import datetime
import decimal
import sqlalchemy

from eto.util import init_logging
from eto.models import OptionTrade, OptionActivity, ActionType, TradeStatus
from eto.models import db_refresh_trades, db_get_session

logger = logging.getLogger(__file__)

def gen_trades():
    session = db_get_session()

    for i in session.query(OptionActivity).order_by(OptionActivity.ref_date): 
        if i.action_id == ActionType.BUY_TO_OPEN:
            logger.debug("OPENING OPTION TRADE: %s %s", i.symbol, i.description)
            q = session.query(OptionTrade).filter(
                    OptionTrade.status_id==TradeStatus.OPEN).filter(
                    OptionTrade.symbol==i.symbol)
            t = q.first()
            if (t is None):
                t = OptionTrade(i.symbol, i.description, i.ref_date)
                # TODO: need to adjust this later if there are  multiple entries.
                t.entry_price = i.price
            else:
                logger.debug("*************** EXISTING OPEN TRADE  "
                             "**********************")

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
            logger.debug("CLOSING OPTION TRADE: %s %s", i.symbol, i.description)
            q = session.query(OptionTrade).filter(
                    OptionTrade.status_id==TradeStatus.OPEN).filter(
                    OptionTrade.symbol==i.symbol)
            t = q.first()
            if (t is None):
                logger.error("***  NO EXISTING OPEN TRADE FOUND "
                             "FOR CLOSING TRADE!  **********************")
            else:
                t.num_closes += 1
                t.exit_quantity += i.quantity
                if t.exit_quantity > t.entry_quantity:
                    logger.error("***  Exit quantity greater than "
                                 "entry quantity! *******************")
                elif t.entry_quantity - t.exit_quantity == 0:
                    logger.debug("\tTRADE CLOSED")
                    t.status_id = TradeStatus.CLOSED
                    t.close_date = i.ref_date
                else:
                    logger.warn("*** Trade not yet closed, "
                                 "could have multiple parcels. ***********")
        
                # This is adjusted later if there are multiple closes.
                t.exit_price = i.price
                t.brokerage += i.brokerage
                t.fees += i.fees
                t.net_total_cost += i.net_total_cost
                t.gross_total_cost += i.gross_total_cost
                i.trade_id = t.id
                session.commit()
        else:
            logger.debug("\tTODO: %s %s", i.symbol, i.description)

    #
    # Find any trades with more than one closing trade, and adjust exit price.
    #
    for t in session.query(OptionTrade).filter(
                OptionTrade.status_id==TradeStatus.CLOSED).filter(
                OptionTrade.num_closes>1):
        logger.debug("*** Adjusting exit price, %d closes for OPTION trade: %s %s",
                     t.num_closes, t.symbol, t.description)
        q = session.query(OptionActivity).filter(
            OptionActivity.action_id==ActionType.SELL_TO_CLOSE).filter(
            OptionActivity.trade_id==t.id)
        l = q.all()
        if len(l) == 0:
            logger.error("*** No closing trades found!!! ******")
            continue     
        if len(l) != t.num_closes:
            logger.error("*** Number of closing trades does not match "
                         "num_closes value!!! ******")
        t.exit_price = decimal.Decimal(0)
        for a in l:
            t.exit_price += a.price
        t.exit_price /= t.num_closes
        session.commit()


if __name__ ==  "__main__":
    loglevel = logging.DEBUG
    init_logging(loglevel)
    logger.info("ETO PROCESSING: " + str(datetime.datetime.now()))
    db_refresh_trades()
    gen_trades()
    logger.info("END (ETO PROCESSING) " + str(datetime.datetime.now()))

