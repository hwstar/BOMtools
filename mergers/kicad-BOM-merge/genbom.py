#!/home/srodgers/.pyenv/versions/3.10.14/bin/python
import os
import sys
import configparser

import subprocess

pcb_assembly_house = ""
project_name = ""
project_revision = "Rev_X1"
bin_directory = "/home/srodgers/bin"

bom_raw_csv="bom_raw.csv"
bom_merged_csv = "bom.csv"
bom_jlcpcb_csv = "bom-jlcpcb.csv"
cpl_jlcpcb_csv = "cpl-jlcpcb.csv"
mfg_config_file_name = "mfgconfig.conf"

def run_bommerge2(bom_file, merged_csv):
	try:
		subprocess.run([bommerge2, bom_file, merged_csv, "--fill-altsrc-fields"], check=True)
	except subprocess.CalledProcessError:
		sys.exit("bommerge2 failed, exiting...")
		

def run_post_process_jlcpcb(bom_file, jlcpcb_bom_file):
	try: 
		subprocess.run([post_process_jlcpcb, bom_file, jlcpcb_bom_file], check=True)
	except subprocess.CalledProcessError:
		sys.exit("post_process_jlcpcb failed, exiting...")
	
def run_jlcpcb_cpl_file(jlcpcb_x_y_csv, cpl_csv):
	try: 
		subprocess.run([jlcpcb_cpl_file, jlcpcb_x_y_csv, cpl_csv], check=True)
	except subprocess.CalledProcessError:
		sys.exit("post_process_jlcpcb failed, exiting...")

# get working directory from OS
working_dir = os.getcwd()
print("Working directory: {}".format(working_dir))

# Set up and read config file

config = configparser.RawConfigParser()
if os.path.exists(mfg_config_file_name):
	config.read(mfg_config_file_name)
else:
	sys.exit("Could not open configuration file: {}".format(mfg_config_file_name))
#	
# Get config file settings
#

# Optional
if(not config["general"]["revision"]):
	printf("Using default project revision: {}".format(revision))
else:
	project_revision = config["general"]["revision"]

if(not config["general"]["bin_directory"]):
	printf("Using default bin directoy of: {}".format(bin_directory))
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



# Use specified working directory if it exists
project_directory = working_dir	

	
#	
# Create the paths to the bomtool utilities
#
bommerge2 = bin_directory+"/"+"bommerge2.py"
post_process_jlcpcb = bin_directory+"/"+"post-process-jlcpcb.py"
jlcpcb_cpl_file = bin_directory+"/"+"jlcpcb-cpl-file.py"


#
# Create the path to the gerber directory
#
gerber_dir = project_directory+"/"+project_revision
#
# Create the path to the X/Y file
#
x_y_file = project_directory+"/"+project_revision+"/"+project_name+"-all-pos.csv"

#	
# Merge the raw bom with the parts database
#
run_bommerge2(bom_raw_csv, bom_merged_csv)
print("KiCad raw BOM merged with database")
#
# Process files for JLCPCB
#
if pcb_assembly_house == "jlcpcb":
	# Create the jlcpcb netlist
	run_post_process_jlcpcb(bom_merged_csv, bom_jlcpcb_csv)
	print("JLCPCB BOM created from merged BOM")

	# Check for X/Y file and if it exists, create the jlcpcb cpl file
	if os.path.exists(x_y_file):
		run_jlcpcb_cpl_file(x_y_file, cpl_jlcpcb_csv)
		print("JLCPCB CPL file generated")
	else:
		print("Warning: No CPL file generated. X-Y file missing") 
#
# Unknown assembly house
#	
else:
	sys.exit("Unknown assembly house");





