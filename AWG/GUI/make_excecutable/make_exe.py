NAME = "AWG"
ONE_FILE = True

import subprocess
import sys
import platform  # Add this import to detect the OS
import os

#move up a dir becouse we are in /make_excecutable
print(os.getcwd())
if not os.getcwd().endswith("make_excecutable"):
    print("must be run from \"/make_excecutable\" folder")
    exit()
os.chdir('..')

#check_and_install_pyinstaller
try:
    subprocess.check_output(['pyinstaller', '--version'])
except FileNotFoundError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

#generic arguments
cmd = ['pyinstaller']
cmd.extend(['--workpath', "bin/build_garbage"])
cmd.extend(['--name', NAME])
cmd.extend(['--add-data', "icon/:icon/"])

#One file or not?
if ONE_FILE:
    cmd.append('--onefile')
else:
    cmd.extend(['-y'])

hidden_imports = []

#OS specific arguments
os_name = platform.system().lower()
print("Running on: ", os_name)
if os_name == "linux":  #LINUX
    cmd.extend(['--distpath', "bin/linux"])
    cmd.extend(['--strip'])
elif os_name == "windows":  #WINDOWS
    cmd.extend(['--distpath', "bin/windows"])
    cmd.extend(['--icon', "icon/icon.ico"])
    cmd.extend(['--hide-console', "hide-late"])
elif os_name == "darwin":   #MACOS
    cmd.extend(['--distpath', "bin/macos"])
    cmd.append('--windowed')
    hidden_imports = ['numpy', 'pyserial', 'PyQt6', 'pyqtgraph']
else:
    print("unknown system")
    exit()

#hidden imports
for hidden_import in hidden_imports:
    cmd.extend(['--hidden-import', hidden_import])

#main file
cmd.append("main.py")

print("command: ", str(cmd))

#excecute
result = subprocess.run(cmd, capture_output=True, text=True)

if result.stdout:
    print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)

if result.returncode == 0:
    print("Packaging successful!")
else:
    print("Packaging failed!")
    
#clean up spec file
os.remove(NAME + ".spec")