FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .

EXPOSE 8080
