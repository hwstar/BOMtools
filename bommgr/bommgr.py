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

import sys
import os
import sqlite3
import argparse
import configparser

defaultMfgr = 'Open Market'
defaultMpn = 'N/A'
defaultDb= '/etc/bommgr/parts.db'
defaultConfig = 'etc/bommgr/bommgr.conf'



def openDB(db):
    # Set up the dabase connection
    global conn, cur

    # Check to see if we can access the database file and that it is writable

    if(os.path.isfile(db) == False):
        print('Error: Database file {} doesn\'t exist'.format(db))
        raise(SystemError)
    if(os.access(db,os.W_OK) == False):
        print('Error: Database file {} is not writable'.format(db))
        raise(SystemError)

    conn = sqlite3.connect(db)
    cur = conn.cursor()


# List part numbers, descriptions, manufacturers, manufacturer part numbers

def listParts():
    global cur, conn, defaultMpn, defaultMfgr

    mfgcur = conn.cursor()
    cur.execute('SELECT Partnumber,Description FROM pndesc')
    res = cur.fetchall()
    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Title","Manufacturer","MPN"))
    for (pn,desc) in res:
        mfg = defaultMfgr
        mpn = defaultMpn
        mfgcur.execute('SELECT Manufacturer,MPN FROM pnmpn WHERE PartNumber=?',[pn])
        minfo = mfgcur.fetchone()
        if(minfo is not None):
            mpn = minfo[1]
            mfgid = minfo[0]
            mfgcur.execute('SELECT MFGName FROM mlist WHERE MFGId=?', [mfgid])
            minfo = mfgcur.fetchone()
            if(minfo is not None):
                mfg = minfo[0]

        print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(pn,desc,mfg,mpn))


# List manufacturers


def listMfgrs():
    global conn,cur
    print('{0:<30}'.format("Manufacturer"))
    cur.execute('SELECT MFGName FROM mlist ')
    minfo = cur.fetchall()
    minfo = sorted(minfo)
    if(minfo is not None):
        for mfgr in minfo:
            print('{0:<30}'.format(mfgr[0]))


# Lookup part number, return a tuple (PartNumber, Description) if present else None if not present

def lookupPN(pn):
    global cur

    cur.execute('SELECT PartNumber,Description FROM pndesc WHERE PartNumber = ?', [pn])
    res = cur.fetchone()
    return res


# Lookup manufacturer, return a tuple (MFGId, MFGName) if present else None if not present

def lookupMfgr(mfgr):
    global cur

    cur.execute('SELECT MFGName,MFGId FROM mlist WHERE MFGName = ?', [mfgr])
    res = cur.fetchone()
    return res

# Lookup manufacturer by ID , return a tuple (MFGId, MFGName) if present else None if not present

def lookupMfgrByID(mid):
    global cur

    cur.execute('SELECT MFGName,MFGId FROM mlist WHERE MFGId = ?', [mid])
    res = cur.fetchone()
    return res


# Lookup manufacturer part number return a tuple (PartNumber, Manufacturer, MPN) if present else None if not present

def lookupMPN(mpn):
    global cur

    cur.execute('SELECT PartNumber,Manufacturer,MPN FROM pnmpn WHERE MPN = ?', [mpn])
    res = cur.fetchone()
    if(res is None):
        return None
    pn = res[0]
    mid = res[1]
    mpn = res[2]

    # Convert Manufacturer ID to name

    res = lookupMfgrByID(mid)
    if res is not None:
        mname = res[0]
    else:
        raise(ProcessLookupError)

    return (pn, mname, mpn)


# Lookup MPN by PN, return an array of dicts containing each MPN found for a specific PN
# Return [] if no MPN's assigned to the PN

