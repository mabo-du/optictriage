"""raw_preview.py — Extracts embedded JPEGs from RAW files.
exports: extract_preview
used_by: ui/import_panel.py, stages/quality_stage.py
rules:
Must prioritize speed: extract embedded preview instead of full demosaicing if possible.
"""

import rawpy
import cv2
import numpy as np
from turbojpeg import TurboJPEG
from typing import Optional

# Initialize TurboJPEG (must be installed on the system, e.g., libturbojpeg.so.0)
try:
    jpeg = TurboJPEG()
except Exception:
    # Fallback if PyTurboJPEG fails to find the library
    jpeg = None

def extract_preview(filepath: str) -> Optional[np.ndarray]:
    """
    Extracts the fastest possible RGB preview from an image.
    For RAWs, it extracts the embedded JPEG.
    For TIFFs/JPEGs, it reads the image directly.
    """
    ext = filepath.lower().split('.')[-1]
    
    if ext in ('cr2', 'nef', 'arw', 'dng'):
        try:
            with rawpy.imread(filepath) as raw:
                try:
                    # Attempt to extract embedded JPEG preview
                    thumb = raw.extract_thumb()
                    if thumb.format == rawpy.ThumbFormat.JPEG:
                        if jpeg:
                            return jpeg.decode(thumb.data)
                        else:
                            # Fallback to OpenCV
                            img_array = np.asarray(bytearray(thumb.data), dtype=np.uint8)
                            return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    elif thumb.format == rawpy.ThumbFormat.BITMAP:
                        return thumb.data
                except rawpy.LibRawNoThumbnailError:
                    # If no thumbnail, we must do a fast half-size demosaic
                    return raw.postprocess(use_camera_wb=True, half_size=True)
        except Exception:
            return None
    
    # For standard images, try PyTurboJPEG first for speed, then OpenCV
    elif ext in ('jpg', 'jpeg'):
        try:
            if jpeg:
                with open(filepath, 'rb') as f:
                    return jpeg.decode(f.read())
            else:
                return cv2.imread(filepath, cv2.IMREAD_COLOR)
        except Exception:
            return cv2.imread(filepath, cv2.IMREAD_COLOR)
    else:
        # Fallback for TIFFs etc
        return cv2.imread(filepath, cv2.IMREAD_COLOR)
