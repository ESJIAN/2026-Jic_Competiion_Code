
import requests
import sys
import os
import time
from pathlib import Path

from src.support.logger import logger

try:
    # Use localhost since we are on the same machine
    r = requests.get('http://127.0.0.1:8000/api/camera/stream', stream=True, timeout=2)
    logger.info(f"Status Code: {r.status_code}")
    logger.info(f"Headers: {r.headers}")
    # Read a bit of content
    for chunk in r.iter_content(chunk_size=1024):
        logger.info(f"Received chunk of size {len(chunk)}")
        break
except Exception as e:
    logger.error(f"Error: {e}")
