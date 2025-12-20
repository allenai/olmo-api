#!/bin/bash
cd ../playground-api/
exec dramatiq src.safety_queue.set_up_safety_queue:set_up_safety_queue src.safety_queue.video_safety_handler --processes 1 --threads 1 --watch src/safety_queue