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


if len(sys.argv) != 2:
    print('Usage: gendb /path/to/parts.db')
    sys.exit(1)

# Validate path name
dbpath = sys.argv[1]
dbdir = os.path.dirname(dbpath)
if os.path.isdir(dbdir) == False:
    print('Error: {} is not a directory'.format(dbdir))
    sys.exit(1)
if os.access(dbdir, os.W_OK) == False:
    print('Error: {}" is not writable'.format(dbdir))
    sys.exit(1)

# If the file exists, exit. We can't continue
if os.path.exists(dbpath):
    print('Error: file {} exists'.format(dbpath))
    sys.exit(1)

# Create the database file
conn = sqlite3.connect(dbpath)

# Create the pndesc table

conn.execute('CREATE TABLE pndesc (PartNumber TEXT,Description TEXT)')
conn.commit()

# Create the pnmpn table

conn.execute('CREATE TABLE pnmpn (PartNumber TEXT,Manufacturer TEXT, MPN TEXT, DataSheet TEXT)')
conn.commit()

# Create the mlist table

conn.execute('CREATE TABLE mlist (MFGId TEXT,MFGName TEXT)')
conn.execute('INSERT INTO mlist (MFGId,MFGName) VALUES (?,?)', ['M0000000','Open Market'])
conn.commit()

#Create the version table
conn.execute('CREATE TABLE version (major INTEGER,minor INTEGER)')
conn.execute('INSERT INTO version (major,minor) VALUES(?,?)', [0,1])
conn.commit()

#Create the config table
conn.execute('CREATE TABLE config (key TEXT,value TEXT)')
conn.commit()

sys.exit(0)