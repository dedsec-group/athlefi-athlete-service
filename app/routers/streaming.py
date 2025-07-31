"""Streaming API Router.

This router provides optimized endpoints for:
- Video streaming with range request support
- Image streaming with caching
- Progressive download for large files
- Adaptive streaming information
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_
import logging

from app.config import SessionDep
from app.models import MediaFile
from app.services.streaming_service import streaming_service, StreamingError

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/stream",
    tags=["streaming"],
)


@router.get("/{file_id}/video")
async def stream_video(
    file_id: int,
    request: Request,
    session: SessionDep = Depends()
) -> StreamingResponse:
    """Stream a video file with range request support.
    
    This endpoint is optimized for video streaming and supports:
    - HTTP Range requests for seeking
    - Progressive download
    - Proper caching headers
    """
    try:
        # Get file record
        statement = select(MediaFile).where(
            and_(
                MediaFile.id == file_id,
                MediaFile.file_type == "video",
                MediaFile.deleted_at.is_(None)
            )
        )
        result = await session.execute(statement)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Create optimized video streaming response
        return await streaming_service.create_video_streaming_response(
            db_file.file_key,
            request,
            db_file.original_filename
        )
        
    except StreamingError as e:
        logger.error(f"Video streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in video streaming: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{file_id}/image")
async def stream_image(
    file_id: int,
    request: Request,
    session: SessionDep = Depends()
) -> StreamingResponse:
    """Stream an image file with optimized caching.
    
    This endpoint is optimized for image delivery with:
    - Aggressive caching headers
    - Efficient streaming
    - Proper content types
    """
    try:
        # Get file record
        statement = select(MediaFile).where(
            and_(
                MediaFile.id == file_id,
                MediaFile.file_type == "image",
                MediaFile.deleted_at.is_(None)
            )
        )
        result = await session.execute(statement)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise HTTPException(status_code=404, detail="Image file not found")
        
        # Create optimized image streaming response
        return await streaming_service.create_image_streaming_response(
            db_file.file_key,
            request,
            db_file.original_filename
        )
        
    except StreamingError as e:
        logger.error(f"Image streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in image streaming: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{file_id}/raw")
async def stream_file_raw(
    file_id: int,
    request: Request,
    session: SessionDep = Depends()
) -> StreamingResponse:
    """Stream any file type with basic streaming support.
    
    This endpoint provides generic file streaming for any file type.
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
        
        # Create generic streaming response
        return await streaming_service.create_streaming_response(
            db_file.file_key,
            request,
            db_file.mime_type,
            db_file.original_filename
        )
        
    except StreamingError as e:
        logger.error(f"File streaming error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in file streaming: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{file_id}/info")
async def get_streaming_info(
    file_id: int,
    session: SessionDep = Depends()
):
    """Get streaming information for a file.
    
    Returns metadata useful for setting up streaming clients.
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
        
        # Get streaming information
        stream_info = await streaming_service.get_adaptive_stream_info(db_file.file_key)
        
        # Add database metadata
        stream_info.update({
            'file_id': db_file.id,
            'filename': db_file.original_filename,
            'file_type': db_file.file_type,
            'mime_type': db_file.mime_type,
            'width': db_file.width,
            'height': db_file.height,
            'duration': db_file.duration,
            'is_public': db_file.is_public,
            'public_url': db_file.public_url
        })
        
        return stream_info
        
    except StreamingError as e:
        logger.error(f"Error getting streaming info: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting streaming info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")