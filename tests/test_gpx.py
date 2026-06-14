import pytest
import tempfile
import os
import json
import numpy as np
from datetime import datetime, timezone
import gpxpy
import gpxpy.gpx
from optictriage.stages.gpx_stage import GpxStage

class MockImage:
    def __init__(self, capture_time, original_path):
        self.capture_time = capture_time
        self.original_path = original_path
        self.output_filename = None
        self.gps_lat = None
        self.gps_lon = None
        self.gps_alt = None
        self.is_flagged = 0
        self.flag_reasons = []

class MockDBManager:
    def __init__(self, settings, images):
        self.settings = settings
        self.images = images
    def get_session(self, session_id):
        class MockSession:
            def __init__(self, s):
                self.settings = s
        return MockSession(self.settings)
    def get_images_by_session(self, session_id):
        return self.images
    def commit(self):
        pass

@pytest.fixture
def dummy_gpx_file(tmp_path):
    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(gpx_track)
    gpx_segment = gpxpy.gpx.GPXTrackSegment()
    gpx_track.segments.append(gpx_segment)
    
    # Track points at t=100 and t=200
    gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(10.0, 20.0, elevation=50.0, time=datetime.fromtimestamp(100, timezone.utc)))
    gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(12.0, 22.0, elevation=60.0, time=datetime.fromtimestamp(200, timezone.utc)))
    
    gpx_path = tmp_path / "track.gpx"
    gpx_path.write_text(gpx.to_xml())
    return str(gpx_path)

def test_gpx_interpolation(dummy_gpx_file, monkeypatch):
    # Mock write_gps_coordinates so it doesn't try to call ExifTool
    import optictriage.stages.gpx_stage
    monkeypatch.setattr(optictriage.stages.gpx_stage, "write_gps_coordinates", lambda p, lat, lon, alt: True)
    
    # Image exactly halfway at t=150. Time offset is 0.
    t_img = datetime.fromtimestamp(150).strftime("%Y:%m:%d %H:%M:%S")
    img1 = MockImage(t_img, "dummy.jpg")
    
    # Image out of bounds (t=300)
    t_out = datetime.fromtimestamp(300).strftime("%Y:%m:%d %H:%M:%S")
    img2 = MockImage(t_out, "dummy2.jpg")
    
    # Image with offset (t=140, but offset +10 = 150)
    t_offset = datetime.fromtimestamp(140).strftime("%Y:%m:%d %H:%M:%S")
    img3 = MockImage(t_offset, "dummy3.jpg")
    
    db1 = MockDBManager({"gpx_path": dummy_gpx_file, "gpx_time_offset": 0}, [img1, img2])
    stage1 = GpxStage(1, db1)
    list(stage1.run())
    
    # img1 should be exactly halfway (lat=11, lon=21, alt=55)
    assert np.isclose(img1.gps_lat, 11.0)
    assert np.isclose(img1.gps_lon, 21.0)
    assert np.isclose(img1.gps_alt, 55.0)
    assert img1.is_flagged == 0
    
    # img2 should be out of bounds
    assert "gpx_out_of_bounds" in img2.flag_reasons
    assert img2.is_flagged == 1
    
    # Test offset
    db2 = MockDBManager({"gpx_path": dummy_gpx_file, "gpx_time_offset": 10}, [img3])
    stage2 = GpxStage(1, db2)
    list(stage2.run())
    
    assert np.isclose(img3.gps_lat, 11.0)
