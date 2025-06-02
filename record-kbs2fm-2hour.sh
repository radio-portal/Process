#!/bin/bash

DAY=$(date +%y%m%d)
TIME=$(date +%H%M)

OUTPUT_DIR="/home/dnlab/input/$DAY"
OUTPUT_FILE="$OUTPUT_DIR/kbs2fm-$TIME.mp3"
mkdir -p "$OUTPUT_DIR"

URL=$(curl -s "https://cfpwwwapi.kbs.co.kr/api/v1/landing/live/channel_code/25" | grep -o '"service_url":"[^"]*' | head -1 | sed 's/"service_url":"//')

if [[ -n "$URL" ]]; then

    ffmpeg -reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 5 -i "$URL" -t 7200 -acodec mp3 "$OUTPUT_FILE" > /home/dnlab/Log/kbs2fm-$TIME.log 2>&1 &
#    ffmpeg -i "$URL" -acodec mp3 "$OUTPUT_FILE" > /dev/null 2>&1 &
    pid_player=$!
else
    echo "Error: Failed to retrieve the stream URL."
    exit 1
fi

sleep 7200

pkill -P $pid_player
kill $pid_player
