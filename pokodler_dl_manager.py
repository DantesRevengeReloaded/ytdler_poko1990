# download manager functions etc
from pytube import YouTube, Playlist
from moviepy.editor import AudioFileClip
import asyncio
import time
import os
from tkinter import filedialog
from tkinter import messagebox
from pokodler_db_manager import store_to_db
from pokodler_config import destination


# Create a function to download a single song
def get_single_data(single_link_entry):
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
def playlist_dl(destination, entry_playlist):
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

def get_video_data(yt_link_video_entry, selected_resolution):
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


async def download_video(yt_link, song_number, playlist_dir, downloaded_videos, selected_resolution):
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

def get_playlist_video_data(yt_link_playlist_video_entry):
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