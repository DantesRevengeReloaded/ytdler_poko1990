#el
import sqlite3
import os
from pokodler_config import *


def create_db():
    conn = sqlite3.connect(os.path.join(appfolder, 'downloaded_songs.db'))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS downloaded_songs
                 (ID INTEGER PRIMARY KEY, Type text, Title text, Time_Length real, Size_MB real, Downloaded_Date text, URL text)''')
    conn.commit()
    conn.close()

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