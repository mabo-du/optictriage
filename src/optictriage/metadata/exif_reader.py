"""exif_reader.py — Extracts EXIF and XMP with pyexiv2 and binary fallback.
exports: extract_metadata(filepath: str) -> dict
used_by: stages/exif_stage.py → ExifStage
rules:
Must implement binary extraction fallback if pyexiv2 fails or omits tags.
"""

import pyexiv2
import re
from typing import Dict, Any

def _extract_binary_xmp(filepath: str) -> Dict[str, str]:
    """
    Fallback method to extract XMP metadata directly from the binary file.
    Useful when pyexiv2 fails on malformed manufacturer namespaces.
    """
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
            
        # Search for xmpmeta block
        start_tag = b'<x:xmpmeta'
        end_tag = b'</x:xmpmeta>'
        
        start_idx = data.find(start_tag)
        if start_idx == -1:
            return {}
            
        end_idx = data.find(end_tag, start_idx)
        if end_idx == -1:
            return {}
            
        xmp_block = data[start_idx:end_idx + len(end_tag)].decode('utf-8', errors='ignore')
        
        # Extremely rudimentary parsing of common tags out of the raw XML.
        # We look for simple patterns like `drone-dji:RelativeAltitude="+120.00"`
        # or `<drone-dji:RelativeAltitude>+120.00</drone-dji:RelativeAltitude>`
        
        parsed_xmp = {}
        
        # Pattern 1: attribute style `prefix:Tag="Value"`
        attr_pattern = re.compile(r'([a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+)="([^"]+)"')
        for match in attr_pattern.finditer(xmp_block):
            parsed_xmp[match.group(1)] = match.group(2)
            
        # Pattern 2: element style `<prefix:Tag>Value</prefix:Tag>`
        elem_pattern = re.compile(r'<([a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+)>([^<]+)</\1>')
        for match in elem_pattern.finditer(xmp_block):
            parsed_xmp[match.group(1)] = match.group(2)
            
        return parsed_xmp
    except Exception:
        return {}


def extract_metadata(filepath: str) -> Dict[str, Any]:
    """
    Extracts all metadata (EXIF/XMP) using pyexiv2.
    If XMP is empty or lacks expected drone tags, supplements with binary fallback.
    """
    metadata = {"exif": {}, "xmp": {}}
    
    try:
        with pyexiv2.Image(filepath) as img:
            metadata["exif"] = img.read_exif() or {}
            metadata["xmp"] = img.read_xmp() or {}
    except Exception:
        # pyexiv2 failed entirely (corrupt header etc), fallback to pure binary XMP
        pass
        
    # Check if we got the expected DJI/Autel namespaces.
    # If not, supplement with binary extraction.
    has_dji = any(k.startswith('Xmp.drone-dji:') for k in metadata["xmp"].keys())
    has_autel = any(k.startswith('Xmp.drone:') for k in metadata["xmp"].keys())
    
    if not (has_dji or has_autel):
        binary_xmp = _extract_binary_xmp(filepath)
        # Prefix with Xmp. to match pyexiv2 output format
        for k, v in binary_xmp.items():
            prefixed_key = f"Xmp.{k}"
            if prefixed_key not in metadata["xmp"]:
                metadata["xmp"][prefixed_key] = v
                
    return metadata
