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

import subprocess
import configparser
from tkinter import *
from tkinter.ttk import *
from tkinter.filedialog import askopenfilename
import pyperclip
from bommdb import *


defaultMpn = 'N/A'
defaultDb= '/etc/bommgr/parts.db'
defaultConfigLocations = ['/etc/bommgr/bommgr.conf','~/.bommgr/bommgr.conf','bommgr.conf']
firstPn = '800000-101'
defaultMID = 'M0000000'

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

        self.bodyframe = Frame(self)
        self.initial_focus = self.body(self.bodyframe)
        self.bodyframe.pack(padx=5, pady=5)

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
# Error popup box
#

class ErrorPopUp(Dialog):

    def __init__(self, parent, title = "Error", xoffset=50, yoffset=50, message=None):
        if title is None or Message is None:
            raise SystemError
        self.message=message
        Dialog.__init__(self, parent, title, xoffset, yoffset)



    def buttonbox(self):
        # Override
        # standard buttons

        box = Frame(self)

        w = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        w.pack(side=LEFT, padx=5, pady=5)

        self.bind("<Return>", self.cancel)
        self.bind("<Escape>", self.cancel)

        box.pack()

    def body(self, master):
        # Print the error message
        Label(master, text=self.message).pack(anchor=W)

#
# Part Search Select Dialog Box
#

class ViewPartsDialog(Dialog):
    search_items = ['RES,0603%','RES,0805%','CAP,0603%','CAP,0805%','XSTR%','IC%']
    def __init__(self, parent, title = "View Parts Like", xoffset=50, yoffset=50):
        if title is None:
            raise SystemError
        Dialog.__init__(self, parent, title, xoffset, yoffset)

    def body(self, master):
        """
        Present combo box of search items
        """
        patframe=Frame(master)
        Label(patframe, text='Search Pattern').grid(row=0, column=0, sticky=W)
        self.search_entry = Combobox(patframe, width=50, values=ViewPartsDialog.search_items)
        self.search_entry.grid(row=0, column=1, sticky=W)
        patframe.pack()
        helpframe=Frame(master)
        Label(helpframe, text='Use % as a wildcard character').pack()
        helpframe.pack()

    def validate(self):
        return True

    def apply(self):
        self.selected = self.search_entry.get()
        if self.selected not in ViewPartsDialog.search_items:
            ViewPartsDialog.search_items.append(self.selected)

    def get_selected(self):
        return self.selected
#
# MPN Search Select Dialog Box
#

class ViewMPNsDialog(Dialog):
    mpn_search_items = []

    def __init__(self, parent, title = "View MPN's Like", xoffset=50, yoffset=50):
        if title is None:
            raise SystemError
        Dialog.__init__(self, parent, title, xoffset, yoffset)

    def body(self, master):
        """
        Present combo box of search items
        """
        patframe=Frame(master)
        Label(patframe, text='Search Pattern').grid(row=0, column=0, sticky=W)
        self.search_entry = Combobox(patframe, width=50, values=ViewMPNsDialog.mpn_search_items)
        self.search_entry.grid(row=0, column=1, sticky=W)
        patframe.pack()
        helpframe=Frame(master)
        Label(helpframe, text='Use % as a wildcard character').pack()
        helpframe.pack()

    def validate(self):
        return True

    def apply(self):
        self.selected = self.search_entry.get()
        if self.selected not in ViewMPNsDialog.mpn_search_items:
            ViewMPNsDialog.mpn_search_items.append(self.selected)

    def get_selected(self):
        print(self.selected)
        return self.selected




#
# Edit Description dialog box
#

class EditDescription(Dialog):
    def __init__(self, parent, title = None, xoffset=50, yoffset=50, values=None, db=None):
        if db is None or values is None or title is None:
            raise SystemError
        self.db = db
        self.values = values
        Dialog.__init__(self, parent, title, xoffset, yoffset)

    def body(self, master):
        Label(master, text='Description').grid(row=0, column=0, sticky=W)
        self.title_entry = Entry(master, width=50)
        partinfo = self.db.lookup_pn(self.values[0])
        if partinfo is None:
            raise SystemError
        self.title_entry.insert(0, partinfo[1])
        self.title_entry.grid(row=0, column=1, sticky=W)

    def validate(self):
        title_entry_text = self.title_entry.get()
        if len(title_entry_text) < 5 or len(title_entry_text) > 50:
            return False
        return True

    def apply(self):
        title_entry_text = self.title_entry.get()
        self.db.update_title(self.values[0], title_entry_text)
        self.values[1] = title_entry_text


