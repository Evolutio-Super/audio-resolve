from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import os, subprocess, tempfile, json

app = FastAPI(title="Audio Resolver")

EXTRACTOR_TOKEN = os.getenv("EXTRACTOR_TOKEN", "")

class ExtractReq(BaseModel):
    url: str
    format: str | None = "m4a"

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/extract")
def extract(req: ExtractReq, authorization: str | None = Header(None)):
    # Auth
    if not EXTRACTOR_TOKEN:
        raise HTTPException(status_code=500, detail="EXTRACTOR_TOKEN missing")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    if authorization.split(" ", 1)[1].strip() != EXTRACTOR_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

    # Resolve direct audio URL without downloading (yt-dlp returns JSON)
    # NOTE: We do NOT persist media. We only resolve a playable audio URL.
    try:
        cmd = [
            "yt-dlp",
            "-J",              # JSON
            "--no-warnings",
            "-f", "bestaudio/best",
            req.url
        ]
        out = subprocess.check_output(cmd, text=True)
        data = json.loads(out)
        # When a playlist-like response returns 'entries', choose first entry
        entry = data["entries"][0] if "entries" in data and data["entries"] else data
        # Find the best audio format URL
        fmts = entry.get("formats", [])
        audio = next((f for f in reversed(fmts) if f.get("acodec") and f.get("url")), None)
        if not audio:
            raise RuntimeError("No audio format found")
        return {
            "ok": True,
            "title": entry.get("title"),
            "duration": entry.get("duration"),
            "audio_url": audio["url"],
            "ext": audio.get("ext"),
            "abr": audio.get("abr")
        }
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"yt-dlp error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
