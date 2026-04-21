FROM python:3.10-slim

WORKDIR /app

# System deps for Pillow / reportlab
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxrender1 libxext6 fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-app.txt .
COPY CLIP/ ./CLIP/
RUN pip install --no-cache-dir -r requirements-app.txt

COPY . .

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
