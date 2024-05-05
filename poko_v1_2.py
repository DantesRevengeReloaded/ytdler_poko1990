import tkinter as tk
from tkinter import filedialog
from pytube import YouTube, Playlist
from tkinter import *
from tkinter.ttk import *
import os
import webbrowser
import asyncio
from tkinter import messagebox
import time
import sqlite3
from moviepy.editor import AudioFileClip
import subprocess

# global variables
version='1.2'
version_details = f'Poko 1990\nCurrent Version: {version}\nVideo Downloader and Converter\nPython Based and Open Source\nSuitable for Linux OS\nDependancies: pytube, tkinter, os, webbrowser, threading, tkinter.messagebox\nAuthor: Pokomaster\nContact: '
destination = '/home/kotsosthegreat/Music/YouTubeMusic'
appfolder = '/mnt/cf36a2d7-ecf4-46c7-a76a-5defe1ad7659/Poko_Projects/ytdler'


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


# Create a function to open the log file
def open_log_file():
    log_file_path = os.path.join(appfolder, 'output.log')
    if os.name == 'nt': # Windows
        os.startfile(log_file_path)
    elif os.name == 'posix': # Linux, macOS
        subprocess.run(['xdg-open', log_file_path])

# Create a function to browse the destination folder
def browse_dest():
    global destination
    destination = filedialog.askdirectory()
    destination = str(destination) + '/'
    print('my destination folder: ', destination)
    browse_label.config(text=str(destination))

# Create a function to open the destination folder, check the OS and open the folder accordingly
def open_destination_folder():
    if os.name == 'nt': # Windows
        os.startfile(destination)
    elif os.name == 'posix': # Linux, macOS
        subprocess.run(['xdg-open', destination])

# Create a function to open the YouTube website
def yt_url():
    webbrowser.open('https://www.youtube.com')

# Create a function to download a single song
def get_single_data():
    yt_link = single_link_entry.get()
    # use asyncio library to download the song
    async def download_audio():
        try:
            print('Starting to download song...')
            start_time = time.time()
            yt = YouTube(yt_link)
            video = yt.streams.filter(only_audio=True).first()
            dlfile = await asyncio.to_thread(video.download, destination)
            base, ext = os.path.splitext(dlfile)
            new_file = base + '.mp3'
            clip = await asyncio.to_thread(AudioFileClip, dlfile)
            await asyncio.to_thread(clip.write_audiofile, new_file, bitrate='192k')
            os.remove(dlfile)
            title = yt.title
            length = round(yt.length / 60, 2) #convert to minutes
            size = round(os.path.getsize(new_file) / (1024 * 1024), 2) #get size in MB
            download_time = time.strftime('%Y-%m-%d %H:%M:%S')
            urlsource = yt_link
            store_to_db(wayofdl='Single_Download', title=title, length=length, size=size, download_time=download_time, urlsource=urlsource)
            end_time = time.time()
            elapsed_time = round((end_time - start_time)/60, 2)
            messagebox.showinfo("Result", f"MP3 song: {title} was downloaded successfully in {elapsed_time} minutes!")
            print(f"MP3 song: {title} was downloaded successfully in {elapsed_time} minutes!")
            print(yt.metadata)
        except Exception as e:
            messagebox.showerror("Error: ", str(e))
            print(str(e))
    asyncio.run(download_audio())


