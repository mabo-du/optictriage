"""metashape.py — Metashape Python script generator.
exports: generate_metashape_script
used_by: stages/export_stage.py → ExportStage
rules:
Use Metashape.app.document API to ingest photos, set CRS, and import GCP CSV.
"""

import os
from optictriage.models import ImageRecord

def generate_metashape_script(records: list[ImageRecord], output_dir: str, gcp_csv_path: str = None):
    """
    Generates a Python script that can be executed within Agisoft Metashape 
    to instantiate a project and ingest the passed photos.
    """
    
    # We only want to import passed (unflagged) images
    passed_images = [r.output_filename for r in records if not r.is_flagged and r.output_filename]
    
    # Format list for Python script output
    photos_list_str = "[\n"
    for filename in passed_images:
        photos_list_str += f"    os.path.join(PASSED_DIR, '{filename}'),\n"
    photos_list_str += "]"
    
    gcp_import_code = ""
    if gcp_csv_path:
        gcp_csv_basename = os.path.basename(gcp_csv_path)
        gcp_import_code = f"""
    # Import GCPs
    gcp_path = os.path.join(BASE_DIR, '{gcp_csv_basename}')
    if os.path.exists(gcp_path):
        chunk.importReference(gcp_path, format=Metashape.ReferenceFormatCSV, columns='nxyz', delimiter=',')
"""

    script_content = f"""# OpticTriage Metashape Import Script
# Run this script from within Agisoft Metashape (Tools -> Run Script)

import Metashape
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASSED_DIR = os.path.join(BASE_DIR, 'passed')

def main():
    doc = Metashape.app.document
    chunk = doc.addChunk()
    chunk.label = "OpticTriage Import"
    
    photos = {photos_list_str}
    
    # Add photos
    chunk.addPhotos(photos)
    
    # Set CRS (WGS84)
    crs = Metashape.CoordinateSystem("EPSG::4326")
    chunk.crs = crs
    {gcp_import_code}
    
    print("OpticTriage: Successfully imported " + str(len(photos)) + " photos.")

if __name__ == "__main__":
    main()
"""
    
    out_path = os.path.join(output_dir, "run_metashape.py")
    with open(out_path, "w") as f:
        f.write(script_content)
    
    return out_path
