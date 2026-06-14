"""rtk_validator.py — Validates RTK accuracy flags.
exports: validate_rtk_accuracy
used_by: stages/export_stage.py
rules:
Apply rules: 50=Fixed, 32-49=Float (with σ), 16=Single Point, 0=Failed.
"""

from optictriage.models import ImageRecord
from optictriage.metadata.exif_reader import extract_metadata
from optictriage.metadata.dji_fix import process_drone_telemetry

def validate_rtk_accuracy(records: list[ImageRecord]) -> list[str]:
    """
    Checks the drone's RTK flag and emits warnings for Float, Single, or Failed states.
    """
    warnings = []
    
    for r in records:
        if r.is_flagged:
            continue
            
        exif, xmp = extract_metadata(r.original_path)
        telemetry = process_drone_telemetry(xmp)
        
        rtk_flag = telemetry.get("rtk_flag")
        if rtk_flag is None:
            # Not an RTK drone, skip or generic warn
            continue
            
        rtk_flag = int(rtk_flag)
        
        lon_std = telemetry.get("rtk_std_lon", 0.0)
        lat_std = telemetry.get("rtk_std_lat", 0.0)
        hgt_std = telemetry.get("rtk_std_hgt", 0.0)
        
        fname = r.output_filename or r.original_path
        
        if rtk_flag == 50:
            pass # Fixed, all good
        elif 32 <= rtk_flag <= 49:
            warnings.append(f"[{fname}] RTK Float - Precision limits: Lon {lon_std}m, Lat {lat_std}m, Hgt {hgt_std}m")
        elif rtk_flag == 16:
            warnings.append(f"[{fname}] CRITICAL: Single Point Positioning (No RTK correction).")
        elif rtk_flag == 0:
            warnings.append(f"[{fname}] CRITICAL: RTK Failed (No GPS lock).")
            
    return warnings
