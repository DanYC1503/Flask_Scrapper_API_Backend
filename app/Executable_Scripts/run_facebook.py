import subprocess
import os

def execute_facebook():
    facebook_exe_path = r"app\Executable_Scripts\Executable\WebScrapper.exe"

    if not os.path.exists(facebook_exe_path):
        print(f"Executable not found at: {facebook_exe_path}")
        return

    try:
        subprocess.Popen([facebook_exe_path], shell=True)
        print("WebScrapper.exe launched successfully.")
    except Exception as e:
        print(f"Failed to launch WebScrapper.exe: {e}")
