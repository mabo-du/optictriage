import time
import numpy as np
import cv2
from optictriage.vision.blur import compute_blur_score
from optictriage.vision.exposure import compute_exposure_clipping
from optictriage.vision.preprocessing import preprocess_for_targets

def profile_pipeline():
    """
    Profiles the computer vision pipeline over 1000 iterations to test 
    against the 360ms per image budget on recommended hardware.
    """
    # Create synthetic 4K image (similar to typical drone shot)
    w, h = 4000, 3000
    img = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
    
    # Warmup
    compute_blur_score(img)
    compute_exposure_clipping(img)
    preprocess_for_targets(img)
    
    total_images = 1000
    print(f"Profiling vision pipeline on {total_images} frames (4000x3000)...")
    
    # Pre-generate images (or reuse one to save RAM)
    
    start_total = time.time()
    
    t_blur = 0.0
    t_exp = 0.0
    t_prep = 0.0
    
    for i in range(total_images):
        # We use a single image to avoid memory exhaustion during the test,
        # but time the execution steps.
        
        t0 = time.time()
        compute_blur_score(img)
        t1 = time.time()
        
        compute_exposure_clipping(img)
        t2 = time.time()
        
        preprocess_for_targets(img)
        t3 = time.time()
        
        t_blur += (t1 - t0)
        t_exp += (t2 - t1)
        t_prep += (t3 - t2)
        
    total_time = time.time() - start_total
    avg_time_ms = (total_time / total_images) * 1000.0
    
    print("-" * 40)
    print("PROFILING RESULTS:")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Average Time per Image: {avg_time_ms:.2f} ms")
    print("\nBreakdown (Total Time / Avg ms per frame):")
    print(f"Blur Scoring: {t_blur:.2f}s / {(t_blur/total_images)*1000:.2f}ms")
    print(f"Exposure Clipping: {t_exp:.2f}s / {(t_exp/total_images)*1000:.2f}ms")
    print(f"Preprocessing (CLAHE+Bilateral): {t_prep:.2f}s / {(t_prep/total_images)*1000:.2f}ms")
    
    print("\nBudget Analysis:")
    print(f"Target Budget: 360 ms")
    if avg_time_ms <= 360:
        print("Status: PASS (Under budget)")
    else:
        print("Status: FAIL (Over budget)")

if __name__ == "__main__":
    profile_pipeline()
