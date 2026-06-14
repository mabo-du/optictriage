"""quality_stage.py — Computes image quality metrics and updates records.
exports: QualityStage
used_by: pipeline.py → Orchestrator
rules:
Must implement memory estimation guard before processing to warn about SfM limits.
"""

from typing import Any, Dict, Generator
import os
import psutil
from concurrent.futures import ProcessPoolExecutor, as_completed

from optictriage.stages.base import Stage
from optictriage.models import ImageRecord, Session
from optictriage.vision.raw_preview import extract_preview
from optictriage.vision.blur import compute_blur_score
from optictriage.vision.gpu_accel import GpuAccelerator
from optictriage.workers import worker_quality_scores

class QualityStage(Stage):
    """Computes blur, exposure, and glare scores for each image."""

    def run(self) -> Generator[Dict[str, Any], None, None]:
        with self.db_manager.get_session() as db_session:
            images = db_session.query(ImageRecord).filter(
                ImageRecord.session_id == self.session_id,
                ImageRecord.processing_state == "exif_extracted",
                ImageRecord.is_flagged == 0
            ).all()

            total = len(images)
            if total == 0:
                yield {"status": "complete", "progress": 100.0, "message": "No unflagged images for quality scoring."}
                return

            # --- PHash Sequential Comparison ---
            session_obj = db_session.query(Session).get(self.session_id)
            settings = session_obj.settings or {}
            phash_threshold = int(settings.get("phash_threshold", 5))

            import imagehash
            from datetime import datetime

            def get_timestamp(img):
                if not img.capture_time:
                    return 0.0
                try:
                    return datetime.strptime(img.capture_time, "%Y:%m:%d %H:%M:%S").timestamp()
                except Exception:
                    return 0.0

            valid_images = [img for img in images if img.phash]
            valid_images.sort(key=get_timestamp)
            
            for i in range(1, len(valid_images)):
                prev_img = valid_images[i-1]
                curr_img = valid_images[i]
                
                try:
                    hash1 = imagehash.hex_to_hash(prev_img.phash)
                    hash2 = imagehash.hex_to_hash(curr_img.phash)
                    dist = hash1 - hash2
                    
                    if dist < phash_threshold:
                        flags = curr_img.flag_reasons or []
                        if "near_duplicate" not in flags:
                            flags.append("near_duplicate")
                            curr_img.flag_reasons = flags
                            curr_img.is_flagged = 1
                except Exception:
                    pass
            
            db_session.commit()
            # -----------------------------------

            # --- Memory Estimation Guard & Batch Sizing ---
            worker_count = int(settings.get("worker_count", max(1, os.cpu_count() - 1)))
            
            # Estimate per-image size
            avg_w = 4000
            avg_h = 3000
            if len(images) > 0 and images[0].image_width:
                avg_w, avg_h = images[0].image_width, images[0].image_height
            image_size_bytes = avg_w * avg_h * 3
            
            target_batch_size = worker_count * 4
            available_ram = psutil.virtual_memory().available
            
            # Dynamic batch resizing
            while target_batch_size > 1:
                estimated_ram = target_batch_size * image_size_bytes * 2
                if estimated_ram <= (available_ram * 0.8):
                    break
                target_batch_size = max(1, target_batch_size // 2)
                
            batch_size = target_batch_size
            yield {"status": "running", "progress": 0.0, "message": f"Processing {total} images in batches of {batch_size} with {worker_count} workers..."}
            # -------------------------------

            accel = GpuAccelerator.get_instance()
            processed_count = 0

            for i in range(0, total, batch_size):
                batch = images[i:i+batch_size]
                
                with ProcessPoolExecutor(max_workers=worker_count) as executor:
                    futures = {}
                    for record in batch:
                        if record.is_flagged:
                            continue
                            
                        try:
                            img_array = extract_preview(record.original_path)
                            if img_array is None:
                                raise ValueError("Failed to extract image preview.")
                            
                            # GPU Preprocessing in main thread
                            gpu_blur_score = None
                            if accel.is_available:
                                gpu_blur_score = compute_blur_score(img_array)
                                
                            future = executor.submit(worker_quality_scores, img_array, gpu_blur_score)
                            futures[future] = record
                            
                        except Exception as e:
                            record.processing_state = "error"
                            record.error_message = f"Quality setup failed: {str(e)}"
                            record.is_flagged = 1
                            record.flag_reasons = (record.flag_reasons or []) + ["quality_error"]
                            processed_count += 1
                            
                    # Collect results
                    for future in as_completed(futures):
                        record = futures[future]
                        processed_count += 1
                        progress = (processed_count / total) * 100
                        yield {"status": "running", "progress": progress, "message": f"Scored {record.output_filename or record.original_path}..."}
                        
                        try:
                            result = future.result()
                            record.blur_score = result["blur_score"]
                            record.exposure_clipped_pct = result["exposure_clipped_pct"]
                            record.glare_score = result["glare_score"]
                            
                            blur_threshold = float(settings.get("blur_threshold", 100.0))
                            exposure_threshold = float(settings.get("exposure_threshold", 1.0))
                            glare_threshold = float(settings.get("glare_threshold", 5.0))
                            
                            errors = []
                            if record.blur_score < blur_threshold:
                                errors.append("blur")
                            if record.exposure_clipped_pct > exposure_threshold:
                                errors.append(f"Overexposed ({record.exposure_clipped_pct:.1f}% clipped)")
                            if record.glare_score > glare_threshold:
                                errors.append(f"Veiling Glare detected ({record.glare_score:.1f}%)")
                                
                            if len(errors) > 0:
                                record.is_flagged = 1
                                record.flag_reasons = (record.flag_reasons or []) + errors
                                
                            record.processing_state = "scored"
                        except Exception as e:
                            record.processing_state = "error"
                            record.error_message = f"Worker failed: {str(e)}"
                            record.is_flagged = 1
                            record.flag_reasons = (record.flag_reasons or []) + ["quality_error"]
                            
                # Commit after every batch
                db_session.commit()

            yield {"status": "complete", "progress": 100.0, "message": "Quality scoring complete."}
