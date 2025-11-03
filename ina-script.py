import os
import subprocess
import argparse

# Set up argument parser
parser = argparse.ArgumentParser(description='Process a single MP3 file using ina_speech_segmenter.py.')
parser.add_argument('--input_mp3_file', required=True, help='Path to the MP3 file to process.')
parser.add_argument('--output_dir', required=True, help='Base directory where output CSV files will be stored. (should include station-time)')
parser.add_argument('--date', required=True, help='Date in YYMMDD format, e.g. 240615')
parser.add_argument('--time', required=True, help='Time string, e.g. 0900')

args = parser.parse_args()

def process_mp3_file(input_file, output_dir, csv_file):
    command = [
        'ina_speech_segmenter.py',
        '-i', input_file,
        '-o', output_dir,
        '-d', 'smn',    # Option for segmenter model
        '-g', 'false', # Option to disable GPU
        '-r', '0.02',
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 결과 파일명 변경
    for file in os.listdir(output_dir):
        if file.endswith('.csv'):
            old_file = os.path.join(output_dir, file)
            os.rename(old_file, csv_file)
            break
    print(f"Processed {input_file}, saved results to {csv_file}")

segments_dir = os.path.join(args.output_dir, "segments")
os.makedirs(segments_dir, exist_ok=True)
csv_file = os.path.join(segments_dir, f"{args.date}{args.time}.csv")
print(f"Processing: {args.input_mp3_file} -> {csv_file}")
process_mp3_file(args.input_mp3_file, segments_dir, csv_file)
