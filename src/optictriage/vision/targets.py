"""targets.py — ArUco and ChArUco detection with subpixel refinement.
exports: detect_targets
used_by: stages/target_stage.py → TargetStage
rules:
Must apply cornerSubPix to all detected marker corners.
"""

import cv2
import numpy as np
from typing import List, Dict, Any

def detect_targets(gray_or_binary_image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Detects ArUco and ChArUco targets in the preprocessed image.
    Applies cornerSubPix for high precision.
    Returns a list of detected targets.
    """
    # Define dictionaries to search
    dicts_to_search = [
        cv2.aruco.DICT_4X4_250,
        cv2.aruco.DICT_6X6_250
    ]
    
    results = []
    
    # Setup subpixel refinement parameters
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.001)
    
    for dict_id in dicts_to_search:
        aruco_dict = cv2.aruco.getPredefinedDictionary(dict_id)
        parameters = cv2.aruco.DetectorParameters()
        
        # Detector changed in OpenCV 4.7+
        try:
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
            corners, ids, rejected = detector.detectMarkers(gray_or_binary_image)
        except AttributeError:
            # Fallback for older OpenCV
            corners, ids, rejected = cv2.aruco.detectMarkers(gray_or_binary_image, aruco_dict, parameters=parameters)
            
        if ids is not None and len(ids) > 0:
            # Refine corners with SubPix
            for i in range(len(corners)):
                cv2.cornerSubPix(gray_or_binary_image, corners[i], (5, 5), (-1, -1), criteria)
                
                # Format output
                marker_corners = corners[i][0].tolist()
                results.append({
                    "target_type": f"aruco_{dict_id}",
                    "id": int(ids[i][0]),
                    "corners": marker_corners
                })
            
            # Attempt ChArUco Interpolation (assume a standard 5x7 or 8x11 board for now, as board definition is required)
            # The exact board parameters usually need to be known. 
            # We will use a standard ChArUco board (5x7, square length 0.04, marker length 0.02)
            try:
                board = cv2.aruco.CharucoBoard((5, 7), 0.04, 0.02, aruco_dict)
                charuco_retval, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
                    corners, ids, gray_or_binary_image, board
                )
                if charuco_retval > 0:
                    for i in range(charuco_retval):
                        results.append({
                            "target_type": "charuco_corner",
                            "id": int(charuco_ids[i][0]),
                            "corners": charuco_corners[i][0].tolist()
                        })
            except cv2.error as e:
                # Edge case: ChArUco board partially outside frame or invalid topology
                pass
            except Exception:
                pass
                
    return results
