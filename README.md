# Research Assistant System (RAS)

A multi-agent AI system that helps researchers write better academic papers by providing real-time feedback, literature discovery, and intelligent Q&A.

## Features

- **Writing Corrections** - Grammar, style, and logical consistency checks
- **Literature Support** - Finds supporting evidence and opposing viewpoints from indexed papers
- **Research Chatbot** - Answers questions with citations from the paper corpus

## Architecture

```
User → Interface Agent → Router Agent → Scout Agent → Expert Agents
                                              ↓
                                     Pinecone (Hybrid Search)
```

| Agent | Role |
|-------|------|
| **Interface** | Analyzes paragraphs for grammar, logic, and facts needing verification |
| **Router** | Orchestrates queries between agents, manages expert registry |
| **Scout** | Retrieves chunks via hybrid search, spawns experts when needed |
| **Expert** | Deep Q&A on a specific paper (one expert per paper) |

## Prerequisites

- Python 3.12+
- MongoDB (for agent checkpointing)
- Terraform 1.5+ (for infrastructure)
- AWS CLI configured

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure Environment

Create a `.env` file:
```
OPENAI_API_KEY=sk-xxx
PINECONE_API_KEY=xxx
MONGO_URI=mongodb://localhost:27017
BOOTSTRAP_BUCKET_NAME=your-bucket
PAPERS_S3_PREFIX=development/your-username/papers
```

### 3. Run the Application

```bash
uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/conversations` | Create new conversation |
| GET | `/api/v1/conversations/{id}` | Get conversation |
| DELETE | `/api/v1/conversations/{id}` | Delete conversation |
| POST | `/api/v1/analyze` | Analyze a paragraph |
| GET | `/api/v1/health` | Health check |

### Example Usage

```bash
# Create conversation
curl -X POST http://localhost:8000/api/v1/conversations

# Analyze paragraph
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "paragraph": "The attention mechanism allows models to focus on relevant parts of the input.",
    "paragraph_index": 0,
    "conversation_id": "<id>"
  }'
```

## Infrastructure Setup

### Bootstrap (Admin)

```powershell
python setup.py bootstrap init
python setup.py bootstrap apply
aws iam add-user-to-group --group-name ras-developers --user-name {username}
```

### Dev Environment

```powershell
$env:UPSTASH_EMAIL = "your-email"
$env:UPSTASH_API_KEY = "your-api-key"

python assume_role.py | Invoke-Expression
python setup.py dev init
python setup.py dev apply
```

## Ingestion Pipeline

The pipeline indexes papers into Pinecone for retrieval:

```powershell
# Producer: Fetch papers from ArXiv → S3 → SQS
python run.py producer up

# Consumer: Parse PDFs → chunk → embed → Pinecone
python run.py consumer up
```

| Mode | Description |
|------|-------------|
| `parse` | Parse PDFs, save raw elements to S3 |
| `process` | Chunk, embed, store to Pinecone |
| `full` | Both (default) |

## CI/CD

| Branch | Environment |
|--------|-------------|
| `main` | Staging |
| `prod` | Production |

GitHub Secrets required:
- `OPENAI_API_KEY`
- `PINECONE_API_KEY`
- `UNSTRUCTURED_API_KEY`
- `UPSTASH_EMAIL` / `UPSTASH_API_KEY`

## Documentation

See [dev_docs.md](dev_docs.md) for detailed documentation:
- Multi-agent implementation details
- Terraform infrastructure
- Retrieval service configuration
- Evaluation results
