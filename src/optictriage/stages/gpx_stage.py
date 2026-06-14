"""gpx_stage.py — GPS Track Alignment stage.
exports: GpxStage
used_by: pipeline.py
rules:
Must apply integer-seconds offset.
Must not extrapolate outside GPX bounds.
"""

from typing import Any, Dict, Generator
from datetime import datetime
import numpy as np
from scipy.interpolate import interp1d
import gpxpy

from optictriage.stages.base import Stage, StageError
from optictriage.metadata.exif_writer import write_gps_coordinates

class GpxStage(Stage):
    def run(self) -> Generator[Dict[str, Any], None, None]:
        session = self.db_manager.get_session(self.session_id)
        settings = session.settings or {}
        gpx_path = settings.get("gpx_path")
        time_offset = int(settings.get("gpx_time_offset", 0))
        
        if not gpx_path:
            yield {"status": "skipped", "progress": 1.0, "message": "No GPX path provided."}
            return
            
        try:
            with open(gpx_path, 'r') as f:
                gpx = gpxpy.parse(f)
        except Exception as e:
            raise StageError(f"Failed to parse GPX: {e}")
            
        points = []
        for track in gpx.tracks:
            for segment in track.segments:
                for pt in segment.points:
                    if pt.time:
                        points.append((pt.time.timestamp(), pt.latitude, pt.longitude, pt.elevation or 0.0))
                        
        if not points:
            raise StageError("GPX file contains no timestamps.")
            
        points.sort(key=lambda x: x[0])
        t_arr = np.array([p[0] for p in points])
        lat_arr = np.array([p[1] for p in points])
        lon_arr = np.array([p[2] for p in points])
        alt_arr = np.array([p[3] for p in points])
        
        lat_interp = interp1d(t_arr, lat_arr, kind='linear', bounds_error=False, fill_value=np.nan)
        lon_interp = interp1d(t_arr, lon_arr, kind='linear', bounds_error=False, fill_value=np.nan)
        alt_interp = interp1d(t_arr, alt_arr, kind='linear', bounds_error=False, fill_value=np.nan)
        
        images = self.db_manager.get_images_by_session(self.session_id)
        if not images:
            yield {"status": "complete", "progress": 1.0, "message": "No images to process"}
            return

        total = len(images)
        
        for idx, img in enumerate(images):
            if not img.capture_time:
                continue
                
            try:
                # Format is typically "YYYY:MM:DD HH:MM:SS"
                dt = datetime.strptime(img.capture_time, "%Y:%m:%d %H:%M:%S")
                img_t = dt.timestamp() + time_offset
                
                lat = float(lat_interp(img_t))
                lon = float(lon_interp(img_t))
                alt = float(alt_interp(img_t))
                
                if np.isnan(lat) or np.isnan(lon):
                    flags = img.flag_reasons or []
                    if "gpx_out_of_bounds" not in flags:
                        flags.append("gpx_out_of_bounds")
                        img.flag_reasons = flags
                        img.is_flagged = 1
                    self.db_manager.commit()
                else:
                    img.gps_lat = lat
                    img.gps_lon = lon
                    img.gps_alt = alt
                    self.db_manager.commit()
                    
                    # Write to file
                    write_gps_coordinates(img.original_path, lat, lon, alt)
                    
            except Exception as e:
                pass
                
            yield {"status": "processing", "progress": (idx + 1) / total, "message": f"Aligned GPX for {img.output_filename or img.original_path}"}
            
        yield {"status": "complete", "progress": 1.0, "message": "GPX alignment complete"}
