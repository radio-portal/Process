## Process Overview
<img width="1847" height="593" alt="image" src="https://github.com/user-attachments/assets/1cc006eb-32a9-4546-95d7-deba5c4fa6b5" />

### process_pipeline.sh
- 자동 녹음 : record/
- 음성/음악 분리 : ina-script.py >> remove-noenergy.py >> modify-script.py
- 텍스트 전사(STT) : make_piece.py
- 요약/조각화 : summarize.py >> merge_mp3.py
- 이미지 생성 : create_image.py
