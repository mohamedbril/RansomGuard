import os
import ctypes
import elevate
import threading
import subprocess
import time
import psutil
import keyboard
import customtkinter as ctk

import honeypot.honeymanager as hm
from ui.settingsui import settings_ui

# Var
app_version = "1.5"

# Other Folder & Honeypot
appdata_path = os.getenv('LOCALAPPDATA')
honeyfiles_path = os.path.join(appdata_path, "RansomGuard", "Honey")
rules_path = os.path.join(appdata_path, "RansomGuard", "Rules")
quarantine = os.path.join(appdata_path, "RansomGuard", "Quarantine")

# Membuat folder RansomGuard jika belum ada
if not os.path.exists(honeyfiles_path) and not os.path.exists(rules_path):
    try:
        os.makedirs(honeyfiles_path)
        os.makedirs(rules_path)
        os.makedirs(quarantine)
    except OSError as e:
        print(f"Failed to create directory {honeyfiles_path}: {e}")

# UAC Admin Req
def run_with_uac():
    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    if not is_admin:
        print("Requesting Admin Access, you can close this window")
        elevate.elevate()



# Open honeypot directory
def open_honeypot_directory():
    if os.path.exists(honeyfiles_path):
        subprocess.Popen(f'explorer "{honeyfiles_path}"')
    else:
        print(f"Path {honeyfiles_path} does not exist.")

# Open Quarantine Directory
def open_quarantine_directory():
    if os.path.exists(honeyfiles_path):
        subprocess.Popen(f'explorer "{quarantine}"')
    else:
        print(f"Path {quarantine} does not exist.")

#Panic Button
def get_process_list():
    return {proc.pid: proc.name() for proc in psutil.process_iter(['pid', 'name'])}

def kill_new_processes(original_processes):
    current_processes = get_process_list()
    new_processes = set(current_processes.keys()) - set(original_processes.keys())
    
    for pid in new_processes:
        print(f"PANIC BUTTON PRESSED: {current_processes[pid]}, killed")
        psutil.Process(pid).terminate()

snapshot = get_process_list()
keyboard.add_hotkey('ctrl + shift + k', kill_new_processes, args=(snapshot,))

# On UI Close stop all features
def on_closing(): 
    app.quit()
    app.destroy()

def main_ui():
    global app
    ctk.set_appearance_mode("System")  
    ctk.set_default_color_theme("green") 

    app = ctk.CTk()  
    app.geometry("360x150")
    app.resizable(False, False)
    app.title(f"RansomGuard v{app_version}")
    app.protocol("WM_DELETE_WINDOW", on_closing)


    # Button Toggle for both protection and Yara scan
    protection_button = ctk.CTkButton(master=app, text="Run", command=lambda:settings_ui())
    protection_button.grid(row=1, column=1, padx=20, pady=10)

    # Open RansomGuard folder 
    open_dir_button = ctk.CTkButton(master=app, text="Honeypot Folder ", command=open_honeypot_directory)
    open_dir_button.grid(row=1, column=2, padx=20, pady=10)

    # Quarantine Folder
    open_quarantine_button = ctk.CTkButton(master=app, text="Quarantine Folder ", command=open_quarantine_directory)
    open_quarantine_button.grid(row=2, column=2, padx=20, pady=10)

    # Random Text
    text = '''
    RansomGuard ©
    '''
    label = ctk.CTkLabel(master=app, text=text, justify="left", anchor="w")
    label.place(relx=0.5, rely=0.9, anchor=ctk.CENTER)

    app.mainloop()

if __name__ == "__main__":
    run_with_uac()
    ctypes.windll.kernel32.SetConsoleTitleW(f"RansomGuard Log , {app_version}")
    hm.create_files_folders()

    try:
        main_ui()
        #settings_ui()
    except Exception as e:
        print(e)
        print("Failed to update one or more protection component. Check your internet connection and re-open this app")
        input("Press anykey to exit")
