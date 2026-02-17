import boto3
from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional, BinaryIO, Callable, TypeVar, Type, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException, status
import uuid
from pathlib import Path
from config import settings
import logging
import asyncio
import json


logger = logging.getLogger(__name__)

T = TypeVar('T')


class ImageManager:
    """Manager for working with S3-compatible storage (MinIO)"""

    def __init__(self):
        """Initialize ImageManager (lazy initialization of S3 client)"""
        self._s3_client = None
        self.bucket_name = settings.s3_bucket_name

    @property
    def s3_client(self):
        """Lazy initialization of S3 client"""
        if self._s3_client is None:
            self._s3_client = boto3.client(
                's3',
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
                region_name=settings.s3_region_name
            )
            # Ensure bucket exists (synchronous call, but bucket creation is idempotent)
            self._ensure_bucket_exists()
        return self._s3_client

    def _ensure_bucket_exists(self) -> None:
        """Ensure S3 bucket exists, create if it doesn't"""
        # Use _s3_client directly to avoid recursion
        if self._s3_client is None:
            return
        try:
            self._s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket '{self.bucket_name}' already exists")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in {'404', 'NoSuchBucket', 'NotFound'}:
                # Bucket doesn't exist, create it
                try:
                    self._s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created S3 bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"Failed to create S3 bucket: {str(create_error)}")
                    # Don't raise - bucket might be created by external process
            else:
                logger.warning(f"Error checking S3 bucket existence: {str(e)}")

    def _set_bucket_public_policy(self) -> None:
        """Set bucket policy to allow public read access"""
        # Use _s3_client directly to avoid property access
        if self._s3_client is None:
            return
        try:
            # Public read policy JSON
            public_read_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                    }
                ]
            }

            policy_json = json.dumps(public_read_policy)
            
            self._s3_client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=policy_json
            )
            logger.info(f"Set public read policy for bucket '{self.bucket_name}'")
        except ClientError as e:
            logger.warning(f"Failed to set bucket policy: {str(e)}")
            # Don't raise - policy might already be set or bucket might not support it
        except Exception as e:
            logger.warning(f"Unexpected error setting bucket policy: {str(e)}")

    async def initialize_bucket(self) -> None:
        """Initialize bucket: ensure it exists and set public policy"""
        # Access s3_client to trigger initialization and bucket creation
        # (bucket creation happens in s3_client property)
        _ = self.s3_client
        
        # Set public policy (synchronous operation)
        self._set_bucket_public_policy()

    def _generate_file_path(self, prefix: str, filename: str) -> str:
        """Generate unique file path for S3"""
        file_extension = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        return f"{prefix}/{unique_filename}"

    async def upload_image(
        self, 
        file_content: bytes, 
        filename: str, 
        prefix: str = "images",
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload image to S3 storage
        
        Args:
            file_content: Binary content of the file
            filename: Original filename
            prefix: Folder prefix in S3 (default: "images")
            content_type: MIME type of the file (optional)
            
        Returns:
            S3 object key (path) of uploaded file
            
        Raises:
            Exception: If upload fails
        """
        try:
            s3_path = self._generate_file_path(prefix, filename)
            
            # Determine content type if not provided
            if not content_type:
                content_type = self._get_content_type(filename)
            
            # Upload to S3 (run in thread pool to avoid blocking)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_path,
                    Body=file_content,
                    ContentType=content_type
                )
            )
            
            logger.info(f"Image uploaded successfully to S3: {s3_path}")
            return s3_path
            
        except ClientError as e:
            logger.error(f"Error uploading image to S3: {str(e)}")
            raise Exception(f"Failed to upload image to S3: {str(e)}")
        except BotoCoreError as e:
            logger.error(f"BotoCore error uploading image: {str(e)}")
            raise Exception(f"Failed to upload image: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading image: {str(e)}")
            raise

    async def delete_image(self, s3_path: str) -> bool:
        """
        Delete image from S3 storage
        
        Args:
            s3_path: S3 object key (path) of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=s3_path
                )
            )
            logger.info(f"Image deleted successfully from S3: {s3_path}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting image from S3: {str(e)}")
            return False
        except BotoCoreError as e:
            logger.error(f"BotoCore error deleting image: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting image: {str(e)}")
            return False

    async def get_image_url(self, s3_path: str, expires_in: int = 3600) -> str:
        """
        Generate presigned URL for image access
        
        Args:
            s3_path: S3 object key (path) of the file
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL for accessing the image
        """
        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                lambda: self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': s3_path},
                    ExpiresIn=expires_in
                )
            )
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise Exception(f"Failed to generate image URL: {str(e)}")
        except BotoCoreError as e:
            logger.error(f"BotoCore error generating presigned URL: {str(e)}")
            raise Exception(f"Failed to generate image URL: {str(e)}")

    def _get_content_type(self, filename: str) -> str:
        """Determine content type based on file extension"""
        extension = Path(filename).suffix.lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.bmp': 'image/bmp'
        }
        return content_types.get(extension, 'application/octet-stream')

    async def image_exists(self, s3_path: str) -> bool:
        """
        Check if image exists in S3
        
        Args:
            s3_path: S3 object key (path) of the file
            
        Returns:
            True if image exists, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=s3_path
                )
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking image existence: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking image existence: {str(e)}")
            return False

    async def upload_and_create_image_record(
        self,
        session: AsyncSession,
        entity_id: int,
        file: UploadFile,
        prefix: str,
        order: int,
        entity_name: str,
        get_entity_func: Callable[[AsyncSession, int], Optional[Any]],
        create_image_func: Callable[[AsyncSession, int, str, int], T],
        schema_class: Type[T]
    ) -> T:
        """
        Upload image to S3 and create image record in database
        
        Args:
            session: Database session
            entity_id: ID of the entity (product, seller, shop_point, etc.)
            file: Uploaded file
            prefix: S3 folder prefix
            order: Image display order
            entity_name: Name of entity for error messages (e.g., "product", "seller")
            get_entity_func: Function to verify entity exists
            create_image_func: Function to create image record in database
            schema_class: Pydantic schema class for validation
            
        Returns:
            Validated image schema
        """
        # Verify entity exists
        entity = await get_entity_func(session, entity_id)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_name.capitalize()} with id {entity_id} not found"
            )

        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image"
            )

        # Read file content
        try:
            file_content = await file.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read file: {str(e)}"
            )

        # Upload to S3
        try:
            s3_path = await self.upload_image(
                file_content=file_content,
                filename=file.filename or "image",
                prefix=prefix,
                content_type=file.content_type
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image: {str(e)}"
            )

        # Create image record in database
        image = await create_image_func(session, entity_id, s3_path, order)
        await session.commit()

        return schema_class.model_validate(image)

    async def delete_image_record(
        self,
        session: AsyncSession,
        image_id: int,
        entity_name: str,
        get_image_func: Callable[[AsyncSession, int], Optional[T]],
        delete_image_func: Callable[[AsyncSession, int], None]
    ) -> None:
        """
        Delete image from S3 and database
        
        Args:
            session: Database session
            image_id: ID of the image record
            entity_name: Name of entity for error messages (e.g., "product", "seller")
            get_image_func: Function to get image record from database
            delete_image_func: Function to delete image record from database
        """
        # Get image record
        image = await get_image_func(session, image_id)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_name.capitalize()} image with id {image_id} not found"
            )

        # Delete from S3
        success = await self.delete_image(image.path)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete image from S3"
            )

        # Delete from database
        await delete_image_func(session, image_id)
        await session.commit()

    async def upload_multiple_and_create_image_records(
        self,
        session: AsyncSession,
        entity_id: int,
        files: list[UploadFile],
        prefix: str,
        start_order: int,
        entity_name: str,
        get_entity_func: Callable[[AsyncSession, int], Optional[Any]],
        create_image_func: Callable[[AsyncSession, int, str, int], T],
        schema_class: Type[T]
    ) -> list[T]:
        """
        Upload multiple images to S3 and create image records in database
        
        Args:
            session: Database session
            entity_id: ID of the entity (product, seller, shop_point, etc.)
            files: List of uploaded files
            prefix: S3 folder prefix
            start_order: Starting order for images (will increment for each image)
            entity_name: Name of entity for error messages (e.g., "product", "seller")
            get_entity_func: Function to verify entity exists
            create_image_func: Function to create image record in database
            schema_class: Pydantic schema class for validation
            
        Returns:
            List of validated image schemas
        """
        # Verify entity exists
        entity = await get_entity_func(session, entity_id)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_name.capitalize()} with id {entity_id} not found"
            )

        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )

        uploaded_images = []
        current_order = start_order

        for file in files:
            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File '{file.filename}' must be an image"
                )

            # Read file content
            try:
                file_content = await file.read()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to read file '{file.filename}': {str(e)}"
                )

            # Upload to S3
            try:
                s3_path = await self.upload_image(
                    file_content=file_content,
                    filename=file.filename or "image",
                    prefix=prefix,
                    content_type=file.content_type
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload image '{file.filename}': {str(e)}"
                )

            # Create image record in database
            image = await create_image_func(session, entity_id, s3_path, current_order)
            uploaded_images.append(schema_class.model_validate(image))
            current_order += 1

        await session.commit()
        return uploaded_images
