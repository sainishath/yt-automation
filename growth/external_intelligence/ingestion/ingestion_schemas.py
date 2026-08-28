# -*- coding: utf-8 -*-
"""
ingestion_schemas.py
--------------------
Schema and data models for tabular external research dataset ingestion (CSV/TSV/XLSX).
Preserves researcher claims vs computed metrics and maintains strict provenance.
"""

from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime


class TranscriptStatus(str, Enum):
    OFFICIAL_CAPTIONS = "OFFICIAL_CAPTIONS"
    AUTO_GENERATED = "AUTO_GENERATED"
    CREATOR_PROVIDED = "CREATOR_PROVIDED"
    UNAVAILABLE = "UNAVAILABLE"


class PerformanceClass(str, Enum):
    HIGH_PERFORMER = "HIGH_PERFORMER"
    NORMAL_PERFORMER = "NORMAL_PERFORMER"
    LOW_PERFORMER = "LOW_PERFORMER"
    UNCLASSIFIED = "UNCLASSIFIED"


@dataclass
class ExternalDatasetRegistryModel:
    dataset_id: str
    dataset_version: str
    source: str = "GEMINI_PUBLIC_RESEARCH"
    collector: str = "HUMAN_OPERATOR"
    collection_timestamp: Optional[str] = None
    schema_version: str = "external_tabular_v1"
    row_count: int = 0
    valid_count: int = 0
    rejected_count: int = 0
    quarantined_count: int = 0
    file_path: Optional[str] = None
    imported_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidatedExternalVideoRecord:
    row_index: int
    channel_name: str
    channel_url: str
    public_subscriber_count: Optional[int]
    video_title: str
    youtube_url: str
    video_id: str
    published_at: Optional[str]
    duration_seconds: float
    views: int
    likes: Optional[int]
    comments: Optional[int]
    transcript_status: TranscriptStatus
    transcript_text: Optional[str]
    transcript_path: Optional[str]
    researcher_classification: PerformanceClass
    researcher_relative_performance: Optional[float]
    computed_classification: PerformanceClass = PerformanceClass.UNCLASSIFIED
    computed_relative_views: float = 1.0
    selection_reason: Optional[str] = None
    uncertainties: List[str] = field(default_factory=list)
    dataset_id: Optional[str] = None
    source_type: str = "PUBLIC_YOUTUBE"
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["transcript_status"] = self.transcript_status.value if hasattr(self.transcript_status, "value") else str(self.transcript_status)
        d["researcher_classification"] = self.researcher_classification.value if hasattr(self.researcher_classification, "value") else str(self.researcher_classification)
        d["computed_classification"] = self.computed_classification.value if hasattr(self.computed_classification, "value") else str(self.computed_classification)
        return d


@dataclass
class IngestionReport:
    dataset_id: str
    file_path: str
    total_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    quarantined_rows: int = 0
    duplicate_rows: int = 0
    missing_transcripts: int = 0
    missing_metrics: int = 0
    performance_distribution: Dict[str, int] = field(default_factory=dict)
    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    quarantine_log: List[Dict[str, Any]] = field(default_factory=list)
    is_dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
