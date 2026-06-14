"""import_stage.py — Scans folders, validates files, and computes hashes.
exports: ImportStage
used_by: pipeline.py → Orchestrator
rules:
Must detect and flag duplicate files based on SHA-256 hash.
"""

import os
import hashlib
from typing import Any, Dict, Generator
from pathlib import Path
import imagehash
from PIL import Image
import cv2

from optictriage.stages.base import Stage
from optictriage.models import Session, ImageRecord
from optictriage.vision.raw_preview import extract_preview

# Magic bytes for common image formats
MAGIC_BYTES = {
    b'\xFF\xD8\xFF': 'JPEG',
    b'\x49\x49\x2A\x00': 'TIFF', # Little-endian
    b'\x4D\x4D\x00\x2A': 'TIFF', # Big-endian
}
# RAW formats often embed TIFF headers, so magic bytes alone aren't perfect, 
# but we combine it with extension checks.
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.tif', '.tiff', '.cr2', '.nef', '.arw', '.dng'}

class ImportStage(Stage):
    """Discovers files, validates magic bytes, and populates the database."""

    def __init__(self, session_id: int, db_manager: Any):
        super().__init__(session_id, db_manager)
        self.input_folder = ""
        self._load_session_details()

    def _load_session_details(self):
        with self.db_manager.get_session() as db_session:
            session_obj = db_session.query(Session).get(self.session_id)
            if session_obj:
                self.input_folder = session_obj.input_folder

    def _compute_sha256(self, filepath: str) -> str:
        """Computes the SHA-256 hash of a file efficiently."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _validate_magic_bytes(self, filepath: str, ext: str) -> bool:
        """Validates that a file's magic bytes correspond to an image format."""
        # For simplicity in v1, we strictly check JPEG and TIFF.
        # Many RAWs (CR2, NEF, DNG) are TIFF-based and share TIFF magic bytes.
        try:
            with open(filepath, "rb") as f:
                header = f.read(4)
                if ext in {'.jpg', '.jpeg'} and header.startswith(b'\xFF\xD8\xFF'):
                    return True
                if ext in {'.tif', '.tiff', '.cr2', '.nef', '.arw', '.dng'}:
                    # ARW can have different headers, DNG/CR2/NEF are usually TIFF-like.
                    # We accept if it matches TIFF magic, or if it's a known RAW extension (trust the extension for now).
                    if header in {b'\x49\x49\x2A\x00', b'\x4D\x4D\x00\x2A'}:
                        return True
                    # If it's a RAW extension and doesn't match standard TIFF magic, we still permit it to proceed to PyExiv2/Rawpy
                    if ext in {'.cr2', '.nef', '.arw', '.dng'}:
                        return True
        except IOError:
            pass
        return False

    def run(self) -> Generator[Dict[str, Any], None, None]:
        if not self.input_folder or not os.path.exists(self.input_folder):
            yield {"status": "error", "progress": 0.0, "message": f"Input folder not found: {self.input_folder}"}
            return

        yield {"status": "running", "progress": 0.0, "message": "Scanning for image files..."}
        
        # Discover files
        discovered_files = []
        for root, _, files in os.walk(self.input_folder):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in ALLOWED_EXTENSIONS:
                    discovered_files.append(os.path.join(root, file))

        total_files = len(discovered_files)
        if total_files == 0:
            yield {"status": "error", "progress": 100.0, "message": "No valid image files found."}
            return

        seen_hashes = set()
        duplicate_count = 0

        # Process and insert
        with self.db_manager.get_session() as db_session:
            for idx, filepath in enumerate(discovered_files):
                ext = Path(filepath).suffix.lower()
                
                # Report progress
                progress = (idx / total_files) * 100
                yield {"status": "running", "progress": progress, "message": f"Processing {os.path.basename(filepath)}..."}
                
                file_size = os.path.getsize(filepath)
                if file_size == 0:
                    record = ImageRecord(
                        session_id=self.session_id,
                        original_path=filepath,
                        file_size_bytes=0,
                        processing_state="error",
                        error_message="Zero-byte file",
                        is_flagged=1,
                        flag_reasons=["corrupt"]
                    )
                    db_session.add(record)
                    continue

                if not self._validate_magic_bytes(filepath, ext):
                    record = ImageRecord(
                        session_id=self.session_id,
                        original_path=filepath,
                        file_size_bytes=file_size,
                        processing_state="error",
                        error_message="Invalid magic bytes",
                        is_flagged=1,
                        flag_reasons=["corrupt"]
                    )
                    db_session.add(record)
                    continue

                # Hash check for duplicates
                file_hash = self._compute_sha256(filepath)
                is_duplicate = file_hash in seen_hashes
                
                phash_str = None
                if not is_duplicate:
                    seen_hashes.add(file_hash)
                    try:
                        preview_arr = extract_preview(filepath)
                        if preview_arr is not None:
                            if len(preview_arr.shape) == 3:
                                preview_arr = cv2.cvtColor(preview_arr, cv2.COLOR_BGR2RGB)
                            pil_img = Image.fromarray(preview_arr)
                            phash_str = str(imagehash.dhash(pil_img))
                    except Exception as e:
                        pass
                
                record = ImageRecord(
                    session_id=self.session_id,
                    original_path=filepath,
                    file_size_bytes=file_size,
                    file_hash=file_hash,
                    phash=phash_str,
                    processing_state="imported",
                )

                if is_duplicate:
                    duplicate_count += 1
                    record.is_flagged = 1
                    record.flag_reasons = ["duplicate"]

                db_session.add(record)

        yield {
            "status": "complete", 
            "progress": 100.0, 
            "message": f"Imported {total_files} files ({duplicate_count} duplicates flagged)."
        }
