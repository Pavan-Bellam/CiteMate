# Developer Documentation

## Project Overview

**RAS (Research Assistant System)** is an AI-powered research writing assistant for researchers in the AI/ML field. The system helps users write better papers by providing real-time feedback, literature discovery, and an intelligent chatbot.

### Target Users
Researchers writing academic papers, primarily in AI/ML (though the architecture supports any domain with appropriate data).

### Core Features

| Feature | Description |
|---------|-------------|
| **Corrections** | Detects grammatical mistakes, finds supporting evidence, and identifies opposing viewpoints in user's writing |
| **Literature Survey** | Automatically discovers relevant papers as the user writes - triggered per paragraph or manually |
| **Chatbot** | Answers research questions with citations and proofs from the paper corpus |

### System Architecture

The project consists of two major components:

#### 1. RAG Pipeline (Completed)
The ingestion and retrieval system that powers all features:
- **Producer**: Fetches papers from ArXiv → S3 → SQS
- **Consumer**: Parses PDFs → chunks → generates embeddings (dense + sparse) → Pinecone
- **Retrieval**: Hybrid search using dense (OpenAI) and sparse (BM25) vectors

#### 2. Multi-Agent System (Core Project)
```
┌─────────────────────────────────────────────────────────────────┐
│                          INTERFACE                              │
│  - User-facing layer                                            │
│  - Handles local corrections (grammar, style, consistency)      │
│  - Formulates questions for external knowledge needs            │
│  - Escalates to Router only when literature context required    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                │ (only when external
                                │  knowledge needed)
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                           ROUTER                                │
│  - Central orchestrator                                         │
│  - Maintains Q&A history and expert registry                    │
│  - Routes questions to existing experts or forwards to Scout    │
│  - Proactively spawns experts for frequently accessed papers    │
└───────────┬─────────────────────────────────┬───────────────────┘
            │                                 │
            │ No expert match                 │ Expert exists
            ▼                                 ▼
┌─────────────────────────────┐          ┌───────────────────────────────┐
│           SCOUT             │          │          EXPERTS              │
│  - Stateless retrieval      │  spawns  │  (one per paper, persistent)  │
│  - Hybrid search (dense +   │─────────►│                               │
│    sparse vectors)          │          │ ┌───────┐ ┌───────┐ ┌───────┐ │
│  - Answers from chunks if   │          │ │Paper A│ │Paper B│ │Paper C│ │
│    sufficient               │          │ └───────┘ └───────┘ └───────┘ │
│  - Spawns expert if deeper  │          │                               │
│    context needed           │          │  - Full paper context loaded  │
└─────────────────────────────┘          │  - Answers questions about    │
                                         │    assigned paper             │
                                         └───────────────────────────────┘
```

**Component Responsibilities:**

| Component | Role | State |
|-----------|------|-------|
| **Interface** | User interaction, local corrections (grammar, style, internal consistency), question formulation, escalation decisions | Stateful (user conversation) |
| **Router** | Orchestration, expert lifecycle management, routing decisions | Stateful (Q&A history + expert registry) |
| **Scout** | Retrieval, first-pass answering, expert spawning when chunks insufficient | Stateless |
| **Expert** | Deep Q&A on assigned paper | Stateful (full paper context) |

### Question Flow
```
User writes paragraph
       │
       ▼
   INTERFACE
   (local corrections: grammar, style, consistency)
       │
       ├──────────────────────┐
       │                      │
       ▼                      ▼
  Local issues only?    Needs external knowledge?
       │                      │
       ▼                      ▼
  Return corrections       ROUTER
  directly to user      (checks expert registry)
                              │
                         ┌────┴────┐
                         │         │
                         ▼         ▼
                      Expert    SCOUT
                      exists    (retrieves chunks)
                         │            │
                         │       ┌────┴────┐
                         │       │         │
                         │       ▼         ▼
                         │  Sufficient?  Spawn/route
                         │       │       to expert
                         │       ▼         │
                         │    Answer       │
                         │       │         │
                         └───┬───┴─────────┘
                             │
                             ▼
                          ROUTER
                         (synthesizes, updates context,
                          may spawn experts for frequent papers)
                             │
                             ▼
                         INTERFACE
                         (returns to user)
```

### Use Case Flows

**Writing Assistance (Corrections + Lit Survey):**
1. User writes/completes a paragraph
2. Interface handles local corrections (grammar, style, internal consistency)
3. Interface identifies needs requiring external knowledge (evidence, counterpoints)
4. Interface formulates questions and escalates to Router
5. Router checks expert registry for relevant experts
6. If no expert match → Scout retrieves chunks, answers directly or spawns experts
7. If expert exists → Router queries expert directly
8. Router synthesizes responses, updates context
9. Interface combines local corrections with literature-based feedback and returns to user

**Chatbot:**
1. User asks a research question
2. Interface passes query to Router
3. Router checks expert registry
4. Routes to existing expert or forwards to Scout
5. Scout retrieves, answers, or spawns expert as needed
6. Router synthesizes response with citations
7. Interface returns answer to user

---
## Project Structure

```
ras/
├── config.json              # Local development config
├── config.staging.json      # Staging environment config
├── config.production.json   # Production environment config
├── setup.py                 # Setup and deployment scripts
├── assume_role.py           # Assume developer role (get temp credentials)
├── .github/
│   └── workflows/
│       ├── deploy-staging.yml     # CI/CD for staging (main branch)
│       └── deploy-production.yml  # CI/CD for production (prod branch)
├── terraform/
│   ├── bootstrap/       # One-time setup (S3 bucket, IAM roles, OIDC)
│   ├── modules/
│   │   ├── ecr/         # ECR repository + push policy
│   │   ├── sqs/         # SQS queue + DLQ
│   │   ├── redis/       # Upstash Redis database
│   │   ├── ecs/         # ECS cluster + task definitions
│   │   └── ssm/         # SSM Parameter Store secrets
│   └── envs/
│       ├── development/ # Per-developer environment
│       ├── shared/      # Shared resources (ECR)
│       ├── staging/     # Staging environment
│       └── production/  # Production environment
└── ingestion/
    ├── producer/        # ArXiv paper fetcher
    └── consumer/        # PDF parser, chunker, embedder
```

## Configuration

`config.json` in root:
```json
{
  "project_name": "ras",
  "aws_region": "us-east-1",
  "aws_account_id": "YOUR_ACCOUNT_ID",
  "username": "YOUR_IAM_USERNAME",
  "bootstrap": {
    "bucket_name": "YOUR_BUCKET_NAME"
  },
  "github": {
    "org": "YOUR_GITHUB_ORG",
    "repository": "YOUR_REPO_NAME",
    "main_branch": "main",
    "prod_branch": "prod"
  }
}
```

- Set `username` to your IAM username before running local setup.
- Set `github` config for CI/CD OIDC authentication (used by bootstrap).


## Infrastructure

### Terraform Structure

#### bootstrap/

Run once by an admin to create shared infrastructure. Uses local state (not remote).

