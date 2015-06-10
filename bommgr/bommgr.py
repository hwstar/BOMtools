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

defaultMpn = 'N/A'
defaultDb= '/etc/bommgr/parts.db'
defaultConfigLocations = ['/etc/bommgr/bommgr.conf','~/.bommgr/bommgr.conf','bommgr.conf']
firstPn = '800000-101'

# Yes/no prompt

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

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
    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Title/Description","Manufacturer","MPN"))
    for (pn,desc) in res:
        mfg = defaultMfgr
        mpn = defaultMpn
        # Try to retrieve manufacturer info
        mfgcur.execute('SELECT Manufacturer,MPN FROM pnmpn WHERE PartNumber=?',[pn])
        minfo = mfgcur.fetchall()

        if minfo == []: # Use defaults if it no MPN and manufacturer
            minfo =[(defaultMfgr,defaultMpn)]

        for i,item in enumerate(minfo):
            mpn = item[1]
            mfgid = item[0]
            mfgcur.execute('SELECT MFGName FROM mlist WHERE MFGId=?', [mfgid])
            mninfo = mfgcur.fetchone()
            if(mninfo is not None):
                mfg = mninfo[0]
            else:
                mfg = defaultMfgr
            if i > 0:
                pn = ''
                desc = ''
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


# Lookup manufacturer part number return a tuple (PartNumber, Manufacturer, MPN, Manufacturer ID ) if present else None if not present

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
        raise(ValueError)

    return (pn, mname, mpn, mid)


# Lookup MPN by PN, return an array of dicts containing each MPN found for a specific PN
# Return [] if no MPN's assigned to the PN

def lookupMPNByPN(pn):
    global cur

    cur.execute('SELECT PartNumber,Manufacturer,MPN FROM pnmpn WHERE PartNumber = ?', [pn])
    res = cur.fetchall()

    reslist = []
    for item in res:
        reslist.append({'pn' : item[0],'mid' : item[1], 'mpn' : item[2]})

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
    # If this is the very first part number added use the default for firstpn
    if res is None or res[0] is None:
        pn = firstPn
    else:
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

    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Title/Description","Manufacturer","MPN"))
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
    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Title/Description","Manufacturer","MPN"))
    res = lookupMPNByPN(pn)
    if(len(res) is not 0):
        for item in res:
            print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(item['pn'],
                desc ,item['mname'], item['mpn']))
    else:
        print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(pn,
            desc, defaultMfgr, defaultMpn))

# Modify title

def modifyTitle(partnumber, newtitle):
    global cur,conn

    cur.execute('DELETE FROM pndesc WHERE PartNumber=?', [partnumber])
    cur.execute('INSERT INTO pndesc (PartNumber,Description) VALUES (?,?)',[partnumber, newtitle])
    conn.commit()



# Modify mpn

def modifyMPN(partnumber, curmpn, newmpn):
    global cur,conn
    res = lookupMPN(curmpn)
    if res is None:
        print('Error: Can\'t get current MPN record')
        raise SystemError
    cur.execute('DELETE FROM pnmpn WHERE PartNumber=? AND MPN=? ', [partnumber, curmpn])
    cur.execute('INSERT INTO pnmpn (PartNumber,Manufacturer,MPN) VALUES (?,?,?)',[partnumber, res[3], newmpn])
    conn.commit()


if __name__ == '__main__':
    conn = None
    cur = None
    parser = argparse.ArgumentParser(description = 'BOM Manager Utility', prog = 'bommgr.py')
    parser.add_argument('--specdb', help='Specify database file path')
    parser.add_argument('--config', help='Specify config file path', default=None)
    subparsers = parser.add_subparsers(dest = 'operation', help='Run bommgr.py {command} -h for additional help')

    parser_nextpn = subparsers.add_parser('nextpn', help='Get next unassigned part number')

    # List sub sub-parser
    parser_list = subparsers.add_parser('list', help='List items')
    parser_list_subparser = parser_list.add_subparsers(dest='listwhat', help='List parts or manufacturers')

    parser_list_pn = parser_list_subparser.add_parser('parts', help='List part numbers')

    parser_list_mpn = parser_list_subparser.add_parser('manuf', help='List manufacturers')


    # Query sub-subparser
    parser_query = subparsers.add_parser('query', help='Query something')
    parser_query_subparser = parser_query.add_subparsers(dest='querywhat', help='Query a part or MPN')

    parser_query_pn = parser_query_subparser.add_parser('pn', help='Query part number')
    parser_query_pn.add_argument('partnumber', help='Part Number')

    parser_query_mpn = parser_query_subparser.add_parser('mpn', help='Query manufacturer\'s part number')
    parser_query_mpn.add_argument('mpartnumber', help='Part Number')


    # Add sub-subparser
    parser_add = subparsers.add_parser('add', help='Add new part')
    parser_add_subparser = parser_add.add_subparsers(dest='addwhat', help='Add a part or MPN')

    # Add part
    parser_add_part = parser_add_subparser.add_parser('part',help='Add part')
    parser_add_part.add_argument('title', help='Title (Part Description)') # title is mandatory for add part
    parser_add_part.add_argument('--mpn', help="Manufacturer's part number")
    parser_add_part.add_argument('--manufacturer',help="Manufacturer name")
    parser_add_part.add_argument('--specpn',help="Specify PN")

    # Add mpn
    parser_add_mpn = parser_add_subparser.add_parser('altmpn',help='Add alternate MPN to existing part')
    parser_add_mpn.add_argument('part', help='Part number') # part number is mandatory for add mpn
    parser_add_mpn.add_argument('mpn', help='Manufacturer Part number') # part number is mandatory for add mpn
    parser_add_mpn.add_argument('manufacturer', help='Manufacturer Name') # Manufacturer name is mandatory
    parser_add_mpn.add_argument('--newmfg', action='store_true', help="Add new manufacturer from name given")


    # Modify sub-subparser
    parser_modify = subparsers.add_parser('modify', help='Modify a title, or manufacturer\'s part number (MPN)')
    parser_modify_title_subparser = parser_modify.add_subparsers(dest='modifywhat', help='Modify a title')

    # Modify title
    parser_modify_title = parser_modify_title_subparser.add_parser('title',help='New title/description to use')
    parser_modify_title.add_argument('partnumber', help='Part number to look up')
    parser_modify_title.add_argument('title', help='New title to use')

    # Modify MPN
    parser_modify_title = parser_modify_title_subparser.add_parser('mpn',help='New manufacturer\'s part number to use')
    parser_modify_title.add_argument('partnumber', help='Part number to look up')
    parser_modify_title.add_argument('curmpn', help='Current MPN')
    parser_modify_title.add_argument('newmpn', help='New MPN')