def open_text_list_audio():
    list_of_songs=filedialog.askopenfilename()
    if not list_of_songs:
        return
    try:
        with open(list_of_songs, 'r') as fl:
            count = 0
            success_count = 0
            start_time = time.time()
            txtlstaudio_dir = os.path.join(destination, f"text_list_audio_{time.strftime('%Y-%m-%d_%H-%M-%S')}")
            os.mkdir(txtlstaudio_dir)
            ttl_url_list = len(fl.readlines())
            print('Total number of urls in the list: ', ttl_url_list)
            fl.seek(0) # reset the file pointer to the beginning of the file
            print('Starting download...')
            for line in fl:
                try:
                    num = f'{count:03d}'
                    yt = YouTube(line)
                    video = yt.streams.filter(only_audio=True).first()
                    dlfile = video.download(txtlstaudio_dir)
                    base, ext = os.path.splitext(dlfile)
                    new_file = base + '.mp3'
                    neww_file = os.path.join(os.path.dirname(new_file), num + '_' + os.path.basename(new_file))
                    clip = AudioFileClip(dlfile)
                    clip.write_audiofile (neww_file, bitrate='192k')
                    os.remove(dlfile)
                    title = yt.title
                    length = round(yt.length / 60, 2) #convert to minutes
                    size = round(os.path.getsize(neww_file) / (1024 * 1024), 2) #get size in MB
                    download_time = time.strftime('%Y-%m-%d %H:%M:%S')
                    urlsource = line
                    store_to_db(wayofdl='List_Audio_Download', title=title, length=length, size=size, download_time=download_time, urlsource=urlsource)
                    print(f"MP3 song: {title} was downloaded successfully!")
                    print(yt.metadata)
                    success_count += 1
                except Exception as e:
                    print(str(e))
            count += 1
        end_time = time.time()
        elapsed_time = round((end_time - start_time)/60, 2)
        messagebox.showinfo('Result', f"for {ttl_url_list} URLs in .txt list {success_count} audio files were downloaded succefully in {elapsed_time} minutes!")
    except Exception as e:
        print('Error: File not found: ', str(e))
        messagebox.showerror('Error', str(e))

def open_text_list_video():
    list_of_songs=filedialog.askopenfilename()
    if not list_of_songs:
        return
    try:
        with open(list_of_songs, 'r') as fl:
            count = 0
            success_count = 0
            start_time = time.time()
            txtlstaudio_dir = os.path.join(destination, f"text_list_video_{time.strftime('%Y-%m-%d_%H-%M-%S')}")
            os.mkdir(txtlstaudio_dir)
            ttl_url_list = len(fl.readlines())
            print('Total number of urls in the list: ', ttl_url_list)
            fl.seek(0) # reset the file pointer to the beginning of the file
            for line in fl:
                try:
                    print('Starting download')
                    yt_video = YouTube(line)
                    video_stream = yt_video.streams.get_highest_resolution()
                    dlfile = video_stream.download(txtlstaudio_dir)
                    title = yt_video.title
                    length = round(yt_video.length / 60, 2) #convert to minutes
                    size = round(os.path.getsize(dlfile) / (1024 * 1024), 2) #get size in MB
                    download_time = time.strftime('%Y-%m-%d %H:%M:%S')
                    urlsource = line
                    store_to_db(wayofdl='List_Video_Download', title=title, length=length, size=size, download_time=download_time, urlsource=urlsource)
                    print(f"Video: {title} was downloaded successfully!")
                    print(yt_video.metadata)
                    success_count += 1
                except Exception as e:
                    print(str(e))
            count += 1
        end_time = time.time()
        elapsed_time = round((end_time - start_time)/60, 2)
        messagebox.showinfo('Result', f"for {ttl_url_list} URLs in txt list {success_count} videos were downloaded succefully in {elapsed_time} minutes!")
        print(f"for {ttl_url_list} URLs in txt list {success_count} videos were downloaded succefully in {elapsed_time} minutes!")
    except Exception as e:
        print('Error: File not found', str(e))
        messagebox.showerror('Error', str(e))


