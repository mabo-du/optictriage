"""colorchecker.py — X-Rite ColorChecker detection.
exports: detect_colorchecker
used_by: stages/target_stage.py → TargetStage
rules:
Flag only, do NOT auto-correct colours.
"""

import cv2
import numpy as np

def detect_colorchecker(image: np.ndarray) -> bool:
    """
    Detects an X-Rite ColorChecker chart using cv2.mcc.
    Returns True if detected. Does NOT apply correction.
    """
    has_mcc, _ = extract_mcc_patches(image)
    return has_mcc

def extract_mcc_patches(image: np.ndarray) -> tuple[bool, list[list[float]]]:
    """
    Detects an X-Rite ColorChecker chart and extracts the 24 measured patch colours.
    Returns (success_bool, rgb_patches).
    rgb_patches is a list of [R, G, B] floats in linear or sRGB (depends on input image).
    Note: getChartsRGB() returns BGR; this function explicitly converts to RGB.
    """
    # mcc requires color image (BGR)
    if len(image.shape) != 3:
        return False, []
        
    try:
        detector = cv2.mcc.CCheckerDetector_create()
        success = detector.process(image, cv2.mcc.MCC24, 1)
        if not success:
            return False, []
            
        checker = detector.getBestColorChecker()
        charts_bgr = checker.getChartsRGB() # Shape usually [24, 3] or [1, 24, 3] depending on OpenCV version
        
        # Ensure it's 2D [24, 3]
        if len(charts_bgr.shape) == 3:
            charts_bgr = charts_bgr[0]
            
        # Convert BGR to RGB
        charts_rgb = charts_bgr[:, ::-1]
        
        return True, charts_rgb.tolist()
    except Exception:
        return False, []

from scipy.optimize import minimize

REFERENCE_LAB_D50 = np.array([
    [37.986, 13.555, 14.059],   [65.711, 18.130, 17.810],   [49.927, -4.880, -21.925],
    [43.139, -13.095, 21.905],  [55.112, 8.844, -25.399],   [70.719, -33.397, -0.199],
    [62.661, 36.067, 57.096],   [40.020, 10.410, -45.964],  [51.124, 48.239, 16.248],
    [30.325, 22.976, -21.587],  [72.532, -23.709, 57.255],  [71.941, 19.363, 67.857],
    [28.778, 14.179, -50.297],  [55.261, -38.342, 31.370],  [42.101, 53.378, 28.190],
    [81.733, 4.039, 79.819],    [51.935, 49.536, -14.282],  [51.038, -28.631, -28.638],
    [96.539, -0.425, 1.186],    [81.257, -0.638, -0.335],   [66.766, -0.734, -0.504],
    [50.867, -0.153, -0.270],   [35.656, -0.421, -1.231],   [20.461, -0.079, -0.973],
])

rgb_to_xyz_d50 = np.array([
    [1.0478112, 0.0228866, -0.0501270],
    [0.0295424, 0.9904844, -0.0170491],
    [-0.0092345, 0.0150436, 0.7521316]
]) @ np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041]
])

def srgb_to_linear(rgb):
    rgb = np.clip(rgb, 0, 1)
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)

def linear_to_srgb(rgb):
    rgb = np.clip(rgb, 0, 1)
    return np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * (rgb ** (1/2.4)) - 0.055)

def xyz_to_lab(xyz):
    Xn, Yn, Zn = 0.96422, 1.00000, 0.82521
    x = xyz[:, 0] / Xn
    y = xyz[:, 1] / Yn
    z = xyz[:, 2] / Zn
    def f(t):
        delta = 6/29
        return np.where(t > delta**3, np.cbrt(t), (t / (3 * delta**2)) + (4 / 29))
    fx, fy, fz = f(x), f(y), f(z)
    return np.column_stack((116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)))

def delta_e_cie2000(lab1, lab2):
    L1, a1, b1 = lab1[:, 0], lab1[:, 1], lab1[:, 2]
    L2, a2, b2 = lab2[:, 0], lab2[:, 1], lab2[:, 2]
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    C_bar = (C1 + C2) / 2.0
    G = 0.5 * (1 - np.sqrt(C_bar**7 / (C_bar**7 + 25**7)))
    a1_prime, a2_prime = (1 + G) * a1, (1 + G) * a2
    C1_prime, C2_prime = np.hypot(a1_prime, b1), np.hypot(a2_prime, b2)
    C_bar_prime = (C1_prime + C2_prime) / 2.0
    h1_prime, h2_prime = np.degrees(np.arctan2(b1, a1_prime)) % 360, np.degrees(np.arctan2(b2, a2_prime)) % 360
    h_bar_prime = np.where(
        np.abs(h1_prime - h2_prime) <= 180,
        (h1_prime + h2_prime) / 2.0,
        np.where(
            h1_prime + h2_prime < 360,
            (h1_prime + h2_prime + 360) / 2.0,
            (h1_prime + h2_prime - 360) / 2.0
        )
    )
    T = 1 - 0.17 * np.cos(np.radians(h_bar_prime - 30)) + 0.24 * np.cos(np.radians(2 * h_bar_prime)) + 0.32 * np.cos(np.radians(3 * h_bar_prime + 6)) - 0.20 * np.cos(np.radians(4 * h_bar_prime - 63))
    delta_h_prime = np.where(
        C1_prime * C2_prime == 0,
        0.0,
        np.where(
            np.abs(h2_prime - h1_prime) <= 180,
            h2_prime - h1_prime,
            np.where(
                h2_prime - h1_prime > 180,
                h2_prime - h1_prime - 360,
                h2_prime - h1_prime + 360
            )
        )
    )
    delta_L_prime, delta_C_prime = L2 - L1, C2_prime - C1_prime
    delta_H_prime = 2 * np.sqrt(C1_prime * C2_prime) * np.sin(np.radians(delta_h_prime) / 2.0)
    L_bar_prime = (L1 + L2) / 2.0
    S_L = 1 + (0.015 * (L_bar_prime - 50)**2) / np.sqrt(20 + (L_bar_prime - 50)**2)
    S_C = 1 + 0.045 * C_bar_prime
    S_H = 1 + 0.015 * C_bar_prime * T
    delta_theta = 30 * np.exp(-((h_bar_prime - 275) / 25)**2)
    R_C = 2 * np.sqrt(C_bar_prime**7 / (C_bar_prime**7 + 25**7))
    R_T = -np.sin(np.radians(2 * delta_theta)) * R_C
    return np.sqrt((delta_L_prime / S_L)**2 + (delta_C_prime / S_C)**2 + (delta_H_prime / S_H)**2 + R_T * (delta_C_prime / S_C) * (delta_H_prime / S_H))

def _ccm_objective(ccm_flat, measured_linear_rgb, reference_lab_d50):
    ccm = ccm_flat.reshape(3, 3)
    corrected_rgb = np.clip(measured_linear_rgb @ ccm.T, 0, 1)
    lab_d50 = xyz_to_lab(corrected_rgb @ rgb_to_xyz_d50.T)
    return np.mean(delta_e_cie2000(lab_d50, reference_lab_d50))

def solve_ccm(measured_patches_srgb: list[list[float]]) -> list[list[float]]:
    """Solves for a 3x3 CCM using Nelder-Mead to minimize CIE dE2000."""
    measured_rgb = np.array(measured_patches_srgb) / 255.0
    measured_linear = srgb_to_linear(measured_rgb)
    initial_ccm = np.eye(3).flatten()
    res = minimize(_ccm_objective, initial_ccm, args=(measured_linear, REFERENCE_LAB_D50), method='Nelder-Mead')
    return res.x.reshape(3, 3).tolist()