#
# Edit Manufacturer dialog box
#

class EditManufacturer(Dialog):
    def __init__(self, parent, title = None, xoffset=50, yoffset=50, values=None, db=None):
        if db is None or values is None or title is None:
            raise SystemError
        self.db = db
        self.values = values
        Dialog.__init__(self, parent, title, xoffset, yoffset)

    def body(self, master):
        """
        Print dialog box body
        """
        Label(master, text='Manufacturer').grid(row=0, column=0, sticky=W)
        self.title_entry = Entry(master, width=30)
        self.title_entry.insert(0, self.values[0])
        self.title_entry.grid(row=0, column=1, sticky=W)

    def validate(self):
        """
        Validate dialog box contents
        """
        self.newmfgname = self.title_entry.get()
        if len(self.newmfgname) < 3 or len(self.newmfgname) > 30:
            return False
        # Did it change
        if self.newmfgname != self.values[0]:
            # Check to see if the user is defining a manufacturer already in the database
            res = self.db.lookup_mfg(self.newmfgname)
            if res is not None:
                e=ErrorPopUp(self.bodyframe, message="Manufacturer already defined")
                return False
        return True

    def apply(self):
        """
        Apply dialog box changes
        """
        res = self.db.lookup_mfg(self.values[0]) # Get old mfg info
        if res is None:
            raise SystemError
        mid = res[1]
        self.db.update_mfg(mid, self.newmfgname)
        self.values[0] = self.newmfgname

#
# Edit Manufacturer's part number dialog box
#

class EditMPN(Dialog):
    def __init__(self, parent, title = None, xoffset=50, yoffset=50, values=None, db=None, tags=None):
        if db is None or values is None or title is None or tags is None:
            raise SystemError
        self.db = db
        self.values = values
        self.tags = tags
        Dialog.__init__(self, parent, title, xoffset, yoffset)

    def body(self, master):
        Label(master, text='Manufacturer Part Number').grid(row=0, column=0, sticky=W)
        self.mpn_entry = Entry(master, width=30)
        partinfo = self.db.lookup_part_by_pn_mpn(self.tags[0], self.values[3])
        if partinfo is None:
            raise SystemError
        self.mpn_entry.insert(0, partinfo[2])
        self.mpn_entry.grid(row=0, column=1, sticky=W)


    def validate(self):
        title_entry_text = self.mpn_entry.get()
        if len(title_entry_text) < 3 or len(title_entry_text) > 30:
            return False
        return True

    def apply(self):
        (pn, mname, mpn, mid) = self.db.lookup_part_by_pn_mpn(self.tags[0], self.values[3])
        newmpn = self.mpn_entry.get()
        self.db.update_mpn(pn, mpn,
                           newmpn, mid)
        self.values[3] = newmpn


#
# Add alternate source dialog box
#

