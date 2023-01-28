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
import pprint


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
# Check consistency. Ensure that there is a JLC part number field
# for each item in input_csv_contents
#

lcsc_count = 0
last_item = 0

for item in input_list:
    # Count an item with an LCSC part number
    if item["Manufacturer"] == "LCSC":
        lcsc_count = lcsc_count + 1
    # Remember the last item processed so that we can compare with the number of LCSC sources we found in the BOM
    last_item = int(item["Item"])

if lcsc_count != last_item:
    print("Warning: {} items missing LCSC alternate sources!".format(last_item - lcsc_count))
#
# Convert to JLCPCB format
#

for row in input_list:
    if row['Manufacturer'] == "LCSC":
        output_data.append({"Comment": row["Title/Description"], "Designator": row["Reference(s)"], "Footprint": row["Footprint"], "JLCPCB Part #": row["Manufacturer Part Number"]})
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





