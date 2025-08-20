FROM python:3.12-slim

# System deps (ffmpeg is required by yt-dlp)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# App code
COPY app.py .

# Railway provides PORT env; default 8080 for local
ENV PORT=8080

EXPOSE 8080

# Start server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
