"""
File Utilities — Phase 7

WHAT IT DOES:
    Handles image file validation, saving uploaded files to disk,
    and cleaning up temporary files.

WHY WE NEED IT:
    Users upload images through the API. We need to:
    1. Validate that the file is actually an image
    2. Check it's not too large
    3. Save it safely to a temporary location
    4. Clean up afterwards
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional, Tuple


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".jfif", ".bmp", ".avif"}
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/jfif",
    "image/pjpeg", "image/bmp", "image/avif", "image/x-png", "application/octet-stream",
}


def validate_image_file(
    filename: str,
    content_type: Optional[str] = None,
    file_size: int = 0,
    max_size_mb: float = 10.0,
) -> Tuple[bool, Optional[str]]:
    """
    Validate an uploaded image file.

    Args:
        filename: Original filename.
        content_type: MIME type from the upload.
        file_size: File size in bytes.
        max_size_mb: Maximum allowed file size in MB.

    Returns:
        Tuple of (is_valid, error_message).
        If valid: (True, None)
        If invalid: (False, "Reason why it's invalid")
    """
    if not filename:
        return False, "No filename provided."

    # Check extension
    ext = Path(filename).suffix.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        return False, (
            f"Unsupported image format: '{ext}'. "
            f"Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Check MIME type if provided
    if content_type:
        content_type_clean = content_type.lower().split(";")[0].strip()
        if not (content_type_clean.startswith("image/") or content_type_clean in ALLOWED_MIME_TYPES):
            return False, (
                f"Unsupported content type: '{content_type}'. "
                f"Please upload a standard image file."
            )

    # Check file size
    max_bytes = int(max_size_mb * 1024 * 1024)
    if file_size > max_bytes:
        size_mb = file_size / (1024 * 1024)
        return False, (
            f"Image too large: {size_mb:.1f} MB. "
            f"Maximum allowed: {max_size_mb} MB."
        )

    return True, None


def save_upload(
    file_bytes: bytes,
    original_filename: str,
    upload_dir: str,
) -> str:
    """
    Save uploaded file bytes to disk with a unique filename.

    Args:
        file_bytes: The raw file content.
        original_filename: Original filename (for extension).
        upload_dir: Directory to save to.

    Returns:
        Full path to the saved file.
    """
    # Create upload directory if needed
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)

    # Generate unique filename preserving original name hint
    import re
    ext = Path(original_filename).suffix.lower()
    raw_stem = Path(original_filename).stem[:30]
    clean_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", raw_stem) if raw_stem else "upload"
    unique_name = f"{clean_stem}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = upload_path / unique_name

    # Write file
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    return str(file_path)


def cleanup_file(file_path: str) -> None:
    """
    Remove a temporary file. Silently ignores if file doesn't exist.
    """
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
    except OSError:
        pass  # Best-effort cleanup
