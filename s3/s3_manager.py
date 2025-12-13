#!/usr/bin/env python3
"""
S3 Storage Manager for Financial Methodologies KB

Provides Python API for working with S3 storage.
"""

import os
import boto3
from pathlib import Path
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class S3StorageManager:
    """Manager for S3 storage operations."""
    
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        bucket_name: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        prefix: str = "financial-methodologies-kb"
    ):
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT")
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET")
        self.prefix = prefix
        
        access_key = access_key or os.getenv("S3_ACCESS_KEY")
        secret_key = secret_key or os.getenv("S3_SECRET_KEY")
        
        if not all([self.endpoint_url, self.bucket_name, access_key, secret_key]):
            raise ValueError("Missing S3 credentials. Set environment variables or pass explicitly.")
        
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=boto3.session.Config(signature_version='s3v4')
        )
    
    def _get_full_key(self, key: str) -> str:
        """Get full S3 key with prefix."""
        if key.startswith(self.prefix):
            return key
        return f"{self.prefix}/{key}".lstrip('/')
    
    def upload_file(self, local_path: str, s3_path: str, metadata: Optional[Dict] = None) -> bool:
        """
        Upload a file to S3.
        
        Args:
            local_path: Path to local file
            s3_path: Destination path in S3 (relative to prefix)
            metadata: Optional metadata dict
        
        Returns:
            True if successful
        """
        full_key = self._get_full_key(s3_path)
        
        extra_args = {}
        if metadata:
            extra_args['Metadata'] = metadata
        
        try:
            # Use multipart upload config
            from botocore.config import Config
            config = Config(signature_version='s3v4')
            transfer_config = boto3.s3.transfer.TransferConfig(
                multipart_threshold=8388608,  # 8MB
                max_concurrency=10,
                multipart_chunksize=8388608,
                use_threads=True
            )
            
            self.s3.upload_file(
                local_path, 
                self.bucket_name, 
                full_key, 
                ExtraArgs=extra_args,
                Config=transfer_config
            )
            print(f"✓ Uploaded {local_path} to s3://{self.bucket_name}/{full_key}")
            return True
        except Exception as e:
            print(f"✗ Error uploading {local_path}: {e}")
            return False
    
    def download_file(self, s3_path: str, local_path: str) -> bool:
        """
        Download a file from S3.
        
        Args:
            s3_path: Path in S3 (relative to prefix)
            local_path: Destination local path
        
        Returns:
            True if successful
        """
        full_key = self._get_full_key(s3_path)
        
        try:
            # Create parent directories if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.s3.download_file(self.bucket_name, full_key, local_path)
            print(f"✓ Downloaded s3://{self.bucket_name}/{full_key} to {local_path}")
            return True
        except Exception as e:
            print(f"✗ Error downloading {s3_path}: {e}")
            return False
    
    def list_files(self, prefix: str = "") -> List[Dict]:
        """
        List files in S3.
        
        Args:
            prefix: Path prefix to filter (relative to project prefix)
        
        Returns:
            List of file info dicts
        """
        full_prefix = self._get_full_key(prefix)
        
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=full_prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified']
                })
            
            return files
        except Exception as e:
            print(f"✗ Error listing files: {e}")
            return []
    
    def sync_directory(self, local_dir: str, s3_dir: str, exclude_patterns: Optional[List[str]] = None) -> int:
        """
        Sync a local directory to S3.
        
        Args:
            local_dir: Local directory path
            s3_dir: S3 directory (relative to prefix)
            exclude_patterns: List of patterns to exclude
        
        Returns:
            Number of files uploaded
        """
        exclude_patterns = exclude_patterns or ['.git', '.DS_Store', '__pycache__']
        local_path = Path(local_dir)
        
        if not local_path.exists():
            print(f"✗ Local directory not found: {local_dir}")
            return 0
        
        uploaded = 0
        for file_path in local_path.rglob('*'):
            if file_path.is_file():
                # Check exclude patterns
                if any(pattern in str(file_path) for pattern in exclude_patterns):
                    continue
                
                relative_path = file_path.relative_to(local_path)
                s3_path = f"{s3_dir}/{relative_path}".replace('\\', '/')
                
                if self.upload_file(str(file_path), s3_path):
                    uploaded += 1
        
        print(f"\n✓ Synced {uploaded} files from {local_dir} to s3://{self.bucket_name}/{self._get_full_key(s3_dir)}")
        return uploaded
    
    def get_file_url(self, s3_path: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for a file.
        
        Args:
            s3_path: Path in S3 (relative to prefix)
            expires_in: URL expiration time in seconds
        
        Returns:
            Presigned URL
        """
        full_key = self._get_full_key(s3_path)
        
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': full_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            print(f"✗ Error generating URL: {e}")
            return ""


def main():
    """CLI interface for S3 storage manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description="S3 Storage Manager")
    parser.add_argument("command", choices=["upload", "download", "list", "sync", "url"])
    parser.add_argument("args", nargs="*", help="Command arguments")
    
    args = parser.parse_args()
    
    manager = S3StorageManager()
    
    if args.command == "upload":
        if len(args.args) < 2:
            print("Usage: upload <local_path> <s3_path>")
            return
        manager.upload_file(args.args[0], args.args[1])
    
    elif args.command == "download":
        if len(args.args) < 2:
            print("Usage: download <s3_path> <local_path>")
            return
        manager.download_file(args.args[0], args.args[1])
    
    elif args.command == "list":
        prefix = args.args[0] if args.args else ""
        files = manager.list_files(prefix)
        for f in files:
            print(f"{f['key']} ({f['size']} bytes, {f['last_modified']})")
    
    elif args.command == "sync":
        if len(args.args) < 2:
            print("Usage: sync <local_dir> <s3_dir>")
            return
        manager.sync_directory(args.args[0], args.args[1])
    
    elif args.command == "url":
        if len(args.args) < 1:
            print("Usage: url <s3_path>")
            return
        url = manager.get_file_url(args.args[0])
        print(url)


if __name__ == "__main__":
    main()
