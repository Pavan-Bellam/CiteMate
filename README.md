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
# Assume the developer role
python assume_role.py | Invoke-Expression

# Initialize and apply infrastructure
python setup.py dev init
python setup.py dev apply
```

Re-run `assume_role.py` when credentials expire (1 hour).

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
python run.py producer build      - Build producer image
python run.py producer up         - Run producer container
python run.py producer down       - Stop producer container
```

Requires AWS credentials (run `python assume_role.py | Invoke-Expression` first).

## Documentation

See [dev_docs.md](dev_docs.md) for detailed infrastructure and component documentation.
