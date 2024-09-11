__author__ = 'srodgers'
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

import sys
import os
import sqlite3

class BOMdb:
    """
    A class to encapsulate the database operations for bommgr.py
    """
    def __init__(self, dbfile):
        self.conn = sqlite3.connect(dbfile)
        self.cur = self.conn.cursor()

        self.major = 0
        self.minor = 0


        self.cur.execute('SELECT major,minor FROM version')
        res = self.cur.fetchone()
        if res is not None:
            self.major = int(res[0])
            self.minor = int(res[1])

    def _get_conn(self):
        return self.conn

    def _get_cur(self):
        return self.cur

    def get_parts(self, like=None):
        """
        Returns a  sorted list of part numbers and descriptions
        :param like:  Database matching string. Use % as a wild card
        :return: List of part numbers and descriptions
        """

        if like != None:
            self.cur.execute('SELECT Partnumber,Description FROM pndesc WHERE Description LIKE ? ORDER BY PartNumber ASC',[like])
        else:
            self.cur.execute('SELECT Partnumber,Description FROM pndesc ORDER BY PartNumber ASC')
        return self.cur.fetchall()

    def get_pnmpn(self):
        """
        Return entire pnmpn table contents
        :return: List of rows with rows as tuples
        """
        self.cur.execute('SELECT Partnumber,Manufacturer,MPN,Datasheet FROM pnmpn ORDER BY PartNumber ASC')
        return self.cur.fetchall()

    def get_mfgrs(self, like=None):
        """
        Returns a sorted list of manufacturers
        :param like: Database matching string. Use % as a wild card
        :return: List of manufacturer tuples
        """
        if like != None:
            self.cur.execute('SELECT MFGName FROM mlist WHERE MFGName LIKE ? ORDER BY MFGName ASC')
        else:
            self.cur.execute('SELECT MFGName FROM mlist ORDER BY MFGName ASC')
        return self.cur.fetchall()



    def get_mfgr_list(self, like=None):
        """
        A better form of get_mfgrs()
        :param like:
        :return: List of manufacturers
        """
        res = self.get_mfgrs(like)
        mfgrs = []
        for item in res:
            mfgrs.append(item[0])
        return mfgrs

    def get_mid_name_list(self):
        """
        Return a list of dictionary entries ordered by the manufacturer ID (mid).
        :return: List of 2 element dictionaries containing keys mid, and mname
        """
        self.cur.execute('SELECT MFGid,MFGName FROM mlist ORDER BY MFGid ASC')
        rows = self.cur.fetchall()
        res = []
        for row in rows:
            res.append({"mid": row[0], "mname": row[1]})
        return res



    def lookup_pn(self, pn):
        """
        Looks up a description by part number
        :param pn: The part number to look up
        :return: The part number and description if there was a match, else None
        """
        self.cur.execute('SELECT PartNumber,Description FROM pndesc WHERE PartNumber = ?', [pn])
        return self.cur.fetchone()

    def lookup_mfg(self, mfgr):
        """
        Look up a manufacturer by name

        :param  a manufacturer name:
        :return: the Manufacturer name and ID if found else None
        """
        self.cur.execute('SELECT MFGName,MFGId FROM mlist WHERE MFGName = ?', [mfgr])
        return self.cur.fetchone()

    def lookup_mfg_by_id(self, mid):
        """
        Look up a manufacturer by ID
        :param mid: The manufacturer ID to look up
        :return: the manufacturer name and ID if found else None
        """
        self.cur.execute('SELECT MFGName,MFGId FROM mlist WHERE MFGId = ?', [mid])
        return self.cur.fetchone()

    def lookup_mpn(self, mpn):
        """
        Look up a manufacturer part number
        Warning: Use this method to see if an mpn exists anywhere queries only.
        Use lookup_part_by_pn_mpn when changing a manufacturer part record.
        :param mpn: a manufacturer part number
        :return: a tuple containing: (part number, manufacturer name, manufacturer part number, manufacturer ID)
        """

        self.cur.execute('SELECT PartNumber,Manufacturer,MPN FROM pnmpn WHERE MPN = ?', [mpn])
        res = self.cur.fetchone()
        if(res is None):
            return None
        pn = res[0]
        mid = res[1]
        mpn = res[2]

        # Convert Manufacturer ID to name

        res = self.lookup_mfg_by_id(mid)
        if res is not None:
            mname = res[0]
        else:
            raise(ValueError) # Something is messed up in the database

        return (pn, mname, mpn, mid)


    def lookup_mpn_like(self, mpn):
        """
        Look up a manufacturer part number similar to the argument
        Warning: Use this method to see if an mpn exists anywhere queries only.
        Use lookup_part_by_pn_mpn when changing a manufacturer part record.
        :param mpn: a manufacturer part number
        :return: a list of tuples containing: part number, manufacturer part number. Empty list returned if no match
        """

        self.cur.execute('SELECT PartNumber,MPN FROM pnmpn WHERE MPN LIKE ?', [mpn])
        res = self.cur.fetchall()
        return res

    def lookup_part_by_pn_mpn(self, pn, mpn):
        """
        Look up a manufacturer part record by part number and manufacturer part number
        :param mpn: a manufacturer part number
        :return: a tuple containing: (part number, manufacturer name, manufacturer part number, manufacturer ID)
        """

        self.cur.execute('SELECT PartNumber,Manufacturer,MPN FROM pnmpn WHERE PartNumber = ? AND MPN = ?', [pn, mpn])
        res = self.cur.fetchone()
        if(res is None):
            return None
        pn = res[0]
        mid = res[1]
        mpn = res[2]

        # Convert Manufacturer ID to name

        res = self.lookup_mfg_by_id(mid)
        if res is not None:
            mname = res[0]
        else:
            raise(ValueError) # Something is messed up in the database

        return (pn, mname, mpn, mid)

    def lookup_mfg_by_pn_mpn(self, pn, mpn):
        """
        "Look up by part number and  manufacturer part number"
        "param: pn: Part number
        :param mpn: a manufacturer part number
        :return: a tuple containing: (manufacturer name, manufacturer ID)
        """

        self.cur.execute('SELECT Manufacturer FROM pnmpn WHERE PartNumber = ? AND MPN = ?', [pn, mpn])
        res = self.cur.fetchone()
        if(res is None):
            return None
        mid = res[0]


        # Convert Manufacturer ID to name

        res = self.lookup_mfg_by_id(mid)
        if res is not None:
            mname = res[0]
        else:
            raise(ValueError) # Something is messed up in the database

        return (mname, mid)

    def mfg_table_has_datasheet_col(self):
        """
        :return: True if database version supports datasheet column in manufacturing table
        """
        return (self.major + (self.minor >= 1)) > 0


    def lookup_mpn_by_pn(self, pn):
        """
        Returns all valid manufacturers and manufacturer part numbers for a part number specified.

        :param pn: The part number to be queried
        :return: Returns a list of dictionaries containing the manufacturer information for the part number
        Dictionary contents: {pn: Part Number, mid: Manufacturer ID, mpn: Manufacturer Part Number
        mname: Manufacturer Name}

        """

        hdc = self.mfg_table_has_datasheet_col()

        if hdc:
            self.cur.execute('SELECT PartNumber,Manufacturer,MPN,DataSheet FROM pnmpn WHERE PartNumber = ?', [pn])
        else:
            self.cur.execute('SELECT PartNumber,Manufacturer,MPN FROM pnmpn WHERE PartNumber = ?',[pn])

        res = self.cur.fetchall()

        reslist = []
        for item in res:
            if hdc:
                reslist.append({'pn' : item[0],'mid' : item[1], 'mpn' : item[2],'datasheet':item[3]})
            else:
                reslist.append({'pn' : item[0],'mid' : item[1], 'mpn' : item[2],'datasheet':None})

        for i,item in enumerate(reslist):
            # Convert Manufacturer ID to name
            res = self.lookup_mfg_by_id(reslist[i]['mid'])
            if res is not None:
                reslist[i]['mname'] = res[0]
            else:
                raise(ValueError) # Something is messed up in the database

        return reslist

    def last_pn(self):
        """
        Return the highest numbered pn in the database
        :return: Part number
        """
        self.cur.execute('SELECT MAX(PartNumber) from pndesc')
        res = self.cur.fetchone()
        if(res is not None):
            return res[0]
        else:
            return None

    def last_mid(self):
        """
        Return the highest numbered manufacturer ID from the database
        :return: Highest mid

        """
        self.cur.execute('SELECT MAX(MFGId) from mlist')
        res = self.cur.fetchone()
        if(res is not None):
            res = res[0]
        return res

    def add_pn(self, pn, desc, mid, mpn ):
        """
        Add a part number to the database, add corresponding manufacturer part number and manufacturer
        :param pn: Part number
        :param desc: Description
        :param mid: Manufacturer ID
        :param mpn:  Manufacturer part number
        :return: N/A
        """

        # Insert part number and description
        self.cur.execute('INSERT INTO pndesc (PartNumber,Description) VALUES (?,?)', [pn, desc])

        # Insert part number, manufacturer id, and manufactuer part number
        self.cur.execute('INSERT INTO pnmpn (PartNumber,Manufacturer,MPN) VALUES (?,?,?)', [pn, mid, mpn])

        # Save (commit) the changes
        self.conn.commit()

    def add_mpn(self, pn, mid, mpn):
        """
        Add a manufacturer's part number

        :param pn: Part number
        :param mid:  Manufacturer ID
        :param mpn: Manufacturer's part number
        :return: N/A
        """

        self.cur.execute('INSERT INTO pnmpn (PartNumber,Manufacturer,MPN) VALUES (?,?,?)', [pn, mid, mpn])
        self.conn.commit()

    def add_mfg_to_mlist(self, mfg, mid):
        """
        Add a manufacturer to the manufacturer list

        :param mfg:  Manufacturer to add
        :param mid:  Manufacturer ID
        :return: N/A
        """
         # Insert the manufacturer
        self.cur.execute('INSERT INTO mlist (MFGId,MFGName) VALUES (?,?)', [mid, mfg])

        # Save (commit) the changes
        self.conn.commit()

    def update_title(self, pn, title):
        """
        Update the title (description of a part number
        :param pn: Part number
        :param title:  Title/Description
        :return: N/A
        """
        self.cur.execute("DELETE FROM pndesc WHERE PartNumber=?",[pn])
        self.cur.execute('INSERT INTO pndesc (PartNumber,Description) VALUES (?,?)', [pn, title])
        # Save (commit) the changes
        self.conn.commit()

    def update_mfg(self,mid, newname):
        """
        Update manufacturer name for a given manufacturer ID

        :param mid: Manufacturer ID
        :param newname: New manufacturer name
        :return: N/A
        """
        self.cur.execute('DELETE FROM mlist WHERE MFGId=?',[mid])
        self.cur.execute('INSERT INTO mlist (MFGName,MFGId) VALUES (?,?)', [newname, mid])
        # Save (commit) the changes
        self.conn.commit()

    def update_mpn(self, pn, curmpn, newmpn, mid):
        """
        Update a manufacturer part number for a given part number/manufacturer part number combination.

        :param pn: Affected part number
        :param mpn: Affected manufacturer part number
        :param mid: New manufacturer ID
        :return:
        """
        self.cur.execute('DELETE FROM pnmpn WHERE PartNumber=? AND MPN=? ', [pn, curmpn])
        self.cur.execute('INSERT INTO pnmpn (PartNumber,Manufacturer,MPN) VALUES (?,?,?)',[pn, mid, newmpn])
        self.conn.commit()

    def update_datasheet(self, pn, mid, mpn, datasheet):
        """
        Update a datasheet for a given part number/mid/manufacturer part number combination.

        :param pn: Affected part number
        :param mid: Manufacturer ID
        :param mpn: Affected manufacturer part number
        :param datasheet: Path to datasheet file
        :return:
        """
        self.cur.execute('DELETE FROM pnmpn WHERE PartNumber=? AND Manufacturer=? AND MPN=? ', [pn, mid, mpn])
        self.cur.execute('INSERT INTO pnmpn (PartNumber,Manufacturer,MPN,DataSheet) VALUES (?,?,?,?)',[pn, mid, mpn, datasheet])
        self.conn.commit()


    def update_mid(self, pn, mpn, oldmid, newmid):
        """
        Update a manufacturer ID for a given part number/manufacturer part number combination.

        :param pn: Affected part number
        :param mpn: Affected manufacturer part number
        :param mid: New manufacturer ID
        :return:
        """
        self.cur.execute('DELETE FROM pnmpn WHERE PartNumber=? AND MPN=? AND Manufacturer=? ', [pn, mpn, oldmid])
        self.cur.execute('INSERT INTO pnmpn (PartNumber,Manufacturer,MPN) VALUES (?,?,?)',[pn, newmid, mpn])
        self.conn.commit()

    def remove_mid(self, mid):
        """
        Remove a manufacturer ID from the MFGid table.

        :param mid - manufacturer ID to remove
        :return: Nothing
        """
        self.cur.execute('DELETE FROM mlist WHERE MFGid=?', [mid])
        self.conn.commit()


    def remove_source(self, pn, mfgid, mpn):
        """
        Remove a source from the pnmpn table.
        Requires a match on part number, manufacturer ID, and manufacturer's part number

        :param pn: Part number
        :param mfgid Manufacturer ID
        :param mpn: Manufacturer's part number
        :return: N/A
        """
        self.cur.execute('DELETE FROM pnmpn WHERE PartNumber=? AND Manufacturer=? AND MPN=? ', [pn, mfgid, mpn])
        self.conn.commit()

    def remove_pnmpn_record(self, part_number):
        """
        Remove a part number to manufacturer number record

        :param part_number:
        :return: N/A
        """
        self.cur.execute("DELETE FROM pnmpn WHERE PartNumber=? ",[part_number])
        self.conn.commit()


    def remove_part_number(self, pn, dryrun = True, annotate=False):
        """
        Remove a part number from the pndesc table
        Requires an explicit match on the part number

        The approved manufacturer(s) will be removed from the pnmpn table, then the part number will be
        removed from the pndesc table.

        Return True if the part number was found and deleted.

        """
        if not self.lookup_pn(pn):
            if annotate:
                print("Part number: {} not found".format(pn))
                return False

        mfgrs = self.lookup_mpn_by_pn(pn)

        if mfgrs:
            # Remove all references to manufacturers
            for mfgr in mfgrs:
                mrec = self.lookup_mfg_by_id(mfgr["mid"])
                # Do not remove Open Market manufacturer records
                # Skip if there is no manufacturer record
                if not mrec or mrec[0] == "Open Market" or mrec[0] == "None":
                    if annotate:
                        if mrec:
                            print("Skipping mpn deletion due to Open Market/None manufacturer")
                        else:
                            print("Skipping mpn deletion due to manufacturer not found")
                        continue
                if annotate:
                    print("Delete mpn: {}".format(mfgr["mpn"]))
                if not dryrun:
                    self.remove_source(pn, mfgr["mid"], mfgr["mpn"])

            if annotate:
                print("Delete Part Number: {}".format(pn))
            if not dryrun:
                # Delete pndesc record(s)
                self.cur.execute('DELETE FROM pndesc WHERE PartNumber=?', [pn])
                self.conn.commit()
                # Delete pnmpn record
                self.cur.execute('DELETE FROM pnmpn WHERE PartNumber=?', [pn])
                self.conn.commit()
        return True



if __name__ == '__main__':
    print ("Database support module for BOMTools, not meant to be run on its own")
    exit(1)