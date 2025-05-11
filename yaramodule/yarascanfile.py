import yara
import os
import psutil
import threading
import shutil  
from notifypy import Notify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Global flag and variables
observers = []
monitoring_flag = False
initial_pids = set()
threads = []

user = os.path.expanduser("~")

# Directories to monitor
MONITORED_DIRECTORIES = [
    os.path.join(user, "Desktop"),
    os.path.join(user, "Downloads"),
    os.path.join(user, "Documents"),
    os.path.join(user, "Pictures"),
    os.path.join(user, "Videos"),
    os.path.join(user, "Music"),
]

# Quarantine directory
QUARANTINE_DIR = os.path.join(user, "AppData", "Local", "RansomGuard", "Quarantine")
os.makedirs(QUARANTINE_DIR, exist_ok=True)  # Create quarantine directory if it doesn't exist

def scan_with_thread(scan_function, file_path, result):
    try:
        result[0] = scan_function(file_path)
    except Exception as e:
        print(f"Error in thread while running {scan_function.__name__}: {e}")
        result[0] = False

def warn(file_path):
    notification = Notify()
    notification.title = "RansomGuard - Yara"
    notification.message = f"Suspicious File detected: {file_path} \n and has been quarantined"
    notification.send()

def quarantine_file(file_path):
    try:
        # Get the original file name and extension
        base, ext = os.path.splitext(file_path)
        new_file_path = f"{base}.malware"  # Add .ransom extension
        os.rename(file_path, new_file_path)  # Rename the file

        # Move the renamed file to the quarantine directory
        shutil.move(new_file_path, os.path.join(QUARANTINE_DIR, os.path.basename(new_file_path)))  # Move to quarantine
        print(f"File {new_file_path} moved to quarantine.")
    except Exception as e:
        print(f"Error quarantining file {file_path}: {e}")

def load_yara_rules(yara_file_path):
    try:
        rules = yara.compile(filepath=yara_file_path)
        return rules
    except yara.SyntaxError as e:
        print(f"YARA Syntax Error: {e}")
        return None
    except Exception as e:
        print(f"Error loading YARA file: {e}")
        return None

def scan_file_with_yara(rules, file_path):
    try:
        matches = rules.match(file_path)
        if matches:
            for match in matches:
                print(f"Detected: {match.rule}")
            return True  # Return True if any match is found
    except Exception as e:
        print(f"Error scanning file {file_path}: {e}")
    return False  # Return False if no match is found

def exploit_scan(file_path):
    yara_file_path = os.path.join(os.getenv('LOCALAPPDATA'), "RansomGuard", "Rules", "Exploit.yar")
    rules = load_yara_rules(yara_file_path)
    return scan_file_with_yara(rules, file_path) if rules else False

def signature(file_path):
    yara_file_path = os.path.join(os.getenv('LOCALAPPDATA'), "RansomGuard", "Rules", "Signature.yar")
    rules = load_yara_rules(yara_file_path)
    return scan_file_with_yara(rules, file_path) if rules else False

def convention_engine(file_path):
    yara_file_path = os.path.join(os.getenv('LOCALAPPDATA'), "RansomGuard", "Rules", "ConventionEngine.yar")
    rules = load_yara_rules(yara_file_path)
    return scan_file_with_yara(rules, file_path) if rules else False

def suspiciousfile(file_path):
    yara_file_path = os.path.join(os.getenv('LOCALAPPDATA'), "RansomGuard", "Rules", "red-is-sus.yar")
    rules = load_yara_rules(yara_file_path)
    return scan_file_with_yara(rules, file_path) if rules else False

class YaraScanHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            print(f"New file created: {event.src_path}")
            self.perform_scans(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            print(f"File modified: {event.src_path}")
            self.perform_scans(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            print(f"File renamed/moved: {event.src_path}")
            self.perform_scans(event.src_path)

    def perform_scans(self, file_path):
        scan_functions = [signature, suspiciousfile, exploit_scan, convention_engine]

        for scan_function in scan_functions:
            result = [False]
            thread = threading.Thread(target=scan_with_thread, args=(scan_function, file_path, result))
            thread.daemon = True  # Make thread a daemon
            thread.start()
            thread.join()  # Wait for the scan to complete
            if result[0]:
                # Call the quarantine function & warn user
                quarantine_file(file_path)
                warn(file_path)  
                break  # Stop further scans if any scan detects malicious activity


def start_monitoring():
    global monitoring_flag, observers, initial_pids
    if monitoring_flag:
        print("Monitoring is already running.")
        return

    initial_pids = set(proc.pid for proc in psutil.process_iter(['pid']))
    monitoring_flag = True
    print("Starting YARA monitoring...")

    for directory in MONITORED_DIRECTORIES:
        if os.path.exists(directory):
            event_handler = YaraScanHandler()
            observer = Observer()
            observer.schedule(event_handler, directory, recursive=True)
            observer.daemon = True
            observer.start()
            observers.append(observer)
            print(f"Monitoring started on: {directory}")
        else:
            print(f"Directory does not exist: {directory}")

def stop_monitoring():
    global monitoring_flag, observers
    if not monitoring_flag:
        print("Monitoring is not running.")
        return

    
    for observer in observers:
        observer.stop()
        observer.join()
    observers.clear()
    print("Yara monitoring stopped.")
    monitoring_flag = False