"""csv_manifest.py — Generates a master CSV manifest using pandas.
exports: generate_csv_manifest
used_by: stages/export_stage.py → ExportStage
rules:
Must export all ImageRecord fields including quality scores, RTK flag, and target coords.
"""

import pandas as pd
import os
from optictriage.models import ImageRecord

def generate_csv_manifest(records: list[ImageRecord], output_dir: str):
    """
    Exports all ImageRecord data to a master CSV using pandas.
    """
    data = []
    for r in records:
        data.append({
            "original_path": r.original_path,
            "output_filename": r.output_filename,
            "file_size_bytes": r.file_size_bytes,
            "image_width": r.image_width,
            "image_height": r.image_height,
            "camera_make": r.camera_make,
            "camera_model": r.camera_model,
            "focal_length_mm": r.focal_length_mm,
            "aperture": r.aperture,
            "iso": r.iso,
            "shutter_speed": r.shutter_speed,
            "gps_lat": r.gps_lat,
            "gps_lon": r.gps_lon,
            "gps_alt": r.gps_alt,
            "relative_alt": r.relative_alt,
            "capture_time": r.capture_time,
            "blur_score": r.blur_score,
            "exposure_clipped_pct": r.exposure_clipped_pct,
            "glare_score": r.glare_score,
            "is_flagged": r.is_flagged,
            "flag_reasons": r.flag_reasons,
            "detected_targets": r.detected_targets,
            "colour_target_detected": r.colour_target_detected,
            "processing_state": r.processing_state,
        })
    
    df = pd.DataFrame(data)
    out_path = os.path.join(output_dir, "optictriage_manifest.csv")
    df.to_csv(out_path, index=False)
    return out_path
