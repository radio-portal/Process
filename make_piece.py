import pandas as pd
import subprocess
import os
import argparse
import re
from dotenv import load_dotenv
import json

load_dotenv()

parser = argparse.ArgumentParser(description='Process multiple MP3 files and generate transcripts.')
parser.add_argument('--mp3_file', required=True, help='Directory containing the MP3 files.')
parser.add_argument('--output_base_dir', required=True, help='Base directory where the output segments and transcripts will be stored.')
parser.add_argument('--date', required=True, help='Date in YYMMDD format, e.g. 240615.')
parser.add_argument('--time', required=True, help='Time string, e.g. 0900.')
parser.add_argument('--station', required=True, help='Station name.')
args = parser.parse_args()

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

def time_to_seconds(time_str):
    h, m = map(int, time_str.split(":"))
    return h * 3600 + m * 60

def apply_playlist_labels(df, playlist, broadcast_start_time):
    # 1. playlist 곡 구간(초 단위) 리스트 생성
    start_sec = time_to_seconds(broadcast_start_time)
    song_segments = []
    for song in playlist:
        song_time = song.get("Time")
        duration = song.get("Duration") or song.get("DurationSec")
        if not song_time or not duration:
            continue
        song_start_sec = time_to_seconds(song_time) - start_sec
        if song_start_sec < 0:
            continue
        # duration이 "mm:ss" 형식이면 초로 변환
        if isinstance(duration, str) and ":" in duration:
            mm, ss = map(int, duration.split(":"))
            duration_sec = mm * 60 + ss
        else:
            duration_sec = float(duration)
        song_end_sec = song_start_sec + duration_sec
        song_segments.append((song_start_sec, song_end_sec))

    # 2. 각 row를 곡 구간 기준으로 쪼개기
    new_rows = []
    for idx, row in df.iterrows():
        seg_start, seg_stop, label = float(row['start']), float(row['stop']), row['labels']
        cur = seg_start
        splits = []
        for song_start, song_end in song_segments:
            # 겹치는 구간 계산
            overlap_start = max(cur, song_start)
            overlap_end = min(seg_stop, song_end)
            if overlap_start < overlap_end:
                # 앞부분(겹치기 전)
                if cur < overlap_start:
                    splits.append({'labels': label, 'start': cur, 'stop': overlap_start})
                # play 구간
                splits.append({'labels': 'play', 'start': overlap_start, 'stop': overlap_end})
                cur = overlap_end
        # 남은 뒷부분
        if cur < seg_stop:
            splits.append({'labels': label, 'start': cur, 'stop': seg_stop})
        new_rows.extend(splits)
    new_df = pd.DataFrame(new_rows)
    return new_df

station = args.station
mp3_file = args.mp3_file

