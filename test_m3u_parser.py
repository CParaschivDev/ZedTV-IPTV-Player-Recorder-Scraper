# M3U Parser Tester
# This script tests the M3U parsing functionality in a standalone way

import re

EXTINF_RE = re.compile(r'^#EXTINF[^,;]*[,;](?P<name>.*)$', re.IGNORECASE)
TVGNAME_RE = re.compile(r'tvg-name="([^"]+)"', re.IGNORECASE)
GT_RE = re.compile(r'group-title="([^"]+)"', re.IGNORECASE)
TVGCOUNTRY_RE = re.compile(r'tvg-country="([^"]+)"', re.IGNORECASE)
TVGLOGO_RE = re.compile(r'tvg-logo="([^"]+)"', re.IGNORECASE)

def _clean(s: str) -> str:
    return (s or '').strip().strip('"').strip()

def parse_extinf(line: str) -> dict:
    """
    Returns a dict with best-effort fields from an #EXTINF line.
    Supports:
      - tvg-name="Name"
      - group-title="Group"
      - tvg-country="Country" 
      - tvg-logo="Logo URL"
      - final name after the last comma OR semicolon
    """
    info = {'name': None, 'group': None, 'country': None, 'logo': None}

    # prefer tvg-name if present
    m = TVGNAME_RE.search(line)
    if m:
        info['name'] = _clean(m.group(1))

    # capture group-title if present
    m = GT_RE.search(line)
    if m:
        info['group'] = _clean(m.group(1))
        
    # capture tvg-country if present
    m = TVGCOUNTRY_RE.search(line)
    if m:
        info['country'] = _clean(m.group(1))
        
    # capture tvg-logo if present
    m = TVGLOGO_RE.search(line)
    if m:
        info['logo'] = _clean(m.group(1))

    # fallback: text after last comma/semicolon
    if not info['name']:
        m = EXTINF_RE.search(line)
        if m:
            info['name'] = _clean(m.group('name'))

    return info

# Test cases
test_lines = [
    '#EXTINF:-1 tvg-id="protv.ro" group-title="General",Pro TV',
    '#EXTINF:-1 tvg-id="digi24.ro" tvg-name="Digi 24" tvg-country="RO";Digi24 HD',
    '#EXTINF:-1 tvg-name="Antena 1" tvg-logo="http://example.com/logo.png" group-title="News",Antena 1',
    '#EXTINF:-1,Just a name after comma',
    '#EXTINF:-1;Just a name after semicolon'
]

print("Testing M3U parser functionality:")
print("-" * 50)

for i, line in enumerate(test_lines):
    print(f"Test {i+1}: {line}")
    result = parse_extinf(line)
    print(f"  Name:    {result['name']}")
    print(f"  Group:   {result['group']}")
    print(f"  Country: {result['country']}")
    print(f"  Logo:    {result['logo']}")
    print("-" * 50)

print("Parser test complete.")
