import os
import pickle
from typing import List, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(BASE_DIR, "data", "data.txt")

VECTOR_STORE_DIR = os.path.join(BASE_DIR, "vector_store")
FAISS_INDEX_PATH = os.path.join(VECTOR_STORE_DIR, "index.faiss")
PKL_PATH = os.path.join(VECTOR_STORE_DIR, "index.pkl")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 150
OVERLAP = 30


def load_text(path: str = DATA_PATH) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"data.txt not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def chunk_text(text: str) -> List[str]:
    words = text.split()
    chunks = []

    step = CHUNK_SIZE - OVERLAP

    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        if len(chunk) > 20:
            chunks.append(chunk)

    return chunks


def get_model():
    return SentenceTransformer(EMBEDDING_MODEL)


def embed(chunks: List[str], model):
    return model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype(np.float32)


def build_index(embeddings):
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index


def save(index, chunks):
    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
    faiss.write_index(index, FAISS_INDEX_PATH)

    with open(PKL_PATH, "wb") as f:
        pickle.dump(chunks, f)


def load():
    index = faiss.read_index(FAISS_INDEX_PATH)

    with open(PKL_PATH, "rb") as f:
        chunks = pickle.load(f)

    return index, chunks


def build_and_save():
    text = load_text()
    chunks = chunk_text(text)
    model = get_model()
    emb = embed(chunks, model)
    index = build_index(emb)

    save(index, chunks)

    return index, chunks, model


def retrieve(query, index, chunks, model, top_k=5):
    q = model.encode([query], normalize_embeddings=True).astype(np.float32)

    scores, idx = index.search(q, top_k)

    results = []
    for s, i in zip(scores[0], idx[0]):
        if i != -1 and s > 0.2:
            results.append((chunks[i], float(s)))

    return results