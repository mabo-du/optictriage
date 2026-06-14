import os
import sqlite3
import numpy as np
from optictriage.exporters.colmap import generate_colmap_files
from optictriage.models import ImageRecord

def test_colmap_blob_and_shift(tmp_path):
    record = ImageRecord()
    record.original_path = "test.jpg"
    record.output_filename = "test.jpg"
    record.camera_make = "DJI"
    record.camera_model = "Mavic 3"
    record.image_width = 4000
    record.image_height = 3000
    record.is_flagged = False
    
    generate_colmap_files([record], str(tmp_path))
    
    db_path = tmp_path / "database.db"
    assert db_path.exists()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT params, prior_focal_length FROM cameras LIMIT 1")
    row = cursor.fetchone()
    
    params_blob = row[0]
    prior_focal_length = row[1]
    
    assert len(params_blob) == 64, f"BLOB length is {len(params_blob)} bytes, expected 64"
    
    params = np.frombuffer(params_blob, dtype=np.float64)
    # [fx, fy, cx, cy, k1, k2, p1, p2]
    cx = params[2]
    cy = params[3]
    
    assert cx == (4000 / 2.0) + 0.5
    assert cy == (3000 / 2.0) + 0.5
    assert prior_focal_length == 1
