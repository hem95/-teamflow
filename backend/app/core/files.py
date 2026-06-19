import os
import uuid
from fastapi import UploadFile, HTTPException
from app.config import settings

# Make sure the upload directory exists when the app starts
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def _safe_extension(filename: str) -> str:
    """
    Pull a short, safe file extension from the original name.
    We only keep letters/numbers so a malicious name can't sneak in
    path characters like '../' or weird symbols.
    """
    _, ext = os.path.splitext(filename or "")
    ext = ext.lstrip(".").lower()
    if not ext.isalnum() or len(ext) > 10:
        return ""
    return ext


async def save_upload(file: UploadFile) -> tuple[str, int]:
    """
    Save an uploaded file to disk under a random unique name.
    Returns (stored_name, size_in_bytes).

    Reads in chunks so a huge upload can't blow up memory, and enforces
    the MAX_UPLOAD_SIZE limit while streaming.
    """
    ext = _safe_extension(file.filename)
    stored_name = f"{uuid.uuid4().hex}{('.' + ext) if ext else ''}"
    dest_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    size = 0
    chunk_size = 1024 * 1024  # 1 MB at a time
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE:
                    out.close()
                    os.remove(dest_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large (max {settings.MAX_UPLOAD_SIZE // (1024*1024)} MB)",
                    )
                out.write(chunk)
    finally:
        await file.close()

    if size == 0:
        # Empty file — clean up and reject
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    return stored_name, size


def attachment_url(stored_name: str) -> str:
    """Public URL the browser uses to fetch the file."""
    return f"/uploads/{stored_name}"
