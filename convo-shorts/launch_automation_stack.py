import subprocess
import os

if __name__ == "__main__":
    bat_path = r"D:\Projects\yt-automations\convo-shorts\start-all.bat"
    if os.path.exists(bat_path):
        print(f"Launching YouTube Automation Stack via: {bat_path}")
        subprocess.run([bat_path], shell=True)
    else:
        print(f"Error: Could not find start-all.bat at {bat_path}")
