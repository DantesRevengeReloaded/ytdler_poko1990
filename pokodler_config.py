#configuration file for pokodler
import os
import webbrowser
import subprocess

# global variables
version='1.2'
version_details = f'Poko 1990\nCurrent Version: {version}\nVideo Downloader and Converter\nPython Based and Open Source\nSuitable for Linux OS\nDependancies: pytube, tkinter, os, webbrowser, threading, tkinter.messagebox\nAuthor: Pokomaster\nContact: '
destination = '/home/kotsosthegreat/Music/YouTubeMusic'
appfolder = '/mnt/cf36a2d7-ecf4-46c7-a76a-5defe1ad7659/virtual_environments/poko_projects/ytdler'


# Check if the output file exists and delete it if it is bigger than 40MB
if os.path.exists(os.path.join(appfolder, 'output.log')):
    # Check the size of the output file
    if os.path.getsize(os.path.join(appfolder, 'output.log')) > 40 * 1024 * 1024: # 40MB
        # Delete the output file
        os.remove(os.path.join(appfolder, 'output.log'))
        # Create a new output file
        with open(os.path.join(appfolder, 'output.log'), 'w') as f:
            f.write('')

else:
    # Create a new output file
    with open(os.path.join(appfolder, 'output.log'), 'w') as f:
        f.write('')

def open_log_file():
    log_file_path = os.path.join(appfolder, 'output.log')
    if os.name == 'nt': # Windows
        os.startfile(log_file_path)
    elif os.name == 'posix': # Linux, macOS
        subprocess.run(['xdg-open', log_file_path])


# Create a function to open the YouTube website
def yt_url():
    webbrowser.open('https://www.youtube.com')