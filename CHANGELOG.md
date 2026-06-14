# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-06-15

### Added
- **Core Engine:** Built a multiprocessing-enabled framework for evaluating image quality across CPU-bound operations.
- **Color Normalization:** Non-destructive color correction module using cv2.mcc ColorCheckers and CIE 2000 ΔE metrics.
- **Quality Analysis:** Exposure clipping detection (shadows and highlights) and HSI-based veiling glare scoring.
- **Blur Detection:** Laplacian variance grid analysis to detect out-of-focus imagery.
- **Near-Duplicates:** Sequential perceptual hashing (dhash) with dynamic temporal ordering to flag hovering drone duplicate frames.
- **Targets:** Automatic identification of ArUco and ChArUco markers, exporting subpixel coordinate detections.
- **Exporters:** Seamless CSV manifest generation, COLMAP database seeding (`database.db`), WebODM `gcp_list.txt` formatting, and Metashape `run_metashape.py` Python automation scripts.
- **Testing:** Comprehensive end-to-end `pytest` suite simulating drone flights, synthetic metadata injections, and full pipeline permutations.
