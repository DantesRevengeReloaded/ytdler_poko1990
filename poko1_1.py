import tkinter as tk
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from tkinter import filedialog
import os
from pytube import YouTube
from pytube import Playlist
import webbrowser


def change_audio_bitrate(audio_path, output_path, bitrate='192k'):
    audio = AudioSegment.from_file(audio_path)
    audio.export(output_path, format='mp3', bitrate=bitrate)

root = tk.Tk()
root.title('Poko 1990',)
root.geometry('400x680+300+100')
root.configure(bg='cyan')

root.resizable(False, False)

status_bar = Label(root, text='Version 1.0', relief=SUNKEN, anchor=W)
status_bar.pack(side=BOTTOM, fill=X)
#photo = PhotoImage(file="prussia.png")
#root.iconphoto(False, photo)

message = tk.Label(root, text='The Best YouTube downloader\n '
                              'of West Attica', font='TIMES 12 bold', bg='cyan', fg='black')
message.place(rely='0.01', relx='0.25')

message2 = tk.Label(root, text="Powered by Pokomaster\n The True Master of Poko\n copyright 2023\n All Rights Reserved",
                    font='TIMES 8 bold', bg='cyan', fg='black')
message2.place(rely='0.8')

destination = '/home/kotsosthegreat/Music/YouTubeMusic'
print(destination)

def browsedest():
    global destination
    destination = filedialog.askdirectory()
    destination = str(destination)+'/'
    print('my folder', destination)


browsebutton = tk.Button(root, text='Browse Destination Folder', font='TIMES', width=25,
                         bg='white',command=browsedest).place(rely='0.2', relx='0.4')


destinationbutton = tk.Button(root, text='Open Destination Folder', font='TIMES', width=25, bg='white').place(rely='0.7', relx= '0.4')


def yturl() :
    webbrowser.open('https://www.youtube.com')

ytbutton=tk.Button(root, text = 'Click to open YouTube', command=yturl, font='TIMES', bg='#8C001A', fg='white', borderwidth='7')
ytbutton.place (rely='0.1')

def getdata() :
    global ytlink2
    ytlink2= ytlink.get()
    try:
        yt = YouTube(ytlink2)
        video = yt.streams.filter(only_audio=True).first()
        dlfile = video.download(destination)
        base, ext = os.path.splitext(dlfile)
        new_file = base + '.mp3'
        os.rename(dlfile, new_file)
        newwfile = os.path.basename(new_file)
        newwfile = os.path.join(destination, '1' + '_' + newwfile)

        # Convert the audio to the desired bitrate (192 kbps in this case)
        change_audio_bitrate(new_file, newwfile, bitrate='192k')
        global goodmess
        goodmess = tk.Label(windlink, text='mp3 song: ' + yt.title + ' was downloaded successfully!')
        goodmess.pack()
    except:
        global badmess
        badmess = tk.Label(windlink, text='An error occurred, check url or connection')
        badmess.pack()


def singlelink() :
    global windlink
    windlink = Toplevel()
    windlink.title('Download and convert a single video')
    windlink.geometry('500x200')
    messagewindlink = tk.Label(windlink, text='Please enter a proper YouTube link: ')
    messagewindlink.pack()
    global ytlink
    ytlink = Entry(windlink, width=50)
    ytlink.pack()
    singledlbutton = Button(windlink, text='Download and convert video to mp3', command=getdata)
    singledlbutton.pack()

def opentextlist() :
    windlink1.filename = filedialog.askopenfilename()
    global listofsongs
    listofsongs=windlink1.filename
    try:
        listofsongs=open(listofsongs)
        count = 1
        for line in listofsongs:
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
                print ('the file with name --',yt.title,'-- was downloaded successfully')
                messagewindlink2 = tk.Label(windlink1, text= 'video: ' + yt.title + ' was downloaded successfully!', 
                                            font='TIMES', bg='black', fg='white')
                messagewindlink2.pack()
            except:
                print ('error has occurred, file with the following url wasnt downloaded:',yt)
                messagewindlink3 = tk.Label(windlink1, text='An error Has occurred, a file was not downloaded',font='TIMES')
                messagewindlink3.pack()
                count += 1
    except:
        print('list couldt run,')
        messagewindlink4 = tk.Label(windlink1, text='Could Not Run List Properly. One Or More Files Were Not Downloaded!').pack()


