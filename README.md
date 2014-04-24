trade-herder
============

Some Python scripts for processing trading data in various ways, mostly
in relation to producing profit-loss reports.  

Mostly written so as to avoid using Excel.  Because Excel can be annoying
(and the alternatives are usually even worse).  Got to the point where I
was like, "screw spreadsheets, I'll write some scripts to do this stuff
instead!"  And here they are, in all their hacky quick and dirty goodness.

Apart from the tedious and repetitive point and clickyness of doing this in
a spreadsheet, I was getting frustrated by Excel's remarkable ability to
find unique and unexpected ways to mangle the data each step of the way.
So I decided to write scripts (and use Unix tools) to do as much processing
of the data as possible (as automatically as possible) without going
anywhere near a spreadsheet until the very end (and then only for
formatting/styling).

These scripts were motivated by a desire to automate the process of
generating profit-loss reports, given (possibly inadequate) raw trade data
from a (possibly inadequate) broker's online trading platform.  While I've
often pondered how nice it would be to have some kind of software to do
this in a "generic" way given disparate (and possibly inadequate) input
file formats, for now these scripts are tailored to the specific input data
of specific brokers.

(It goes without saying these scripts come with no warranty, are not fit
for any purpose whatsoever, and most certainly do not represent financial
advice, or any advice whatsoever, nor are they endorsed by any individual
or corporate entity, not even me.  They are mostly just an exercise in
Python programming and SQLAlchemy.  They do what I need them to do, and may
eventually evolve into a more substantial piece of trading software, but at
this stage nothing here is even close to production quality, or any but the
loosest definition of "quality".  For various reasons I am deliberately
avoiding any mention of the brokers and trading platforms -- and their
reporting deficiencies -- that motivated these scripts.)


The Options Scripts
-------------------

Assumes CSV input file of historical option trade transactions (buys,
sells, expiry, exercise).  Goal is to get the profit/loss of each "trade"
(i.e. match up the buys and sells, calculate profit/loss).

The CSV input data file ("activity.csv") has the following fields:

	Symbol, Description, Action, Quantity, Price, Commission, Reg Fees, Date, TransactionID, Order Number, Transaction Type ID, Total Cost

The "Date" field is actually a date-time field in US format: MM/DD/YYYY hh:mm:ss AM/PM

No matter what I tried, and despite much dicking around with the Text
Import Wizard, I could not get Excel to parse that properly and reformat it
for my locale (Australia) as DD/MM/YYYY hh:mm:ss AM/PM.

This was my initial motivation for giving up on Excel and writing scripts
instead.  Hence the first script, designed to fix this, csv_us2au_date.py:

	./csv_us2au_date.py activity.csv activity_datefixed.csv 7

The data processing scripts assume the input data is in chronological
order.  So if the raw input file is in reverse chronological order, it will
need to be reversed:

	tac activity_datefixed.csv > activity_datefixed_rev.csv

So now we should have sane input data.  

First we create a database (sqlite for now):

	./eto-create-db.py

Then import our sanitised data file:

	./eto-import.py activity_datefixed_rev.csv 

Now we can analyse the data and get some profit/loss calculations going:

	./eto-process.py 

Finally, the money shot (so to speak).  Generate output csv files with
profit/loss calculations for each trade:

	./eto-csv-export.py ProfitLoss

This will generate two output files, ProfitLoss_raw_events.csv and
ProfitLoss_format_events.csv.  They both present the same data in slightly
different ways.  Both files are suitable for loading in a spreadsheet for
final tweaking/error-checking.



The Stock/CFD Scripts
---------------------

The CFD scripts are designed to deal with a far more pain in the ass input
file than the options scripts.  Just a list of raw transactions.  Fields
are:

    TYPE, DATE, REF, DESC, PERIOD, OPEN, CURRENCY, SIZE, CLOSE, AMOUNT


Create database:

    ./cfd-create-db.py 


Load input file into database:

    ./cfd-import.py datadir/input.csv 


Pre-process/Categorise raw transaction data:

    ./cfd-categorise.py 


Simple report using just the raw transaction data.  Summarises totals.

    ./cfd-report.py


Process the raw data, generate data more suitable for reporting:

    ./cfd-process.py


Produce report.  Will use entire dataset by default.  Specify command line
args to limit date ranges (run with --help for details).

    ./cfd-csv-export.py outdir



Author
------

Robert Iwancz  
www.voidynullness.net  
``@robulouski``  

