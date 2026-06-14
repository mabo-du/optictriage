import pytest
import time
import numpy as np
import os
from concurrent.futures import ProcessPoolExecutor
from optictriage.workers import worker_quality_scores

def test_multiprocessing_speedup():
    """
    Asserts that wall-clock time for processing a 100-image synthetic batch
    on the CPU-only path is lower with the worker pool than sequential.
    """
    # 1. Create a synthetic batch of 100 images (640x480 to keep test runtime reasonable)
    images = [np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8) for _ in range(100)]
    
    # 2. Sequential processing
    start_seq = time.time()
    for img in images:
        worker_quality_scores(img)
    seq_time = time.time() - start_seq
    
    # 3. Multiprocessing
    worker_count = max(2, os.cpu_count() - 1) if os.cpu_count() else 2
    
    start_mp = time.time()
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(worker_quality_scores, img) for img in images]
        for f in futures:
            f.result()
    mp_time = time.time() - start_mp
    
    print(f"\nSequential Time: {seq_time:.2f}s")
    print(f"Multiprocessing Time ({worker_count} workers): {mp_time:.2f}s")
    print(f"Speedup Ratio: {seq_time / mp_time:.2f}x")
    
    # Multiprocessing must be faster
    assert mp_time < seq_time, f"MP ({mp_time:.2f}s) not faster than Seq ({seq_time:.2f}s)"
