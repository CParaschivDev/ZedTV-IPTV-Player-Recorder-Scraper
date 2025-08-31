import asyncio
import ctypes
import json
import logging
import os.path
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from sys import platform as platform
from typing import List, Optional
import programs
import requests
from pydantic import BaseModel

# Import PySimpleGUI through our compatibility layer
from psgcompat import sg

import player

if not os.path.isdir("records"):
    os.mkdir("records")
    
# Default icon
icon = None

def get_config_path():
    if platform == "win32":
        return os.path.join(os.environ['USERPROFILE'], '.zedtv', 'config.json')
    else:
        return os.path.expanduser('~/.zedtv/config.json')

def get_log_path():
    if platform == "win32":
        return os.path.join(os.environ['LOCALAPPDATA'], 'ZEDTV', 'zedtv.log')
    else:
        return os.path.join(os.path.expanduser('~'), '.zedtv', 'zedtv.log')

class IpModel(BaseModel):
    ip: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    loc: Optional[str] = None
    org: Optional[str] = None
    postal: Optional[str] = None
    timezone: Optional[str] = None

DEFAULT_CFG = {"default_country": "RO", "geo_detection": True, "playlist_last_path": ""}

def load_config() -> dict:
    path = get_config_path()
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        save_config(DEFAULT_CFG)
        return None
    return DEFAULT_CFG

def save_config(cfg: dict) -> None:
    path = get_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(cfg, f)

window = None  # This will be set when the GUI is initialized

def get_country_safe(cfg: dict) -> str:
    if not cfg.get("geo_detection", True):
        return cfg.get("default_country", "RO").upper()
    try:
        r = requests.get("https://ipinfo.io/json", timeout=5)
        if r.ok:
            data = r.json()
            country = (data.get("country") or cfg.get("default_country", "RO")).upper()
            return country
    except Exception as e:
        logging.warning(f"Geo-IP failed: {e}")
        if 'status' in window:
            window['status'].update("Geo-IP failed, using default country: RO")
        pass
    return cfg.get("default_country", "RO").upper()

@dataclass
class Channel:
    name: str
    url: str
    logo: str = ""
    tvg_country: str = ""
    group_title: str = ""

import re

EXTINF_RE = re.compile(r'^#EXTINF[^,;]*[,;](?P<name>.*)$', re.IGNORECASE)
TVGNAME_RE = re.compile(r'tvg-name="([^"]+)"', re.IGNORECASE)
GT_RE      = re.compile(r'group-title="([^"]+)"', re.IGNORECASE)
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

def load_m3u(file_path, country="RO"):
    """
    Read an M3U and yield entries as Channel objects
    
    Args:
        file_path: Path to the M3U file
        country: ISO-2 country code to filter channels by (if tvg-country tags exist)
    """
    channels = []
    last_info = None
    
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
                
            if line.startswith('#EXTINF'):
                last_info = parse_extinf(line)
            elif line.startswith('#'):
                # ignore other tags
                continue
            else:
                # this should be the URL line
                url = line.strip()
                name = (last_info or {}).get('name') or url  # final fallback = url
                logo = (last_info or {}).get('logo') or ""
                tvg_country = (last_info or {}).get('country') or ""
                group = (last_info or {}).get('group') or ""
                
                # Use named parameters to ensure correct mapping
                ch = Channel(name=name, url=url, logo=logo, tvg_country=tvg_country, group_title=group)
                channels.append(ch)
                last_info = None
                
    # Filter by country if country tags are present
    has_country_tags = any(c.tvg_country for c in channels)
    if has_country_tags:
        # Only filter if channel has a tag — keep channels without country tags
        channels = [c for c in channels if not c.tvg_country or c.tvg_country.upper() == country]
        
    return channels

