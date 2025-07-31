"""File Validation Service.

This service handles validation of uploaded files including:
- File type validation (MIME type checking)
- File size validation
- File content validation
- Image and video metadata extraction
"""

import magic
import io
from PIL import Image
from typing import Optional, Dict, Any, Tuple
import logging

from app.config import (
    MAX_FILE_SIZE,
    ALLOWED_IMAGE_TYPES,
    ALLOWED_VIDEO_TYPES
)

logger = logging.getLogger(__name__)


class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    pass


class FileValidator:
    """Service for validating uploaded files."""
    
    def __init__(self):
        """Initialize the file validator."""
        self.magic_mime = magic.Magic(mime=True)
        
    def validate_file_size(self, file_size: int) -> bool:
        """Validate file size against maximum allowed size.
        
        Args:
            file_size: Size of the file in bytes
            
        Returns:
            True if file size is valid
            
        Raises:
            FileValidationError: If file size exceeds limit
        """
        if file_size > MAX_FILE_SIZE:
            max_mb = MAX_FILE_SIZE / (1024 * 1024)
            current_mb = file_size / (1024 * 1024)
            raise FileValidationError(
                f"File size {current_mb:.2f}MB exceeds maximum allowed size of {max_mb:.2f}MB"
            )
        return True
    
    def validate_mime_type(self, file_content: bytes, expected_type: str) -> str:
        """Validate and detect the actual MIME type of a file.
        
        Args:
            file_content: File content as bytes
            expected_type: Expected file type ('image' or 'video')
            
        Returns:
            Detected MIME type
            
        Raises:
            FileValidationError: If MIME type is not allowed
        """
        try:
            # Detect actual MIME type
            detected_mime = self.magic_mime.from_buffer(file_content)
            
            # Validate against allowed types
            allowed_types = []
            if expected_type == 'image':
                allowed_types = ALLOWED_IMAGE_TYPES
            elif expected_type == 'video':
                allowed_types = ALLOWED_VIDEO_TYPES
            else:
                raise FileValidationError(f"Unknown file type: {expected_type}")
            
            if detected_mime not in allowed_types:
                raise FileValidationError(
                    f"File type {detected_mime} not allowed. "
                    f"Allowed types for {expected_type}: {', '.join(allowed_types)}"
                )
            
            logger.info(f"File validated with MIME type: {detected_mime}")
            return detected_mime
            
        except magic.MagicException as e:
            raise FileValidationError(f"Failed to detect file type: {e}")
    
    def extract_image_metadata(self, file_content: bytes) -> Dict[str, Any]:
        """Extract metadata from an image file.
        
        Args:
            file_content: Image file content as bytes
            
        Returns:
            Dictionary containing image metadata
        """
        try:
            with Image.open(io.BytesIO(file_content)) as img:
                metadata = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
                
                # Extract EXIF data if available
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif_data = img._getexif()
                    if exif_data:
                        # Common EXIF tags
                        metadata['exif'] = {
                            'orientation': exif_data.get(274),  # Orientation
                            'datetime': exif_data.get(306),     # DateTime
                            'camera_make': exif_data.get(271),  # Make
                            'camera_model': exif_data.get(272), # Model
                        }
                
                logger.info(f"Extracted image metadata: {metadata}")
                return metadata
                
        except Exception as e:
            logger.error(f"Failed to extract image metadata: {e}")
            return {}
    
    def extract_video_metadata(self, file_content: bytes) -> Dict[str, Any]:
        """Extract basic metadata from a video file.
        
        Note: For full video metadata extraction, consider using ffprobe/ffmpeg
        This is a basic implementation that extracts file size and type.
        
        Args:
            file_content: Video file content as bytes
            
        Returns:
            Dictionary containing basic video metadata
        """
        try:
            # Basic metadata that we can extract without additional dependencies
            metadata = {
                'file_size': len(file_content),
                'format': 'video'  # Could be enhanced with ffprobe
            }
            
            # TODO: Implement proper video metadata extraction with ffprobe
            # This would require additional dependencies and system tools
            
            logger.info(f"Extracted video metadata: {metadata}")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract video metadata: {e}")
            return {}
    
    def validate_image_content(self, file_content: bytes) -> Tuple[bool, Dict[str, Any]]:
        """Validate image content and extract metadata.
        
        Args:
            file_content: Image file content as bytes
            
        Returns:
            Tuple of (is_valid, metadata)
        """
        try:
            # Try to open and verify the image
            with Image.open(io.BytesIO(file_content)) as img:
                # Verify the image can be processed
                img.verify()
                
            # Extract metadata from a fresh copy (verify() consumes the image)
            metadata = self.extract_image_metadata(file_content)
            
            # Additional validation rules
            max_dimension = 10000  # 10k pixels max dimension
            if metadata.get('width', 0) > max_dimension or metadata.get('height', 0) > max_dimension:
                raise FileValidationError(
                    f"Image dimensions too large. Maximum allowed: {max_dimension}x{max_dimension}"
                )
            
            return True, metadata
            
        except FileValidationError:
            raise
        except Exception as e:
            raise FileValidationError(f"Invalid image file: {e}")
    
    def validate_video_content(self, file_content: bytes) -> Tuple[bool, Dict[str, Any]]:
        """Validate video content and extract metadata.
        
        Args:
            file_content: Video file content as bytes
            
        Returns:
            Tuple of (is_valid, metadata)
        """
        try:
            # Basic validation - check if file starts with common video signatures
            video_signatures = {
                b'\x00\x00\x00\x18ftypmp4': 'mp4',
                b'\x00\x00\x00\x20ftypM4V': 'm4v',
                b'RIFF': 'avi',  # Simplified check
                b'\x1a\x45\xdf\xa3': 'webm/mkv',
            }
            
            file_start = file_content[:20]
            is_valid_video = any(
                file_start.startswith(sig) for sig in video_signatures.keys()
            )
            
            if not is_valid_video:
                # Try MIME type check as fallback
                detected_mime = self.magic_mime.from_buffer(file_content)
                is_valid_video = detected_mime in ALLOWED_VIDEO_TYPES
            
            if not is_valid_video:
                raise FileValidationError("Invalid video file format")
            
            # Extract basic metadata
            metadata = self.extract_video_metadata(file_content)
            
            return True, metadata
            
        except FileValidationError:
            raise
        except Exception as e:
            raise FileValidationError(f"Invalid video file: {e}")
    
    def validate_file(
        self,
        file_content: bytes,
        filename: str,
        expected_type: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Comprehensive file validation.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            expected_type: Expected file type ('image' or 'video')
            
        Returns:
            Tuple of (detected_mime_type, metadata)
            
        Raises:
            FileValidationError: If validation fails
        """
        # Validate file size
        self.validate_file_size(len(file_content))
        
        # Validate and detect MIME type
        detected_mime = self.validate_mime_type(file_content, expected_type)
        
        # Content-specific validation and metadata extraction
        if expected_type == 'image':
            is_valid, metadata = self.validate_image_content(file_content)
        elif expected_type == 'video':
            is_valid, metadata = self.validate_video_content(file_content)
        else:
            raise FileValidationError(f"Unsupported file type: {expected_type}")
        
        if not is_valid:
            raise FileValidationError(f"File validation failed for {filename}")
        
        # Add common metadata
        metadata.update({
            'original_filename': filename,
            'detected_mime_type': detected_mime,
            'file_size': len(file_content)
        })
        
        logger.info(f"File validation successful for {filename}")
        return detected_mime, metadata


# Global instance
file_validator = FileValidator()