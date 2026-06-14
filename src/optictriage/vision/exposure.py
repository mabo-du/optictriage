"""exposure.py — Calculates exposure clipping percentages.
exports: compute_exposure_clipping
used_by: stages/quality_stage.py → QualityStage
rules:
Must return the total percentage of clipped pixels (0 or 255).
"""

import cv2
import numpy as np

def compute_exposure_clipping(image: np.ndarray) -> float:
    """
    Computes the percentage of pixels that are completely black (0) 
    or completely white (255) across all channels.
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    total_pixels = gray.size
    
    # Count pure black
    black_pixels = np.count_nonzero(gray == 0)
    
    # Count pure white
    white_pixels = np.count_nonzero(gray == 255)
    
    clipped_pct = ((black_pixels + white_pixels) / total_pixels) * 100.0
    return float(clipped_pct)
