#!/bin/sh
set -e

# HF Spaces only allows writes under /tmp at runtime. Duckling creates a ./log dir on startup.
cd /tmp
duckling-example-exe -p 8000 &
echo "[Duckling] Starting on :8000 (cwd=/tmp)..."

ready=0
i=0
while [ "$i" -lt 30 ]; do
  if python -c "
import urllib.request
urllib.request.urlopen(
    urllib.request.Request(
        'http://127.0.0.1:8000/parse',
        data=b'locale=en_US&text=tomorrow&dims=[\"time\"]',
        method='POST',
    ),
    timeout=2,
)
" 2>/dev/null; then
    echo "[Duckling] Ready on :8000"
    ready=1
    break
  fi
  i=$((i + 1))
  sleep 1
done

if [ "$ready" -eq 0 ]; then
  echo "[Duckling] WARNING: not ready after 30s"
fi

cd /app
exec uvicorn main:app --host 0.0.0.0 --port 7860
