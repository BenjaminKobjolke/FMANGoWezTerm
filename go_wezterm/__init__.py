from fman import DirectoryPaneCommand, show_alert
from fman.url import as_human_readable, as_url
import subprocess
import os
import string
import ctypes
import re
import datetime
import traceback

# Set to True to enable logging
ENABLE_LOGGING = True

class Logger:
    def __init__(self):
        self.log_file = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'fman_wezterm_debug.log')
    
    def log(self, message):
        """Write a timestamped message to the log file if logging is enabled"""
        if not ENABLE_LOGGING:
            return
            
        try:
            # Ensure the directory exists
            log_dir = os.path.dirname(self.log_file)
            os.makedirs(log_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            # Print the error to stderr or show an alert
            import sys
            print(f"Error writing to log file: {str(e)}", file=sys.stderr)
            show_alert(f"Error writing to log file: {str(e)}")
    
    def get_log_file_path(self):
        """Get the path to the log file"""
        return self.log_file

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

class GoWezterm(DirectoryPaneCommand):
    def __call__(self):
        # Initialize logger
        logger = Logger()
        log_file = logger.get_log_file_path()
        logger.log("=== New GoWezterm execution ===")

        wezterm_path = "C:\\Program Files\\WezTerm\\wezterm-gui.exe"
        current_path = self.pane.get_path()
        human_readable_path = as_human_readable(current_path)
        
        logger.log(f"Original path: {human_readable_path}")
        
        # Check if the path is a network path (starts with \\)
        if human_readable_path.startswith('\\\\'):
            logger.log("Detected network path")
            
            try:
                # First, check if the network path is already mapped to a drive letter
                logger.log("Checking for existing drive mappings with 'net use'")
                net_use_output = subprocess.check_output('net use', shell=True).decode('utf-8')
                logger.log(f"net use output:\n{net_use_output}")
                
                # Parse the network path to get server and share
                server, share, remaining_path, server_share = parse_network_path(human_readable_path)
                
                if server_share:
                    logger.log(f"Server: {server}")
                    logger.log(f"Share: {share}")
                    logger.log(f"Server+Share: {server_share}")
                    logger.log(f"Remaining path: {remaining_path}")
                    
                    # Look for existing drive mappings
                    drive_letter = find_existing_drive_mapping(server_share, net_use_output)
                    
                    if drive_letter:
                        # Use the existing drive mapping
                        logger.log(f"Found existing drive mapping: {drive_letter} for {server_share}")
                        new_path = f"{drive_letter}{remaining_path}"
                        logger.log(f"Constructed new path: {new_path}")
                        
                        # Convert the path to a URL that fman understands
                        new_url = as_url(new_path)
                        logger.log(f"Setting fman pane to URL: {new_url}")
                        
                        # Set the pane's path to the new URL
                        self.pane.set_path(new_url)

                        # Launch WezTerm with the new path
                        cmd = f'"{wezterm_path}" start --cwd "{new_path}"'
                        logger.log(f"Launching WezTerm with command: {cmd}")
                        subprocess.call(cmd)
                    else:
                        # No existing mapping found, find a free drive letter and create a new mapping
                        logger.log("No existing drive mapping found, creating a new one")
                        
                        # Get free drive letters using Windows API
                        free_drives = get_free_drive_letters()
                        logger.log(f"Free drive letters: {free_drives}")
                        
                        if free_drives:
                            # Use the first free drive letter (highest available letter)
                            free_drive = free_drives[0]
                            logger.log(f"Using free drive letter: {free_drive}")
                            
                            # Create a new network mapping
                            logger.log(f"Creating new network mapping for {server_share}")
                            result = create_network_mapping(free_drive, server_share)
                            logger.log(f"Result of net use command: {result}")
                            if result == 0:
                                # Mapping was successful
                                # Construct the new path with the mapped drive
                                new_path = f"{free_drive}{remaining_path}"
                                logger.log(f"Constructed new path: {new_path}")
                                
                                # Convert the path to a URL that fman understands
                                new_url = as_url(new_path)
                                logger.log(f"Setting fman pane to URL: {new_url}")
                                
                                # Set the pane's path to the new URL
                                self.pane.set_path(new_url)

                                # Launch WezTerm with the new path
                                cmd = f'"{wezterm_path}" start --cwd "{new_path}"'
                                logger.log(f"Launching WezTerm with command: {cmd}")
                                subprocess.call(cmd)
                            else:
                                # Mapping failed, fall back to the original behavior
                                logger.log(f"Failed to create network mapping, falling back to original behavior")
                                fallback_cmd = f'"{wezterm_path}" start --cwd "{human_readable_path}"'
                                logger.log(f"Falling back to original command: {fallback_cmd}")
                                subprocess.call(fallback_cmd)
                        else:
                            # No free drive letters found, fall back to the original behavior
                            logger.log(f"No free drive letters found, falling back to original behavior")
                            fallback_cmd = f'"{wezterm_path}" start --cwd "{human_readable_path}"'
                            logger.log(f"Falling back to original command: {fallback_cmd}")
                            subprocess.call(fallback_cmd)
                else:
                    # Couldn't parse the network path, fall back to the batch file approach
                    logger.log("Couldn't parse network path, using pushd approach")

                    # Create a simple batch file to handle the network path
                    temp_batch_file = create_batch_file(human_readable_path, wezterm_path, log_file)
                    logger.log(f"Created batch file: {temp_batch_file}")
                    
                    # Just start the batch file directly
                    logger.log("Starting batch file directly")
                    logger.log(temp_batch_file)
                    os.startfile(temp_batch_file)
                
            except Exception as e:
                # If anything goes wrong, log the error and fall back to the original behavior
                logger.log(f"Error handling network path: {str(e)}")
                logger.log(traceback.format_exc())
                show_alert(f"Error handling network path: {str(e)}")

                # Log the fallback command
                fallback_cmd = f'"{wezterm_path}" start --cwd "{human_readable_path}"'
                logger.log(f"Falling back to original command: {fallback_cmd}")
                subprocess.call(fallback_cmd)
        else:
            # Not a network path, use the original behavior
            cmd = f'"{wezterm_path}" start --cwd "{human_readable_path}"'
            logger.log(f"Not a network path, using original command: {cmd}")
            subprocess.call(cmd)

class MapNetworkDrive(DirectoryPaneCommand):
    def __call__(self):
        # Initialize logger
        logger = Logger()
        log_file = logger.get_log_file_path()
        logger.log("=== New MapNetworkDrive execution (WezTerm) ===")
        
        current_path = self.pane.get_path()
        human_readable_path = as_human_readable(current_path)
        
        logger.log(f"Original path: {human_readable_path}")
        
        # Check if the path is a network path (starts with \\)
        if human_readable_path.startswith('\\\\'):
            logger.log("Detected network path")
            
            try:
                # First, check if the network path is already mapped to a drive letter
                logger.log("Checking for existing drive mappings with 'net use'")
                net_use_output = subprocess.check_output('net use', shell=True).decode('utf-8')
                logger.log(f"net use output:\n{net_use_output}")
                
                # Parse the network path to get server and share
                server, share, remaining_path, server_share = parse_network_path(human_readable_path)
                
                if server_share:
                    logger.log(f"Server: {server}")
                    logger.log(f"Share: {share}")
                    logger.log(f"Server+Share: {server_share}")
                    logger.log(f"Remaining path: {remaining_path}")
                    
                    # Look for existing drive mappings
                    drive_letter = find_existing_drive_mapping(server_share, net_use_output)
                    
                    if drive_letter:
                        # Use the existing drive mapping
                        logger.log(f"Found existing drive mapping: {drive_letter} for {server_share}")
                        new_path = f"{drive_letter}{remaining_path}"
                        logger.log(f"Constructed new path: {new_path}")
                        
                        # Convert the path to a URL that fman understands
                        new_url = as_url(new_path)
                        logger.log(f"Setting fman pane to URL: {new_url}")
                        
                        # Set the pane's path to the new URL
                        self.pane.set_path(new_url)
                        
                    else:
                        # No existing mapping found, find a free drive letter and create a new mapping
                        logger.log("No existing drive mapping found, creating a new one")
                        
                        # Get free drive letters using Windows API
                        free_drives = get_free_drive_letters()
                        logger.log(f"Free drive letters: {free_drives}")
                        
                        if free_drives:
                            # Use the first free drive letter (highest available letter)
                            free_drive = free_drives[0]
                            logger.log(f"Using free drive letter: {free_drive}")
                            
                            # Create a new network mapping
                            logger.log(f"Creating new network mapping for {server_share}")
                            result = create_network_mapping(free_drive, server_share)
                            logger.log(f"Result of net use command: {result}")
                            
                            if result == 0:
                                # Mapping was successful
                                # Construct the new path with the mapped drive
                                new_path = f"{free_drive}{remaining_path}"
                                logger.log(f"Constructed new path: {new_path}")
                                
                                # Convert the path to a URL that fman understands
                                new_url = as_url(new_path)
                                logger.log(f"Setting fman pane to URL: {new_url}")
                                
                                # Set the pane's path to the new URL
                                self.pane.set_path(new_url)
                                
                            else:
                                # Mapping failed
                                logger.log(f"Failed to create network mapping")
                                show_alert(f"Failed to create network mapping for {server_share}")
                        else:
                            # No free drive letters found
                            logger.log(f"No free drive letters found")
                            show_alert("No free drive letters available for mapping")
                else:
                    # Couldn't parse the network path
                    logger.log("Couldn't parse network path")
                    show_alert("Invalid network path format")
                
            except Exception as e:
                # If anything goes wrong, log the error
                logger.log(f"Error handling network path: {str(e)}")
                logger.log(traceback.format_exc())
                show_alert(f"Error handling network path: {str(e)}")
        else:
            # Not a network path
            logger.log("Not a network path")
            show_alert("Not a network path. This command only works with network paths.")

# Export both commands
__all__ = ['GoWezterm', 'MapNetworkDrive']
