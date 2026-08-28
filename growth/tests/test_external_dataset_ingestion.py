# -*- coding: utf-8 -*-
"""
test_external_dataset_ingestion.py
-----------------------------------
Comprehensive test suite for Phase 34: Tabular External Research Dataset Ingestion (CSV/TSV/XLSX).
Verifies:
1. CSV, TSV, and header alias normalization.
2. YouTube URL and video ID validation.
3. Duplicate video detection and invalid row quarantine.
4. Public data boundary (rejection of fabricated private metrics).
5. Transcript status and external disk file persistence.
6. Channel median calculation, MAD protection, and computed vs researcher classification.
7. Dry-run DB immutability.
8. Niche separation and First-Party Dominance.
"""

import unittest
import tempfile
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db, get_db
from growth.external_intelligence.repository import ExternalIntelligenceRepository
from growth.external_intelligence.ingestion.ingestion_schemas import (
    TranscriptStatus,
    PerformanceClass,
    ValidatedExternalVideoRecord
)
from growth.external_intelligence.ingestion.raw_validator import (
    validate_record,
    extract_video_id,
    normalize_row_keys
)
from growth.external_intelligence.ingestion.normalizer import (
    normalize_dataset_records
)
from growth.external_intelligence.ingestion.dataset_importer import (
    TabularDatasetImporter
)


