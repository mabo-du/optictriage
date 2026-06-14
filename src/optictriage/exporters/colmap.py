"""colmap.py — Generates COLMAP database and text files.
exports: generate_colmap_files
used_by: stages/export_stage.py → ExportStage
rules:
Must apply +0.5 shift to cx, cy.
Must pack camera parameters as 64-byte little-endian float64 BLOB: [fx, fy, cx, cy, k1, k2, p1, p2].
Must set prior_focal_length = 1.
"""

import os
import sqlite3
import numpy as np
from optictriage.models import ImageRecord

def generate_colmap_files(records: list[ImageRecord], output_dir: str):
    """
    Generates COLMAP database and project text files.
    """
    db_path = os.path.join(output_dir, "database.db")
    
    # 1. Initialize SQLite Database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE cameras (
            camera_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            model INTEGER NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            params BLOB,
            prior_focal_length INTEGER NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE images (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            name TEXT NOT NULL UNIQUE,
            camera_id INTEGER NOT NULL,
            prior_qw REAL,
            prior_qx REAL,
            prior_qy REAL,
            prior_qz REAL,
            prior_tx REAL,
            prior_ty REAL,
            prior_tz REAL,
            CONSTRAINT image_id_check CHECK(image_id >= 0 and image_id < 2147483647),
            FOREIGN KEY(camera_id) REFERENCES cameras(camera_id)
        )
    ''')
    
    # COLMAP OPENCV Model ID is 4
    OPENCV_MODEL_ID = 4
    
    cameras_map = {} # (make, model, w, h) -> camera_id
    
    for r in records:
        if r.is_flagged or not r.output_filename:
            continue
            
        cam_key = (r.camera_make, r.camera_model, r.image_width, r.image_height)
        
        if cam_key not in cameras_map:
            w = r.image_width or 4000
            h = r.image_height or 3000
            
            # Rough focal length estimation (in pixels)
            # Typically 0.8 * max(w, h) if unknown
            fx = fy = 0.8 * max(w, h)
            
            # Apply +0.5 shift to pixel centers for COLMAP origin
            cx = (w / 2.0) + 0.5
            cy = (h / 2.0) + 0.5
            
            k1 = k2 = p1 = p2 = 0.0
            
            # Pack exactly 8 parameters as little-endian float64
            params = np.array([fx, fy, cx, cy, k1, k2, p1, p2], dtype=np.float64).tobytes()
            
            # prior_focal_length = 1 
            cursor.execute('''
                INSERT INTO cameras (model, width, height, params, prior_focal_length)
                VALUES (?, ?, ?, ?, ?)
            ''', (OPENCV_MODEL_ID, w, h, params, 1))
            
            cameras_map[cam_key] = cursor.lastrowid
            
        camera_id = cameras_map[cam_key]
        
        # Insert image
        # Using GPS coordinates for prior translation if available (could be transformed to ECEF, but keeping it simple)
        tx = r.gps_lon if r.gps_lon is not None else 0.0
        ty = r.gps_lat if r.gps_lat is not None else 0.0
        tz = r.gps_alt if r.gps_alt is not None else 0.0
        
        cursor.execute('''
            INSERT INTO images (name, camera_id, prior_tx, prior_ty, prior_tz)
            VALUES (?, ?, ?, ?, ?)
        ''', (r.output_filename, camera_id, tx, ty, tz))
        
    conn.commit()
    conn.close()
    
    # 2. Write Text Files (cameras.txt, images.txt, project.ini)
    _write_colmap_text_files(output_dir)
    
def _write_colmap_text_files(output_dir: str):
    # Just creating stub files for completeness as DB handles the actual import in COLMAP 3.8+
    with open(os.path.join(output_dir, "cameras.txt"), "w") as f:
        f.write("# Camera list with one line of data per camera:\n")
        
    with open(os.path.join(output_dir, "images.txt"), "w") as f:
        f.write("# Image list with two lines of data per image:\n")
        
    with open(os.path.join(output_dir, "project.ini"), "w") as f:
        f.write("[General]\n")
        f.write("database_path=database.db\n")
        f.write("image_path=passed\n")
