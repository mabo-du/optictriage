import pytest
import os
import sqlite3
from datetime import datetime
from optictriage.models import ImageRecord, Session
from optictriage.stages.export_stage import ExportStage

class MockDBManager:
    def __init__(self, session_obj, records):
        self.session_obj = session_obj
        self.records = records
        self.committed = False
        
    def get_session(self):
        class DBSession:
            def __init__(self, m):
                self.m = m
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            def query(self, cls):
                class Query:
                    def __init__(self, c, m):
                        self.c = c
                        self.m = m
                    def get(self, id):
                        return self.m.session_obj
                    def filter(self, *args, **kwargs):
                        return self
                    def all(self):
                        return self.m.records
                return Query(cls, self.m)
            def commit(self):
                self.m.committed = True
        return DBSession(self)

def test_segmentation_logic(tmp_path):
    session = Session(id=1, input_folder="in", output_folder=str(tmp_path), settings={
        "split_time_gap_mins": 5.0,
        "split_alt_shift_m": 10.0,
        "split_gps_jump_m": 50.0
    })
    
    # R1: base
    r1 = ImageRecord(id=1, session_id=1, original_path="1.jpg", is_flagged=0,
                     capture_time="2026:06:14 10:00:00", gps_alt=100.0, gps_lat=0.0, gps_lon=0.0)
    # R2: time gap 6 mins -> should split to group 2
    r2 = ImageRecord(id=2, session_id=1, original_path="2.jpg", is_flagged=0,
                     capture_time="2026:06:14 10:06:00", gps_alt=100.0, gps_lat=0.0, gps_lon=0.0)
    # R3: alt shift 15m -> should split to group 3
    r3 = ImageRecord(id=3, session_id=1, original_path="3.jpg", is_flagged=0,
                     capture_time="2026:06:14 10:06:10", gps_alt=115.0, gps_lat=0.0, gps_lon=0.0)
    # R4: distance shift ~111km (1 deg lat) -> should split to group 4
    r4 = ImageRecord(id=4, session_id=1, original_path="4.jpg", is_flagged=0,
                     capture_time="2026:06:14 10:06:20", gps_alt=115.0, gps_lat=1.0, gps_lon=0.0)
    # R5: flagged image, shouldn't cause split, should be group 4
    r5 = ImageRecord(id=5, session_id=1, original_path="5.jpg", is_flagged=1,
                     capture_time="2026:06:14 10:06:30", gps_alt=115.0, gps_lat=1.0, gps_lon=0.0)
                     
    records = [r1, r2, r3, r4, r5]
    
    db = MockDBManager(session, records)
    stage = ExportStage(1, db)
    
    # Mock shutil.copy2 to prevent actual copying
    import shutil
    old_copy = shutil.copy2
    shutil.copy2 = lambda src, dst: None
    try:
        list(stage.run())
    finally:
        shutil.copy2 = old_copy
        
    assert r1.camera_group_idx == 1
    assert r2.camera_group_idx == 2
    assert r3.camera_group_idx == 3
    assert r4.camera_group_idx == 4
    assert r5.camera_group_idx == 4
    
    # Verify paths
    assert r1.output_filename.startswith("group_1/IMG_0000")
    assert r2.output_filename.startswith("group_2/IMG_0001")
    # Flagged doesn't get group_X prefix
    assert not r5.output_filename.startswith("group_")
    assert r5.output_filename.startswith("IMG_0004")
