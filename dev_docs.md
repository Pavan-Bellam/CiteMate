# Developer Documentation

## Project Structure

```
ras/
├── config.json          # Project configuration
├── setup.py             # Setup and deployment scripts
├── assume_role.py       # Assume developer role (get temp credentials)
├── terraform/
│   ├── bootstrap/       # One-time setup (S3 bucket, IAM roles)
│   ├── modules/
│   │   ├── storage/     # S3 folder creation
│   │   ├── ecr/         # ECR repository + push policy
│   │   ├── sqs/         # SQS queue + DLQ
│   │   ├── redis/       # Upstash Redis database
│   │   ├── ecs/         # ECS cluster + task definitions
│   │   └── ssm/         # SSM Parameter Store secrets
│   └── envs/
│       └── development/ # Environment-specific config
└── ingestion/
    ├── producer/        # ArXiv paper fetcher
    └── consumer/        # PDF parser, chunker, embedder
```

## Configuration

`config.json` in root (copy from `config.example.json`):
```json
{
  "project_name": "ras",
  "aws_region": "us-east-1",
  "aws_account_id": "YOUR_ACCOUNT_ID",
  "username": "YOUR_IAM_USERNAME",
  "bootstrap": {
    "bucket_name": "YOUR_BUCKET_NAME"
  }
}
```

Set `username` to your IAM username before running local setup.


## Infrastructure

### Terraform Structure

#### bootstrap/

Run once by an admin to create shared infrastructure. Uses local state (not remote).

**Files:**
- `main.tf` - AWS provider config with default tags (Project, Environment=bootstrap)
- `versions.tf` - Requires Terraform >= 1.5.0, AWS provider >= 6.0.0
- `variables.tf` - Input variables (project_name, aws_region, aws_account_id, bucket_name)
- `s3.tf` - Creates the shared S3 bucket with versioning enabled
- `iam.tf` - Creates developer role, policies, and group
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

#### modules/storage/

Creates S3 folder objects under a given prefix.

**Files:**
- `s3.tf` - Creates empty S3 objects as folder placeholders
- `variables.tf` - bucket_name, prefix, folders (list)
- `outputs.tf` - folder_keys, bucket_name

**Usage:**
```hcl
module "storage" {
  source      = "../../modules/storage"
  bucket_name = var.bucket_name
  prefix      = "development/${var.developer}"
  folders     = ["papers", "models"]
}
```

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
- `storage` - Creates folders under `development/{developer}/`
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

#### Staging Environment

Deploy staging infrastructure with ECS, SSM secrets, and all supporting resources.

**Prerequisites:**

1. Create `config.staging.json` (copy from `config.json`):
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
   - S3 folders under `staging/papers/`
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
│   ├── openai_client.py # Embedding generation
│   ├── pinecone_client.py # Vector storage
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
3. When token threshold reached: embed batch → store in Pinecone
4. Flush remaining chunks at end

**Full mode:**
Combines parse and process in one continuous pipeline.

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
| `PINECONE_INDEX_NAME` | Pinecone index name | `ras-papers` |
| `EMBEDDING_DIMENSION` | Embedding vector dimension | `3072` |

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