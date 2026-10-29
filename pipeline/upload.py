# -*- coding: utf-8 -*-
"""
pipeline/upload.py
------------------
Alias module re-exporting compliant upload & alerting helpers from pipeline/upload_guard.py.
"""

from pipeline.upload_guard import (
    append_rag_citations_to_description,
    build_youtube_insert_body,
    format_rag_citations_footer,
    send_discord_alert,
)

__all__ = [
    "append_rag_citations_to_description",
    "build_youtube_insert_body",
    "format_rag_citations_footer",
    "send_discord_alert",
]