class AddAlternateSourceDialog(Dialog):
    """
    Add part dialog box
    """
    def __init__(self, parent, title = "Add Alternate Source", xoffset=50, yoffset=50, db=None, pn=None):
        """
        :param parent: Parent window
        :param title: Title of add part dialog box
        :param xoffset: Offset in X direction
        :param yoffset: Offset in Y direction
        :param db: Database object
        :return: N/A
        """
        if db is None or title is None or pn is None:
            raise SystemError
        self.db = db
        self.pn = pn
        self.success = False
        Dialog.__init__(self, parent, title, xoffset, yoffset)


    def body(self, master):
        """
        Display the fields for the manufacturer part number
        :param master: Parent window
        """
        self.mfgrs = self.db.get_mfgr_list()
        def_sel = self.mfgrs.index(defaultMfgr)

        Label(master, text='Manufacturer').grid(row=2, column=0, sticky=W)
        self.mfgr_entry = Combobox(master, width=30, values=self.mfgrs)
        self.mfgr_entry.current(def_sel)
        self.mfgr_entry.grid(row=2, column=1, sticky=W)

        Label(master, text='Manufacturer Part Number').grid(row=3, column=0, sticky=W)
        self.mpn_entry = Entry(master, width=30)
        self.mpn_entry.insert(0, defaultMpn)
        self.mpn_entry.grid(row=3, column=1, sticky=W)


    def validate(self):
        """
        Validate manufacturer part number
        """
        x = len(self.mpn_entry.get())
        if x < 3 or x > 30:
            return False

        # Validate manufacturer, and add a new manufacturer if need be
        self.new_mname = self.mfgr_entry.get()
        if self.new_mname not in self.mfgrs:
            confirm_mfg = AddMfgrDialog(self.parent, new_mfg=self.new_mname)
            if confirm_mfg.confirmed() is False:
                return False
            else:
                nextmid = nextFreeMID(self.db)
                # Add manufacturer and MID to manufacturer list
                self.db.add_mfg_to_mlist(self.new_mname, nextmid)
                self.mfgrs.append(self.new_mname)

        # Get the mid for the manufacturer name
        res = self.db.lookup_mfg(self.new_mname)
        if res is None:
            raise SystemError
        self.new_mid = res[1]

        # Check for duplicate manufacturer part record
        sources = self.db.lookup_mpn_by_pn(self.pn)
        self.new_mpn = self.mpn_entry.get()
        for item in sources:
            if self.new_mname == item['mname'] and self.new_mpn == item['mpn']:
                return False # Item already a valid source

        return True

    def apply(self):
        """
        Write the new manufacturer part record to the database
        """
        self.db.add_mpn(self.pn, self.new_mid, self.new_mpn)
        self.success = True

    def get_new_mfgpartrec(self):
        """
        Return new manufacturer and mpn
        :return: Dict with pn, mid, mfg and mpn if successful else none
        """
        if self.success:
            return {'pn': self.pn, 'mid': self.new_mid, 'mfg': self.new_mname, 'mpn': self.new_mpn}
        else:
            return None

#
# Add manufacturer confirmation dialog box

class AddMfgrDialog(Dialog):
    def __init__(self, parent, title="Add Manufacturer", xoffset=50, yoffset=50, new_mfg=None):
        if new_mfg is None:
            raise SystemError
        self.confirm = False
        self.new_mfg = new_mfg
        self.titlestr = title
        Dialog.__init__(self, parent, title, xoffset, yoffset)

    def body(self, master):
        label_text = self.titlestr+': '+self.new_mfg+'?'
        Label(master, text=label_text).pack()


    def apply(self):
        self.confirm = True

    def confirmed(self):
        return self.confirm

#
# Remove source dialog box
#

class RemoveSourceDialog(Dialog):
    def __init__(self, parent, title="Remove Source", xoffset=50, yoffset=50, db=None, pn=None, mfg=None, mpn=None):
        """
        :param parent: Parent window
        :param title: Title of add part dialog box
        :param xoffset: Offset in X direction
        :param yoffset: Offset in Y direction
        :param db: Database object
        :param pn: Part number
        :param mfg: Manufacturer
        :param mpn: Manufacturer part number
        :return: N/A

        """
        if(db is None or pn is None or mfg is None or mpn is None):
            raise SystemError
        self.db = db
        self.pn = pn
        self.mfg = mfg
        self.mpn = mpn
        Dialog.__init__(self, parent, title, xoffset, yoffset)

    def body(self, master):
        Label(master, text='Part Number').grid(row=0, column=0, sticky=W)
        Label(master, text=self.pn, relief=SUNKEN).grid(row=0, column=1, sticky=W)

        Label(master, text='Manufacturer').grid(row=1, column=0, sticky=W)
        Label(master, text=self.mfg, relief=SUNKEN).grid(row=1, column=1, sticky=W)

        Label(master, text='Manufacturer Part Number').grid(row=2, column=0, sticky=W)
        Label(master, text=self.mpn, relief=SUNKEN).grid(row=2, column=1, sticky=W)

        Label(master, text='').grid(row=3, column=0, sticky=W)
        Label(master, text='').grid(row=3, column=1, sticky=W)

        Label(master, text='Type YES in the box to confirm deletion').grid(row=4, column=0, sticky=W)
        self.yes_entry = Entry(master, width=3)
        self.yes_entry.grid(row=4, column=1, sticky=W)

    def validate(self):
        if self.yes_entry.get() == 'YES':
            return True
        else:
            return False

    def apply(self):
        res = self.db.lookup_mfg(self.mfg)
        if res is None:
            raise SystemError
        mid = res[1]
        self.db.remove_source(self.pn, mid, self.mpn)

