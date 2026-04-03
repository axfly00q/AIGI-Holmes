import os, sys
# ensure project root is on sys.path
sys.path.insert(0, os.getcwd())

from backend.main import app
import uvicorn

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=7860, log_level='info')
