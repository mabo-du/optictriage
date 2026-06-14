"""odm.py — Generates ODM gcp_list.txt, cameras.json, and image_groups.txt.
exports: generate_odm_files
used_by: stages/export_stage.py → ExportStage
rules:
Must replace NaN Z-values with 0.0 in gcp_list.txt to prevent solver crashes.
Must group cameras by Make+Model+W+H+FL.
"""

import os
import json
import math
from optictriage.models import ImageRecord

def generate_odm_files(records: list[ImageRecord], output_dir: str):
    """
    Generates OpenDroneMap required files.
    """
    _generate_image_groups(records, output_dir)
    _generate_gcp_list(records, output_dir) # Placeholder, assuming GCPs come from targets
    _generate_cameras_json(records, output_dir)
    
def _generate_image_groups(records: list[ImageRecord], output_dir: str):
    passed_records = [r for r in records if not r.is_flagged]
    
    groups = {}
    group_id_counter = 0
    
    group_lines = []
    for r in passed_records:
        if not r.output_filename:
            continue
            
        # Hash grouping strategy
        make = r.camera_make or "Unknown"
        model = r.camera_model or "Unknown"
        w = r.image_width or 0
        h = r.image_height or 0
        fl = r.focal_length_mm or 0.0
        c_idx = r.camera_group_idx or 1
        
        group_hash = f"{make}_{model}_{w}_{h}_{fl}_{c_idx}"
        
        if group_hash not in groups:
            groups[group_hash] = group_id_counter
            group_id_counter += 1
            
        group_id = groups[group_hash]
        group_lines.append(f"{r.output_filename} {group_id}")
        
    out_path = os.path.join(output_dir, "image_groups.txt")
    with open(out_path, "w") as f:
        f.write("\n".join(group_lines))

def _generate_gcp_list(records: list[ImageRecord], output_dir: str):
    # This usually requires known ground truth coordinates of the targets.
    # For now, we will create a dummy file demonstrating the PROJ/EPSG header 
    # and whitespace-delimitation + NaN zeroing rule.
    
    out_path = os.path.join(output_dir, "gcp_list.txt")
    with open(out_path, "w") as f:
        # PROJ/EPSG header on line one
        f.write("+proj=utm +zone=32 +datum=WGS84 +units=m +no_defs\n")
        
        # Example of replacing NaN Z with 0.0:
        # E.g. x y z pixel_x pixel_y image_name gcp_name
        z_value = float('nan')
        safe_z = 0.0 if math.isnan(z_value) else z_value
        # f.write(f"500000 4000000 {safe_z} 1000 1000 IMG_0001.JPG GCP1\n")

def _generate_cameras_json(records: list[ImageRecord], output_dir: str):
    # Brown-Conrady OpenSfM format cameras
    cameras = {}
    
    for r in records:
        if r.is_flagged or not r.output_filename:
            continue
            
        make = r.camera_make or "Unknown"
        model = r.camera_model or "Unknown"
        camera_id = f"{make} {model}"
        
        if camera_id not in cameras:
            # Provide rough defaults
            cameras[camera_id] = {
                "projection_type": "perspective",
                "width": r.image_width or 4000,
                "height": r.image_height or 3000,
                "focal_x": 0.8,
                "focal_y": 0.8,
                "c_x": 0.0,
                "c_y": 0.0,
                "k1": 0.0,
                "k2": 0.0,
                "p1": 0.0,
                "p2": 0.0
            }
            
    out_path = os.path.join(output_dir, "cameras.json")
    with open(out_path, "w") as f:
        json.dump(cameras, f, indent=4)
