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

version='1.2'
version_details = f'Poko 1990\nCurrent Version: {version}\nVideo Downloader and Converter\nPython Based and Open Source\nSuitable for Linux OS\nDependancies: pytube, tkinter, os, webbrowser, threading, tkinter.messagebox\nAuthor: Pokomaster\nContact: '
destination = '/home/kotsosthegreat/Music/YouTubeMusic'
appfolder = '/mnt/cf36a2d7-ecf4-46c7-a76a-5defe1ad7659/virtual_environments/poko_projects/ytdler/'

print('the destination folder is: ', destination)
def open_log_file():
    log_file_path = f"{appfolder}output.log"
    os.system(f"xdg-open {log_file_path}")

def browse_dest():
    global destination
    destination = filedialog.askdirectory()
    destination = str(destination) + '/'
    print('my destination folder: ', destination)
    browse_label.config(text=str(destination))


def yt_url():
    webbrowser.open('https://www.youtube.com')

def get_single_data():
    yt_link = single_link_entry.get()
    async def download_audio():
        try:
            print('starting download')
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
            messagebox.showinfo("Success!!!", f"MP3 song: {title} was downloaded successfully!")
            print('mp3 song: ' + title + ' was downloaded successfully!')
            print(yt.metadata)
        except Exception as e:
            messagebox.showerror("Error: ", str(e))
            print(str(e))

    asyncio.run(download_audio())

def open_text_list():
    wind_link1.filename = filedialog.askopenfilename()
    global list_of_songs
    list_of_songs = wind_link1.filename
    try:
        list_of_songs = open(list_of_songs)
        count = 1
        for line in list_of_songs:
            num = f'{count:03d}'.format()
            line.split()
            line = line.strip()
            link = line
            yt = YouTube(link)
            video = yt.streams.filter(only_audio=True).first()
            try:
                dlfile = video.download(destination)
                base, ext = os.path.splitext(dlfile)
                new_file = base + '.mp3'
                os.rename(dlfile, new_file)
                newwfile = os.path.basename(new_file)
                newwfile = os.path.join(destination + str(num) + '_' + newwfile)
                print('the file with name --', yt.title, '-- was downloaded successfully')
                messagewindlink2 = tk.Label(wind_link1, text='video: ' + yt.title + ' was downloaded successfully!', 
                                            font='TIMES', bg='black', fg='white')
                messagewindlink2.pack()
            except:
                print('error has occurred, file with the following URL was not downloaded:', yt)
                messagewindlink3 = tk.Label(wind_link1, text='An error has occurred, a file was not downloaded', font='TIMES')
                messagewindlink3.pack()
                count += 1
    except:
        print('list could not run')
        messagewindlink4 = tk.Label(wind_link1, text='Could Not Run List Properly. One Or More Files Were Not Downloaded!').pack()

def list_link():
    global wind_link1
    wind_link1 = tk.Toplevel(root)
    wind_link1.title('Download and convert videos from txt list')
    wind_link1.geometry('600x200')
    button_list = tk.Button(wind_link1, text='Browse a text list And Download', font='TIMES', command=open_text_list)
    button_list.pack()


async def download_song(yt_link, song_number):
    try:
        print(f'starting download for song {song_number}')
        yt = YouTube(yt_link)
        video = yt.streams.filter(only_audio=True).first()
        dlfile = await asyncio.to_thread(video.download, destination)
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
        store_to_db(wayofdl='Playlist_Download', title=title, length=length, size=size, download_time=download_time, urlsource=urlsource)
        print(f'song {song_number} downloaded successfully!')
    except Exception as e:
        print(f'error downloading song {song_number}: {e}')

def playlist_dl():
    yt_playlist_link = entry_playlist.get()
    async def download_playlist():
        print('link is: ' + yt_playlist_link)
        yt_list = Playlist(yt_playlist_link)
        print(f"Number of items in yt_list: {len(yt_list)}")
        success_count = 0
        tasks = []
        for song_number, yt_link in enumerate(yt_list, start=1):
            tasks.append(asyncio.create_task(download_song(yt_link, song_number)))
        await asyncio.gather(*tasks)
        messagebox.showinfo("Success!!!", f"{len(yt_list)} songs downloaded successfully!")
    asyncio.run(download_playlist())

def get_video_data():
    yt_link_video = yt_link_video_entry.get()
    try:
        yt_video = YouTube(yt_link_video)
        if resolution.get() == 'highest':
            video_stream = yt_video.streams.get_highest_resolution()
        else:
            video_stream = yt_video.streams.filter(res='360p').first()
        dl_video_file = video_stream.download(destination)
        messagebox.showinfo("Success!!!", f"Video: {yt_video.title} was downloaded successfully!")
    except Exception as e:
        print(f"an error has occurred: {e}")
        print(f"an error has occurred, video with the title: {yt_video.title}, was not downloaded")



def on_exit():
    root.destroy()

def store_to_db(wayofdl, title, length, size, download_time, urlsource):
    conn = sqlite3.connect(f"{appfolder}downloaded_songs.db")
    # Create a cursor object
    c = conn.cursor()
    #Create a table to store downloaded songs
    c.execute('''CREATE TABLE IF NOT EXISTS downloaded_songs
             (ID INTEGER PRIMARY KEY, Type text, Title text, Time_Length real, Size_MB real, Downloaded_Date text, URL text)''')
    c.execute("INSERT INTO downloaded_songs (Type, Title, Time_Length, Size_MB, Downloaded_Date, URL) VALUES (?, ?, ?, ?, ?, ?)", 
              (wayofdl, title, length, size, download_time, urlsource))
    conn.commit()
    conn.close()
    
# Create the UI of the application

