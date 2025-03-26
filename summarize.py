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

    # Prompt for OpenAI
    prompt = f"""
    다음은 MBC에서 진행되는 라디오 프로그램을 받아적은 텍스트 입니다. 아래 조건에 맞게 요약해주기 바랍니다.
    1. 음악을 기준으로 나누어 제목, 주요 내용, 청취자 사연, 음악 소개, 광고 정보를 포함하여 요약 바랍니다.
    2. 제목은 주요 내용과 청취자 사연, 음악을 바탕으로 흥미가 생길 수 있는 짧은 한 줄이어야 합니다. 광고 내용이 들어가서는 안됩니다.
    3. 청취자 사연과 음악 소개, 광고 정보는 있을 수도 있고 없을 수도 있습니다. 없다면 없다고 표시해주면 됩니다.
    4. 청취자 사연은 전화번호 또는 도시 또는 동 이름과 청취자 이름을 포함할 수도 있고 포함하지 않을 수도 있습니다. 이는 매번 다를 수 있습니다.
    5. 청취자 사연은 연속으로 여러 사람이 소개될 수 있습니다. 그럴 경우 조각을 나누어 주시기 바랍니다.
    6. 음악 소개는 제목과 가수 또는 연주악기 등에 대한 소개가 나옵니다. 제목이나 가수가 한국어가 아닌 다른 언어라면 주어진 텍스트에는 잘못 표기되어 있을 수 있습니다. 이를 바르게 고쳐 작성해주어야 합니다.
    7. 음악 소개는 보통 1곡이지만 2곡 또는 연속적으로 3곡을 소개해줄 수도 있습니다.
    8. 광고 정보는 간단하게 제품, 회사, 특징만 요약해주면 됩니다.
    9. 유튜브에서 나오는 텍스트는 처리하지 않습니다. 예를 들어 구독과 좋아요 같은 것은 오류입니다.
    10. 내용, 사연, 음악 소개, 광고 정보는 각각 없을 수도 있습니다. 없다면 '없음'으로만 표시해주면 됩니다.
    11. 주요 내용에 광고 정보가 들어가면 안됩니다.

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

def process_today_file(input_directory, date_str=None):
    """Process transcript file for the specified date."""
    # 날짜 형식 통일: process_pipeline.sh와 동일하게 YYMMDD 형식 사용
    if date_str is None:
        # 어제 날짜를 YYMMDD 형식으로 가져옴 (process_pipeline.sh와 동일)
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%y%m%d')  # 240615 형식
    
    print(f"Processing files for date: {date_str}")
    
    # 처리할 파일들을 저장할 리스트
    files_to_process = []

    # Traverse the directory structure
    for root, dirs, files in os.walk(input_directory):
        for file in files:
            # 파일명 패턴: segments_info로 시작하고 날짜가 포함된 csv 파일 찾기
            if file.startswith('segments_info') and file.endswith('.csv') and date_str in file:
                files_to_process.append((root, file))

    # 시간순으로 정렬 (파일명에 포함된 시간 정보 사용)
    files_to_process.sort(key=lambda x: x[1])  # 파일명으로 정렬

    # 각 파일 처리
    for root, file in files_to_process:
        csv_file_path = os.path.join(root, file)
        output_file_path = os.path.join(root, f'summary-{date_str}.txt')

        print(f"Processing {csv_file_path}...")

        with open(csv_file_path, 'r', encoding='utf-8-sig') as csvfile, open(output_file_path, 'w', encoding='utf-8') as outfile:
            reader = csv.DictReader(csvfile)
            combined_transcript = ""
            current_duration = 0
            seg_start = 0

            for row in reader:
                duration = float(row['Duration'])
                transcript = row['Transcript']
                start = row['Start Time']
                stop = row['Stop Time']
                seg_stop = stop

                clean_text = clean_transcript(transcript)
                combined_transcript += clean_text
                current_duration += duration

                if current_duration > 100 and len(combined_transcript) > 10:
                    summary = summary_request(combined_transcript)
                    minute = round(float(seg_stop) - float(seg_start)) // 60
                    seconds = round(float(seg_stop) - float(seg_start)) % 60
                    outfile.write(f"[{seg_start} : {seg_stop}] {minute}분 {seconds}초\n")
                    outfile.write(summary + "\n")
                    outfile.write("--------------------------------------------\n")
                    combined_transcript = ""
                    current_duration = 0
                    seg_start = seg_stop

            # Process the remaining transcript
            if combined_transcript:
                summary = summary_request(combined_transcript)
                outfile.write("Summary: " + summary + "\n")

        print(f"Summary saved to {output_file_path}")

    if not files_to_process:
        print(f"No files found for date: {date_str}")

# Main execution
if __name__ == "__main__":
    # 명령줄 인자 파싱 추가
    parser = argparse.ArgumentParser(description='Process transcript files and generate summaries.')
    parser.add_argument('--input_directory', type=str, default='/home/dnlab/transcripts',
                        help='Base directory containing transcript files')
    parser.add_argument('--date', type=str, default=None,
                        help='Date in YYMMDD format (e.g., 240615). If not provided, yesterday\'s date will be used.')
    
    args = parser.parse_args()
    
    # 입력된 인자로 함수 실행
    process_today_file(args.input_directory, args.date)