#
# Add part dialog box
#

class AddPartDialog(Dialog):
    """
    Add part dialog box
    """
    def __init__(self, parent, title = "Add Part", xoffset=50, yoffset=50, db=None, pnhint='', deschint=''):
        """

        :param parent: Parent window
        :param title: Title of add part dialog box
        :param xoffset: Offset in X direction
        :param yoffset: Offset in Y direction
        :param db: Database object
        :param pnhint: part number hint
        :param deschint: description hint

        :return: N/A
        """
        if db is None or title is None:
            raise SystemError
        self.db = db
        self.pnhint = pnhint
        self.deschint = deschint
        Dialog.__init__(self, parent, title, xoffset, yoffset)

    def new_pn(self):
        """
        Return the next available part number from the database
        :return: Part number string
        """
        res = self.db.last_pn()
        # If this is the very first part number added use the default for firstpn
        if res is None or res[0] is None:
            pn = firstPn
        else:
            pn = res
        (prefix, suffix) = pn.split('-')
        nextnum = int(prefix) + 1
        pn = '{prefix:06d}-{suffix:03d}'.format(prefix=nextnum, suffix=101)
        return pn

    def body(self, master):
        if self.pnhint != '':
            nextpn = self.pnhint
        else:
            nextpn = self.new_pn()
        self.mfgrs = self.db.get_mfgr_list()
        def_sel = self.mfgrs.index(defaultMfgr)

        Label(master, text='Part Number').grid(row=0, column=0, sticky=W)
        self.pn_entry = Entry(master, width=10)
        self.pn_entry.insert(0, nextpn)
        self.pn_entry.grid(row=0, column=1, sticky=W)

        Label(master, text='Description').grid(row=1, column=0, sticky=W)
        self.desc_entry = Entry(master, width=50)
        if self.deschint is not '':
            self.desc_entry.insert(0, self.deschint)
        self.desc_entry.grid(row=1, column=1, sticky=W)

        Label(master, text='Manufacturer').grid(row=2, column=0, sticky=W)
        self.mfgr_entry = Combobox(master, width=30, values=self.mfgrs)
        self.mfgr_entry.current(def_sel)
        self.mfgr_entry.grid(row=2, column=1, sticky=W)

        Label(master, text='Manufacturer Part Number').grid(row=3, column=0, sticky=W)
        self.mpn_entry = Entry(master, width=30)
        self.mpn_entry.insert(0, defaultMpn)
        self.mpn_entry.grid(row=3, column=1, sticky=W)


    def validate(self):

        # Validate part number
        pn = self.pn_entry.get()
        x = len(pn)
        if x != 10:
            return False
        if pn[6] != '-':
            return False

        # Validate description
        x = len(self.desc_entry.get())
        if x < 5 or x > 50:
            return False

        # Validate manufacturer part number
        x = len(self.mpn_entry.get())
        if x < 3 or x > 30:
            return False

        # Validate manufacturer, and add a new manufacturer if need be
        selected = self.mfgr_entry.get()
        if selected not in self.mfgrs:
            confirm_mfg = AddMfgrDialog(self.parent, new_mfg=selected)
            if confirm_mfg.confirmed() is False:
                return False
            else:
                # Assign a new mid
                mid = self.db.last_mid()
                if mid is not None:
                    mid = int(mid[1:]) + 1
                else:
                    mid = 0
                nextmid = 'M{num:07d}'.format(num=mid)
                # Add manufacturer and MID to manufacturer list
                self.db.add_mfg_to_mlist(selected, nextmid)
                self.mfgrs.append(selected)



        return True

    def apply(self):
        # Retreive all fields
        pn = self.pn_entry.get()
        desc = self.desc_entry.get()
        mfgr = self.mfgr_entry.get()
        mpn = self.mpn_entry.get()

        # Get the mid for the manufacturer name
        res = self.db.lookup_mfg(mfgr)
        if res is None:
            raise SystemError
        mid = res[1]

        # Create the part record and manufacturer part record
        self.db.add_pn(pn, desc, mid, mpn)