async def download_song(yt_link, song_number, playlist_dir, downloaded_songs, total_songs):
    try:
        print(f'starting download song {song_number}')
        yt = YouTube(yt_link)
        video = yt.streams.filter(only_audio=True).first()
        dlfile = await asyncio.to_thread(video.download, playlist_dir)
        base, ext = os.path.splitext(dlfile)
        new_file = base + '.mp3'
        clip = await asyncio.to_thread(AudioFileClip, dlfile)
        await asyncio.to_thread(clip.write_audiofile, new_file, bitrate='192k')
        os.remove(dlfile)
        num = f'{song_number:03d}'
        newwfile = os.path.join(os.path.dirname(new_file), num + '_' + os.path.basename(new_file))
        os.rename(new_file, newwfile)
        title = yt.title
        length = round(yt.length / 60, 2) #convert to minutes
        size = round(os.path.getsize(newwfile) / (1024 * 1024), 2) #get size in MB
        download_time = time.strftime('%Y-%m-%d %H:%M:%S')
        urlsource = yt_link
        store_to_db(wayofdl='Playlist_Download', title=title, length=length, size=size, 
                    download_time=download_time, urlsource=urlsource)
        downloaded_songs.append(song_number)
        print(f'song {song_number} downloaded successfully!')
    except Exception as e:
        print(f'error downloading song {song_number}: {e}')
        
# Download all songs from a playlist
def playlist_dl(destination):
    try:    
        yt_playlist_link = entry_playlist.get()
        # Check if the YouTube playlist URL exists
        if not Playlist(yt_playlist_link):
            raise ValueError("Invalid YouTube playlist URL")
        start_time = time.time()
        #create a playlist folder so the songs will be downloaded separately
        playlist_dir = os.path.join(destination, f"playlist_{time.strftime('%Y-%m-%d_%H-%M-%S')}")
        os.mkdir(playlist_dir)
        downloaded_songs = []
        async def download_playlist():
            print('link is: ' + yt_playlist_link)
            yt_list = Playlist(yt_playlist_link)
            total_songs = len(yt_list)
            print(f"Number of items in yt_list: {total_songs}")
            print('Starting download...')
            #run the download_song function for each song in the playlist using asyncio
            tasks = []
            for song_number, yt_link in enumerate(yt_list, start=1):
                tasks.append(asyncio.create_task(download_song(yt_link, song_number, playlist_dir, 
                                                               downloaded_songs, total_songs)))
            await asyncio.gather(*tasks)
            #check if all songs were downloaded successfully, details and show a message
            end_time = time.time()
            elapsed_time = round((end_time - start_time)/60, 2)
            num_of_downloaded_songs = len(downloaded_songs)
            messagebox.showinfo("Result", f"{num_of_downloaded_songs} out of total {total_songs} songs in Playlist were downloaded successfully in {elapsed_time} minutes!")
            print(f"{num_of_downloaded_songs} out of total {total_songs} songs in Playlist were downloaded successfully in {elapsed_time} minutes!")
        asyncio.run(download_playlist())
    except Exception as e:
        print(f"an error has occurred: {e}")
        messagebox.showerror("Error", str(e))

def get_video_data():
    yt_link_video = yt_link_video_entry.get()
    try:
        start_time = time.time()
        yt_video = YouTube(yt_link_video)
        if selected_resolution == 'highest':
            print('Downloading in highest resolution')
            video_stream = yt_video.streams.get_highest_resolution()
        else:
            print('Downloading in low resolution')
            video_stream = yt_video.streams.filter(res='360p').first()
        dl_video_file = video_stream.download(destination)
        title = yt_video.title
        length = round(yt_video.length / 60, 2) #convert to minutes
        size = round(os.path.getsize(dl_video_file) / (1024 * 1024), 2) #get size in MB
        download_time = time.strftime('%Y-%m-%d %H:%M:%S')
        urlsource = yt_link_video
        store_to_db(wayofdl='Single_Video_Download', title=title, length=length, size=size, download_time=download_time, urlsource=urlsource)
        end_time = time.time()
        elapsed_time = round((end_time - start_time)/60, 2)
        messagebox.showinfo("Result", f"Video: {yt_video.title} was downloaded successfully in {elapsed_time} minutes!")
        print(f"Video: {yt_video.title} was downloaded successfully in {elapsed_time} minutes!")
    except Exception as e:
        print(f"an error has occurred: {e}")
        print(f"an error has occurred, video with the title: {yt_video.title}, was not downloaded: {e}")
        messagebox.showerror("Error", str(e))


