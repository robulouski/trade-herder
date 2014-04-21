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
# models.py: Stock/CFD database module
#

from __future__ import division, unicode_literals, print_function
import sys
import logging
import datetime
import decimal
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref

from cfd.config import Config

g_config = Config()

logger = logging.getLogger(__name__)


engine = sqlalchemy.create_engine(
                    g_config.db_connect_str,
                    echo=False)
Base = declarative_base()
Session = sqlalchemy.orm.sessionmaker(bind=engine)


def get_session():
    return Session()


def db_refresh_trades():
    ''' Delete and recreate generated tables for new processing run.'''

    t = Base.metadata.tables['stock_position']
    t.drop(engine, True)
    t.create(engine)
    t = Base.metadata.tables['stock_activity']
    t.drop(engine, True)
    t.create(engine)
    t = Base.metadata.tables['stock_trade']
    t.drop(engine, True)
    t.create(engine)


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

#=== ENUMS ===

class ActionType(object):
    OPEN  		= 1
    CLOSE    		= 2
    BUY_TO_OPEN 	= 3
    SELL_TO_CLOSE 	= 4
    EXERCISE            = 5
    NAMES = ['???', 'OPEN', 'CLOSE', 'BUY TO OPEN', 'SELL TO CLOSE', 'EXERCISE']


class TradeStatus(object):
    OPEN    = 1
    CLOSED  = 2
    HOLD    = 3
    NAMES = ['???', 'OPEN', 'CLOSED', 'HOLD']


###############################################################################


#=== Data Tables ===

#
#  "RawData"  (stock_raw)
#
class RawData(Base):
    ''' Table for storing raw data imported from transaction data file.'''
    __tablename__ = 'stock_raw'

    CAT_UNKNOWN = 0    
    # Trades
    CAT_TRADE = 1   
    # Fees (cash transactions)
    # (Although there are fees like brokerage which belong to trades,
    # as opposed to fees like exchange data which are general, and more like 
    # cash transactions...hmmm
    CAT_COMM = 2
    CAT_RISK = 3
    CAT_XFEE = 4
    # Interest (cash transactions)
    CAT_INTEREST = 5
    # other cash transactions 
    CAT_DIVIDEND = 6
    CAT_TRANSFER = 7
    # index trades
    CAT_INDEX = 8


    id 			= Column(Integer, primary_key=True)
    import_id 		= Column(Integer, nullable = False)  # order imported from input file
    type 		= Column(String(255), nullable = False)  
    ref_date 		= Column(sqlalchemy.Date, nullable = False)  
    broker_ref  	= Column(String(255), nullable = False)  
    description  	= Column(String(255), nullable = False)  
    period      	= Column(String(255), nullable = False)  
    open 		= Column(CurrencyType, nullable = False)
    currency    	= Column(String(255), nullable = False)  
    size 		= Column(Integer, nullable = False)
    close 		= Column(CurrencyType, nullable = False)
    amount 		= Column(CurrencyType, nullable = False)
    # Remaining fields are for scripting use, not imported from data.
    tags         	= Column(String(255), nullable = False)  
    category 		= Column(Integer, nullable = False)
    position_id 	= Column(Integer, ForeignKey('stock_position.id'), nullable = True)
    activity_id	        = Column(Integer, ForeignKey('stock_activity.id'), nullable = True)

    def __init__(self, row, importid=0):
        self.init_from_list(row, importid)

    # Order of fields in raw ig input file is:
    #
    #   TYPE DATE REF DESC PERIOD OPEN CURRENCY SIZE CLOSE AMOUNT
    #
    def init_from_list(self, row, importid=0):
        self.import_id = importid
        self.type = row[0]
        self.ref_date = datetime.datetime.strptime(row[1], '%d/%m/%y').date()
        self.broker_ref = row[2]
        self.description = row[3]
        self.period = row[4]
        self.open = decimal.Decimal(row[5])
        self.currency = row[6]
        self.size = row[7]
        self.close = decimal.Decimal(row[8])
        self.amount = decimal.Decimal(row[9])
        self.tags = ""
        self.category = self.CAT_UNKNOWN 

        # Adjust price only for entries before December 2008.
        # Add tag to those entries that were adjusted.
        if self.type == 'DEAL' and self.ref_date < datetime.date(2008, 12, 1):
            if self.open > 0:
                self.open = self.open / 100
            if self.close > 0:
                self.close = self.close / 100
            self.tags += "priceadjust|"


def db_create():
    session = Session()
    Base.metadata.drop_all(engine) 
    Base.metadata.create_all(engine) 
#    db_populate_ref(session)



#
#  Different terminology to the OX scripts.  
#  "Position" will refer to a collection of one or more related trades.
#  Trade represents a parcel of security/derivative/instruments that has been 
#  bought then sold (closed).
#  Activity represents a trade transaction, (buy, sell, etc)
#  So Trades consist of multiple Activities, and Positions consist of one or more Trades.
#  Position --> Trade --> Activity
#
#  There is some deliberate de-normalisation and data duplication to make reporting easier
#  (for now)
#

class StockPosition(Base):
    __tablename__ = 'stock_position'

    id 			= Column(Integer, primary_key=True)
    symbol 		= Column(String(255), nullable = False)  
    description 	= Column(String(255), nullable = False)  
    open_date 		= Column(sqlalchemy.DateTime, nullable = False)  
    close_date 		= Column(sqlalchemy.DateTime, nullable = True)  
    status_id 		= Column(Integer, nullable = False)
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
    broker_ref 		= Column(String(255), nullable = False)  


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
        self.broker_ref = ""


