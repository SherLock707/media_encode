import os
import subprocess
import json
import shutil
import time
import signal
from concurrent.futures import ThreadPoolExecutor
import threading
import sys

def convert_to_720p(input_file, output_file):
    process = None
    t_start_time = 0
    def monitor_time():
        # while process.poll() is None:
        #     t_elapsed_time = time.time() - t_start_time
        #     if t_elapsed_time > 0.00:
        #         print(f"Elapsed time: {t_elapsed_time:.2f} seconds")
        #     time.sleep(300) # 5min
        t_elapsed_time = 0
        while process.poll() is None:
            sys.stdout.flush()
            time.sleep(60) #300 5min
            t_elapsed_time = time.time() - t_start_time
            print(f"Elapsed time: {(t_elapsed_time/60):.2f} min", end='\r')
        print(f"Elapsed time: {(t_elapsed_time/60):.2f} min")
            

    title = os.path.splitext(os.path.basename(input_file))[0]
    print(f'==================ENCODING: {title}=====================')
    cmd = [
        'ffmpeg',
        # '-loglevel', 'error', 
        '-y',
        '-i', input_file,
        '-vf', 'scale=1280:720',
        '-c:v', 'libx265',
        '-r', '24000/1001',
        '-crf', '22',
        '-preset', 'slow',
        '-tune', 'animation',
        '-x265-params', 'limit-sao=1:deblock=1,1:bframes=8:ref=6:psy-rd=1.5:psy-rdoq=2:aq-mode=3',
        '-pix_fmt', 'yuv420p10le',
        '-map', '0',  # Copy all streams from the source
        '-c:s', 'copy',
        '-c:a', 'copy',
        '-metadata', f'title={title}',
        output_file
    ]
    
    start_time = time.time()
    # subprocess.run(cmd, check=True)

    output_log_file = 'ffmpeg_output.log'
    with open(output_log_file, 'a') as log_file:
        # subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT, check=True)
        process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
    
    # Record the start time
    t_start_time = time.time()
    time_monitor_thread = threading.Thread(target=monitor_time)
    time_monitor_thread.start()
    process.wait()
    time_monitor_thread.join()

    time_taken = (time.time() - start_time) / 60
    print(f"Time taken: {time_taken:.2f} Mins")
    print(f'==================COMPLETE: {title}=====================\n\n')

# Input and output folder paths
input_folder = '/run/media/itachi/DATA_SATA_4TB/Media/ENCODE/pending_encoding'
output_folder = '/run/media/itachi/DATA_SATA_4TB/Media/ENCODE/encoded_archive'

# Initialize a list to store the converted file names
converted_files = []

# Check if the JSON file exists, and if it does, load the list of converted files
json_file = 'encoded_file_list.json'
if os.path.exists(json_file):
    with open(json_file, 'r') as f:
        converted_files = json.load(f)


# Define a function for conversion
def convert_and_copy(input_file, output_file):
    # if not os.path.exists(output_file):
        # try:
        # Perform the conversion
    convert_to_720p(input_file, output_file)

    # Add the converted file to the list
    converted_files.append(os.path.basename(input_file))

    # Update the JSON file
    with open(json_file, 'w') as f:
        json.dump(converted_files, f, indent=4)


max_threads = 1
with ThreadPoolExecutor(max_threads) as executor:
    for root, dirs, files in os.walk(input_folder):
        for file in sorted(files):
            if file.endswith('.mkv'):
                # print(f'Found {file}')
                input_file_path = os.path.join(root, file)
                output_dir = os.path.join(output_folder, os.path.relpath(root, input_folder))
                output_file_path = os.path.join(output_dir, file.replace('.mkv', '_720p.mkv'))
                if file not in converted_files:
                    # print(f'New {file}')
                    os.makedirs(output_dir, exist_ok=True)
                    executor.submit(convert_and_copy, input_file_path, output_file_path)
            elif os.path.isfile(os.path.join(root, file)):  
                input_file_path = os.path.join(root, file)
                output_file_path = os.path.join(output_folder, os.path.relpath(input_file_path, input_folder))
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                shutil.copy(input_file_path, output_file_path)