#!/bin/bash

# Specify the log file path
log_file="/mnt/cf36a2d7-ecf4-46c7-a76a-5defe1ad7659/Poko_Projects/ytdler/output.log"

#activate virtual environment
cd /mnt/cf36a2d7-ecf4-46c7-a76a-5defe1ad7659/Poko_Projects/ytdler
source venv/bin/activate >> "$log_file" 2>&1

echo "Start of Session: $(date)">> "$log_file"

# Redirect standard output and standard error to the log file
python3 poko1_2.py >> "$log_file" 2>&1

echo "End of Session" >> "$log_file"
echo "----------------------------------------" >> "$log_file"

#deactivate virtual environment
deactivate

/bin/bash