import os
import re
import pandas as pd
import argparse
from pydub import AudioSegment

# 이전에 발생했던 KeyError를 해결하기 위해 'labels' 컬럼을 사용합니다. 
# 현재 코드에는 'labels'가 사용되고 있으므로 그대로 유지합니다.
LABEL_COLUMN = 'labels' 

def parse_summary_intervals(summary_path):
    segments = []
    segment_num = 0
    try:
        with open(summary_path, 'r', encoding='utf-8') as f:
            for line in f:
                # 🌟 ID 추출 로직 추가: 'ID: 1 [4.54 - 351.06]' 형태에서 ID와 구간 모두 추출
                m_id = re.match(r'ID:\s*(\d+)\s*\[(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\]', line)
                if m_id:
                    segment_num = int(m_id.group(1)) # ID를 사용
                    start = float(m_id.group(2))
                    stop = float(m_id.group(3))
                    # (ID, Start, Stop)
                    segments.append((segment_num, start, stop))
    except FileNotFoundError:
        print(f"Error: Summary file not found at {summary_path}")
    return segments

def create_label_csv(noenergy_csv_path, summary_path, label_csv_path):
    df = pd.read_csv(noenergy_csv_path)
    segments = parse_summary_intervals(summary_path)

    # 🌟 DEBUG: 입력 CSV의 컬럼 확인
    print(f"DEBUG: Input CSV Columns: {df.columns.tolist()}")

    # 🌟 오류 방지: 'labels' 컬럼이 있는지 다시 한번 확인
    if LABEL_COLUMN not in df.columns:
        print(f"🚨 Error: Column '{LABEL_COLUMN}' not found in the input CSV. Please check the column name.")
        return None

    assigned_segments = []
    for idx, row in df.iterrows():
        # label = row[LABEL_COLUMN] # 현재 코드에서는 사용되지만, 매칭 로직은 모든 세그먼트에 적용
        start = row['start']
        stop = row['stop']
        seg_num = 0
        
        # 🌟 수정된 매칭 로직: 모든 세그먼트가 겹치는 Summary ID 구간을 찾습니다.
        # speech뿐 아니라 모든 세그먼트(music, noise, noEnergy 등)를 긴 요약 구간에 할당합니다.
        for s_id, s_start, s_stop in segments:
            # CSV 세그먼트 [start, stop]이 Summary 구간 [s_start, s_stop]과 겹치는지 확인
            if not (stop <= s_start or start >= s_stop):
                seg_num = s_id # 요약본 ID를 Segment 번호로 할당
                break
        
        assigned_segments.append(seg_num)

    df['Segment'] = assigned_segments

    # --- 0번 Segment 채우기 로직 유지 (매칭되지 않은 구간을 앞뒤 ID로 채움) ---
    
    # 앞쪽 0번 segment -> 다음 segment로
    for i in range(len(df)):
        if df.loc[i, 'Segment'] == 0:
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
    
    # ----------------------------------------------------------------------

    # 60초 이상 music → silence로 변경 로직 유지
    new_labels = []
    for idx, row in df.iterrows():
        duration = row['stop'] - row['start']
        if row[LABEL_COLUMN] == 'music' and duration >= 60:
            new_labels.append('silence')
        else:
            new_labels.append(row[LABEL_COLUMN])
    df['labels'] = new_labels

    df.to_csv(label_csv_path, index=False)
    print(f"Saved label CSV to {label_csv_path}")
    return df

# 나머지 merge_segments 함수 및 __main__ 부분은 유지 (컬럼 이름 'labels' 사용 확인)
# ----------------------------------------------------------------------

def merge_segments(label_csv_path, segment_dir, output_dir):
    df = pd.read_csv(label_csv_path)
    os.makedirs(output_dir, exist_ok=True)

    merged_segments = {}
    for seg_num in df['Segment'].unique():
        merged_segments[seg_num] = AudioSegment.empty()

    # 파일 인덱스 카운터 초기화 (외부 스크립트와의 순서 일치 확인 필요)
    # 현재 코드는 idx + 1 을 사용하므로 그대로 유지합니다.
    
    for idx, row in df.iterrows():
        label = row['labels']
        seg_num = row['Segment']
        start = row['start']
        stop = row['stop']
        duration_ms = (stop - start) * 1000

        # idx + 1을 사용하므로, 0부터 시작하는 파일 생성 스크립트와 맞지 않을 수 있습니다.
        # 만약 파일 이름이 0부터 시작한다면 file_index = idx로 수정해야 합니다.
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
        if seg_num > 0: # Segment ID가 0이 아닌 것만 저장
            out_path = os.path.join(output_dir, f"merged_segment_{seg_num}.mp3")
            audio.export(out_path, format="mp3")
            print(f"Saved {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="특정 라디오 방송의 세그먼트를 병합")
    # 🌟 수정: date_str, time, station 모두 필수 인수로 받도록 변경
    parser.add_argument('--date', type=str, required=True, help='날짜 (예: 250510)')
    parser.add_argument('--time', type=str, required=True, help='방송 시간 (예: 1400)')
    parser.add_argument('--station', type=str, required=True, help='방송국 이름 (예: kbs2fm)')
    args = parser.parse_args()

    date_str = args.date
    station_time = args.time
    station = args.station
    
    base_dir = '/home/dnlab/processed'
    
    # 🌟 수정: 단일 폴더 경로를 직접 구성
    station_time_dir = f"{station}-{station_time}"
    full_path = os.path.join(base_dir, f"{date_str}-music", station_time_dir)

    if not os.path.isdir(full_path):
        print(f"🚨 오류: 디렉토리를 찾을 수 없습니다: {full_path}")
        exit()

    print(f"✅ 처리 시작: {date_str} {station}-{station_time}")

    segment_dir = os.path.join(full_path, "segments")
    transcript_dir = os.path.join(full_path, "transcripts")
    play_dir = os.path.join(full_path, "play")

    noenergy_csv = os.path.join(segment_dir, f"{date_str}{station_time}_play.csv")
    summary_txt = os.path.join(transcript_dir, f"summary.txt")
    label_csv = os.path.join(segment_dir, f"{date_str}{station_time}-label.csv")

    if not (os.path.exists(noenergy_csv) and os.path.exists(summary_txt)):
        print(f"[skip] 파일 없음: {noenergy_csv} 또는 {summary_txt}")
    else:
        # 1. 라벨 CSV 생성
        df_labeled = create_label_csv(noenergy_csv, summary_txt, label_csv)

        if df_labeled is not None:
            # 2. 병합 수행
            merge_segments(label_csv, segment_dir, play_dir)