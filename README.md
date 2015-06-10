**BOMtools**
=========
This is a set of python scripts for managing parts in a kicad schematic 
(other schematic capture packages may be supported in the future)

*Introduction*

The project consists of a BOM manager script (bommgr.py) written in
python 3 and a merger script for kicad xml files written in python 2.7.

The merger script looks for a PartNumber field in the kicad xml file,
and opens the sqlite database to look up other relevant fields based
on the part number. It then generates a .csv file with all of the
relevant fields included.

Part numbers are expected to be in 6-3 format (e.g. 800000-101). You use
the manager script to add new part numbers like this:

bommgr.py add "XSTR,NPN,GP,50V"

This will automatically assign a new part number and spit it out
when it has been added to the database.

The only requirement is the title/description, but there are other
options available to customize the new part number in the database.

You can override the part number and assign a custom part number with
the --specpn option. This is good for inputting tabulated part numbers
(i.e. a series of connectors).

You can specify a manufacturer with the --manufacturer option and a
manufacturer's part number with the --mpn option. For new parts entered
without these options, the default values will be used:

"Open Market" for the manufacturer
"N/A" for the manufacturer's part number

Other command line options are available to get the next part number to
be assigned, modify a title, list all the parts or manufacturers, query
by part number or manufacturer.

Once all your parts are in the database, you can run the merge program
by calling it from kicad. 

The output will look like this when imported into your spreadsheet:

![ProjectPicture](Screenshot.png)


*Installation*

The following python3 modules are required for bommgr.py:

sqlite3
argparse
configparser

The following python2.7 modules are required for bommerge.py:

kicad_netlist_reader
csv
sqlite3
ArgParse
ConfigParser

When running the parts manager or the kicad merger, the database will
need to be created. A separate script, gendb.py in the bommgr
directory does this.

*Notice*

This is currently alpha software. There will most likely be bugs. This is not feature complete. There
are several important commands missing. There is no facility to delete part numbers once they have been
assigned, and there probably never will be as that is dangerous. 

Use at your own risk.

Feedback is appreciated.





