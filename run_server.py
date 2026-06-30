import os, sys
# ensure project root is on sys.path
sys.path.insert(0, os.getcwd())

# Load .env before importing app so all env vars (e.g. SERPER_API_KEY) are available
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.main import app
import uvicorn

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=7860, log_level='info')