async def download_video(yt_link, song_number, playlist_dir, downloaded_videos):
    try:
        print(f'starting download video {song_number}')
        yt = YouTube(yt_link)
        if selected_resolution == 'highest':
            print('Downloading in highest resolution')
            video = yt.streams.get_highest_resolution()
        else:
            print('Downloading in low resolution')
            video = yt.streams.filter(res='360p').first()
        dlfile = await asyncio.to_thread(video.download, playlist_dir)
        title = yt.title
        length = round(yt.length / 60, 2) #convert to minutes
        size = round(os.path.getsize(dlfile) / (1024 * 1024), 2) #get size in MB
        download_time = time.strftime('%Y-%m-%d %H:%M:%S')
        urlsource = yt_link
        store_to_db(wayofdl='Playlist_Video_Download', title=title, length=length, size=size, download_time=download_time, urlsource=urlsource)
        print(f'Video {yt.title} downloaded successfully!')
        downloaded_videos.append(song_number)
    except Exception as e:
        print(f'error downloading song {yt.title}: {e}')

def get_playlist_video_data():
    yt_link_playlist_video = yt_link_playlist_video_entry.get()
    try:
        start_time = time.time()
        playlist_dir = os.path.join(destination, f"video_playlist_{time.strftime('%Y-%m-%d_%H-%M-%S')}")
        os.mkdir(playlist_dir)
        downloaded_videos = []
        async def download_video_playlist():
            print('link is: ' + yt_link_playlist_video)
            yt_list = Playlist(yt_link_playlist_video)
            total_videos=len(yt_list)
            print(f"Number of items in yt_list: {total_videos}")
            tasks = []
            for song_number, yt_link in enumerate(yt_list, start=1):
                tasks.append(asyncio.create_task(download_video(yt_link, song_number, playlist_dir, downloaded_videos)))
            await asyncio.gather(*tasks)
            num_of_downloaded_videos = len(downloaded_videos)
            end_time = time.time()
            elapsed_time = round((end_time - start_time)/60, 2)
            messagebox.showinfo("Result", f"{num_of_downloaded_videos} of total {total_videos} videos in Playlist were downloaded in {elapsed_time} minutes!")
            print(f"{num_of_downloaded_videos} of total {total_videos} videos in Playlist were downloaded in {elapsed_time} minutes!")
        asyncio.run(download_video_playlist())
    except Exception as e:
        messagebox.showerror("Error", str(e))
        print(f"an error has occurred: {e}")


