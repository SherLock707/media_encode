import os
import subprocess
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# Check if the JSON file exists, and if it does, load the list of converted files
json_file = 'encoded_file_list.json'
if os.path.exists(json_file):
    with open(json_file, 'r') as f:
        converted_files = set(json.load(f))

# Function to convert a video to 720p
def convert_to_720p(input_file, output_file):
    title = os.path.splitext(os.path.basename(input_file))[0]
    print(f'==================PROCESSING: {title}=====================')
    cmd = [
        'ffmpeg',
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
        '-map', '0',
        '-c:s', 'copy',
        '-c:a', 'copy',
        '-metadata', f'title={title}',
        output_file
    ]
    
    start_time = time.time()
    # with open('ffmpeg_output.log', 'a') as log_file:
    #     subprocess.run(cmd, stdout=log_file, stderr=subprocess.STDOUT, check=True)

    with tqdm(total=100, desc='Progress', position=0, leave=True) as pbar:
        with open('ffmpeg_output.log', 'a') as log_file:
            process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, universal_newlines=True)
            for line in process.stdout:
                if 'frame=' in line and 'fps=' in line:
                    parts = line.split()
                    for part in parts:
                        if part.startswith('time='):
                            time_str = part.replace('time=', '').strip()
                            time_parts = time_str.split(':')
                            if len(time_parts) == 3:
                                hours, minutes, seconds = map(int, time_parts)
                                elapsed_seconds = hours * 3600 + minutes * 60 + seconds
                                pbar.n = elapsed_seconds
                                pbar.update(0)
            process.wait()

    time_taken = (time.time() - start_time) / 60
    print(f"Time taken: {time_taken:.2f} Mins")
    print(f'==================COMPLETE: {title}=====================\n\n')

# Function to convert and copy files
def convert_and_copy(input_file, output_file):
    if input_file.endswith('.mkv'):
        if os.path.basename(input_file) not in converted_files:
            convert_to_720p(input_file, output_file)
            converted_files.add(os.path.basename(input_file))
            with open(json_file, 'w') as f:
                json.dump(list(converted_files), f)
    else:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        shutil.copy(input_file, output_file)

# Input and output folder paths
input_folder = '/run/media/itachi/DATA_SATA_4TB/Media/ENCODE/pending_encoding'
output_folder = '/run/media/itachi/DATA_SATA_4TB/Media/ENCODE/encoded_archive'

# Initialize a list to store the converted file names
converted_files = set()

max_threads = 2
with ThreadPoolExecutor(max_threads) as executor:
    for root, dirs, files in os.walk(input_folder):
        for file in sorted(files):
            input_file_path = os.path.join(root, file)
            output_file_path = os.path.join(output_folder, os.path.relpath(input_file_path, input_folder))
            executor.submit(convert_and_copy, input_file_path, output_file_path)
