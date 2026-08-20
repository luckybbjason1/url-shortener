"""
URL Shortener Service - 自动赚钱服务
提供 URL 短链接服务，按点击量和订阅收费
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import hashlib
import time
import random
import sqlite3
from pathlib import Path
from datetime import datetime

app = FastAPI(title="URL Shortener Service", version="1.0.0")

DB_PATH = Path.home() / "桌面" / "url-shortener" / "urls.db"
DB_PATH.parent.mkdir(exist_ok=True)

class ShortenRequest(BaseModel):
    url: str
    custom_slug: Optional[str] = None
    expire_days: Optional[int] = None

@app.get("/")
async def root():
    return {
        "message": "URL Shortener Service",
        "version": "1.0.0",
        "pricing": {
            "free": "100 URLs, 1000 clicks/month",
            "basic": "$9.99/month - 1000 URLs, 10000 clicks",
            "pro": "$29.99/month - 10000 URLs, 100000 clicks",
            "enterprise": "$99.99/month - Unlimited"
        }
    }

@app.post("/shorten")
async def shorten(request: ShortenRequest):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            clicks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    ''')
    conn.commit()
    
    slug = request.custom_slug or hashlib.md5(f"{request.url}{time.time()}".encode()).hexdigest()[:8]
    
    expires_at = None
    if request.expire_days:
        expires_at = datetime.now().isoformat()
    
    try:
        cursor.execute(
            "INSERT INTO urls (slug, original_url, expires_at) VALUES (?, ?, ?)",
            (slug, request.url, expires_at)
        )
        conn.commit()
        short_url = f"https://short.link/{slug}"
        return {"short_url": short_url, "slug": slug, "original_url": request.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.get("/{slug}")
async def redirect(slug: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT original_url, clicks FROM urls WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="URL not found")
    
    cursor.execute("UPDATE urls SET clicks = clicks + 1 WHERE slug = ?", (slug,))
    conn.commit()
    conn.close()
    
    return {"redirect": row[0], "clicks": row[1] + 1}

@app.get("/stats")
async def stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM urls")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(clicks) FROM urls")
    clicks = cursor.fetchone()[0] or 0
    conn.close()
    return {"total_urls": total, "total_clicks": clicks, "revenue_estimate": f"${clicks * 0.001:.2f}"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