log_path = get_log_path()
os.makedirs(os.path.dirname(log_path), exist_ok=True)
logging.basicConfig(filename=log_path, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

cfg = load_config()
country = get_country_safe(cfg)

# Main GUI layout
menu_def = [['File', ['Open', 'Exit']],
            ['Settings', ['Configure']],
            ['Help', 'About']]

# Channel selection column (top left)
channel_filter_column = [
    [sg.InputText(key='-FILTER-', enable_events=True, size=(20, 1)),
     sg.Button('Filter', key='-FILTER-BUTTON-')],
    [sg.Listbox(values=[], size=(40, 20), key='-CHANNELS-', enable_events=True)]
]

# Group selection column (top right)
group_column = [
    [sg.Text("Groups:"), sg.Button('All Channels', key='-ALL-CHANNELS-')],
    [sg.Listbox(values=[], size=(30, 20), key='-GROUPS-', enable_events=True)]
]

# Channel details column (bottom left)
channel_details_column = [
    [sg.Listbox(values=[], size=(40, 20), key='-CHANNEL-DETAILS-', enable_events=True)]
]

# Preview column (middle)
preview_column = [
    [sg.Image(key='-IMAGE-')]
]

# Program listing column (right)
program_column = [
    [sg.Listbox(values=[], size=(40, 20), key='-PROGRAMS-', enable_events=True)]
]
status_bar = [sg.Text('', key='status', size=(50,1), justification='center')]

layout = [
    [sg.Menu(menu_def)],
    [sg.Text('ZedTV IPTV Player, Recorder, and Scraper', font=('Any', 18))],
    [sg.Column(channel_filter_column), sg.Column(group_column)],
    [sg.Column(channel_details_column),
     sg.VSeparator(),
     sg.Column(preview_column),
     sg.VSeparator(),
     sg.Column(program_column)],
    [sg.Button('Play'), sg.Button('Record'), sg.Button('Stop')],
    [sg.Button('Generate EPG')],
    [sg.Text('Status: Idle', key='-STATUS-')],
    status_bar
]

window = sg.Window('ZedTV IPTV Player Recorder Scraper', layout, icon=icon, resizable=True, finalize=True)

channels = []
current_player = None
current_recorder = None
if cfg['playlist_last_path'] == "":
    window['-CHANNELS-'].update(['Use File → Open to load an M3U. For Romania testing: ro.m3u from iptv-org.'])

while True:
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Exit':
        break
    
    try:
        if event == sg.WIN_CLOSED:
            break
        elif event == 'Open':
            file_path = sg.popup_get_file('Select M3U file', file_types=(('M3U Files', '*.m3u'),), default_path=cfg['playlist_last_path'])
            if file_path:
                cfg['playlist_last_path'] = os.path.dirname(file_path)
                save_config(cfg)
                channels = load_m3u(file_path, country)
                # Update the channels list
                window['-CHANNELS-'].update([ch.name for ch in channels])
                
                # Extract and update group list
                groups = sorted(set(ch.group_title for ch in channels if ch.group_title))
                window['-GROUPS-'].update(groups)
        elif event == 'Configure':
            settings_layout = [
                [sg.Checkbox("Use Geo-IP auto detect (fallback to default if it fails)", default=cfg['geo_detection'], key='geo_detection')],
                [sg.Text("Default Country (ISO-2)"), sg.Input(cfg['default_country'], key='default_country', size=(5,1))],
                [sg.Button('Save'), sg.Button('Cancel')]
            ]
            settings_window = sg.Window('Settings', settings_layout)
            while True:
                ev, val = settings_window.read()
                if ev == 'Save':
                    cfg['geo_detection'] = val['geo_detection']
                    cfg['default_country'] = val['default_country'].upper()
                    save_config(cfg)
                    country = get_country_safe(cfg)
                    settings_window.close()
                    break
                elif ev in ('Cancel', sg.WIN_CLOSED):
                    settings_window.close()
                    break
        elif event == 'Play':
            selected_channels = values.get('-CHANNELS-', [])
            if selected_channels and channels:
                if isinstance(selected_channels, list) and len(selected_channels) > 0:
                    selected_name = selected_channels[0]
                    # Find the channel with this name
                    selected_channel = next((ch for ch in channels if ch.name == selected_name), None)
                    if selected_channel:
                        if current_player:
                            # Stop existing player if one is running
                            current_player.stop()
                            current_player = None
                        # Create a new player for this URL
                        current_player = player.MediaPlayer(selected_channel.url)
                        current_player.play()
                        window['-STATUS-'].update(f"Status: Playing {selected_channel.name}")
                    else:
                        window['-STATUS-'].update("Status: Error - Channel not found")
                else:
                    window['-STATUS-'].update("Status: Error - No channel selected")
        elif event == 'Stop':
            if current_player:
                current_player.stop()
                current_player = None
                window['-STATUS-'].update("Status: Stopped")
        elif event == '-CHANNELS-':
            # Update display when a channel is selected but don't start playback yet
            selected_channels = values.get('-CHANNELS-', [])
            if selected_channels and isinstance(selected_channels, list) and len(selected_channels) > 0:
                window['-STATUS-'].update(f"Status: Selected {selected_channels[0]}")
        elif event == '-GROUPS-':
            # Filter channels by selected group
            selected_groups = values.get('-GROUPS-', [])
            if selected_groups and isinstance(selected_groups, list) and len(selected_groups) > 0:
                selected_group = selected_groups[0]
                # Filter channels that belong to this group
                filtered_channels = [ch for ch in channels if ch.group_title == selected_group]
                window['-CHANNELS-'].update([ch.name for ch in filtered_channels])
                window['-STATUS-'].update(f"Status: Group '{selected_group}' selected")
        elif event == '-ALL-CHANNELS-':
            # Reset to show all channels
            if channels:
                window['-CHANNELS-'].update([ch.name for ch in channels])
                window['-STATUS-'].update("Status: Showing all channels")
        elif event == '-FILTER-BUTTON-' or event == '-FILTER-' and values['-FILTER-']:
            # Filter channels by text input
            if channels:
                filter_text = values['-FILTER-'].lower()
                filtered_channels = [ch for ch in channels if filter_text in ch.name.lower()]
                window['-CHANNELS-'].update([ch.name for ch in filtered_channels])
                window['-STATUS-'].update(f"Status: Filtered by '{filter_text}'")
                if not filtered_channels:
                    window['-STATUS-'].update(f"Status: No channels match '{filter_text}'")
        elif event == '-FILTER-' and not values['-FILTER-']:
            # When filter is cleared, show all channels
            if channels:
                window['-CHANNELS-'].update([ch.name for ch in channels])
                window['-STATUS-'].update("Status: Showing all channels")
    except Exception as e:
        logging.exception(f"Error in event loop: {e}")
        window['-STATUS-'].update(f"Status: Error: {e}")

window.close()
