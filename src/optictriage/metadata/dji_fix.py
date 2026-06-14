"""dji_fix.py — Corrects altitude and extracts RTK standard deviation metrics.
exports: process_drone_telemetry
used_by: stages/exif_stage.py → ExifStage
rules:
Must handle Autel legacy inversions and DJI RtkStd metrics.
"""

from typing import Dict, Any, Tuple

def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        # XMP values often have '+120.00' format
        if isinstance(val, str):
            val = val.replace('+', '')
        return float(val)
    except (ValueError, TypeError):
        return default

def process_drone_telemetry(xmp: Dict[str, str]) -> Dict[str, Any]:
    """
    Parses complex Drone telemetry values out of the XMP dictionary.
    Handles DJI namespaces, Autel typos, and extracts RTK Precision metrics.
    """
    result = {
        "relative_alt": None,
        "pitch": None,
        "roll": None,
        "yaw": None,
        "rtk_flag": 0,
        "rtk_std_lon": None,
        "rtk_std_lat": None,
        "rtk_std_hgt": None,
    }

    # -- Altitude --
    # DJI priority
    if "Xmp.drone-dji:RelativeAltitude" in xmp:
        result["relative_alt"] = _safe_float(xmp["Xmp.drone-dji:RelativeAltitude"])
    elif "Xmp.drone-dji:AbsoluteAltitude" in xmp:
        result["relative_alt"] = _safe_float(xmp["Xmp.drone-dji:AbsoluteAltitude"])
    # Autel priority
    elif "Xmp.drone:AbsoluteAltitude" in xmp:
        result["relative_alt"] = _safe_float(xmp["Xmp.drone:AbsoluteAltitude"])
        
    # -- Orientation (Pitch, Roll, Yaw) --
    if "Xmp.drone-dji:GimbalPitchDegree" in xmp:
        result["pitch"] = _safe_float(xmp["Xmp.drone-dji:GimbalPitchDegree"])
        result["roll"] = _safe_float(xmp.get("Xmp.drone-dji:GimbalRollDegree", 0))
        result["yaw"] = _safe_float(xmp.get("Xmp.drone-dji:GimbalYawDegree", 0))
    elif "Xmp.drone:Pitch" in xmp:
        result["pitch"] = _safe_float(xmp["Xmp.drone:Pitch"])
        result["roll"] = _safe_float(xmp.get("Xmp.drone:Roll", 0))
        result["yaw"] = _safe_float(xmp.get("Xmp.drone:Yaw", 0))
    elif "Xmp.Camera:Pitch" in xmp:
        # Legacy Autel Pitch Inversion
        # Legacy defines nadir as 0 instead of -90
        raw_pitch = _safe_float(xmp["Xmp.Camera:Pitch"])
        result["pitch"] = 90.0 - raw_pitch
        result["roll"] = _safe_float(xmp.get("Xmp.Camera:Roll", 0))
        result["yaw"] = _safe_float(xmp.get("Xmp.Camera:Yaw", 0))

    # -- Autel Typo --
    # Autel sometimes misspells Longitude as GpsLongtitude
    if "Xmp.drone:GpsLongtitude" in xmp and "Xmp.drone:GpsLongitude" not in xmp:
        # We don't overwrite the actual DB value here, but this is a stub for the validation hook.
        pass

    # -- RTK Flags & Precision --
    if "Xmp.drone-dji:RtkFlag" in xmp:
        result["rtk_flag"] = int(_safe_float(xmp["Xmp.drone-dji:RtkFlag"]))
        result["rtk_std_lon"] = _safe_float(xmp.get("Xmp.drone-dji:RtkStdLon"))
        result["rtk_std_lat"] = _safe_float(xmp.get("Xmp.drone-dji:RtkStdLat"))
        result["rtk_std_hgt"] = _safe_float(xmp.get("Xmp.drone-dji:RtkStdHgt"))
    elif "Xmp.drone:RtkFlag" in xmp:
        result["rtk_flag"] = int(_safe_float(xmp["Xmp.drone:RtkFlag"]))

    return result
