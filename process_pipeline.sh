#!/bin/bash

# 사용법: ./modify_pipeline.sh <날짜> <방송국>
if [ "$#" -ne 3 ]; then
    echo "사용법: $0 <날짜> <방송국> <시간>"
    exit 1
fi

DATE=$1
STATION=$2
TIME=$3

# 날짜 설정
INPUT_FILE="/home/dnlab/input/$DATE/$STATION-$TIME.mp3"
PROCESSED_DIR="/home/dnlab/processed/$DATE/$STATION-$TIME"

if [ -z "$INPUT_FILE" ]; then
    echo "No input file found for $DATE"
    exit 1
else
    echo "Processing file: $INPUT_FILE"
fi

source ~/anaconda3/etc/profile.d/conda.sh

# Step 1: ina-script.py 실행 (segment 환경)
conda activate segment
echo "[1] activate segment"
mkdir -p "$PROCESSED_DIR"
echo "[1] make dir $PROCESSED_DIR"
echo "[1] Process ina-script.py"
python /home/dnlab/Project/modify_process/ina-script.py --input_mp3_file "$INPUT_FILE" --output_dir "$PROCESSED_DIR" --date "$DATE" --time "$TIME"
echo "[1] Done"
conda deactivate

# # Step 2-1: remove-noenergy.py 실행 (segment 환경)
conda activate segment
echo "[2-1] Process remove-noenergy.py"
python /home/dnlab/Project/modify_process/remove-noenergy.py --date "$DATE" --station "$STATION" --time "$TIME"
echo "[2-1] Done"
conda deactivate

# # Step 2-2: modify-script.py 실행 (segment 환경)
conda activate segment
echo "[2-2] Process modify-script.py"
python /home/dnlab/Project/modify_process/modify-script.py --date "$DATE" --station "$STATION" --time "$TIME"
echo "[2-2] Done"
conda deactivate

# Step 3: make_piece.py 실행 (whisper 환경)
conda activate whisper
echo "[3] activate whisper"
echo "[3] Process make_piece.py"
python /home/dnlab/Project/modify_process/make_piece.py --mp3_file "$INPUT_FILE" --output_base_dir "$PROCESSED_DIR" --date "$DATE" --time "$TIME" --station "$STATION"
echo "[3] Done"
conda deactivate

# Step 4: summarize.py 실행 (summary 환경)
conda activate summary
echo "[4] activate summary"
echo "[4] Process summarize.py"
python /home/dnlab/Project/modify_process/summarize.py --csv_file "$PROCESSED_DIR/transcripts/segments_info.csv" --output_file "$PROCESSED_DIR/transcripts/summary.txt"
echo "[4] Done"
conda deactivate

# Step 5: merge_mp3.py 실행 (segment 환경)
conda activate segment
echo "[5] Process merge_mp3.py"
python /home/dnlab/Project/modify_process/merge_mp3.py --date $DATE --time $TIME --station $STATION
conda deactivate

# Step 6: create_image.py 실행 (summary 환경)
conda activate summary
echo "[6] Process create_image.py"
python /home/dnlab/Project/create_image.py --date $DATE --time $TIME --station $STATION


echo "All processes completed successfully!"