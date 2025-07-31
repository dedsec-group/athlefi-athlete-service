"""File Management API Router.

This router provides endpoints for:
- File upload (with presigned URLs)
- File download and streaming
- File metadata management
- File deletion and cleanup
"""

import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
import logging

from app.config import SessionDep, PRESIGNED_URL_EXPIRY
from app.models import (
    MediaFile, MediaFileCreate, MediaFilePublic, MediaFileUpdate,
    UploadResponse, PresignedUrlResponse, FileType
)
from app.services.r2_service import r2_service, R2StorageError
from app.services.file_validation import file_validator, FileValidationError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/files",
    tags=["files"],
)


# Upload Endpoints
@router.post("/upload/presigned", response_model=UploadResponse)
async def create_presigned_upload_url(
    original_filename: str = Form(...),
    file_type: FileType = Form(...),
    is_public: bool = Form(False),
    athlete_id: Optional[int] = Form(None),
    session: SessionDep = Depends()
):
    """Generate a presigned URL for file upload.
    
    This endpoint creates a database record and returns a presigned URL
    that clients can use to upload files directly to R2.
    """
    try:
        # Generate unique file key
        file_key = r2_service.generate_file_key(original_filename, athlete_id)
        
        # Determine content type based on file extension and type
        file_ext = original_filename.split('.')[-1].lower() if '.' in original_filename else ''
        content_type_map = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp',
            'mp4': 'video/mp4', 'avi': 'video/avi', 'mov': 'video/mov',
            'wmv': 'video/wmv', 'webm': 'video/webm'
        }
        content_type = content_type_map.get(file_ext, 'application/octet-stream')
        
        # Generate presigned upload URL
        upload_url = await r2_service.generate_presigned_upload_url(
            file_key, content_type, PRESIGNED_URL_EXPIRY
        )
        
        # Create database record
        db_file = MediaFile(
            filename=f"{original_filename.split('.')[0]}_{file_key.split('/')[-1]}",
            original_filename=original_filename,
            file_type=file_type.value,
            mime_type=content_type,
            file_size=0,  # Will be updated after upload
            file_key=file_key,
            is_public=is_public,
            athlete_id=athlete_id,
            public_url=r2_service.get_public_url(file_key) if is_public else None
        )
        
        session.add(db_file)
        await session.commit()
        await session.refresh(db_file)
        
        return UploadResponse(
            file_id=db_file.id,
            filename=db_file.filename,
            file_key=file_key,
            upload_url=upload_url,
            public_url=db_file.public_url,
            expires_in=PRESIGNED_URL_EXPIRY
        )
        
    except R2StorageError as e:
        logger.error(f"R2 storage error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in presigned upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/upload/direct", response_model=MediaFilePublic)