#
# Base class for displaying part numbers and manufacturers
#

class DisplayFrame:
    frame = None # Class variable shared between siblings
    def __init__(self, parent, db):
        self.parent = parent
        self.db = db


#
# Class to show manufacturers
#

class ShowManufacturers(DisplayFrame):
    def __init__(self, parent, db):
        DisplayFrame.__init__(self, parent, db)
        self.empopupmenu = Menu(self.parent, tearoff=0)
        self.empopupmenu.add_command(label="Edit Manufacturer...", command=self.edit_mfg)



    def refresh(self):
        """
        Refresh screen with current list entries
        :return: N/A
        """
        if(DisplayFrame.frame is not None):
            DisplayFrame.frame.destroy()
        DisplayFrame.frame = Frame(self.parent)
        self.frame = DisplayFrame.frame
        self.frame.pack(side=TOP, fill=BOTH, expand=Y)
        self.ltree = Treeview(height="26", columns=("Manufacturer"))
        ysb = Scrollbar(orient='vertical', command=self.ltree.yview)
        xsb = Scrollbar(orient='horizontal', command=self.ltree.xview)
        self.ltree.configure(xscroll=xsb.set, yscroll=ysb.set)
        self.ltree.heading('#1', text='Manufacturer', anchor=W)


        self.ltree.column('#1', stretch=YES, minwidth=0, width=200)
        self.ltree.column('#0', stretch=NO, minwidth=0, width=0) #width 0 for special heading
        self.ltree.bind("<Button-3>", self.popup)

        manufacturers = self.db.get_mfgrs()
        for manuf in manufacturers:
            parent_iid = self.ltree.insert("", "end", tag=[manuf,'mfgrec'], values=(manuf[0],))

        # add tree and scrollbars to frame
        self.ltree.grid(in_=self.frame, row=0, column=0, sticky=NSEW)
        ysb.grid(in_=self.frame, row=0, column=1, sticky=NS)
        xsb.grid(in_=self.frame, row=1, column=0, sticky=EW)
        # set frame resizing priorities
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

    def popup(self, event):
        """
        Act on right click
        :param event:
        :return: N/A
        """

        # select row under mouse
        iid = self.ltree.identify_row(event.y)
        self.itemid = iid
        if iid:
            # mouse pointer over item
            self.ltree.selection_set(iid)
            item = self.ltree.item(iid)
            self.itemvalues = item['values']
            self.itemtags = item['tags']
            self.empopupmenu.tk_popup(event.x_root, event.y_root)

    def edit_mfg(self):
        """

        :return: N/A
        """
        title = 'Edit Manufacturer: ' + self.itemvalues[0]
        e = EditManufacturer(self.parent, values=self.itemvalues, db=self.db, title=title)

        self.ltree.item(self.itemid, values=self.itemvalues)

#
# Class to show part list
#

