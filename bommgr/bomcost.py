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
import sys
import os
import csv
import json
import urllib3
import urllib.parse
from decimal import Decimal

defaultConfigLocations = ['/etc/bommgr/bommgr.conf','~/.bommgr/bommgr.conf','bommgr.conf']

# Customize default configurations to user's home directory

for i in range(0, len(defaultConfigLocations)):
    defaultConfigLocations[i] = os.path.expanduser(defaultConfigLocations[i])


parser = argparse.ArgumentParser(description = 'BOM Costing Utility', prog = 'bomcost.py')
parser.add_argument('infile', help="input: BOM file in .csv format")
parser.add_argument('outfile', help="output: Costed BOM file in .csv format")
parser.add_argument('--config', help='Specify config file path', default=None)
parser.add_argument('--debug', help='Debug level (0-5)', default='0')


# parse the args and die on error

args = parser.parse_args()

# Convert debug level to number
debug = int(args.debug)

# Read the config file, if any
config = configparser.ConfigParser()

if(args.config is not None):
    configLocation = os.path.expanduser(args.config)
else:
    configLocation = defaultConfigLocations

config.read(configLocation)

# Sanity check the config file

try:
    general = config['general']
except KeyError:
    print('Error: no config file found or it is missing [general] section')
    sys.exit(2)

try:
    bomcost = config['bomcost']
except KeyError:
    print('Error: no [bomcost] section in config file')
    sys.exit(2)

# Retrieve approved sellers
sellers = [x.strip() for x in bomcost.get('sellers', '').split(',')]

# Retrieve excluded packaging
excluded_packaging = [x.strip() for x in bomcost.get('excluded-packaging', '').split(',')]

# Receive the currency we want pricing to be in
currency = bomcost.get('currency','USD')

# Configure urrllib3 pool
http = urllib3.PoolManager(2)


# Open the non-costed BOM .csv file for processing
csv_file = open(args.infile, "r")
csv_reader = csv.DictReader(csv_file)

# Open a file to write the costed bom to, if the file cannot be opened print error and exit
try:
    outputfile = open(args.outfile, 'w')
except IOError:
    print("Can't open output file for writing: " + args.outfile)
    sys.exit(2)


# Create a new csv writer object to use as the output formatter
out = csv.writer( outputfile, lineterminator='\n', delimiter=',', quotechar='\"', quoting=csv.QUOTE_MINIMAL )

# Columns to print on first list of output file
output_columns = ['Item', 'Part Number', 'Qty', 'Reference(s)', 'Title/Description', 'Value on Schematic', 'Manufacturer',
           'Manufacturer Part Number','Vendor', 'Vendor SKU', 'Stock','Unit Cost','Ext Cost']

# Write column header to output file
out.writerow( output_columns )     # write column header

line_items = []
queries = []
for line_item in csv_reader:
    # Skip line items without part numbers and manufacturers
    if not line_item['Manufacturer Part Number'] or not line_item['Manufacturer']:
        continue
    # Add it to the list
    line_items.append(line_item)
    # Add it to the query
    queries.append({'mpn': line_item['Manufacturer Part Number'],
                    'brand': line_item['Manufacturer'],
                    'reference': len(line_items) - 1}) # reference id to match up to input list later

# Send queries

results = []
for i in range(0, len(queries), 20):
    # Batch queries in groups of 20, query limit of
    # parts match endpoint
    batched_queries = queries[i: i + 20]

    url = 'http://octopart.com/api/v3/parts/match?queries={}'.format(urllib.parse.quote(json.dumps(batched_queries)))
    url += '&apikey=16d032b7'
    #data = urllib3.urlopen(url).read()
    r = http.request('GET', url)
    response = json.loads(r.data.decode('utf-8'))

    # Record results for analysis
    results.extend(response['results'])


# Analyze results sent back by Octopart API


print("Found {} line items in BOM.".format(len(line_items)))
# Price BOM
hits = 0
total_avg_price = 0
for result in results:
    line_item = line_items[result['reference']]
    if len(result['items']) == 0:
        if(debug > 2):
            print("Did not find match on line item %s" % line_item)
        continue

    # Get pricing from the first item for desired quantity
    quantity = Decimal(line_items[result['reference']]['Qty'])
    prices = []
    for offer in result['items'][0]['offers']:
        #Exclude offers without pricing
        if currency not in offer['prices'].keys():
            continue
        #Exclude sellers not in the sellers list
        if offer['seller']['name'] not in sellers:
            continue
        # Exclude any parts in undesired packaging
        if offer['packaging'] in excluded_packaging:
            continue
        # Exclude offers with no stock
        if offer['in_stock_quantity'] <= 0:
            continue
        price = None
        for price_tuple in offer['prices']['USD']:
            # Find correct price break
            if price_tuple[0] > quantity:
                break
            # Cast pricing string to Decimal for precision
            # calculations
            price = Decimal(price_tuple[1])
        if price is not None:
            if(debug > 1):
                print('MPN: {} QTY: {} SKU: {} VEND: {} PRICE: {} STOCK: {}'.format(result['items'][0]['mpn'], quantity, offer['sku'], offer['seller']['name'], price, offer['in_stock_quantity'] ))
            prices.append(price)
            index = result['reference']
            output_row = line_items[index]
            output_row['Vendor'] = offer['seller']['name']
            output_row['Vendor SKU'] = offer['sku']
            output_row['Stock'] = offer['in_stock_quantity']
            output_row['Unit Cost'] = price
            output_row['Ext Cost'] = price * Decimal(line_items[index]['Qty'])
            row = []
            for item in output_columns:
                row.append(output_row[item])   # Append column
            out.writerow(row)

    if len(prices) == 0:
        if(debug > 1):
            print("Warning: Did not find pricing on line item {}".format(line_item))
        continue
    avg_price = quantity * sum(prices) / len(prices)
    total_avg_price += avg_price
    hits += 1

print()
print('Matched on {0:.1f}% of BOM, total average price is USD ${1:.2f}'.format((hits / float(len(line_items))) * 100, total_avg_price))
