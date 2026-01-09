import argparse
import logging
import os

from src import (
    S3Client,
    SQSClient,
    UnstructuredClient,
    RedisClient,
    ChunkData,
    OpenAIClient,
    PineconeClient,
    BM25Client,
    setup_logging,
)

logger = logging.getLogger(__name__)


def parse_paper(
    arxiv_id: str,
    s3_client: S3Client,
    unstructured_client: UnstructuredClient,
) -> list[dict]:
    """Parse a PDF and save raw elements to S3."""
    with s3_client.download_pdf(arxiv_id) as pdf_path:
        elements = unstructured_client.parse_pdf(pdf_path)
        logger.info(f"Parsed {arxiv_id}: {len(elements)} elements")

    s3_client.save_raw_elements(arxiv_id, elements)
    logger.info(f"Saved raw elements for {arxiv_id}")
    return elements


def embed_and_store(
    redis_client: RedisClient,
    openai_client: OpenAIClient,
    pinecone_client: PineconeClient,
    bm25_client: BM25Client,
) -> dict:
    """Pop chunks from Redis, embed (dense + sparse), and store in Pinecone."""
    chunks = redis_client.pop_batch()
    if not chunks:
        return {"dense": 0, "sparse": 0}

    texts = [c.text for c in chunks]

    # Generate dense embeddings (OpenAI)
    embeddings = openai_client.embed_texts(texts)

    # Generate sparse vectors (BM25)
    sparse_vectors = bm25_client.encode_documents(texts)

    ids = [f"{c.arxiv_id}_{c.chunk_index}" for c in chunks]
    metadatas = [
        {
            "arxiv_id": c.arxiv_id,
            "chunk_index": c.chunk_index,
            "text": c.text,
            **c.metadata,
        }
        for c in chunks
    ]

    result = pinecone_client.upsert_vectors(ids, embeddings, metadatas, sparse_vectors)
    logger.info(f"Embedded and stored {result['dense']} dense, {result['sparse']} sparse vectors")
    return result


def process_paper(
    arxiv_id: str,
    elements: list[dict],
    unstructured_client: UnstructuredClient,
    redis_client: RedisClient,
    openai_client: OpenAIClient,
    pinecone_client: PineconeClient,
    bm25_client: BM25Client,
) -> list[dict]:
    """Chunk elements, push to Redis, embed when threshold reached."""
    chunks = unstructured_client.chunk_elements(elements)
    logger.info(f"Chunked {arxiv_id}: {len(chunks)} chunks")

    for i, chunk in enumerate(chunks):
        chunk_data = ChunkData(
            arxiv_id=arxiv_id,
            chunk_index=i,
            text=chunk["text"],
            token_count=chunk["metadata"]["estimated_tokens"],
            metadata=chunk["metadata"],
        )
        redis_client.push_chunk(chunk_data)

        if redis_client.should_embed():
            embed_and_store(redis_client, openai_client, pinecone_client, bm25_client)

    return chunks


def run_parse(
    sqs_client: SQSClient,
    s3_client: S3Client,
    unstructured_client: UnstructuredClient,
) -> None:
    """Parse mode: consume from SQS, parse PDFs, save raw elements to S3."""
    logger.info("Running in PARSE mode - polling for messages...")

    while True:
        message = sqs_client.receive_message()

        if message is None:
            logger.debug("No messages, continuing to poll...")
            continue

        arxiv_id = message["body"]["arxiv_id"]
        logger.info(f"Processing {arxiv_id}")

        try:
            parse_paper(arxiv_id, s3_client, unstructured_client)
            sqs_client.delete_message(message["receipt_handle"])
            logger.info(f"Completed {arxiv_id}")
        except Exception as e:
            logger.error(f"Failed to process {arxiv_id}: {e}")


