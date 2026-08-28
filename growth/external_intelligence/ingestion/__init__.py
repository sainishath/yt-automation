# -*- coding: utf-8 -*-
"""
growth.external_intelligence.ingestion
--------------------------------------
Tabular research dataset ingestion package (CSV/TSV/XLSX).
"""

from growth.external_intelligence.ingestion.ingestion_schemas import (
    TranscriptStatus,
    PerformanceClass,
    ExternalDatasetRegistryModel,
    ValidatedExternalVideoRecord,
    IngestionReport
)
from growth.external_intelligence.ingestion.raw_validator import (
    validate_record,
    normalize_row_keys,
    extract_video_id
)
from growth.external_intelligence.ingestion.normalizer import (
    normalize_dataset_records
)
from growth.external_intelligence.ingestion.dataset_importer import (
    TabularDatasetImporter
)

__all__ = [
    "TranscriptStatus",
    "PerformanceClass",
    "ExternalDatasetRegistryModel",
    "ValidatedExternalVideoRecord",
    "IngestionReport",
    "validate_record",
    "normalize_row_keys",
    "extract_video_id",
    "normalize_dataset_records",
    "TabularDatasetImporter"
]
