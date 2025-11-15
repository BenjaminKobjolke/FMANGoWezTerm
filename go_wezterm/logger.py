import os
import datetime

# Set to False to disable logging
ENABLE_LOGGING = False

class Logger:
    def __init__(self):
        self.log_file = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'fman_wezterm_debug.log')
    
    def log(self, message):
        """Write a timestamped message to the log file if logging is enabled"""
        if not ENABLE_LOGGING:
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def get_log_file_path(self):
        """Get the path to the log file"""
        return self.log_file
