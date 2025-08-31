@echo off
echo Installing required packages...
pip install -r requirements.txt

echo Building executable with PyInstaller...
pyinstaller -F -w main.py -n ZEDTV --add-data "lib;lib"

echo Build complete. Executable is in the dist folder.
