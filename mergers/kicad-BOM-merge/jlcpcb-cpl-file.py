#!/usr/bin/env python3
import csv
import argparse

# Rewrite the first line of the pick and place file so JLCPCB reads it without error

parser = argparse.ArgumentParser(description = 'CPL file post processor for JLCPCB assembly services', prog = 'post-process-jlcpcb.py')
parser.add_argument('infile',help='bommerge.py csv input file')
parser.add_argument('outfile',help='JLCPCB csv output file')

# parse the args and die on error
args = parser.parse_args()

inputFileName = args.infile
outputFileName = args.outfile

with open(inputFileName, 'r') as inFile, open(outputFileName, 'w') as outfile:
    r = csv.reader(inFile)
    w = csv.writer(outfile)

    next(r, None)  # skip the first row from the reader, the old header
    # write new header
    w.writerow(['Designator', 'Val', 'Package', 'Mid X', 'Mid Y', 'Rotation', 'Layer'])

    # copy the rest
    for row in r:
        w.writerow(row)