#!/bin/bash
exec dramatiq api.safety_queue:setup_safety_queue api.thread.chat.safety.safety_checkers.google_video_safety_checker --processes 2 --threads 8
