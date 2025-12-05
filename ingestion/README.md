# Ingestion

Ingests ArXiv papers into the vector database for semantic search.

## Pipeline

```
ArXiv API → Download PDFs → S3 → SQS → Process → Embeddings → Pinecone
```

## Components

### Producer

Fetches paper metadata from ArXiv, downloads PDFs, and uploads to S3.

- Runs nightly to fetch papers submitted the previous day
- Rate limited to 20 requests/minute (ArXiv limit)
- Skips papers already in S3 (deduplication)
- Retries failed downloads with exponential backoff

### Consumer

*Coming soon*

## Running Locally

```bash
cd producer
uv sync
uv run python main.py
```

## Running Tests

```bash
cd producer
uv run pytest -v
```