def lookupMPNByPN(pn):
    global cur

    cur.execute('SELECT PartNumber,Manufacturer,MPN FROM pnmpn WHERE PartNumber = ?', [pn])
    res = cur.fetchall()

    reslist = []
    for item in res:
        reslist.append({'pn' : item[0],'mid' : item[1], 'mpn' : item[2]})

    print(reslist) # DEBUG
    for i,item in enumerate(reslist):
        # Convert Manufacturer ID to name
        res = lookupMfgrByID(reslist[i]['mid'])
        if res is not None:
            reslist[i]['mname'] = res[0]
        else:
            raise(ValueError)

    return reslist


# Add a new manufacturer to the manufacturer's list


def addMfgr(new_mfgr):
    global conn, cur
    # Does it already exist?
    minfo = lookupMfgr(new_mfgr)
    if(minfo is not None):
        print('Error: Manufacturer "{}" is already in the manufacturer\'s list'.format(new_mfgr))
        raise(ValueError)


    # Get the last used ID and generate the next ID to be used
    cur.execute('SELECT MAX(MFGId) from mlist')
    minfo = cur.fetchone()
    if len(minfo) != 0:
        midnum = int(minfo[0][1:]) + 1
    else:
        midnum = 0
    nextid = 'M{num:07d}'.format(num=midnum)

    # Insert the manufacturer
    cur.execute('INSERT INTO mlist (MFGId,MFGName) VALUES (?,?)', [nextid, new_mfgr])

    # Save (commit) the changes
    conn.commit()

    print("Manufacturer {} added".format(new_mfgr))

# Validate a part number to ensure it is in the correct 6-3 format

def validatePN(pn):
    try:
        (prefix, suffix) = pn.split('-')
    except ValueError:
        print('Error: Bad part number format, needs to be XXXXXX-YYY')
        raise(ValueError)

    if len(prefix) != 6 or len(suffix)!= 3:
        print('Error: Bad part number format, needs to be XXXXXX-YYY')
        raise(ValueError)


# Return the next available part number

def nextPN():
    global cur
     # Get the last used part number and generate the next ID to be used
    cur.execute('SELECT MAX(PartNumber) from pndesc')
    res = cur.fetchone()
    pn = res[0]
    (prefix, suffix) = pn.split('-')
    nextnum = int(prefix) + 1
    pn = '{prefix:06d}-{suffix:03d}'.format(prefix=nextnum, suffix=101)
    return pn

# Add a new part to the database

def newPart(desc, newpn = None, mfg='', mpn=''):
    global cur
    pinfo = None

    if(len(desc) == 0 or len(desc) > 50):
        print("Error: Description must be between 1 and 50 characters")
        raise ValueError

    # Define the next part number to be used

    if(newpn is not None):
        # User defined part number, need to validate it
        pinfo = lookupPN(newpn)
        if(pinfo is not None):
            print('Error: Part number {} already exists'.format(newpn))
            raise(ValueError)
        validatePN(newpn)
        pn = newpn
    else:
        pn = nextPN()

    # Avoid duplicate part number assignment if mpn is not N/A

    if mpn is not None:
        minfo = lookupMPN(mpn)
        if mpn != defaultMpn and minfo is not None and minfo[1] == mfg:
            print("Error: MPN already exists with same manufacturer under part number {}".format(minfo[0]))
            raise(ValueError)

    # Check to see if the manufacturer exists
    minfo = lookupMfgr(mfg)
    if minfo is None:
        # Manufacturer doesn't exist, create it
        addMfgr(mfg)
        # Get its ID
        minfo = lookupMfgr(mfg)

    mname = minfo[0]
    mid = minfo[1]

    # We now have a valid pn, desc, mname, mpn, and mid. Insert the pn and description in the pndesc table,
    # and insert the pn, mid, and mpn in the pnmpn table

   # Insert part number and description
    cur.execute('INSERT INTO pndesc (PartNumber,Description) VALUES (?,?)', [pn, desc])

   # Insert part number, manufacturer id, and manufactuer part number
    cur.execute('INSERT INTO pnmpn (PartNumber,Manufacturer,MPN) VALUES (?,?,?)', [pn, mid, mpn])

    # Save (commit) the changes
    conn.commit()
    return pn



# Update the title (description) of a part number

