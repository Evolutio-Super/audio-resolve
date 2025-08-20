from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import os, subprocess, json

APP_TOKEN = os.environ.get("EXTRACTOR_TOKEN")

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

class ExtractBody(BaseModel):
    url: str
    format: str | None = "m4a"

@app.post("/extract")
def extract(
    body: ExtractBody,
    authorization: str = Header(default="")
):
    # simple bearer check
    if not APP_TOKEN:
        raise HTTPException(status_code=500, detail="EXTRACTOR_TOKEN not configured")
    if not authorization.startswith("Bearer ") or authorization.split(" ", 1)[1] != APP_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")

    # Produce a direct audio URL without downloading (yt-dlp -g)
    # Fallback to m4a, but allow other formats if needed.
    ytdlp_fmt = "bestaudio[ext=m4a]/bestaudio/best"
    try:
        result = subprocess.run(
            ["yt-dlp", "-g", "-f", ytdlp_fmt, body.url],
            check=True, capture_output=True, text=True
        )
        direct_url = result.stdout.strip().splitlines()[-1]
        return {"ok": True, "direct_audio_url": direct_url, "format": body.format or "m4a"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"yt-dlp error: {e.stderr or e.stdout}")
