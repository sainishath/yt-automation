# -*- coding: utf-8 -*-
"""
ingest_global_history.py
------------------------
Batch ingestion and vectorization engine for Pipeline 1 (Chronos Shift).
Expands Qdrant collection 'history_visual_rag' across diverse global civilizational domains:
- East Asia: Three Kingdoms, Tang, Song, Ming/Qing, Sengoku/Edo Japan, Mongol Empire
- South Asia: Maurya, Gupta, Mughal, Chola, Vijayanagara
- Africa: Mali, Kush/Nubia, Songhai, Aksum, Great Zimbabwe, Benin, Carthage
- Pre-Columbian Americas: Aztec/Tenochtitlan, Maya, Inca/Tahuantinsuyu, Olmec, Cahokia
- Middle East & Islamic Golden Age: Abbasid Caliphate, Umayyad Cordoba, Ottoman, Byzantine, Persia
- Classical & Modern Turning Points: Alexandria, Rome, Renaissance, Industrial Revolution, Waterloo
"""

import os
import sys
import uuid
import json
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest_models
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COLLECTION_NAME = "history_visual_rag"
VECTOR_DIM = 384
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        break_pos = text.rfind(". ", start, end)
        if break_pos == -1 or break_pos < start + (chunk_size // 2):
            break_pos = text.rfind(" ", start, end)
        if break_pos == -1:
            break_pos = end
        else:
            break_pos += 1
        chunk = text[start:break_pos].strip()
        if chunk:
            chunks.append(chunk)
        start = break_pos - overlap if (break_pos - overlap) > start else break_pos
    return chunks

def load_corpus_from_json(json_path: Path) -> List[Dict[str, Any]]:
    if not json_path.exists():
        return []
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_raw_files_from_dir(dir_path: Path) -> List[Dict[str, Any]]:
    documents = []
    if not dir_path.exists():
        return documents
    for fpath in dir_path.glob("*.txt"):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if len(content) > 200:
                doc_name = fpath.stem.replace("_", " ").title()
                documents.append({
                    "title": f"Historical Archive: {doc_name}",
                    "region": "Global / Archival",
                    "era": "Historical",
                    "source": fpath.name,
                    "entities": [doc_name],
                    "text": content[:45000]
                })
                logging.info(f"Loaded raw document: {fpath.name} ({len(content)} chars)")
        except Exception as e:
            logging.warning(f"Failed to read {fpath}: {e}")
    return documents

def run_ingestion(corpus_json: Path = None, raw_dir: Path = None, wipe_existing: bool = False):
    logging.info(f"Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL)

    cols = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in cols or wipe_existing:
        if wipe_existing and COLLECTION_NAME in cols:
            client.delete_collection(COLLECTION_NAME)
        logging.info(f"Creating collection '{COLLECTION_NAME}' (size={VECTOR_DIM}, metric=Cosine)...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=rest_models.VectorParams(
                size=VECTOR_DIM,
                distance=rest_models.Distance.COSINE
            )
        )

    logging.info(f"Loading embedding model '{EMBEDDING_MODEL_NAME}'...")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

    all_docs = []
    if corpus_json and corpus_json.exists():
        all_docs.extend(load_corpus_from_json(corpus_json))
    if raw_dir and raw_dir.exists():
        all_docs.extend(load_raw_files_from_dir(raw_dir))

    logging.info(f"Preparing chunks for {len(all_docs)} historical articles/documents...")
    points = []

    for doc in all_docs:
        raw_text = doc.get("text", "")
        chunks = chunk_text(raw_text, chunk_size=550, overlap=100)
        for idx, chunk_str in enumerate(chunks):
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc.get('title')}_{idx}_{chunk_str[:30]}"))
            payload = {
                "id": f"{doc.get('source', 'corpus')}_{idx}",
                "title": doc.get("title"),
                "region": doc.get("region", "Global"),
                "era": doc.get("era", "Historical"),
                "source": doc.get("source"),
                "entities": doc.get("entities", []),
                "text": chunk_str,
                "chunk_index": idx,
                "total_chunks": len(chunks)
            }
            points.append((chunk_id, chunk_str, payload))

    logging.info(f"Generated {len(points)} text chunks. Calculating embeddings in batches...")
    BATCH_SIZE = 64
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i : i + BATCH_SIZE]
        texts = [b[1] for b in batch]
        embeddings = embedder.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        qdrant_points = [
            rest_models.PointStruct(
                id=chunk_id,
                vector=emb.tolist(),
                payload=payload
            )
            for (chunk_id, chunk_str, payload), emb in zip(batch, embeddings)
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=qdrant_points)
        logging.info(f"Upserted batch {i // BATCH_SIZE + 1} / {(len(points) + BATCH_SIZE - 1) // BATCH_SIZE} ({len(qdrant_points)} points)")

    info = client.get_collection(COLLECTION_NAME)
    logging.info(f"SUCCESS! Collection '{COLLECTION_NAME}' now contains {info.points_count} points.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline 1 Global History Ingestion")
    default_json = Path(__file__).parent.parent / "data" / "historical_rag" / "global_history_corpus.json"
    default_raw = Path(__file__).parent.parent / "data" / "historical_rag" / "raw"
    parser.add_argument("--corpus-json", type=str, default=str(default_json))
    parser.add_argument("--raw-dir", type=str, default=str(default_raw))
    parser.add_argument("--wipe", action="store_true")
    args = parser.parse_args()
    run_ingestion(corpus_json=Path(args.corpus_json), raw_dir=Path(args.raw_dir), wipe_existing=args.wipe)