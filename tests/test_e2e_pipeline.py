import os
import pytest
import piexif
from PIL import Image, ImageDraw
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from optictriage.database import Base, DatabaseManager
from optictriage.models import Session, ImageRecord
from optictriage.pipeline import PipelineOrchestrator
from optictriage.stages.import_stage import ImportStage
from optictriage.stages.exif_stage import ExifStage
from optictriage.stages.quality_stage import QualityStage
from optictriage.stages.target_stage import TargetStage
from optictriage.stages.export_stage import ExportStage
from unittest.mock import patch

def _decimal_to_dms(deg):
    deg = abs(deg)
    d = int(deg)
    md = (deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return ((d, 1), (m, 1), (int(sd * 10000), 10000))

def create_synthetic_jpeg(path, lat, lon, alt, capture_time, is_blur=False, offset=0):
    if is_blur:
        img = Image.new('RGB', (100, 100), color='gray')
    else:
        img = Image.new('RGB', (100, 100), color='blue')
        draw = ImageDraw.Draw(img)
        draw.rectangle([20 + offset, 20 + offset, 80 - offset, 80 - offset], fill="white")
        
    exif_dict = {
        "0th": {
            piexif.ImageIFD.Make: b"SyntheticMake",
            piexif.ImageIFD.Model: b"SyntheticModel",
        },
        "Exif": {
            piexif.ExifIFD.FocalLength: (50, 1),
            piexif.ExifIFD.DateTimeOriginal: capture_time.encode('utf-8')
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: b'N' if lat >= 0 else b'S',
            piexif.GPSIFD.GPSLatitude: _decimal_to_dms(lat),
            piexif.GPSIFD.GPSLongitudeRef: b'E' if lon >= 0 else b'W',
            piexif.GPSIFD.GPSLongitude: _decimal_to_dms(lon),
            piexif.GPSIFD.GPSAltitudeRef: 0,
            piexif.GPSIFD.GPSAltitude: (int(alt * 1000), 1000)
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    img.save(path, "jpeg", exif=exif_bytes)

class MockDBManager(DatabaseManager):
    def __init__(self, engine):
        self.engine = engine
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def get_session(self):
        class SessionContextManager:
            def __init__(self, session_maker):
                self.session = session_maker()
            def __enter__(self):
                return self.session
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None:
                    self.session.commit()
                else:
                    self.session.rollback()
                self.session.close()
        return SessionContextManager(self.SessionLocal)

def test_full_pipeline_e2e(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    
    base_lat = 34.0522
    base_lon = -118.2437
    base_alt = 100.0
    
    for i in range(12):
        path = input_dir / f"img_{i:02d}.jpg"
        is_blur = (i == 5)
        # Force img_02 to be visually identical to img_01 to trigger near duplicate
        offset = 1 if i == 2 else i
        
        create_synthetic_jpeg(
            str(path),
            lat=base_lat + (i * 0.0001),
            lon=base_lon + (i * 0.0001),
            alt=base_alt,
            capture_time=f"2023:01:01 12:00:{i:02d}",
            is_blur=is_blur,
            offset=offset
        )
        
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    
    db_manager = MockDBManager(engine)
    
    with db_manager.get_session() as db:
        session = Session(
            input_folder=str(input_dir),
            output_folder=str(output_dir),
            settings={
                "export_colmap": True,
                "export_odm": True,
                "export_metashape": True,
                # Disable default thresholds for synthetic tests:
                # Pillow-generated images lack real-world texture and dynamic range,
                # so the default thresholds would flag all generated images as overexposed/glare.
                "exposure_threshold": 100.0,
                "glare_threshold": 100.0,
                "phash_threshold": 1
            }
        )
        db.add(session)
        db.commit()
        session_id = session.id

    orchestrator = PipelineOrchestrator(session_id, db_manager)
    orchestrator.add_stage(ImportStage)
    orchestrator.add_stage(ExifStage)
    orchestrator.add_stage(QualityStage)
    orchestrator.add_stage(TargetStage)
    orchestrator.add_stage(ExportStage)
    
    # Run the pipeline with mocked telemetry so synthetic JPEGs don't get flagged for missing XMP
    with patch('optictriage.stages.exif_stage.process_drone_telemetry') as mock_telemetry, \
         patch('optictriage.stages.exif_stage.write_altitude') as mock_write:
        mock_telemetry.return_value = {"relative_alt": 100.0, "rtk_flag": 50}
        mock_write.return_value = True
        list(orchestrator.run())
    
    # Find the generated export directory
    export_dirs = list(output_dir.glob("OpticTriage_Export_*"))
    assert len(export_dirs) == 1, "Expected exactly one export directory"
    export_dir = export_dirs[0]
    
    # Assertions
    # 1. Master CSV manifest
    import csv
    manifest_path = export_dir / "optictriage_manifest.csv"
    assert manifest_path.exists(), "CSV manifest does not exist"
    
    with open(manifest_path, 'r') as f:
        reader = list(csv.DictReader(f))
        assert len(reader) == 12, f"CSV manifest has {len(reader)} rows, expected 12"
        for row in reader:
            assert row['output_filename']
            assert row['blur_score']
            assert row['exposure_clipped_pct']
            
    # 2. Passed and flagged subdirectories
    passed_dir = export_dir / "passed"
    flagged_dir = export_dir / "flagged"
    assert passed_dir.exists(), "Passed directory does not exist"
    assert flagged_dir.exists(), "Flagged directory does not exist"
    
    num_passed = len(list(passed_dir.rglob("*.jpg")))
    num_flagged = len(list(flagged_dir.glob("*.jpg")))
    assert num_passed + num_flagged == 12, f"Expected 12 images between passed/flagged, got {num_passed + num_flagged}"
    
    # 3. Near-identical image flagged
    with db_manager.get_session() as db:
        records = db.query(ImageRecord).filter_by(session_id=session_id).all()
        
        img_02 = next((r for r in records if "img_02.jpg" in r.original_path), None)
        assert img_02 is not None
        assert img_02.is_flagged, "img_02 was not flagged"
        assert "near_duplicate" in img_02.flag_reasons, "img_02 missing near_duplicate flag"
        
        # 4. Intentionally blurred image is flagged
        img_05 = next((r for r in records if "img_05.jpg" in r.original_path), None)
        assert img_05 is not None
        assert img_05.is_flagged, "img_05 was not flagged"
        assert "blur" in img_05.flag_reasons, "img_05 missing blur flag"
        
    # 5. COLMAP database
    colmap_db_path = export_dir / "colmap" / "database.db"
    assert colmap_db_path.exists(), "COLMAP database does not exist"
    import sqlite3
    with sqlite3.connect(colmap_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT params FROM cameras")
        rows = cursor.fetchall()
        assert len(rows) > 0, "COLMAP cameras table is empty"
        assert len(rows[0][0]) == 64, "COLMAP camera params BLOB is not exactly 64 bytes"
        
    # 6. ODM gcp_list.txt
    gcp_list_path = export_dir / "odm" / "gcp_list.txt"
    if gcp_list_path.exists():
        with open(gcp_list_path, "r") as f:
            lines = f.readlines()
            if lines:
                assert lines[0].startswith("+proj=") or lines[0].startswith("EPSG:") or lines[0].startswith("WGS84"), "Invalid PROJ string in GCP list"
                for line in lines:
                    assert "NaN" not in line and "nan" not in line, "NaN found in GCP list"
            
    # 7. Metashape script
    metashape_script_path = export_dir / "metashape" / "run_metashape.py"
    assert metashape_script_path.exists(), "Metashape script does not exist"
    with open(metashape_script_path, "r") as f:
        content = f.read()
        assert "Metashape.app.document" in content, "Metashape script missing Metashape.app.document"
