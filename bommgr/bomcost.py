
import argparse
import configparser
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


# parse the args and die on error

args = parser.parse_args()

# Read the config file, if any
config = configparser.ConfigParser()

if(args.config is not None):
    configLocation = os.path.expanduser(args.config)
else:
    configLocation = defaultConfigLocations

config.read(configLocation)

# Configure urrllib3 pool

http = urllib3.PoolManager(2)



csv_file = open(args.infile, "r")
csv_reader = csv.DictReader(csv_file)
line_items = []
queries = []
for line_item in csv_reader:
    # Skip line items without part numbers and manufacturers
    if not line_item['Manufacturer Part Number'] or not line_item['Manufacturer']:
        continue
    line_items.append(line_item)
    queries.append({'mpn': line_item['Manufacturer Part Number'],
                    'brand': line_item['Manufacturer'],
                    'reference': len(line_items) - 1})


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
        #print "Did not find match on line item %s" % line_item
        continue

    # Get pricing from the first item for desired quantity
    quantity = Decimal(line_items[result['reference']]['Qty'])
    prices = []
    for offer in result['items'][0]['offers']:
        if 'USD' not in offer['prices'].keys():
            continue
        #print(offer) # DEBUG
        if offer['seller']['name'] != 'Digi-Key' and offer['seller']['name'] != 'Mouser' and offer['seller']['name'] != 'Newark' and offer['seller']['name'] != 'Jameco':
            continue
        if offer['packaging'] == 'Custom Reel':
            continue
        if offer['in_stock_quantity'] == 0:
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
            #print(offer)
            print('MPN: {} QTY: {} SKU: {} VEND: {} PRICE: {} STOCK: {}'.format(result['items'][0]['mpn'], quantity, offer['sku'], offer['seller']['name'], price, offer['in_stock_quantity'] ))
            prices.append(price)

    if len(prices) == 0:
        print("Warning: Did not find pricing on line item {}".format(line_item))
        continue
    avg_price = quantity * sum(prices) / len(prices)
    total_avg_price += avg_price
    hits += 1

print()
print('Matched on {0:.1f}% of BOM, total average price is USD ${1:.2f}'.format((hits / float(len(line_items))) * 100, total_avg_price))
