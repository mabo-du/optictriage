"""exif_stage.py — Extracts EXIF data and updates ImageRecords.
exports: ExifStage
used_by: pipeline.py → Orchestrator
rules:
Must not fail pipeline if a single image has malformed EXIF. Flag and continue.
"""

from typing import Any, Dict, Generator
from optictriage.stages.base import Stage
from optictriage.models import ImageRecord, Session
from optictriage.metadata.exif_reader import extract_metadata
from optictriage.metadata.dji_fix import process_drone_telemetry
from optictriage.metadata.validators import validate_metadata
from optictriage.metadata.exif_writer import write_altitude
import os

def _parse_rational(val: Any) -> float:
    try:
        # Some EXIF rational values are formatted as "numerator/denominator"
        if isinstance(val, str) and "/" in val:
            num, den = val.split("/")
            return float(num) / float(den)
        return float(val)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0

def _parse_gps(val: Any) -> float:
    try:
        # Example: "48/1 51/1 33/1"
        if isinstance(val, str):
            parts = val.split()
            if len(parts) == 3:
                deg = _parse_rational(parts[0])
                min_ = _parse_rational(parts[1])
                sec = _parse_rational(parts[2])
                return deg + (min_ / 60.0) + (sec / 3600.0)
        return float(val)
    except Exception:
        return 0.0

class ExifStage(Stage):
    """Processes images sequentially to extract and validate metadata."""

    def run(self) -> Generator[Dict[str, Any], None, None]:
        with self.db_manager.get_session() as db_session:
            # Only process images that are imported and not flagged as duplicates
            images = db_session.query(ImageRecord).filter_by(
                session_id=self.session_id, 
                processing_state="imported"
            ).all()

            total = len(images)
            if total == 0:
                yield {"status": "complete", "progress": 100.0, "message": "No unflagged images to process."}
                return
                
            # Fetch base station elevation from session settings (default 0.0)
            base_elevation = 0.0
            session_obj = db_session.query(Session).get(self.session_id)
            if session_obj and session_obj.settings:
                base_elevation = float(session_obj.settings.get("base_station_elevation", 0.0))

            yield {"status": "running", "progress": 0.0, "message": f"Extracting EXIF for {total} images..."}

            for idx, record in enumerate(images):
                progress = (idx / total) * 100
                yield {"status": "running", "progress": progress, "message": f"Reading metadata for {record.output_filename or record.original_path}..."}

                try:
                    errors = []
                    
                    if os.path.getsize(record.original_path) == 0:
                        record.is_flagged = 1
                        record.processing_state = "error"
                        record.flag_reasons = (record.flag_reasons or []) + ["Zero-byte file."]
                        continue

                    metadata = extract_metadata(record.original_path)
                    exif = metadata.get("exif", {})
                    xmp = metadata.get("xmp", {})
                    
                    if not exif:
                        errors.append("Truncated or missing EXIF block.")

                    # Extract basic EXIF
                    record.camera_make = exif.get("Exif.Image.Make")
                    record.camera_model = exif.get("Exif.Image.Model")
                    record.focal_length_mm = _parse_rational(exif.get("Exif.Photo.FocalLength"))
                    record.aperture = _parse_rational(exif.get("Exif.Photo.FNumber"))
                    record.iso = int(_parse_rational(exif.get("Exif.Photo.ISOSpeedRatings", 0)))
                    record.shutter_speed = str(exif.get("Exif.Photo.ExposureTime"))
                    record.capture_time = str(exif.get("Exif.Photo.DateTimeOriginal"))

                    # Parse standard GPS
                    lat = _parse_gps(exif.get("Exif.GPSInfo.GPSLatitude"))
                    lat_ref = exif.get("Exif.GPSInfo.GPSLatitudeRef", "N")
                    if lat_ref == "S": lat = -lat
                    
                    lon = _parse_gps(exif.get("Exif.GPSInfo.GPSLongitude"))
                    lon_ref = exif.get("Exif.GPSInfo.GPSLongitudeRef", "E")
                    if lon_ref == "W": lon = -lon
                    
                    record.gps_lat = lat
                    record.gps_lon = lon
                    record.gps_alt = _parse_rational(exif.get("Exif.GPSInfo.GPSAltitude"))

                    # Image dimensions (often stored in Exif.Photo.PixelXDimension)
                    width = exif.get("Exif.Photo.PixelXDimension")
                    height = exif.get("Exif.Photo.PixelYDimension")
                    if width and height:
                        record.image_width = int(width)
                        record.image_height = int(height)

                    # Edge Case: Missing GPS tags
                    if not exif.get("Exif.GPSInfo.GPSLatitude") or not exif.get("Exif.GPSInfo.GPSLongitude"):
                        errors.append("Missing GPS location tags.")

                    # DJI/Autel specific Telemetry parsing
                    if str(record.camera_make).upper() == "DJI" and not xmp:
                        errors.append("DJI drone missing XMP telemetry block.")
                        
                    telemetry = process_drone_telemetry(xmp)
                    record.relative_alt = telemetry.get("relative_alt")
                    
                    # Apply Altitude Fix Write-Back via ExifTool
                    if record.relative_alt is not None:
                        fixed_alt = record.relative_alt + base_elevation
                        success = write_altitude(record.original_path, fixed_alt)
                        if success:
                            record.gps_alt = fixed_alt
                        else:
                            errors.append("Failed to write corrected altitude to file via ExifTool.")

                    # Validate tags
                    is_valid, validation_errors = validate_metadata(telemetry, exif)
                    errors.extend(validation_errors)
                    
                    if len(errors) > 0:
                        record.is_flagged = 1
                        existing_flags = record.flag_reasons or []
                        record.flag_reasons = existing_flags + errors

                    record.processing_state = "exif_extracted"

                except Exception as e:
                    record.processing_state = "error"
                    record.error_message = f"Metadata extraction failed: {str(e)}"
                    record.is_flagged = 1
                    existing_flags = record.flag_reasons or []
                    record.flag_reasons = existing_flags + ["metadata_error"]

            yield {"status": "complete", "progress": 100.0, "message": "EXIF extraction complete."}
