# -*- coding: utf-8 -*-
"""
server.py
---------
Lightweight REST API Bridge connecting Growth Intelligence to n8n Automation Workflows.
Runs on Port 8010.
"""

import sys
import json
import logging
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from growth.db.database import init_db
from growth.db.models import GrowthRepository, VideoModel
from growth.planner.content_planner import ContentPlanner
from growth.analytics.collector import AnalyticsCollector
from growth.learning.learning_engine import LearningEngine

PORT = 8010
LOG_FILE = Path("growth_server.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [GrowthServer] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)


class GrowthRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        repo = GrowthRepository()

        if path == "/api/growth/health" or path == "/health":
            self._send_json(200, {
                "status": "ok",
                "service": "growth-intelligence-server",
                "port": PORT
            })

        elif path == "/api/growth/plan-next":
            channel = params.get("channel", ["channel_a"])[0]
            try:
                planner = ContentPlanner(repo)
                plan = planner.plan_next_video(channel)
                self._send_json(200, {"status": "success", "plan": plan})
            except Exception as e:
                logging.error(f"Planning failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/growth/dashboard":
            try:
                ch_a_vids = repo.list_videos_by_channel("channel_a")
                ch_b_vids = repo.list_videos_by_channel("channel_b")
                self._send_json(200, {
                    "status": "success",
                    "channels": {
                        "channel_a": {"video_count": len(ch_a_vids)},
                        "channel_b": {"video_count": len(ch_b_vids)}
                    }
                })
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/external-intelligence/channels":
            try:
                from growth.external_intelligence.repository import ExternalIntelligenceRepository
                ext_repo = ExternalIntelligenceRepository(repo.db_path)
                channel = params.get("channel", [None])[0]
                channels = ext_repo.list_external_channels(channel)
                self._send_json(200, {"status": "success", "external_channels": channels})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/external-intelligence/patterns":
            try:
                from growth.external_intelligence.repository import ExternalIntelligenceRepository
                ext_repo = ExternalIntelligenceRepository(repo.db_path)
                channel = params.get("channel", ["channel_a"])[0]
                patterns = ext_repo.list_patterns(channel)
                self._send_json(200, {"status": "success", "patterns": patterns})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/external-intelligence/recommendations":
            try:
                from growth.external_intelligence.repository import ExternalIntelligenceRepository
                from growth.external_intelligence.recommendation_engine import build_explainable_recommendation
                from growth.external_intelligence.schemas import ExternalPriorModel, ExternalPatternModel, TransferabilityScoreModel, TransferabilityClassification, PriorStatus, PatternType
                ext_repo = ExternalIntelligenceRepository(repo.db_path)
                channel = params.get("channel", ["channel_a"])[0]
                priors = ext_repo.list_external_priors(channel)
                recs = []
                for pr in priors:
                    pat_data = ext_repo.get_pattern(pr["pattern_id"])
                    ts_data = ext_repo.get_transferability_score(pr["pattern_id"], channel)
                    if pat_data and ts_data:
                        pat_model = ExternalPatternModel(
                            pattern_id=pat_data["pattern_id"], target_channel_id=channel,
                            pattern_type=PatternType(pat_data["pattern_type"]), name=pat_data["name"],
                            description=pat_data["description"], surface_technique=pat_data["surface_technique"],
                            underlying_principle=pat_data["underlying_principle"], our_possible_implementation=pat_data["our_possible_implementation"],
                            channel_count=pat_data["channel_count"], video_count=pat_data["video_count"], confidence=pat_data["confidence"]
                        )
                        ts_model = TransferabilityScoreModel(
                            transferability_id=ts_data["transferability_id"], pattern_id=pr["pattern_id"],
                            target_channel_id=channel, topic_similarity=ts_data["topic_similarity"],
                            audience_similarity=ts_data["audience_similarity"], format_similarity=ts_data["format_similarity"],
                            production_similarity=ts_data["production_similarity"], evidence_strength=ts_data["evidence_strength"],
                            repeatability=ts_data["repeatability"], overall_transferability_score=ts_data["overall_transferability_score"],
                            classification=TransferabilityClassification(ts_data["classification"]), reason=ts_data["reason"]
                        )
                        prior_model = ExternalPriorModel(
                            prior_id=pr["prior_id"], target_channel_id=channel, pattern_id=pr["pattern_id"],
                            hypothesis=pr["hypothesis"], transferability_classification=TransferabilityClassification(pr["transferability_classification"]),
                            prior_weight=pr["prior_weight"], status=PriorStatus(pr["status"])
                        )
                        recs.append(build_explainable_recommendation(prior_model, pat_model, ts_model))
                self._send_json(200, {"status": "success", "recommendations": recs})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/growth/experiments/external":
            try:
                channel = params.get("channel", [None])[0]
                experiments = repo.list_experiments(channel_id=channel)
                ext_experiments = [
                    e for e in experiments
                    if e.get("external_prior_id") or e.get("provenance") in ["EXTERNAL_INTELLIGENCE", "PUBLIC_YOUTUBE", "SIMULATION"]
                ]
                self._send_json(200, {"status": "success", "count": len(ext_experiments), "experiments": ext_experiments})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/experiments/ready", "/api/growth/experiments/ready"]:
            try:
                from growth.experiments.experiment_queue import ExperimentQueue
                queue = ExperimentQueue(repo=repo)
                channel = params.get("channel", [None])[0]
                if channel:
                    ready = queue.get_ready_experiments(channel)
                else:
                    ready = queue.get_ready_experiments("channel_a") + queue.get_ready_experiments("channel_b")
                self._send_json(200, {"status": "success", "count": len(ready), "ready_experiments": ready})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path.endswith("/outcome") and (path.startswith("/api/experiments/") or path.startswith("/api/growth/experiments/")):
            try:
                from growth.experiments.experiment_manager import ExperimentManager
                exp_id = path.split("/")[-2]
                mgr = ExperimentManager(repo=repo)
                outcome = mgr.evaluate_experiment_from_db(exp_id)
                self._send_json(200, {"status": "success", "outcome": outcome})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path.endswith("/lineage") and (path.startswith("/api/experiments/") or path.startswith("/api/growth/experiments/")):
            try:
                from growth.experiments.lineage_tracker import ExperimentLineageTracker
                exp_id = path.split("/")[-2]
                tracker = ExperimentLineageTracker(repo=repo)
                lineage = tracker.trace_experiment(exp_id)
                self._send_json(200, {"status": "success", "lineage": lineage})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/strategy-versions", "/api/growth/strategy-versions"]:
            try:
                from growth.strategy.strategy_manager import StrategyManager
                strat_mgr = StrategyManager()
                strat_a = strat_mgr.get_active_strategy("channel_a")
                strat_b = strat_mgr.get_active_strategy("channel_b")
                self._send_json(200, {"status": "success", "strategy_versions": {"channel_a": strat_a, "channel_b": strat_b}})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/experiments", "/api/growth/experiments"] or path.startswith("/api/experiments/") or path.startswith("/api/growth/experiments/"):
            try:
                clean_path = path.replace("/api/growth/experiments/", "").replace("/api/experiments/", "").strip()
                if clean_path and clean_path not in ["/api/experiments", "/api/growth/experiments"]:
                    exp = repo.get_experiment(clean_path)
                    if exp:
                        arms = repo.get_experiment_arms(clean_path)
                        self._send_json(200, {"status": "success", "experiment": exp, "arms": arms})
                    else:
                        self._send_json(404, {"status": "error", "message": f"Experiment '{clean_path}' not found"})
                else:
                    channel = params.get("channel", [None])[0]
                    status_filter = params.get("status", [None])[0]
                    experiments = repo.list_experiments(channel_id=channel, status=status_filter)
                    self._send_json(200, {"status": "success", "count": len(experiments), "experiments": experiments})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})

        else:
            self._send_json(404, {"status": "error", "message": "Endpoint not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(post_body)
        except Exception:
            payload = {}

        repo = GrowthRepository()
        collector = AnalyticsCollector(repo, use_mock_engine=True)

        if path == "/api/growth/record-upload":
            try:
                vid_id = payload.get("video_id")
                channel_id = payload.get("channel_id", "channel_a")
                title = payload.get("title", f"Video {vid_id}")
                duration = float(payload.get("duration", 45.0))
                yt_id = payload.get("youtube_video_id")
                yt_url = payload.get("youtube_url")

                vid = VideoModel(
                    video_id=vid_id,
                    channel_id=channel_id,
                    pipeline_id="alternate-history-shorts" if channel_id == "channel_a" else "convo-shorts",
                    title=title,
                    duration=duration,
                    youtube_video_id=yt_id,
                    youtube_url=yt_url,
                    upload_status="UPLOADED",
                    privacy_status=payload.get("privacy_status", "public"),
                    review_status="APPROVED",
                    strategy_version=payload.get("strategy_version", "v1.0")
                )
                repo.upsert_video(vid)
                collector.collect_snapshots_for_video(vid_id, duration=duration)

                self._send_json(200, {"status": "success", "video_id": vid_id, "message": "Upload recorded and snapshots queued"})
            except Exception as e:
                logging.error(f"Record upload failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/growth/run-learning-cycle":
            channel = payload.get("channel_id", "channel_a")
            try:
                engine = LearningEngine(repo, collector)
                res = engine.run_channel_learning_cycle(channel)
                self._send_json(200, {"status": "success", "learning_cycle": res})
            except Exception as e:
                logging.error(f"Learning cycle failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path == "/api/external-intelligence/research":
            channel = payload.get("channel_id", "channel_a")
            use_live = payload.get("use_live_api", False)
            try:
                from growth.external_intelligence.researcher import ExternalResearcher
                researcher = ExternalResearcher(repo=None)
                res = researcher.run_channel_research(channel, use_live_api=use_live)
                self._send_json(200, {"status": "success", "research_result": res})
            except Exception as e:
                logging.error(f"External research failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/experiments/approve", "/api/growth/experiments/approve"]:
            try:
                exp_id = payload.get("experiment_id")
                from growth.experiments.experiment_queue import ExperimentQueue
                queue = ExperimentQueue(repo=repo)
                res = queue.approve_experiment(exp_id)
                self._send_json(200, res)
            except Exception as e:
                logging.error(f"Approve experiment failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/jobs/create-experiment-job", "/api/growth/jobs/create-experiment-job"]:
            try:
                channel = payload.get("channel_id", "channel_a")
                topic_override = payload.get("topic_override")
                from growth.experiments.production_adapter import ProductionJobAdapter
                adapter = ProductionJobAdapter(repo=repo)
                job_res = adapter.create_experiment_production_job(channel, topic_override=topic_override)
                self._send_json(200, {"status": "success", "job": job_res})
            except Exception as e:
                logging.error(f"Create experiment job failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/videos/register-upload", "/api/growth/videos/register-upload"]:
            try:
                vid_id = payload.get("video_id")
                yt_id = payload.get("youtube_video_id")
                yt_url = payload.get("youtube_url")
                privacy = payload.get("privacy_status", "public")
                from growth.experiments.sample_tracker import ExperimentSampleTracker
                tracker = ExperimentSampleTracker(repo=repo)
                res = tracker.register_real_upload(video_id=vid_id, youtube_video_id=yt_id, youtube_url=yt_url, privacy=privacy)
                self._send_json(200, res)
            except Exception as e:
                logging.error(f"Register upload failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        elif path in ["/api/snapshots/check-due", "/api/growth/snapshots/check-due"]:
            try:
                from growth.analytics.snapshot_scheduler import SnapshotScheduler
                scheduler = SnapshotScheduler(repo=repo, dry_run=payload.get("dry_run", False))
                sched_res = scheduler.run_pending_snapshot_checks()
                self._send_json(200, sched_res)
            except Exception as e:
                logging.error(f"Check due snapshots failed: {e}")
                self._send_json(500, {"status": "error", "message": str(e)})

        else:
            self._send_json(404, {"status": "error", "message": "Endpoint not found"})


def run_server(port: int = PORT):
    init_db()
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, GrowthRequestHandler)
    logging.info(f"Growth Intelligence REST API server running on http://127.0.0.1:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down Growth server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
