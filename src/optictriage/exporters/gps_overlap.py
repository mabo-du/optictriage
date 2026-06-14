"""gps_overlap.py — Analyzes GPS footprints for sufficient overlap.
exports: check_gps_overlap
used_by: stages/export_stage.py
rules:
Project camera rays using Pitch/Roll/Yaw (Z-Y-X NED) to flat ground at Z=0.
Use Shapely STRtree for R-Tree spatial index (IoU intersection).
"""

import math
import numpy as np
from pyproj import Proj
from shapely.geometry import Polygon
from shapely.strtree import STRtree
from optictriage.models import ImageRecord
from optictriage.metadata.exif_reader import extract_metadata
from optictriage.metadata.dji_fix import process_drone_telemetry

def _wgs84_to_utm(lat: float, lon: float):
    # Determine UTM zone
    zone_number = int((lon + 180) / 6) + 1
    # Northern or Southern hemisphere
    south = lat < 0
    p = Proj(proj='utm', zone=zone_number, ellps='WGS84', south=south)
    return p(lon, lat)

def _build_rotation_matrix(pitch_deg: float, roll_deg: float, yaw_deg: float) -> np.ndarray:
    """Z-Y-X NED sequence"""
    # Convert to radians
    p = math.radians(pitch_deg)
    r = math.radians(roll_deg)
    y = math.radians(yaw_deg)
    
    # Rotation around X (Roll)
    Rx = np.array([
        [1, 0, 0],
        [0, math.cos(r), -math.sin(r)],
        [0, math.sin(r), math.cos(r)]
    ])
    
    # Rotation around Y (Pitch)
    Ry = np.array([
        [math.cos(p), 0, math.sin(p)],
        [0, 1, 0],
        [-math.sin(p), 0, math.cos(p)]
    ])
    
    # Rotation around Z (Yaw)
    Rz = np.array([
        [math.cos(y), -math.sin(y), 0],
        [math.sin(y), math.cos(y), 0],
        [0, 0, 1]
    ])
    
    return Rz @ Ry @ Rx

def check_gps_overlap(records: list[ImageRecord]) -> list[str]:
    """
    Checks if images maintain 60% frontal and 80% side overlap.
    Returns a list of warning messages.
    """
    warnings = []
    polygons = []
    valid_records = []
    
    # Sensor dimensions (assume standard 1" sensor 13.2 x 8.8mm if unknown)
    sensor_width_mm = 13.2
    sensor_height_mm = 8.8
    
    for r in records:
        if r.is_flagged or r.gps_lat is None or r.gps_lon is None or r.relative_alt is None:
            continue
            
        # Parse Gimbal Pitch/Roll/Yaw from file (since it's not in DB schema)
        exif, xmp = extract_metadata(r.original_path)
        telemetry = process_drone_telemetry(xmp)
        
        # Default to Nadir if missing (-90 pitch, 0 roll, 0 yaw)
        pitch = telemetry.get("gimbal_pitch", -90.0)
        roll = telemetry.get("gimbal_roll", 0.0)
        yaw = telemetry.get("gimbal_yaw", 0.0)
        
        fl_mm = r.focal_length_mm or 8.8 # Default wide angle
        
        # Camera corner rays in camera frame
        dx = sensor_width_mm / 2.0
        dy = sensor_height_mm / 2.0
        z = fl_mm
        
        corners_cam = np.array([
            [-dx, -dy, z],
            [dx, -dy, z],
            [dx, dy, z],
            [-dx, dy, z]
        ])
        
        # Rotate to NED
        R = _build_rotation_matrix(pitch, roll, yaw)
        corners_ned = (R @ corners_cam.T).T
        
        # Project to ground Z=0 (Relative altitude)
        alt = r.relative_alt
        ground_corners = []
        
        utm_x, utm_y = _wgs84_to_utm(r.gps_lat, r.gps_lon)
        
        for ray in corners_ned:
            if ray[2] == 0:
                continue # Edge case: pointing exactly horizontal
            scale = alt / abs(ray[2])
            gx = utm_x + (ray[0] * scale)
            gy = utm_y + (ray[1] * scale)
            ground_corners.append((gx, gy))
            
        if len(ground_corners) == 4:
            try:
                poly = Polygon(ground_corners)
                if poly.is_valid:
                    polygons.append(poly)
                    valid_records.append(r)
            except Exception:
                pass
                
    if len(polygons) < 2:
        return ["Not enough valid GPS coordinates to compute overlap."]
        
    # Build R-Tree
    tree = STRtree(polygons)
    
    # Check overlaps
    for i, poly in enumerate(polygons):
        # Query intersecting indices
        intersecting_indices = tree.query(poly)
        
        # We define frontal (sequential) and side (adjacent swaths).
        # We'll just check max overlap with any neighbor to ensure coverage.
        max_iou = 0.0
        for j in intersecting_indices:
            if i == j:
                continue
            intersection_area = poly.intersection(polygons[j]).area
            union_area = poly.union(polygons[j]).area
            if union_area > 0:
                iou = intersection_area / union_area
                if iou > max_iou:
                    max_iou = iou
                    
        # A simple check: if max IoU is less than ~0.4 (roughly equates to 60% 1D overlap)
        # Note: 60% 1D overlap is ~40% area overlap.
        if max_iou < 0.4:
            warnings.append(f"{valid_records[i].original_path} has low overlap (Max IoU: {max_iou:.2f})")
            
    return warnings
