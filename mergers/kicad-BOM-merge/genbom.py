#!/home/srodgers/.pyenv/versions/3.10.14/bin/python
import os
import sys
import argparse
import configparser

import subprocess

pcb_assembly_house = ""
project_name = ""
project_revision = "Rev_X1"
bin_directory = "/home/srodgers/bin"

bom_raw_csv="bom_raw.csv"
bom_composite_csv = "bom-composite.csv"
bom_assy_csv = "bom-assy.csv"
assy_x_y_csv = "x_y.csv"
mfg_config_file_name = "mfgconfig.conf"

def run_bommerge2(bom_file, merged_csv):
	try:
		subprocess.run([bommerge2_tool, bom_file, merged_csv, "--fill-altsrc-fields"], check=True)
	except subprocess.CalledProcessError:
		sys.exit("bommerge2 failed, exiting...")
		

def run_post_process_jlcpcb(bom_file, jlcpcb_bom_file):
	try: 
		subprocess.run([assy_bom_tool, bom_file, jlcpcb_bom_file], check=True)
	except subprocess.CalledProcessError:
		sys.exit("post_process_jlcpcb failed, exiting...")
	
def run_jlcpcb_cpl_file(jlcpcb_x_y_csv, cpl_csv):
	try: 
		subprocess.run([x_y_file_tool, jlcpcb_x_y_csv, cpl_csv], check=True)
	except subprocess.CalledProcessError:
		sys.exit("post_process_jlcpcb failed, exiting...")


# Read command line arguments

parser = argparse.ArgumentParser(description="Generate BOM's")
parser.add_argument("--tool_directory", help="Specify path to tool directory")
parser.add_argument("--raw-bom", help="Specify kicad raw BOM file name")
parser.add_argument("--composite-output-bom", help="Specify output BOM filename")
parser.add_argument("--assembly_bom", help="Specify file name of assembly house BOM")
parser.add_argument("--x_y_file", help="Specify file name of X-Y file")
parser.add_argument("--config-file", help="Specify path to config file")
parser.add_argument("--working-directory", help="Specify working directory")
args = parser.parse_args()

# get working directory from OS
working_dir = os.getcwd()

# Use specified working directory if it exists
if args.working_directory:
	project_directory = args.working_directory
else:
	# Working directory arg not specified
	# Use working directory from OS
	project_directory = working_dir
	# Create full path to config file using project directory

mfg_config_file_name = project_directory+"/"+mfg_config_file_name


# Override config file location
if args.config_file:
	mfg_config_file_name = args.config_file

# Set up and read config file

config = configparser.RawConfigParser()
if os.path.exists(mfg_config_file_name):
	config.read(mfg_config_file_name)
else:
	sys.exit("Could not open configuration file: {}".format(mfg_config_file_name))

# Get config file settings

# Optional
if(not config["general"]["revision"]):
	print("Using default project revision: {}".format(project_revision))
else:
	project_revision = config["general"]["revision"]

if(not config["general"]["bin_directory"]):
	print("Using default bin directoy of: {}".format(bin_directory))
else:
	bin_directory = config["general"]["bin_directory"]

# Mandatory
	
if(not config["general"]["project_name"]):
	sys.exit("Missing project_name in config file")
else:
	project_name = config["general"]["project_name"]

if(not config["general"]["fab_assembly_house"]):
	sys.exit("Missing fab_assembly_house in config file")
else:
	pcb_assembly_house = config["general"]["fab_assembly_house"]


# Create the paths to the bomtool utilities

if args.tool_directory:
	bin_directory = args.tool_directory

bommerge2_tool = bin_directory + "/" + "bommerge2.py"
assy_bom_tool = bin_directory + "/" + "post-process-jlcpcb.py"
x_y_file_tool = bin_directory + "/" + "jlcpcb-cpl-file.py"

# Create the path to the gerber directory


gerber_dir = project_directory+"/"+project_revision

kicad_x_y_file = project_directory + "/" + project_revision + "/" + project_name + "-all-pos.csv"

# Path overrides from command line

if args.x_y_file: # X/Y output file
	assy_x_y_csv = args.x_y_file
else:
	assy_x_y_csv = project_directory + '/' + assy_x_y_csv

if args.raw_bom: # Raw bom input file
	bom_raw_csv = args.raw_bom
else:
	bom_raw_csv = project_directory + "/" + bom_raw_csv

if args.composite_output_bom:
	bom_composite_csv = args.composite_output_bom
else:
	bom_composite_csv = project_directory + "/" + bom_composite_csv

if args.assembly_bom:
	bom_assy_csv = args.assembly_bom
else:
	bom_assy_csv = project_directory + "/" + bom_assy_csv


# Merge the raw bom with the parts database

run_bommerge2(bom_raw_csv, bom_composite_csv)
print("KiCad raw BOM merged with database")

# Process files for JLCPCB

if pcb_assembly_house == "jlcpcb":
	# Create the jlcpcb netlist
	run_post_process_jlcpcb(bom_composite_csv, bom_assy_csv)
	print("JLCPCB BOM created from merged BOM")

	# Check for X/Y file and if it exists, create the jlcpcb cpl file
	if os.path.exists(kicad_x_y_file):
		run_jlcpcb_cpl_file(kicad_x_y_file, assy_x_y_csv)
		print("JLCPCB CPL file generated")
	else:
		print("Warning: No CPL file generated. Kicad X-Y file missing")

# Unknown assembly house


else:
	sys.exit("Unknown assembly house");





