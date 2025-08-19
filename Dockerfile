FROM python:3.12-slim

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

# Expose port (Railway will set PORT env var)
EXPOSE 8080

# Health check with dynamic port
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD sh -c "curl -f http://localhost:\${PORT:-8080}/health || exit 1"

# Run the application with Railway's PORT env var
CMD sh -c "uvicorn app:app --host 0.0.0.0 --port \${PORT:-8080}"
