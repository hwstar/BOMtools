#!/usr/bin/env/python
from __future__ import print_function
__author__ = 'srodgers'

#
# Example python script to generate a BOM from a KiCad generic netlist
#
# Example: Sorted and Grouped CSV BOM
#
"""
    @package
    Generate a csv BOM list from Kicad xml file and sqlite3 parts database.
    Components are sorted by ref and grouped by value
    If PartNumber field is present, pull in the description, Manufacturer, and Manufacturer Part Number
    Fields are (if present in Kicad and Parts Database)
    Item, Part Number, Qty, Reference(s), Description, Value, Manufacturer,Manufacturer Part Number
"""



# Import the KiCad python helper, csv formatter, and sqlite3 modules
import string
import kicad_netlist_reader
import csv
import sys
import sqlite3

def myEqu(self, other):
    """myEqu is a more advanced equivalence function for components which is
    used by component grouping. Normal operation is to group components based
    on their value and footprint.

    In this example of a custom equivalency operator we compare the
    value, the part name and the footprint.

    """
    result = True
    if self.getValue() != other.getValue():
        result = False
    elif self.getPartName() != other.getPartName():
        result = False
    elif self.getFootprint() != other.getFootprint():
        result = False

    return result


# override csv.writer's writerow() to support encoding conversion (initial encoding is utf8):
def writerow( acsvwriter, columns ):
    utf8row = []
    for col in columns:
        utf8row.append( str(col) )  # currently, no change
    acsvwriter.writerow( utf8row )


# Fetch description from parts database if it exists, otherwise return empty string

def getdescr(pn):
    if len(pn) == 0 :
        return pn
    cur.execute('SELECT Description FROM pndesc WHERE PartNumber=?', [pn])
    res = cur.fetchone()

    if(res is not None):
        return res[0].decode('utf-8')
    else:
        return ''

# Fetch manufacturer's info from parts database if it exists
# If the part does not exist, then return 'Open Market' as the source is not controlled.

def getmfginfo(pn):
    res = {}
    res['MFG'] = 'Open Market'
    res['MPN'] = 'N/A'
    if len(pn) == 0 :
        return res
    cur.execute('SELECT Manufacturer,MPN FROM pnmpn WHERE PartNumber=?', [pn])
    info = cur.fetchone()
    if info is not None :
        res['MPN'] = info[1]
        mfgid = info[0]
        cur.execute('SELECT MFGName FROM mlist WHERE MFGId=?', [mfgid])
        minfo = cur.fetchone()
        if minfo is not None:
            res['MFG'] = minfo[0]
    return res

# Group consecutive array elements into an array of arrays

def group_consecutives(vals, step=1):
    """Return list of consecutive lists of numbers from vals (number list)."""
    run = []
    result = [run]
    expect = None
    for v in vals:
        if (v == expect) or (expect is None):
            run.append(v)
        else:
            run = [v]
            result.append(run)
        expect = v + step
    return result

# Sort and pack consecutive reference designators into ranges

def pack_ref_designators(inplist):

    # Strip off the prefix
    i = 0
    prefix = ''
    nlist = []
    for item in inplist:
        for i in range(len(item)):
            if item[i] in '0123456789':
                prefix = item[0:i]
                nlist.append(int(item[i:]))
                break

    # Sort the numbers
    slist = group_consecutives(sorted(nlist))
    outlist = []
    for item in slist:
        if len(item) > 2: # If 3 more more consecutive values output a range Xyy-Xzz
            outlist.append(prefix + str(item[0]) + '-' + prefix + str(item[-1]))
        else:
            for i,val in enumerate(item):
                outlist.append(prefix+str(val))

    return outlist




# Override the component equivalence operator - it is important to do this
# before loading the netlist, otherwise all components will have the original
# equivalency operator.
kicad_netlist_reader.comp.__eq__ = myEqu

if len(sys.argv) != 4:
    print("Usage ", __file__, "<parts database> <generic_netlist.xml> <output.csv>", file=sys.stderr)
    sys.exit(1)

# Define order of command line arguments
dbpath = sys.argv[1]
infile = sys.argv[2]
outfile = sys.argv[3]

# Set up the dabase connection
conn = sqlite3.connect(dbpath)
cur = conn.cursor()

# Generate an instance of a generic netlist, and load the netlist tree from
# the command line option. If the file doesn't exist, execution will stop
net = kicad_netlist_reader.netlist(infile)

# Open a file to write to, if the file cannot be opened output to stdout
# instead
try:
    f = open(outfile, 'w')
except IOError:
    e = "Can't open output file for writing: " + outfile
    print( __file__, ":", e, sys.stderr )
    f = sys.stdout

# subset the components to those wanted in the BOM, controlled
# by <configure> block in kicad_netlist_reader.py
components = net.getInterestingComponents()

compfields = net.gatherComponentFieldUnion(components)
partfields = net.gatherLibPartFieldUnion()

# remove Reference, Value, Datasheet, and Footprint, they will come from 'columns' below
partfields -= set( ['Reference', 'Value', 'Datasheet', 'Footprint'] )

columnset = compfields | partfields     # union

# prepend an initial 'hard coded' list and put the enchillada into list 'columns'
columns = ['Item', 'Part Number', 'Qty', 'Reference(s)', 'Description', 'Value on Schematic', 'Manufacturer', 'Manufacturer Part Number']

# Create a new csv writer object to use as the output formatter
out = csv.writer( f, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_MINIMAL )


row = []

writerow( out, [] )                        # blank line
writerow( out, [] )                        # blank line
writerow( out, [] )                        # blank line
writerow( out, [] )                        # blank line
writerow( out, columns )                   # column header


# Get all of the components in groups of matching parts + values
# (see kicad_netlist_reader.py)
grouped = net.groupComponents(components)


# Output component information organized by group, aka as collated:
item = 0
for group in grouped:
    del row[:]
    refs = ""

    # Add the reference of every component in the group and keep a reference
    # to the component so that the other data can be filled in once per group


    grplist = []

    for component in group:
        if len(refs) > 0:
            refs += ", "
        grplist.append(component.getRef())
        refs += component.getRef()
        c = component

    plist = pack_ref_designators(grplist)
    refs = ""
    for i, rgroup in enumerate(plist):
        if(i):
            refs += ','
        refs += rgroup

    # Fill in the component groups common data

    item += 1
    row.append( item ) # Item number
    pn = c.getField('PartNumber', False)
    row.append(pn) # Part number
    row.append( len(group) ) # Quantity
    row.append(refs) # Reference Designators
    row.append(getdescr(pn))   # Descr
    row.append( c.getValue() )
    mfginfo = getmfginfo(pn)
    row.append(mfginfo['MFG'])
    row.append(mfginfo['MPN'])
    writerow( out, row  )

f.close()

