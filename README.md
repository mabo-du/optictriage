# OpticTriage

OpticTriage is an advanced pre-processing and quality control pipeline for large-scale drone photogrammetry datasets. It filters out blurry, glary, or poorly-overlapped images, extracts EXIF/RTK telemetry, detects ArUco/ChArUco/ColorChecker targets, and exports instantly ready structures for Metashape, OpenDroneMap, and COLMAP.

## Installation

### Dependencies
OpticTriage relies on several system binaries which must be installed:
- **ExifTool**: Required for writing corrected telemetry back into DJI files.
- **libexiv2**: C++ library underneath pyexiv2 for fast EXIF extraction.
- **libjpeg-turbo**: Required for PyTurboJPEG to extract embedded raw previews quickly.

Ensure these are accessible in your system `PATH`.
If using the bundled version (via PyInstaller), the appropriate ExifTool binary is included in the `bin/` directory.

### Quick Start
```bash
# Clone the repository
git clone https://github.com/your-org/optictriage.git
cd optictriage

# Install dependencies (uv recommended)
uv pip install -e .

# Run the app
python src/optictriage/app.py
```

## Workflow Tutorial
1. **Import Stage**: Select your raw image directory and an output destination. OpticTriage utilizes SHA-256 chunked hashing to instantly flag duplicate files.
2. **Metadata & RTK**: Scans DJI/Autel XMP payloads. Automatically corrects the `GPSAltitude` EXIF tag by utilizing RelativeAltitude + Base Station Elevation, directly rewriting the source file to prevent vertical bowing in SfM reconstructions. Flags any images with lost RTK Fixed states (Float/Single Point).
3. **Quality Stage**: Assesses focus/blur via a Gridded Laplacian (top 5% sharpest patches), exposure clipping, and glare estimation via true HSI color conversion. Images falling below your thresholds are flagged.
4. **Target Detection**: Runs a computer vision pipeline (LAB CLAHE equalisation, Bilateral Filtering) to locate ArUco, ChArUco, and ColorChecker targets. Corners are refined to subpixel precision (`cornerSubPix`) and serialized.
5. **Export & Finalize**: Copies images non-destructively to `passed/` and `flagged/` folders. It generates a Python script to instantly spin up Agisoft Metashape, prepares `image_groups.txt` and `cameras.json` for ODM, and scaffolds `database.db` with an exact 64-byte OPENCV parameter blob for COLMAP.

## GPU Acceleration
OpticTriage will probe your system on launch. If an Nvidia GPU with CUDA is detected (via OpenCV), it will engage a two-tier GPU path:
- **Tier 1 (Compute Heavy)**: Grayscale/LAB conversion, Laplacian filters, and CLAHE.
- **Tier 2 (Filtering)**: Bilateral Edge-Preserving noise reduction.

*Note: The first GPU call permanently reserves approximately 100MB of VRAM for the CUDA context. Please terminate OpticTriage before launching downstream pipelines like Metashape or COLMAP to fully release this VRAM back to your solver.*

## Hardware Guidance

**Minimum:**
- CPU: Intel Core i7 / AMD Ryzen 7
- RAM: 32 GB 
- GPU: Nvidia RTX 3060
- Storage: 1TB NVMe Gen3

**Recommended:**
- CPU: Intel Core i9 / AMD Ryzen 9
- RAM: 64 GB
- GPU: Nvidia RTX 4080 (Desktop or 150W+ Laptop Chassis. *Note: Thin laptop chassis variants running at 80W TGP will drastically underperform on CUDA pipelines*).
- Storage: 2TB NVMe Gen4