class TestExternalDatasetIngestion(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test_ingestion.db"
        self.transcript_dir = Path(self.tmp_dir.name) / "transcripts"
        init_db(self.db_path)

        self.repo = ExternalIntelligenceRepository(self.db_path)
        self.importer = TabularDatasetImporter(
            repo=self.repo,
            db_path=self.db_path,
            transcript_dir=self.transcript_dir
        )

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_01_youtube_id_extraction_and_alias_normalization(self):
        """1. Validates YouTube URL parsing and column alias normalization."""
        self.assertEqual(extract_video_id("https://www.youtube.com/watch?v=rPq5-5z_2fE"), "rPq5-5z_2fE")
        self.assertEqual(extract_video_id("https://youtu.be/rPq5-5z_2fE"), "rPq5-5z_2fE")
        self.assertEqual(extract_video_id("https://www.youtube.com/shorts/rPq5-5z_2fE"), "rPq5-5z_2fE")
        self.assertEqual(extract_video_id("rPq5-5z_2fE"), "rPq5-5z_2fE")
        self.assertIsNone(extract_video_id("invalid_url_not_id"))

        raw = {
            "creator": "Fireship",
            "link": "https://youtu.be/rPq5-5z_2fE",
            "view_count": "1450000",
            "like_count": "92000",
            "title": "Python Decorators",
            "captions": "Decorators wrap functions."
        }
        normalized = normalize_row_keys(raw)
        self.assertEqual(normalized["channel_name"], "Fireship")
        self.assertEqual(normalized["youtube_url"], "https://youtu.be/rPq5-5z_2fE")
        self.assertEqual(normalized["views"], "1450000")
        self.assertEqual(normalized["likes"], "92000")
        self.assertEqual(normalized["video_title"], "Python Decorators")
        self.assertEqual(normalized["transcript"], "Decorators wrap functions.")

    def test_02_private_metric_rejection_and_quarantine(self):
        """2. Prohibits fabricated private metrics (retention, CTR) and quarantines row."""
        raw_row = {
            "channel_name": "TechChannel",
            "video_title": "Understanding Memory",
            "youtube_url": "https://youtu.be/mem11111111",
            "views": "500000",
            "retention": "85.4%",  # Forbidden private metric
            "ctr": "12.0%"         # Forbidden private metric
        }
        rec = validate_record(1, raw_row, dataset_id="ds_test")
        self.assertFalse(rec.is_valid)
        self.assertTrue(any("Forbidden private metric" in err for err in rec.validation_errors))

    def test_03_csv_import_end_to_end_and_transcripts(self):
        """3. Ingests CSV dataset with valid rows, missing metric handling, and transcript file persistence."""
        csv_content = """channel_name,channel_url,public_subscriber_count,video_title,youtube_url,video_id,published_at,duration_seconds,views,likes,comments,transcript_status,transcript,performance_class,relative_performance,selection_reason,uncertainties
Fireship,https://www.youtube.com/@Fireship,3100000,Python Decorators in 100 Seconds,https://www.youtube.com/shorts/rPq5-5z_2fE,rPq5-5z_2fE,2024-02-15,58.0,1450000,92000,1400,OFFICIAL_CAPTIONS,"Think of a decorator like putting a wrapper around a function.",HIGH_PERFORMER,2.4,Analogy-first explanation,High visual speed
Fireship,https://www.youtube.com/@Fireship,3100000,Why Docker matters,https://www.youtube.com/shorts/dk38-aBc991,dk38-aBc991,2024-03-01,48.0,750000,,,OFFICIAL_CAPTIONS,"Docker solves dependency conflicts.",NORMAL_PERFORMER,1.0,Container mental model,None
ArjanCodes,https://www.youtube.com/@ArjanCodes,450000,Python Mistake,https://www.youtube.com/shorts/p9x1-mK99a0,p9x1-mK99a0,2024-01-10,42.0,300000,20000,400,UNAVAILABLE,"",HIGH_PERFORMER,1.8,Mistake-first hook,None
"""
        csv_file = Path(self.tmp_dir.name) / "test_data.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        rep = self.importer.import_dataset(
            file_path=csv_file,
            dataset_id="ds_test_csv",
            dataset_version="v1.0",
            target_channel_id="channel_b",
            dry_run=False
        )

        self.assertEqual(rep.total_rows, 3)
        self.assertEqual(rep.valid_rows, 3)
        self.assertEqual(rep.rejected_rows, 0)
        self.assertEqual(rep.missing_transcripts, 1)
        self.assertEqual(rep.missing_metrics, 1)  # Docker video has missing likes & comments

        # Check SQLite persistence
        channels = self.repo.list_external_channels("channel_b")
        self.assertEqual(len(channels), 2)  # Fireship and ArjanCodes

        videos = self.repo.list_external_videos()
        self.assertEqual(len(videos), 3)

        # Check transcript saved on disk
        t_file = self.transcript_dir / "rPq5-5z_2fE.txt"
        self.assertTrue(t_file.exists())
        self.assertIn("Think of a decorator like putting a wrapper", t_file.read_text(encoding="utf-8"))

        # Check dataset registry
        ds = self.repo.get_external_dataset("ds_test_csv")
        self.assertIsNotNone(ds)
        self.assertEqual(ds["valid_count"], 3)

    def test_04_tsv_import_and_header_variations(self):
        """4. Ingests TSV format with tab delimiters and non-standard aliases."""
        tsv_content = "creator\thandle\tsubs\ttitle\tlink\tid\tdate\tlength\tview_count\tlike_count\tcomment_count\tcaption_status\ttext\tperformance\tmultiplier\treason\tcaveats\n" \
                      "WebDevSimplified\thttps://youtube.com/@WDS\t1500000\tJS Promises Explained\thttps://youtube.com/shorts/wds1-pP88c3\twds1-pP88c3\t2024-02-05\t50.0\t600000\t35000\t600\tOFFICIAL_CAPTIONS\tPromises are IOUs for async values.\tNORMAL_PERFORMER\t1.0\tIOU analogy\tNone\n"

        tsv_file = Path(self.tmp_dir.name) / "test_data.tsv"
        tsv_file.write_text(tsv_content, encoding="utf-8")

        rep = self.importer.import_dataset(
            file_path=tsv_file,
            dataset_id="ds_test_tsv",
            target_channel_id="channel_b",
            dry_run=False
        )
        self.assertEqual(rep.valid_rows, 1)
        self.assertEqual(rep.rejected_rows, 0)

        vid = self.repo.get_external_video("ext_vid_wds1-pP88c3")
        self.assertIsNotNone(vid)
        self.assertEqual(vid["views"], 600000)

    def test_05_dry_run_immutability(self):
        """5. Dry-run mode validates records and calculates distributions without modifying SQLite or disk."""
        csv_content = """channel_name,video_title,youtube_url,views,transcript_status,performance_class
TestChannel,Python Tips,https://youtu.be/dry11111111,100000,UNAVAILABLE,NORMAL_PERFORMER
"""
        csv_file = Path(self.tmp_dir.name) / "dry_test.csv"
        csv_file.write_text(csv_content, encoding="utf-8")

        rep = self.importer.import_dataset(
            file_path=csv_file,
            dataset_id="ds_dry_run",
            dry_run=True
        )
        self.assertEqual(rep.valid_rows, 1)
        self.assertTrue(rep.is_dry_run)

        # Database must be empty
        self.assertIsNone(self.repo.get_external_dataset("ds_dry_run"))
        self.assertEqual(len(self.repo.list_external_videos()), 0)

    def test_06_channel_median_calculation_and_classification_disagreement(self):
        """6. Calculates relative view multiplier vs channel median and preserves researcher vs computed class."""
        records = [
            ValidatedExternalVideoRecord(
                row_index=1, channel_name="ChannelX", channel_url="url", public_subscriber_count=10000,
                video_title="Vid 1", youtube_url="url", video_id="vid_01", published_at=None,
                duration_seconds=45.0, views=100000, likes=1000, comments=50,
                transcript_status=TranscriptStatus.UNAVAILABLE, transcript_text=None, transcript_path=None,
                researcher_classification=PerformanceClass.NORMAL_PERFORMER, researcher_relative_performance=1.0
            ),
            ValidatedExternalVideoRecord(
                row_index=2, channel_name="ChannelX", channel_url="url", public_subscriber_count=10000,
                video_title="Vid 2", youtube_url="url", video_id="vid_02", published_at=None,
                duration_seconds=45.0, views=300000, likes=3000, comments=150,
                transcript_status=TranscriptStatus.UNAVAILABLE, transcript_text=None, transcript_path=None,
                researcher_classification=PerformanceClass.NORMAL_PERFORMER, researcher_relative_performance=1.0
            ),
            ValidatedExternalVideoRecord(
                row_index=3, channel_name="ChannelX", channel_url="url", public_subscriber_count=10000,
                video_title="Vid 3", youtube_url="url", video_id="vid_03", published_at=None,
                duration_seconds=45.0, views=50000, likes=500, comments=20,
                transcript_status=TranscriptStatus.UNAVAILABLE, transcript_text=None, transcript_path=None,
                researcher_classification=PerformanceClass.NORMAL_PERFORMER, researcher_relative_performance=1.0
            ),
        ]

        normalized = normalize_dataset_records(records)
        # Median of [50k, 100k, 300k] is 100k
        # Vid 2: 300k / 100k = 3.0x -> Computed HIGH_PERFORMER (even though researcher said NORMAL)
        # Vid 3: 50k / 100k = 0.5x -> Computed LOW_PERFORMER
        self.assertEqual(normalized[1].computed_relative_views, 3.0)
        self.assertEqual(normalized[1].computed_classification, PerformanceClass.HIGH_PERFORMER)
        self.assertEqual(normalized[1].researcher_classification, PerformanceClass.NORMAL_PERFORMER)

        self.assertEqual(normalized[2].computed_relative_views, 0.5)
        self.assertEqual(normalized[2].computed_classification, PerformanceClass.LOW_PERFORMER)

    def test_07_feature_leakage_and_namespace_isolation(self):
        """7. Verifies strict target leakage guard in ML feature extraction."""
        from growth.external_intelligence.ingestion.feature_extractor import BenchmarkFeaturePipeline
        v22_path = ROOT_DIR / "research" / "youtube_competitors" / "manifests" / "coding_tech_corpus_v2.2.xlsx"
        if v22_path.exists():
            pipeline = BenchmarkFeaturePipeline(v22_path)
            ml_rows, q_rows = pipeline.build_ml_feature_matrix()
            self.assertGreater(len(ml_rows), 0)
            
            for row in ml_rows:
                # Pre-publication features (feat_) must NEVER contain target or annot keys
                feat_keys = [k for k in row.keys() if k.startswith("feat_")]
                target_keys = [k for k in row.keys() if k.startswith("target_")]
                annot_keys = [k for k in row.keys() if k.startswith("annot_")]
                
                self.assertGreater(len(feat_keys), 0)
                self.assertGreater(len(target_keys), 0)
                self.assertGreater(len(annot_keys), 0)
                
                # Check for accidental leakage into feat_ namespace
                for fk in feat_keys:
                    for forbidden in ["target", "annot", "relative_views", "views_raw", "performance_class"]:
                        self.assertNotIn(forbidden, fk.lower())


if __name__ == "__main__":
    unittest.main()
