#!/bin/bash

DAY=$(date +%y%m%d)
TIME=$(date +%H%M)

OUTPUT_DIR="/home/dnlab/input/$DAY"
OUTPUT_FILE="$OUTPUT_DIR/mbc-economic-$TIME.mp3"
mkdir -p "$OUTPUT_DIR"

URL=$(curl -s "https://sminiplay.imbc.com/aacplay.ashx?agent=webapp&channel=sfm" | grep -oP 'https?://[^"]+')

if [[ -n "$URL" ]]; then

    ffmpeg -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -i "$URL" -t 480 -acodec mp3 "$OUTPUT_FILE" > /home/dnlab/Log/mbc-economic.log 2>&1 &
#    ffmpeg -i "$URL" -acodec mp3 "$OUTPUT_FILE" > /dev/null 2>&1 &
    pid_player=$!
else
    echo "Error: Failed to retrieve the stream URL."
    exit 1
fi

sleep 3600

pkill -P $pid_player
kill $pid_player
