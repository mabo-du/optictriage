"""models.py — SQLAlchemy ORM models for OpticTriage sessions and images.
exports: Session, ImageRecord
used_by: database.py → init_db, pipeline.py → orchestrator
rules:
Must use SQLAlchemy 2.0 declarative base.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator, VARCHAR

Base = declarative_base()


class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string."""

    impl = VARCHAR
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class Session(Base):
    __tablename__ = "session"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    input_folder: Mapped[str] = mapped_column(String, nullable=False)
    output_folder: Mapped[str] = mapped_column(String, nullable=False)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONEncodedDict, nullable=True)
    state: Mapped[str] = mapped_column(String, default="idle")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    images: Mapped[List["ImageRecord"]] = relationship(
        "ImageRecord", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, state='{self.state}')>"


class ImageRecord(Base):
    __tablename__ = "image_record"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("session.id"), nullable=False)
    
    original_path: Mapped[str] = mapped_column(String, nullable=False)
    output_filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # EXIF
    camera_make: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    camera_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    focal_length_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    aperture: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    iso: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    shutter_speed: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    gps_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gps_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gps_alt: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relative_alt: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capture_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Quality scores
    blur_score: Mapped[Optional[float]] = mapped_column(Float, default=-1.0)
    exposure_clipped_pct: Mapped[Optional[float]] = mapped_column(Float, default=-1.0)
    glare_score: Mapped[Optional[float]] = mapped_column(Float, default=-1.0)
    is_flagged: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    flag_reasons: Mapped[Optional[List[str]]] = mapped_column(JSONEncodedDict, nullable=True)

    # Target detection
    detected_targets: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONEncodedDict, nullable=True)
    colour_target_detected: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    
    # Segmentation
    camera_group_idx: Mapped[Optional[int]] = mapped_column(Integer, default=1)

    # Color Normalization
    color_patches: Mapped[Optional[List[List[float]]]] = mapped_column(JSONEncodedDict, nullable=True)
    ccm_matrix: Mapped[Optional[List[List[float]]]] = mapped_column(JSONEncodedDict, nullable=True)
    ccm_applied: Mapped[Optional[bool]] = mapped_column(Integer, default=0)
    ccm_keyframe_id: Mapped[Optional[int]] = mapped_column(ForeignKey("image_record.id"), nullable=True)

    # State
    processing_state: Mapped[str] = mapped_column(String, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="images")

    __table_args__ = (
        Index("idx_image_session", "session_id"),
        Index("idx_image_state", "session_id", "processing_state"),
    )

    def __repr__(self) -> str:
        return f"<ImageRecord(id={self.id}, processing_state='{self.processing_state}')>"
