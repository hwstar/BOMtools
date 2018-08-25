#!/usr/bin/python3

"""
    This file is part of BOMtools.

    BOMtools is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    BOMTools is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with BOMTools.  If not, see <http://www.gnu.org/licenses/>.

"""

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
import kicad_netlist_reader
import csv
import sys
import os
import sqlite3
import configparser
import argparse

defaultConfigLocations = ['/etc/bommgr/bommgr.conf','~/.bommgr/bommgr.conf','bommgr.conf']
defaultDb = '/etc/bommgr/parts.db'
defaultMPN = 'N/A'
unk = 'Unknown'
unkPn = 'XXXXXX-XXX'


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
    global unk
    if len(pn) == 0 :
        return pn
    cur.execute('SELECT Description FROM pndesc WHERE PartNumber=?', [pn])
    res = cur.fetchone()

    if(res is not None):
        return res[0]
    else:
        return unk


# Get manufacturer by ID

def getmfgr(mid):
    global cur
    cur.execute('SELECT MFGName FROM mlist WHERE MFGId=?', [mid])
    minfo = cur.fetchone()
    if minfo is not None:
        return minfo[0]
    else:
        return None

# Fetch manufacturer's info from parts database if it exists
# Return an array of dictionaries containing the matched manufacturers info
# If the part does not exist, then return default manufacturer as the source is not controlled.

def getmfginfo(pn):
    global cur, defaultMfgr, defaultMPN

    res = []
    res.append({'MFG': defaultMfgr, 'MPN': defaultMPN})

    if len(pn) == 0 :
        return res

    cur.execute('SELECT Manufacturer,MPN FROM pnmpn WHERE PartNumber=?', [pn])
    info = cur.fetchall()

    if len(info) :
        res = []
        for item in info:
            d = {}
            d['MPN'] = item[1]
            mfgid = item[0]
            minfo = getmfgr(mfgid)
            if minfo is not None:
                d['MFG'] = minfo
            else:
                d['MFG'] = defaultMfgr
            res.append(d)
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

# Add item to grouped_items

def add_item(grouped_items, part_number, reference, value):
    if(len(grouped_items) > 0):
        for item in grouped_items:
            if item['Part Number'] == part_number:
                # Found match to existing item
                item['Reference(s)'].append(reference)
                item['Value On Schematic'] = value
                return
    # New item in existing list, or
    # First item
    grouped_items.append({'Part Number': part_number, 'Reference(s)': [reference], 'Value On Schematic': value})



# Override the component equivalence operator - it is important to do this
# before loading the netlist, otherwise all components will have the original
# equivalency operator.
kicad_netlist_reader.comp.__eq__ = myEqu

# Customize default configurations to user's home directory

for i in range(0, len(defaultConfigLocations)):
    defaultConfigLocations[i] = os.path.expanduser(defaultConfigLocations[i])


#command line parser setup
parser = argparse.ArgumentParser(description = 'BOM merger for kicad', prog = 'bommerge.py')
parser.add_argument('infile',help='kicad xml input file')
parser.add_argument('outfile',help='csv output file')
parser.add_argument('--specdb',help='specify database file to use')
parser.add_argument('--config',help='specify config file to use')
parser.add_argument('--const',help='specify BOM construction keyword')
parser.add_argument('--usecwd',action='store_true', help='Use current working directory for local config file instead of path to input file')

# parse the args and die on error
args = parser.parse_args()

# get the path to the directory with the project files
[ph,pt] = os.path.split(args.infile)



if(args.config is not None):
    configLocation = os.path.expanduser(args.config)
else:
    # If --usecwd is not specified,
    # add path for input file to local config file.
    # Kicad passes in full paths from a different working dir.
    # and we need to see if there is a
    # local config file to read.
    if args.usecwd is False:
        defaultConfigLocations[2] = ph + os.path.sep + defaultConfigLocations[2]
    configLocation = defaultConfigLocations

# Attempt to read the config file

Config = configparser.ConfigParser()
Config.read(configLocation)
try:
    configdict = dict(Config.items("general"))
except configparser.NoSectionError:
    configdict={}

try:
    configdict['merge'] = dict(Config.items("merge"))
except configparser.NoSectionError:
    configdict['merge']={}

# Get list of ignored reference designators if it exists
ignoredrefs = []
if 'ignorerefs' in configdict['merge']:
    for ignoredref in configdict['merge']['ignorerefs'].replace(' ','').split(','):
        ignoredrefs.append(ignoredref)

# If there are part numbers and references to add which are not in the schematic BOM,
# parse these here