class ShowParts(DisplayFrame):
    def __init__(self, parent, db):
        DisplayFrame.__init__(self, parent, db)
        self.dsdir = general.get('datasheets', None)
        if self.dsdir is not None:
            self.dsdir = os.path.expanduser(self.dsdir)
        self.pdfviewer = general.get('pdfviewer', None)
        # create a popup menu
        self.pnpopupmenu = Menu(self.parent, tearoff=0)
        self.pnpopupmenu.add_command(label="Copy part number to clipboard", command=self.copy_pn)
        self.pnpopupmenu.add_command(label="Edit Description",command=self.edit_description)
        self.pnpopupmenu.add_command(label="Add tabulated part number", command=self.add_tabulated_part)
        self.pnpopupmenu.add_command(label="Add alternate source", command=self.add_alternate_source)


        self.mpnpopupmenu = Menu(self.parent, tearoff=0)
        self.mpnpopupmenu.add_command(label="Copy manufacturer part number to clipboard", command=self.copy_pn)

        self.hdc = self.db.mfg_table_has_datasheet_col()

        self.mpnpopupmenu.add_command(label="Open Data Sheet", command=self.open_data_sheet, state = DISABLED)

        self.mpnpopupmenu.add_command(label="Edit Manufacturer Part Number", command=self.edit_mpn)

        self.mpnpopupmenu.add_command(label="Associate Data Sheet...", command=self.associate_data_sheet, state=DISABLED)


        self.mpnpopupmenu.add_command(label="Remove this source", command=self.remove_source, state=DISABLED)

    def refresh_mpn_processor(self, like):
        """
        Process refresh items  (default)
        :param like: - search string
        :return: N/A
        """
        parts = self.db.lookup_mpn_like(like)

        for row,(pn,mpn) in enumerate(parts):
            res = self.db.lookup_pn(pn)
            desc = res[1]
            parent_iid = self.ltree.insert("", "end", tag=[pn,'partrec'], values=((pn, desc, '', '')))
            self.populate_source_list(pn, parent_iid)
            children = self.ltree.get_children(parent_iid)
            for child in children:
                self.ltree.see(child)


    def refresh_default_processor(self, like):
        """
        Process refresh items  (default)
        :param like: - search string
        :return: N/A
        """
        parts = self.db.get_parts(like)

        for row,(pn,desc) in enumerate(parts):
            mfg = defaultMfgr
            mpn = defaultMpn
            parent_iid = self.ltree.insert("", "end",  tag=[pn,'partrec'], values=((pn, desc, '', '')))
            self.populate_source_list(pn, parent_iid)


    def refresh(self, like=None, processor='DEFAULT'):
        """
        Refresh screen with current list entries
        :param: like - match string
        :param: callback - processing function. Use default if set to None
        :return: N/A
        """
        self.like = like
        if(DisplayFrame.frame is not None):
            DisplayFrame.frame.destroy()
        DisplayFrame.frame = Frame(self.parent)
        self.frame = DisplayFrame.frame
        self.frame.pack(side=TOP, fill=BOTH, expand=Y)
        self.ltree = Treeview(height="26", columns=("Part Number","Description","Manufacturer","Manufacturer Part Number"), selectmode="extended")
        ysb = Scrollbar(orient='vertical', command=self.ltree.yview)
        xsb = Scrollbar(orient='horizontal', command=self.ltree.xview)
        self.ltree.configure(xscroll=xsb.set, yscroll=ysb.set)
        self.ltree.heading('#1', text='Part Number', anchor=W)
        self.ltree.heading('#2', text='Description', anchor=W)
        self.ltree.heading('#3', text='Manufacturer', anchor=W)
        self.ltree.heading('#4', text='Manufacturer Part Number', anchor=W)

        self.ltree.column('#1', stretch=NO, minwidth=0, width=200)
        self.ltree.column('#2', stretch=NO, minwidth=0, width=500)
        self.ltree.column('#3', stretch=NO, minwidth=0, width=300)
        self.ltree.column('#4', stretch=YES, minwidth=0, width=300)
        self.ltree.column('#0', stretch=NO, minwidth=0, width=0) #width 0 for special heading
        self.ltree.bind("<Button-3>", self.popup)


        # Process items to view on screen
        if processor == 'DEFAULT':
            self.refresh_default_processor(like)
        elif processor == 'MPN':
            self.refresh_mpn_processor(like)

        # add tree and scrollbars to frame
        self.ltree.grid(in_=self.frame, row=0, column=0, sticky=NSEW)
        ysb.grid(in_=self.frame, row=0, column=1, sticky=NS)
        xsb.grid(in_=self.frame, row=1, column=0, sticky=EW)
        # set frame resizing priorities
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

    def popup(self, event):
        """
        Act on right click
        :param event:
        :return: N/A
        """

        # select row under mouse
        iid = self.ltree.identify_row(event.y)
        self.itemid = iid
        if iid:
            # mouse pointer over item
            self.ltree.selection_set(iid)
            item = self.ltree.item(iid)
            self.itemvalues = item['values']
            self.itemtags = item['tags']
            if item['tags'][1] == 'partrec':
                # Remember part number
                self.pnpopupmenu.tk_popup(event.x_root, event.y_root)
            elif item['tags'][1] == 'mfgpartrec':
                sources = self.db.lookup_mpn_by_pn(item['tags'][0])

                # Pull datasheet path from database if it is available
                self.datasheet = None
                for source in sources:
                    if source['mpn'] == str(self.itemvalues[3]):
                        self.datasheet = source['datasheet']


                # Enable the datasheet selection if there is a path specified in the config file
                # The datasheet is specified in the manufacturer table,
                # the default manufacturer is not specified, and
                # the path to the pdf viewer is specified in the config file

                if self.hdc is True and self.datasheet is not None \
                        and self.dsdir is not None\
                        and self.pdfviewer is not None\
                        and self.itemvalues[2] != defaultMfgr:
                    self.mpnpopupmenu.entryconfig(1, state=NORMAL)
                else:
                    self.mpnpopupmenu.entryconfig(1, state=DISABLED)

                # If we have the datasheet column
                if self.hdc is True:
                    # Enable if not the default manufacturer
                    if self.itemvalues[2] != defaultMfgr:
                            self.mpnpopupmenu.entryconfig(3, state=NORMAL)
                    else:
                            self.mpnpopupmenu.entryconfig(3, state=DISABLED)

                # If more than one source, then enable the removal of a source
                if len(sources) > 1:
                    self.mpnpopupmenu.entryconfig(4 , state=NORMAL)
                else:
                    self.mpnpopupmenu.entryconfig(4, state=DISABLED)
                self.mpnpopupmenu.tk_popup(event.x_root, event.y_root)

        else:
            # mouse pointer not over item
            # occurs when items do not fill frame
            # no action required
            pass

    def copy_pn(self):
        """
        Copy part number or manufacturer part number to clipboard
        :return: N/A
        """
        if self.itemvalues[0] != '':
            pyperclip.copy(self.itemvalues[0])
        else:
            pyperclip.copy(self.itemvalues[3])

    def edit_description(self):
        """
        Display Dialog box and allow user to edit part description
        :return: N/A
        """
        title = 'Edit Description: ' + self.itemvalues[0]
        e = EditDescription(self.parent, values=self.itemvalues, db=self.db, title=title)

        self.ltree.item(self.itemid, values=self.itemvalues)

    def edit_mpn(self):
        """
        Display Dialog box and allow user to edit the manufacturer part number
        :return: N/A
        """
        title = 'Edit Manufacturer Part Number: ' + str(self.itemvalues[3])
        e = EditMPN(self.parent, values=self.itemvalues, tags=self.itemtags, db=self.db, title=title)

        self.ltree.item(self.itemid, values=self.itemvalues)

    def add_tabulated_part(self):
        """
        Add a tabulated part number with the same prefix as the part number clicked on
        :return: N/A
        """
        pnsplit = self.itemvalues[0].split('-')
        pnhint = pnsplit[0]+'-'
        deschint = self.itemvalues[1]
        a = AddPartDialog(self.parent,title='Add Tabulated Part',db=self.db, pnhint=pnhint, deschint=deschint)

        self.refresh(self.like)

    def populate_source_list(self, pn, itemid):
        """
        Build the list of sources (mfg, mpn)
        :param pn:
        :param itemid:
        :return:
        """
        res = self.db.lookup_mpn_by_pn(pn)

        # If no MFG/MPN, use default

        if res == []:
            res =[{'mname':defaultMfgr,'mpn':defaultMpn}]

        for item in res:
            mfg = item['mname']
            mpn = item['mpn']
            self.ltree.insert(itemid, "end", tag=[pn,'mfgpartrec'], values=(('', '', mfg, mpn)))

    def rebuild_source_list(self, pn, itemid):
        """
        Rebuild the list of children
        :param: parent part number
        :param: parent item id
        """
        children = self.ltree.get_children(itemid)
        self.ltree.delete(children)

        self.populate_source_list(pn, itemid)

    def add_alternate_source(self):
        """
        Display dialog box and allow user to add an alternate manufacturer and MPN
        :return:N/A

        """
        a = AddAlternateSourceDialog(self.parent, pn=self.itemtags[0], db=self.db, title="Add Alternate Source")

        self.rebuild_source_list(self.itemtags[0], self.itemid)

    def remove_source(self):
        """
        Remove a source from the database
        :return: N/A
        """
        mpn = self.itemvalues[3]
        mfg = self.itemvalues[2]
        pn = self.itemtags[0]
        r = RemoveSourceDialog(self.parent, db=self.db, pn=pn, mfg=mfg, mpn=mpn, title="Remove Source")
        self.ltree.delete(self.itemid)


    def open_data_sheet(self):
        """
        Run the pdf viewer to display the datasheet
        :return: N/A
        """
        if self.datasheet[0] == os.pathsep:
            pdfpath = self.datasheet[0] # Path is absolute
        else:
            pdfpath = os.path.join(self.dsdir, self.datasheet) # Path is relative to datasheet directory
        subprocess.Popen((self.pdfviewer, pdfpath))


    def associate_data_sheet(self):
        """
        Associate a datasheet to a manufacturer part number

        :return: N/A
        """
        # Get the path to the datasheet from the user
        path = askopenfilename(parent=root, initialdir=self.dsdir, defaultextension='.pdf', title='Associate Datasheet')
        print(len(path))
        # If something was entered, then store the path in the manufacturer table
        if path is not None and len(path):
            # If it starts with the datasheet directory, remove that from the path name plus the leading separator
            if path.startswith(self.dsdir):
                path = path[len(self.dsdir) + 1:]

            # Get every key needed to do the update
            pn = self.itemtags[0]
            mpn = self.itemvalues[3]
            res = self.db.lookup_mfg_by_pn_mpn(pn, mpn)
            if res is None:
                raise SystemError
            mid = res[1]

            #print(pn, mpn, mid, path)

            # update the path

            self.db.update_datasheet(pn, mid, mpn, path)


