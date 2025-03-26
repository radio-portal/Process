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

# Function to run the ina_speech_segmenter script with options
def process_mp3_file(input_file, output_dir, csv_file):
		# Run the ina_speech_segmenter script with -d sm and -g false options
		command = [
				'ina_speech_segmenter.py',
				'-i', input_file,
				'-o', output_dir,
				'-d', 'smn',	# Option for segmenter model
				'-g', 'false',	# Option to gender
		]
		subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

		# output- 이 붙은 파일에서 output- 제거
		for file in os.listdir(output_dir):
				if file.startswith('mbc-') and file.endswith('.csv'):
						old_file = os.path.join(output_dir, file)
						os.rename(old_file, csv_file)
						break
		print(f"Processed {input_file}, saved results to {csv_file}")
# Iterate through all MP3 files in the input_mp3_dir (which is a directory like 250304)
for mp3_file in os.listdir(args.input_mp3_dir):
		# Only process .mp3 files
		if not mp3_file.endswith('.mp3'):
				continue

		# Extract time (HHMM) from the mp3 file name (assuming time is in the format mbc-1400.mp3)
		time_match = re.search(r'(\d{4})\.mp3$', mp3_file)	# Match the last 4 digits before ".mp3"
		if time_match:
				time = time_match.group(1)	# Extract time (HHMM)

				# Extract the date (250304) from the input_mp3_dir path, assuming the directory name is the date
				date_dir = os.path.basename(args.input_mp3_dir)
				print(f"{date_dir}")
				# Define the output subdirectory based on the input directory name (e.g., 250304)
				output_subdir = os.path.join(args.output_dir, f"mbc-{time}")
				os.makedirs(output_subdir, exist_ok=True)

				# CSV file path: /home/segments/{date}/mbc-{time}/{date}{time}.csv
				csv_file = os.path.join(output_subdir, f"{date_dir}{time}.csv")	# e.g., /home/segments/250304/mbc-1400/2503041400.csv

				# Full path to the input MP3 file
				input_mp3_path = os.path.join(args.input_mp3_dir, mp3_file)	# e.g., /home/input/250304/mbc-1400.mp3

				# Process the MP3 file with the segmenter and the additional options
				print(f"Processing: {input_mp3_path} -> {csv_file}")	# Debug output to confirm paths
				process_mp3_file(input_mp3_path, output_subdir, csv_file)	# Process the file

		else:
				print(f"Skipping {mp3_file}, no valid time found in the filename.")
