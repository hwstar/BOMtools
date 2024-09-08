#!/usr/bin/env python3
#
# Convert csv output from bommerge.py into the format that JLCPCB wants to see.
# This program looks at the BOM line-by-line and copies the rows where the
# manufacturer is set to LCSC. It then writes out another .csv file in
# the format that JLCPCB expects.
#
# There is a simple consistency checker which counts the number of BOM items
# and compares it to the number of rows where LCSC was seen as a manufacturer.
# A warning is printed if there is any difference in the two values.
#
# For this program to work correctly, the switch --fill-altsrc-fields must be specified
# when bommerge.py is run.
#


import sys
import csv
import argparse
import re

#
# Choose the first LCSC part in a comma separated list of LCSC part numbers.
# JLCPCB assembly throws out the part if there are commas in the part number.
# Components with commas in the input BOM will typically have the fist part number as a basic component.
#

def choose_first_lcsc_part_number(part_number_str):
    if "," in part_number_str:
        lcsc_pn = part_number_str.split(",")[0]
    else:
        lcsc_pn = part_number_str
    return lcsc_pn



#
# Expand a reference designator list with dashes to a list containing only commas
#
def expand_reference_designators(input_string):
    expanded_list = list()

    if "-" not in input_string:
        return input_string


    raw_item_list = input_string.split(",")



    for refdes in raw_item_list:
        if "-" in refdes:
            startstop_refdes = refdes.split('-')
            start_refdes = startstop_refdes[0]
            stop_refdes = startstop_refdes[1]



            ms = re.match(r"([a-z]+)([0-9]+)", start_refdes, re.I)
            if ms:
                msps = ms.groups()
            else:
                raise(ValueError("Malformed starting reference designator"))
            me = re.match(r"([a-z]+)([0-9]+)", stop_refdes, re.I)
            if me:
                meps = me.groups()
            else:
                raise(ValueError("Malformed ending reference designator"))

            if msps[0] != meps[0]:
                raise(ValueError("Starting and ending references designator prefixes don't match"))


            for i in range(int(msps[1]), int(meps[1]) + 1):
                expanded_list.append(msps[0] + str(i))
        else:
            expanded_list.append(refdes)

    expanded_str = ','.join(expanded_list)
    return expanded_str


parser = argparse.ArgumentParser(description = 'BOM post processor for JLCPCB assembly services', prog = 'post-process-jlcpcb.py')
parser.add_argument('infile',help='bommerge.py csv input file')
parser.add_argument('outfile',help='JLCPCB csv output file')

# parse the args and die on error
args = parser.parse_args()

infile = args.infile
outfile = args.outfile

output_data = list()
input_list = list()

#
# Read in the bommerge.py .csv file
#

with open(infile, newline='') as csvfile:
    input_csv_contents = csv.DictReader(csvfile)

    #
    # Convert object to list of dicts
    #

    for row in input_csv_contents:
        input_list.append(row)

#
# Check consistency. Ensure that there is a LCSC part number field
# for each item in input_csv_contents
#


# Group alternate sources

current_item = -1
lcsc_found = False
mfg_list = []
alternate_sources = []

for item in input_list:
    new_item_number = int(item["Item"])
    if new_item_number != current_item:
        if current_item != -1:
            mfg_list.append(alternate_sources)
            alternate_sources = []
        current_item = new_item_number
    alternate_sources.append(item)

mfg_list.append(alternate_sources)

# Check alternate sources for presence of LCSC manufacturer

missing_lcsc_part_numbers = False
for item in mfg_list:
    found = False
    for alt_source_index in range(0, len(item)):
        if ((item[alt_source_index]["Manufacturer"] == "LCSC" and
             item[alt_source_index]["Manufacturer Part Number"].startswith("C"))
                or int(item[alt_source_index]['Qty']) == 0):
            found = True
    if not found:
        missing_lcsc_part_numbers = True
        print("Error: No LCSC part number found for item: {}, part number {}".format(int(item[0]["Item"]), item[0]["Part Number"]))

if missing_lcsc_part_numbers:
    sys.exit("Exiting due to missing LCSC part numbers")

#
# Convert to JLCPCB format
#

for row in input_list:
    if row['Manufacturer'] == "LCSC":
        refdes_expanded = expand_reference_designators(row["Reference(s)"])
        output_data.append({"Comment": row["Title/Description"],
                            "Designator": refdes_expanded,
                            "Footprint": row["Footprint"],
                            "JLCPCB Part #": choose_first_lcsc_part_number(row["Manufacturer Part Number"])})
#
# Generate the output file
#

with open(outfile, 'w', newline='') as csvoutfile:
    fieldnames =["Comment", "Designator", "Footprint", "JLCPCB Part #"]
    writer = csv.DictWriter(csvoutfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in output_data:
        writer.writerow(row)

# Done
print("Conversion to LCSC format complete")
sys.exit(0)





