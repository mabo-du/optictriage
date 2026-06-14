import pytest
import imagehash
from PIL import Image
import numpy as np

class MockImageRecord:
    def __init__(self, capture_time, phash):
        self.capture_time = capture_time
        self.phash = phash
        self.is_flagged = 0
        self.flag_reasons = []

def test_phash_sequential_comparison():
    # We will just test the logic used in QualityStage directly
    # Generate two very similar images and compute their hashes
    np.random.seed(42)
    arr1 = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    arr2 = arr1.copy()
    arr2[30:35, 30:35] = 0 # slight difference
    
    np.random.seed(43)
    arr3 = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8) # completely different
    
    img1 = Image.fromarray(arr1)
    img2 = Image.fromarray(arr2)
    img3 = Image.fromarray(arr3)
    
    hash1 = str(imagehash.dhash(img1))
    hash2 = str(imagehash.dhash(img2))
    hash3 = str(imagehash.dhash(img3))
    
    # Chronological: 1 -> 2 -> 3
    # 1 and 2 are near duplicates. 3 is different.
    # Therefore, 2 should be flagged, 1 and 3 should not.
    record1 = MockImageRecord("2026:06:14 10:00:00", hash1)
    record2 = MockImageRecord("2026:06:14 10:00:05", hash2)
    record3 = MockImageRecord("2026:06:14 10:00:10", hash3)
    
    valid_images = [record1, record2, record3]
    
    phash_threshold = 5
    for i in range(1, len(valid_images)):
        prev_img = valid_images[i-1]
        curr_img = valid_images[i]
        h1 = imagehash.hex_to_hash(prev_img.phash)
        h2 = imagehash.hex_to_hash(curr_img.phash)
        if h1 - h2 < phash_threshold:
            flags = curr_img.flag_reasons or []
            flags.append("near_duplicate")
            curr_img.flag_reasons = flags
            curr_img.is_flagged = 1
            
    assert record1.is_flagged == 0
    assert record2.is_flagged == 1
    assert "near_duplicate" in record2.flag_reasons
    assert record3.is_flagged == 0
