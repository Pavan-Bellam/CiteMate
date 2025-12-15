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

## Quick Start

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

## CI/CD Pipelines

Deployments are automated via GitHub Actions using OIDC authentication.

| Branch | Environment | Workflow |
|--------|-------------|----------|
| `main` | Staging | `deploy-staging.yml` |
| `prod` | Production | `deploy-production.yml` |

### GitHub Secrets Required

Add in **Repository → Settings → Secrets and variables → Actions**:

- `UNSTRUCTURED_API_KEY`
- `UPSTASH_EMAIL`
- `UPSTASH_API_KEY`
- `PINECONE_API_KEY`
- `OPENAI_API_KEY`

No AWS credentials needed - OIDC handles authentication.

### Manual Trigger

Workflows can also be triggered manually via **Actions → Run workflow**.

## Commands

### Infrastructure (setup.py)

```
python setup.py bootstrap init/apply/destroy  - Bootstrap (admin)
python setup.py dev init/apply/destroy        - Dev environment
python setup.py staging init/apply/destroy    - Staging environment
python setup.py production init/apply/destroy - Production environment
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

## Configuration Files

| File | Purpose |
|------|---------|
| `config.json` | Local development |
| `config.staging.json` | Staging environment |
| `config.production.json` | Production environment |

## Environment Variables

Create a `.env` file in the project root for local development:

```
UNSTRUCTURED_API_KEY=your-api-key
UPSTASH_EMAIL=your-email
UPSTASH_API_KEY=your-api-key
PINECONE_API_KEY=xxx
OPENAI_API_KEY=sk-xxx
```

## Documentation

See [dev_docs.md](dev_docs.md) for detailed infrastructure and component documentation.
