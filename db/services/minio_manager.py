"""
MinIO Manager Service
Handles image storage operations.
"""
import io
import hashlib
import aiohttp
from typing import Optional
from minio import Minio
from minio.error import S3Error

from ..config import (
    MINIO_HOST, MINIO_PORT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY,
    MINIO_BUCKET, MINIO_SECURE
)


class MinIOManager:
    """
    Manager for MinIO object storage operations.
    Handles image download, upload, and retrieval.
    """
    
    def __init__(self):
        self._client: Optional[Minio] = None
        self._bucket = MINIO_BUCKET
    
    def connect(self) -> bool:
        """Connect to MinIO server."""
        try:
            self._client = Minio(
                f"{MINIO_HOST}:{MINIO_PORT}",
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            
            # Ensure bucket exists
            if not self._client.bucket_exists(self._bucket):
                self._client.make_bucket(self._bucket)
                print(f"[MinIO] Created bucket: {self._bucket}")
            
            print(f"[MinIO] Connected to {MINIO_HOST}:{MINIO_PORT}")
            return True
            
        except Exception as e:
            print(f"[MinIO] Connection failed: {e}")
            return False
    
    def _generate_filename(self, url: str, index: int = 0) -> str:
        """Generate filename from URL."""
        # Extract extension from URL
        ext = 'jpg'
        if '.' in url.split('/')[-1]:
            ext = url.split('.')[-1].split('?')[0][:4]  # Max 4 chars
        
        if index == 0:
            return f"main.{ext}"
        return f"content_{index}.{ext}"
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        print(f"[MinIO] Failed to download {url}: HTTP {response.status}")
                        return None
        except Exception as e:
            print(f"[MinIO] Download error {url}: {e}")
            return None
    
    def upload_image(self, news_id: str, filename: str, image_bytes: bytes) -> Optional[str]:
        """
        Upload image to MinIO.
        
        Args:
            news_id: News item ID (used as folder)
            filename: Name for the file
            image_bytes: Image data
            
        Returns:
            MinIO path or None if failed
        """
        try:
            object_name = f"{news_id}/{filename}"
            
            self._client.put_object(
                bucket_name=self._bucket,
                object_name=object_name,
                data=io.BytesIO(image_bytes),
                length=len(image_bytes),
                content_type=self._get_content_type(filename)
            )
            
            path = f"minio://{self._bucket}/{object_name}"
            print(f"[MinIO] Uploaded: {path}")
            return path
            
        except S3Error as e:
            print(f"[MinIO] Upload failed: {e}")
            return None
    
    def _get_content_type(self, filename: str) -> str:
        """Get MIME type from filename."""
        ext = filename.split('.')[-1].lower()
        types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'webp': 'image/webp',
            'gif': 'image/gif'
        }
        return types.get(ext, 'application/octet-stream')
    
    async def process_news_images(self, news_id: str, media: dict) -> dict:
        """
        Download and store all images for a news item.
        
        Args:
            news_id: News item ID
            media: Media dict with main_image and content_images
            
        Returns:
            Updated media dict with minio_path fields
        """
        result = {
            'main_image': None,
            'content_images': [],
            'videos': media.get('videos', [])
        }
        
        # Process main image
        main_url = media.get('main_image')
        if main_url:
            image_bytes = await self.download_image(main_url)
            if image_bytes:
                minio_path = self.upload_image(
                    news_id,
                    self._generate_filename(main_url, 0),
                    image_bytes
                )
                result['main_image'] = {
                    'original_url': main_url,
                    'minio_path': minio_path
                }
        
        # Process content images
        content_images = media.get('content_images', [])
        for i, img_url in enumerate(content_images[:5]):  # Limit to 5
            image_bytes = await self.download_image(img_url)
            if image_bytes:
                minio_path = self.upload_image(
                    news_id,
                    self._generate_filename(img_url, i + 1),
                    image_bytes
                )
                result['content_images'].append({
                    'original_url': img_url,
                    'minio_path': minio_path
                })
        
        return result
    
    def get_image(self, news_id: str, filename: str) -> Optional[bytes]:
        """
        Retrieve image from MinIO.
        
        Returns:
            Image bytes or None if not found
        """
        try:
            object_name = f"{news_id}/{filename}"
            response = self._client.get_object(self._bucket, object_name)
            return response.read()
        except S3Error as e:
            print(f"[MinIO] Get failed: {e}")
            return None
        finally:
            if 'response' in locals():
                response.close()
                response.release_conn()
    
    def delete_news_images(self, news_id: str) -> bool:
        """Delete all images for a news item."""
        try:
            objects = self._client.list_objects(
                self._bucket,
                prefix=f"{news_id}/"
            )
            for obj in objects:
                self._client.remove_object(self._bucket, obj.object_name)
            print(f"[MinIO] Deleted images for: {news_id}")
            return True
        except S3Error as e:
            print(f"[MinIO] Delete failed: {e}")
            return False
