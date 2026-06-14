"""target_stage.py — Detects markers and updates ImageRecord.
exports: TargetStage
used_by: pipeline.py → Orchestrator
rules:
Must write detected targets as JSON to ImageRecord.
"""

from typing import Any, Dict, Generator
import json
import os
import psutil
from concurrent.futures import ProcessPoolExecutor, as_completed

from optictriage.stages.base import Stage
from optictriage.models import ImageRecord, Session
from optictriage.vision.raw_preview import extract_preview
from optictriage.vision.preprocessing import preprocess_for_targets
from optictriage.vision.gpu_accel import GpuAccelerator
from optictriage.workers import worker_detect_targets

class TargetStage(Stage):
    """Detects ArUco, ChArUco, and ColorChecker targets in images."""

    def run(self) -> Generator[Dict[str, Any], None, None]:
        with self.db_manager.get_session() as db_session:
            # We only process images that passed quality scoring (or we can process all)
            images = db_session.query(ImageRecord).filter(
                ImageRecord.session_id == self.session_id,
                ImageRecord.processing_state == "scored"
            ).all()

            total = len(images)
            if total == 0:
                yield {"status": "complete", "progress": 100.0, "message": "No images available for target detection."}
                return

            session_obj = db_session.query(Session).get(self.session_id)
            settings = session_obj.settings or {}
            worker_count = int(settings.get("worker_count", max(1, os.cpu_count() - 1)))
            
            # Estimate per-image size
            avg_w = 4000
            avg_h = 3000
            if len(images) > 0 and images[0].image_width:
                avg_w, avg_h = images[0].image_width, images[0].image_height
            image_size_bytes = avg_w * avg_h * 3
            
            target_batch_size = worker_count * 4
            available_ram = psutil.virtual_memory().available
            
            while target_batch_size > 1:
                estimated_ram = target_batch_size * image_size_bytes * 2
                if estimated_ram <= (available_ram * 0.8):
                    break
                target_batch_size = max(1, target_batch_size // 2)
                
            batch_size = target_batch_size
            yield {"status": "running", "progress": 0.0, "message": f"Processing {total} images in batches of {batch_size} with {worker_count} workers..."}

            accel = GpuAccelerator.get_instance()
            processed_count = 0

            for i in range(0, total, batch_size):
                batch = images[i:i+batch_size]
                
                with ProcessPoolExecutor(max_workers=worker_count) as executor:
                    futures = {}
                    for record in batch:
                        try:
                            img_array = extract_preview(record.original_path)
                            if img_array is None:
                                raise ValueError("Failed to extract image preview.")
                            
                            # GPU Preprocessing in main thread
                            # preprocess_for_targets automatically uses CUDA if accel.is_available
                            binary = preprocess_for_targets(img_array)
                            
                            future = executor.submit(worker_detect_targets, img_array, binary)
                            futures[future] = record
                            
                        except Exception as e:
                            record.processing_state = "error"
                            record.error_message = f"Target setup failed: {str(e)}"
                            record.is_flagged = 1
                            record.flag_reasons = (record.flag_reasons or []) + ["target_error"]
                            processed_count += 1
                            
                    # Collect results
                    for future in as_completed(futures):
                        record = futures[future]
                        processed_count += 1
                        progress = (processed_count / total) * 100
                        yield {"status": "running", "progress": progress, "message": f"Scanned {record.output_filename or record.original_path}..."}
                        
                        try:
                            result = future.result()
                            if result["detected_targets"]:
                                record.detected_targets = result["detected_targets"]
                            
                            record.colour_target_detected = result["colour_target_detected"]
                            if result["color_patches"]:
                                record.color_patches = result["color_patches"]
                                
                            record.processing_state = "targets_done"
                        except Exception as e:
                            record.processing_state = "error"
                            record.error_message = f"Worker failed: {str(e)}"
                            record.is_flagged = 1
                            record.flag_reasons = (record.flag_reasons or []) + ["target_error"]
                            
                db_session.commit()

            yield {"status": "complete", "progress": 100.0, "message": "Target detection complete."}
