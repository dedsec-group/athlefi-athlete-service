"""Cloudflare R2 Storage Service.

This service handles all interactions with Cloudflare R2 storage including:
- File upload with presigned URLs
- File download and streaming
- File deletion and cleanup
- Metadata management
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, BinaryIO, Dict, Any
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from botocore.config import Config
import logging

from app.config import (
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_ENDPOINT_URL,
    R2_BUCKET_NAME,
    R2_PUBLIC_DOMAIN,
    PRESIGNED_URL_EXPIRY
)

logger = logging.getLogger(__name__)


class R2StorageError(Exception):
    """Custom exception for R2 storage operations."""
    pass


class R2Service:
    """Service for managing files in Cloudflare R2 storage."""
    
    def __init__(self):
        """Initialize the R2 service with boto3 client."""
        self._client = None
        self._bucket_name = R2_BUCKET_NAME
        self._public_domain = R2_PUBLIC_DOMAIN
        
    @property
    def client(self):
        """Lazy initialization of boto3 client."""
        if self._client is None:
            try:
                # Configure boto3 for Cloudflare R2
                config = Config(
                    region_name='auto',
                    retries={'max_attempts': 3, 'mode': 'adaptive'},
                    max_pool_connections=50
                )
                
                self._client = boto3.client(
                    's3',
                    endpoint_url=R2_ENDPOINT_URL,
                    aws_access_key_id=R2_ACCESS_KEY_ID,
                    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
                    config=config
                )
                
                # Verify connection
                self._client.head_bucket(Bucket=self._bucket_name)
                logger.info(f"Successfully connected to R2 bucket: {self._bucket_name}")
                
            except NoCredentialsError:
                raise R2StorageError("R2 credentials not configured properly")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    raise R2StorageError(f"R2 bucket '{self._bucket_name}' not found")
                else:
                    raise R2StorageError(f"Failed to connect to R2: {e}")
            except Exception as e:
                raise R2StorageError(f"Unexpected error connecting to R2: {e}")
                
        return self._client
    
    def generate_file_key(self, filename: str, athlete_id: Optional[int] = None) -> str:
        """Generate a unique file key for R2 storage.
        
        Args:
            filename: Original filename
            athlete_id: Optional athlete ID for organization
            
        Returns:
            Unique file key for R2 storage
        """
        # Extract file extension
        file_ext = filename.split('.')[-1] if '.' in filename else ''
        
        # Generate unique identifier
        unique_id = str(uuid.uuid4())
        
        # Create organized path structure
        year_month = datetime.now().strftime("%Y/%m")
        
        if athlete_id:
            file_key = f"athletes/{athlete_id}/{year_month}/{unique_id}"
        else:
            file_key = f"general/{year_month}/{unique_id}"
            
        if file_ext:
            file_key += f".{file_ext}"
            
        return file_key
    
    async def generate_presigned_upload_url(
        self,
        file_key: str,
        content_type: str,
        expires_in: int = PRESIGNED_URL_EXPIRY
    ) -> str:
        """Generate a presigned URL for file upload.
        
        Args:
            file_key: Unique file key in R2
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned upload URL
        """
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _generate_url():
                return self.client.generate_presigned_url(
                    'put_object',
                    Params={
                        'Bucket': self._bucket_name,
                        'Key': file_key,
                        'ContentType': content_type,
                        'Metadata': {
                            'uploaded_at': datetime.now().isoformat(),
                            'original_content_type': content_type
                        }
                    },
                    ExpiresIn=expires_in
                )
            
            url = await loop.run_in_executor(None, _generate_url)
            logger.info(f"Generated presigned upload URL for key: {file_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            raise R2StorageError(f"Failed to generate upload URL: {e}")
    
    async def generate_presigned_download_url(
        self,
        file_key: str,
        expires_in: int = PRESIGNED_URL_EXPIRY
    ) -> str:
        """Generate a presigned URL for file download.
        
        Args:
            file_key: File key in R2
            expires_in: URL expiration time in seconds
            
        Returns:
            Presigned download URL
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _generate_url():
                return self.client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self._bucket_name,
                        'Key': file_key
                    },
                    ExpiresIn=expires_in
                )
            
            url = await loop.run_in_executor(None, _generate_url)
            logger.info(f"Generated presigned download URL for key: {file_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned download URL: {e}")
            raise R2StorageError(f"Failed to generate download URL: {e}")
    
    def get_public_url(self, file_key: str) -> Optional[str]:
        """Get public URL for a file if public domain is configured.
        
        Args:
            file_key: File key in R2
            
        Returns:
            Public URL or None if not configured
        """
        if self._public_domain:
            return f"{self._public_domain.rstrip('/')}/{file_key}"
        return None
    
    async def upload_file(
        self,
        file_key: str,
        file_data: BinaryIO,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Upload a file directly to R2 (for server-side uploads).
        
        Args:
            file_key: Unique file key in R2
            file_data: File binary data
            content_type: MIME type of the file
            metadata: Additional metadata
            
        Returns:
            True if upload successful
        """
        try:
            upload_metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'original_content_type': content_type
            }
            if metadata:
                upload_metadata.update(metadata)
            
            loop = asyncio.get_event_loop()
            
            def _upload():
                self.client.put_object(
                    Bucket=self._bucket_name,
                    Key=file_key,
                    Body=file_data,
                    ContentType=content_type,
                    Metadata=upload_metadata
                )
            
            await loop.run_in_executor(None, _upload)
            logger.info(f"Successfully uploaded file: {file_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to upload file {file_key}: {e}")
            raise R2StorageError(f"Failed to upload file: {e}")
    
    async def delete_file(self, file_key: str) -> bool:
        """Delete a file from R2 storage.
        
        Args:
            file_key: File key to delete
            
        Returns:
            True if deletion successful
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _delete():
                self.client.delete_object(
                    Bucket=self._bucket_name,
                    Key=file_key
                )
            
            await loop.run_in_executor(None, _delete)
            logger.info(f"Successfully deleted file: {file_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete file {file_key}: {e}")
            raise R2StorageError(f"Failed to delete file: {e}")
    
    async def file_exists(self, file_key: str) -> bool:
        """Check if a file exists in R2 storage.
        
        Args:
            file_key: File key to check
            
        Returns:
            True if file exists
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _check_exists():
                self.client.head_object(
                    Bucket=self._bucket_name,
                    Key=file_key
                )
                return True
            
            return await loop.run_in_executor(None, _check_exists)
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking file existence {file_key}: {e}")
            raise R2StorageError(f"Error checking file existence: {e}")
    
    async def get_file_metadata(self, file_key: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a file in R2 storage.
        
        Args:
            file_key: File key to get metadata for
            
        Returns:
            File metadata or None if not found
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _get_metadata():
                response = self.client.head_object(
                    Bucket=self._bucket_name,
                    Key=file_key
                )
                return {
                    'content_length': response.get('ContentLength'),
                    'content_type': response.get('ContentType'),
                    'last_modified': response.get('LastModified'),
                    'etag': response.get('ETag'),
                    'metadata': response.get('Metadata', {})
                }
            
            return await loop.run_in_executor(None, _get_metadata)
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            logger.error(f"Error getting file metadata {file_key}: {e}")
            raise R2StorageError(f"Error getting file metadata: {e}")
    
    async def copy_file(self, source_key: str, dest_key: str) -> bool:
        """Copy a file within R2 storage.
        
        Args:
            source_key: Source file key
            dest_key: Destination file key
            
        Returns:
            True if copy successful
        """
        try:
            loop = asyncio.get_event_loop()
            
            def _copy():
                copy_source = {
                    'Bucket': self._bucket_name,
                    'Key': source_key
                }
                self.client.copy_object(
                    CopySource=copy_source,
                    Bucket=self._bucket_name,
                    Key=dest_key
                )
            
            await loop.run_in_executor(None, _copy)
            logger.info(f"Successfully copied file from {source_key} to {dest_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to copy file from {source_key} to {dest_key}: {e}")
            raise R2StorageError(f"Failed to copy file: {e}")


# Global instance
r2_service = R2Service()