# PROJECT 20 — Automated Photogrammetry Pre-Processor
## Overview

A lightweight utility that pre-processes batches of photographs before they are fed into photogrammetry software (Agisoft Metashape, OpenDroneMap, COLMAP). Managing thousands of photos before processing is chaotic — scale targets need to be detected and measured, images need quality filtering, EXIF metadata needs standardising, and camera calibration data needs extracting. This tool automates that pre-processing pipeline and produces a clean, organised input folder with a manifest file, saving significant time at the start of every photogrammetry project.

## Target users

- Archaeologists running photogrammetry for site and artefact documentation
- Palaeontologists digitising fossil specimens
- Heritage documentation professionals
- Drone survey operators preparing UAV photo sets for processing
- Museum collections digitisation teams

## MVP scope (v1)

- Import a folder of images (JPG, TIFF, RAW)
- EXIF metadata extraction and display: camera model, focal length, GPS coordinates, capture time
- Image quality filtering: flag blurry images (Laplacian variance), flag overexposed/underexposed images
- Scale bar / coded target detection: detect Agisoft-compatible coded targets (CircleCV and ChArUco markers) in images
- Colour target detection: detect X-Rite ColorChecker or similar for colour normalisation
- Export: renamed and organised photo set with a CSV manifest (filename, EXIF data, quality scores, detected targets)
- Camera calibration data extraction from EXIF for common cameras

## Feature roadmap (v2+)

- Automatic camera group detection: separate photo groups by camera angle, altitude, or time gap (for multi-camera or multi-pass surveys)
- Colour normalisation pipeline: apply colour correction from detected reference chart
- GPS track import (.gpx) and alignment with image timestamps for UAV surveys
- OpenDroneMap project file generator
- Agisoft Metashape project XML generator (pre-populated with detected markers and camera groups)
- Duplicate detection: flag near-identical images (insufficient baseline for stereo reconstruction)
- RAW format support via rawpy
- GCP (Ground Control Point) file generator in Metashape and ODM formats from GPS measurements

## Tech stack recommendation

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python | OpenCV, rawpy, piexif, Pillow all available |
| GUI | PyQt6 or Tauri+React | Simple workflow-style UI |
| Computer vision | OpenCV | Target detection, blur detection, exposure analysis |
| EXIF | piexif + ExifTool (subprocess) | piexif for read, ExifTool for comprehensive write |
| Image preview | Pillow | Fast thumbnail generation |
| Data output | Pandas → CSV | Manifest file |
| Packaging | PyInstaller | |

## Architecture notes

- Model the pipeline as a **sequential processing graph**: Import → EXIF Extract → Quality Score → Target Detect → Organise → Export. Each stage is independent and can be run/re-run individually.
- **Blur detection** using Laplacian variance is fast and effective: compute `cv2.Laplacian(gray_image, cv2.CV_64F).var()`. Low variance = blurry. Threshold is camera/lens dependent — allow the user to set it based on a histogram of scores across the set.
- **Coded target detection** uses OpenCV's ArUco module for ChArUco and custom circular target detection for Agisoft targets. This is a well-solved problem in the OpenCV ecosystem.
- Process images in **background threads** with a progress queue. Thousands of images must be processed efficiently. Use Python multiprocessing for CPU-bound operations (blur detection, target detection).
- The **output manifest CSV** should be designed to be directly importable by Agisoft Metashape via its CSV import feature and by ODM's argument format. Study both tools' documented input formats.

## Core data model

```
Session
  id, input_folder, output_folder, created_at, settings (JSON)

ImageRecord
  id, session_id, original_path, output_path
  camera_make, camera_model, focal_length_mm, aperture, iso, shutter_speed
  gps_lat, gps_lon, gps_alt, capture_time
  blur_score, exposure_score, is_flagged, flag_reason
  detected_targets (JSON list of {target_id, x, y, size})
  colour_target_detected (bool)

ProcessingManifest (output)
  session_id, image_records, summary_stats, created_at
```

## Existing resources to leverage

- **OpenCV ArUco module** — coded target detection: `cv2.aruco`
- **piexif** — Python EXIF library: https://github.com/hMatoba/Piexif
- **ExifTool** — comprehensive EXIF tool by Phil Harvey: https://exiftool.org
- **OpenDroneMap** — study its input format: https://github.com/OpenDroneMap/ODM
- **Agisoft Metashape Python API** — for generating project files: https://agisoft.freshdesk.com/support/solutions/articles/31000148855
- **rawpy** — RAW image processing in Python: https://github.com/letmaik/rawpy

## Technical risks

- **Coded target diversity** — multiple competing coded target systems exist (ArUco, April Tag, Agisoft proprietary). Support the most common ones (ArUco Dict 4×4 and 6×6, ChArUco) and document limitations.
- **RAW format support** — camera RAW formats are extremely diverse (CR2, CR3, ARW, NEF, DNG). rawpy handles most via LibRaw but unusual camera models may fail. Test with common cameras used in fieldwork.
- **Colour correction complexity** — full colour profile correction (X-Rite colour science) is complex. In v1, simply detect the target and flag the image; defer actual colour correction to v2.

