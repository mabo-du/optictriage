"""exif_writer.py — Subprocess wrapper for ExifTool.
exports: write_altitude
used_by: stages/exif_stage.py → ExifStage
rules:
Must use exiftool subprocess for safe in-place EXIF modification.
"""

import subprocess
import os
import logging

def write_altitude(filepath: str, altitude: float) -> bool:
    """
    Overwrites GPSAltitude and GPSAltitudeRef using ExifTool.
    This permanently modifies the original file safely.
    """
    if not os.path.exists(filepath):
        return False
        
    try:
        # -overwrite_original prevents creating _original backups
        # -GPSAltitudeRef=0 forces Above Sea Level
        cmd = [
            "exiftool",
            f"-GPSAltitude={altitude:.3f}",
            "-GPSAltitudeRef=0",
            "-overwrite_original",
            filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    except Exception as e:
        logging.error(f"ExifTool subprocess failed: {e}")
        return False

def write_gps_coordinates(filepath: str, lat: float, lon: float, alt: float) -> bool:
    """
    Overwrites GPSLatitude, GPSLongitude, and GPSAltitude using ExifTool.
    Includes proper hemisphere references.
    """
    if not os.path.exists(filepath):
        return False
        
    try:
        lat_ref = "N" if lat >= 0 else "S"
        lon_ref = "E" if lon >= 0 else "W"
        
        cmd = [
            "exiftool",
            f"-GPSLatitude={abs(lat)}",
            f"-GPSLatitudeRef={lat_ref}",
            f"-GPSLongitude={abs(lon)}",
            f"-GPSLongitudeRef={lon_ref}",
            f"-GPSAltitude={alt:.3f}",
            "-GPSAltitudeRef=0",
            "-overwrite_original",
            filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    except Exception as e:
        logging.error(f"ExifTool subprocess failed: {e}")
        return False
