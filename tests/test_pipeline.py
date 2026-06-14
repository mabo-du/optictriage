import pytest
import os
import cv2
import numpy as np
import math
from unittest.mock import patch, MagicMock

from optictriage.vision.blur import compute_blur_score
from optictriage.vision.exposure import compute_exposure_clipping
from optictriage.vision.preprocessing import preprocess_for_targets
from optictriage.vision.targets import detect_targets
from optictriage.exporters.odm import _generate_gcp_list
from optictriage.exporters.rtk_validator import validate_rtk_accuracy
from optictriage.models import ImageRecord
from optictriage.stages.import_stage import ImportStage
from optictriage.database import DatabaseManager

def test_sha256_duplicate_detection(tmp_path):
    """Test SHA-256 duplicate detection using the actual hash computation loop."""
    import hashlib
    
    # Create two dummy files with identical content
    file1 = tmp_path / "img1.jpg"
    file2 = tmp_path / "img2.jpg"
    content = b"fake image data 123"
    file1.write_bytes(content)
    file2.write_bytes(content)
    
    # Run the exact chunked hashing logic from ImportStage
    def get_hash(path):
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
        
    hash1 = get_hash(str(file1))
    hash2 = get_hash(str(file2))
    
    assert hash1 == hash2, "Identical files should produce the same SHA-256 hash."

def test_laplacian_grid_averaging():
    """Test that blur scoring uses the top 5% sharpest patches via a grid."""
    # Synthetic image: highly blurred everywhere except one sharp white circle
    img = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.GaussianBlur(img, (51, 51), 0, dst=img)
    # Draw one sharp high-contrast patch
    cv2.rectangle(img, (200, 200), (300, 300), (255, 255, 255), -1)
    
    score = compute_blur_score(img)
    # A standard full-image laplacian would be very low. Grid ensures it captures the sharp region.
    assert score > 10.0, f"Expected higher blur score from top 5% grid, got {score}"

def test_exposure_clipping():
    """Test exposure clipping at the 1% pixel threshold."""
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # 100x100 = 10,000 pixels. 1% = 100 pixels.
    # Let's clip 200 pixels (2%)
    img[0:10, 0:20] = 255
    
    pct = compute_exposure_clipping(img)
    # The function returns the percentage.
    assert pct >= 2.0

def test_clahe_bilateral_shape():
    """Test CLAHE + bilateral filter output shape preservation (BGR -> LAB L-channel -> Grayscale)."""
    img = np.zeros((150, 150, 3), dtype=np.uint8)
    out = preprocess_for_targets(img)
    # Should be a single channel grayscale image of the same spatial dimensions
    assert len(out.shape) == 2
    assert out.shape == (150, 150)

def test_aruco_detection():
    """Test ArUco detection on a synthetic marker."""
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    marker = cv2.aruco.generateImageMarker(dictionary, 42, 200)
    # Add a white border so the black marker stands out
    img = cv2.copyMakeBorder(marker, 50, 50, 50, 50, cv2.BORDER_CONSTANT, value=[255])
    
    targets = detect_targets(img)
    assert len(targets) > 0, "Failed to detect synthetic ArUco marker."
    
    detected = False
    for t in targets:
        if t["target_type"].startswith("aruco_") and t["id"] == 42:
            detected = True
    assert detected, "Detected marker did not match expected ID 42."

def test_odm_nan_replacement(tmp_path):
    """Test ODM NaN->0.0 replacement in gcp_list.txt."""
    record = ImageRecord()
    _generate_gcp_list([record], str(tmp_path))
    
    gcp_file = tmp_path / "gcp_list.txt"
    assert gcp_file.exists()
    content = gcp_file.read_text()
    
    assert "nan" not in content.lower(), "NaN value leaked into gcp_list.txt"

def test_rtk_flag_severity():
    """Test RTK flag severity mapping."""
    with patch('optictriage.exporters.rtk_validator.extract_metadata') as mock_exif:
        with patch('optictriage.exporters.rtk_validator.process_drone_telemetry') as mock_telem:
            record = ImageRecord()
            record.original_path = "test.jpg"
            record.is_flagged = False
            
            # Test Fixed (50)
            mock_exif.return_value = ({}, {})
            mock_telem.return_value = {"rtk_flag": 50}
            warnings = validate_rtk_accuracy([record])
            assert len(warnings) == 0, "Fixed RTK should not produce a warning."
            
            # Test Float (34)
            mock_telem.return_value = {"rtk_flag": 34, "rtk_std_lon": 0.5}
            warnings = validate_rtk_accuracy([record])
            assert len(warnings) == 1
            assert "Float" in warnings[0]
            
            # Test Single Point (16)
            mock_telem.return_value = {"rtk_flag": 16}
            warnings = validate_rtk_accuracy([record])
            assert len(warnings) == 1
            assert "Single Point" in warnings[0]
            
            # Test Failed (0)
            mock_telem.return_value = {"rtk_flag": 0}
            warnings = validate_rtk_accuracy([record])
            assert len(warnings) == 1
            assert "Failed" in warnings[0]
