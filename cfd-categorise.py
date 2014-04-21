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
#  cfd-categorise.py
#

from __future__ import division, unicode_literals, print_function
import os.path
import sys
import re
import sqlalchemy
sys.path.insert(0, '.')

from cfd.models import get_session, RawData, ModelsError


def categorise():
    session = get_session()
    for i in session.query(RawData):
        if i.type == "DEAL":
            if (re.match(r'Australia\s*200', i.description, re.IGNORECASE)):
                i.category = RawData.CAT_INDEX
            else:
                i.category = RawData.CAT_TRADE
        elif i.type == "DEPO" and "BPAY" in i.description.upper():
            i.category = RawData.CAT_TRANSFER
        elif i.type == "WITH" and "eft payment sent" in i.description.lower():
            i.category = RawData.CAT_TRANSFER
        elif (   i.type == "EXCHANGE"  
              or "ASX FEE" in i.description.upper()
              or re.search(r'Transfer from.*to.*at', i.description, re.IGNORECASE)):
            i.category = RawData.CAT_XFEE
        elif (i.type == "WITH" and "LONG INT" in i.description.upper()):
            i.category = RawData.CAT_INTEREST
        elif (i.type == "DEPO" and "SHORT INT" in i.description.upper()):
            i.category = RawData.CAT_INTEREST
        elif (i.type == "WITH" and " COMM " in i.description.upper()):
            i.category = RawData.CAT_COMM
        elif (i.type == "WITH" and " CRPREM " in i.description.upper()):
            i.category = RawData.CAT_RISK
        elif (   i.type == "DIVIDEND"  
              or re.match(r'DVD[A-Z]', i.description, re.IGNORECASE)):
            i.category = RawData.CAT_DIVIDEND
        else:
            i.category = RawData.CAT_UNKNOWN

    session.commit()

if __name__ ==  "__main__":
    categorise()