def updateTitle(pn, desc):
    global cur
    pinfo = lookupPN(pn)
    if(pinfo is None):
        print("Error: Part number {} not in database").format(pn)
        raise(ValueError)
    pn = pinfo[0]
    cur.execute("DELETE FROM pndesc WHERE PartNumber=?",[pn])
    cur.execute('INSERT INTO pndesc (PartNumber,Description) VALUES (?,?)', [pn, desc])
     # Save (commit) the changes
    conn.commit()


# Query by MPN and print results if the MPN exists

def queryMPN(mpn):
    res = lookupMPN(mpn)
    if(res is None):
        print("MPN does not exist")
        return
    pn = res[0]
    mname = res[1]
    mpn = res[2]

    res = lookupPN(pn)
    desc = res[1]

    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Title","Manufacturer","MPN"))
    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(pn, desc ,mname , mpn))


# Query by PN and print results if the PN exists
# prints multiple lines if there are multiple MPN's mapped to a PN

def queryPN(pn):
    global defaultMpn, defaultMfgr
    res = lookupPN(pn)
    if(res is None):
        print("Part number does not exist")
        return
    pn = res[0]
    desc = res[1]
    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Description","Manufacturer","MPN"))
    res = lookupMPNByPN(pn)
    if(len(res) is not 0):
        for item in res:
            print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(item['pn'],
                desc ,item['mname'], item['mpn']))
    else:
        print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(pn,
            desc, defaultMfgr, defaultMpn))



if __name__ == '__main__':
    conn = None
    cur = None
    parser = argparse.ArgumentParser(description = 'BOM Manager Utility', prog = 'bommgr.py')
    parser.add_argument('--specdb', help='Specify database file path')
    parser.add_argument('--config', help='Specify config file path', default=defaultConfig)
    subparsers = parser.add_subparsers(dest = 'operation', help='Run bommgr.py {command} -h for additional help')
    parser_nextpn = subparsers.add_parser('nextpn', help='Get next unassigned part number')
    parser_list = subparsers.add_parser('list', help='Dump list to console')
    parser_list.add_argument('--type', help='List manufacturers or parts (default)')
    parser_query = subparsers.add_parser('query', help='Return parts info')
    parser_query.add_argument('item', help='Query item')
    parser_query.add_argument('--by', help='Query by pn or mpn (default)')
    parser_add = subparsers.add_parser('add', help='Add new part')
    parser_add.add_argument('title', help='Title (Part Description)')
    parser_add.add_argument('--mpn', help="Manufacturer's part number")
    parser_add.add_argument('--manufacturer',help="Manufacturer name")
    parser_add.add_argument('--specpn',help="Specify PN")

    # parse the args and die on error

    args = parser.parse_args()

    # Read the config file, if any
    config = configparser.ConfigParser()
    config.read(args.config)
    general = config['general']

    # Open the database file

    # If database specified in args, override default and config path
    if(args.specdb is not None):
        db = args.specdb
    else:
        db = general.get('db', defaultDb)

    openDB(db)

     # if nextpn, print the next available part number
    if(args.operation is None):
        print("Error: no operation specified")
        sys.exit(2)

    if(args.operation == 'nextpn'):
        print(nextPN())
        sys.exit(0)

    if(args.operation == 'list'):
        if(args.type == 'manufacturers'):
            listMfgrs()
        elif(args.type is None or args.type == 'parts'): # Default
            listParts()
        sys.exit(0)

    # Query by pn or mpn (default)
    if(args.operation == 'query'):
        if(args.by == 'pn'):
            queryPN(args.item)
        elif(args.by is None or args.by == 'mpn'): # Default
            queryMPN(args.item)
        sys.exit(0)

    if(args.operation == 'add'):
        title = args.title
        pn = None
        if(args.specpn):
            pn = args.specpn
        mname = defaultMfgr
        if(args.manufacturer):
            mname = args.manufacturer
        mpn = defaultMpn
        if(args.mpn):
            mpn = args.mpn
        pn = newPart(title, pn, mname, mpn)
        print("New part number added: {}".format(pn))



















