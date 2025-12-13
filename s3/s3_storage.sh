#!/usr/bin/env bash
set -euo pipefail

# S3 Configuration
S3_ENDPOINT="https://s3.ru1.storage.beget.cloud"
S3_BUCKET="db6a1f644d97-la-ducem"
S3_PREFIX="financial-methodologies-kb"

# Load credentials from environment or .env file
: "${S3_ACCESS_KEY:?Set S3_ACCESS_KEY environment variable}"
: "${S3_SECRET_KEY:?Set S3_SECRET_KEY environment variable}"

# Configure AWS CLI
aws configure set aws_access_key_id "$S3_ACCESS_KEY"
aws configure set aws_secret_access_key "$S3_SECRET_KEY"
aws configure set region ru-1

echo "=== S3 Storage Manager for Financial Methodologies KB ==="
echo "Endpoint: $S3_ENDPOINT"
echo "Bucket: $S3_BUCKET"
echo "Prefix: $S3_PREFIX"
echo ""

# Function to upload file
upload_file() {
    local local_path="$1"
    local s3_path="$2"
    
    echo "Uploading $local_path to s3://$S3_BUCKET/$S3_PREFIX/$s3_path"
    aws s3 cp "$local_path" "s3://$S3_BUCKET/$S3_PREFIX/$s3_path" \
        --endpoint-url "$S3_ENDPOINT"
}

# Function to sync directory
sync_to_s3() {
    local local_dir="$1"
    local s3_dir="$2"
    
    echo "Syncing $local_dir to s3://$S3_BUCKET/$S3_PREFIX/$s3_dir"
    aws s3 sync "$local_dir" "s3://$S3_BUCKET/$S3_PREFIX/$s3_dir" \
        --endpoint-url "$S3_ENDPOINT" \
        --exclude "*.git/*" \
        --exclude "*.DS_Store"
}

# Function to list files
list_files() {
    local s3_path="${1:-}"
    
    echo "Listing files in s3://$S3_BUCKET/$S3_PREFIX/$s3_path"
    aws s3 ls "s3://$S3_BUCKET/$S3_PREFIX/$s3_path" \
        --endpoint-url "$S3_ENDPOINT" \
        --recursive
}

# Function to download file
download_file() {
    local s3_path="$1"
    local local_path="$2"
    
    echo "Downloading s3://$S3_BUCKET/$S3_PREFIX/$s3_path to $local_path"
    aws s3 cp "s3://$S3_BUCKET/$S3_PREFIX/$s3_path" "$local_path" \
        --endpoint-url "$S3_ENDPOINT"
}

# Main menu
case "${1:-help}" in
    upload)
        upload_file "${2:-}" "${3:-}"
        ;;
    sync)
        sync_to_s3 "${2:-}" "${3:-}"
        ;;
    list)
        list_files "${2:-}"
        ;;
    download)
        download_file "${2:-}" "${3:-}"
        ;;
    sync-books)
        echo "Syncing books directory..."
        sync_to_s3 "books" "books"
        ;;
    help|*)
        echo "Usage: $0 {upload|sync|list|download|sync-books|help}"
        echo ""
        echo "Commands:"
        echo "  upload <local_file> <s3_path>   - Upload single file"
        echo "  sync <local_dir> <s3_dir>       - Sync directory to S3"
        echo "  list [s3_path]                  - List files in S3"
        echo "  download <s3_path> <local_file> - Download file from S3"
        echo "  sync-books                      - Quick sync books directory"
        echo ""
        echo "Examples:"
        echo "  $0 upload book.pdf books/simple-numbers/book.pdf"
        echo "  $0 sync ./books books"
        echo "  $0 list books/"
        echo "  $0 sync-books"
        ;;
esac
