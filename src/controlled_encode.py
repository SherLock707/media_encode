import os
import subprocess
import json
import shutil
import time
import signal
import concurrent.futures
import threading

max_threads = 1
executor = concurrent.futures.ThreadPoolExecutor(max_threads)
thread_semaphore = threading.Semaphore(max_threads)

# Flag to indicate if threads should be killed.
paused = False
kill_threads_flag = False

def pause_threads():
    global paused
    paused = True

def resume_threads():
    global paused
    paused = False
    thread_semaphore.release()

def kill_threads():
    global kill_threads_flag
    kill_threads_flag = True
    executor.shutdown(wait=False)

def submit_task(task, *args, **kwargs):
    global kill_threads_flag
    while paused:
        pass  # Wait while paused
    if kill_threads_flag:
        return
    thread_semaphore.acquire()
    return executor.submit(task, *args, **kwargs)

# Function to handle Ctrl+C (SIGINT) signal
def handle_sigint(signum, frame):
    kill_threads()
    print("KILLED ALL")
    exit(0)

# Function to handle Ctrl+P (SIGUSR1) signal
def handle_pause(signum, frame):
    pause_threads()
    print("PAUSED ALL")

# Function to handle Ctrl+R (SIGUSR2) signal
def handle_resume(signum, frame):
    resume_threads()
    print("RESUMED ALL")

# Set up signal handlers
signal.signal(signal.SIGINT, handle_sigint)  # Ctrl+C
signal.signal(signal.SIGUSR1, handle_pause)  # Ctrl+P
signal.signal(signal.SIGUSR2, handle_resume)  # Ctrl+R

def convert_to_720p(input_file, output_file):
    title = os.path.splitext(os.path.basename(input_file))[0]
    print(f'==================PROCESSING: {title}=====================')
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
        subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT, check=True)

    time_taken = (time.time() - start_time) / 60
    print(f"Time taken: {time_taken:.2f} Mins")
    print(f'==================COMPLETE: {title}=====================\n\n')

# Input and output folder paths
# input_folder = '/run/media/itachi/DATA_SATA_4TB/Media/ENCODE/pending_encoding'
# output_folder = '/run/media/itachi/DATA_SATA_4TB/Media/ENCODE/encoded_archive'
input_folder = '/run/media/itachi/DATA_SATA_4TB/Media/ENCODE/test/input'
output_folder = '/run/media/itachi/DATA_SATA_4TB/Media/ENCODE/test/output'

# Initialize a list to store the converted file names
converted_files = []

# Check if the JSON file exists, and if it does, load the list of converted files
json_file = 'encoded_file_list_test.json'
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


with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
    for root, dirs, files in os.walk(input_folder):
        if kill_threads_flag:
            break
        
        for file in sorted(files):
            if file.endswith('.mkv'):
                input_file_path = os.path.join(root, file)
                output_dir = os.path.join(output_folder, os.path.relpath(root, input_folder))
                output_file_path = os.path.join(output_dir, file.replace('.mkv', '_720p.mkv'))
                
                if file not in converted_files:
                    os.makedirs(output_dir, exist_ok=True)
                    submit_task(convert_and_copy, input_file_path, output_file_path)
            elif os.path.isfile(os.path.join(root, file)):
                input_file_path = os.path.join(root, file)
                output_file_path = os.path.join(output_folder, os.path.relpath(input_file_path, input_folder))
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                shutil.copy(input_file_path, output_file_path)