def listlink() :
    global windlink1
    windlink1 = Toplevel()
    windlink1.title('Download and convert videos from txt list')
    windlink1.geometry('600x200')
    global buttonlist
    buttonlist = tk.Button(windlink1, text = 'Browse a text list And Download', font='TIMES', command=opentextlist)
    buttonlist.pack()

def playlistlink() :
    global windlink2
    windlink2 = Toplevel()
    windlink2.title('Download and convert videos from YouTube Playlist')
    windlink2.geometry('600x500')
    message4 =tk.Label(windlink2, text='Please enter a playlist url: ', font='TIMES 12 bold')
    message4.pack()
    global entryplaylist
    entryplaylist = tk.Entry(windlink2, width=50)
    entryplaylist.pack()
    global buttonplaylist
    buttonplaylist = tk.Button(windlink2, text='Download and convert all videos from playlist', 
                               activeforeground='white', bg='cyan', activebackground='black', font='TIMES', command=playlistdl)
    buttonplaylist.pack()

def playlistdl() :
    global ytplaylistlink
    ytplaylistlink = entryplaylist.get()
    global ytlist
    ytlist = Playlist(ytplaylistlink)
    count = 1
    successcount = 0
    totalcount = 0
    for sololink in ytlist :
        num = f'{count:03d}'.format()
        print(num)
        videourl = YouTube(sololink)
        video = videourl.streams.filter(only_audio=True).first()
        try:
            dlfile = video.download(destination)
            base, ext = os.path.splitext(dlfile)
            new_file = base + '.mp3'
            os.rename(dlfile, new_file)
            newwfile = os.path.basename(new_file)
            newwfile = os.path.join(destination + str(num) + '_' + newwfile)
            os.rename(new_file, newwfile)
            print ('the file with name --',videourl.title,'-- was downloaded successfully')
            successcount += 1
        except:
            print ('error has occurred, file with the following url was not downloaded:',videourl)
            messagewindlink4 = tk.Label(windlink2, text='An error Has occurred, a file was not downloaded', font='TIMES')
            messagewindlink4.pack()
        count += 1
        totalcount += 1
    global strresult
    strresult = str(successcount) + ' songs out of ' + str(totalcount) + ' total were downloaded successfully!'
    strresult = str(strresult)
    global listresult
    listresult = tk.Label(windlink2, text=strresult).pack()

def getvideodata() :
    global ytlinkvideo
    ytlinkvideo=ytlinkvideo.get()
    try:
        ytvideo = YouTube(ytlinkvideo)
        truevideo = ytvideo.streams.filter(progressive=True, file_extension='mp4').first()
        dlvideofile = truevideo.download(destination)
        global goodmessvideo
        goodmessvideo = tk.Label(windlinkvideo, text='YouTube video: ' + ytvideo.title + ' was downloaded successfully!')
        goodmessvideo.pack()
    except:
        global badmessvideo
        badmessvideo = tk.Label(windlinkvideo, text='An error occurred, check url or connection')
        badmessvideo.pack()


def singlelinkvideo() :
    global windlinkvideo
    windlinkvideo = Toplevel()
    windlinkvideo.title('Download and convert a single video')
    windlinkvideo.geometry('500x200')
    messagewindlinkvideo = tk.Label(windlinkvideo, text='Please enter a proper YouTube link: ')
    messagewindlinkvideo.pack()
    global ytlinkvideo
    ytlinkvideo = Entry(windlinkvideo, width=50)
    ytlinkvideo.pack()
    singledlbuttonvideo = Button(windlinkvideo, text='Download and convert video to mp3', command=getvideodata)
    singledlbuttonvideo.pack()

choosebutton1 = tk.Button(root, text='Single mp3 Download (paste link)', 
                          activebackground='light green', highlightbackground='black', relief='raised', font='TIMES', 
                          width=30, bg='white', command=singlelink).place(rely='0.3')
choosebutton2 = tk.Button(root, text='Download mp3 from *.txt list', activebackground='light green', highlightbackground='black', relief='raised', font='TIMES',
                           width=30, bg='white', command=listlink).place(rely='0.4')
choosebutton3 = tk.Button(root, text='Download mp3 from YouTube Playlist', activebackground='light green', 
                          highlightbackground='black', relief='raised', font='TIMES', width=30, bg='white', command=playlistlink).place(rely='0.5')
choosebutton4 = tk.Button(root, text='Download Single Video (paste link)', activebackground='red', activeforeground='white', 
                          highlightbackground='black', relief='raised', font='TIMES', width=30, command=singlelinkvideo, bg='white').place(rely='0.6')

root.mainloop()