date_match = re.search(r'([a-zA-Z0-9]+)-(\d{4})\.mp3', os.path.basename(mp3_file))
if date_match:
    station = date_match.group(1) # station 추출
    output_dir = args.output_base_dir
    segment_dir = os.path.join(output_dir, "segments")
    transcript_dir = os.path.join(output_dir, "transcripts")
    read_csv = os.path.join(segment_dir, f"{args.date}{args.time}_play.csv")
    to_csv = os.path.join(transcript_dir, f"segments_info.csv")
    os.makedirs(segment_dir, exist_ok=True)
    os.makedirs(transcript_dir, exist_ok=True)
    
    if os.path.exists(read_csv):
        print(f"Processing {mp3_file} with associated CSV {read_csv}")
        df = pd.read_csv(read_csv, sep=',')

        playlist_json_path = os.path.join(os.getcwd(), "input", args.date, f"{station}-{args.time}-playlist.json")
        try:
            with open(playlist_json_path, 'r', encoding='utf-8') as f:
                playlist = json.load(f)
        except FileNotFoundError:
            print(f"Playlist file not found at {playlist_json_path}. Silent segments will not have song info.")
            playlist = []

        # 🌟 방송국별 playlist 기반 play label 덮어쓰기 및 초기화 로직
        mbc_playlist_index = 0 # MBC playlist 순차 처리를 위한 인덱스

        if station in ['kbs2fm', 'sbs'] and playlist:
            # 기존 로직: kbs2fm, sbs는 Time 정보 기반으로 play 라벨 덮어쓰기
            broadcast_start_time = f"{args.time[:2]}:{args.time[2:]}"
            # apply_playlist_labels 함수는 외부 정의 필요
            df = apply_playlist_labels(df, playlist, broadcast_start_time)
        elif station == 'mbc' and playlist:
            # MBC는 Time 정보가 없으므로, playlist의 곡을 순차적으로 사용하기 위해
            # apply_playlist_labels는 사용하지 않음.
            pass

        # 병합 로직 추가: (이전과 동일)
        merged_segments = []
        prev_row = None
        for idx, row in df.iterrows():
            row_start = float(row['start'])
            row_stop = float(row['stop'])
            # 1초 미만 간격이면 병합
            if prev_row is not None and row['labels'] == prev_row['labels'] and abs(row_start - float(prev_row['stop'])) < 1:
                prev_row['stop'] = row_stop
            else:
                if prev_row is not None:
                    merged_segments.append(prev_row)
                prev_row = row.copy()
                prev_row['start'] = row_start
                prev_row['stop'] = row_stop
        if prev_row is not None:
            merged_segments.append(prev_row)
        df = pd.DataFrame(merged_segments)

        song_index = 0
        group_id = 1
        segment_data = []

        for i in range(len(df)):
            row = df.iloc[i]
            label = row['labels']
            start_time = row['start']
            stop_time = row['stop']
            duration = stop_time - start_time

            seg = {
                'Id': group_id,
                'Start Time': start_time,
                'Stop Time': stop_time,
                'Duration': duration,
                'Type': label,
                'MP3 File': '',
                'Transcript File': '',
                'Transcript': ''
            }

            if label == 'play':
                seg['MP3 File'] = "N/A"
                seg['Transcript File'] = "N/A"
                
                matched_song_info = None

                if station in ['kbs2fm', 'sbs']:
                    # 기존 로직: Time 정보가 있는 방송국 (kbs2fm, sbs)
                    # playlist에서 해당 구간의 곡 정보 찾기 (start_time이 곡 시작 시간과 가장 가까운 곡을 찾음)
                    min_diff = float('inf')
                    for song in playlist:
                        song_time = song.get("Time")
                        if not song_time: continue
                        # 방송 시작 시간 기준 상대 초
                        # time_to_seconds 함수는 외부 정의 필요
                        song_start_sec = time_to_seconds(song_time) - time_to_seconds(f"{args.time[:2]}:{args.time[2:]}")
                        diff = abs(start_time - song_start_sec)
                        if diff < min_diff:
                            min_diff = diff
                            matched_song_info = song
                            
                elif station == 'mbc':
                    # 🌟 MBC 로직: Time 정보가 없으므로, play 세그먼트가 나타날 때마다 playlist를 순차적으로 사용
                    if mbc_playlist_index < len(playlist):
                        matched_song_info = playlist[mbc_playlist_index]
                        mbc_playlist_index += 1 # 인덱스 증가
                    
                
                if matched_song_info and matched_song_info.get('Artist') and matched_song_info.get('Title'):
                    seg['Transcript'] = f"[{matched_song_info['Artist']} - {matched_song_info['Title']}]"
                else:
                    seg['Transcript'] = "[play]" # 매칭된 곡이 없거나 정보 부족 시 기본값
                    
                segment_data.append(seg)
                group_id += 1
                continue
                
            elif label in ['speech', 'music']:
                label_prefix = f"{label}_"
                output_filename = os.path.join(segment_dir, f"{label_prefix}output_segment_{group_id}.mp3")
                # extract_segment 함수는 외부 정의 필요
                file_names, transcribed_text = extract_segment(
                    mp3_file,
                    start_time, duration, output_filename, label, transcript_dir
                )
                seg['MP3 File'] = file_names['MP3']
                seg['Transcript File'] = file_names['Transcript']
                seg['Transcript'] = transcribed_text
                segment_data.append(seg)
                group_id += 1
                
            else: # noise, noEnergy etc.
                label_prefix = f"{label}_"
                output_filename = os.path.join(segment_dir, f"{label_prefix}output_segment_{group_id}.mp3")
                # extract_segment 함수는 외부 정의 필요
                file_names, transcribed_text = extract_segment(
                    mp3_file,
                    start_time, duration, output_filename, label, transcript_dir
                )
                seg['MP3 File'] = file_names['MP3']
                seg['Transcript File'] = "N/A"
                seg['Transcript'] = ""
                segment_data.append(seg)
                group_id += 1

        # Now process extraction and transcription (이후 로직은 동일)
        segments_df = pd.DataFrame(segment_data)
        # Reorder columns to have ID first
        cols = ['Id', 'Start Time', 'Stop Time', 'Duration', 'Type', 'MP3 File', 'Transcript File', 'Transcript']
        segments_df = segments_df[cols]
        segments_df.to_csv(to_csv, index=False)
        print(f"Saved segment information to {to_csv}")
    else:
        print(f"CSV file {read_csv} not found. Skipping {mp3_file}.")