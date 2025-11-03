import re
import os
import argparse
from io import BytesIO
from PIL import Image

# Google GenAI 및 환경 설정 관련 라이브러리 (추가)
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# 1. Gemini Client 초기화
# ---------------------------------------------------------------------

load_dotenv()
try:
    # 환경 변수 GEMINI_API_SECOND가 설정되어 있음을 가정
    client = genai.Client(api_key=os.environ.get('GEMINI_API_IMAGE'))
except Exception as e:
    print(f"🚨 Google GenAI Client 초기화 오류: {e}")
    print("API 키 환경 변수 'GEMINI_API_SECOND' 설정을 확인해주세요.")
    client = None

# ---------------------------------------------------------------------
# 2. 요약본 파싱 함수 (동일)
# ---------------------------------------------------------------------

def parse_summary_by_id(full_summary_text):
    """전체 요약 텍스트를 ID별로 분리하고 각 ID의 정보를 구조화하여 반환합니다."""
    delimiter_pattern = re.compile(
        r'^(ID:\s*(\d+)\s*\[(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\][\s\S]*?)(?=^ID:\s*\d+\s*\[|\Z)',
        re.MULTILINE
    )
    matches = delimiter_pattern.findall(full_summary_text)
    structured_data = []
    
    for match in matches:
        full_block = match[0].strip()
        summary_id = int(match[1])
        start_time = float(match[2])
        stop_time = float(match[3])
        
        first_line_pattern = re.compile(r'^ID:\s*\d+\s*\[.*?\][\s\S]*?요약[\s\S]*?\n', re.MULTILINE)
        content_match = first_line_pattern.sub('', full_block, count=1).strip()
        
        # '제목' 정보 추출 (추가)
        title_match = re.search(r'\*\*제목:\*\*\s*(.+)', content_match)
        title = title_match.group(1).strip() if title_match else "제목 없음"

        structured_data.append({
            'id': summary_id,
            'start': start_time,
            'stop': stop_time,
            'title': title, # 제목 추가
            'content': content_match # 전체 내용 유지
        })
    return structured_data

# ---------------------------------------------------------------------
# 3. 이미지 생성 및 저장 함수 (동일)
# ---------------------------------------------------------------------

def generate_and_save_images(parsed_summaries, date_str, station_time, station):
    """
    파싱된 요약본 리스트를 기반으로 각 ID별 이미지를 생성하고 저장합니다.
    저장 경로: /home/dnlab/Project/{date_str}-{station}-{station_time}/ID_{ID번호}_image.png
    """
    if client is None:
        print("🚨 GenAI 클라이언트가 초기화되지 않아 이미지 생성을 건너뜁니다.")
        return
    
    # 🌟 출력 디렉토리 경로 구성: 날짜와 방송 정보를 포함
    output_base_dir = "/home/dnlab/processed" # 프로젝트의 기본 저장 위치를 /home/dnlab/Project로 가정
    output_dir = os.path.join(output_base_dir, f"{date_str}", f"{station}-{station_time}", "images")
        
    os.makedirs(output_dir, exist_ok=True)
    print(f"🖼️ 이미지는 다음 디렉토리에 저장됩니다: {output_dir}")
    
    for item in parsed_summaries:
        summary_id = item['id']
        summary_title = item['title'] # 제목 사용
        summary_content = item['content'] # 전체 내용 사용
        
        prompt = f"""
            다음 텍스트의 제목과 내용을 바탕으로 썸네일 이미지를 생성해 주세요.
            이미지에는 어떠한 텍스트도 포함하지 말아 주세요.
            광고, 워터마크, 로고 등을 포함하지 말아 주세요.
            
            ---
            **제목:** {summary_title}
            **내용:** {summary_content}
            ---
        """

        print(f"🖼️ ID {summary_id} (제목: '{summary_title[:20]}...')에 대한 이미지 생성 요청 중...")
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image", 
                contents=prompt
            )

            image_found = False
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    # 파일명: ID_{ID번호}_image.png
                    image_path = os.path.join(output_dir, f"summary_{summary_id}_image.png")
                    image = Image.open(BytesIO(part.inline_data.data))
                    image.save(image_path)
                    print(f"✅ ID {summary_id} 이미지 저장 완료: {image_path}")
                    image_found = True
                    break
                elif part.text is not None:
                    print(f"⚠️ ID {summary_id} 이미지 생성 실패. 모델 응답: {part.text[:50]}...")
            
            if not image_found:
                 print(f"⚠️ ID {summary_id} 이미지 생성 실패: 응답에서 이미지 데이터 파트가 발견되지 않았습니다.")

        except Exception as e:
            print(f"🚨 ID {summary_id} 이미지 생성 API 호출 오류: {e}")

# ---------------------------------------------------------------------
# 4. 파일 입력 및 처리 로직 (main 함수 수정)
# ---------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="특정 방송의 요약 파일을 분석하고 Gemini를 사용하여 이미지 생성 및 저장")
    # 🌟 수정: date, time, station 인수를 받도록 변경
    parser.add_argument('--date', type=str, required=True, help='날짜 (예: 250510)')
    parser.add_argument('--time', type=str, required=True, help='방송 시간 (예: 1400)')
    parser.add_argument('--station', type=str, required=True, help='방송국 이름 (예: kbs2fm)')
    args = parser.parse_args()

    date_str = args.date
    station_time = args.time
    station = args.station

    # 🌟 summary.txt 파일 경로 구성
    base_dir = '/home/dnlab/processed'
    transcript_dir = os.path.join(base_dir, f"{date_str}", f"{station}-{station_time}", "transcripts")
    summary_file_path = os.path.join(transcript_dir, "summary.txt")

    if not os.path.exists(summary_file_path):
        print(f"🚨 오류: Summary 파일을 찾을 수 없습니다: {summary_file_path}")
        exit(1)

    try:
        with open(summary_file_path, 'r', encoding='utf-8') as f:
            summary_text = f.read()
            
        # 1. 요약본 ID별로 파싱
        parsed_summaries = parse_summary_by_id(summary_text)

        print(f"✅ Summary 파일 '{summary_file_path}' 처리 완료. 총 {len(parsed_summaries)}개의 ID 발견.")
        
        if parsed_summaries:
            # 2. 파싱된 요약본을 기반으로 이미지 생성 및 저장
            # 🌟 date, time, station 정보를 전달하여 출력 경로에 활용
            generate_and_save_images(parsed_summaries, date_str, station_time, station)
        else:
            print("🔍 파싱된 요약본 ID가 없습니다. 이미지 생성을 건너뜜니다.")

    except Exception as e:
        print(f"🚨 파일을 읽거나 처리하는 중 심각한 오류 발생: {e}")