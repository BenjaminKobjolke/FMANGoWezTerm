import string
import ctypes
import subprocess
import re
import os

def get_free_drive_letters():
    """Get a list of free drive letters in reverse alphabetical order (Z to A)"""
    drives_bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
    all_letters = string.ascii_uppercase
    used = {all_letters[i] for i in range(26) if drives_bitmask & (1 << i)}
    free = [letter + ':' for letter in all_letters if letter not in used]
    # Return in reverse order (Z to A)
    return sorted(free, reverse=True)

def find_existing_drive_mapping(server_share, net_use_output):
    """Find an existing drive mapping for a network path"""
    drive_letter = None
    for line in net_use_output.splitlines():
        if server_share in line:
            # Extract the drive letter (e.g., "V:")
            parts = line.split()
            for part in parts:
                if len(part) == 2 and part[1] == ':':
                    drive_letter = part
                    break
            if drive_letter:
                break
    return drive_letter

def parse_network_path(path):
    """Parse a network path into server, share, and remaining path"""
    match = re.match(r'\\\\([^\\]+)\\([^\\]+)(.*)', path)
    if match:
        server = match.group(1)
        share = match.group(2)
        remaining_path = match.group(3)
        server_share = f'\\\\{server}\\{share}'
        return server, share, remaining_path, server_share
    return None, None, None, None

def create_network_mapping(drive, server_share):
    """Create a network mapping using net use"""
    map_cmd = f'net use {drive} "{server_share}"'
    result = subprocess.call(map_cmd, shell=True)
    return result

def create_batch_file(path, wezterm_path, log_file):
    """Create a batch file to handle network paths that can't be parsed"""
    temp_batch_file = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'fman_wezterm_launcher.bat')

    with open(temp_batch_file, 'w') as f:
        f.write('@echo off\n')
        f.write(f'echo Current directory before pushd: %CD% > "{log_file}.batch.log"\n')
        f.write(f'pushd "{path}"\n')
        f.write(f'echo Result of pushd (errorlevel): %errorlevel% >> "{log_file}.batch.log"\n')
        f.write(f'echo Current directory after pushd: %CD% >> "{log_file}.batch.log"\n')
        f.write(f'echo Starting WezTerm with: "{wezterm_path}" start --cwd "%CD%" >> "{log_file}.batch.log"\n')
        f.write(f'"{wezterm_path}" start --cwd "%CD%"\n')
        f.write(f'echo Result of start (errorlevel): %errorlevel% >> "{log_file}.batch.log"\n')

    return temp_batch_file