---

## Deep Research Prompt — Project 20

> I am building a photogrammetry pre-processing utility for archaeologists and palaeontologists. I need research:
>
> 1. **Photogrammetry input requirements**: What pre-processing steps do Agisoft Metashape, OpenDroneMap (ODM), and COLMAP each require or benefit from? What are their documented input formats for camera calibration data, GCP files, and coded target information? How should images be named and organised for optimal processing?
>
> 2. **Coded photogrammetry targets**: What types of coded targets are used in archaeological photogrammetry? Cover: Agisoft Metashape circular coded targets, ArUco markers, ChArUco boards, and April Tags. For each: what is the detection algorithm, what OpenCV module handles it, and what output format does Metashape/ODM expect for target positions?
>
> 3. **Image quality metrics for photogrammetry**: What image quality metrics are most relevant for photogrammetry input selection? Cover: blur/sharpness metrics (Laplacian variance, FFT-based), exposure analysis (histogram statistics), and overlap analysis (GPS-based coverage estimation for UAV datasets). What threshold values are commonly used?
>
> 4. **EXIF metadata standards**: What EXIF and XMP metadata tags are most important for photogrammetry? What Python libraries read and write EXIF reliably across JPEG, TIFF, and RAW formats? What metadata does Metashape read automatically from EXIF? How is GPS altitude encoding handled (relative vs absolute)?
>
> 5. **Colour calibration targets**: What colour calibration targets are used in archaeological photography (X-Rite ColorChecker, SpyderCHECKR, custom grey cards)? How are they detected in images using OpenCV? What colour correction transforms are applied once a target is detected?
>
> 6. **OpenDroneMap input format**: What is the complete documented input specification for OpenDroneMap? What is the format of GCP files (.txt), camera calibration files, and image EXIF requirements for GPS-tagged UAV surveys?

---

# Appendix A — Recommended Build Order

The following order balances impact, technical complexity, and the ability to reuse components across projects:

| Phase | Projects | Rationale |
|---|---|---|
| **Phase 1 — High impact, well-scoped** | #3 Harris Matrix, #19 LiDAR QGIS Plugin, #20 Photo Pre-processor | Relatively contained, large user base, builds familiarity with the domain |
| **Phase 2 — Core productivity tools** | #9 Field Database, #2 Stratigraphic Plotter, #1 QDA App | Foundational tools used daily; larger scope but clear requirements |
| **Phase 3 — Specialist tools** | #4 Osteometric Sorting, #7 Lithic Analyzer, #16 Bio Profile Estimator | Domain-specific, moderate complexity, reuse Python/Qt stack from Phase 2 |
| **Phase 4 — AI-assisted tools** | #10 Ceramic Classifier, #11 Grey Literature NLP, #5 ZooMS Viewer | Require ML components; Phase 3 experience with domain helps scoping |
| **Phase 5 — Complex infrastructure** | #12 CT Segmentation, #15 aDNA Dashboard, #13 QField Sync | Most technically demanding; benefit from all prior experience |
| **Phase 6 — Finishing the set** | #6 CRM Forms, #8 3D Educator, #14 Isotopic Mapping, #17 Mesh Tool, #18 Ceramic Profile | Round out the toolkit; some reuse components from earlier phases |

---

# Appendix B — Shared Tech Stack Reference

Several technology choices recur across projects. Master these once:

| Technology | Used In | Notes |
|---|---|---|
| Python + PyQt6 | #4, #5, #7, #12, #16, #17, #18 | Core desktop app stack for scientific Python |
| Tauri + React | #2, #9, #14 | Lighter cross-platform desktop alternative to Electron |
| Electron + React | #1, #3, #15 | When Node.js ecosystem is needed |
| SQLite | Almost all | Local project storage; learn it well |
| Open3D + trimesh | #7, #12, #17, #18 | 3D mesh processing in Python |
| PyTorch + ONNX | #10, #12 | ML training and deployment |
| QGIS Plugin API | #19 | Python-based, good documentation |
| D3.js | #2, #3, #15 | Complex custom visualisations |
| spaCy | #11 | NLP pipeline |
| FastAPI | #10, #11 | Lightweight Python API layer |

---

# Appendix C — Open Data Sources

| Resource | Relevant Projects | URL |
|---|---|---|
| Neotoma Paleoecology Database | #2, #14 | https://neotomadb.org |
| Morphosource (3D models) | #7, #8, #12 | https://www.morphosource.org |
| Smithsonian 3D | #8 | https://3d.si.edu |
| ADS Grey Literature Library | #11 | https://archaeologydataservice.ac.uk |
| GBIF Species API | #14 | https://www.gbif.org/developer |
| PeriodO | #9, #14 | https://perio.do |
| Getty AAT | #9, #11 | https://vocab.getty.edu/aat |
| open-archaeo directory | All | https://open-archaeo.info |
| Zooarchaeology by MS markers | #5 | Published in Buckley et al. papers |
| California OHP DPR 523 forms | #6 | https://ohp.parks.ca.gov |

---

*Document compiled May 2026. Check open-archaeo.info regularly for new projects in these spaces — the community is active.*
