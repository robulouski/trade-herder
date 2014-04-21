trade-herder
============

Some Python scripts for processing trading data in various ways, mostly
in relation to producing profit-loss reports.  

Mostly written so as to avoid using Excel.  Because Excel can be annoying
(and the alternatives are usually even worse).  Got to the point where I
was like, "screw spreadsheets, I'll write some scripts to do this stuff
instead!"  And here they are, in all their hacky quick and dirty goodness.

The initial problem these scripts were written to solve was this:

The option broker's trading platform provides an export of historical trade
transactions (buys, sells, expiry, exercise) as a csv file.  I want to know
the profit/loss of each "trade" (i.e. match up the buys and sells,
calculate profit/loss).  Apart from the tedious and repetitive point and
clickyness of doing this in a spreadsheet, I was getting frustrated by
Excel's remarkable ability to find unique and unexpected ways to mangle the
data each step of the way.  So I decided to write scripts (and use Unix
tools) to do as much processing of the data as possible (as automatically
as possible) without going anywhere near a spreadsheet until the very end
(and then only for formatting/styling).  

(It goes without saying these scripts come with no warranty, are not fit
for any purpose whatsoever, and using them may cause a rift in the
space–time continuum, unleashing hordes of Lovecraftian hell-beasts
hell-bent on the destruction of humanity.  Consider yourself warned.  They
are mostly an exercise in Python programming and SQLAlchemy.  They do what
I need them to do, and may eventually evolve into a more substantial piece
of trading software, but at this stage nothing here is even close to
production quality, or any but the loosest definition of "quality".  For
various reasons I am deliberately avoiding any mention of the brokers and
trading platform -- and their reporting deficiencies -- that motivated
these scripts.)


The Options Scripts
-------------------

The csv data file from the broker ("activity.csv") has the following fields:

	Symbol, Description, Action, Quantity, Price, Commission, Reg Fees, Date, TransactionID, Order Number, Transaction Type ID, Total Cost

The "Date" field is actually a date-time field in US format: MM/DD/YYYY hh:mm:ss AM/PM

No matter what I tried, and despite much dicking around with the Text
Import Wizard, I could not get Excel to parse that properly and reformat it
for my locale (Australia) as DD/MM/YYYY hh:mm:ss AM/PM.

This was my initial motivation for giving up on Excel and writing scripts
instead.  Hence the first script, designed to fix this, csv_us2au_date.py:

	./csv_us2au_date.py activity.csv activity_datefixed.csv 7

The broker data is in reverse chronological order.  The scripts assume it's
in chronological order, so needs to be reversed:

	tac activity_datefixed.csv > activity_datefixed_rev.csv

So now we have sane input data.  

First we create a database (sqlite for now):

	./models.py

Then import our sanitised data file:

	./import_activity.py activity_datefixed_rev.csv 

Now we can analyse the data and get some profit/loss calculations going:

	./gen_trades.py 

Finally, the money shot (so to speak).  Generate output csv files with
profit/loss calculations for each trade:

	./export_trades.py ProfitLoss

This will generate two output files, ProfitLoss_raw_events.csv and
ProfitLoss_format_events.csv.  They both present the same data in slightly
different ways.  Both files are suitable for loading in a spreadsheet for
final tweaking.


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

