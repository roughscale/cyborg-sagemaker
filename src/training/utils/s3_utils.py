"""S3 utility functions for uploading/downloading files."""

import boto3
import logging
from pathlib import Path
from typing import Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Uploader:
    """Helper class for uploading files to S3."""

    def __init__(self, bucket_name: Optional[str] = None, region: str = 'us-east-1'):
        """Initialize S3 uploader.

        Args:
            bucket_name: S3 bucket name (optional, can be set per upload)
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3', region_name=region)
        logger.info(f"S3Uploader initialized for region: {region}")

    def upload_file(
        self,
        local_path: str,
        s3_key: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Upload a file to S3.

        Args:
            local_path: Path to local file
            s3_key: S3 object key (path in bucket)
            bucket_name: S3 bucket name (uses instance bucket if not provided)

        Returns:
            True if upload succeeded, False otherwise
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            logger.error("No bucket name provided")
            return False

        local_file = Path(local_path)
        if not local_file.exists():
            logger.error(f"Local file not found: {local_path}")
            return False

        try:
            logger.info(f"Uploading {local_path} to s3://{bucket}/{s3_key}")
            self.s3_client.upload_file(
                str(local_path),
                bucket,
                s3_key
            )
            logger.info(f"Successfully uploaded to s3://{bucket}/{s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return False

    def upload_directory(
        self,
        local_dir: str,
        s3_prefix: str,
        bucket_name: Optional[str] = None,
        pattern: str = "*"
    ) -> int:
        """Upload all files in a directory to S3.

        Args:
            local_dir: Path to local directory
            s3_prefix: S3 prefix (directory path in bucket)
            bucket_name: S3 bucket name (uses instance bucket if not provided)
            pattern: Glob pattern for files to upload (default: all files)

        Returns:
            Number of files uploaded
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            logger.error("No bucket name provided")
            return 0

        local_path = Path(local_dir)
        if not local_path.exists():
            logger.error(f"Local directory not found: {local_dir}")
            return 0

        # Find all matching files
        files = list(local_path.rglob(pattern))
        uploaded_count = 0

        for file_path in files:
            if file_path.is_file():
                # Calculate relative path for S3 key
                relative_path = file_path.relative_to(local_path)
                s3_key = f"{s3_prefix.rstrip('/')}/{relative_path}"

                if self.upload_file(str(file_path), s3_key, bucket):
                    uploaded_count += 1

        logger.info(f"Uploaded {uploaded_count}/{len(files)} files from {local_dir}")
        return uploaded_count

    def download_file(
        self,
        s3_key: str,
        local_path: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Download a file from S3.

        Args:
            s3_key: S3 object key (path in bucket)
            local_path: Path to save file locally
            bucket_name: S3 bucket name (uses instance bucket if not provided)

        Returns:
            True if download succeeded, False otherwise
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            logger.error("No bucket name provided")
            return False

        try:
            # Create parent directory if it doesn't exist
            local_file = Path(local_path)
            local_file.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading s3://{bucket}/{s3_key} to {local_path}")
            self.s3_client.download_file(
                bucket,
                s3_key,
                str(local_path)
            )
            logger.info(f"Successfully downloaded to {local_path}")
            return True

        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            return False

    def file_exists(self, s3_key: str, bucket_name: Optional[str] = None) -> bool:
        """Check if a file exists in S3.

        Args:
            s3_key: S3 object key
            bucket_name: S3 bucket name (uses instance bucket if not provided)

        Returns:
            True if file exists, False otherwise
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            logger.error("No bucket name provided")
            return False

        try:
            self.s3_client.head_object(Bucket=bucket, Key=s3_key)
            return True
        except ClientError:
            return False


def get_s3_uploader(bucket_name: Optional[str] = None) -> S3Uploader:
    """Get an S3Uploader instance.

    Args:
        bucket_name: S3 bucket name (optional)

    Returns:
        S3Uploader instance
    """
    return S3Uploader(bucket_name=bucket_name)