def create_db():
    conn = sqlite3.connect(os.path.join(appfolder, 'downloaded_songs.db'))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS downloaded_songs
                 (ID INTEGER PRIMARY KEY, Type text, Title text, Time_Length real, Size_MB real, Downloaded_Date text, URL text)''')
    conn.commit()
    conn.close()

create_db()

def get_total_size():
    conn = sqlite3.connect(os.path.join(appfolder, 'downloaded_songs.db'))
    c = conn.cursor()
    c.execute("SELECT SUM (Size_MB) FROM downloaded_songs")
    result = c.fetchone()[0]
    conn.close()
    return result if result is not None else 0

def get_total_songs():
    try:
        conn = sqlite3.connect(os.path.join(appfolder, 'downloaded_songs.db'))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM downloaded_songs")
        result = c.fetchone()[0]
        conn.close()
        return round(result,2) if result is not None else 0
    except Exception as e:
        print('Unable to retrieve data for the application: ', str(e))
        return 0

def update_status_bar():
    if get_total_size() <= 1:
        total_size = 0
    else:
        total_size = round(get_total_size(), 2)
    if get_total_songs() <= 1:
        total_songs = 0
    else:
        total_songs = get_total_songs()
    status_bar.config(text=f'Version: {version} | Total Size Of Files Downloaded: {total_size} MB | Total Files Downloaded: {total_songs}')

def store_to_db(wayofdl, title, length, size, download_time, urlsource):
    conn = sqlite3.connect(os.path.join(appfolder, 'downloaded_songs.db'))
    # Create a cursor object
    c = conn.cursor()
    #Create a table to store downloaded songs
    c.execute('''CREATE TABLE IF NOT EXISTS downloaded_songs
             (ID INTEGER PRIMARY KEY, Type text, Title text, Time_Length real, Size_MB real, Downloaded_Date text, URL text)''')
    c.execute("INSERT INTO downloaded_songs (Type, Title, Time_Length, Size_MB, Downloaded_Date, URL) VALUES (?, ?, ?, ?, ?, ?)", 
              (wayofdl, title, length, size, download_time, urlsource))
    print('storing data to db...')
    conn.commit()
    conn.close()


# Create the UI of the application

root = tk.Tk()
root.title('Poko 1990')
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
window_width = int(screen_width * 0.8)
window_height = int(screen_height * 0.8)
if window_width < 800:
    window_width = 800
if window_height < 600:
    window_height = 600
x = int((screen_width - window_width) / 2 - window_width / 4)
y = int((screen_height - window_height) / 2 - window_height / 4)
root.geometry(f'{window_width}x{window_height}+{x}+{y}')
root.configure(bg='black', cursor='heart', borderwidth=5, relief='groove', bd=5)
root.resizable(True, True)
root.wm_minsize(800, 600) # set the minimum size of the window

def on_exit():
    root.destroy()

#Create attributes for buttons entries and labels
entry_button_attrs = {'width': 47, 'bg': 'white'}
dl_button_attrs = {'activeforeground':'white', 'bg' : 'black', 'fg' : 'yellow',
                    'activebackground':'black', 'font' : 'TIMES', 'width': 40}
small_label_attrs = {'font': 'Arial 12 bold', 'bg': 'white', 'fg': 'black', 'width': 70, 'relief': 'groove', 'borderwidth': 2, 'height': 1}
message_attrs = {'font': 'TIMES 10 bold', 'bg': 'black', 'fg': 'yellow'}
small_message_attrs = {'font': 'TIMES 8 bold', 'bg': 'black', 'fg': 'yellow'}
bar_attrs= {'bg': 'gray20', 'fg': 'white'} 
youtube_button_attrs = {'font': 'Arial 12 bold', 'bg': 'red', 'fg': 'white',
                        'width': 15, 'height': 2,'relief': 'groove', 'borderwidth': 2}

def on_exit():
    if messagebox.askokcancel("Exit", "Do you want to exit?"):
        root.destroy()

# Create a menu bar
menu_bar = Menu(root, activebackground='gray15', activeforeground='white', **bar_attrs)

# Create a File menu
file_menu = Menu(menu_bar, tearoff=0)
file_menu.add_command(label="Download from *.txt file (audio)", command=open_text_list_audio)
file_menu.add_command(label="Download from *.txt file (video)", command=open_text_list_video)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=on_exit)
#file_menu.add_command(label="Exit Without Prompt", command=root.destroy)
menu_bar.add_cascade(label="File", menu=file_menu)

preferances_menu = Menu(menu_bar, tearoff=0)
preferances_menu.add_command(label="Browse Destination Folder", command=browse_dest)
preferances_menu.add_command(label="Open Destination Folder",command=open_destination_folder)
menu_bar.add_cascade(label="Preferences", menu=preferances_menu)

# Create a Help menu
help_menu = Menu(menu_bar, tearoff=0)
help_menu.add_command(label="Open Log File", command=open_log_file)
help_menu.add_separator()
help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", version_details, icon='info', type='ok'))
menu_bar.add_cascade(label="Help", menu=help_menu)

# Add the menu bar to the root window
root.config(menu=menu_bar)

message = tk.Label(root, text='The Best YouTube downloader\n'
                              'of West Attica', **message_attrs)
message.place(rely='0.01', relx='0.1')

yt_button = tk.Button(root, text='Open YouTube', command=yt_url, **youtube_button_attrs)
yt_button.place(rely='0.1', relx=0.5, anchor='center')

# Create a label for the destination folder
browse_label = tk.Label(root, text=str(destination), **small_label_attrs )
browse_label.place(rely='0.2', relx='0.01') 
browse_button = tk.Button(root, text='set destination\n folder', 
                          command=browse_dest, relief='groove', bg='#C2D1E5')
browse_button.place(rely='0.22', relx='0.95', anchor='e')

# Create a label for the single link entry and button
single_link_entry = tk.Entry(root, **entry_button_attrs)
single_link_entry.place(rely='0.4', relx='0.01')
single_dl_button = tk.Button(root, text='Download Single mp3', command=get_single_data, **dl_button_attrs)
single_dl_button.place(rely='0.4', relx='0.5')

# Create a label for the playlist entry and button
entry_playlist = tk.Entry(root, **entry_button_attrs)
entry_playlist.place(rely='0.5', relx='0.01')
button_playlist = tk.Button(root, text='Download Playlist as mp3 Songs', 
                            command=lambda: playlist_dl(destination), **dl_button_attrs)
button_playlist.place(rely='0.5', relx='0.5')

# Create a label for the single video entry and button
yt_link_video_entry = tk.Entry(root, **entry_button_attrs)
yt_link_video_entry.place(rely='0.6', relx='0.01')
button_single_video = tk.Button(root, text='Download Single Video', command=get_video_data, **dl_button_attrs)
button_single_video.place(rely='0.6', relx='0.5')

# Create a label for the single video entry and button
yt_link_playlist_video_entry = tk.Entry(root, **entry_button_attrs)
yt_link_playlist_video_entry.place(rely='0.7', relx='0.01')
button_playlist_video = tk.Button(root, text='Download Videos from Playlist', 
                                  command=get_playlist_video_data, **dl_button_attrs)
button_playlist_video.place(rely='0.7', relx='0.5')


def clear_entries():
    yt_link_video_entry.delete(0, 'end')
    single_link_entry.delete(0, 'end')
    entry_playlist.delete(0, 'end')
    yt_link_playlist_video_entry.delete(0, 'end')

# Create a button to clear all entry widgets
clear_button = tk.Button(root, text='Clear All Text In Entries', command=clear_entries, **dl_button_attrs)
clear_button.place(relx='0.01', rely='0.3', anchor='w')

# Create a variable to store the selected resolution
resolution = tk.StringVar(value='highest')

# Create a frame for the radio buttons
radio_frame = tk.Frame(root, bg='black')
radio_frame.place(rely='0.8', relx='0.5', anchor='center')

# Create a radio button for highest resolution
highest_resolution_button = tk.Radiobutton(radio_frame, text='Highest Resolution', variable=resolution, value='highest')
highest_resolution_button.pack(side='left')

# Create a radio button for normal resolution
normal_resolution_button = tk.Radiobutton(radio_frame, text='Normal Resolution', variable=resolution, value='normal')
normal_resolution_button.pack(side='left', padx=10)

# Get the selected resolution
selected_resolution = resolution.get()
if not selected_resolution:
    selected_resolution = 'highest'

# Create a label for the powered by message
message2_label = tk.Label(root, text="Powered by Pokomaster\n The True Master of Poko\n copyright 2023\n All Rights Reserved",
                    **small_message_attrs)
message2_label.place(rely='0.85')

# Create a status bar
status_bar = Label(root,background='gray20',foreground='white', text=f'Version: {version}', relief=SUNKEN, anchor=E)
status_bar.pack(side=BOTTOM, fill=X)

update_status_bar()

root.protocol("WM_DELETE_WINDOW", on_exit)

root.mainloop()