import os
import time
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
import yt_dlp
import uvicorn
from urllib.parse import urlparse

app = FastAPI(title="Audio URL Resolver", version="1.0.0")
security = HTTPBearer()

# Load environment variables
EXTRACTOR_TOKEN = os.getenv("EXTRACTOR_TOKEN")
if not EXTRACTOR_TOKEN:
    raise ValueError("EXTRACTOR_TOKEN environment variable is required")

# Rate limiting (simple in-memory counter)
request_counts = {}
RATE_LIMIT = 30  # requests per minute

class ExtractRequest(BaseModel):
    url: HttpUrl
    format: str = "m4a"  # "m4a" or "best"
    redirect: bool = False

class ExtractResponse(BaseModel):
    audio_url: str
    expiresAt: Optional[str] = None
    durationSec: Optional[int] = None
    title: Optional[str] = None
    channel: Optional[str] = None

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the bearer token"""
    if credentials.credentials != EXTRACTOR_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials

def check_rate_limit(request: Request):
    """Simple rate limiting"""
    client_ip = request.client.host
    current_time = time.time()
    minute_window = int(current_time // 60)
    
    key = f"{client_ip}:{minute_window}"
    count = request_counts.get(key, 0)
    
    if count >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    request_counts[key] = count + 1
    
    # Clean old entries (keep only current and previous minute)
    keys_to_remove = [k for k in request_counts.keys() if int(k.split(':')[1]) < minute_window - 1]
    for k in keys_to_remove:
        del request_counts[k]

def validate_youtube_url(url: str) -> bool:
    """Validate that URL is from YouTube"""
    parsed = urlparse(str(url))
    allowed_hosts = ['youtube.com', 'www.youtube.com', 'youtu.be', 'm.youtube.com']
    return parsed.hostname in allowed_hosts

def extract_audio_url(youtube_url: str, format_preference: str = "m4a") -> dict:
    """Extract audio URL using yt-dlp without downloading"""
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio' if format_preference == "m4a" else 'bestaudio',
        'quiet': True,
        'no_warnings': True,
        'extractaudio': False,  # Don't download, just extract info
        'noplaylist': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info without downloading
            info = ydl.extract_info(youtube_url, download=False)
            
            # Get the best audio format
            audio_url = info.get('url')
            if not audio_url:
                raise ValueError("No audio stream found")
            
            # Extract metadata
            title = info.get('title', 'Unknown')
            uploader = info.get('uploader', 'Unknown')
            duration = info.get('duration')  # in seconds
            
            return {
                'audio_url': audio_url,
                'title': title,
                'channel': uploader,
                'duration_sec': duration
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract audio URL: {str(e)}")

@app.post("/extract")
async def extract_audio_url_endpoint(
    request: Request,
    body: ExtractRequest,
    token: str = Depends(verify_token)
):
    """Resolve YouTube URL to direct audio stream URL"""
    
    # Check rate limit
    check_rate_limit(request)
    
    # Validate YouTube URL
    if not validate_youtube_url(str(body.url)):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    try:
        # Extract audio URL and metadata
        result = extract_audio_url(str(body.url), body.format)
        
        # Log request (without sensitive URLs)
        url_host = urlparse(str(body.url)).hostname
        print(f"Resolved audio for {url_host} video, duration: {result.get('duration_sec', 'unknown')}s")
        
        # Return redirect or JSON based on request
        if body.redirect:
            return RedirectResponse(url=result['audio_url'], status_code=302)
        else:
            return ExtractResponse(
                audio_url=result['audio_url'],
                title=result.get('title'),
                channel=result.get('channel'),
                durationSec=result.get('duration_sec')
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "Audio URL Resolver",
        "version": "1.0.0",
        "endpoints": {
            "POST /resolve": "Resolve YouTube URL to audio stream",
            "GET /healthz": "Health check"
        },
        "auth": "Bearer token required"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)