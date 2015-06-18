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
from bommdb import *

defaultMpn = 'N/A'
defaultDb= '/etc/bommgr/parts.db'
defaultConfigLocations = ['/etc/bommgr/bommgr.conf','~/.bommgr/bommgr.conf','bommgr.conf']
firstPn = '800000-101'
defaultMID='M0000000'

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

# List part numbers, descriptions, manufacturers, manufacturer part numbers

def listParts(like=None):
    global defaultMpn, defaultMfgr
    global DB

    res = DB.get_parts(like)

    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Title/Description","Manufacturer","MPN"))
    for (pn,desc) in res:
        # Try to retrieve manufacturer info
        minfo = DB.lookup_mpn_by_pn(pn)

        if minfo == []: # Use defaults if it no MPN and manufacturer
            minfo =[{'mname': defaultMfgr, 'mpn': defaultMpn}]

        for i,item in enumerate(minfo):
            if i > 0:
                pn = ''
                desc = ''
            print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(pn,desc,minfo[i]['mname'],minfo[i]['mpn']))


# List manufacturers


def listMfgrs():
    global DB
    print('{0:<30}'.format("Manufacturer"))
    minfo = DB.get_mfgrs()
    if(minfo is not None):
        for mfgr in minfo:
            print('{0:<30}'.format(mfgr[0]))



# Add a new manufacturer to the manufacturer's list


def addMfgr(new_mfgr):
    global DB
    # Does it already exist?
    minfo = DB.lookup_mfg(new_mfgr)
    if(minfo is not None):
        print('Error: Manufacturer "{}" is already in the manufacturer\'s list'.format(new_mfgr))
        raise(ValueError)


    # Get the last used ID and generate the next ID to be used
    mid = DB.last_mid()
    if mid is not None:
        mid = int(mid[1:]) + 1
    else:
        mid = 0
    nextid = 'M{num:07d}'.format(num=mid)

    DB.add_mfg_to_mlist(new_mfgr, nextid)

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
    global DB
     # Get the last used part number and generate the next ID to be used
    res = DB.last_pn()
    # If this is the very first part number added use the default for firstpn
    if res is None or res[0] is None:
        pn = firstPn
    else:
        pn = res
        (prefix, suffix) = pn.split('-')
        nextnum = int(prefix) + 1
        pn = '{prefix:06d}-{suffix:03d}'.format(prefix=nextnum, suffix=101)
    return pn

# Add a new part to the database

def newPart(desc, newpn = None, mfg='', mpn=''):
    global DB
    pinfo = None

    if(len(desc) == 0 or len(desc) > 50):
        print("Error: Description must be between 1 and 50 characters")
        raise ValueError

    # Define the next part number to be used

    if(newpn is not None):
        # User defined part number, need to validate it
        pinfo = DB.lookup_pn(newpn)
        if(pinfo is not None):
            print('Error: Part number {} already exists'.format(newpn))
            raise(ValueError)
        validatePN(newpn)
        pn = newpn
    else:
        pn = nextPN()

    # Avoid duplicate part number assignment if mpn is not N/A

    if mpn is not None:
        minfo = DB.lookup_mpn(mpn)
        if mpn != defaultMpn and minfo is not None and minfo[1] == mfg:
            print("Error: MPN already exists with same manufacturer under part number {}".format(minfo[0]))
            raise(ValueError)

    # Check to see if the manufacturer exists
    minfo = DB.lookup_mfg(mfg)
    if minfo is None:
        # Manufacturer doesn't exist, create it
        addMfgr(mfg)
        # Get its ID
        minfo = DB.lookup_mfg(mfg)

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



# Query by MPN and print results if the MPN exists

def queryMPN(mpn):
    global DB
    res = DB.lookup_mpn(mpn)
    if(res is None):
        print("MPN does not exist")
        return
    pn = res[0]
    mname = res[1]
    mpn = res[2]

    res = DB.lookup_pn(pn)
    desc = res[1]

    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Title/Description","Manufacturer","MPN"))
    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(pn, desc ,mname , mpn))


# Query by PN and print results if the PN exists
# prints multiple lines if there are multiple MPN's mapped to a PN

def queryPN(pn):
    global defaultMpn, defaultMfgr
    global DB

    res = DB.lookup_pn(pn)
    if(res is None):
        print("Part number does not exist")
        return
    pn = res[0]
    desc = res[1]
    print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Title/Description","Manufacturer","MPN"))
    res = DB.lookup_mpn_by_pn(pn)
    if(len(res) is not 0):
        for item in res:
            print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(item['pn'],
                desc ,item['mname'], item['mpn']))
    else:
        print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(pn,
            desc, defaultMfgr, defaultMpn))

