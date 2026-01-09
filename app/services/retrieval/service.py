import os
import time
import asyncio
import logging
from enum import Enum
from functools import wraps
from langsmith.wrappers import wrap_openai
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from pinecone import PineconeAsyncio

from pinecone_text.sparse import BM25Encoder
from openai import AsyncOpenAI

logger = logging.getLogger("retrieval_service")


def retry_on_api_error(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator to retry API calls with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {delay:.1f}s"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator


class RetrievalMode(str, Enum):
    SEMANTIC = "semantic"
    BM25 = "bm25"
    HYBRID = "hybrid"


class RetrievalService:
    """Service for retrieving relevant documents from Pinecone using semantic, BM25, or hybrid search."""

    def __init__(self):
        logger.info("Initializing RetrievalService")

        # Pinecone
        self.pc = PineconeAsyncio(api_key=os.environ["PINECONE_API_KEY"])
        self.dense_index = self.pc.IndexAsyncio(host=os.environ["DENSE_INDEX_URL"])
        self.sparse_index = self.pc.IndexAsyncio(host=os.environ["SPARSE_INDEX_URL"])

        # OpenAI
        self.openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-large")
        self.openai = wrap_openai(self.openai_client)

        # BM25
        bm25_path = os.environ.get("BM25_ENCODER_PATH", "bm25_encoder.json")
        print(f"bm25_path: {bm25_path}")
        if not os.path.exists(bm25_path):
            raise FileNotFoundError(f"BM25 encoder not found: {bm25_path}")
        self.bm25 = BM25Encoder().load(bm25_path)

        # Retrieval config
        self.default_mode = RetrievalMode(os.environ.get("DEFAULT_MODE", "hybrid"))
        self.top_k = int(os.environ.get("TOP_K", "10"))
        self.rrf_k = int(os.environ.get("RRF_K", "60"))

        # Reranking config
        self.rerank_enabled = os.environ.get("RERANK_ENABLED", "true").lower() == "true"
        self.rerank_model = os.environ.get("RERANK_MODEL", "bge-reranker-v2-m3")
        self.rerank_top_n = int(os.environ.get("RERANK_TOP_N", "10"))

        logger.info(f"RetrievalService initialized (mode={self.default_mode.value}, rerank={self.rerank_enabled})")
    
    @traceable(name="Get Embedding", run_type="embedding")
    @retry_on_api_error(max_retries=3, base_delay=1.0)
    async def _get_embedding(self, text: str) -> list[float]:
        """Get dense embedding for text."""
        response = await self.openai.embeddings.create(input=text, model=self.embedding_model)
        return response.data[0].embedding

    @traceable(name="Get Sparse Vector", run_type="embedding")
    def _get_sparse_vector(self, text: str) -> dict:
        """Get sparse BM25 vector for text."""
        return self.bm25.encode_queries(text)

    def _extract_arxiv_id(self, chunk_id: str) -> str | None:
        """Extract arxiv_id from chunk_id format: {arxiv_id}_{chunk_number}."""
        parts = chunk_id.rsplit("_", 1)
        return parts[0] if len(parts) > 1 else None

    def _rank_fusion(self, dense_ids: list[str], sparse_ids: list[str]) -> list[str]:
        """Reciprocal Rank Fusion (RRF) to merge two ranked lists."""
        scores = {}
        for rank, doc_id in enumerate(dense_ids):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (self.rrf_k + rank + 1)
        for rank, doc_id in enumerate(sparse_ids):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (self.rrf_k + rank + 1)
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_id for doc_id, _ in sorted_docs]

    @traceable(name="Query Dense Index", run_type="retriever")
    @retry_on_api_error(max_retries=3, base_delay=1.0)
    async def _query_dense(self, query: str, top_k: int, include_metadata: bool = True) -> list:
        """Query dense index."""
        embedding = await self._get_embedding(query)
        results = await self.dense_index.query(
            vector=embedding, top_k=top_k, include_metadata=include_metadata
        )
        return results.matches

    @traceable(name="Query Sparse Index", run_type="retriever")
    @retry_on_api_error(max_retries=3, base_delay=1.0)
    async def _query_sparse(self, query: str, top_k: int, include_metadata: bool = True) -> list:
        """Query sparse index."""
        sparse_vec = self._get_sparse_vector(query)
        results = await self.sparse_index.query(
            sparse_vector={"indices": sparse_vec["indices"], "values": sparse_vec["values"]},
            top_k=top_k,
            include_metadata=include_metadata,
        )
        return results.matches
    
    def _dedup_results(self, dense_vectors: list, sparse_vectors: list) -> list:
        """Deduplicate results from dense and sparse vectors."""
        results = []
        seen_ids = set()
        
        # Interleave results
        for i in range(max(len(dense_vectors), len(sparse_vectors))):
            if i < len(dense_vectors):
                dv = dense_vectors[i]
                if dv.id not in seen_ids:
                    results.append(dv)
                    seen_ids.add(dv.id)
            
            if i < len(sparse_vectors):
                sv = sparse_vectors[i]
                if sv.id not in seen_ids:
                    results.append(sv)
                    seen_ids.add(sv.id)
                    
        return results

    @traceable(name="Rerank Candidates", run_type="tool")
    # @retry_on_api_error(max_retries=3, base_delay=1.0)
    async def _rerank(self, query: str, candidates: list, top_n: int) -> list:
        """Rerank candidates using Pinecone reranking."""
        
        # Extract text from candidates (assuming metadata has 'text' field)
        docs = [c.metadata.get("text", "") for c in candidates]

        rerank_kwargs = {
            "model": self.rerank_model,
            "query": query,
            "documents": docs,
            "top_n": top_n,
            "return_documents": False,
        }
        if self.rerank_model not in ("cohere-rerank-3.5",):
            rerank_kwargs["parameters"] = {"truncate": "END"}

        reranked = await self.pc.inference.rerank(**rerank_kwargs)
        
        # Map back to original candidates using index
        results = []
        for r in reranked.data:
            candidate = candidates[r.index]
            results.append({
                "id": candidate.id,
                "score": r.score,
                "arxiv_id": candidate.metadata.get("arxiv_id") or self._extract_arxiv_id(candidate.id),
                "metadata": candidate.metadata,
            })
            
        return results

    @traceable(name="Retrieve", run_type="chain")
    async def retrieve(
        self,
        query: str,
        mode: RetrievalMode | str | None = None,
        top_k: int | None = None,
        rerank: bool | None = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks from Pinecone.

        Args:
            query: Search query.
            mode: Retrieval mode (semantic, bm25, hybrid). Defaults to config.
            top_k: Number of results. Defaults to config.
            rerank: Whether to rerank results. Defaults to config.

        Returns:
            List of matching documents with id, score, and metadata.
        """
        mode = RetrievalMode(mode) if mode else self.default_mode
        top_k = top_k or self.top_k
        rerank = rerank if rerank is not None else self.rerank_enabled

        # Trace attributes for this query
        run = get_current_run_tree()
        model_full_name = f"{mode.value}"
        run.metadata['mode'] = mode.value
        run.metadata['top_k'] = top_k
        run.metadata['rerank'] = rerank
        run.metadata['embedding_model'] = self.embedding_model
        if self.rerank_enabled:
            run.metadata['rerank_top_n'] = self.rerank_top_n
            run.metadata['rerank_model'] = self.rerank_model
            run.metadata['rrf_k'] = self.rrf_k
            model_full_name += f"-rerank-{self.rerank_model}"
            
        run.metadata['model_full_name'] = model_full_name

        logger.debug(f"Retrieve: mode={mode.value}, top_k={top_k}, rerank={rerank}")

        # For reranking, fetch more candidates initially
        initial_k = 20 if rerank else top_k

        dense_matches = []
        sparse_matches = []
        
        # Parallelize queries
        tasks = []
        if mode in (RetrievalMode.SEMANTIC, RetrievalMode.HYBRID):
            tasks.append(self._query_dense(query, initial_k))
        else:
            tasks.append(asyncio.sleep(0)) # Placeholder

        if mode in (RetrievalMode.BM25, RetrievalMode.HYBRID):
            tasks.append(self._query_sparse(query, initial_k))
        else:
            tasks.append(asyncio.sleep(0)) # Placeholder
            
        results_list = await asyncio.gather(*tasks)
        
        if mode in (RetrievalMode.SEMANTIC, RetrievalMode.HYBRID):
            dense_matches = results_list[0] if isinstance(results_list[0], list) else []
        if mode in (RetrievalMode.BM25, RetrievalMode.HYBRID):
            sparse_matches = results_list[1] if isinstance(results_list[1], list) else []

        # Process results
        if rerank:
            # Build candidates dict for reranking
            candidates = self._dedup_results(dense_matches, sparse_matches)

            if not candidates:
                return []

            reranked_result = await self._rerank(query, candidates, self.rerank_top_n)
            return reranked_result

        else:
            # Non-reranked path
            if mode == RetrievalMode.SEMANTIC:
                matches = dense_matches
            elif mode == RetrievalMode.BM25:
                matches = sparse_matches
            else:  # HYBRID
                # Optimize Rank Fusion
                dense_map = {m.id: m for m in dense_matches}
                sparse_map = {m.id: m for m in sparse_matches}
                
                dense_ids = [m.id for m in dense_matches]
                sparse_ids = [m.id for m in sparse_matches]
                
                fused_ids = self._rank_fusion(dense_ids, sparse_ids)[:top_k]
                
                results = []
                for doc_id in fused_ids:
                    # Prefer dense match for score/metadata if available, else sparse
                    m = dense_map.get(doc_id) or sparse_map.get(doc_id)
                    if m:
                        results.append({
                            "id": m.id,
                            "score": m.score, # Note: This score is from the original retrieval, not RRF score
                            "arxiv_id": m.metadata.get("arxiv_id") or self._extract_arxiv_id(m.id),
                            "metadata": m.metadata,
                        })
                return results

            # Semantic or BM25 only
            return [
                {
                    "id": m.id,
                    "score": m.score,
                    "arxiv_id": m.metadata.get("arxiv_id") or self._extract_arxiv_id(m.id),
                    "metadata": m.metadata,
                }
                for m in matches[:top_k]
            ]
            
    async def close(self):
        await self.dense_index.close()
        await self.sparse_index.close()