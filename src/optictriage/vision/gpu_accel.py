"""gpu_accel.py — GPU Acceleration with tiered CUDA fallback.
exports: GpuAccelerator
used_by: vision/blur.py, vision/preprocessing.py
rules:
Must use cv2.cuda_Stream objects to overlap upload, compute, download.
Must pre-allocate GpuMat buffers and reuse via .upload().
"""

import cv2
import numpy as np

class GpuAccelerator:
    _instance = None
    
    def __init__(self):
        try:
            self.is_available = cv2.cuda.getCudaEnabledDeviceCount() > 0
        except AttributeError:
            # OpenCV not compiled with CUDA
            self.is_available = False
            
        self.stream = None
        self.gpu_src = None
        self.gpu_gray = None
        self.gpu_lab = None
        self.gpu_l_channel = None
        self.gpu_clahe_out = None
        self.gpu_filtered = None
        self.gpu_laplacian = None
        self.clahe = None
        
        if self.is_available:
            self.stream = cv2.cuda_Stream()
            
            # Tier 1 & 2 objects
            self.gpu_src = cv2.cuda_GpuMat()
            self.gpu_gray = cv2.cuda_GpuMat()
            self.gpu_lab = cv2.cuda_GpuMat()
            self.gpu_l_channel = cv2.cuda_GpuMat()
            self.gpu_clahe_out = cv2.cuda_GpuMat()
            self.gpu_filtered = cv2.cuda_GpuMat()
            self.gpu_laplacian = cv2.cuda_GpuMat()
            
            self.clahe = cv2.cuda.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
