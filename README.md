# Research Assistant System (RAS)

A RAG system for academic paper literature surveys.

## What it does

- Supports claims with relevant papers from indexed academic papers
- Provides opposing viewpoints from literature
- Uses agentic RAG for deep paper analysis

## Prerequisites

- Python 3.12+
- Terraform 1.5+
- AWS CLI configured with credentials

## Setup

### 1. Configure

Edit `config.json` and set your IAM username:
```json
{
  "username": "your-iam-username"
}
```

### 2. Bootstrap (Admin only)

```powershell
python setup.py bootstrap init
python setup.py bootstrap apply
```

Then add developers to the group:
```bash
aws iam add-user-to-group --group-name ras-developers --user-name {username}
```

### 3. Dev Environment

```powershell
# Set Upstash credentials (for Terraform)
$env:UPSTASH_EMAIL = "your-email@example.com"
$env:UPSTASH_API_KEY = "your-upstash-api-key"

# Assume the developer role
python assume_role.py | Invoke-Expression

# Initialize and apply infrastructure
python setup.py dev init
python setup.py dev apply
```

Re-run `assume_role.py` when credentials expire (1 hour).

Get Upstash credentials from [Upstash Console](https://console.upstash.com/account/api).

## Commands

### Infrastructure (setup.py)

```
python setup.py bootstrap init    - Initialize bootstrap terraform
python setup.py bootstrap apply   - Apply bootstrap infrastructure
python setup.py bootstrap destroy - Destroy bootstrap infrastructure

python setup.py dev init          - Initialize dev terraform
python setup.py dev apply         - Apply dev infrastructure
python setup.py dev destroy       - Destroy dev infrastructure
```

### Services (run.py)

```
python run.py producer build          - Build producer image
python run.py producer up             - Run producer container
python run.py producer down           - Stop producer container

python run.py consumer build          - Build consumer image
python run.py consumer up [mode]      - Run consumer (mode: parse, process, full)
python run.py consumer down           - Stop consumer container
```

**Consumer modes:**
- `parse` - Consume from SQS, parse PDFs, save raw elements to S3
- `process` - Load raw elements from S3, chunk, embed, store to Pinecone
- `full` - Parse and process in one pipeline (default)

Requires AWS credentials (run `python assume_role.py | Invoke-Expression` first).

### Environment Variables

Create a `.env` file in the project root for secrets:

```
# Unstructured API (for PDF parsing)
UNSTRUCTURED_API_KEY=your-api-key

# Redis (from Terraform output or Upstash console)
REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379

# OpenAI (for embeddings)
OPENAI_API_KEY=sk-xxx

# Pinecone (for vector storage)
PINECONE_API_KEY=xxx
```

Docker-compose automatically loads this file.

**For Terraform** (set in shell, not .env):
```powershell
$env:UPSTASH_EMAIL = "your-email"
$env:UPSTASH_API_KEY = "your-api-key"
```

## Documentation

See [dev_docs.md](dev_docs.md) for detailed infrastructure and component documentation.