#
# Return the next free manufacturer ID
#

def nextFreeMID(db):
    mid = db.last_mid()
    if mid is not None:
        mid = int(mid[1:]) + 1
    else:
        mid = 0
    return 'M{num:07d}'.format(num=mid)


#
# Add a new part number to the database
#

def addPN():
    AddPartDialog(root, db=DB)
    parts.refresh()


def viewPartsLike():
    res = ViewPartsDialog(root)
    selected=res.get_selected()
    parts.refresh(selected)

def viewMPNsLike():
    res = ViewMPNsDialog(root)
    selected = res.get_selected()

    parts.refresh(selected,'MPN')
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

    # Check to see if we can access the database file and that it is writable

    if(os.path.isfile(db) == False):
        print('Error: Database file {} doesn\'t exist'.format(db))
        raise(SystemError)
    if(os.access(db,os.W_OK) == False):
        print('Error: Database file {} is not writable'.format(db))
        raise(SystemError)

    DB = BOMdb(db)

    # Look up default manufacturer

    res = DB.lookup_mfg_by_id(defaultMID)
    if(res is None):
        defaultMfgr = 'Default MFG Error'
    else:
        defaultMfgr = res[0]

    # Set up the TCL add window

    root = Tk()
    root.title("Part Manager")
    app=FullScreenApp(root)

    parts = ShowParts(root, DB)
    manufacturers = ShowManufacturers(root, DB)

    menubar = Menu(root, tearoff = 0)
    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=filemenu)
    # display the menu
    root.config(menu=menubar)

    editmenu = Menu(menubar, tearoff = 0)
    menubar.add_cascade(label="Edit", menu=editmenu)
    editmenu.add_command(label="Add part number...", command=addPN)


    viewmenu = Menu(menubar, tearoff = 0)
    viewmenu.add_command(label="View All Parts", command=parts.refresh)
    viewmenu.add_command(label="View Parts Like...", command=viewPartsLike)
    viewmenu.add_command(label="View View Manufacturer Part Numbers Like...", command=viewMPNsLike)
    viewmenu.add_command(label="View Manufacturers", command=manufacturers.refresh)
    menubar.add_cascade(label="View", menu=viewmenu)


    # display the menu
    root.config(menu=menubar)


    parts.refresh()

    root.mainloop()