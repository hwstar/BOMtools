#!/usr/bin/env python3
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

__author__ = 'srodgers'

import argparse
import configparser
import sys
import os
import csv
import sqlite3

defaultConfigLocations = ['/etc/bommgr/bommgr.conf','~/.bommgr/bommgr.conf','bommgr.conf']
defaultDb = '/etc/bommgr/parts.db'
defaultMPN = 'N/A'
unk = 'Unknown'
unkPn = 'XXXXXX-XXX'

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



# Customize default configurations to user's home directory

for i in range(0, len(defaultConfigLocations)):
    defaultConfigLocations[i] = os.path.expanduser(defaultConfigLocations[i])


#command line parser setup
parser = argparse.ArgumentParser(description = 'BOM merger for eagle', prog = 'bommerge-eagle.py')
parser.add_argument('infile',help='eagle csv input file with part numbers')
parser.add_argument('outfile',help='csv output file')
parser.add_argument('--specdb',help='specify database file to use')
parser.add_argument('--config',help='specify config file to use')
parser.add_argument('--const',help='specify BOM construction keyword')

# parse the args and die on error
args = parser.parse_args()


if(args.config is not None):
    configLocation = os.path.expanduser(args.config)
else:
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


# Get the default manufacturer from the database
defaultMfgr = getmfgr('M0000000')
if(defaultMfgr is None):
    defaultMfgr = 'Default MFG Error'

# Open the eagle .csv file for processing
csv_file = open(args.infile, "r")
csv_reader = csv.DictReader(csv_file, delimiter=';')

# Open a file to write the costed bom to, if the file cannot be opened print error and exit
try:
    outputfile = open(args.outfile, 'w')
except IOError:
    print("Can't open output file for writing: " + args.outfile)
    sys.exit(2)

output_columns = ['Item', 'Part Number', 'Qty', 'Reference(s)', 'Title/Description', 'Value on Schematic', 'Manufacturer',
           'Manufacturer Part Number']

# Create a new csv writer object to use as the output formatter
out = csv.writer( outputfile, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_MINIMAL )

# Write column header to output file
out.writerow( output_columns )     # write column header

matched_items = []
unmatched_items = []

# Coalesce individual parts into groups

for line_item in csv_reader:

    try:
        constkwds = line_item['CONSTRUCTION'].replace(' ','').split(',')
    except KeyError:
        constkwds = []
    if len(constkwds) and constkwds[0] == '':
        constkwds = []

    # Filter out ignored reference designators
    skip = False
    for ignoredref in ignoredrefs:
        if line_item['Part'].startswith(ignoredref):
            skip = True
    if skip == True:
        continue


    # Attempt part number lookup
    try:
        pn = line_item['PARTNUMBER']
    except KeyError:
        pn = unkPn

    # Filter by construction if --const option was passed on command line
    if args.const is not None and len(constkwds):
        print(pn, args.const, constkwds)
        if args.const not in constkwds:
            print('skip')
            continue

    descr = getdescr(pn)

    if pn == unkPn or descr == '':
        unmatched_items.append({'Part Number': pn, 'Qty': 1, 'Reference(s)': line_item['Part'],
                                'Value on Schematic': line_item['Value'], 'Manufacturer': unk,
                                'Manufacturer Part Number': unk})
    else:
        add_item(matched_items, pn, line_item['Part'], line_item['Value'])

lastindex = 1
for i,item in enumerate(matched_items):
    mfginfo = getmfginfo(item['Part Number'])
    lastindex = i + 1
    item['Item'] = lastindex
    item['Qty'] = len(item['Reference(s)'])
    item['Reference(s)'] = pack_ref_designators(item['Reference(s)'])
    # Create string from list of references
    refs = ""
    for j, rgroup in enumerate(item['Reference(s)']):
        if(j):
            refs += ','
        refs += rgroup
    # Convert to string
    item['Reference(s)'] = refs
    item['Title/Description'] = getdescr(item['Part Number'])
    item['Manufacturer'] = mfginfo[0]['MFG']
    item['Manufacturer Part Number'] = mfginfo[0]['MPN']


    row = []

    row.append(item['Item'])
    row.append(item['Part Number'])
    row.append(item['Qty'])
    row.append(item['Reference(s)'])
    row.append(item['Title/Description'])
    row.append(item['Value On Schematic'])
    row.append(item['Manufacturer'])
    row.append(item['Manufacturer Part Number'])

    out.writerow(row)

    alt_source_index = 1
    while alt_source_index < len(mfginfo):
        row = []
        row.append(item['Item'])
        row.append('') # Part number
        row.append('') # Qty
        row.append('') # Reference(s)
        row.append('') # Title/Description
        row.append('') # Value On Schematic
        row.append(mfginfo[alt_source_index]['Manufacturer'])
        row.append(mfginfo[alt_source_index]['Manufacturer Part Number'])
        alt_source_index += 1



# Append unmatched items to end of csv file

for unmatched_item in  unmatched_items:
    del row[:]
    lastindex += 1
    row.append( lastindex ) # Item number
    row.append(unkPn) # Part number
    row.append('1') # Quantity
    row.append(unmatched_item['Reference(s)']) #Reference
    row.append(unk) # Title/Description
    row.append(unmatched_item['Value on Schematic'])
    writerow(out, row)













