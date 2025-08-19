ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

# Install system dependencies (yt-dlp needs ffmpeg)
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Create startup script to handle environment variables properly
RUN echo '#!/bin/sh\nPORT=${PORT:-8080}\nexec uvicorn app:app --host 0.0.0.0 --port $PORT' > /app/start.sh && \
    chmod +x /app/start.sh

# Health check with proper environment variable handling
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Use the startup script
CMD ["/app/start.sh"]
