import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, collection_name: str = "repo_code_chunks"):
        self.collection_name = collection_name
        self.vector_size = 384  # Standard size for BAAI/bge-small-en or miniLM

        # Initialize Qdrant Client (in-memory or networked)
        if settings.qdrant_url == ":memory:":
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key or None,
            )

        self._embedder = None
        self._init_collection()

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from fastembed import TextEmbedding
                self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            except Exception as e:
                logger.warning(f"FastEmbed not loaded, using fallback embedding: {e}")
                self._embedder = "fallback"
        return self._embedder

    def _compute_embeddings(self, texts: list[str]) -> list[list[float]]:
        embedder = self._get_embedder()
        if embedder != "fallback" and embedder is not None:
            return [list(vector) for vector in embedder.embed(texts)]

        # Simple deterministic hash-based fallback embedding if fastembed is absent
        embeddings = []
        for text in texts:
            vec = [0.0] * self.vector_size
            for idx, char in enumerate(text[: self.vector_size]):
                vec[idx % self.vector_size] += (ord(char) % 31) / 31.0
            # normalize
            norm = sum(x**2 for x in vec) ** 0.5 or 1.0
            embeddings.append([x / norm for x in vec])
        return embeddings

    def _init_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
        except Exception as e:
            logger.error(f"Error initializing Qdrant collection: {e}")

    def add_chunks(self, chunks: list[dict[str, Any]]):
        """
        Adds code or document chunks to Qdrant.
        Each chunk must have 'text' and optional 'metadata'.
        """
        if not chunks:
            return

        texts = [c["text"] for c in chunks]
        vectors = self._compute_embeddings(texts)
        points = []

        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            import uuid
            point_id = chunk.get("id") or str(uuid.uuid4())
            payload = {
                "text": chunk["text"],
                **(chunk.get("metadata") or {})
            }
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def search(self, query: str, limit: int = 5, filter_dict: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Semantic search for similar code, past comments, or learnings.
        """
        try:
            query_vector = self._compute_embeddings([query])[0]
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=limit,
                )
                hits = response.points
            elif hasattr(self.client, "search"):
                hits = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=limit,
                )
            else:
                hits = []

            return [
                {
                    "score": getattr(hit, "score", 1.0),
                    "payload": getattr(hit, "payload", {}),
                    "id": getattr(hit, "id", ""),
                }
                for hit in hits
            ]
        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []
