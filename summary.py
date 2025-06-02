import csv
import re
import os
import argparse
from openai import OpenAI
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get('OPEN_AI_API_KEY'))

def clean_transcript(transcript):
    """Remove text in square brackets and trim whitespace."""
    return re.sub(r'\[.*?\]', '', transcript).strip()

def summary_request(transcript):
    """Send a request to the OpenAI API to summarize the transcript."""
    clean_text = clean_transcript(transcript)

    prompt = f"""
    다음은 라디오 프로그램을 받아적은 텍스트 입니다. 아래 조건에 맞게 요약해주기 바랍니다.
    1. 음악을 기준으로 나누어 제목, 주요 내용, 청취자 사연, 음악 소개, 광고 정보를 포함하여 요약 바랍니다.
    2. 제목은 주요 내용과 청취자 사연, 음악을 바탕으로 흥미와 관심을 이끌 수 있어야 합니다. 광고 내용이 들어가서는 안됩니다.
    3. 청취자 사연과 음악 소개, 광고 정보는 있을 수도 있고 없을 수도 있습니다. 없다면 없다고 표시해주면 됩니다.
    4. 청취자 사연은 전화번호 또는 도시 또는 동 이름과 청취자 이름을 포함할 수도 있고 포함하지 않을 수도 있습니다. 이는 매번 다를 수 있습니다.
    5. 청취자 사연은 연속으로 여러 사람이 소개될 수 있습니다. 그럴 경우 조각을 나누어 주시기 바랍니다.
    6. 음악 소개는 제목과 가수 또는 연주악기 등에 대한 소개가 나옵니다. 제목이나 가수가 한국어가 아닌 다른 언어라면 주어진 텍스트에는 잘못 표기되어 있을 수 있습니다. 이를 바르게 고쳐 작성해주어야 합니다.
    7. 음악 소개는 보통 1곡이지만 2곡 또는 연속적으로 3곡을 소개해줄 수도 있습니다.
    8. 광고 정보는 간단하게 제품, 회사, 특징만 요약해주면 됩니다.
    9. 유튜브에서 나오는 텍스트는 처리하지 않습니다. 예를 들어 구독과 좋아요 같은 것은 오류입니다.
    10. 내용, 사연, 음악 소개, 광고 정보는 각각 없을 수도 있습니다. 없다면 '없음'으로만 표시해주면 됩니다.
    11. 주요 내용에 광고 정보가 들어가면 안됩니다.
    12. 다음 태그 중 가장 적절한 태그 최대 3개를 골라 마지막 줄에 적어주세요.
    - 사연, 음악, 게스트, 토크, 정보, 퀴즈, 연애, 건강, 공지
    - 청취자 사연이 없을 시 사연 태그는 넣지 마세요.
    - 음악 소개가 없을 시 음악 태그는 넣지 마세요.

    텍스트:
    {clean_text}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
        temperature=0.5,
        n=1
    )

    return response.choices[0].message.content.strip()

def process_file_by_date(base_dir, date_str):
    """
    Process transcript CSV files for given date in base_dir.
    Looks for files named like 'segments_info_{date}{time}.csv' in
    /home/dnlab/processed/{date}/{station}-{time}/transcripts/
    """

    print(f"Processing date: {date_str}")

    # 예상 디렉토리 경로: /home/dnlab/processed/{date}
    date_dir = os.path.join(base_dir, date_str)

    if not os.path.exists(date_dir):
        print(f"Input directory {date_dir} does not exist.")
        return

    # 찾은 CSV 파일 리스트 (full path)
    csv_files = []

    # 하위 디렉토리 탐색
    for station_time_dir in os.listdir(date_dir):
        full_dir = os.path.join(date_dir, station_time_dir, 'transcripts')
        if not os.path.isdir(full_dir):
            continue

        # transcripts 내 파일 확인
        for f in os.listdir(full_dir):
            if f == 'segments_info.csv':
                csv_files.append(os.path.join(full_dir, f))

    if not csv_files:
        print("No matching CSV files found.")
        return

    # 시간 순 정렬 (파일명에 시간 포함되어 있다고 가정)
    csv_files.sort()

    for csv_path in csv_files:
        print(f"Processing file: {csv_path}")

        # 파일명에서 {time} 추출 (예: segments_info_2406150900.csv → 0900)
        match = re.search(r'segments_info_\d{6}(\d{4})\.csv', os.path.basename(csv_path))
        if match:
            time_str = match.group(1)
        else:
            time_str = "unknown"

        out_path = os.path.join(os.path.dirname(csv_path), f'summary.txt')

        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile, \
             open(out_path, 'w', encoding='utf-8') as outfile:

            reader = csv.DictReader(csvfile)

            combined_transcript = ""
            current_duration = 0
            seg_start = None
            seg_end = None

            for row in reader:
                if row['Type'].lower() != 'speech':
                    continue

                try:
                    duration = float(row['Duration'])
                    start = float(row['Start Time'])
                    stop = float(row['Stop Time'])
                except Exception as e:
                    print(f"Error parsing numeric values in row: {e}")
                    continue

                transcript = row['Transcript']
                clean_text = clean_transcript(transcript)

                if seg_start is None:
                    seg_start = start

                seg_end = stop
                combined_transcript += clean_text + " "
                current_duration += duration

                if current_duration >= 100 and combined_transcript.strip():
                    summary = summary_request(combined_transcript.strip())
                    outfile.write(f"[{seg_start:.2f} - {seg_end:.2f}] 약 {int(current_duration // 60)}분 {int(current_duration % 60)}초 구간 요약\n")
                    outfile.write(summary + "\n")
                    outfile.write("-" * 40 + "\n")

                    combined_transcript = ""
                    current_duration = 0
                    seg_start = None
                    seg_end = None

            # 남은 구간 요약
            if combined_transcript.strip():
                summary = summary_request(combined_transcript.strip())
                if seg_start is not None and seg_end is not None:
                    minutes = int(current_duration // 60)
                    seconds = int(current_duration % 60)
                    outfile.write(f"[{seg_start:.2f} - {seg_end:.2f}] 약 {minutes}분 {seconds}초 남은 구간 요약\n")
                else:
                    outfile.write("[시간 정보 없음] 남은 구간 요약\n")
                outfile.write(summary + "\n")

        print(f"Summary saved to {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize radio transcript segments using OpenAI.')
    parser.add_argument('--date', type=str, required=True, help='Date in YYMMDD format, e.g. 240615')
    args = parser.parse_args()

    BASE_DIR = '/home/dnlab/processed'  # 기본 경로

    process_file_by_date(BASE_DIR, args.date)