**Files:**
- `main.tf` - AWS provider config with default tags (Project, Environment=bootstrap)
- `versions.tf` - Requires Terraform >= 1.5.0, AWS provider >= 6.0.0
- `variables.tf` - Input variables (project_name, aws_region, aws_account_id, bucket_name, github_org, github_repository, main_branch, prod_branch)
- `oidc.tf` - GitHub Actions OIDC identity provider
- `iam_policy.tf` - IAM policies for GitHub Actions CI/CD
- `s3.tf` - Creates the shared S3 bucket with versioning enabled
- `iam.tf` - Creates developer role, policies, group, and GitHub OIDC roles
- `locals.tf` - (empty)

**Resources Created:**

1. **S3 Bucket** (`aws_s3_bucket.state_bucket`)
   - Name: from config.json `bootstrap.bucket_name`
   - Versioning enabled
   - `force_destroy = true` (can delete even with objects)

2. **Developer Role** (`ras-developer-role`)
   - Assumable by any IAM user in the account
   - Requires `sts:SetSourceIdentity` with username (for audit trail)
   - All resource access is scoped to `development/${aws:SourceIdentity}/` path

3. **Developer Terraform State Policy** (`ras-developer-terraform-state-policy`)
   - ListBucket on `development/{username}/terraform/*`
   - GetObject/PutObject on `terraform.tfstate`
   - GetObject/PutObject/DeleteObject on `terraform.tfstate.tflock`

4. **Developer Infrastructure Policy** (`ras-developer-infrastructure-policy`)
   - S3: Full access to `development/{username}/*`
   - ECR: Create/delete repos matching `ras-dev-{username}-*`
   - IAM: Create/delete policies matching `ras-dev-{username}-*`

5. **Developers Group** (`ras-developers`)
   - Members can assume the developer role
   - Add IAM users to this group to grant access

6. **GitHub OIDC Provider** (`aws_iam_openid_connect_provider.oidc`)
   - URL: `https://token.actions.githubusercontent.com`
   - Allows GitHub Actions to assume IAM roles without long-lived credentials

7. **GitHub Staging OIDC Role** (`ras-github-stage-oidc-role`)
   - Assumable by GitHub Actions from the `main` branch
   - Used for deploying staging infrastructure
   - Trust policy restricts to specific repo and branch

8. **GitHub Production OIDC Role** (`ras-github-prod-oidc-role`)
   - Assumable by GitHub Actions from the `prod` branch
   - Used for deploying production infrastructure
   - Trust policy restricts to specific repo and branch

9. **GitHub Actions Policies** (`ras-github-actions-staging`, `ras-github-actions-production`)
   - Terraform state access (S3)
   - ECR push/pull
   - SSM parameter management
   - ECS cluster and task management
   - IAM role/policy management (scoped to environment prefix)
   - CloudWatch log groups
   - EventBridge scheduler

#### modules/ecr/

Creates ECR repositories for producer and consumer images with a push policy.

**Files:**
- `main.tf` - ECR repositories (producer + consumer) + IAM push policy
- `variables.tf` - repository_name
- `outputs.tf` - repository URLs, ARNs, push_policy_arn
- `versions.tf` - AWS provider >= 6.0.0

**Resources Created:**
- `{repository_name}-producer` - ECR repo for producer image
- `{repository_name}-consumer` - ECR repo for consumer image

**Configuration:**
- `image_tag_mutability = "MUTABLE"` (can overwrite tags)
- `scan_on_push = false` (no automatic vulnerability scanning)

**Push Policy Permissions:**
- `ecr:GetAuthorizationToken` (on `*`)
- Push actions: BatchCheckLayerAvailability, GetDownloadUrlForLayer, BatchGetImage, PutImage, InitiateLayerUpload, UploadLayerPart, CompleteLayerUpload

**Outputs:**
- `producer_repository_url` - URL for producer ECR repo
- `producer_repository_arn` - ARN for producer ECR repo
- `consumer_repository_url` - URL for consumer ECR repo
- `consumer_repository_arn` - ARN for consumer ECR repo
- `push_policy_arn` - IAM policy ARN for pushing images

#### modules/sqs/

Creates an SQS queue with a dead letter queue.

**Files:**
- `main.tf` - Main queue + DLQ with redrive policy
- `variables.tf` - queue_name, visibility_timeout, retention, etc.
- `outputs.tf` - queue_url, queue_arn, dlq_url, dlq_arn

**Configuration:**
- `visibility_timeout_seconds` - default 600 (10 min)
- `message_retention_seconds` - default 1209600 (14 days)
- `receive_wait_time_seconds` - default 20 (long polling)
- `max_receive_count` - default 3 (then sent to DLQ)

**Usage:**
```hcl
module "sqs" {
  source     = "../../modules/sqs"
  queue_name = "${var.project_name}-dev-${var.developer}-papers"
}
```

#### modules/redis/

Creates an Upstash Redis database for chunk batching.

**Files:**
- `main.tf` - Upstash Redis database resource (global region)
- `variables.tf` - redis_db_name, redis_primary_region, redis_tls
- `outputs.tf` - redis_url (connection string)
- `versions.tf` - Upstash provider requirement

**Configuration:**
- `redis_primary_region` - default "us-east-1"
- `redis_tls` - default true
- Uses global region with specified primary region

**Usage:**
```hcl
module "redis" {
  source               = "../../modules/redis"
  redis_db_name        = "${var.project_name}-dev-${var.developer}"
  redis_primary_region = "us-east-1"
}
```

**Note:** Requires Upstash provider credentials set as environment variables:
```powershell
$env:UPSTASH_EMAIL = "your-email@example.com"
$env:UPSTASH_API_KEY = "your-upstash-api-key"
```

