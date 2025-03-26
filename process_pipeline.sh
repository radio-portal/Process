#!/bin/bash

# Date
#YESTERDAY=$(date +"%y%m%d") # for test
YESTERDAY=$(date -d "yesterday" +"%y%m%d")
INPUT_DIR="/home/dnlab/input/$YESTERDAY"

INPUT_FILE=$(find "$INPUT_DIR" -type f -name "*.mp3")

if [ -z "$INPUT_FILE" ]; then
		echo "No input file found for $YESTERDAY"
		exit 1
else
		echo "Processing file: $INPUT_FILE"
fi

# Step 1: Run ina-script.py in the 'segment' environment
source ~/anaconda3/etc/profile.d/conda.sh

conda activate segment
echo "activate segment"
mkdir -p /home/dnlab/segments/$YESTERDAY
echo "make dir segments/$YESTERDAY"
echo "Process ina-script.py"
python /home/dnlab/Project/ina-script_gpu.py --input_mp3_dir "$INPUT_DIR" --output_dir /home/dnlab/segments/$YESTERDAY
echo "Done"
conda deactivate

# Step 2: Run remove_noenergy.py in the 'segment' environment
conda activate segment
echo "Process remove-noenergy.py"
python /home/dnlab/Project/remove-noenergy.py /home/dnlab/segments/$YESTERDAY
echo "Done"
conda deactivate

# Step 3: Run segmenter.py in the 'whisper' environment
conda activate whisper
echo "activate whisper"
mkdir -p /home/dnlab/transcripts/$YESTERDAY
echo "make dir transcripts/$YESTERDAY"
echo "Process segmenter.py"
python /home/dnlab/Project/segmenter.py --mp3_file_dir "$INPUT_DIR" --output_base_dir /home/dnlab/segments/$YESTERDAY --transcript_base_dir /home/dnlab/transcripts/$YESTERDAY --stations_file /home/dnlab/input/stations.txt
echo "Done"
conda deactivate

# Step 4: Run summarize.py in the 'whisper' environment
conda activate summary
echo "Process summarize.py"
python /home/dnlab/Project/summarize.py --input_directory /home/dnlab/transcripts/$YESTERDAY --date $YESTERDAY
echo "Done"
conda deactivate

echo "All processes completed successfully!"
