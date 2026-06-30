"""Embedding utilities — encode text and compute similarity for pre-filtering."""
import numpy as np
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")

SIMILARITY_THRESHOLD = 0.25  # jobs below this are skipped before Claude


def embed(text: str) -> bytes:
    """Return a normalised embedding as raw bytes (for SQLite BLOB storage)."""
    vector = _model.encode(text, normalize_embeddings=True)
    return vector.astype(np.float32).tobytes()


def cosine_similarity(a_bytes: bytes, b_bytes: bytes) -> float:
    """Cosine similarity between two stored embeddings.
    Both are normalised, so dot product == cosine similarity."""
    a = np.frombuffer(a_bytes, dtype=np.float32)
    b = np.frombuffer(b_bytes, dtype=np.float32)
    return float(np.dot(a, b))


def is_relevant(job_embedding: bytes, cv_embedding: bytes) -> bool:
    """Return True if the job is similar enough to the CV to be worth rating."""
    return cosine_similarity(job_embedding, cv_embedding) >= SIMILARITY_THRESHOLD
