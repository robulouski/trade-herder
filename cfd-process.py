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
#  cfd-process.py
#

from __future__ import division, unicode_literals, print_function
import os.path
import sys
import logging
import re
import sqlalchemy
import decimal
import datetime

sys.path.insert(0, '.')

from cfd.models import RawData, StockPosition, StockActivity, StockTrade, ModelsError, ActionType
from cfd.models import get_session, db_refresh_trades

D = decimal.Decimal


APPLICATION_NAME = "CFD PROCESS"
version_data = (0, 3, 0)
VERSION_STRING = "%d.%d.%d" % version_data
__version__ = VERSION_STRING

logger = logging.getLogger()


def init_logging(level=None):
    formatter = logging.Formatter('%(levelname)s:\t%(message)s\t[%(name)s]')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    logfile = logging.FileHandler('gencfdprocess.log')
    logfile.setLevel(logging.DEBUG)
    logfile.setFormatter(formatter)
    logger.addHandler(console)
    logger.addHandler(logfile)
    
    if level:
        logger.setLevel(level)
        logger.info("Starting %s v%s: setting log level to %d", APPLICATION_NAME, VERSION_STRING, level)
    else:
        logger.info("Starting " + APPLICATION_NAME + " " + VERSION_STRING)


def get_comm_for_position(session, ref_date, broker_ref):
    q = session.query(RawData).filter(RawData.category==RawData.CAT_COMM, 
                                      RawData.ref_date<=ref_date,
                                      RawData.description.like('%'+broker_ref+'%')
                                      ).order_by(RawData.import_id, RawData.ref_date)
    return q.all()


def get_position_activities(session, pos, is_first_only=False):
    q = session.query(StockActivity).filter(StockActivity.position_id==pos.id
                                      ).order_by(StockActivity.id)
    if is_first_only:
        return q.first()

    return q.all()


def new_position(session, raw):
    # find opening commission transaction
    logger.debug("Creating new position for %s", raw.broker_ref)
    q = session.query(RawData).filter(RawData.category==RawData.CAT_RISK, 
                                       RawData.ref_date<=raw.ref_date,
                                       RawData.description.like('%'+raw.broker_ref+'%'))
    other_fees = q.all()
    total_other_fees = D(0)
    if len(other_fees):
        for fee in other_fees:
            total_other_fees += fee.amount
        logger.debug("Total of %d other fees for %s: %s", 
                     len(other_fees), raw.broker_ref, total_other_fees)
    comm = get_comm_for_position(session, raw.ref_date, raw.broker_ref)
    if len(comm) == 2:
        logger.debug("%d commissions found for %s", len(comm), raw.broker_ref)
    else:
        logger.warn("FOUND %d COMMISSIONS FOR %s (%s)", len(comm), raw.broker_ref, raw.description)

    pos = StockPosition(raw.description, raw.description, raw.ref_date)
    pos.broker_ref = raw.broker_ref
    pos.num_opens += 1
    pos.num_closes += 1
    pos.entry_quantity += raw.size
    pos.fees += total_other_fees

    c_open = None
    c_close = None

    if len(comm) > 0:
        c_open = comm[0]
        pos.brokerage += c_open.amount
        logger.debug("Using commission %d for open of %s", c_open.id, raw.broker_ref)
        if len(comm) > 1:
            c_close = comm[1]
            pos.brokerage += c_close.amount
            logger.debug("Using commission %d for close of %s", c_close.id, raw.broker_ref)      
            if c_close.ref_date != raw.ref_date:
                logger.error("CLOSING COMMISSION DATE MISMATCH on %d for close of %s", 
                             c_close.id, raw.broker_ref)
        # TODO: Handle/Check for more than 2 commissions?  Check dates??
        # Closing commission should be on same date as closing trade.

    a_open = StockActivity(ActionType.OPEN, raw=raw, comm=c_open)
    a_open.fees = total_other_fees
    a_close = StockActivity(ActionType.CLOSE, raw=raw, comm=c_close)
    trade = StockTrade(a_open, a_close, raw)

    session.add(pos)
    session.add(trade)
    session.add(a_open)
    session.add(a_close)
    session.commit()

    if c_open:
        c_open.position_id = pos.id
        c_open.activity_id = a_open.id
    if c_close:
        c_close.position_id = pos.id
        c_close.activity_id = a_close.id
    if len(other_fees):
        for fee in other_fees:
            fee.position_id = pos.id
            fee.activity_id = a_open.id

    trade.position_id = pos.id
    a_open.position_id = pos.id
    a_close.position_id = pos.id
    a_open.trade_id = trade.id
    a_close.trade_id = trade.id
    

def add_to_position(session, raw, pos):
    # find opening commission transaction
    logger.debug("Adding raw trade %d to position %d for  %s", raw.id, pos.id, raw.broker_ref)
    comm = get_comm_for_position(session, raw.ref_date, raw.broker_ref)
    if len(comm) > 1:
        logger.info("%d commissions found for multi-tranche %s", len(comm), raw.broker_ref)
    pos.num_closes += 1
    pos.entry_quantity += raw.size

    c_open = None
    c_close = None

    if len(comm) > 0:
        c_close = comm[-1]
        pos.brokerage += c_close.amount
        logger.debug("Using commission %d for ANOTHER close of %s", c_close.id, raw.broker_ref)      
        if c_close.ref_date != raw.ref_date:
            logger.error("CLOSING COMMISSION DATE MISMATCH on %d for close of %s", 
                         c_close.id, raw.broker_ref)
        # TODO: Handle/Check for more than 2 commissions?  Check dates??
        # Closing commission should be on same date as closing trade.

    a_close = StockActivity(ActionType.CLOSE, raw=raw, comm=c_close)

    # Update quantity in first open activity.
    # The underlying logic only works if there is only one open, but multiple closes.
    a_open = get_position_activities(session, pos, True)
    a_open.quantity += raw.size

    trade = StockTrade(a_open, a_close, raw)    

    session.add(trade)
    session.add(a_close)
    session.commit()

    if c_close:
        c_close.position_id = pos.id
        c_close.activity_id = a_close.id
    a_close.position_id = pos.id
    a_close.trade_id = trade.id


def cfd_process():
    session = get_session()

    for i in session.query(RawData).filter(
                                    sqlalchemy.or_(RawData.category==RawData.CAT_TRADE,
                                                   RawData.category==RawData.CAT_INDEX)
                                    ).order_by(RawData.import_id, RawData.ref_date):
        # OK, so this will essentially be a closing trade.  Or part of one.
        # Check if there is already an open position with this broker ref
        #     TODO
        #     If so, Check if there's more than one...if so things could be messy...
        #     Is there any way to work out exact quantities in this case???
        #     I'm going to assume there's no legging into trades for now (and I don't think there is?)
        #     There's no way to defnitively process if there is (without cross referencing
        #     other data files).  For now can just assume first commission is on trade open,
        #     and all subsequent commissions are as part of closing a tranche.
        q = session.query(StockPosition).filter(StockPosition.broker_ref==i.broker_ref)
        pos = q.first()
        if pos is None:
            # Create new Position, and open/close activities
            pos = new_position(session, i)
        else:
            # update quantities/activities in the existing position
            add_to_position(session, i, pos)
    session.commit()


if __name__ ==  "__main__":
    loglevel = logging.DEBUG
    init_logging(loglevel)
    logger.info("CFD PROCESS: " + str(datetime.datetime.now()))
    db_refresh_trades()
    cfd_process()

