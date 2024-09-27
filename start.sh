#!/bin/bash

echo "Worker Initiated"

echo "Starting WebUI API"
python /ComfyUI/main.py &
echo "Starting RunPod Handler"
python -u /api_handler.py