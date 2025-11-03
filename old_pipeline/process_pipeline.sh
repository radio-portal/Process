#!/bin/bash

# 날짜 설정
YESTERDAY=$(date -d "YESTERDAY" +"%y%m%d")
INPUT_DIR="/home/dnlab/input/$YESTERDAY"
PROCESSED_DIR="/home/dnlab/processed/$YESTERDAY"
STATIONS_FILE="/home/dnlab/input/stations.txt"

INPUT_FILE=$(find "$INPUT_DIR" -type f -name "*.mp3")

if [ -z "$INPUT_FILE" ]; then
    echo "No input file found for $YESTERDAY"
    exit 1
else
    echo "Processing file: $INPUT_FILE"
fi

# Step 1: ina-script.py 실행 (segment 환경)
source ~/anaconda3/etc/profile.d/conda.sh
conda activate segment
echo "[1] activate segment"
mkdir -p "$PROCESSED_DIR"
echo "[1] make dir $PROCESSED_DIR"
echo "[1] Process ina-script.py"
python /home/dnlab/Project/ina-script.py --input_mp3_dir "$INPUT_DIR" --output_dir "$PROCESSED_DIR"
echo "[1] Done"
conda deactivate

# Step 2: modify_ina.py 실행 (segment 환경)
conda activate segment
echo "[2] Process modify_ina.py"
python /home/dnlab/Project/modify_ina.py "$PROCESSED_DIR"
echo "[2] Done"
conda deactivate

# Step 3: make_piece.py 실행 (whisper 환경)
conda activate whisper
echo "[3] activate whisper"
echo "[3] Process make_piece.py"
python /home/dnlab/Project/make_piece.py --mp3_file_dir "$INPUT_DIR" --output_base_dir "$PROCESSED_DIR" --transcript_base_dir "$PROCESSED_DIR" --stations_file "$STATIONS_FILE"
echo "[3] Done"
conda deactivate

echo "All processes completed successfully!"

# Step 4: Run summarize.py in the 'whisper' environment
conda activate summary
echo "Process summarize.py"
python /home/dnlab/Project/summary.py --date $YESTERDAY
echo "Done"
conda deactivate

echo "All processes completed successfully!"
