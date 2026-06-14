# OpticTriage User Guide

OpticTriage is a lightweight, non-destructive diagnostic utility designed to pre-process large batches of field photographs (e.g., from drone surveys) before they enter computationally expensive Structure-from-Motion (SfM) pipelines like COLMAP, WebODM, or Agisoft Metashape.

## Features

- **Quality Screening:** Automatically detect and flag blurred, overexposed, or glare-affected images using adjustable thresholds.
- **Near-Duplicate Detection:** Prevents unnecessary SfM processing by flagging sequential near-duplicate frames caused by hovering drones.
- **Color Normalization:** Non-destructively apply ColorChecker matrix transformations based on keyframe observations.
- **Target Detection:** Export high-precision subpixel coordinates for ArUco and ChArUco markers in the field.
- **Direct SfM Exports:** Generate pre-seeded `database.db` for COLMAP, `gcp_list.txt` for WebODM, and Python scripts for one-click Agisoft Metashape ingestion.

## Installation

### Standalone Executable
You can download the pre-compiled standalone executable for your operating system (Windows, macOS, Linux) from the GitHub Releases page. No Python installation is required.

### Python Package (PyPI)
If you prefer to run OpticTriage in your own Python environment:
```bash
pip install optictriage
```

## Workflow

1. **Import:** Select a folder containing your raw or JPEG drone photographs. Choose an output destination.
2. **Settings:** Adjust quality thresholds in the UI (Blur, Exposure, Glare). Toggle specific SfM exporters (WebODM, COLMAP, Metashape).
3. **Execute:** Run the pipeline. OpticTriage will use multiprocessing to rapidly analyze imagery and extract telemetry/EXIF data.
4. **Review:** Once complete, check the export directory. 
   - Good images are soft-linked or copied into the `passed/` directory.
   - Poor quality images are isolated in the `flagged/` directory.
   - You will find a master `optictriage_manifest.csv` and specific subdirectories containing files ready for direct import into your chosen photogrammetry software.

## Integrations

- **COLMAP:** OpticTriage outputs an initialized `colmap/database.db` file. The database is pre-seeded with all cameras, EXIF focal length priors, and passed images. You can immediately launch COLMAP and proceed to Feature Extraction without importing files manually.
- **WebODM:** OpticTriage outputs an `odm/gcp_list.txt` file containing the precise subpixel coordinate matches for any detected ArUco/ChArUco targets.
- **Metashape:** Run the `metashape/run_metashape.py` file from within the Agisoft Metashape application via `Tools -> Run Script` to automatically create a chunk, import photos, set the coordinate system (WGS84), and bind GCP markers.
