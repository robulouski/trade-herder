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
# models.py
# 
# Minimal database for storing/importing/analysing option trade data.
#



from __future__ import division
import sys
import datetime
import decimal
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
#import sqlalchemy.types as types


class Config(object):
    def __init__(self):
        self.db_connect_str = 'sqlite:///oxherded.db'
    
    def is_sqlite(self):
        return True   # for now


g_config = Config()


engine = sqlalchemy.create_engine(
                    g_config.db_connect_str,
                    echo=False)
Base = declarative_base()
Session = sqlalchemy.orm.sessionmaker(bind=engine)


class ModelsError(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg


class DecimalString(sqlalchemy.types.TypeDecorator):
    impl = sqlalchemy.types.String

    def process_bind_param(self, value, dialect):
        return str(value)

    def process_result_value(self, value, dialect):
        return decimal.Decimal(value)

#
# Grrrr.... 
#
if g_config.is_sqlite():
    CurrencyType = DecimalString
else:
    CurrencyType = sqlalchemy.Numeric


###############################################################################
#
#  Database tables that should perhaps be ENUMs instead...
#
###############################################################################

class ActionType(Base):
    __tablename__ = 'action_type'
    
    BUY  		= 1
    SELL    		= 2
    BUY_TO_OPEN 	= 3
    SELL_TO_CLOSE 	= 4
    EXERCISE            = 5
    NAMES = ['???', 'BUY', 'SELL', 'BUY TO OPEN', 'SELL TO CLOSE', 'EXERCISE']

    id    = Column(Integer, primary_key=True)
    label = Column(String(40), nullable = False)  
 
    @staticmethod
    def populate(session):
        C = ActionType
        print "Initialising ", C.__tablename__
        for i in range(1, len(C.NAMES)):
            print "%d = %s" % (i, C.NAMES[i])
            record = C(id=i, label=C.NAMES[i])
            session.add(record)
        session.commit()


class TradeStatus(Base):
    __tablename__ = 'trade_status'
    
    OPEN    = 1
    CLOSED  = 2
    HOLD    = 3
    NAMES = ['???', 'OPEN', 'CLOSED', 'HOLD']

    id    = Column(Integer, primary_key=True)
    label = Column(String(40), nullable = False)  
 
    @staticmethod
    def populate(session):
        C = TradeStatus
        print "Initialising ", C.__tablename__
        for i in range(1, len(C.NAMES)):
            print "%d = %s" % (i, C.NAMES[i])
            record = C(id=i, label=C.NAMES[i])
            session.add(record)
        session.commit()



###############################################################################
#
#  "Canonica"l Reference data tables
#  Stuff average users rarely/shouldn't/won't-want-to modify.
#
###############################################################################

class CloseReason(Base):
    __tablename__ = 'close_reason'
    
    id    = Column(Integer, primary_key=True)
    label = Column(String(80), nullable = False)  
    title = Column(String(255), nullable = False)  

    @staticmethod
    def populate(session):
        data = (
            (1,'STOP LOSS',		'Stock hit entry stop loss.'),
            (2,'GAP STOP',		'Price gapped down through entry stop loss.'),
            (3,'TRAILING STOP LOSS',    'Stock hit trailing stop loss.'),
            (4,'GAP TRAILING STOP',	
               'Price gapped down through trailing stop loss.'),
            (5,'MARKET EXIT',      	'Closed at market.'),
            (6,'MARKET PROFIT',    	'Closed at market, taking profit.'),
            (7,'MARKET LOSS',      	
               'Closed at market for a loss, before hitting stop loss.'),
            (999,'UNKNOWN',             'Just...you know...kinda felt like it...')
            )
        print "Initialising ", __tablename__
        for d in data:
            print "%d = %s" % (d[0], d[1])
            record = CloseReason(id=d[0], label=d[1], title=d[2])
            session.add(record)
        session.commit()


class Exchange(Base):
    __tablename__ = 'exchange'
    
    id = Column(Integer, primary_key=True)
    label = Column(String(40), nullable = False)  
    title = Column(String(255), nullable = False)  

    @staticmethod
    def populate(session):
        data = (
            (1,'ASX','Australian Stock Exchange'),
            (2,'NYSE','New York Stock Exchange'),
            (3,'NASDAQ','NASDAQ Stock Market'),
            (4,'AMEX','American Stock Exchange'),
            (5,'FX','Foreign Exchange'),
            (6,'ETO.US','US Options'),
            (7,'ETO.AU','Australian Options'),
            (8,'OPT.FX','Foreign Exchange Options'),
            (9,'OB','Pink Sheets'),
            (999,'UNKNOWN','UNKNOWN')
            )

        for d in data:
            print "%d = %s" % (d[0], d[1])
            record = Exchange(id=d[0], label=d[1], title=d[2])
            session.add(record)
        session.commit()


class Instrument(Base):
    __tablename__ = 'instrument'
    
    id = Column(Integer, primary_key=True)
    label = Column(String(40), nullable = False)  

    @staticmethod
    def populate(session):
        data = (
            (1,'STOCK'),
            (2,'INDEX'),
            (3,'OPTION'),
            (4,'CFD'),
            (5,'FOREX'),
            (6,'FUTURES'),
            (7,'EMINI'),
            (999,'OTHER')
            )

        for d in data:
            print "%d = %s" % (d[0], d[1])
            record = Instrument(id=d[0], label=d[1])
            session.add(record)
        session.commit()




###########################################################################
#
#  User data tables
#
###########################################################################



#
#  "OptionActivity"
#
# Option trade details.
#

class OptionActivity(Base):
    __tablename__ = 'option_activity'
    
    OPTION_CONTRACT_SIZE = 100

    id 			= Column(Integer, primary_key=True)
    trade_id 		= Column(Integer, ForeignKey('option_trade.id'))  
    ref_date 		= Column(sqlalchemy.DateTime, nullable = False)  
    symbol 		= Column(String(255), nullable = False)  
    description 	= Column(String(255), nullable = False)  
    action_id 		= Column(Integer, ForeignKey('action_type.id'))  
    quantity 		= Column(CurrencyType, nullable = False)
    price 		= Column(CurrencyType, nullable = False)
    brokerage 		= Column(CurrencyType, nullable = False)
    fees 		= Column(CurrencyType, nullable = False)
    net_total_cost 	= Column(CurrencyType, nullable = False)
    gross_total_cost 	= Column(CurrencyType, nullable = False)
    broker_ref 		= Column(String(255), nullable = False)  

    def update_gross(self):
        self.gross_total_cost = self.quantity * OptionActivity.OPTION_CONTRACT_SIZE * self.price

    def is_closing_action(self):
        return (   self.action_id == ActionType.SELL_TO_CLOSE
                or self.action_id == ActionType.EXERCISE)

    def __init__(self, row):
        self.init_from_list(row)

    # Order of fields in raw activity file is:
    # Symbol, Description, Action, Quantity, Price, Commission, Reg Fees, 
    # Date, TransactionID, Order Number, Transaction Type ID, Total Cost
    def init_from_list(self, row):
        self.ref_date = datetime.datetime.strptime(row[7], '%d/%m/%Y %I:%M:%S %p')
        self.symbol = row[0]
        self.description = row[1]
        self.broker_ref = row[9]

        found = False
        for i in range(1, len(ActionType.NAMES)):
            if row[2].upper() == ActionType.NAMES[i]:
                self.action_id = i
                found = True
                break
        if not found:
            raise ModelsError('init_with_list', "Invalid Action Type")
        if self.action_id == ActionType.BUY or self.action_id == ActionType.SELL:
            # This block is redundant -- looks like there will be a Sell To Close
            # in the raw data for option exercise.
            raise ModelsError('init_with_list', 
                                "Ignoring Buy or Sell action!")

#            if 'exercise' not in self.description.lower():
#                raise ModelsError('init_with_list', 
#                                   "Buy or Sell action that doesn't look like an option exercise")
            self.action_id = ActionType.EXERCISE
            self.quantity = decimal.Decimal(row[3]) / OptionActivity.OPTION_CONTRACT_SIZE
            self.price = 0
            self.brokerage = 0
            self.fees = 0
            self.net_total_cost = 0
            # TODO: An equivalent "BUY" (or "EXERCISE"?) activity for the equity will eventually
            # need to be created (in a future equity_trade table, most likely).
        else:
            self.quantity = decimal.Decimal(row[3])
            self.price = decimal.Decimal(row[4])
            self.brokerage = decimal.Decimal(row[5])
            self.fees = decimal.Decimal(row[6])
            net_str = row[11].replace('-', '')
            self.net_total_cost = decimal.Decimal(net_str)
        
        self.update_gross()    
        
        if (self.action_id == ActionType.BUY_TO_OPEN):
            if self.net_total_cost != (self.gross_total_cost + self.brokerage + self.fees):
                print "*** ERROR: Net/Gross calculation error!"
                raise ModelsError('init_with_list', "Net/Gross calculation error!")
        elif (self.action_id == ActionType.SELL_TO_CLOSE):
            if self.net_total_cost != (self.gross_total_cost - self.brokerage - self.fees):
                print "*** ERROR: Net/Gross calculation error!"
                raise ModelsError('init_with_list', "Net/Gross calculation error!")


class OptionTrade(Base):
    __tablename__ = 'option_trade'

    id 			= Column(Integer, primary_key=True)
    symbol 		= Column(String(255), nullable = False)  
    description 	= Column(String(255), nullable = False)  
    open_date 		= Column(sqlalchemy.DateTime, nullable = False)  
    close_date 		= Column(sqlalchemy.DateTime, nullable = True)  
    status_id 		= Column(Integer, ForeignKey('trade_status.id'))  
    entry_quantity 	= Column(CurrencyType, nullable = False)
    exit_quantity 	= Column(CurrencyType, nullable = False)
    entry_price 	= Column(CurrencyType, nullable = False)
    exit_price 		= Column(CurrencyType, nullable = False)
    brokerage 		= Column(CurrencyType, nullable = False)
    fees 		= Column(CurrencyType, nullable = False)
    net_total_cost 	= Column(CurrencyType, nullable = False)
    gross_total_cost 	= Column(CurrencyType, nullable = False)
    num_opens 		= Column(Integer, nullable = False)
    num_closes 		= Column(Integer, nullable = False)

    def __init__(self, sym, desc, dt):
        self.symbol = sym
        self.description = desc
        self.open_date = dt
        self.status_id = TradeStatus.OPEN
        self.entry_quantity = 0
        self.exit_quantity = 0
        self.entry_price = 0
        self.exit_price = 0
        self.brokerage = 0
        self.fees = 0
        self.net_total_cost = 0
        self.gross_total_cost = 0
        self.num_opens = 0
        self.num_closes = 0

def db_populate_ref(session):
    # "Enums"
    ActionType.populate(session)
    TradeStatus.populate(session)


#
# MAIN 
#  - For now, used to create a fresh database from scratch.
#  - Therefore any existing database will, obviously, be blown away.  Don't
#    run this script if that would be undesirable.
#


def db_create():
    session = Session()
    Base.metadata.drop_all(engine) 
    Base.metadata.create_all(engine) 
    db_populate_ref(session)

def db_refresh_trades():
    t = Base.metadata.tables['option_trade']
    t.drop(engine, True)
    t.create(engine)

if __name__ ==  "__main__":
    db_create()