# Modify mpn

def modifyMPN(partnumber, curmpn, newmpn):
    global DB
    res = DB.lookup_mpn(curmpn)
    if res is None:
        print('Error: Can\'t get current MPN record')
        raise SystemError
    mid = res[3]
    DB.update_mpn(partnumber, curmpn, newmpn, mid)


# Modify manufacturer name for a given part number and MPN

def modifyMFG(partnumber, curmpn, newmfgid):
    global DB
    res = DB.lookup_mpn(curmpn)
    if res is None:
        print('Error: Unknown MPN {}'.format(curmpn))
        raise SystemError
    res = DB.lookup_mfg_by_id(newmfgid)
    if res is None:
        print('Error: Unknown manufacturer ID {}'.format(newmfgid))
        raise SystemError

    DB.update_mid(partnumber, curmpn, newmfgid)


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
    parser_list_pn.add_argument('--like', help="Return like matches only")

    parser_list_mpn = parser_list_subparser.add_parser('mfg', help='List manufacturers')


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
    parser_add_part.add_argument('--mpn', dest="mpn", help="Manufacturer's part number")
    parser_add_part.add_argument('--mfg', dest="manufacturer", help="Manufacturer name")
    parser_add_part.add_argument('--specpn', help="Specify PN")

    # Add mpn
    parser_add_mpn = parser_add_subparser.add_parser('altmpn',help='Add alternate MPN to existing part')
    parser_add_mpn.add_argument('part', help='Part number') # part number is mandatory for add mpn
    parser_add_mpn.add_argument('mpn', help='Manufacturer Part number') # part number is mandatory for add mpn
    parser_add_mpn.add_argument('manufacturer', help='Manufacturer Name') # Manufacturer name is mandatory
    parser_add_mpn.add_argument('--forcenewmfg', action='store_true', help="Force add of new manufacturer from name given")


    # Modify sub-subparser
    parser_modify = subparsers.add_parser('modify', help='Modify a title, or manufacturer\'s part number (MPN)')
    parser_modify_title_subparser = parser_modify.add_subparsers(dest='modifywhat', help='Modify a title')

    # Modify title
    parser_modify_title = parser_modify_title_subparser.add_parser('title',help='New title/description to use')
    parser_modify_title.add_argument('partnumber', help='Part number to look up')
    parser_modify_title.add_argument('title', help='New title to use')

    # Modify MPN
    parser_modify_mpn = parser_modify_title_subparser.add_parser('mpn',help='New manufacturer\'s part number to use')
    parser_modify_mpn.add_argument('partnumber', help='Part number to look up')
    parser_modify_mpn.add_argument('curmpn', help='Current MPN')
    parser_modify_mpn.add_argument('newmpn', help='New MPN')

    # Modify MFG
    parser_modify_mfg = parser_modify_title_subparser.add_parser('mfg',help='New manufacturer to use')
    parser_modify_mfg.add_argument('partnumber', help='Part number to look up')
    parser_modify_mfg.add_argument('curmpn', help='Current MPN')
    parser_modify_mfg.add_argument('manufacturer', help='New Manufacturer')
    parser_modify_mfg.add_argument('--forcenewmfg', action='store_true', help="Force add of new manufacturer from name given")

    # Modify manufacturer in manufacturer's list
    parser_modify_mlistmfg = parser_modify_title_subparser.add_parser('mlistmfg',help='Modify manufacturer name in manufacturer\'s list')
    parser_modify_mlistmfg.add_argument('curmfg', help='Current Manufacturer')
    parser_modify_mlistmfg.add_argument('newmfg', help='New Manufacturer')

    ## Parser code end


    ## Customize default configurations to user's home directory

    for i in range(0, len(defaultConfigLocations)):
        defaultConfigLocations[i] = os.path.expanduser(defaultConfigLocations[i])

    # parse the args and die on error

    args = parser.parse_args()

    # Read the config file, if any
    config = configparser.ConfigParser()

    if(args.config is not None):
        configLocation = os.path.expanduser(args.config)
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
        db = os.path.expanduser(args.specdb)
    else:
        if general is not None:
            db = os.path.expanduser(general.get('db', defaultDb))
            print(db)
        else:
            db = defaultDb


    # Check to see if we can access the database file and that it is writable

    if(os.path.isfile(db) == False):
        print('Error: Database file {} doesn\'t exist'.format(db))
        raise(SystemError)
    if(os.access(db,os.W_OK) == False):
        print('Error: Database file {} is not writable'.format(db))
        raise(SystemError)

    DB = BOMdb(db)


    print()
    print("Info: Database used: {}".format(os.path.abspath(db)))
    print()

    # Look up default manufacturer

    res = DB.lookup_mfg_by_id(defaultMID)
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
        if args.listwhat == 'mfg':
            listMfgrs()
        elif args.listwhat == 'parts':
            listParts(args.like)
        else:
            print('Error: unknown list option {}'.format(args.listwhat))
            sys.exit(2)

        sys.exit(0)

    # Query by pn or mpn
    if args.operation == 'query' :
        if args.querywhat == 'pn':
            queryPN(args.partnumber)
        elif args.querywhat == 'mpn':
            queryMPN(args.mpartnumber)
        else:
            print('Error: unknown query option {}'.format(args.querywhat))
            sys.exit(2)
        sys.exit(0)

    # Add a part number or manufacturer
    if args.operation == 'add':
        if args.addwhat == 'part':
            title = args.title
            if args.specpn:
                pn = args.specpn
            else:
                pn = nextPN()
            mname = defaultMfgr
            if args.manufacturer:
                mname = args.manufacturer
            mpn = defaultMpn
            if args.mpn:
                mpn = args.mpn
            if True:
                print('About to add:')
                print()
                print("MPN            : {}".format(mpn))
                print("Manufacturer   : {}".format(mname))
                print()
                print("as {}, {}".format(pn, title))
                print()
                if query_yes_no('Add new part?','no') is False:
                    sys.exit(0)
            pn = newPart(title, pn, mname, mpn)
            print('New part number added: {}'.format(pn))
        elif args.addwhat == 'altmpn':
            pn = args.part
            mpn = args.mpn
            mname = args.manufacturer
            res = DB.lookup_pn(pn)
            # Sanity checks
            if res is None :
                print('Error: no such part number {}'.format(pn))
                sys.exit(2)
            desc = res[1]
            res = DB.lookup_mpn(mpn)
            if res is not None:
                print('Error: MPN {} is already in the database'.format(mpn))
                sys.exit(2)
            minfo = DB.lookup_mfg(mname)
            if args.forcenewmfg is False and minfo is None:
                print('Error: Manufacturer {} is not in the database. Add with --forcenewmfg'.format(mname))
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
                minfo = DB.lookup_mfg(mname)
            mid = minfo[1]
            DB.add_mpn(pn, mid, mpn)
            print("Alternate MPN added")

        else:
            print('Unrecognized addwhat option')
            sys.exit(2)

    # Modify a title or an MPN
    if args.operation == 'modify':

        partnumber = ''
        if args.modifywhat in ['title', 'mpn', 'mfg']:
            partnumber = args.partnumber
            res = DB.lookup_pn(partnumber)
            if(res is None):
                print('Error: no such part number {}'.format(partnumber))
                sys.exit(2)

        # Modify title
        if args.modifywhat == 'title':
            DB.update_title(partnumber, args.title)

        # Modify mpn
        elif args.modifywhat == 'mpn' :
            curmpn = args.curmpn
            newmpn = args.newmpn
            res = DB.lookup_mpn(curmpn)
            if(res is None):
                print('Error: no such manufacturer part number {}'.format(curmpn))
                sys.exit(2)
            modifyMPN(partnumber, curmpn, newmpn)

        # Modify manufacturer
        elif args.modifywhat == 'mfg':
            curmpn = args.curmpn
            mfgr = args.manufacturer
            res = DB.lookup_mpn(curmpn)
            if(res is None):
                print('Error: no such manufacturer part number {}'.format(curmpn))
                sys.exit(2)
            # See if mfgr already exists
            res = DB.lookup_mfg(mfgr)
            if res is None:
                if args.forcenewmfg:
                    # Create new manufacturer
                    addMfgr(mfgr)
                    # Get the newly assigned mid
                    res = DB.lookup_mfg(mfgr)
                else:
                    print('Error: Manufacturer {} not in database. Add with --forcenewmfg'.format(mfgr))
                    sys.exit(2)
            mid = res[1]
            modifyMFG(partnumber, curmpn, mid)


        # Modify menufacturer name in manufacturer's list

        elif args.modifywhat == 'mlistmfg':
            curmfg = args.curmfg
            newmfg = args.newmfg

            res = DB.lookup_mfg(curmfg)
            if(res is None):
                print('Error: Manufacturer not in database')
                sys.exit(2)
            mid = res[1]

            if(DB.lookup_mfg(newmfg) is not None):
                print('Error: New Manufacturer already in database')
                sys.exit(2)
            DB.update_mfg(mid, newmfg)

        else:
            print('Error: unrecognized modifywhat option')
            sys.exit(2)























