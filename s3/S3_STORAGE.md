# S3 Storage Configuration

## Credentials

- **S3 Endpoint**: https://s3.ru1.storage.beget.cloud
- **Bucket Name**: db6a1f644d97-la-ducem
- **Access Key**: JQDHVXZY7XFWUHF8LV0S
- **Secret Key**: `pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk`

## URL Formats

- **Path style**: https://s3.ru1.storage.beget.cloud/db6a1f644d97-la-ducem1
- **Virtual hosted style**: https://db6a1f644d97-la-ducem1.s3.ru1.storage.beget.cloud

## Project Folder Structure

```
s3://db6a1f644d97-la-ducem/financial-methodologies-kb/
├── books/
│   ├── cash-flow-story/
│   │   └── cash_flow_story_joss_milner.pdf
│   ├── simple-numbers/
│   │   ├── simple_numbers_greg_crabtree_2011.pdf
│   │   └── 2020-Simple-Numbers-Presentation-Crisis-Mode.pptx
│   ├── power-of-one/
│   │   └── power_of_one_methodology.pdf
│   ├── toc/
│   │   ├── the_goal_goldratt.pdf
│   │   └── corbett_throughput_accounting_2009.pdf
│   ├── lean-accounting/
│   │   └── practical_lean_accounting_maskell.pdf
│   ├── valuation/
│   │   └── copeland_company_valuation.pdf
│   └── metrics/
│       └── phelps_smart_business_metrics.docx
│
├── templates/
│   ├── methodology/
│   │   ├── README.md
│   │   ├── model.md
│   │   ├── workflow.md
│   │   └── decisions.md
│   ├── excel/
│   │   ├── osv_template.xlsx
│   │   ├── balance_template.xlsx
│   │   └── cashflow_template.xlsx
│   └── reports/
│       └── power_of_one_report_template.xlsx
│
├── guides/
│   ├── integration/
│   │   └── 1c_integration_guide.docx
│   ├── methodologies/
│   │   └── consolidation_methodology.docx
│   └── implementation/
│       └── methodology_implementation_checklist.md
│
├── presentations/
│   ├── lean_finance.pptx
│   └── financial_analysis_basics.pptx
│
└── datasets/
    ├── examples/
    │   ├── rebeccas_coffee_financials.xlsx
    │   └── manufacturing_example.xlsx
    └── benchmarks/
        ├── make_sell_do_benchmarks.xlsx
        └── industry_standards.xlsx
```

## Usage

### Using AWS CLI

```bash
# Configure AWS CLI with S3 credentials
aws configure set aws_access_key_id JQDHVXZY7XFWUHF8LV0S
aws configure set aws_secret_access_key pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk
aws configure set region ru-1

# Upload file
aws s3 cp local_file.pdf s3://db6a1f644d97-la-ducem/financial-methodologies-kb/books/simple-numbers/ \
  --endpoint-url https://s3.ru1.storage.beget.cloud

# List files
aws s3 ls s3://db6a1f644d97-la-ducem/financial-methodologies-kb/books/ \
  --endpoint-url https://s3.ru1.storage.beget.cloud

# Download file
aws s3 cp s3://db6a1f644d97-la-ducem/financial-methodologies-kb/books/file.pdf . \
  --endpoint-url https://s3.ru1.storage.beget.cloud

# Sync local folder to S3
aws s3 sync ./books/ s3://db6a1f644d97-la-ducem/financial-methodologies-kb/books/ \
  --endpoint-url https://s3.ru1.storage.beget.cloud
```

### Using Python boto3

```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='https://s3.ru1.storage.beget.cloud',
    aws_access_key_id='JQDHVXZY7XFWUHF8LV0S',
    aws_secret_access_key='pjVG1Zt5G6y8N8eYAmPnKcnnPpfxB3KVCcFrEyfk'
)

# Upload file
s3.upload_file(
    'local_file.pdf',
    'db6a1f644d97-la-ducem',
    'financial-methodologies-kb/books/simple-numbers/file.pdf'
)

# List objects
response = s3.list_objects_v2(
    Bucket='db6a1f644d97-la-ducem',
    Prefix='financial-methodologies-kb/books/'
)

# Download file
s3.download_file(
    'db6a1f644d97-la-ducem',
    'financial-methodologies-kb/books/file.pdf',
    'local_file.pdf'
)
```

## Best Practices

1. **Naming Convention**:
   - Use lowercase with hyphens for folders
   - Use underscores for files
   - Include version or date in filename if needed

2. **Organization**:
   - Group by methodology/topic
   - Keep source materials separate from generated content
   - Use consistent folder structure

3. **Access Control**:
   - Keep credentials in environment variables or secure vault
   - Never commit credentials to Git
   - Use IAM policies for fine-grained access

4. **Metadata**:
   - Set appropriate Content-Type for files
   - Add custom metadata for tracking (author, version, methodology)
   - Use tags for categorization

## Security Notes

⚠️ **IMPORTANT**: The credentials in this file should be:
- Stored securely (use `.env` file with `.gitignore`)
- Rotated periodically
- Not shared publicly
- Access-controlled at bucket level
