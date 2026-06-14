"""database_migration.py — Handles SQLite schema migrations dynamically.
exports: migrate_db
used_by: database.py
rules:
Check column existence using PRAGMA table_info before applying ALTER TABLE.
"""

import sqlite3
import os

def migrate_db(db_path: str):
    """Applies schema migrations to an existing SQLite database."""
    # Handle SQLAlchemy connection strings
    if db_path.startswith("sqlite:///"):
        path = db_path.replace("sqlite:///", "")
    else:
        path = db_path
        
    # If the file doesn't exist, SQLAlchemy create_all will handle it
    if path == ":memory:" or not os.path.exists(path):
        return
        
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(image_record)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if not columns:
            return # Table might not exist yet
            
        # V2.0 Color Normalization Schema Changes
        if "color_patches" not in columns:
            cursor.execute("ALTER TABLE image_record ADD COLUMN color_patches VARCHAR")
        if "ccm_matrix" not in columns:
            cursor.execute("ALTER TABLE image_record ADD COLUMN ccm_matrix VARCHAR")
        if "ccm_applied" not in columns:
            cursor.execute("ALTER TABLE image_record ADD COLUMN ccm_applied INTEGER DEFAULT 0")
        if "ccm_keyframe_id" not in columns:
            cursor.execute("ALTER TABLE image_record ADD COLUMN ccm_keyframe_id INTEGER REFERENCES image_record(id)")
            
        conn.commit()
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        conn.close()
