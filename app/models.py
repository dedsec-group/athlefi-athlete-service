"""Database models for the athlete service."""

from datetime import date, datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from enum import Enum

Base = declarative_base()


class Athlete(Base):
    """Represents an athlete with personal and sports information."""
    __tablename__ = "athlete"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    country = Column(String, index=True)
    birth_date = Column(Date, index=True)
    height = Column(Integer, index=True)
    weight = Column(Integer, index=True)
    sport = Column(String, index=True)
    nick_name = Column(String, index=True)
    bio = Column(Text, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)

    # Relationship with files
    files = relationship("MediaFile", back_populates="athlete")


class MediaFile(Base):
    """Represents a media file stored in Cloudflare R2."""
    __tablename__ = "media_file"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False, index=True)  # image or video
    mime_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_key = Column(String, nullable=False, unique=True, index=True)  # R2 object key
    public_url = Column(String, nullable=True)  # CDN URL if available
    is_public = Column(Boolean, default=False, index=True)
    width = Column(Integer, nullable=True)  # For images/videos
    height = Column(Integer, nullable=True)  # For images/videos
    duration = Column(Integer, nullable=True)  # For videos (in seconds)
    
    # Relationships
    athlete_id = Column(Integer, ForeignKey("athlete.id"), nullable=True, index=True)
    athlete = relationship("Athlete", back_populates="files")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True, index=True)


# Pydantic Enums
class FileType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class MediaFileStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Pydantic models for API
class AthleteBase(BaseModel):
    """Base class for all athletes."""
    # Personal Data
    name: str
    country: str
    birth_date: date
    height: int
    weight: int

    # Career Data
    sport: str
    nick_name: str
    bio: str

    class Config:
        from_attributes = True


class AthletePublic(AthleteBase):
    """Represents an athlete with public information."""
    id: int
    name: str
    country: str
    sport: str
    birth_date: date
    created_at: datetime
    updated_at: datetime


class AthleteCreate(AthleteBase):
    """Represents an athlete to be created."""
    pass


class AthleteUpdate(BaseModel):
    """Represents an athlete to be updated."""
    name: Optional[str] = None
    country: Optional[str] = None
    birth_date: Optional[date] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    sport: Optional[str] = None
    nick_name: Optional[str] = None
    bio: Optional[str] = None


# Media File Pydantic Models
class MediaFileBase(BaseModel):
    """Base model for media files."""
    filename: str
    original_filename: str
    file_type: FileType
    mime_type: str
    file_size: int
    is_public: bool = False
    athlete_id: Optional[int] = None

    class Config:
        from_attributes = True


class MediaFilePublic(MediaFileBase):
    """Public representation of a media file."""
    id: int
    file_key: str
    public_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class MediaFileCreate(BaseModel):
    """Model for creating a media file."""
    original_filename: str
    file_type: FileType
    is_public: bool = False
    athlete_id: Optional[int] = None


class MediaFileUpdate(BaseModel):
    """Model for updating a media file."""
    filename: Optional[str] = None
    is_public: Optional[bool] = None
    athlete_id: Optional[int] = None


class UploadResponse(BaseModel):
    """Response model for file upload."""
    file_id: int
    filename: str
    file_key: str
    upload_url: str
    public_url: Optional[str] = None
    expires_in: int


class PresignedUrlResponse(BaseModel):
    """Response model for presigned URL generation."""
    url: str
    expires_in: int
    file_key: str