def run_process(
    s3_client: S3Client,
    unstructured_client: UnstructuredClient,
    redis_client: RedisClient,
    openai_client: OpenAIClient,
    pinecone_client: PineconeClient,
    bm25_client: BM25Client,
) -> None:
    """Process mode: load raw elements from S3, chunk, embed, store."""
    logger.info("Running in PROCESS mode - loading all raw elements from S3...")

    arxiv_ids = s3_client.list_raw_arxiv_ids()

    for arxiv_id in arxiv_ids:
        try:
            elements = s3_client.load_raw_elements(arxiv_id)
            if elements is None:
                logger.warning(f"No raw elements found for {arxiv_id}")
                continue

            process_paper(
                arxiv_id,
                elements,
                unstructured_client,
                redis_client,
                openai_client,
                pinecone_client,
                bm25_client,
            )
            logger.info(f"Completed {arxiv_id}")
        except Exception as e:
            logger.error(f"Failed to process {arxiv_id}: {e}")

    # Flush any remaining chunks
    remaining = redis_client.get_pending_count()
    if remaining > 0:
        logger.info(f"Flushing {remaining} remaining chunks")
        embed_and_store(redis_client, openai_client, pinecone_client, bm25_client)

    logger.info("Process mode completed")


def run_full(
    sqs_client: SQSClient,
    s3_client: S3Client,
    unstructured_client: UnstructuredClient,
    redis_client: RedisClient,
    openai_client: OpenAIClient,
    pinecone_client: PineconeClient,
    bm25_client: BM25Client,
) -> None:
    """Full mode: parse, chunk, embed, store in one pipeline."""
    logger.info("Running in FULL mode - polling for messages...")

    while True:
        message = sqs_client.receive_message()

        if message is None:
            logger.debug("No messages, continuing to poll...")
            # Flush any pending chunks while waiting
            if redis_client.get_pending_count() > 0:
                embed_and_store(redis_client, openai_client, pinecone_client, bm25_client)
            continue

        arxiv_id = message["body"]["arxiv_id"]
        logger.info(f"Processing {arxiv_id}")

        try:
            elements = parse_paper(arxiv_id, s3_client, unstructured_client)
            process_paper(
                arxiv_id,
                elements,
                unstructured_client,
                redis_client,
                openai_client,
                pinecone_client,
                bm25_client,
            )
            sqs_client.delete_message(message["receipt_handle"])
            logger.info(f"Completed {arxiv_id}")
        except Exception as e:
            logger.error(f"Failed to process {arxiv_id}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAS Consumer")
    parser.add_argument(
        "mode",
        choices=["parse", "process", "full"],
        help="parse: SQS -> parse -> S3 | process: S3 -> chunk -> embed -> Pinecone | full: all",
    )
    args = parser.parse_args()

    setup_logging()

    s3_client = S3Client(
        bucket_name=os.environ["BUCKET_NAME"],
        prefix=os.environ["BUCKET_PREFIX"],
    )
    unstructured_client = UnstructuredClient(
        api_key=os.environ["UNSTRUCTURED_API_KEY"],
        chunk_max_characters=int(os.environ.get("CHUNK_MAX_CHARACTERS", "1500")),
        chunk_new_after_n_chars=int(os.environ.get("CHUNK_NEW_AFTER_N_CHARS", "1000")),
        chunk_combine_under_n_chars=int(os.environ.get("CHUNK_COMBINE_UNDER_N_CHARS", "500")),
    )

    if args.mode == "parse":
        sqs_client = SQSClient(queue_url=os.environ["QUEUE_URL"])
        run_parse(sqs_client, s3_client, unstructured_client)
    else:
        # process and full modes need Redis, OpenAI, Pinecone, BM25
        redis_client = RedisClient(
            url=os.environ["REDIS_URL"],
            token_threshold=int(os.environ.get("EMBEDDING_TOKEN_THRESHOLD", "8000")),
        )
        openai_client = OpenAIClient(
            api_key=os.environ["OPENAI_API_KEY"],
            model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        pinecone_client = PineconeClient(
            api_key=os.environ["PINECONE_API_KEY"],
            index_name=os.environ["PINECONE_INDEX_NAME"],
        )
        bm25_client = BM25Client()

        if args.mode == "process":
            run_process(
                s3_client,
                unstructured_client,
                redis_client,
                openai_client,
                pinecone_client,
                bm25_client,
            )
        else:
            sqs_client = SQSClient(queue_url=os.environ["QUEUE_URL"])
            run_full(
                sqs_client,
                s3_client,
                unstructured_client,
                redis_client,
                openai_client,
                pinecone_client,
                bm25_client,
            )


if __name__ == "__main__":
    main()
