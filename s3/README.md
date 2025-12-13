# S3 Integration for Financial Methodologies KB

This directory contains tools and documentation for working with S3 object storage.

## Structure

```
s3/
├── .env                    # S3 credentials (not in git)
├── .env.example           # Template for credentials
├── SETUP_GUIDE.md         # Detailed setup guide for S3 clients
├── S3_STORAGE.md          # Project-specific S3 documentation
├── s3_manager.py          # Python S3 manager (boto3)
└── s3_storage.sh          # Bash script for S3 operations
```

## Quick Start

### 1. Setup Credentials

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp s3/.env.example s3/.env
# Edit s3/.env with your credentials
```

### 2. Python Manager

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install boto3 python-dotenv

# Use the manager
python3 s3/s3_manager.py list books/
python3 s3/s3_manager.py sync books books
```

### 3. Bash Script

```bash
# Set environment
export S3_ACCESS_KEY=your_key
export S3_SECRET_KEY=your_secret

# Use the script
./s3/s3_storage.sh list books/
./s3/s3_storage.sh sync-books
```

## Storage Structure

```
s3://db6a1f644d97-la-ducem1/financial-methodologies-kb/
├── books/                  # Reference materials and books
├── templates/             # Excel and document templates
├── guides/                # Implementation guides
├── presentations/         # Presentations
└── datasets/              # Example datasets
```

## Documentation

- **SETUP_GUIDE.md** - Complete guide for all S3 clients (AWS CLI, S3cmd, Rclone, etc.)
- **S3_STORAGE.md** - Project-specific usage and best practices

## Security

⚠️ **Important**: Never commit `.env` file to git. It's already in `.gitignore`.

## See Also

- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Rclone Documentation](https://rclone.org/docs/)
