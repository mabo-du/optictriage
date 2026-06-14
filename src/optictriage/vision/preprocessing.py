"""preprocessing.py — Image preprocessing pipeline for target detection.
exports: preprocess_for_targets
used_by: vision/targets.py → detect_targets
rules:
Must apply LAB CLAHE, bilateral filtering, and adaptive thresholding.
"""

import cv2
import numpy as np

from optictriage.vision.gpu_accel import GpuAccelerator

def preprocess_for_targets(image: np.ndarray) -> np.ndarray:
    """
    Preprocesses an image to maximize target detection success.
    Applies CLAHE on the L channel of LAB color space, and bilateral filtering 
    to remove noise while keeping edges sharp.
    Returns a grayscale image suitable for ArUco detection (which applies its own thresholding).
    Uses CUDA acceleration if available.
    """
    accel = GpuAccelerator.get_instance()
    
    if accel.is_available:
        # CUDA Path
        accel.gpu_src.upload(image, accel.stream)
        
        # 1. LAB Conversion
        if len(image.shape) == 3:
            cv2.cuda.cvtColor(accel.gpu_src, cv2.COLOR_BGR2LAB, accel.gpu_lab, stream=accel.stream)
            # split channels
            channels = cv2.cuda.split(accel.gpu_lab, stream=accel.stream)
            l_channel = channels[0]
            
            # CLAHE on L channel
            accel.clahe.apply(l_channel, accel.stream, accel.gpu_clahe_out)
            
            # Merge back (optional) or just use the L-channel as our grayscale equivalent
            # For ArUco, the L channel is an excellent high-contrast grayscale representation.
            gray_equivalent = accel.gpu_clahe_out
        else:
            accel.clahe.apply(accel.gpu_src, accel.stream, accel.gpu_clahe_out)
            gray_equivalent = accel.gpu_clahe_out
            
        # 2. Bilateral filter (Tier 2 CUDA)
        cv2.cuda.bilateralFilter(gray_equivalent, 9, 75, 75, accel.gpu_filtered, stream=accel.stream)
        
        # Download
        filtered = accel.gpu_filtered.download(stream=accel.stream)
        accel.stream.waitForCompletion()
        
        return filtered
        
    # CPU Path fallback
    if len(image.shape) != 3:
        # Fallback if already grayscale
        gray = image
    else:
        # 1. LAB conversion and CLAHE on L-channel
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        
        # Merge back and convert to grayscale for further processing
        merged_lab = cv2.merge((cl, a, b))
        bgr = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        
    # 2. Bilateral filter for edge-preserving smoothing
    filtered = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    
    return filtered
