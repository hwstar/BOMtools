__author__ = 'srodgers'
from distutils.core import setup

setup(
    name='bommerge.py',
    version='0.1dev',
    url='https://github.com/hwstar/BOMTools',
    license='GNU GPL Version 3',
    author='srodgers',
    author_email='steve_at_rodgers619_dot_com',
    description='A bill of materials merge utility for Kicad EDA',
    scripts=['bommerge.py'],
    requires=['argparse', 'sqlite3', 'ConfigParser','csv','kicad_netlist_reader']
)