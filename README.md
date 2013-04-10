trade-herder
============

Some python scripts I was driven to write after cracking the shits with
Excel while preparing a profit-loss summary of option trades for my tax
return.  Got to the point where I was like, "fuck spreadsheets, I'll write
some scripts to do this shit instead".  And here they are, in all their
hackily quick and dirty goodness.

The initial problem these scripts were written to solve was this:

The broker's trading platform provides an export of historical trade
transactions (buys, sells, expiry, exercise) as a csv file.  I want to know
the profit/loss of each "trade" (i.e. match up the buys and sells,
calculate profit/loss).  Apart from the tedious and repetitive point and
clickyness of doing this in a spreadsheet, I was getting frustrated by
Excel's remarkable ability to find unique and unexpected ways to mangle the
data each step of the way.  So I decided to write scripts (and use unix
tools) to do as much processing of the data as possible (as automatically
as possible) without going anywhere near a spreadsheet until the very end
(and then only for formatting).

