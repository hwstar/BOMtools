#!/usr/bin/env python3
import os
import sys
import argparse
import configparser
import click
import bommdb

defaultConfigLocations = ['/etc/bommgr/bommgr.conf', '~/.bommgr/bommgr.conf', 'bommgr.conf']




def make_manuf_use_list():
    """
    Create manufacturer use list
    :return: a list of dictionaries with  mid, mname, and reference_count keys for each item in the list.
    """
    mlist = db.get_mid_name_list()
    for item in mlist:
        item["reference_count"] = 0
    return mlist

def get_parts_flagged_for_deletion():
    """
    Return a list of parts flagged for deletion.
    If the manufacturer description field contains the word "REMOVE"
    then it is added to the list of part numbers to be deleted.

    :return: a list of part numbers to remove
    """
    parts = db.get_parts()

    parts_to_remove = []
    for part in parts:
        if "REMOVE" in part[1]:
            parts_to_remove.append(part[0])

    return parts_to_remove


def remove_flagged_parts():
    """
    Remove part numbers flagged for deletion
    Remove any manufacturer records first, then
    remove the part number record

    :return: None
    """
    parts_to_remove = get_parts_flagged_for_deletion()

    if parts_to_remove:
        print("Parts to remove:")
        for part in parts_to_remove:
            print(part)
    else:
        print("No parts to remove")
        return

    for pn in parts_to_remove:
        db.remove_part_number(pn, dryrun=False, annotate=True)

    print("Parts removed")

def check(fix = False, remove_deleted_pns=False, noprompt=False, test=False):
    pnmpn = db.get_pnmpn()

    # Look for parts flagged for deletion
    print()
    print("*** Check ***")
    print()
    print("Phase 1: Part numbers flagged for deletion")
    to_be_deleted = get_parts_flagged_for_deletion()

    if to_be_deleted:
        for item, pn in enumerate(to_be_deleted):
            print(f'{item:>5d}. {pn}')
        if remove_deleted_pns:
            yes = False
            if not noprompt:
                if click.confirm("Delete unused part numbers"):
                    yes = True
            else:
                yes = True

            if yes:
                for pn in to_be_deleted:
                    db.remove_part_number(pn, dryrun=False, annotate=True)
    else:
        print("No part numbers flagged for deletion")

    print()

    print ("Phase 2: Look for invalid Manufacturer ID references")

    index = 1
    invalid_manufacturer_ids = []
    for item in pnmpn:
        mfgr = db.lookup_mfg_by_id(item[1])
        if not mfgr[0]:
            invalid_manufacturer_ids.append({"mpn": item[0], "mid": item[1], "pn":item[2], "mname":mfgr[0]})
            print(f'{index:>5d}. {invalid_manufacturer_ids[-1]["mid"]:<10s} {invalid_manufacturer_ids[-1]["mname"]:<60s}')
            index = index + 1

    if test:
        invalid_manufacturer_ids = []
        # Bogus record for testing
        invalid_manufacturer_ids.append({"mpn": "3T592", "mid": "M99999", "pn": "999999-101", "mname": "Widget co."})
    if not invalid_manufacturer_ids:
        print("No invalid manufacturer id's found")
    else:
        yes = False
        if fix:
            if not noprompt:
                if click.confirm("Delete invalid manufacturer ID references"):
                    yes = True
            else:
                yes = True
        if yes:
            for iid in invalid_manufacturer_ids:
                db.remove_source(iid["pn"], iid["mid"], iid["mpn"])
    print()

    # Look for unused MID's
    print("Phase 3: Look for unused Manufacturer ID's")

    manuf_use_list = make_manuf_use_list()

    mids_to_delete = []

    for item in pnmpn:
        for row in manuf_use_list:
            if row["mid"] == item[1]:
                row["reference_count"] = row["reference_count"] + 1
    index = 1
    for row in manuf_use_list:
        if not row["reference_count"]:
            mfgr = db.lookup_mfg_by_id(row["mid"])
            mids_to_delete.append(row["mid"])
            print(f'{index:>5d}. {row["mid"]:<10s} {mfgr[0]:<60s}')
            index = index + 1

    if not mids_to_delete:
        print("No unused manufacturer ID's found")
    else:
        if fix:
            yes = False
            if fix:
                if not noprompt:
                    if click.confirm("Delete unused manufacturer ID references"):
                        yes = True
                else:
                    yes = True
            if yes:
                for mid in mids_to_delete:
                    db.remove_mid(mid)
                print("Unused manufacturer ID's removed")


if __name__ == '__main__':

    # Command line arguments
    parser = argparse.ArgumentParser(description = "BOM Maintenance Utility", prog = "btmaintutil.py")
    parser.add_argument("--config", help="Specify config file path", default=None)
    parser.add_argument("--fix", help="Fix database inconsistencies", action="store_true")
    parser.add_argument("--remove-deleted-pns", help="Remove part numbers marked for deletion", action="store_true")
    parser.add_argument("--noprompt", help="Don't prompt during fix or part number deletion", action="store_true")

    ## Customize default configurations to user's home directory

    for i in range(0, len(defaultConfigLocations)):
        defaultConfigLocations[i] = os.path.expanduser(defaultConfigLocations[i])

    # parse the args and die on error

    args = parser.parse_args()

    if args.config:
        configLocation = os.path.expanduser(args.config)
    else:
        configLocation = defaultConfigLocations

    # Read the config file to get the path to the DB

    config = configparser.ConfigParser()

    config.read(configLocation)

    if not config.has_option("general", "db"):
        sys.exit("Config file missing, general section missing, or missing db item in general section")

    dbpath = os.path.expanduser(config["general"]["db"])
    # Check to see te DB file exists
    if not os.path.exists(dbpath):
        sys.exit("DB file: {} does not exist".format(dbpath))
    # Make connection to db
    db = bommdb.BOMdb(dbpath)


    check(fix=args.fix, remove_deleted_pns=args.remove_deleted_pns,  noprompt=args.noprompt)