addparts = {}
if 'addparts' in configdict['merge']:
    aplist=configdict['merge']['addparts'].replace(' ','').split(';')
    for apitem in aplist:
        [k,v] = apitem.split(':')
        refs = v.split(',')
        addparts[k] = sorted(refs)


# Decide which db path to use

if args.specdb:
    dbpath = os.path.expanduser(args.specdb)
elif'db' in configdict:
    dbpath = os.path.expanduser(configdict['db'])
else:
    dbpath = defaultDb

print('Info: Using database file {}'.format(dbpath))

infile = args.infile
outfile = args.outfile


# Set up the database connection
conn = sqlite3.connect(dbpath)
cur = conn.cursor()


# Get the default manufactuer from the database
defaultMfgr = getmfgr('M0000000')
if(defaultMfgr is None):
    defaultMfgr = 'Default MFG Error'



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
columns = ['Item', 'Part Number', 'Qty', 'Reference(s)', 'Title/Description', 'Value on Schematic', 'Manufacturer', 'Manufacturer Part Number']

# Create a new csv writer object to use as the output formatter
out = csv.writer( f, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_MINIMAL )


row = []
writerow( out, columns )                   # column header
matched_items = []
unmatched_items = []

# Get all of the components in groups of matching parts + values
# (see kicad_netlist_reader.py)

for component in components:
    pn = component.getField('PartNumber')
    ref = component.getRef()
    value = component.getValue()
    constkwds = component.getField('Construction').replace(' ','').split(',')
    if constkwds[0] == '':
        constkwds = []
    footprint= component.getFootprint()

    # Filter out ignored reference designators
    skip = False
    for ignoredref in ignoredrefs:
        if ref.startswith(ignoredref):
            skip = True
    if skip == True:
        continue

    # Filter by construction if --const option was passed on command line
    if args.const is not None and len(constkwds):
        if args.const not in constkwds:
            continue

    if pn == '':
        unmatched_items.append({'Reference(s)': ref,
                                'Value on Schematic': value})
    else:
        add_item(matched_items, pn, ref, value)

if addparts is not {}:
    for part in addparts:
        for ref in addparts[part]:
            add_item(matched_items, part, ref, '')
    # We have to re-sort the entire BOM, as the added parts are appended to the end
    matched_items = sorted(matched_items,key=lambda item: item['Reference(s)'][0])

# Output component information organized by group, aka as collated:
item = 0
for match in matched_items:
    del row[:]

    # Add the reference of every component in the group and keep a reference
    # to the component so that the other data can be filled in once per group

    grplist = match['Reference(s)']

    plist = pack_ref_designators(grplist)
    refs = ''
    for i, rgroup in enumerate(plist):
        if(i):
            refs += ','
        refs += rgroup


    # Fill in the component groups common data

    item += 1
    row.append( item ) # Item number
    pn = match['Part Number']
    row.append(pn) # Part number
    row.append( len(grplist) ) # Quantity
    row.append(refs) # Reference Designators

    # Attempt part number lookup
    # if lookup fails, print ????

    descr = unk
    mfginfo = []
    d = {'MFG':unk, 'MPN':unk}
    mfginfo.append(d)
    if(pn != unkPn):
        # Try to get pn from database
        descr = getdescr(pn)
        if(descr != unk):
            # Try to get manufacturer info from database
            # This can return multiple entries
            mfginfo = getmfginfo(pn)

    row.append(descr)   # Descr
    row.append(match['Value On Schematic'] )
    row.append(mfginfo[0]['MFG'])
    row.append(mfginfo[0]['MPN'])
    writerow( out, row  )

    mfginfo.pop(0)
    if len(mfginfo) == 0:
        continue # Process next item in list
    # If we get here, then there is more than one source for the part number
    for altsrc in mfginfo:
        del row[:]
        row.append( item ) # Repeat Item
        row.append('') # Blank part number
        row.append('') # Blank quantity
        row.append('') # Blank refs
        row.append('') # Blank descr
        row.append('') # Schematic value
        row.append(altsrc['MFG'])
        row.append(altsrc['MPN'])
        writerow(out, row)

# Append unmatched items to end of csv file as Kicad does not print script output

for unmatched_item in  unmatched_items:
    del row[:]
    item += 1
    row.append( item ) # Item number
    row.append(unkPn) # Part number
    row.append('1') # Quantity
    row.append(unmatched_item['Reference(s)']) #Reference
    row.append(unk) # Description
    row.append(unmatched_item['Value on Schematic'])
    writerow(out, row)



f.close()

