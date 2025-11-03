import csv
import re
import os
import argparse
from google import genai
from google.genai.errors import APIError
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict

MAX_PROMPT_LENGTH = 3000

load_dotenv()

client = genai.Client(api_key=os.environ.get('GEMINI_API_SECOND'))

def clean_transcript(transcript):
    """Remove text in square brackets and trim whitespace."""
    return re.sub(r'\[.*?\]', '', transcript).strip()

def summary_request(transcript):
    """Send a request to the OpenAI API to summarize the transcript."""
    clean_text = clean_transcript(transcript)

    prompt = f"""
    다음은 라디오 프로그램을 받아적은 텍스트야. 텍스트를 아래 조건에 맞게 요약해줘.
    1. 제목, 주요 내용, 청취자 사연, 광고 정보를 순서대로 포함하여 요약해야 해.
    2. 제목은 주요 내용과 청취자 사연, 음악을 바탕으로 흥미와 관심을 이끌 수 있어야 하고, 광고 내용이 들어가서는 안돼.
    3. 청취자 사연과 광고 정보는 있을 수도 있고 없을 수도 있어. 없다면 없다고 표시해.
    4. 청취자 사연은 [전화번호 또는 도시 또는 ~~동, 청취자 이름 등]을 포함할 수도 있고 포함하지 않을 수도 있어. 이는 매번 달라.
    5. 청취자 사연은 연속으로 여러 사람이 소개될 수 있어. 그럴 경우 구간을 나눠서 처리해.
    6. 광고 정보는 간단하게 제품, 회사, 특징만 요약해주면 돼.
    7. 유튜브에서 나오는 텍스트는 절대 처리하지 않아. 예를 들어 구독과 좋아요 같은 것은 오류야.
    8. 내용, 사연, 광고 정보는 각각 없을 수도 있어. 없다면 '없음'으로만 표시해.
    9. 주요 내용에 광고 정보가 들어가면 안돼.
    10. 다음 태그 중 가장 적절한 태그 최대 3개를 골라 마지막 줄에 적어.
    - [사연, 음악, 게스트, 토크, 정보, 퀴즈, 연애, 건강, 공지]
    - 청취자 사연이 없을 시 사연 태그는 넣지 마.

    텍스트:
    {clean_text}
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "max_output_tokens": 4096,
            "temperature": 0.4,
        }
    )
    try:
        if response.text is None:
            block_reason = None
            if response.candidates and response.candidates[0].finish_reason:
                block_reason = response.candidates[0].finish_reason.name
            
                print(f"경고: Gemini 응답 텍스트가 None입니다. 차단 사유: {block_reason}. Prompt length: {len(clean_text)}.")
                return "요약 오류"
        
        return response.text.strip()
    except APIError as e:
        print(f"Gemini API 오류: {e}")
        return ""
    except Exception as e:
        print(f"예기치 않은 오류 발생: {e}")
        return ""

# def recursive_summary(text):
#     """
#     텍스트가 MAX_PROMPT_LENGTH보다 길면 분할하여 요약하고, 
#     최종적으로 하나의 요약본을 반환합니다.
#     """
#     # 텍스트가 이미 충분히 짧다면 바로 요약 요청
#     if len(text) <= MAX_PROMPT_LENGTH:
#         return summary_request(text)

#     # 텍스트를 MAX_PROMPT_LENGTH 크기의 청크(chunk)로 나눔
#     chunk_size = MAX_PROMPT_LENGTH 
    
#     # 한국어 토큰이 문자당 2~3토큰인 점을 고려하여, 안전하게 문자 수를 토큰 제한보다 작게 설정
#     # (예: MAX_PROMPT_LENGTH를 3000 정도로 설정하여 LLM API의 토큰 제한에 맞추는 것이 좋습니다.)
    
#     chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    
#     # 1단계 요약: 각 청크를 요약
#     summaries = []
#     for i, chunk in enumerate(chunks):
#         # 각 청크를 요약할 때는 '다음 내용을 요약하시오'와 같은 프롬프트를 추가할 수 있습니다.
#         summaries.append(summary_request(chunk))
        
#     # 2단계 요약: 요약본들을 다시 합쳐서 최종 요약 요청 (재귀 호출)
#     combined_summaries = " ".join(summaries)

#     # 재귀적으로 다시 호출하여 최종적으로 하나의 짧은 요약본을 만듭니다.
#     return recursive_summary(combined_summaries)

def process_single_file(csv_path, out_path):
    print(f"Processing: {csv_path}")

    if not os.path.exists(csv_path):
        print(f"Input file {csv_path} does not exist.")
        return

    with open(csv_path, 'r', encoding='utf-8-sig') as csvfile, \
         open(out_path, 'w', encoding='utf-8') as outfile:

        reader = csv.DictReader(csvfile)

        combined_transcript = ""
        section_id = 1
        section_start = None
        section_end = None
        section_duration = 0

        for row in reader:
            row_type = row['Type'].lower()
            try:
                duration = float(row['Duration'])
                start = float(row['Start Time'])
                stop = float(row['Stop Time'])
            except Exception as e:
                print(f"Error parsing numeric values in row: {e}")
                continue

            transcript = row['Transcript']
            clean_text = clean_transcript(transcript)

            if section_start is None:
                section_start = start
            section_end = stop
            section_duration += duration

            if row_type == 'play':
                music_info = transcript.strip()
                # summary = recursive_summary(combined_transcript.strip())
                summary = summary_request(combined_transcript.strip())
                minutes = int(section_duration // 60)
                seconds = int(section_duration % 60)
                outfile.write(f"ID: {section_id}  [{section_start:.2f} - {section_end:.2f}] 약 {minutes}분 {seconds}초 구간 요약\n")
                outfile.write(summary + "\n")
                outfile.write(f"음악 정보: {music_info}\n")
                outfile.write("-" * 40 + "\n")

                section_id += 1
                section_start = None
                section_end = None
                section_duration = 0
                combined_transcript = ""
                
            elif row_type in ['speech', 'music']:
                combined_transcript += clean_text + " "

            if len(combined_transcript) > MAX_PROMPT_LENGTH:
                    # summary = recursive_summary(combined_transcript.strip())
                    summary = summary_request(combined_transcript.strip())
                    minutes = int(section_duration // 60)
                    seconds = int(section_duration % 60)
                    outfile.write(f"ID: {section_id}  [{section_start:.2f} - {section_end:.2f}] 약 {minutes}분 {seconds}초 구간 요약\n")
                    outfile.write(summary + "\n")
                    outfile.write(f"음악 정보: [없음]\n")
                    outfile.write("-" * 40 + "\n")

                    section_id += 1
                    section_start = None
                    section_end = None
                    section_duration = 0
                    combined_transcript = ""

        if combined_transcript.strip():
            # summary = recursive_summary(combined_transcript.strip())
            summary = summary_request(combined_transcript.strip())
            minutes = int(section_duration // 60)
            seconds = int(section_duration % 60)
            outfile.write(f"ID: {section_id}  [{section_start:.2f} - {section_end:.2f}] 약 {minutes}분 {seconds}초 남은 구간 요약\n")
            outfile.write(summary + "\n")
            outfile.write("음악 정보: [없음]\n")

    print(f"Summary saved to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize radio transcript segments using OpenAI.')
    parser.add_argument('--csv_file', type=str, required=True, help='Path to segments_info.csv file')
    parser.add_argument('--output_file', type=str, required=True, help='Path to save summary.txt')
    args = parser.parse_args()
    process_single_file(args.csv_file, args.output_file)
