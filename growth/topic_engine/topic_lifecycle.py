# -*- coding: utf-8 -*-
"""
topic_lifecycle.py
------------------
Manages the complete lifecycle of topic candidates:
DISCOVERED → SCORED → QUEUED → ASSIGNED → PRODUCED → PUBLISHED → MEASURED → LEARNED → ARCHIVED.
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from growth.db.database import get_db, DEFAULT_DB_PATH
from growth.topic_engine.topic_scorer import score_topic
from growth.topic_engine.deduplicator import is_duplicate_topic


LIFECYCLE_STATES = [
    "DISCOVERED", "SCORED", "QUEUED", "ASSIGNED", "PRODUCED",
    "PUBLISHED", "MEASURED", "LEARNED", "ARCHIVED"
]


class TopicLifecycleManager:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path

    def add_candidate_topic(
        self,
        channel_id: str,
        topic_text: str,
        category: str,
        cluster: str = "General",
        risk_tier: str = "proven"
    ) -> str:
        """Discovers and inserts a new candidate topic if not duplicate."""
        existing_topics = self.list_topics(channel_id)
        existing_texts = [t["topic_text"] for t in existing_topics]
        is_dup, matched = is_duplicate_topic(topic_text, existing_texts)
        if is_dup:
            raise ValueError(f"Duplicate topic detected: '{topic_text}' matches '{matched}'")

        score_res = score_topic(topic_text, channel_id, category)
        topic_id = f"top_{uuid.uuid4().hex[:8]}"

        with get_db(self.db_path) as conn:
            conn.execute("""
                INSERT INTO topic_candidates (
                    topic_id, channel_id, topic_text, category, cluster,
                    score, score_breakdown, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'QUEUED')
            """, (
                topic_id, channel_id, topic_text, category, cluster,
                score_res["final_score"], json.dumps(score_res["breakdown"])
            ))

        return topic_id

    def list_topics(self, channel_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM topic_candidates WHERE channel_id = ? AND status = ? ORDER BY score DESC",
                    (channel_id, status)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM topic_candidates WHERE channel_id = ? ORDER BY score DESC",
                    (channel_id,)
                ).fetchall()
            return [dict(r) for r in rows]

    def update_topic_status(self, topic_id: str, new_status: str) -> None:
        if new_status not in LIFECYCLE_STATES:
            raise ValueError(f"Invalid lifecycle state: {new_status}")
        with get_db(self.db_path) as conn:
            conn.execute("UPDATE topic_candidates SET status = ? WHERE topic_id = ?", (new_status, topic_id))

    def get_next_queued_topic(self, channel_id: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM topic_candidates WHERE channel_id = ? AND status = 'QUEUED' ORDER BY score DESC LIMIT 1",
                (channel_id,)
            ).fetchone()
            return dict(row) if row else None
