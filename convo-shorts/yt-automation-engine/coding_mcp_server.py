# -*- coding: utf-8 -*-
"""
coding_mcp_server.py
--------------------
FastMCP server exposing specialized tools for Pipeline 2 (Coding & System Design).
"""

import json
import urllib.request
from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer

mcp = FastMCP("coding-education-rag")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
COLLECTION = "coding_education_rag"
QDRANT_URL = "http://127.0.0.1:6333"

def _qdrant_search(query_vector: list, limit: int = 3, filter_category: str = None):
    payload = {"vector": query_vector, "limit": limit, "with_payload": True}
    if filter_category:
        payload["filter"] = {
            "must": [{"key": "category", "match": {"value": filter_category}}]
        }
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            res = json.loads(r.read().decode("utf-8"))
            return res.get("result", [])
    except Exception:
        return []

@mcp.tool()
def search_code_patterns(query: str, limit: int = 3) -> str:
    """Retrieves senior vs junior code patterns and pitfalls."""
    q_vec = embedder.encode(query).tolist()
    results = _qdrant_search(q_vec, limit=limit, filter_category="code_pattern")
    return "\n\n---\n\n".join([f"### {h['payload'].get('title')}\n{h['payload'].get('text')}" for h in results])

@mcp.tool()
def search_system_design(concept: str, limit: int = 3) -> str:
    """Retrieves system design tradeoffs (sharding, caching, streaming, rate limiting)."""
    q_vec = embedder.encode(concept).tolist()
    results = _qdrant_search(q_vec, limit=limit, filter_category="system_design")
    return "\n\n---\n\n".join([f"### {h['payload'].get('title')}\n{h['payload'].get('text')}" for h in results])

@mcp.tool()
def search_production_postmortems(incident_query: str, limit: int = 2) -> str:
    """Retrieves real-world engineering post-mortems and outage root causes for storytelling."""
    q_vec = embedder.encode(incident_query).tolist()
    results = _qdrant_search(q_vec, limit=limit, filter_category="post_mortem")
    return "\n\n---\n\n".join([f"### {h['payload'].get('title')}\n{h['payload'].get('text')}" for h in results])

if __name__ == "__main__":
    mcp.run()
