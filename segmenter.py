import pandas as pd
import subprocess
import os
import argparse
import re
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get('OPEN_AI_API_KEY'))

# Set up argument parser
parser = argparse.ArgumentParser(description='Process multiple MP3 files and generate transcripts.')
parser.add_argument('--mp3_file_dir', required=True, help='Directory containing the MP3 files.')
parser.add_argument('--output_base_dir', required=True, help='Base directory where the output segments will be stored.')
parser.add_argument('--transcript_base_dir', required=True, help='Base directory where transcripts will be stored.')
parser.add_argument('--stations_file', required=True, help='File containing list of station names.')
args = parser.parse_args()

def load_stations(file_path):
		with open(file_path, 'r') as file:
				stations = [line.strip() for line in file.readlines()]
		return stations

# Function to run ffmpeg command for extracting segments
def extract_segment(input_file, start, duration, output_file, label, transcript_dir):
		command = [
				'ffmpeg',
				'-i', input_file,
				'-ss', str(start),
				'-t', str(duration),
				'-c', 'copy',
				output_file,
				'-y'
		]
		transcribed_text = ""
		subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		print("done: ", command)
		
		file_names = {'MP3': '', 'Transcript': ''}	# To store the filenames of the mp3 and text file
		
		if label == 'speech' or label == 'music':
				if label == 'speech':	 
						transcript_filename = f"speech_{int(start)}.txt"
				elif label == 'music':
						transcript_filename = f"music_{int(start)}.txt"

				full_transcript_path = f"{transcript_dir}/{transcript_filename}"
				whisper_command = [
						'whisper',
						output_file,
						'--model', 'large',
						'--language', 'ko',
						'--output_format', 'txt',
						'--device', 'cuda',
						'--condition_on_previous_text', 'False',
						'--output_dir', transcript_dir
				]
				transcription = subprocess.run(whisper_command, stdout=subprocess.PIPE, text=True)
				transcribed_text = transcription.stdout.strip()
				with open(full_transcript_path, 'w') as f:
						f.write(transcribed_text)
				file_names['Transcript'] = transcript_filename

		file_names['MP3'] = os.path.basename(output_file)
		
		return file_names, transcribed_text

stations = load_stations(args.stations_file)

# Process each MP3 file in the directory
mp3_files = [f for f in os.listdir(args.mp3_file_dir) if f.endswith('.mp3')]

for mp3_file in mp3_files:
		# Extract date from the mp3 file name (assuming format: {station}-{time}.mp3)
		date_match = re.search(r'([a-zA-Z0-9]+)-(\d{4})\.mp3', mp3_file)
		if date_match:
				station = date_match.group(1)
				
				if not any(station_name in station for station_name in stations):
						print(f"Skipping {mp3_file}: Station {station} not in the list.")
						continue

				date_str = os.path.basename(os.path.normpath(args.output_base_dir)) 
				time_str = date_match.group(2)	# HHMM
				
				print(date_str)
				# Define directories and file paths based on the extracted date
				output_dir = os.path.join(args.output_base_dir, f"{station}-{time_str}")
				transcript_dir = os.path.join(args.transcript_base_dir, f"transcript-{station}-{time_str}")
				read_csv = os.path.join(output_dir, f"{date_str}{time_str}-noenergy.csv")
				to_csv = os.path.join(transcript_dir, f"segments_info_{date_str}{time_str}.csv")
				
				# Create directories if they don't exist
				os.makedirs(output_dir, exist_ok=True)
				os.makedirs(transcript_dir, exist_ok=True)

				# Check if the CSV file exists before processing
				if os.path.exists(read_csv):
						print(f"Processing {mp3_file} with associated CSV {read_csv}")
						
						# Load the input segment meta file data
						df = pd.read_csv(read_csv, sep=',')
						
						segment_data = []

						# Process each segment in the CSV
						for index, row in df.iterrows():
								if row['labels'] in ['speech', 'music']:
										start_time = row['start']
										stop_time = row['stop']
										duration = stop_time - start_time
										label_prefix = 'music_' if row['labels'] == 'music' else 'speech_'
										output_filename = os.path.join(output_dir, f"{label_prefix}output_segment_{index + 1}.mp3")
										print("for loop in ", start_time)
										file_names, transcribed_text = extract_segment(
												os.path.join(args.mp3_file_dir, mp3_file),
												start_time, duration, output_filename, row['labels'], transcript_dir
										)
										segment_data.append({
												'Start Time': start_time,
												'Stop Time': stop_time,
												'Duration': duration,
												'Type': row['labels'],
												'MP3 File': file_names['MP3'],
												'Transcript File': file_names['Transcript'],
												'Transcript': transcribed_text
										})
						
						# Create a DataFrame from the segment data and write to CSV
						segments_df = pd.DataFrame(segment_data)
						segments_df.to_csv(to_csv, index=False)
						print(f"Saved segment information to {to_csv}")
				else:
						print(f"CSV file {read_csv} not found. Skipping {mp3_file}.")