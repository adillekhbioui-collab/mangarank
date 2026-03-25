"""
backend/routes/proxy.py

GET /proxy/image — fetch, resize, cache and serve optimised cover images.
"""

import os
import io
import hashlib

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from PIL import Image

from backend import deps
from backend.constants import IMAGE_CACHE_DIR

router = APIRouter(tags=["proxy"])


def process_image(content: bytes, cache_path: str) -> None:
    """Resize to 300 px width and save as WebP to the disk cache."""
    img = Image.open(io.BytesIO(content))

    if img.mode != "RGB":
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert("RGB")

    target_width = 300
    if img.size[0] > target_width:
        wpercent = target_width / float(img.size[0])
        hsize = int(float(img.size[1]) * wpercent)
        img = img.resize((target_width, hsize), Image.Resampling.LANCZOS)

    img.save(cache_path, "WEBP", quality=80)


@router.get("/proxy/image")
async def proxy_image(url: str, response: Response):
    """Fetch, resize, cache, and serve optimized (300px WebP) cover images."""
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")

    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_path = os.path.join(IMAGE_CACHE_DIR, f"{url_hash}.webp")

    # Serve from disk cache if available
    if os.path.exists(cache_path):
        response.headers["Cache-Control"] = "public, max-age=86400"
        return FileResponse(cache_path, media_type="image/webp")

    # Fetch from source
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = await deps.http_client.get(url, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"Proxy fetch failed for {url}: {e}")
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        await run_in_threadpool(process_image, r.content, cache_path)
        response.headers["Cache-Control"] = "public, max-age=86400"
        return FileResponse(cache_path, media_type="image/webp")
    except Exception as e:
        print(f"Error processing image {url}: {e}")
        # Fallback to original image bytes
        return Response(content=r.content, media_type=r.headers.get("content-type", "image/jpeg"))
