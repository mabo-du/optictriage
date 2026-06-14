import pytest
import numpy as np
import os
import cv2

from optictriage.vision.colorchecker import (
    srgb_to_linear, 
    linear_to_srgb, 
    solve_ccm, 
    REFERENCE_LAB_D50, 
    _ccm_objective
)
from optictriage.stages.color_stage import ColorStage
from optictriage.models import Session, ImageRecord, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_srgb_linearization_reversible():
    """Assert that gamma decoding and encoding are lossless inverses."""
    rgb = np.random.rand(100, 3)
    linear = srgb_to_linear(rgb)
    rgb_back = linear_to_srgb(linear)
    assert np.allclose(rgb, rgb_back, atol=1e-5)

def lab_to_xyz(lab):
    Xn, Yn, Zn = 0.96422, 1.00000, 0.82521
    L, a, b = lab[:, 0], lab[:, 1], lab[:, 2]
    
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200
    
    delta = 6/29
    def inv_f(t):
        return np.where(t > delta, t**3, 3 * delta**2 * (t - 4/29))
        
    return np.column_stack((inv_f(fx) * Xn, inv_f(fy) * Yn, inv_f(fz) * Zn))

def test_ccm_reduces_error():
    """Assert that Nelder-Mead optimization successfully minimizes dE2000 on a linear cast."""
    from optictriage.vision.colorchecker import rgb_to_xyz_d50
    
    # 1. Generate perfect linear RGB patches from REFERENCE_LAB_D50
    perfect_xyz_d50 = lab_to_xyz(REFERENCE_LAB_D50)
    perfect_linear_rgb = perfect_xyz_d50 @ np.linalg.inv(rgb_to_xyz_d50.T)
    perfect_linear_rgb = np.clip(perfect_linear_rgb, 0, 1)
    
    # 2. Apply a known linear cast (e.g. Red * 0.85, Blue * 1.10)
    cast_linear_rgb = perfect_linear_rgb * np.array([0.85, 1.0, 1.10])
    cast_linear_rgb = np.clip(cast_linear_rgb, 0, 1)
    
    # 3. Encode to sRGB as expected by solve_ccm
    cast_srgb = linear_to_srgb(cast_linear_rgb)
    measured_patches_srgb = (cast_srgb * 255.0).astype(int).tolist()
    
    # Calculate initial error
    initial_dE = _ccm_objective(np.eye(3).flatten(), cast_linear_rgb, REFERENCE_LAB_D50)
    
    # Solve CCM
    ccm = solve_ccm(measured_patches_srgb)
    final_dE = _ccm_objective(np.array(ccm).flatten(), cast_linear_rgb, REFERENCE_LAB_D50)
    
    assert final_dE < initial_dE, f"CCM failed to reduce dE: initial {initial_dE}, final {final_dE}"
    assert final_dE < 2.0, f"CCM failed to achieve acceptable error. Final dE2000 = {final_dE}"

def test_color_stage_non_destructive_and_tiff(tmp_path):
    """
    Assert that the ColorStage:
    1. Writes corrected images to the colour_corrected folder.
    2. Does not overwrite the original source files.
    3. Outputs lossless TIFF by default.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    DBSession = sessionmaker(bind=engine)
    db = DBSession()

    export_dir = str(tmp_path / "export")
    session = Session(input_folder="dummy", output_folder=export_dir)
    db.add(session)
    db.commit()

    # Create dummy source image
    img_path = str(tmp_path / "test.jpg")
    cv2.imwrite(img_path, np.zeros((100, 100, 3), dtype=np.uint8))
    
    # Create keyframe record
    record = ImageRecord(
        session_id=session.id,
        original_path=img_path,
        camera_group_idx=1,
        colour_target_detected=1,
        # Fake patches
        color_patches=np.random.randint(50, 200, (24, 3)).tolist()
    )
    db.add(record)
    db.commit()

    # Run stage
    class MockDBManager:
        def get_session(self):
            class Ctx:
                def __enter__(self): return db
                def __exit__(self, *args): pass
            return Ctx()

    stage = ColorStage(session.id, MockDBManager())
    list(stage.run())

    # Assertions
    out_dir = os.path.join(export_dir, "colour_corrected")
    assert os.path.exists(out_dir), "colour_corrected directory not created"
    
    out_files = os.listdir(out_dir)
    assert len(out_files) == 1, "Expected exactly 1 output file"
    assert out_files[0] == "test.tiff", "Output should default to lossless TIFF format"
    
    assert os.path.exists(img_path), "Original source file was destructively overwritten"
    
    db.refresh(record)
    assert record.ccm_applied == True, "Database record was not updated with ccm_applied=True"
