"""glare.py — Detects veiling glare using HSI color space.
exports: compute_glare_score
used_by: stages/quality_stage.py → QualityStage
rules:
Convert to HSI and threshold high-I, low-S regions.
"""

import cv2
import numpy as np

def compute_glare_score(image: np.ndarray) -> float:
    """
    Detects veiling glare by identifying regions with high intensity and low saturation.
    Returns the percentage of the image area affected by glare.
    """
    if len(image.shape) != 3:
        return 0.0 # Cannot detect glare reliably on grayscale
        
    # OpenCV uses HSV, but HSI is better for this.
    # We can approximate by converting to HSV and using V as I, or calculate I manually.
    # Let's do a strict manual HSI conversion for Intensity and Saturation.
    
    # Normalize to 0-1
    bgr = image.astype(np.float32) / 255.0
    b, g, r = cv2.split(bgr)
    
    # Intensity
    i = (b + g + r) / 3.0
    
    # Saturation
    minimum = np.minimum(np.minimum(r, g), b)
    s = np.zeros_like(i)
    non_zero_i = i > 0
    s[non_zero_i] = 1 - (minimum[non_zero_i] / i[non_zero_i])
    
    # Glare threshold: High Intensity (>0.85) and Low Saturation (<0.15)
    glare_mask = (i > 0.85) & (s < 0.15)
    
    glare_pixels = np.count_nonzero(glare_mask)
    total_pixels = i.size
    
    glare_pct = (glare_pixels / total_pixels) * 100.0
    return float(glare_pct)
