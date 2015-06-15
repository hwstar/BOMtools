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
import configparser
from tkinter import *
from tkinter.ttk import *

defaultMpn = 'N/A'
defaultDb= '/etc/bommgr/parts.db'
defaultConfigLocations = ['/etc/bommgr/bommgr.conf','~/.bommgr/bommgr.conf','bommgr.conf']
firstPn = '800000-101'

listFrame = None

#
#
#
#
# Classes for TK GUI
#
#
#
#

#
# Full screen App Class. Sets up TK to use full screen
#


class FullScreenApp(object):
    def __init__(self, master, **kwargs):
        self.master=master
        pad=3
        self._geom='200x200+0+0'
        master.geometry("{0}x{1}+0+0".format(
            master.winfo_screenwidth()-pad, master.winfo_screenheight()-pad))
        master.bind('<Escape>',self.toggle_geom)

    def toggle_geom(self,event):
        geom = self.master.winfo_geometry()
        print(geom,self._geom)
        self.master.geometry(self._geom)
        self._geom=geom


#
# Dialog class
#

class Dialog(Toplevel):

    def __init__(self, parent, title = None, xoffset = 50, yoffset = 50):

        Toplevel.__init__(self, parent)
        self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        self.buttonbox()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx()+xoffset,
                                  parent.winfo_rooty()+yoffset))

        self.initial_focus.focus_set()

        self.wait_window(self)

    #
    # construction hooks
    #

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden

        pass

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons

        box = Frame(self)

        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)
        w = Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()

    #
    # standard button semantics
    #

    def ok(self, event=None):

        if not self.validate():
            self.initial_focus.focus_set() # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply()

        self.cancel()

    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks
    #

    def validate(self):

        return 1 # override

    def apply(self):

        pass # override

#
#
#
#
# Support functions
#
#
#
#

def openDB(db):
    # Set up the dabase connection
    global conn, cur

    # Check to see if we can access the database file and that it is writable

    conn = sqlite3.connect(db)
    cur = conn.cursor()
    if(os.path.isfile(db) == False):
        print('Error: Database file {} doesn\'t exist'.format(db))
        raise(SystemError)
    if(os.access(db,os.W_OK) == False):
        print('Error: Database file {} is not writable'.format(db))
        raise(SystemError)



# List part numbers, descriptions, manufacturers, manufacturer part numbers in a TreeView class with
# Vertical and horizontal scrollbars


def listParts(like=None):
    global cur, conn, defaultMpn, defaultMfgr, listFrame

    if listFrame is not None:
        listFrame.destroy()
        listFrame = None

    listFrame=Frame(root)
    listFrame.pack(side=TOP, fill=BOTH, expand=Y)


    ltree = Treeview(height="26", columns=("Part Number","Description","Manufacturer","Manufactuer Part Number"), selectmode="extended")
    ysb = Scrollbar(orient='vertical', command=ltree.yview)
    xsb = Scrollbar(orient='horizontal', command=ltree.xview)
    ltree.configure(xscroll=xsb.set, yscroll=ysb.set)
    ltree.heading('#1', text='Part Number', anchor=W)
    ltree.heading('#2', text='Description', anchor=W)
    ltree.heading('#3', text='Manufacturer', anchor=W)
    ltree.heading('#4', text='Manufacturer Part Number', anchor=W)
    ltree.column('#1', stretch=NO, minwidth=0, width=200)
    ltree.column('#2', stretch=NO, minwidth=0, width=500)
    ltree.column('#3', stretch=NO, minwidth=0, width=300)
    ltree.column('#4', stretch=YES, minwidth=0, width=300)
    ltree.column('#0', stretch=NO, minwidth=0, width=0) #width 0 for special heading

    mfgcur = conn.cursor()
    if like != None:
        cur.execute('SELECT Partnumber,Description FROM pndesc WHERE Description LIKE ? ORDER BY PartNumber ASC',[like])
    else:
        cur.execute('SELECT Partnumber,Description FROM pndesc ORDER BY PartNumber ASC')
    res = cur.fetchall()
    #print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format("Part Num","Title/Description","Manufacturer","MPN"))


    for row,(pn,desc) in enumerate(res):
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
            #print('{0:<20}  {1:<50}  {2:<30}  {3:<20}'.format(pn,desc,mfg,mpn))
            ltree.insert("", "end", "", values=((pn, desc, mfg, mpn)), tags=(row))

    # add tree and scrollbars to frame
    ltree.grid(in_=listFrame, row=0, column=0, sticky=NSEW)
    ysb.grid(in_=listFrame, row=0, column=1, sticky=NS)
    xsb.grid(in_=listFrame, row=1, column=0, sticky=EW)
    # set frame resizing priorities
    listFrame.rowconfigure(0, weight=1)
    listFrame.columnconfigure(0, weight=1)


# List manufacturers


def listMfgrs():
    global conn,cur
    print('{0:<30}'.format("Manufacturer"))
    cur.execute('SELECT MFGName FROM mlist ORDER BY MFGName ASC')
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


# Lookup manufacturer, return a tuple (MFGName,MFGId) if present else None if not present

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


# Update manufacturer name in manufacturer's list

def updateMfgrList(mid, newmfgr):
    global cur
    pinfo = lookupMfgrByID(mid)
    if(pinfo is None):
        print("Error: current manufacturer name not in database")
        raise(ValueError)
    mid = pinfo[1]
    cur.execute('DELETE FROM mlist WHERE MFGId=?',[mid])
    cur.execute('INSERT INTO mlist (MFGName,MFGId) VALUES (?,?)', [newmfgr, mid])
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

# Modify manufacturer name for a given part number and MPN

def modifyMFG(partnumber, curmpn, newmfgid):
    global cur,conn
    res = lookupMPN(curmpn)
    if res is None:
        print('Error: Unknown MPN {}'.format(curmpn))
        raise SystemError
    res = lookupMfgrByID(newmfgid)
    if res is None:
        print('Error: Unknown manufacturer ID {}'.format(newmfgid))
        raise SystemError
    cur.execute('DELETE FROM pnmpn WHERE PartNumber=? AND MPN=? ', [partnumber, curmpn])
    cur.execute('INSERT INTO pnmpn (PartNumber,Manufacturer,MPN) VALUES (?,?,?)',[partnumber, newmfgid, curmpn])
    conn.commit()


#
#
#
#
# Main line code
#
#
#
#
#

if __name__ == '__main__':
    conn = None
    cur = None

   ## Customize default configurations to user's home directory

    for i in range(0, len(defaultConfigLocations)):
        defaultConfigLocations[i] = os.path.expanduser(defaultConfigLocations[i])


    # Read the config file
    config = configparser.ConfigParser()

    configLocation = defaultConfigLocations

    config.read(configLocation)

    try:
        general = config['general']
    except KeyError:
        print('Error: no config file found')
        sys.exit(2)

    # Open the database file


    db = os.path.expanduser(general.get('db', defaultDb))

    openDB(db)


    # Look up default manufacturer

    res = lookupMfgrByID('M0000000')
    if(res is None):
        defaultMfgr = 'Default MFG Error'
    else:
        defaultMfgr = res[0]

    # Set up the TCL add window

    root = Tk()
    app=FullScreenApp(root)
    menubar = Menu(root, tearoff = 0)
    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=filemenu)
    # display the menu
    root.config(menu=menubar)

    viewmenu = Menu(menubar, tearoff = 0)
    viewmenu.add_command(label="List Parts", command=listParts)
    menubar.add_cascade(label="View", menu=viewmenu)


    # display the menu
    root.config(menu=menubar)

    root.mainloop()