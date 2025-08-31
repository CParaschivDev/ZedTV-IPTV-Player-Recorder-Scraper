#!/usr/bin/env python3
"""
Test script to verify the PySimpleGUI compatibility layer works correctly.
This will test both the presence of v4 and v5 APIs through our compatibility layer.
"""

print("Testing PySimpleGUI compatibility layer...")

# Import through our compatibility layer
from psgcompat import sg

# Test for basic sg presence
print(f"PySimpleGUI version: {sg.__version__} ({sg.__file__})")

# Test v4/v5 API components
api_tests = [
    "InputText", "Input", "Button", "SimpleButton", "Submit", "OK", "Cancel"
]

for api in api_tests:
    if hasattr(sg, api):
        print(f"✓ sg.{api} exists")
    else:
        print(f"✗ sg.{api} missing")

# Create a simple test window using v4 style APIs
print("\nCreating test window with v4 style APIs...")
layout = [
    [sg.Text("This is a test window using compatibility layer")],
    [sg.InputText("Test input", key="-INPUT-")],
    [sg.Submit(), sg.Cancel()]
]

window = sg.Window("Compatibility Test", layout, finalize=True)
print("Window created successfully!")

print("\nClose the window to exit test.")
while True:
    event, values = window.read(timeout=100)
    if event in (sg.WIN_CLOSED, "Cancel"):
        break

window.close()
print("Test completed successfully!")
