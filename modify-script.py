import pandas as pd
import argparse
import os
import sys
import json

def merge_no_energy_first(df):
    merged_data = []
    i = 0
    while i < len(df):
        current_row = df.iloc[i].copy()
        if current_row['labels'] == 'noEnergy' or current_row['labels'] == 'noise':
            if i < len(df) - 1:
                next_row = df.iloc[i + 1].copy()
                next_row['start'] = current_row['start']
                merged_data.append(next_row)
                i += 2
            else:
                merged_data.append(current_row)
                i += 1
        else:
            merged_data.append(current_row)
            i += 1
    return pd.DataFrame(merged_data)

def merge_rows(df):
    merged_data = []
    current_row = df.iloc[0].copy()
    for i in range(1, len(df)):
        next_row = df.iloc[i]
        if current_row['stop'] - current_row['start'] <= 0:
            if current_row['labels'] != next_row['labels']:
                continue
            current_row['stop'] = max(current_row['stop'], next_row['stop'])
            current_row['labels'] = next_row['labels']
        else:
            merged_data.append(current_row.copy())
            current_row = next_row.copy()
    merged_data.append(current_row)
    return pd.DataFrame(merged_data)

def merge_play_segments(df):
    """연속된 play segment를 하나로 합침 + play끼리 간격 100초 미만이면 병합"""
    if df.empty:
        return df
    merged = []
    prev = df.iloc[0].copy()
    for i in range(1, len(df)):
        curr = df.iloc[i]
        if prev['labels'] == 'play' and curr['labels'] == 'play' and (curr['start'] - prev['stop']) < 240:
            prev['stop'] = curr['stop']
        else:
            merged.append(prev)
            prev = curr.copy()
    merged.append(prev)
    return pd.DataFrame(merged)

def time_str_to_seconds(tstr):
    # 'HH:MM:SS' 또는 'MM:SS' 또는 'SS' 형식 지원
    parts = tstr.split(':')
    parts = [float(p) for p in parts]
    if len(parts) == 3:
        return parts[0]*3600 + parts[1]*60 + parts[2]
    elif len(parts) == 2:
        return parts[0]*60 + parts[1]
    else:
        return parts[0]

def time_arg_to_seconds(timestr):
    # 'HHMM' 형식(예: '1400')을 분 단위로 변환
    hour = int(timestr[:2])
    minute = int(timestr[2:])
    return hour*60 + minute

def process_file(date, station, time):
    # base_dir = os.path.join(os.getcwd(), "processed", date, f"{station}-{time}", "segments")
    base_dir = os.path.join(os.getcwd(), "processed", f"{date}-music", f"{station}-{time}", "segments")
    input_file = os.path.join(base_dir, f"{date}{time}.csv")
    output_csv = os.path.join(base_dir, f"{date}{time}_play.csv")

    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist.")
        sys.exit(1)

    print(f"Processing {input_file}...")
    df = pd.read_csv(input_file, sep='\t')

    # playlist 정보 (Time, Duration 사용)
    playlist_json = os.path.join(os.getcwd(), "input", date, f"{station}-{time}-playlist.json")
    with open(playlist_json, "r", encoding="utf-8") as f:
        playlist = json.load(f)
    playlist_times = []
    playlist_durations = []
    base_time_sec = time_arg_to_seconds(time)  # 기준 초
    for item in playlist:
        # Time을 초로 변환 후 기준 초를 빼서 상대 초로 저장
        if 'Time' in item:
            abs_time_sec = time_str_to_seconds(item['Time'])
            rel_time_sec = abs_time_sec - base_time_sec
            playlist_times.append(rel_time_sec)
        else:
            playlist_times.append(None)
        # duration이 null/None/'' 등 비어있으면 None으로 저장
        dur = item.get('Duration')
        if dur is None or dur == '' or str(dur).lower() == 'null':
            playlist_durations.append(None)
        else:
            playlist_durations.append(float(dur))

    # 결과 세그먼트 리스트
    merged_segments = []
    play_candidates = []
    n = len(df)
    i = 0
    while i < n:
        row = df.iloc[i]
        if row['labels'] == 'speech':
            # 연속된 speech/noEnergy/noise를 모두 합병
            start = row['start']
            stop = row['stop']
            j = i + 1
            while j < n and df.iloc[j]['labels'] in ['speech', 'noEnergy', 'noise']:
                stop = df.iloc[j]['stop']
                j += 1
            merged_segments.append({'labels': 'speech', 'start': start, 'stop': stop})
            i = j
        elif row['labels'] == 'music':
            # music/noEnergy/noise 연속 블록 합치기
            block_start = row['start']
            block_stop = row['stop']
            j = i + 1
            while j < n and df.iloc[j]['labels'] in ['music', 'noEnergy', 'noise']:
                block_stop = df.iloc[j]['stop']
                j += 1
            duration = block_stop - block_start
            if duration >= 60:
                play_candidates.append({'start': block_start, 'stop': block_stop})
            else:
                merged_segments.append({'labels': 'music', 'start': block_start, 'stop': block_stop})
            i = j
        elif row['labels'] == 'noEnergy':
            # music/noEnergy/noise 블록에 포함되어 처리됨
            i += 1
        else:
            # noise 등 기타 라벨은 무시
            i += 1

    # play 후보들 간격 240초 미만이면 play로 라벨링하지 않고 music으로 둠
    play_candidates = sorted(play_candidates, key=lambda x: x['start'])
    valid_play = []
    for idx, block in enumerate(play_candidates):
        prev_stop = play_candidates[idx-1]['stop'] if idx > 0 else None
        next_start = play_candidates[idx+1]['start'] if idx < len(play_candidates)-1 else None
        # 앞뒤 play 후보와의 간격이 240초 이상이어야 play로 인정
        prev_ok = (prev_stop is None) or (block['start'] - prev_stop >= 100)
        next_ok = (next_start is None) or (next_start - block['stop'] >= 100)
        if prev_ok and next_ok:
            valid_play.append(block)
        else:
            merged_segments.append({'labels': 'music', 'start': block['start'], 'stop': block['stop']})
    for block in valid_play:
        merged_segments.append({'labels': 'play', 'start': block['start'], 'stop': block['stop']})

    final_df = pd.DataFrame(merged_segments)
    final_df = final_df.sort_values('start').reset_index(drop=True)
    final_df = merge_play_segments(final_df)
    final_df.to_csv(output_csv, index=False)
    print(f"모든 곡에 대해 play 변환 및 병합 완료! 결과 파일: {output_csv}")

def select_plays(play_candidates, playlist_count, min_gap=0):
    play_candidates = sorted(play_candidates, key=lambda x: x['start'])
    selected = []
    last_stop = None
    for block in play_candidates:
        if last_stop is None or block['start'] - last_stop >= min_gap:
            selected.append(block)
            last_stop = block['stop']
        if len(selected) == playlist_count:
            break
    return selected

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Full segmenter: remove noEnergy/noise, merge, and assign music segment Ids.')
    parser.add_argument('--date', type=str, required=True, help='Date in YYMMDD format, e.g. 240615')
    parser.add_argument('--station', type=str, required=True, help='Station name, e.g. kbs')
    parser.add_argument('--time', type=str, required=True, help='Time string, e.g. 0900')
    args = parser.parse_args()
    process_file(args.date, args.station, args.time)