root = tk.Tk()
root.title('Poko 1990')
root.geometry('800x600')
root.configure(bg='cyan', )
root.resizable(False, False)

#Create attributes for buttons entries and labels
normal_button_attrs = {'font': 'TIMES', 'bg': 'white', 'width': 40}
entry_button_attrs = {'width': 47, 'bg': 'white'}
dl_button_attrs = {'activeforeground':'white', 'bg' : 'green',
                    'activebackground':'black', 'font' : 'TIMES', 'width': 40}
small_label_attrs = {'font': 'Arial 12 bold', 'bg': 'white', 'fg': 'black', 'width': 70, 'relief': 'groove', 'borderwidth': 2}
bold_label_attrs = {'font': 'TIMES 12 bold', 'bg': 'cyan', 'fg': 'black'}

def on_exit():
    if messagebox.askokcancel("Exit", "Do you want to exit?"):
        root.destroy()

# Create a menu bar
menu_bar = Menu(root)

# Create a File menu
file_menu = Menu(menu_bar, tearoff=0)
file_menu.add_command(label="Download from *.txt file (audio)", command=list_link)
file_menu.add_command(label="Download from *.txt file (video)")
file_menu.add_separator()
file_menu.add_command(label="Exit", command=on_exit)
#file_menu.add_command(label="Exit Without Prompt", command=root.destroy)
menu_bar.add_cascade(label="File", menu=file_menu)

# Create a View menu
view_menu = Menu(menu_bar, tearoff=0)
view_menu.add_command(label="Normal Mode")
view_menu.add_command(label="Dark Mode")
menu_bar.add_cascade(label="View", menu=view_menu)

preferances_menu = Menu(menu_bar, tearoff=0)
preferances_menu.add_command(label="Browse Destination Folder", command=browse_dest)
preferances_menu.add_command(label="Open Destination Folder")
menu_bar.add_cascade(label="Preferences", menu=preferances_menu)

# Create a Help menu
help_menu = Menu(menu_bar, tearoff=0)
help_menu.add_command(label="Open Log File", command=open_log_file)
help_menu.add_separator()
help_menu.add_command(label="About", command=lambda: messagebox.showinfo("About", version_details))
menu_bar.add_cascade(label="Help", menu=help_menu)

# Add the menu bar to the root window
root.config(menu=menu_bar)

button_width=20

message = tk.Label(root, text='The Best YouTube downloader\n'
                              'of West Attica', font='TIMES 12 bold', bg='cyan', fg='black')
message.place(rely='0.01', relx='0.1')

button_width=20

yt_button = tk.Button(root, text='Open YouTube', command=yt_url, width=button_width, 
                      font='TIMES', bg='#8C001A', fg='white', borderwidth='2')
yt_button.place(rely='0.1', relx=0.5, anchor='center')


# Create a label for the destination folder
browse_label = tk.Label(root, text=str(destination), **small_label_attrs )
browse_label.place(rely='0.2', relx='0.01') 
browse_button = tk.Button(root, text='...', command=browse_dest, borderwidth='2', relief='groove')
browse_button.place(rely='0.22', relx='0.9', anchor='e')

# Create a label for the single link entry and button
single_link_entry = tk.Entry(root, **entry_button_attrs)
single_link_entry.place(rely='0.4', relx='0.01')
single_dl_button = tk.Button(root, text='Download and convert video to mp3', command=get_single_data, **dl_button_attrs)
single_dl_button.place(rely='0.4', relx='0.5')

# Create a label for the playlist entry and button
entry_playlist = tk.Entry(root, **entry_button_attrs)
entry_playlist.place(rely='0.5', relx='0.01')
button_playlist = tk.Button(root, text='Download and convert all videos from playlist', command=playlist_dl, **dl_button_attrs)
button_playlist.place(rely='0.5', relx='0.5')

# Create a label for the single video entry and button
yt_link_video_entry = tk.Entry(root, **entry_button_attrs)
yt_link_video_entry.place(rely='0.6', relx='0.01')
button_single_video = tk.Button(root, text='Download Single Video (paste link)', command=get_video_data, **dl_button_attrs)
button_single_video.place(rely='0.6', relx='0.5')

def clear_entries():
    yt_link_video_entry.delete(0, 'end')
    single_link_entry.delete(0, 'end')
    entry_playlist.delete(0, 'end')

# Create a button to clear all entry widgets
clear_button = tk.Button(root, text='Clear All Text In Entry', command=clear_entries)
clear_button.place(relx='0.1', rely='0.3')

# Create a variable to store the selected resolution
resolution = tk.StringVar()

# Create a frame for the radio buttons
radio_frame = tk.Frame(root)
radio_frame.place(rely='0.7', relx='0.5', anchor='center')

# Create a radio button for highest resolution
highest_resolution_button = tk.Radiobutton(radio_frame, text='Highest Resolution', variable=resolution, value='highest')
highest_resolution_button.pack(side='left')

# Create a radio button for normal resolution
normal_resolution_button = tk.Radiobutton(radio_frame, text='Normal Resolution', variable=resolution, value='normal')
normal_resolution_button.pack(side='left', padx=10)


# Create a label for the powered by message
message2_label = tk.Label(root, text="Powered by Pokomaster\n The True Master of Poko\n copyright 2023\n All Rights Reserved",
                    font='TIMES 8 bold', bg='cyan', fg='black')
message2_label.place(rely='0.8')

# Create a status bar
status_bar = Label(root, text=f'Version: {version}', relief=SUNKEN, anchor=E)
status_bar.pack(side=BOTTOM, fill=X)

root.protocol("WM_DELETE_WINDOW", on_exit)

root.mainloop()