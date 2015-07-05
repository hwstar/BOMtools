from distutils.core import setup

setup(
    name='bommgr',
    version='0.1dev',
    url='https://github.com/hwstar/BOMTools',
    license='GNU GPL Version 3',
    author='srodgers',
    author_email='steve_at_rodgers619_dot_com',
    description='A bill of materials manager to manage electronic parts',
    scripts=['bommgr.py', 'bomcost.py', 'partmgr.py', 'bommdb.py'],
    requires=['argparse', 'sqlite3', 'configparser', 'tkinter', 'tkinter.ttk',
              'csv', 'json', 'urllib3', 'urllib.parse', 'decimal', 'pyperclip']
)
