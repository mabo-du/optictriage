# Product Requirements Document (PRD): Automated Photogrammetry Pre-Processor

## 1. Product Vision & Strategy

**The Problem:** Managing thousands of field photographs before processing them in 3D photogrammetry software (like Agisoft Metashape or OpenDroneMap) is chaotic and time-consuming. Blurry photos, missing metadata, and misidentified ground targets can cause expensive, mathematically complex 3D reconstructions to fail catastrophically.

**The Solution:** A lightweight desktop utility that acts as an "assembly line" for field data. It imports batches of photos, evaluates their health, extracts critical data, and outputs a perfectly organized package of files that 3D software can seamlessly swallow.

**Naming Strategy:**
To capture a wide audience while maintaining a professional tone, we will test a shortlist of three names with actual users to see which resonates best:

* **OpticTriage:** Best conceptual fit for the diagnostic, non-destructive philosophy.


* **PhotoPrep Pro:** Best for immediate clarity and broad, professional appeal.


* **TrenchLens:** Best for targeted marketing specifically to archaeologists.



---

## 2. Core Operating Principles

To keep this tool fast, safe, and reliable, the architecture will adhere to four strict rules:

1. **Sequential Processing:** The app operates as an assembly line: Import -> EXIF Extract -> Quality Score -> Target Detect -> Organize -> Export. Each stage is independent.


2. **Warnings, Not Deletions:** The app will never automatically delete a user's file. It provides non-destructive diagnostics (health scores) and flags problematic images for human review.


3. **Speed via Previews:** Decoding massive RAW sensor data takes too long. The app will extract the embedded, pre-processed JPEG previews hidden inside RAW files to perform all quality checks and target detection lightning-fast.


4. **Precision Over Recall:** When detecting ground targets, the app must prioritize certainty. A false positive (e.g., mistaking a rock for a target) will ruin a 3D model. If the app isn't absolutely sure it found a target, it will ignore it.



---

## 3. MVP Scope (Version 1.0)

To prevent scope creep, the first version of this app will firmly push back against over-engineering. We will avoid complex internal databases, simultaneous multiprocessing, and microscopic subpixel math until the core foundation is proven to work smoothly.

### Feature 1: Import & Pre-flight Checks

* **Supported Formats:** JPG, TIFF, and common RAW files (CR2, NEF, ARW, DNG).


* **Fast Extraction:** Use `rawpy` and `ExifTool` to instantly rip embedded JPEGs from RAW files.


* **Basic QA:** Calculate checksums (digital fingerprints) to flag exact duplicate files, and verify all images share the same dimensions (width/height) to prevent software crashes.



### Feature 2: Interactive Quality Triage

* **Smart Blur Detection:** The app will chop images into grids and calculate the variance of the Laplacian (sharpness) on the sharpest 5% of the image to avoid flagging photos with intentional background blur.


* **User-Controlled Thresholds:** Instead of hardcoded blur limits, the app will generate an interactive histogram. The user can drag a slider to dictate what constitutes "too blurry" for their specific project.


* **Exposure & Overlap:** Flag images with severe clipped highlights (sun glare) and use GPS data to warn if drone photos have less than 60-75% geographical overlap.



### Feature 3: Robust Target Detection

* **Image Enhancement:** Apply Contrast-Limited Adaptive Histogram Equalization (CLAHE) to the images before scanning to reveal targets hiding in deep shadows or mud.


* **Supported Targets:** Focus on detecting ArUco markers and ChArUco boards, which possess high occlusion resilience and built-in error correction.


* **Color Checkers:** The app will detect X-Rite ColorCheckers and simply flag the photo for the user. We will strictly avoid automatically batch-correcting colors in Version 1 to prevent unnatural color shifts across shifting lighting conditions.



### Feature 4: Metadata Standardization

* **The Drone Altitude Fix:** Consumer drones (like DJI) record inaccurate "Sea Level" altitude in standard EXIF tags, but hide accurate "Takeoff" altitude in XMP tags.


* **Safe Injection:** Using a background process of `pyexiftool`, the app will safely overwrite the flawed `GPSAltitude` with the highly precise `RelativeAltitude` to prevent the final 3D model from curving or "bowing" vertically.



### Feature 5: Exporting & Manifests

The tool will not use a universal export file. Instead, it will output "ready-to-import packages" tailored to specific software platforms.

* **Master Manifest:** A highly detailed CSV file logging every photo's filename, EXIF data, health scores, and detected targets.


* **OpenDroneMap (ODM):** Automatically generate the required `gcp_list.txt` (ground control points) and `cameras.json` (intrinsic camera lens settings) files.


* **Agisoft Metashape:** Generate a `.py` (Python) script that the user can run inside Metashape to automatically set up their project, load the photos, and pin the targets, bypassing the need to hack Metashape's proprietary project files.


* **COLMAP:** Generate the required `images.txt` and `cameras.txt` files.



---

## 4. Technical Stack

* **Language:** Python.


* **User Interface:** PyQt6 or Tauri+React for a simple, workflow-style desktop interface.


* **Computer Vision:** OpenCV (for target detection, CLAHE, and blur analysis).


* **Metadata Management:** `pyexiftool` (safest for rewriting delicate RAW/TIFF headers without corrupting them).


* **Image Processing:** `Pillow` and `rawpy` (for fast thumbnail extraction).



---

## 5. Future Roadmap (Version 2.0+)

Once the simple assembly line of Version 1 is stable and field-tested, development will pivot to more advanced, computationally heavy features:

* **Database Infrastructure:** Replace the simple CSV manifest system with a robust local SQLite database to allow for complex session saving and partial pipeline re-runs.


* **Multiprocessing:** Implement Python multiprocessing to handle several photos simultaneously, speeding up the workflow for massive drone datasets.


* **Subpixel Refinement:** Implement OpenCV's `cornerSubPix` algorithms to achieve sub-millimeter accuracy on ground targets.


* **Automated Color Normalization:** Build a full color correction pipeline using the detected ColorChecker data to normalize lighting across the entire dataset.


* **Camera Grouping:** Automatically separate photo sets by time gaps or drastic GPS changes.