class StockActivity(Base):
    __tablename__ = 'stock_activity'
    
    id 			= Column(Integer, primary_key=True)
    position_id 	= Column(Integer, ForeignKey('stock_position.id') , nullable = True)  
    # Stop gap for now.  But for situations like 2 tranche open and 1 close, an open 
    # activity will be associated with 2 trades!  (But I can't imagine any situation 
    # where 2 "close" activities would be associated with one trade...maybe option exercise???)
    trade_id 		= Column(Integer, ForeignKey('stock_trade.id'), nullable = True)  
    ref_date 		= Column(sqlalchemy.DateTime, nullable = False)  
    symbol 		= Column(String(255), nullable = False)  
    description 	= Column(String(255), nullable = False)  
    action_id 		= Column(Integer, nullable = False)  # ForeignKey('action_type.id'))  
    quantity 		= Column(CurrencyType, nullable = False)
    price 		= Column(CurrencyType, nullable = False)
    brokerage 		= Column(CurrencyType, nullable = False)
    fees 		= Column(CurrencyType, nullable = False)
    net_total_cost 	= Column(CurrencyType, nullable = False)
    gross_total_cost 	= Column(CurrencyType, nullable = False)
    broker_ref 		= Column(String(255), nullable = False)  

    def __init__(self, action, raw=None, comm=None, sym="", desc="", dt=None):
        self.symbol = sym
        self.description = desc
        self.ref_date = dt
        self.action_id = action
        self.quantity = 0
        self.price = decimal.Decimal(0)
        self.brokerage = decimal.Decimal(0)
        self.fees = decimal.Decimal(0)
        self.net_total_cost = decimal.Decimal(0)
        self.gross_total_cost = decimal.Decimal(0)
        self.broker_ref = ""

        self.symbol = raw.description
        self.description = raw.description
        self.broker_ref = raw.broker_ref
        self.quantity = raw.size
        # If closed same day as open, there may not be a commission
        self.ref_date = raw.ref_date 
        if self.action_id == ActionType.OPEN:
            self.price = raw.open
            # If comm is given, use data for open, otherwise assume 
            # it was open on same day as closed.
            if comm:
                self.ref_date = comm.ref_date
        elif self.action_id == ActionType.CLOSE:
            self.price = raw.close
        else:
            logger.error("INVALID ACTION TYPE FOR %s", raw.broker_ref)

        if comm:
            self.brokerage = comm.amount
            if self.brokerage < 0:
                self.brokerage *= -1


# Exit Date	Entry Date	Company	
# Buy Price	Qty	Total Position Entry	Entry Commission	Other Commission	
# Sell Price	Total Position Exit	Exit Commission	
# Gross Return	Net Return	Gross % Return	NET % Return
class StockTrade(Base):
    __tablename__ = 'stock_trade'
    
    id 			= Column(Integer, primary_key=True)
    position_id 	= Column(Integer, ForeignKey('stock_position.id'))  
    import_id 		= Column(Integer, nullable = False)  # order imported from input file
    entry_date 		= Column(sqlalchemy.DateTime, nullable = False)  
    exit_date 		= Column(sqlalchemy.DateTime, nullable = False)  
    symbol 		= Column(String(255), nullable = False)  
    description 	= Column(String(255), nullable = False)  
    quantity 		= Column(CurrencyType, nullable = False)
    entry_price		= Column(CurrencyType, nullable = False)
    exit_price 		= Column(CurrencyType, nullable = False)
    entry_brokerage	= Column(CurrencyType, nullable = False)
    exit_brokerage	= Column(CurrencyType, nullable = False)
    fees 		= Column(CurrencyType, nullable = False)
    #net_total_cost 	= Column(CurrencyType, nullable = False)
    gross_total_imp	= Column(CurrencyType, nullable = False) # from imported data
    broker_ref 		= Column(String(255), nullable = False)  
    category 		= Column(Integer, nullable = False)

    def __init__(self, entry_action, exit_action, raw):
        self.quantity = 0
        self.entry_price = 0
        self.exit_price = 0
        self.brokerage = 0
        self.fees = 0
        #self.net_total_cost = 0
        #self.gross_total_cost = 0
        self.broker_ref = ""

        self.symbol = raw.description
        self.description = raw.description
        self.broker_ref = raw.broker_ref
        self.category = raw.category
        self.quantity = raw.size
        assert self.quantity == exit_action.quantity
        self.import_id = raw.import_id
        self.entry_date = entry_action.ref_date 
        self.exit_date = exit_action.ref_date 
        self.entry_price = entry_action.price
        self.exit_price = exit_action.price
        self.entry_brokerage = entry_action.brokerage
        self.exit_brokerage = exit_action.brokerage
        self.fees = entry_action.fees + exit_action.fees
        self.gross_total_imp = raw.amount
        if self.gross_total_imp != self.get_gross_total():
            logger.error("GROSS TOTAL DOES NOT MATCH FOR %s", raw.broker_ref)
            total =  self.get_gross_total()
            logger.error("value is %s [%s]", str(total), str(type(total)))

#        assert self.gross_total_imp == self.get_gross_total()

    def get_entry_total(self):
        if self.category == RawData.CAT_INDEX:
            return (self.entry_price * self.quantity * 5)
        else:
            return (self.entry_price * self.quantity)

    def get_exit_total(self):
        if self.category == RawData.CAT_INDEX:
            return (self.exit_price * self.quantity * 5)
        else:
            return (self.exit_price * self.quantity)

    def get_gross_total(self):
        return self.get_exit_total() - self.get_entry_total()
