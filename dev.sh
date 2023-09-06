#!/bin/bash
set -euo pipefail
exec flask run --host 0.0.0.0 --port 8000 --reload --debug