Get credentials from [Upstash Console](https://console.upstash.com/account/api).

#### modules/ecs/

Creates an ECS cluster and task definitions for producer and consumer services (nightly batch jobs).

**Files:**
- `cluster.tf` - ECS Fargate cluster
- `task_definition.tf` - Producer and consumer task definitions
- `iam.tf` - Execution role, task roles, and policies
- `variables.tf` - Input variables
- `versions.tf` - AWS provider >= 6.0.0

**Resources Created:**

1. **ECS Cluster** (`aws_ecs_cluster.this`)
   - Name: `{project_name}-{environment}`

2. **Task Definitions** (Fargate)
   - Producer: `{project_name}-{environment}-producer`
   - Consumer: `{project_name}-{environment}-consumer`
   - CPU: 256, Memory: 512
   - Network mode: awsvpc

3. **IAM Roles:**
   - **Execution Role** (`ecs_execution_role`) - For ECS to pull images and read SSM parameters
   - **Producer Task Role** - S3 PutObject (pdfs), SQS SendMessage
   - **Consumer Task Role** - SQS Receive/Delete, S3 Get/Put (pdfs, raw), S3 ListBucket

**Consumer Secrets (injected from SSM):**
- `UNSTRUCTURED_API_KEY`
- `UPSTASH_EMAIL`
- `UPSTASH_API_KEY`
- `PINECONE_API_KEY`
- `REDIS_URL`
- `OPENAI_API_KEY`

**Usage:**
```hcl
module "ecs" {
  source = "../modules/ecs"

  project_name    = var.project_name
  environment     = var.environment
  bucket_name     = var.bucket_name
  producer_image  = "${module.ecr.producer_repository_url}:latest"
  consumer_image  = "${module.ecr.consumer_repository_url}:latest"
  ssm_parameter_arns = module.ssm.parameter_arns
  ssm_parameters     = module.ssm.parameter_names
}
```

#### modules/ssm/

Creates SSM Parameter Store SecureString parameters for application secrets.

**Files:**
- `main.tf` - SSM parameter resources
- `variables.tf` - Secret values (marked sensitive)
- `outputs.tf` - Parameter ARNs and names
- `locals.tf` - Prefix helper
- `versions.tf` - AWS provider >= 6.0.0

**Parameters Created:**
- `/{project_name}/{environment}/unstructured-api-key`
- `/{project_name}/{environment}/upstash-email`
- `/{project_name}/{environment}/upstash-api-key`
- `/{project_name}/{environment}/pinecone-api-key`
- `/{project_name}/{environment}/redis-url`
- `/{project_name}/{environment}/openai-api-key`

**Usage:**
```hcl
module "ssm" {
  source = "../modules/ssm"

  project_name         = var.project_name
  environment          = var.environment
  unstructured_api_key = var.unstructured_api_key  # From CI/CD secrets
  upstash_email        = var.upstash_email
  upstash_api_key      = var.upstash_api_key
  pinecone_api_key     = var.pinecone_api_key
  redis_url            = var.redis_url
  openai_api_key       = var.openai_api_key
}
```

#### envs/development/

Per-developer environment configuration.

**Files:**
- `main.tf` - Provider config (AWS + Upstash) + module calls
- `variables.tf` - project_name, aws_region, bucket_name, developer, storage_folders, redis config
- `versions.tf` - Terraform >= 1.5.0, AWS >= 6.0.0, Upstash >= 2.1.0, S3 backend (partial config)
- `outputs.tf` - redis_url, sqs_queue_url
- `development.tfbackend` - Backend config template (bucket, key, region)

**Default Tags:**
- Project: `ras`
- Environment: `development`
- Developer: `{developer variable}`

**Modules Used:**
- `sqs` - Creates SQS queue for paper processing
- `redis` - Creates Upstash Redis for chunk batching

**Backend Configuration:**
The `.tfbackend` file is generated by `setup.py dev init` with your username:
```
bucket = "{bucket_name}"
key    = "development/{username}/terraform/terraform.tfstate"
region = "{aws_region}"
```

### S3 Bucket Structure

```
{bucket_name}/
├── development/
│   └── {username}/           # Per-developer workspace
│       ├── papers/
│       │   ├── pdfs/         # Research paper PDFs
│       │   └── raw/          # Parsed elements (JSON)
│       └── terraform/
│           └── terraform.tfstate
├── staging/
│   └── papers/
└── production/
    └── papers/
```

### AWS Authentication

The developer role requires `sts:SetSourceIdentity` which AWS config profiles don't support directly. Use `assume_role.py` to get temporary credentials.

**assume_role.py** - Assumes the developer role with your IAM username as source identity.

```bash
# PowerShell - outputs commands to set env vars, pipe to execute
python assume_role.py | Invoke-Expression

# Or just print the credentials to copy/paste
python assume_role.py --print
```

**How it works:**
1. Reads `config.json` for account ID and project name
2. Gets your IAM username via `aws sts get-caller-identity`
3. Calls `aws sts assume-role` with `--source-identity {username}`
4. Outputs PowerShell commands to set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`

**Credentials expire after 1 hour** (default STS duration).

### Setup Commands

**setup.py** automates terraform commands using values from `config.json`.

#### Bootstrap (Admin)

Run once to create shared infrastructure (S3 bucket, IAM roles, developer group):

```powershell
python setup.py bootstrap init     # terraform init
python setup.py bootstrap apply    # terraform apply
python setup.py bootstrap destroy  # terraform destroy
```

Requires admin AWS credentials.

#### Dev Environment

Run after bootstrap to set up your dev environment infrastructure:

```powershell
# 1. Set your username in config.json

# 2. Set Upstash credentials (required for Terraform Upstash provider)
$env:UPSTASH_EMAIL = "your-email@example.com"
$env:UPSTASH_API_KEY = "your-upstash-api-key"

# 3. Assume the developer role
python assume_role.py | Invoke-Expression

# 4. Initialize and apply
python setup.py dev init     # generates dev.tfbackend, terraform init
python setup.py dev apply    # terraform apply
python setup.py dev destroy  # terraform destroy
```

`dev init` generates `terraform/envs/development/dev.tfbackend` with your username.

**Note:** Re-run `python assume_role.py | Invoke-Expression` when credentials expire (1 hour).

**Note:** Upstash credentials are required for the Upstash Terraform provider. Get them from [Upstash Console](https://console.upstash.com/account/api).

### Admin Steps

1. Run bootstrap:
   ```powershell
   python setup.py bootstrap init
   python setup.py bootstrap apply
   ```

2. Add developers to the group:
   ```bash
   aws iam add-user-to-group --group-name ras-developers --user-name {username}
   ```

## CI/CD Pipelines

GitHub Actions workflows automate deployments to staging and production using OIDC authentication (no AWS credentials stored in GitHub).

### Workflows

| Workflow | Trigger | Environment | Image Tag |
|----------|---------|-------------|-----------|
| `deploy-staging.yml` | Push to `main` or manual | Staging | `:staging` |
| `deploy-production.yml` | Push to `prod` or manual | Production | `:prod` |

### GitHub Secrets Required

Add these in **Repository → Settings → Secrets and variables → Actions**:

| Secret | Description |
|--------|-------------|
| `UNSTRUCTURED_API_KEY` | Unstructured.io API key |
| `UPSTASH_EMAIL` | Upstash account email |
| `UPSTASH_API_KEY` | Upstash API key |
| `PINECONE_API_KEY` | Pinecone API key |
| `OPENAI_API_KEY` | OpenAI API key |

**Note:** AWS credentials are NOT needed - OIDC authentication is used.

### How It Works

1. Workflow reads config from `config.staging.json` or `config.production.json`
2. Authenticates to AWS via OIDC using the GitHub OIDC role
3. Creates `.env` file from GitHub Secrets
4. Runs `python setup.py {environment} init` and `apply` (deploys shared + environment infrastructure)
5. Gets ECR repository URLs from shared terraform output
6. Builds and pushes producer/consumer Docker images to ECR with environment-specific tags

### Config Files

Config files are tracked in git (not secrets):
- `config.json` - Local development
- `config.staging.json` - Staging environment
- `config.production.json` - Production environment

### Manual Deployment

Workflows can be triggered manually via **Actions → Deploy Staging/Production → Run workflow**.

---

#### Staging Environment (Local)

Deploy staging infrastructure locally with ECS, SSM secrets, and all supporting resources.

**Prerequisites:**

1. Create `config.staging.json`:
   ```json
   {
     "project_name": "ras",
     "aws_region": "us-east-1",
     "aws_account_id": "YOUR_ACCOUNT_ID",
     "bootstrap": {
       "bucket_name": "YOUR_BUCKET_NAME"
     },
     "producer": {
       "arxiv_category": "cs.AI,cs.LG,cs.CL",
       "max_results": 10,
       "max_pages": 20
     },
     "consumer": {
       "mode": "full",
       "chunk_max_characters": 1500,
       "chunk_new_after_n_chars": 1000,
       "chunk_combine_under_n_chars": 500,
       "embedding_model": "text-embedding-3-large",
       "embedding_token_threshold": 6000,
       "pinecone_index_name": "ras-papers"
     },
     "redis": {
       "redis_primary_region": "us-east-1",
       "redis_tls": true
     },
     "pinecone": {
       "embedding_dimension": "3072"
     }
   }
   ```

2. Create `.env` file with secrets:
   ```
   UNSTRUCTURED_API_KEY=xxx
   UPSTASH_EMAIL=xxx
   UPSTASH_API_KEY=xxx
   PINECONE_API_KEY=xxx
   OPENAI_API_KEY=xxx
   ```

**Commands:**

```powershell
# Set Upstash credentials for Terraform provider
$env:UPSTASH_EMAIL = "your-email@example.com"
$env:UPSTASH_API_KEY = "your-upstash-api-key"

# Initialize (runs shared first, then staging)
python setup.py staging init

# Apply (runs shared first, then staging)
python setup.py staging apply

# Destroy staging only (shared/ECR preserved)
python setup.py staging destroy
```

**What gets created:**

1. **Shared** (runs automatically):
   - ECR repositories: `{project_name}-producer`, `{project_name}-consumer`
   - ECR push policy for CI/CD

2. **Staging**:
   - SQS queue + DLQ
   - Upstash Redis database
   - SSM parameters (secrets stored as SecureString)
   - ECS cluster + task definitions (producer, consumer)
   - IAM roles and policies

**Notes:**
- `staging apply` automatically runs `shared apply` first
- ECR image URLs are fetched from shared outputs
- Producer/consumer configs come from `config.staging.json`
- Secrets come from `.env` file
- CloudWatch log groups are auto-created at `/ecs/{project_name}-staging/`

## Producer

The producer fetches papers from ArXiv and uploads PDFs to S3.

### Structure

```
ingestion/producer/
├── main.py              # Entry point
├── src/
│   ├── arxiv_client.py  # ArXiv API + PDF download
│   ├── s3_client.py     # S3 upload
│   └── pdf_utils.py     # PDF page count validation
├── Dockerfile           # uv + Python 3.12
└── pyproject.toml       # Dependencies (arxiv, boto3, httpx, pypdf)
```

### How It Works

1. Fetches paper metadata from ArXiv (query: `cat:cs.LG`)
2. Downloads PDFs
3. Checks page count (skips papers exceeding `MAX_PAGES`)
4. Uploads to S3 at `{BUCKET_PREFIX}/pdfs/{arxiv_id}.pdf`
5. Sends message to SQS with paper metadata and S3 key

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BUCKET_NAME` | S3 bucket name | from config.json |
| `BUCKET_PREFIX` | S3 key prefix | `development/{username}/papers` |
| `QUEUE_URL` | SQS queue URL | from run.py |
| `ARXIV_CATEGORY` | ArXiv category (comma-separated for multiple) | `cs.LG` or `cs.AI,cs.LG,cs.CL` |
| `MAX_RESULTS` | Max papers to fetch | `10` |
| `START_DATE` | Start of date range (ISO format, optional) | `2024-01-01` |
| `END_DATE` | End of date range (ISO format, optional) | `2024-12-01` |
| `MAX_PAGES` | Skip papers exceeding this page count | `20` |
| `AWS_ACCESS_KEY_ID` | AWS credentials | from assume_role.py |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | from assume_role.py |
| `AWS_SESSION_TOKEN` | AWS credentials | from assume_role.py |

Default behavior fetches papers from the last 1 day. Set `START_DATE` and `END_DATE` for bulk loads.

### Running with run.py

```powershell
# Assume role first
python assume_role.py | Invoke-Expression

# Build and run
python run.py producer build
python run.py producer up
python run.py producer down
```

`run.py` reads `config.json` and sets `BUCKET_NAME` and `BUCKET_PREFIX` automatically.

### Running Locally (without Docker)

```powershell
cd ingestion/producer
uv sync

# Set env vars (use values from your config.json)
$env:BUCKET_NAME = "your-bucket-name"
$env:BUCKET_PREFIX = "development/your-username/papers"

uv run python main.py
```

## Consumer

The consumer processes papers from SQS, parses PDFs using Unstructured API, chunks them, generates embeddings, and stores vectors in Pinecone.

### Structure

```
ingestion/consumer/
├── main.py              # Entry point with mode selection
├── src/
│   ├── s3_client.py     # S3 download/upload (PDFs + raw elements)
│   ├── sqs_client.py    # SQS receive/delete
│   ├── unstructured_client.py  # PDF parsing + chunking
│   ├── redis_client.py  # Chunk batching with token threshold
│   ├── openai_client.py # Dense embedding generation (OpenAI)
│   ├── bm25_client.py   # Sparse embedding generation (BM25)
│   ├── bm25_encoder.json # Pre-trained BM25 encoder
│   ├── pinecone_client.py # Vector storage (dense + sparse indices)
│   └── logger.py        # Logging setup
├── Dockerfile           # uv + Python 3.12
└── pyproject.toml       # Dependencies
```

### Modes

The consumer supports three modes for flexibility during development:

| Mode | Description | Use Case |
|------|-------------|----------|
| `parse` | SQS → parse PDF → save raw elements to S3 | Initial ingestion |
| `process` | Load raw from S3 → chunk → embed → Pinecone | Re-process with new params |
| `full` | Both parse and process (default) | Production pipeline |

### How It Works

**Parse mode:**
1. Polls SQS for messages
2. Downloads PDF from S3
3. Parses via Unstructured API
4. Saves raw elements to S3 at `{BUCKET_PREFIX}/raw/{arxiv_id}.json`
5. Deletes SQS message

**Process mode:**
1. Lists all raw element files in S3
2. For each paper: load elements → chunk → push to Redis
3. When token threshold reached:
   - Generate dense embeddings (OpenAI)
   - Generate sparse vectors (BM25)
   - Store in separate Pinecone indices (dense + sparse)
4. Flush remaining chunks at end

**Full mode:**
Combines parse and process in one continuous pipeline.

### Hybrid Search (Dense + Sparse)

The consumer generates both dense and sparse vectors for hybrid search:

| Vector Type | Source | Pinecone Index | Metric |
|-------------|--------|----------------|--------|
| Dense | OpenAI `text-embedding-3-large` | `{name}-dense-{env}-{dim}` | cosine |
| Sparse | BM25 (pinecone-text) | `{name}-sparse-{env}` | dotproduct |

**Index naming example** (with `PINECONE_INDEX_NAME=ras-papers`, `ENVIRONMENT=staging`, `EMBEDDING_DIMENSION=3072`):
- Dense: `ras-papers-dense-staging-3072`
- Sparse: `ras-papers-sparse-staging`

Both indices store the same vector IDs and metadata, enabling hybrid retrieval at query time.

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BUCKET_NAME` | S3 bucket name | from config.json |
| `BUCKET_PREFIX` | S3 key prefix | `development/{username}/papers` |
| `QUEUE_URL` | SQS queue URL | from run.py |
| `MODE` | Consumer mode | `parse`, `process`, or `full` |
| `UNSTRUCTURED_API_KEY` | Unstructured API key | your API key |
| `CHUNK_MAX_CHARACTERS` | Max chunk size | `1500` |
| `CHUNK_NEW_AFTER_N_CHARS` | Soft limit for new chunk | `1000` |
| `CHUNK_COMBINE_UNDER_N_CHARS` | Combine small chunks | `500` |
| `REDIS_URL` | Upstash Redis connection URL | `rediss://...` |
| `EMBEDDING_TOKEN_THRESHOLD` | Tokens before embedding batch | `8000` |
| `OPENAI_API_KEY` | OpenAI API key | your API key |
| `EMBEDDING_MODEL` | OpenAI embedding model | `text-embedding-3-large` |
| `PINECONE_API_KEY` | Pinecone API key | your API key |
| `PINECONE_INDEX_NAME` | Pinecone index base name | `ras-papers` |
| `EMBEDDING_DIMENSION` | Embedding vector dimension | `3072` |
| `ENVIRONMENT` | Environment name (used in index naming) | `dev`, `staging`, `prod` |

### Running with run.py

```powershell
# Assume role first
python assume_role.py | Invoke-Expression

# Build
python run.py consumer build

# Run in different modes
python run.py consumer up           # default: full mode
python run.py consumer up parse     # parse only
python run.py consumer up process   # process only (no SQS needed)

python run.py consumer down
```

### Running Locally (without Docker)

```powershell
cd ingestion/consumer
uv sync

# Set env vars
$env:BUCKET_NAME = "your-bucket-name"
$env:BUCKET_PREFIX = "development/your-username/papers"
$env:QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789/queue-name"
$env:UNSTRUCTURED_API_KEY = "your-api-key"
$env:REDIS_URL = "rediss://default:xxx@xxx.upstash.io:6379"
$env:OPENAI_API_KEY = "sk-xxx"
$env:PINECONE_API_KEY = "xxx"
$env:PINECONE_INDEX_NAME = "ras-papers"
$env:EMBEDDING_DIMENSION = "3072"

# Run in different modes
uv run python main.py full
uv run python main.py parse
uv run python main.py process
```

### Experimentation Workflow

1. Run producer once to fetch papers:
   ```powershell
   python run.py producer up
   ```

2. Parse all papers (saves raw elements to S3):
   ```powershell
   python run.py consumer up parse
   ```

3. Experiment with chunking params in `config.json`, then re-process:
   ```powershell
   python run.py consumer up process
   ```

4. Repeat step 3 as needed - no re-parsing required.

## Retrieval Service

The retrieval service provides flexible search capabilities over the ingested papers using semantic, BM25, or hybrid approaches.

### Architecture

The retrieval service uses a **dual-index architecture** with separate Pinecone indices:

| Index Type | Vector Source | Pinecone Index URL | Metric |
|------------|---------------|-------------------|--------|
| **Dense** | OpenAI `text-embedding-3-large` | `retrieval.dense_index_url` | cosine |
| **Sparse** | BM25 (pinecone-text) | `retrieval.sparse_index_url` | dotproduct |

Both indices store the same vector IDs and metadata, enabling flexible retrieval strategies at query time.

### Retrieval Modes

The service supports three retrieval modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| `semantic` | Dense vector search using OpenAI embeddings | Conceptual similarity, semantic understanding |
| `bm25` | Sparse vector search using BM25 term matching | Keyword-based retrieval, exact term matches |
| `hybrid` | Combines semantic + BM25 using Reciprocal Rank Fusion (RRF) | Best overall performance, balances semantic and lexical matching |

### Reranking

Optional reranking can be applied to improve result quality:

- **Candidate Fetching**: Fetches `initial_k=20` candidates from the index(es)
- **Reranking**: Applies a reranker model to score and re-order candidates
- **Final Results**: Returns top `rerank_top_n` results

**Supported Reranker Models:**
- `pinecone-rerank-v0` - Pinecone's reranking model
- `cohere-rerank-3.5` - Cohere's latest reranker
- `bge-reranker-v2-m3` - BGE reranker model

### Configuration

Configuration is in `config.json` under the `retrieval` section:

```json
{
  "retrieval": {
    "dense_index_url": "https://...",
    "sparse_index_url": "https://...",
    "embedding_model": "text-embedding-3-large",
    "bm25_encoder_path": "bm25_encoder.json",
    "default_mode": "hybrid",
    "top_k": 50,
    "rrf_k": 60,
    "rerank_enabled": false,
    "rerank_model": "bge-reranker-v2-m3",
    "rerank_top_n": 10
  }
}
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| `dense_index_url` | Pinecone dense index host URL | Required |
| `sparse_index_url` | Pinecone sparse index host URL | Required |
| `embedding_model` | OpenAI embedding model for queries | `text-embedding-3-large` |
| `bm25_encoder_path` | Path to pre-trained BM25 encoder | `bm25_encoder.json` |
| `default_mode` | Default retrieval mode | `hybrid` |
| `top_k` | Number of results to return | `50` |
| `rrf_k` | RRF parameter (controls rank fusion) | `60` |
| `rerank_enabled` | Enable reranking | `false` |
| `rerank_model` | Reranker model to use | `bge-reranker-v2-m3` |
| `rerank_top_n` | Number of reranked results | `10` |

### Environment Variables

The retrieval service requires the following environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `PINECONE_API_KEY` | Pinecone API key | `pcsk_xxx` |



### Evaluation Results

Performance metrics on a test set of 303 queries (Hit@K, MRR, and latency):

| Configuration | Hit@1 | Hit@5 | Hit@10 | MRR | Avg Latency (ms) | P50 Latency (ms) | P95 Latency (ms) |
|--------------|-------|-------|--------|-----|------------------|------------------|------------------|
| **semantic** | 0.726 | 0.871 | 0.911 | 0.788 | 527 | 482 | 758 |
| **bm25** | 0.756 | 0.881 | 0.914 | 0.808 | 102 | 102 | 169 |
| **hybrid** | **0.785** | **0.904** | **0.944** | **0.835** | 500 | 453 | 711 |
| semantic+pinecone-rerank-v0 | **0.828** | 0.917 | 0.931 | **0.866** | 1182 | 1064 | 1356 |
| semantic+cohere-rerank-3.5 | 0.805 | 0.911 | 0.934 | 0.849 | 1011 | 769 | 1851 |
| semantic+bge-reranker-v2-m3 | 0.802 | 0.904 | 0.924 | 0.843 | 1014 | 857 | 1609 |
| bm25+pinecone-rerank-v0 | 0.594 | 0.680 | 0.696 | 0.631 | 662 | 655 | 805 |
| bm25+cohere-rerank-3.5 | 0.825 | 0.911 | 0.927 | 0.862 | 510 | 386 | 1005 |
| bm25+bge-reranker-v2-m3 | 0.512 | 0.574 | 0.597 | 0.541 | 569 | 474 | 1353 |
| hybrid+pinecone-rerank-v0 | 0.825 | 0.927 | **0.954** | 0.870 | 1464 | 1379 | 1772 |
| **hybrid+cohere-rerank-3.5** | **0.832** | **0.927** | **0.950** | **0.872** | 989 | 808 | 1770 |
| hybrid+bge-reranker-v2-m3 | 0.805 | 0.901 | 0.941 | 0.851 | 1163 | 1035 | 1686 |

**Key Findings:**
- **Best overall**: `hybrid+cohere-rerank-3.5` achieves the highest Hit@1 (0.832) and MRR (0.872)
- **Best without reranking**: `hybrid` mode provides strong performance (Hit@1: 0.785, MRR: 0.835)
- **Fastest**: `bm25` mode is 5x faster than semantic search (102ms vs 527ms avg)
- **Hybrid benefit**: Hybrid search outperforms both semantic and BM25 individually
- **Reranking trade-off**: Reranking improves accuracy by ~5-7% but adds 500-1000ms latency

### Manual ECR Push (if needed)

CI/CD handles image builds automatically, but for manual pushes:

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin {account_id}.dkr.ecr.us-east-1.amazonaws.com

# Producer
cd ingestion/producer
docker build -t {account_id}.dkr.ecr.us-east-1.amazonaws.com/ras-producer:{tag} .
docker push {account_id}.dkr.ecr.us-east-1.amazonaws.com/ras-producer:{tag}

# Consumer
cd ingestion/consumer
docker build -t {account_id}.dkr.ecr.us-east-1.amazonaws.com/ras-consumer:{tag} .
docker push {account_id}.dkr.ecr.us-east-1.amazonaws.com/ras-consumer:{tag}
```

**Tags:** Use `:staging` for staging, `:prod` for production.

---

## Multi-Agent Implementation

This section documents the implemented agent components.

### Expert Agent

The Expert Agent is a stateful, paper-specific Q&A agent. Each expert maintains full context of a single research paper and answers questions based solely on that paper's content.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Expert Agent                                │
├─────────────────────────────────────────────────────────────────┤
│  State: Full paper content + conversation history               │
│  Memory: MongoDB (via LangGraph checkpointing)                  │
│  Model: GPT-5 with reasoning effort: medium                     │
└─────────────────────────────────────────────────────────────────┘
          │                                    ▲
          │ create_thread(paper_id)            │ query(question, thread_id)
          ▼                                    │
┌──────────────────┐                  ┌────────────────────┐
│  S3 (paper JSON) │                  │  ExpertAgentResponse│
│  Parsed by       │                  │  - title           │
│  Unstructured.io │                  │  - description     │
└──────────────────┘                  │  - answer          │
                                      └────────────────────┘
```

#### File Structure

```
app/agents/expert/
├── __init__.py      # Module exports: query, create_thread, ExpertAgentResponse
├── main.py          # Agent initialization and public API
├── models.py        # Pydantic models for structured responses
├── prompt.py        # System prompt defining agent behavior
└── utils.py         # Paper retrieval and markdown conversion
```

#### Lifecycle

1. **Creation**: `create_thread(paper_id)` fetches paper from S3, converts to markdown, initializes expert
2. **Query**: `query(question, thread_id)` asks questions using the expert's thread
3. **Persistence**: Conversation history persists in MongoDB via LangGraph checkpointing

#### Usage

```python
from app.agents.expert import create_thread, query

# Create an expert for a paper
thread_id, title, description = await create_thread("2512.02942v1")
# Returns: ("uuid-xxx", "Paper Title", "Brief description of paper scope")

# Ask questions
response = await query("What methodology does this paper use?", thread_id)
# Returns: ExpertAgentResponse(answer="The paper uses...")
```

#### Response Model

```python
class ExpertAgentResponse(BaseModel):
    title: Optional[str]       # Paper title (first message only)
    description: Optional[str] # Paper summary (first message only)
    answer: Optional[str]      # Response to user's question
```

#### Paper Processing Flow

```
paper_id
    │
    ▼
get_markdown_of_paper(paper_id)
    │
    ├── get_parsed_from_s3()     # Fetch JSON from S3
    │       │
    │       ▼
    │   {bucket}/{prefix}/raw/{paper_id}.json
    │
    └── convert_to_markdown()     # Convert to LLM-friendly format
            │
            ├── element_to_markdown()   # Handle each element type
            │       - Title → # heading
            │       - Header → ## heading
            │       - Table → markdown table
            │       - ListItem → bullet point
            │       - CodeSnippet → code block
            │       - etc.
            │
            └── Page breaks + list grouping
```

#### Exception Hierarchy

```
RASException (base)
├── PaperNotFoundError      # Paper doesn't exist in S3
├── PaperParseError         # Markdown conversion failed
└── AgentError (base)
    ├── ExpertNotFoundError     # Expert not in registry
    ├── ExpertQueryError        # LLM call failed
    └── ExpertCreationError     # Expert initialization failed
```

#### Logging Strategy

| Level | What | Example |
|-------|------|---------|
| DEBUG | High-volume operations | Query processing, S3 fetch |
| INFO | Significant events | Expert created successfully |
| ERROR | Failures | Query failed, S3 error |

Logs are JSON-formatted for CloudWatch compatibility with context fields:
- `agent`: "expert"
- `paper_id`: ArXiv ID
- `thread_id`: Expert thread identifier

#### Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `EXPERT_MODEL` | LLM model for expert | `gpt-5` |
| `BOOTSTRAP_BUCKET_NAME` | S3 bucket for papers | Required |
| `PAPERS_S3_PREFIX` | S3 prefix path | Required |
| `MONGO_URI` | MongoDB connection string | Required |

### Scout Agent

The Scout Agent is a stateless retrieval agent that searches the knowledge base and answers questions using retrieved chunks. When chunks are insufficient, it spawns Expert agents for deep paper analysis.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Scout Agent                                │
├─────────────────────────────────────────────────────────────────┤
│  State: expert_registry + retrieval_count + seen_paper_ids       │
│  Memory: None (stateless)                                        │
│  Model: GPT-5 with reasoning effort: medium                      │
└─────────────────────────────────────────────────────────────────┘
          │
          │ query(question)
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Tools:                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  sample_chunks   │  │  query_paper     │  │  search_paper  │ │
│  │  - Broad search  │  │  - Specific paper│  │  - Find by     │ │
│  │  - top_k=50→3/ppr│  │  - By arxiv_id   │  │    title/kw    │ │
│  │  - Max 3 calls   │  │  - Unlimited     │  │  - Returns IDs │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  spawn_and_ask                                            │   │
│  │  - Creates Expert for paper_id, queries with question     │   │
│  │  - Updates expert_registry                                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Response:                                                       │
│  - answer: Synthesized answer with citations                     │
│  - expert_registry: Any experts spawned during answering         │
└─────────────────────────────────────────────────────────────────┘
```

#### File Structure

```
app/agents/scout/
├── __init__.py      # Module exports: query
├── main.py          # Agent initialization, tools, and public API
├── models.py        # ScoutState with expert_registry reducer
└── prompt.py        # System prompt defining agent behavior
```

#### Workflow

1. **Initial Retrieval**: Pre-retrieves 50 chunks, filters to top 3 per paper
2. **Assess Chunks**: Agent evaluates if chunks can answer the question
3. **Escalation Order**:
   - `query_paper` - Get more chunks from a seen paper (unlimited, cheap)
   - `spawn_and_ask` - Full paper context via Expert (expensive, last resort)
   - `sample_chunks` - Search for new papers (max 3 calls total)
4. **Return**: Returns answer with citations and any spawned experts

#### Retrieval Limits

To prevent infinite retrieval loops, Scout enforces:
- `MAX_RETRIEVAL_ATTEMPTS = 3` - Hard limit on `sample_chunks` calls per query
- `seen_paper_ids` - Tracks papers already retrieved, auto-excluded from future `sample_chunks`
- `query_paper` is unlimited - use for deep dives into specific papers
- After limit reached, agent must work with existing chunks or use `spawn_and_ask`

#### Usage

```python
from app.agents.scout import query

# Query the knowledge base
result = await query("What is the attention mechanism?")
# Returns: {"answer": "The attention mechanism... (2512.02942v1)", "expert_registry": {...}}
```

#### Tools

| Tool | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `sample_chunks` | Broad search across new papers (max 3 calls) | `query` | List of chunks (top 3 per paper) or limit error |
| `query_paper` | Deep dive into a specific paper (unlimited) | `arxiv_id`, `query`, `top_k=5` | List of chunks from that paper |
| `search_paper` | Find paper by title/keywords | `title_keywords` | List of {arxiv_id, title} matches |
| `spawn_and_ask` | Creates Expert for paper, asks question | `paper_id`, `question` | Answer string or Command |

#### Error Handling in spawn_and_ask

The `spawn_and_ask` tool handles errors gracefully and returns user-friendly messages:

| Error | Response |
|-------|----------|
| `PaperNotFoundError` | "Could not create expert: paper {id} not found in the knowledge base." |
| `LLMTimeoutError` | "Could not create expert for paper {id}: service temporarily unavailable." |
| `LLMRateLimitError` | "Could not create expert for paper {id}: service temporarily unavailable." |
| `ExpertCreationError` | "Could not create expert for paper {id}. The paper may be malformed." |
| `ExpertQueryError` | "Could not get answer from expert for paper {id}." |

#### State Model

```python
class ScoutState(AgentState):
    expert_registry: Annotated[Dict[str, Any], merge_dicts]
    # Maps paper_id -> {thread_id, title, description}
    retrieval_count: int
    # Tracks sample_chunks calls for limit enforcement
    seen_paper_ids: Annotated[Set[str], merge_sets]
    # Papers already retrieved, auto-excluded from sample_chunks
```

- `merge_dicts` reducer accumulates experts across tool calls
- `merge_sets` reducer accumulates seen papers for exclusion filtering
- `retrieval_count` enforces `MAX_RETRIEVAL_ATTEMPTS` limit

#### Logging Strategy

| Level | What | Example |
|-------|------|---------|
| DEBUG | High-volume operations | Chunk retrieval, reusing expert |
| INFO | Significant events | spawn_and_ask called, expert created, query completed |
| WARNING | Recoverable issues | Paper not found, rate limit hit |
| ERROR | Failures | Expert creation failed, query failed |

Logs are JSON-formatted with context fields:
- `agent`: "scout"
- `paper_id`: ArXiv ID (when applicable)
- `question_preview`: First 100 chars of question

#### Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `SCOUT_MODEL` | LLM model for Scout | `gpt-5` |

### Router Agent

The Router Agent is the central orchestrator that maintains conversation history, manages the expert registry, and routes questions to appropriate agents (Scout or existing Experts).

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Router Agent                               │
├─────────────────────────────────────────────────────────────────┤
│  State: Conversation history + expert_registry                   │
│  Memory: MongoDB (via LangGraph checkpointing)                   │
│  Model: GPT-5 with reasoning effort: medium                      │
└─────────────────────────────────────────────────────────────────┘
          │
          │ query(thread_id, query, expert_registry)
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Tools:                                                          │
│  ┌──────────────────┐  ┌────────────────────────────────────┐   │
│  │  create_expert   │  │  get_expert_registry                │   │
│  │  - Spawns Expert │  │  - Lists available experts          │   │
│  │    for paper_id  │  │  - Shows paper titles/descriptions  │   │
│  └──────────────────┘  └────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  RouterResponse (structured output):                             │
│  - answer: Final answer with citations (or None)                 │
│  - expert_questions: {paper_id: [questions]} for Experts         │
│  - scout_questions: [questions] for Scout                        │
│  - expert_registry: Updated registry                             │
└─────────────────────────────────────────────────────────────────┘
```

#### File Structure

```
app/agents/router/
├── __init__.py      # Module exports: query
├── main.py          # Agent initialization, tools, and public API
├── models.py        # RouterState and RouterResponse models
└── prompt.py        # System prompt defining routing behavior
```

#### Workflow

1. **Receive Query**: Gets user query with optional expert_registry from Scout
2. **Detect New Experts**: Compares incoming registry vs checkpointed state
3. **Notify LLM**: Appends new experts info to message if any found
4. **Route Decision**: LLM decides to ask Scout, ask Experts, or answer
5. **Return**: Structured response with routing decision or final answer

#### Usage

```python
from app.agents.router import query

# First query - no experts yet
result = await query(
    thread_id="conv-123",
    query="What is the attention mechanism?",
    expert_registry={}
)
# Returns: {"answer": None, "scout_questions": ["attention mechanism transformer"], ...}

# After Scout returns with spawned experts
result = await query(
    thread_id="conv-123",
    query="Scout found: The attention mechanism allows...",
    expert_registry={"2512.02942v1": {"thread_id": "...", "title": "Attention Is All You Need", ...}}
)
# Router now knows about the new expert
```

#### Response Model

```python
class RouterResponse(BaseModel):
    expert_questions: Optional[Dict[str, List[str]]]  # {paper_id: [questions]}
    scout_questions: Optional[List[str]]              # Questions for Scout
    answer: Optional[str]                             # Final answer (or None)
```

#### Tools

| Tool | Description | Returns |
|------|-------------|---------|
| `create_expert` | Spawns Expert for paper_id | Command or error message |
| `get_expert_registry` | Lists available experts | Formatted expert list |

#### Error Handling in create_expert

| Error | Response |
|-------|----------|
| Expert already exists | "Expert already exists for paper {id}." |
| `PaperNotFoundError` | "Could not create expert: paper {id} not found in the knowledge base." |
| `LLMTimeoutError` | "Could not create expert for paper {id}: service temporarily unavailable." |
| `ExpertCreationError` | "Could not create expert for paper {id}. The paper may be malformed." |

#### Logging Strategy

| Level | What | Example |
|-------|------|---------|
| DEBUG | Low-level operations | get_expert_registry called, expert already exists |
| INFO | Significant events | create_expert called, query processing, query completed |
| WARNING | Recoverable issues | Paper not found, rate limit hit |
| ERROR | Failures | Expert creation failed |

#### Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `ROUTER_MODEL` | LLM model for Router | `gpt-5` |
| `MONGO_URI` | MongoDB connection string | Required |

### Interface Agent

The Interface Agent is the user-facing layer that analyzes research paper paragraphs for grammar, logic, and factual accuracy.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Interface Agent                              │
├─────────────────────────────────────────────────────────────────┤
│  State: Document context (via MongoDB checkpointing)             │
│  Memory: Paragraphs + corrections history                        │
│  Model: GPT-5 with reasoning effort: low                         │
└─────────────────────────────────────────────────────────────────┘
          │
          │ query(paragraph, paragraph_index, is_update)
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Analysis:                                                       │
│  1. Grammar & Style - spelling, punctuation, academic tone       │
│  2. Logic & Flow - coherence, consistency with prev paragraphs   │
│  3. Fact Identification - claims needing literature verification │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  InterfaceResponse:                                              │
│  - grammar_corrections: List[str]                                │
│  - logic_issues: List[str]                                       │
│  - fact_questions: List[str] → sent to Router                    │
│  - answer_to_user: str (final response)                          │
└─────────────────────────────────────────────────────────────────┘
```

#### File Structure

```
app/agents/interface/
├── __init__.py      # Module exports: query
├── main.py          # Agent initialization and public API
├── models.py        # InterfaceResponse model
└── prompt.py        # System prompt for paragraph analysis
```

#### Message Format (Checkpointed)

Interface uses message-based checkpointing with prefixes:
```
Human: [NEW PARAGRAPH 0] The attention mechanism allows...
AI: {grammar_corrections: [], logic_issues: [], fact_questions: ["What accuracy..."], ...}
```

#### Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `INTERFACE_MODEL` | LLM model for Interface | `gpt-5` |

### Graph Orchestration

The Graph module coordinates all agents using LangGraph's StateGraph with conditional branching and parallel execution.

#### Architecture

```
START → interface_analyze → [branch]
                              ├── END (no fact questions)
                              └── create_router_request → router → [branch]
                                                                     ├── expert ─┐
                                                                     ├── scout ──┼→ create_router_request (loop)
                                                                     └── interface_fact_results → END
```

#### File Structure

```
app/agents/graph/
├── __init__.py      # Module exports: get_graph, analyze_paragraph, AnalysisResult
├── main.py          # StateGraph definition, nodes, and branching logic
├── model.py         # GraphState and GraphContext schemas
└── runner.py        # High-level analyze_paragraph() API
```

#### Graph State

```python
class GraphState(AgentState):
    # Interface state
    interface_thread_id: str
    interface_paragraph: Optional[str]
    interface_paragraph_index: Optional[int]
    interface_is_update: bool
    interface_grammar_corrections: List[str]
    interface_logic_issues: List[str]
    interface_fact_questions: List[str]
    interface_fact_results: List[str]

    # Router state
    router_thread_id: str
    expert_registry: Dict[str, Dict[str, Any]]
    expert_questions: Dict[str, List[str]]
    expert_answers: Dict[str, str]
    scout_questions: List[str]
    scout_answers: List[str]
    router_questions: List[str]
    router_incoming_answers: List[str]
    router_final_answer: Optional[str]
```

#### Checkpointing

- `conversation_id` is used as the graph's `thread_id` for checkpointing
- `interface_thread_id` and `router_thread_id` are stored in graph state checkpoint
- On first invocation: new UUIDs are generated for thread IDs
- On subsequent invocations: thread IDs are retrieved from checkpoint

#### Usage

```python
from app.agents.graph import analyze_paragraph
from app.services.conversations import ConversationService

conversation = conversation_service.create()
result = await analyze_paragraph(
    conversation=conversation,
    paragraph="Your text here...",
    paragraph_index=0,
)
# Returns: AnalysisResult with grammar_corrections, logic_issues, fact_results
```

---

## FastAPI Application

The application exposes a REST API for managing conversations and analyzing paragraphs.

### Project Structure

```
app/
├── main.py                    # FastAPI app factory with lifespan
├── api/
│   ├── __init__.py
│   ├── dependencies.py        # Dependency injection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── analysis.py        # AnalyzeRequest, AnalyzeResponse
│   │   └── conversations.py   # ConversationResponse, ConversationCreateResponse
│   └── routes/
│       ├── __init__.py        # Router aggregation
│       ├── analysis.py        # POST /api/v1/analyze
│       ├── conversations.py   # CRUD /api/v1/conversations
│       └── health.py          # Health checks
├── models/
│   ├── __init__.py
│   └── conversation.py        # Conversation document model
├── services/
│   └── conversations/
│       ├── __init__.py
│       └── service.py         # ConversationService
└── core/
    └── lifespan.py            # Application lifecycle management
```

### Conversation Model

```python
@dataclass
class Conversation:
    conversation_id: str   # Also used as graph thread_id
    created_at: datetime
    updated_at: datetime
```

Note: `interface_thread_id` and `router_thread_id` are NOT stored in the conversation document. They are stored in the graph state checkpoint.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/conversations` | Create new conversation |
| GET | `/api/v1/conversations/{id}` | Get conversation by ID |
| DELETE | `/api/v1/conversations/{id}` | Delete conversation |
| POST | `/api/v1/analyze` | Analyze paragraph |
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/ready` | Readiness check |

### Lifecycle Management

The `lifespan.py` module manages singleton services:

```python
# Singletons initialized at startup
_mongo_client: MongoClient
_checkpointer: MongoDBSaver
_retrieval_service: RetrievalService
_conversation_service: ConversationService

# Getter functions for dependency injection
def get_checkpointer() -> MongoDBSaver
def get_retrieval_service() -> RetrievalService
def get_conversation_service() -> ConversationService
```

### Running the Application

```bash
uvicorn app.main:app --reload
```

### Example API Usage

```bash
# Create conversation
curl -X POST http://localhost:8000/api/v1/conversations

# Analyze paragraph
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "paragraph": "Your text here...",
    "paragraph_index": 0
  }'

# Continue with same conversation
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "paragraph": "Next paragraph...",
    "paragraph_index": 1,
    "conversation_id": "<id from previous response>"
  }'
```