# Print a y/n prompt and wait for input



    # parse the args and die on error

    args = parser.parse_args()

    # Read the config file, if any
    config = configparser.ConfigParser()

    if(args.config is not None):
        configLocation = args.config
    else:
        configLocation = defaultConfigLocations

    config.read(configLocation)

    try:
        general = config['general']
    except KeyError:
        print('Warning: no config file found')
        general = None

    # Open the database file

    # If database specified in args, override default and config path
    if args.specdb is not None:
        db = args.specdb
    else:
        if general is not None:
            db = general.get('db', defaultDb)
        else:
            db = defaultDb

    openDB(db)

    print()
    print("Info: Database used: {}".format(os.path.abspath(db)))
    print()

    # Look up default manufacturer

    res = lookupMfgrByID('M0000000')
    if(res is None):
        defaultMfgr = 'Default MFG Error'
    else:
        defaultMfgr = res[0]


     # if nextpn, print the next available part number
    if args.operation is None:
        print('Error: no operation specified')
        sys.exit(2)

    if args.operation == 'nextpn':
        print(nextPN())
        sys.exit(0)

    if args.operation == 'list':
        if args.listwhat == 'manuf':
            listMfgrs()
        elif args.listwhat == 'parts':
            listParts()
        sys.exit(0)

    # Query by pn or mpn
    if args.operation == 'query' :
        if args.querywhat == 'pn':
            queryPN(args.partnumber)
        elif args.querywhat == 'mpn':
            queryMPN(args.mpartnumber)
        sys.exit(0)

    # Add a part number or manufacturer
    if args.operation == 'add':
        if args.addwhat == 'part':
            title = args.title
            pn = None
            if args.specpn:
                pn = args.specpn
            mname = defaultMfgr
            if(args.manufacturer):
                mname = args.manufacturer
            mpn = defaultMpn
            if args.mpn:
                mpn = args.mpn
            pn = newPart(title, pn, mname, mpn)
            print('New part number added: {}'.format(pn))
        elif args.addwhat == 'altmpn':
            pn = args.part
            mpn = args.mpn
            mname = args.manufacturer
            res = lookupPN(pn)
            # Sanity checks
            if res is None :
                print('Error: no such part number {}'.format(pn))
                sys.exit(2)
            desc = res[1]
            res = lookupMPN(mpn)
            if res is not None:
                print('Error: MPN {} is already in the database'.format(mpn))
                sys.exit(2)
            minfo = lookupMfgr(mname)
            if args.newmfg is False and minfo is None:
                print('Error: Manufacturer {} is not in the database. Add with --newmfg'.format(mname))
                sys.exit(2)
            if True:
                print('About to add:')
                print()
                print("MPN            : {}".format(mpn))
                print("Manufacturer   : {}".format(mname))
                print()
                print("to {}, {}".format(pn, desc))
                print()
                if query_yes_no('Add alternate mpn?','no') is False:
                    sys.exit(0)
            if(minfo is None): # Add new manufacturer if it doesn't exist
                addMfgr(mname)
                minfo=lookupMfgr(mname)
            mid = minfo[1]
             # Insert part number, manufacturer id, and manufactuer part number
            cur.execute('INSERT INTO pnmpn (PartNumber,Manufacturer,MPN) VALUES (?,?,?)', [pn, mid, mpn])
            conn.commit()
            print("Alternate MPN added")

        else:
            print('Unrecognized addwhat option')
            sys.exit(2)

    # Modify a title or an MPN
    if args.operation == 'modify':
        partnumber = args.partnumber
        res = lookupPN(partnumber)
        if(res is None):
            print('Error: no such part number {}'.format(partnumber))
            sys.exit(2)
        if args.modifywhat == 'title':
            modifyTitle(partnumber, args.title)
        elif args.what == 'mpn' :
            res = lookupPN(partnumber)
            if res is None :
                print('Error: no such part number {}'.format(partnumber))
                sys.exit(2)
            curmpn = args.curmpn
            newmpn = args.newmpn
            res = lookupMPN(curmpn)
            if(res is None):
                print('Error: no such manufacturer part number {}'.format(curmpn))
                sys.exit(2)
            modifyMPN(partnumber, curmpn, newmpn)
        else:
            print('Error: unrecognized modifywhat option')
            sys.exit(2)























