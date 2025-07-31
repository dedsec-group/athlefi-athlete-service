"""Streaming Service for Large File Handling.

This service provides streaming capabilities for:
- Progressive video streaming
- Range request handling
- Chunked file transmission
- Adaptive bitrate streaming support
"""

import asyncio
import aiohttp
from typing import Optional, AsyncGenerator, Tuple
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse
import logging

from app.services.r2_service import r2_service, R2StorageError

logger = logging.getLogger(__name__)


class StreamingError(Exception):
    """Custom exception for streaming operations."""
    pass


class StreamingService:
    """Service for streaming files from R2 storage."""
    
    def __init__(self):
        """Initialize the streaming service."""
        self.chunk_size = 8192  # 8KB chunks for streaming
        self.max_chunk_size = 1048576  # 1MB max chunk for large files
    
    async def get_file_size(self, file_key: str) -> int:
        """Get the size of a file in R2 storage.
        
        Args:
            file_key: File key in R2 storage
            
        Returns:
            File size in bytes
        """
        try:
            metadata = await r2_service.get_file_metadata(file_key)
            if not metadata:
                raise StreamingError(f"File not found: {file_key}")
            return metadata.get('content_length', 0)
        except R2StorageError as e:
            raise StreamingError(f"Failed to get file size: {e}")
    
    def parse_range_header(self, range_header: str, file_size: int) -> Tuple[int, int]:
        """Parse HTTP Range header and return start and end positions.
        
        Args:
            range_header: HTTP Range header value
            file_size: Total file size in bytes
            
        Returns:
            Tuple of (start, end) positions
        """
        try:
            # Parse "bytes=start-end" format
            if not range_header.startswith('bytes='):
                raise ValueError("Invalid range header format")
            
            range_spec = range_header[6:]  # Remove "bytes=" prefix
            
            if '-' not in range_spec:
                raise ValueError("Invalid range specification")
            
            start_str, end_str = range_spec.split('-', 1)
            
            if start_str and end_str:
                # Both start and end specified: "bytes=200-999"
                start = int(start_str)
                end = int(end_str)
            elif start_str and not end_str:
                # Only start specified: "bytes=200-"
                start = int(start_str)
                end = file_size - 1
            elif not start_str and end_str:
                # Only end specified: "bytes=-500" (last 500 bytes)
                end = file_size - 1
                start = file_size - int(end_str)
            else:
                raise ValueError("Invalid range specification")
            
            # Validate range
            if start < 0 or end >= file_size or start > end:
                raise ValueError("Invalid range values")
            
            return start, end
            
        except (ValueError, IndexError) as e:
            raise StreamingError(f"Invalid range header: {e}")
    
    async def stream_file_range(
        self,
        file_key: str,
        start: int = 0,
        end: Optional[int] = None
    ) -> AsyncGenerator[bytes, None]:
        """Stream a file or file range from R2 storage.
        
        Args:
            file_key: File key in R2 storage
            start: Start byte position
            end: End byte position (inclusive)
            
        Yields:
            File content chunks
        """
        try:
            # Generate presigned URL for download
            download_url = await r2_service.generate_presigned_download_url(file_key)
            
            # Set up range headers for partial content
            headers = {}
            if end is not None:
                headers['Range'] = f'bytes={start}-{end}'
            elif start > 0:
                headers['Range'] = f'bytes={start}-'
            
            # Stream file content
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url, headers=headers) as response:
                    if response.status not in (200, 206):  # 206 = Partial Content
                        raise StreamingError(f"Failed to stream file: HTTP {response.status}")
                    
                    # Stream in chunks
                    async for chunk in response.content.iter_chunked(self.chunk_size):
                        yield chunk
                        
        except aiohttp.ClientError as e:
            raise StreamingError(f"Network error while streaming: {e}")
        except R2StorageError as e:
            raise StreamingError(f"R2 storage error: {e}")
    
    async def create_streaming_response(
        self,
        file_key: str,
        request: Request,
        content_type: str = "application/octet-stream",
        filename: Optional[str] = None
    ) -> StreamingResponse:
        """Create a streaming response for a file.
        
        Args:
            file_key: File key in R2 storage
            request: FastAPI request object
            content_type: MIME type of the file
            filename: Optional filename for download
            
        Returns:
            StreamingResponse object
        """
        try:
            # Get file size
            file_size = await self.get_file_size(file_key)
            
            # Check for range request
            range_header = request.headers.get('range')
            
            if range_header:
                # Handle range request
                try:
                    start, end = self.parse_range_header(range_header, file_size)
                    content_length = end - start + 1
                    
                    # Create streaming generator
                    stream_generator = self.stream_file_range(file_key, start, end)
                    
                    # Prepare headers for partial content
                    headers = {
                        'Accept-Ranges': 'bytes',
                        'Content-Range': f'bytes {start}-{end}/{file_size}',
                        'Content-Length': str(content_length)
                    }
                    
                    if filename:
                        headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    return StreamingResponse(
                        stream_generator,
                        status_code=206,  # Partial Content
                        headers=headers,
                        media_type=content_type
                    )
                    
                except StreamingError:
                    # Fall back to full file if range parsing fails
                    pass
            
            # Handle full file request
            stream_generator = self.stream_file_range(file_key)
            
            headers = {
                'Accept-Ranges': 'bytes',
                'Content-Length': str(file_size)
            }
            
            if filename:
                headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return StreamingResponse(
                stream_generator,
                status_code=200,
                headers=headers,
                media_type=content_type
            )
            
        except StreamingError as e:
            logger.error(f"Streaming error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_video_streaming_response(
        self,
        file_key: str,
        request: Request,
        filename: Optional[str] = None
    ) -> StreamingResponse:
        """Create a streaming response optimized for video files.
        
        Args:
            file_key: File key in R2 storage
            request: FastAPI request object
            filename: Optional filename
            
        Returns:
            StreamingResponse optimized for video streaming
        """
        try:
            # Get file metadata to determine video type
            metadata = await r2_service.get_file_metadata(file_key)
            if not metadata:
                raise StreamingError(f"File not found: {file_key}")
            
            content_type = metadata.get('content_type', 'video/mp4')
            
            # Create streaming response with video-specific optimizations
            response = await self.create_streaming_response(
                file_key, request, content_type, filename
            )
            
            # Add video-specific headers
            response.headers.update({
                'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                'X-Content-Type-Options': 'nosniff'
            })
            
            return response
            
        except StreamingError as e:
            logger.error(f"Video streaming error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_image_streaming_response(
        self,
        file_key: str,
        request: Request,
        filename: Optional[str] = None
    ) -> StreamingResponse:
        """Create a streaming response optimized for image files.
        
        Args:
            file_key: File key in R2 storage
            request: FastAPI request object
            filename: Optional filename
            
        Returns:
            StreamingResponse optimized for image delivery
        """
        try:
            # Get file metadata to determine image type
            metadata = await r2_service.get_file_metadata(file_key)
            if not metadata:
                raise StreamingError(f"File not found: {file_key}")
            
            content_type = metadata.get('content_type', 'image/jpeg')
            
            # Create streaming response
            response = await self.create_streaming_response(
                file_key, request, content_type, filename
            )
            
            # Add image-specific headers
            response.headers.update({
                'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                'X-Content-Type-Options': 'nosniff'
            })
            
            return response
            
        except StreamingError as e:
            logger.error(f"Image streaming error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_adaptive_stream_info(
        self,
        file_key: str
    ) -> dict:
        """Get information for adaptive streaming (placeholder for future HLS/DASH support).
        
        Args:
            file_key: Video file key in R2 storage
            
        Returns:
            Dictionary with streaming information
        """
        try:
            metadata = await r2_service.get_file_metadata(file_key)
            if not metadata:
                raise StreamingError(f"File not found: {file_key}")
            
            # Basic streaming info (can be extended for HLS/DASH)
            stream_info = {
                'file_key': file_key,
                'content_type': metadata.get('content_type'),
                'file_size': metadata.get('content_length'),
                'supports_range_requests': True,
                'streaming_protocols': ['progressive'],  # Can add 'hls', 'dash' later
                'chunk_size_recommended': self.chunk_size
            }
            
            return stream_info
            
        except R2StorageError as e:
            raise StreamingError(f"Failed to get stream info: {e}")


# Global instance
streaming_service = StreamingService()