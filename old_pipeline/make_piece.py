import pandas as pd
import subprocess
import os
import argparse
import re
from dotenv import load_dotenv

load_dotenv()

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
    file_names = {'MP3': '', 'Transcript': ''}
    if label == 'speech' or label == 'music':
        if label == 'speech':
            transcript_filename = f"speech_{int(start)}.txt"
        elif label == 'music':
            transcript_filename = f"music_{int(start)}.txt"
        full_transcript_path = os.path.join(transcript_dir, transcript_filename)
        whisper_command = [
            'whisper',
            output_file,
            '--model', 'large',
            '--language', 'ko',
            '--output_format', 'txt',
            '--device', 'cuda',
            '--condition_on_previous_text', 'False',
            '--output_dir', transcript_dir,
        ]
        transcription = subprocess.run(whisper_command, stdout=subprocess.PIPE, text=True)
        transcribed_text = transcription.stdout.strip()
        with open(full_transcript_path, 'w') as f:
            f.write(transcribed_text)
        file_names['Transcript'] = transcript_filename
    file_names['MP3'] = os.path.basename(output_file)
    return file_names, transcribed_text

stations = load_stations(args.stations_file)
mp3_files = [f for f in os.listdir(args.mp3_file_dir) if f.endswith('.mp3')]
for mp3_file in mp3_files:
    date_match = re.search(r'([a-zA-Z0-9]+)-(\d{4})\.mp3', mp3_file)
    if date_match:
        station = date_match.group(1)
        if not any(station_name in station for station_name in stations):
            print(f"Skipping {mp3_file}: Station {station} not in the list.")
            continue
        date_str = os.path.basename(os.path.normpath(args.output_base_dir))
        time_str = date_match.group(2)
        print(date_str)
        output_dir = os.path.join(args.output_base_dir, f"{station}-{time_str}")
        segment_dir = os.path.join(output_dir, "segments")
        transcript_dir = os.path.join(output_dir, "transcripts")
        read_csv = os.path.join(segment_dir, f"{date_str}{time_str}-noenergy.csv")
        to_csv = os.path.join(transcript_dir, f"segments_info.csv")
        os.makedirs(segment_dir, exist_ok=True)
        os.makedirs(transcript_dir, exist_ok=True)
        if os.path.exists(read_csv):
            print(f"Processing {mp3_file} with associated CSV {read_csv}")
            df = pd.read_csv(read_csv, sep=',')
            segment_data = []
            for index, row in df.iterrows():
                if row['labels'] in ['speech', 'music']:
                    start_time = row['start']
                    stop_time = row['stop']
                    duration = stop_time - start_time
                    label_prefix = 'music_' if row['labels'] == 'music' else 'speech_'
                    output_filename = os.path.join(segment_dir, f"{label_prefix}output_segment_{index + 1}.mp3")
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
            segments_df = pd.DataFrame(segment_data)
            segments_df.to_csv(to_csv, index=False)
            print(f"Saved segment information to {to_csv}")
        else:
            print(f"CSV file {read_csv} not found. Skipping {mp3_file}.")
