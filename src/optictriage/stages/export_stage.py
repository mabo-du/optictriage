"""export_stage.py — Copies files to output structure and generates exports.
exports: ExportStage
used_by: pipeline.py → Orchestrator
rules:
Copy, do NOT move. Create timestamped directory.
"""

import os
import shutil
from datetime import datetime
from typing import Any, Dict, Generator

from optictriage.stages.base import Stage
from optictriage.models import ImageRecord, Session
from optictriage.exporters.csv_manifest import generate_csv_manifest
from optictriage.exporters.metashape import generate_metashape_script
from optictriage.exporters.odm import generate_odm_files
from optictriage.exporters.colmap import generate_colmap_files
from optictriage.exporters.gps_overlap import check_gps_overlap
from optictriage.exporters.rtk_validator import validate_rtk_accuracy

class ExportStage(Stage):
    """Handles file copying, folder structuring, and platform-specific exports."""

    def run(self) -> Generator[Dict[str, Any], None, None]:
        with self.db_manager.get_session() as db_session:
            session_obj = db_session.query(Session).get(self.session_id)
            if not session_obj:
                return
                
            base_output_dir = session_obj.output_folder
            records = db_session.query(ImageRecord).filter(
                ImageRecord.session_id == self.session_id
            ).all()

            if not records:
                yield {"status": "complete", "progress": 100.0, "message": "No images to export."}
                return

            yield {"status": "running", "progress": 0.0, "message": "Segmenting camera groups..."}
            
            # --- Grouping Logic ---
            def get_ts(r):
                if not r.capture_time: return 0.0
                try: return datetime.strptime(r.capture_time, "%Y:%m:%d %H:%M:%S").timestamp()
                except Exception: return 0.0

            records.sort(key=get_ts)
            
            settings = session_obj.settings or {}
            gap_mins = float(settings.get("split_time_gap_mins", 5.0))
            alt_shift_m = float(settings.get("split_alt_shift_m", 10.0))
            gps_jump_m = float(settings.get("split_gps_jump_m", 50.0))
            
            def haversine(lat1, lon1, lat2, lon2):
                import math
                R = 6371000
                phi1, phi2 = math.radians(lat1), math.radians(lat2)
                dphi = math.radians(lat2 - lat1)
                dlambda = math.radians(lon2 - lon1)
                a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
                return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

            group_idx = 1
            for i in range(len(records)):
                if i > 0 and not records[i].is_flagged and not records[i-1].is_flagged:
                    prev = records[i-1]
                    curr = records[i]
                    split = False
                    
                    if gap_mins > 0:
                        t1, t2 = get_ts(prev), get_ts(curr)
                        if t1 > 0 and t2 > 0 and (t2 - t1) > (gap_mins * 60):
                            split = True
                            
                    if not split and alt_shift_m > 0:
                        a1, a2 = prev.gps_alt, curr.gps_alt
                        if a1 is not None and a2 is not None and abs(a2 - a1) > alt_shift_m:
                            split = True
                            
                    if not split and gps_jump_m > 0:
                        if prev.gps_lat is not None and prev.gps_lon is not None and curr.gps_lat is not None and curr.gps_lon is not None:
                            dist = haversine(prev.gps_lat, prev.gps_lon, curr.gps_lat, curr.gps_lon)
                            if dist > gps_jump_m:
                                split = True
                                
                    if split:
                        group_idx += 1
                        
                records[i].camera_group_idx = group_idx
            db_session.commit()
            # ----------------------

            yield {"status": "running", "progress": 5.0, "message": "Creating output directories..."}
            
            # 1. Output Folder Structure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = os.path.join(base_output_dir, f"OpticTriage_Export_{timestamp}")
            passed_dir = os.path.join(export_dir, "passed")
            flagged_dir = os.path.join(export_dir, "flagged")
            
            os.makedirs(passed_dir, exist_ok=True)
            os.makedirs(flagged_dir, exist_ok=True)

            total = len(records)
            for idx, r in enumerate(records):
                progress = (idx / total) * 50.0 # First half of progress is copying
                yield {"status": "running", "progress": progress, "message": f"Copying {os.path.basename(r.original_path)}..."}
                
                # Format incremental name
                base_name = f"IMG_{idx:04d}_{os.path.basename(r.original_path)}"
                
                if r.is_flagged:
                    r.output_filename = base_name
                    target_dir = flagged_dir
                else:
                    r.output_filename = f"group_{r.camera_group_idx}/{base_name}"
                    target_dir = passed_dir
                
                target_path = os.path.join(target_dir, r.output_filename)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Non-destructive copy
                shutil.copy2(r.original_path, target_path)
                r.processing_state = "exported"

            # 2. Exporters
            yield {"status": "running", "progress": 60.0, "message": "Generating Master CSV Manifest..."}
            csv_path = generate_csv_manifest(records, export_dir)
            
            # Fetch user selected exporters from session settings
            settings = session_obj.settings or {}
            
            if settings.get("export_odm", False):
                yield {"status": "running", "progress": 85.0, "message": "Generating WebODM files..."}
                odm_dir = os.path.join(export_dir, "odm")
                os.makedirs(odm_dir, exist_ok=True)
                generate_odm_files(records, odm_dir)
                
            if settings.get("export_colmap", False):
                yield {"status": "running", "progress": 90.0, "message": "Generating COLMAP database..."}
                colmap_dir = os.path.join(export_dir, "colmap")
                os.makedirs(colmap_dir, exist_ok=True)
                generate_colmap_files(records, colmap_dir)
                
            if settings.get("export_metashape", False):
                yield {"status": "running", "progress": 92.0, "message": "Generating Metashape script..."}
                metashape_dir = os.path.join(export_dir, "metashape")
                os.makedirs(metashape_dir, exist_ok=True)
                generate_metashape_script(records, metashape_dir, csv_path)

            # 3. GPS & RTK Validations
            yield {"status": "running", "progress": 95.0, "message": "Running GPS & RTK validations..."}
            overlap_warnings = check_gps_overlap(records)
            rtk_warnings = validate_rtk_accuracy(records)
            
            # Write warnings to a log file
            if overlap_warnings or rtk_warnings:
                with open(os.path.join(export_dir, "QC_Warnings.log"), "w") as f:
                    f.write("=== OpticTriage Quality Control Warnings ===\n\n")
                    for w in rtk_warnings:
                        f.write(f"{w}\n")
                    f.write("\n")
                    for w in overlap_warnings:
                        f.write(f"{w}\n")

            yield {"status": "complete", "progress": 100.0, "message": "Export complete.", "export_path": export_dir}
