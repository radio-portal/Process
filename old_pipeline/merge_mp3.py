import os
import re
import pandas as pd
from pydub import AudioSegment

def parse_summary_intervals(summary_path):
    segments = []
    segment_num = 0
    with open(summary_path, 'r', encoding='utf-8') as f:
        for line in f:
            m = re.match(r'\[(\d+\.?\d*) - (\d+\.?\d*)\]', line)
            if m:
                segment_num += 1
                start = float(m.group(1))
                stop = float(m.group(2))
                segments.append((segment_num, start, stop))
    return segments

def create_label_csv(noenergy_csv_path, summary_path, label_csv_path):
    df = pd.read_csv(noenergy_csv_path)
    segments = parse_summary_intervals(summary_path)

    assigned_segments = []
    for idx, row in df.iterrows():
        label = row['labels']
        start = row['start']
        stop = row['stop']
        seg_num = 0
        if label == 'speech':
            for s_num, s_start, s_stop in segments:
                if not (stop <= s_start or start >= s_stop):
                    seg_num = s_num
                    break
        assigned_segments.append(seg_num)

    df['Segment'] = assigned_segments

    # 앞쪽 0번 segment -> 다음 segment로
    for i, row in df.iterrows():
        if row['Segment'] == 0:
            for j in range(i + 1, len(df)):
                if df.loc[j, 'Segment'] > 0:
                    df.at[i, 'Segment'] = df.loc[j, 'Segment']
                    break

    # 뒤쪽 0번 segment -> 이전 segment로
    for i in reversed(range(len(df))):
        if df.loc[i, 'Segment'] == 0:
            for j in reversed(range(i)):
                if df.loc[j, 'Segment'] > 0:
                    df.at[i, 'Segment'] = df.loc[j, 'Segment']
                    break

    # 60초 이상 music → silence로 변경
    new_labels = []
    for idx, row in df.iterrows():
        duration = row['stop'] - row['start']
        if row['labels'] == 'music' and duration >= 60:
            new_labels.append('silence')
        else:
            new_labels.append(row['labels'])
    df['labels'] = new_labels

    df.to_csv(label_csv_path, index=False)
    print(f"Saved label CSV to {label_csv_path}")
    return df

def merge_segments(label_csv_path, segment_dir, output_dir):
    df = pd.read_csv(label_csv_path)
    os.makedirs(output_dir, exist_ok=True)

    merged_segments = {}
    for seg_num in df['Segment'].unique():
        merged_segments[seg_num] = AudioSegment.empty()

    for idx, row in df.iterrows():
        label = row['labels']
        seg_num = row['Segment']
        start = row['start']
        stop = row['stop']
        duration_ms = (stop - start) * 1000

        file_index = idx + 1
        file_name = f"{label}_output_segment_{file_index}.mp3"
        file_path = os.path.join(segment_dir, file_name)

        if label == 'silence':
            silence = AudioSegment.silent(duration=duration_ms)
            merged_segments[seg_num] += silence
            continue

        if os.path.exists(file_path):
            try:
                audio = AudioSegment.from_file(file_path)
                merged_segments[seg_num] += audio
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        else:
            print(f"Missing file: {file_path}")

    for seg_num, audio in merged_segments.items():
        out_path = os.path.join(output_dir, f"merged_segment_{seg_num}.mp3")
        audio.export(out_path, format="mp3")
        print(f"Saved {out_path}")

if __name__ == "__main__":
    # 기본 설정
    date_str = '250522'
    station_time = '2200'
    station = 'mbc'
    base_dir = '/home/dnlab/processed'
    segment_dir = os.path.join(base_dir, date_str, f"{station}-{station_time}", "segments")
    transcript_dir = os.path.join(base_dir, date_str, f"{station}-{station_time}", "transcripts")
    play_dir = os.path.join(base_dir, date_str, f"{station}-{station_time}", "play")

    noenergy_csv = os.path.join(segment_dir, f"{date_str}{station_time}-noenergy.csv")
    summary_txt = os.path.join(transcript_dir, f"summary_{date_str}{station_time}.txt")
    label_csv = os.path.join(segment_dir, f"{date_str}{station_time}-label.csv")

    # 1. 라벨 CSV 생성
    create_label_csv(noenergy_csv, summary_txt, label_csv)

    # 2. 병합 수행
    merge_segments(label_csv, segment_dir, play_dir)
