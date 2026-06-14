"""blur.py — Computes Laplacian variance for blur detection.
exports: compute_blur_score
used_by: stages/quality_stage.py → QualityStage
rules:
Must use grid-based top 5% sharpest patches.
"""

import cv2
import numpy as np

from optictriage.vision.gpu_accel import GpuAccelerator

def compute_blur_score(image: np.ndarray, grid_size: int = 10) -> float:
    """
    Computes a blur score by applying a Laplacian filter.
    Instead of full-image variance (which fails on flat textures like sky/ground),
    it divides the image into a grid and averages the variance of the top 5% sharpest patches.
    Higher score = sharper.
    """
    accel = GpuAccelerator.get_instance()
    
    if accel.is_available:
        accel.gpu_src.upload(image, accel.stream)
        cv2.cuda.cvtColor(accel.gpu_src, cv2.COLOR_BGR2GRAY, accel.gpu_gray, stream=accel.stream)
        
        cv2.cuda.Laplacian(accel.gpu_gray, cv2.CV_32F, accel.gpu_laplacian, ksize=3, stream=accel.stream)
        laplacian = accel.gpu_laplacian.download(stream=accel.stream)
        accel.stream.waitForCompletion()
    else:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)

    h, w = laplacian.shape
    patch_h, patch_w = h // grid_size, w // grid_size
    
    variances = []
    
    for i in range(grid_size):
        for j in range(grid_size):
            y1, y2 = i * patch_h, (i + 1) * patch_h
            x1, x2 = j * patch_w, (j + 1) * patch_w
            
            patch = laplacian[y1:y2, x1:x2]
            variances.append(patch.var())
            
    # Sort and take top 5%
    variances.sort(reverse=True)
    top_5_pct_count = max(1, int(len(variances) * 0.05))
    
    top_variances = variances[:top_5_pct_count]
    return float(np.mean(top_variances))