async def upload_file_direct(
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    is_public: bool = Form(False),
    athlete_id: Optional[int] = Form(None),
    session: SessionDep = Depends(),
    background_tasks: BackgroundTasks = None
):
    """Upload a file directly through the API server.
    
    This endpoint handles file upload through the server, validates the file,
    and uploads it to R2. Use this for smaller files or when client-side
    upload is not feasible.
    """
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate file
        detected_mime, metadata = file_validator.validate_file(
            file_content, file.filename, file_type.value
        )
        
        # Generate unique file key
        file_key = r2_service.generate_file_key(file.filename, athlete_id)
        
        # Upload to R2
        success = await r2_service.upload_file(
            file_key, file_content, detected_mime
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        
        # Create database record
        db_file = MediaFile(
            filename=f"{file.filename.split('.')[0]}_{file_key.split('/')[-1]}",
            original_filename=file.filename,
            file_type=file_type.value,
            mime_type=detected_mime,
            file_size=len(file_content),
            file_key=file_key,
            is_public=is_public,
            athlete_id=athlete_id,
            public_url=r2_service.get_public_url(file_key) if is_public else None,
            width=metadata.get('width'),
            height=metadata.get('height'),
            duration=metadata.get('duration')
        )
        
        session.add(db_file)
        await session.commit()
        await session.refresh(db_file)
        
        logger.info(f"Successfully uploaded file: {file.filename} as {file_key}")
        return db_file
        
    except FileValidationError as e:
        logger.error(f"File validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except R2StorageError as e:
        logger.error(f"R2 storage error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in direct upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Download and Streaming Endpoints
@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    session: SessionDep = Depends()
):
    """Download a file or redirect to presigned URL.
    
    For public files, this may redirect to the public URL.
    For private files, this generates a presigned download URL.
    """
    try:
        # Get file record
        statement = select(MediaFile).where(
            and_(MediaFile.id == file_id, MediaFile.deleted_at.is_(None))
        )
        result = await session.execute(statement)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # For public files with public domain, redirect directly
        if db_file.is_public and db_file.public_url:
            return RedirectResponse(url=db_file.public_url)
        
        # Generate presigned download URL
        download_url = await r2_service.generate_presigned_download_url(db_file.file_key)
        return RedirectResponse(url=download_url)
        
    except R2StorageError as e:
        logger.error(f"R2 storage error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in download: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{file_id}/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_download_url(
    file_id: int,
    expires_in: int = Query(PRESIGNED_URL_EXPIRY, le=86400),  # Max 24 hours
    session: SessionDep = Depends()
):
    """Get a presigned download URL for a file.
    
    This is useful for client applications that need to handle
    the download URL themselves.
    """
    try:
        # Get file record
        statement = select(MediaFile).where(
            and_(MediaFile.id == file_id, MediaFile.deleted_at.is_(None))
        )
        result = await session.execute(statement)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Generate presigned download URL
        download_url = await r2_service.generate_presigned_download_url(
            db_file.file_key, expires_in
        )
        
        return PresignedUrlResponse(
            url=download_url,
            expires_in=expires_in,
            file_key=db_file.file_key
        )
        
    except R2StorageError as e:
        logger.error(f"R2 storage error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in presigned URL generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# File Management Endpoints
@router.get("/", response_model=List[MediaFilePublic])
async def list_files(
    athlete_id: Optional[int] = Query(None),
    file_type: Optional[FileType] = Query(None),
    is_public: Optional[bool] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: SessionDep = Depends()
):
    """List files with optional filtering."""
    try:
        # Build query
        conditions = [MediaFile.deleted_at.is_(None)]
        
        if athlete_id is not None:
            conditions.append(MediaFile.athlete_id == athlete_id)
        if file_type is not None:
            conditions.append(MediaFile.file_type == file_type.value)
        if is_public is not None:
            conditions.append(MediaFile.is_public == is_public)
        
        statement = select(MediaFile).where(and_(*conditions)).offset(offset).limit(limit)
        result = await session.execute(statement)
        files = result.scalars().all()
        
        return files
        
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{file_id}", response_model=MediaFilePublic)
async def get_file(
    file_id: int,
    session: SessionDep = Depends()
):
    """Get file metadata by ID."""
    try:
        statement = select(MediaFile).where(
            and_(MediaFile.id == file_id, MediaFile.deleted_at.is_(None))
        )
        result = await session.execute(statement)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        return db_file
        
    except Exception as e:
        logger.error(f"Error getting file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/{file_id}", response_model=MediaFilePublic)
async def update_file(
    file_id: int,
    file_update: MediaFileUpdate,
    session: SessionDep = Depends()
):
    """Update file metadata."""
    try:
        # Get file record
        statement = select(MediaFile).where(
            and_(MediaFile.id == file_id, MediaFile.deleted_at.is_(None))
        )
        result = await session.execute(statement)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Update fields
        update_data = file_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_file, field, value)
        
        # Update public URL if visibility changed
        if 'is_public' in update_data:
            db_file.public_url = (
                r2_service.get_public_url(db_file.file_key) 
                if db_file.is_public else None
            )
        
        session.add(db_file)
        await session.commit()
        await session.refresh(db_file)
        
        return db_file
        
    except Exception as e:
        logger.error(f"Error updating file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    hard_delete: bool = Query(False),
    session: SessionDep = Depends(),
    background_tasks: BackgroundTasks = None
):
    """Delete a file (soft delete by default, hard delete optional)."""
    try:
        # Get file record
        statement = select(MediaFile).where(MediaFile.id == file_id)
        result = await session.execute(statement)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        if hard_delete:
            # Delete from R2 storage
            background_tasks.add_task(r2_service.delete_file, db_file.file_key)
            
            # Delete from database
            await session.delete(db_file)
        else:
            # Soft delete
            from datetime import datetime
            db_file.deleted_at = datetime.now()
            session.add(db_file)
        
        await session.commit()
        
        return {"message": f"File {'deleted' if hard_delete else 'marked for deletion'}"}
        
    except R2StorageError as e:
        logger.error(f"R2 storage error during deletion: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Utility Endpoints
@router.post("/{file_id}/confirm-upload")
async def confirm_upload(
    file_id: int,
    session: SessionDep = Depends()
):
    """Confirm that a presigned upload was completed and update file metadata.
    
    This endpoint should be called after a successful presigned upload
    to verify the file exists and update metadata.
    """
    try:
        # Get file record
        statement = select(MediaFile).where(MediaFile.id == file_id)
        result = await session.execute(statement)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Verify file exists in R2
        file_exists = await r2_service.file_exists(db_file.file_key)
        if not file_exists:
            raise HTTPException(status_code=400, detail="File upload not completed")
        
        # Get file metadata from R2
        r2_metadata = await r2_service.get_file_metadata(db_file.file_key)
        if r2_metadata:
            db_file.file_size = r2_metadata.get('content_length', 0)
            # Update mime type if detected differently
            if r2_metadata.get('content_type'):
                db_file.mime_type = r2_metadata['content_type']
        
        session.add(db_file)
        await session.commit()
        await session.refresh(db_file)
        
        return {"message": "Upload confirmed", "file": db_file}
        
    except R2StorageError as e:
        logger.error(f"R2 storage error: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    except Exception as e:
        logger.error(f"Error confirming upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")