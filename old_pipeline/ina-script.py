import os
import subprocess
import argparse
import re
import csv

# Set up argument parser
parser = argparse.ArgumentParser(description='Process multiple MP3 files using ina_speech_segmenter.py.')
parser.add_argument('--input_mp3_dir', required=True, help='Directory containing the MP3 files to process.')
parser.add_argument('--output_dir', required=True, help='Base directory where output CSV files will be stored.')

args = parser.parse_args()

def process_mp3_file(input_file, output_dir, csv_file, station):
    command = [
        'ina_speech_segmenter.py',
        '-i', input_file,
        '-o', output_dir,
        '-d', 'smn',    # Option for segmenter model
        '-g', 'false', # Option to disable GPU
        '-r', '0.02',
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    for file in os.listdir(output_dir):
        if file.startswith(station) and file.endswith('.csv'):
            old_file = os.path.join(output_dir, file)
            os.rename(old_file, csv_file)
            break
    print(f"Processed {input_file}, saved results to {csv_file}")

for mp3_file in os.listdir(args.input_mp3_dir):
    if not mp3_file.endswith('.mp3'):
        continue

    match = re.search(r'([a-zA-Z0-9]+)-(\d{4})\.mp3$', mp3_file)
    if match:
        station = match.group(1)
        time = match.group(2)
        date_dir = os.path.basename(args.input_mp3_dir)
        print(f"{date_dir}")
        output_subdir = os.path.join(args.output_dir, f"{station}-{time}", "segments")
        os.makedirs(output_subdir, exist_ok=True)
        csv_file = os.path.join(output_subdir, f"{date_dir}{time}.csv")
        input_mp3_path = os.path.join(args.input_mp3_dir, mp3_file)
        print(f"Processing: {input_mp3_path} -> {csv_file}")
        process_mp3_file(input_mp3_path, output_subdir, csv_file, station)
    else:
        print(f"Skipping {mp3_file}, no valid time found in the filename.")
