"""Profile photo storage on local disk (a Docker volume in production).

Files get random, unguessable names and are served read-only through the API,
so an <img> tag can load them without an auth header. Only JPEG, PNG and WebP
are accepted, detected from the file's bytes rather than its declared type.
"""

import re
import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.common.config import get_settings

URL_PREFIX = "/api/media/photos/"
_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}\.(jpg|png|webp)$")
_MEDIA_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}

router = APIRouter(prefix="/media", tags=["media"])


def _photo_dir() -> Path:
    d = Path(get_settings().media_dir) / "photos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sniff(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


async def save_photo(upload: UploadFile) -> str:
    limit = get_settings().max_photo_bytes
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, detail=f"Photo must be {limit // (1024 * 1024)} MB or smaller"
        )
    ext = _sniff(data[:16])
    if ext is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Photo must be a JPEG, PNG or WebP image")
    name = f"{secrets.token_urlsafe(18)}.{ext}"
    (_photo_dir() / name).write_bytes(data)
    return URL_PREFIX + name


def delete_photo(url: str | None) -> None:
    """Remove a previously uploaded photo (ignores external URLs)."""
    if not url or not url.startswith(URL_PREFIX):
        return
    name = url[len(URL_PREFIX) :]
    if _NAME_RE.match(name):
        (_photo_dir() / name).unlink(missing_ok=True)


@router.get("/photos/{name}", include_in_schema=False)
def get_photo(name: str):
    if not _NAME_RE.match(name):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    path = _photo_dir() / name
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return FileResponse(
        path,
        media_type=_MEDIA_TYPES[name.rsplit(".", 1)[1]],
        headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"},
    )
