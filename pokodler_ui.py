import tkinter as tk
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from pokodler_config import *
from pokodler_db_manager import *
#from pokodler_dl_manager import get_single_data, playlist_dl, get_video_data, get_playlist_video_data
import pokodler_dl_manager
# from pokodler_dl_manager import open_text_list_audio, open_text_list_video
from tkinter import filedialog
import os
import subprocess


   
create_db()

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


# Create a function to browse the destination folder
def browse_dest():
    global destination
    destination = filedialog.askdirectory()
    destination = str(destination) + '/'
    print('my destination folder: ', destination)
    browse_label.config(text=destination)

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
file_menu.add_command(label="Download from *.txt file (audio)", command=pokodler_dl_manager.open_text_list_audio)
file_menu.add_command(label="Download from *.txt file (video)", command=pokodler_dl_manager.open_text_list_video)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=on_exit)
#file_menu.add_command(label="Exit Without Prompt", command=root.destroy)
menu_bar.add_cascade(label="File", menu=file_menu)


# Create a function to open the destination folder, check the OS and open the folder accordingly
def open_destination_folder():
    if os.name == 'nt': # Windows
        os.startfile(destination)
    elif os.name == 'posix': # Linux, macOS
        subprocess.run(['xdg-open', destination])


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
single_dl_button = tk.Button(root, text='Download Single mp3', command=pokodler_dl_manager.get_single_data, **dl_button_attrs)
single_dl_button.place(rely='0.4', relx='0.5')

# Create a label for the playlist entry and button
entry_playlist = tk.Entry(root, **entry_button_attrs)
entry_playlist.place(rely='0.5', relx='0.01')
button_playlist = tk.Button(root, text='Download Playlist as mp3 Songs', 
                            command=pokodler_dl_manager.playlist_dl (self, entry_playlist.get()), **dl_button_attrs)
button_playlist.place(rely='0.5', relx='0.5')

# Create a label for the single video entry and button
yt_link_video_entry = tk.Entry(root, **entry_button_attrs)
yt_link_video_entry.place(rely='0.6', relx='0.01')
button_single_video = tk.Button(root, text='Download Single Video', command=pokodler_dl_manager.get_video_data, **dl_button_attrs)
button_single_video.place(rely='0.6', relx='0.5')

# Create a label for the single video entry and button
yt_link_playlist_video_entry = tk.Entry(root, **entry_button_attrs)
yt_link_playlist_video_entry.place(rely='0.7', relx='0.01')
button_playlist_video = tk.Button(root, text='Download Videos from Playlist', 
                                  command=pokodler_dl_manager.get_playlist_video_data, **dl_button_attrs)
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