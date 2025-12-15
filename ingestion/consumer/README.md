# Consumer

Processes papers from SQS, parses PDFs using Unstructured API, and chunks them for embedding.

## Modes

```bash
python main.py parse    # SQS -> parse PDF -> save raw to S3
python main.py process  # Load raw from S3 -> chunk all papers
python main.py full     # Both (default)
```

## Quick Start

```powershell
# From project root
python assume_role.py | Invoke-Expression
python run.py consumer build
python run.py consumer up [mode]
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `BUCKET_NAME` | S3 bucket name |
| `BUCKET_PREFIX` | S3 key prefix (e.g., `development/user/papers`) |
| `QUEUE_URL` | SQS queue URL |
| `UNSTRUCTURED_API_KEY` | Unstructured API key |
| `CHUNK_MAX_CHARACTERS` | Max chunk size (default: 1500) |
| `CHUNK_NEW_AFTER_N_CHARS` | Soft limit for new chunk (default: 1000) |
| `CHUNK_COMBINE_UNDER_N_CHARS` | Combine small chunks (default: 500) |
| `MODE` | Consumer mode: parse, process, full |

## S3 Structure

```
{BUCKET_PREFIX}/
├── pdfs/{arxiv_id}.pdf  # From producer
└── raw/{arxiv_id}.json  # Parsed elements (from consumer)
```

## Experimentation

1. Parse papers once: `python run.py consumer up parse`
2. Tweak chunking params in `config.json`
3. Re-process: `python run.py consumer up process`
4. Repeat as needed - no re-parsing required
