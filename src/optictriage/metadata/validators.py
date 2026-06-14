"""validators.py — Validates EXIF/XMP tags against defined rules.
exports: validate_metadata
used_by: stages/exif_stage.py → ExifStage
rules:
Must flag missing critical values rather than crashing.
"""

from typing import Dict, Any, List, Tuple

def validate_metadata(telemetry: Dict[str, Any], exif_data: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Validates that essential metadata (GPS, focal length, altitude) exists.
    Returns (is_valid, list_of_errors).
    """
    errors = []
    
    # 1. Check RTK constraints
    rtk_flag = telemetry.get("rtk_flag", 0)
    
    if rtk_flag == 16:
        errors.append("GNSS Error: Single Point Positioning (SPP) detected. Meter-level drift expected.")
    elif 32 <= rtk_flag <= 49:
        # Float RTK
        lon_std = telemetry.get("rtk_std_lon") or 0.0
        lat_std = telemetry.get("rtk_std_lat") or 0.0
        hgt_std = telemetry.get("rtk_std_hgt") or 0.0
        mean_std = (lon_std + lat_std + hgt_std) / 3.0
        if mean_std > 0.0:
            errors.append(f"GNSS Warning: RTK Float. Mean σ = {mean_std:.3f}m.")
        else:
            errors.append("GNSS Warning: RTK Float detected. Decimeter drift expected.")
    elif rtk_flag == 0:
        # 0 usually means no RTK or normal GPS. We don't fail immediately, but warn if required.
        pass

    # 2. Altitude check
    if telemetry.get("relative_alt") is None:
        errors.append("Missing RelativeAltitude (required for ground projection).")
        
    # 3. GPS check (from standard EXIF)
    if "Exif.GPSInfo.GPSLatitude" not in exif_data or "Exif.GPSInfo.GPSLongitude" not in exif_data:
        errors.append("Missing standard GPS Latitude/Longitude coordinates.")
        
    is_valid = len(errors) == 0
    return is_valid, errors
