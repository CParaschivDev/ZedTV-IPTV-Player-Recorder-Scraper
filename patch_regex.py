# Regex Patch
# This script updates the regex pattern in main.py and test_m3u_parser.py

import re
import fileinput
import sys

def update_regex_in_file(filename):
    """Updates the EXTINF_RE regex pattern in a file"""
    print(f"Updating regex in {filename}...")
    
    # Read the file
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update the regex pattern if needed
    if 'EXTINF_RE = re.compile(r\'^#EXTINF[^,;]*[,;](?P<n>.*)$\'' in content:
        content = content.replace(
            'EXTINF_RE = re.compile(r\'^#EXTINF[^,;]*[,;](?P<n>.*)$\'', 
            'EXTINF_RE = re.compile(r\'^#EXTINF[^,;]*[,;](?P<name>.*)$\''
        )
        
        # Write the updated content back to the file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated regex in {filename}")
    else:
        print(f"No regex pattern found to update in {filename}")

# Update both files
update_regex_in_file('main.py')
update_regex_in_file('test_m3u_parser.py')

print("Done!")
