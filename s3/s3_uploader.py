#!/usr/bin/env python3
"""
Simple S3 uploader for Financial Methodologies KB
Uses AWS credentials from ~/.aws/ directory
"""

import os
import sys
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

# S3 Configuration
ENDPOINT_URL = 'https://s3.ru1.storage.beget.cloud'
BUCKET_NAME = 'db6a1f644d97-la-ducem1'
PROJECT_PREFIX = 'financial-methodologies-kb'

class S3Uploader:
    def __init__(self):
        """Initialize S3 client with Beget endpoint"""
        self.bucket_name = BUCKET_NAME
        self.project_prefix = PROJECT_PREFIX
        
        # Create S3 client with explicit endpoint and S3v4 signature
        from botocore.config import Config
        
        self.s3 = boto3.client(
            's3',
            endpoint_url=ENDPOINT_URL,
            region_name='ru1',
            config=Config(signature_version='s3v4')
        )
        
        # Note: head_bucket may return 403 even with valid credentials
        # We'll test connection on first actual operation
        print(f"🔗 S3 client initialized for bucket: {self.bucket_name}")
    
    def upload_file(self, local_path: str, s3_key: str = None) -> bool:
        """
        Upload a file to S3
        
        Args:
            local_path: Path to local file
            s3_key: S3 object key (if None, uses filename with project prefix)
        
        Returns:
            bool: True if successful
        """
        local_file = Path(local_path)
        
        if not local_file.exists():
            print(f"❌ File not found: {local_path}")
            return False
        
        # Generate S3 key if not provided
        if s3_key is None:
            s3_key = f"{self.project_prefix}/{local_file.name}"
        elif not s3_key.startswith(self.project_prefix):
            s3_key = f"{self.project_prefix}/{s3_key}"
        
        try:
            print(f"⬆️  Uploading {local_file.name} -> s3://{self.bucket_name}/{s3_key}")
            
            # Upload file
            self.s3.upload_file(
                str(local_file),
                self.bucket_name,
                s3_key
            )
            
            print(f"✅ Uploaded: {s3_key}")
            return True
            
        except ClientError as e:
            print(f"❌ Upload failed: {e}")
            return False
    
    def upload_directory(self, local_dir: str, s3_prefix: str = None) -> dict:
        """
        Upload all files from a directory to S3
        
        Args:
            local_dir: Path to local directory
            s3_prefix: S3 prefix for uploaded files
        
        Returns:
            dict: Statistics (success, failed, skipped)
        """
        local_path = Path(local_dir)
        
        if not local_path.is_dir():
            print(f"❌ Directory not found: {local_dir}")
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        if s3_prefix is None:
            s3_prefix = f"{self.project_prefix}/{local_path.name}"
        elif not s3_prefix.startswith(self.project_prefix):
            s3_prefix = f"{self.project_prefix}/{s3_prefix}"
        
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        # Get all files recursively
        files = list(local_path.rglob('*'))
        files = [f for f in files if f.is_file()]
        
        print(f"\n📁 Uploading directory: {local_dir}")
        print(f"📊 Found {len(files)} files")
        print(f"🎯 Target: s3://{self.bucket_name}/{s3_prefix}/\n")
        
        for file_path in files:
            # Calculate relative path
            rel_path = file_path.relative_to(local_path)
            s3_key = f"{s3_prefix}/{rel_path}".replace('\\', '/')
            
            if self.upload_file(str(file_path), s3_key):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        print(f"\n📊 Upload complete:")
        print(f"   ✅ Success: {stats['success']}")
        print(f"   ❌ Failed: {stats['failed']}")
        
        return stats
    
    def list_files(self, prefix: str = None) -> list:
        """
        List files in S3 bucket
        
        Args:
            prefix: S3 prefix to filter by
        
        Returns:
            list: List of object keys
        """
        if prefix and not prefix.startswith(self.project_prefix):
            prefix = f"{self.project_prefix}/{prefix}"
        elif prefix is None:
            prefix = self.project_prefix
        
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                print(f"📁 No files found with prefix: {prefix}")
                return []
            
            objects = response['Contents']
            print(f"\n📁 Found {len(objects)} files in s3://{self.bucket_name}/{prefix}/\n")
            
            for obj in objects:
                size_mb = obj['Size'] / (1024 * 1024)
                print(f"   📄 {obj['Key']} ({size_mb:.2f} MB)")
            
            return [obj['Key'] for obj in objects]
            
        except ClientError as e:
            print(f"❌ List failed: {e}")
            return []
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """
        Download a file from S3
        
        Args:
            s3_key: S3 object key
            local_path: Path to save file locally
        
        Returns:
            bool: True if successful
        """
        try:
            print(f"⬇️  Downloading s3://{self.bucket_name}/{s3_key} -> {local_path}")
            
            # Create parent directories if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            self.s3.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
            
            print(f"✅ Downloaded: {local_path}")
            return True
            
        except ClientError as e:
            print(f"❌ Download failed: {e}")
            return False


def main():
    """CLI interface for S3 uploader"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 s3_uploader.py upload <file_or_dir> [s3_key]")
        print("  python3 s3_uploader.py list [prefix]")
        print("  python3 s3_uploader.py download <s3_key> <local_path>")
        print("\nExamples:")
        print("  python3 s3_uploader.py upload books/")
        print("  python3 s3_uploader.py upload book.pdf books/book.pdf")
        print("  python3 s3_uploader.py list books/")
        sys.exit(1)
    
    command = sys.argv[1]
    uploader = S3Uploader()
    
    if command == 'upload':
        if len(sys.argv) < 3:
            print("❌ Please specify file or directory to upload")
            sys.exit(1)
        
        path = sys.argv[2]
        s3_key = sys.argv[3] if len(sys.argv) > 3 else None
        
        if os.path.isdir(path):
            uploader.upload_directory(path, s3_key)
        else:
            uploader.upload_file(path, s3_key)
    
    elif command == 'list':
        prefix = sys.argv[2] if len(sys.argv) > 2 else None
        uploader.list_files(prefix)
    
    elif command == 'download':
        if len(sys.argv) < 4:
            print("❌ Please specify s3_key and local_path")
            sys.exit(1)
        
        s3_key = sys.argv[2]
        local_path = sys.argv[3]
        uploader.download_file(s3_key, local_path)
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()
