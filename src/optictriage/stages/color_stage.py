"""color_stage.py — Applies automated color normalization to the dataset.
exports: ColorStage
used_by: pipeline.py
rules:
Lossless output format (TIFF) is preferred.
Do not overwrite source files.
"""

from typing import Any, Dict, Generator
import os
import cv2
import numpy as np

from optictriage.stages.base import Stage
from optictriage.models import ImageRecord, Session
from optictriage.vision.colorchecker import solve_ccm, srgb_to_linear, linear_to_srgb

class ColorStage(Stage):
    """Assigns keyframes and applies Color Correction Matrices (CCM)."""
    
    def run(self) -> Generator[Dict[str, Any], None, None]:
        with self.db_manager.get_session() as db_session:
            session_obj = db_session.query(Session).get(self.session_id)
            settings = session_obj.settings or {}
            export_jpeg = settings.get("export_jpeg", False)
        
        images = db_session.query(ImageRecord).filter_by(
            session_id=self.session_id,
            is_flagged=0
        ).order_by(ImageRecord.capture_time).all()
        
        if not images:
            yield {"status": "complete", "progress": 100.0, "message": "No images available for color normalization."}
            return
            
        export_dir = os.path.join(session_obj.output_folder, "colour_corrected")
        os.makedirs(export_dir, exist_ok=True)
        
        # Group by camera_group_idx
        groups = {}
        for img in images:
            grp = img.camera_group_idx or 1
            if grp not in groups:
                groups[grp] = []
            groups[grp].append(img)
            
        total = len(images)
        processed = 0
        
        yield {"status": "running", "progress": 0.0, "message": "Starting color normalization..."}
        
        for grp, group_images in groups.items():
            keyframes = [img for img in group_images if img.colour_target_detected == 1 and img.color_patches]
            
            if not keyframes:
                for img in group_images:
                    img.flag_reasons = (img.flag_reasons or []) + ["no_ccm_available"]
                    img.is_flagged = 1
                    processed += 1
                db_session.commit()
                continue
                
            # Precompute CCMs for keyframes
            keyframe_ccms = {}
            for kf in keyframes:
                try:
                    ccm = solve_ccm(kf.color_patches)
                    kf.ccm_matrix = ccm
                    keyframe_ccms[kf.id] = np.array(ccm)
                except Exception as e:
                    kf.error_message = f"CCM solving failed: {str(e)}"
                    kf.is_flagged = 1
                    
            valid_keyframes = [kf for kf in keyframes if kf.ccm_matrix]
            if not valid_keyframes:
                for img in group_images:
                    img.flag_reasons = (img.flag_reasons or []) + ["no_ccm_available"]
                    img.is_flagged = 1
                    processed += 1
                db_session.commit()
                continue
                
            # Apply to images
            for img in group_images:
                progress = (processed / total) * 100
                yield {"status": "running", "progress": progress, "message": f"Normalizing {img.output_filename or img.original_path}..."}
                
                # Find nearest keyframe in time
                nearest_kf = min(valid_keyframes, key=lambda kf: abs(img.capture_time.timestamp() - kf.capture_time.timestamp()) if img.capture_time and kf.capture_time else 0)
                ccm = keyframe_ccms[nearest_kf.id]
                
                try:
                    # Load image
                    img_array = cv2.imread(img.original_path, cv2.IMREAD_UNCHANGED)
                    if img_array is None:
                        raise ValueError(f"Could not read {img.original_path}")
                        
                    is_16bit = img_array.dtype == np.uint16
                    
                    # Convert BGR to RGB
                    if len(img_array.shape) == 3:
                        rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
                    else:
                        rgb = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
                        
                    # Normalize to 0-1
                    rgb_norm = rgb.astype(np.float32) / (65535.0 if is_16bit else 255.0)
                    
                    # Linearize
                    linear_rgb = srgb_to_linear(rgb_norm)
                    
                    # Apply CCM
                    flat_linear = linear_rgb.reshape(-1, 3)
                    corrected_flat = np.clip(flat_linear @ ccm.T, 0, 1)
                    corrected_linear = corrected_flat.reshape(linear_rgb.shape)
                    
                    # Re-encode sRGB
                    corrected_srgb = linear_to_srgb(corrected_linear)
                    
                    # Scale back
                    if is_16bit:
                        out_array = (corrected_srgb * 65535.0).astype(np.uint16)
                    else:
                        out_array = (corrected_srgb * 255.0).astype(np.uint8)
                        
                    # Convert RGB to BGR for saving
                    out_bgr = cv2.cvtColor(out_array, cv2.COLOR_RGB2BGR)
                    
                    # Determine output format
                    basename = img.output_filename or os.path.basename(img.original_path)
                    name, ext = os.path.splitext(basename)
                    
                    is_jpeg_source = ext.lower() in ['.jpg', '.jpeg']
                    if is_jpeg_source and export_jpeg:
                        out_ext = ext
                        out_path = os.path.join(export_dir, basename)
                        cv2.imwrite(out_path, out_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                    else:
                        out_ext = ".tiff"
                        out_path = os.path.join(export_dir, name + out_ext)
                        cv2.imwrite(out_path, out_bgr, [int(cv2.IMWRITE_TIFF_COMPRESSION), 1]) # 1 = None/LZW
                        
                    img.ccm_applied = True
                    img.ccm_keyframe_id = nearest_kf.id
                    
                except Exception as e:
                    img.processing_state = "error"
                    img.error_message = f"Color normalization failed: {str(e)}"
                    img.is_flagged = 1
                    img.flag_reasons = (img.flag_reasons or []) + ["color_error"]
                    
                processed += 1
                
            db_session.commit()
            
        yield {"status": "complete", "progress": 100.0, "message": "Color normalization complete."}
