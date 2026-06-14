"""workers.py — Pure CPU module for ProcessPoolExecutor workers.
exports: worker_quality_scores, worker_detect_targets, worker_compute_phash
used_by: stages/quality_stage.py, stages/target_stage.py, stages/import_stage.py
rules:
Functions must be module-level to support pickle serialization.
No CUDA or GpuAccelerator calls allowed here.
"""

import cv2
import numpy as np
import imagehash
from PIL import Image

from optictriage.vision.blur import compute_blur_score
from optictriage.vision.exposure import compute_exposure_clipping
from optictriage.vision.glare import compute_glare_score
from optictriage.vision.targets import detect_targets
from optictriage.vision.colorchecker import extract_mcc_patches

def worker_quality_scores(img_array: np.ndarray, gpu_blur_score: float = None) -> dict:
    """Calculates quality metrics. Computes blur score if not already done on GPU."""
    blur_score = gpu_blur_score
    if blur_score is None:
        blur_score = compute_blur_score(img_array)
        
    exposure_clip = compute_exposure_clipping(img_array)
    glare_score = compute_glare_score(img_array)
    
    return {
        "blur_score": blur_score,
        "exposure_clipped_pct": exposure_clip,
        "glare_score": glare_score
    }

def worker_detect_targets(img_array: np.ndarray, preprocessed_gray: np.ndarray) -> dict:
    """Detects ArUco/ChArUco and ColorChecker targets."""
    targets = detect_targets(preprocessed_gray)
    
    has_mcc, patches = extract_mcc_patches(img_array)
    
    return {
        "detected_targets": targets,
        "colour_target_detected": 1 if has_mcc else 0,
        "color_patches": patches
    }

def worker_compute_phash(img_array: np.ndarray) -> str:
    """Computes perceptual hash via dhash."""
    if len(img_array.shape) == 3:
        # Check if it's already RGB or BGR. BGR is default from extract_preview
        rgb_arr = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
    else:
        rgb_arr = img_array
    
    pil_img = Image.fromarray(rgb_arr)
    return str(imagehash.dhash(pil_img))
